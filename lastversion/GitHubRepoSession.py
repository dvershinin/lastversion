import json
import logging
import math
import os
import re
import time
from datetime import timedelta

import feedparser
from appdirs import user_cache_dir
from dateutil import parser

from .ProjectHolder import ProjectHolder
from .utils import ApiCredentialsError, BadProjectError

log = logging.getLogger(__name__)

TOKEN_PRO_TIP = 'ProTip: set GITHUB_API_TOKEN env var as per ' \
                'https://github.com/dvershinin/lastversion#tips'


def set_matching_from_tag(ret, tag):
    ret = tag


def asset_matches(asset, search, regex_matching):
    """Check if the asset equals to string or satisfies a regular expression
    Args:
        asset (dict): asset dict as returned by the API
        search (str): string or regexp to match asset's name or label with
        regex_matching (bool): whether search argument is a regexp
    Returns:
        bool: Whether match is satisfied
    """
    if regex_matching:
        if asset['label'] and re.search(search, asset['label']):
            return True
        if asset['name'] and re.search(search, asset['name']):
            return True
    elif search in (asset['label'], asset['name']):
        return True
    return False


class GitHubRepoSession(ProjectHolder):
    """A class to represent a GitHub project holder."""

    DEFAULT_HOSTNAME = 'github.com'
    DEFAULT_HOLDER = True

    # one-word aliases or simply known popular repos to skip using search API
    KNOWN_REPOS_BY_NAME = {
        'php': {
            'repo': 'php/php-src',
            # get URL from official website because it is a "prepared" source
            'release_url_format': "https://www.php.net/distributions/php-{version}.tar.gz"
        },
        'linux': {'repo': 'torvalds/linux'},
        'kernel': {'repo': 'torvalds/linux'},
        'openssl': {'repo': 'openssl/openssl'}
    }

    """
    The last alphanumeric after digits is part of version scheme, not beta level.
    E.g. 1.1.1b is not beta. Hard-coding such odds repos is required.
    """
    LAST_CHAR_FIX_REQUIRED_ON = [
        'openssl/openssl'
    ]

    """ The following format will benefit from:
    1) not using API, so is not subject to its rate limits
    2) likely has been accessed by someone in CDN and thus faster
    3) provides more or less unique filenames once the stuff is downloaded
    See https://fedoraproject.org/wiki/Packaging:SourceURL#Git_Tags
    We use variation of this: it does not need a parsed version (thus works for --pre better)
    and it is not broken on fancy release tags like v1.2.3-stable
    https://github.com/OWNER/PROJECT/archive/%{gittag}/%{gittag}-%{version}.tar.gz
    """
    RELEASE_URL_FORMAT = "https://{hostname}/{repo}/archive/{tag}/{name}-{tag}.{ext}"
    SHORT_RELEASE_URL_FORMAT = "https://{hostname}/{repo}/archive/{tag}.{ext}"

    def find_repo_by_name_only(self, repo):
        if repo.startswith(('https://', 'http://')):
            return None
        cache_repo_names_file = "{}/repos.json".format(user_cache_dir("lastversion"))
        try:
            with open(cache_repo_names_file, 'r') as reader:
                cache = json.load(reader)
        except (IOError, ValueError):
            cache = {}
        try:
            if repo in cache and time.time() - cache[repo]['updated_at'] < 3600 * 24 * 30:
                log.info("Found {} in repo short name cache".format(repo))
                if not cache[repo]['repo']:
                    raise BadProjectError(
                        'No project found on GitHub for search query: {}'.format(repo)
                    )
                return cache[repo]['repo']
        except TypeError:
            pass
        log.info("Making query against GitHub API to search repo {}".format(repo))
        r = self.get(
            '{}/search/repositories?q={}+in:name'.format(self.api_base, repo))
        if r.status_code == 404:
            # when not found, skip using this holder in the factory by not setting self.repo
            return None
        if r.status_code != 200:
            raise BadProjectError(
                'Error while identifying full repository on GitHub for search query: {}'.format(
                    repo
                )
            )
        data = r.json()
        full_name = ''
        if data['items']:
            full_name = data['items'][0]['full_name']
        cache[repo] = {
            'repo': full_name,
            'updated_at': int(time.time())
        }
        try:
            with open(cache_repo_names_file, 'w') as writer:
                writer.write(
                    json.dumps(cache)
                )
        except (IOError, ValueError):
            pass
        if not full_name:
            raise BadProjectError(
                'No project found on GitHub for search query: {}'.format(repo)
            )
        return full_name

    def __init__(self, repo, hostname):
        super(GitHubRepoSession, self).__init__()
        self.rate_limited_count = 0
        self.api_token = os.getenv("GITHUB_API_TOKEN")
        if not self.api_token:
            self.api_token = os.getenv("GITHUB_TOKEN")
        self.hostname = hostname
        if not self.hostname:
            self.hostname = self.DEFAULT_HOSTNAME
        # Explicitly specify the API version that we want:
        self.headers.update({
            'Accept': 'application/vnd.github.v3+json'
        })
        if self.api_token:
            log.info('Using API token.')
            self.headers.update({'Authorization': "token {}".format(self.api_token)})
        if self.hostname != self.DEFAULT_HOSTNAME:
            self.api_base = 'https://{}/api/v3'.format(self.hostname)
        else:
            self.api_base = 'https://api.{}'.format(self.DEFAULT_HOSTNAME)
        if '/' not in repo:
            official_repo = self.try_get_official(repo)
            if official_repo:
                repo = official_repo
                log.info('Using official repo {}'.format(repo))
            else:
                repo = self.find_repo_by_name_only(repo)
                if repo:
                    log.info('Using repo {} obtained from search API'.format(self.repo))
                else:
                    return
        self.set_repo(repo)

    def get_rate_limit_url(self):
        return '{}/rate_limit'.format(self.api_base)

    def get(self, url, **kwargs):
        r = super(GitHubRepoSession, self).get(url, **kwargs)
        log.info('Got HTTP status code {} from {}'.format(r.status_code, url))
        if r.status_code == 401:
            if self.api_token:
                raise ApiCredentialsError('API request was denied despite using an API token. '
                                          'Missing scopes?')
            raise ApiCredentialsError('Denied API access. Please set GITHUB_API_TOKEN env var '
                                      'as per https://github.com/dvershinin/lastversion#tips')
        if r.status_code == 403:
            if 'X-RateLimit-Reset' in r.headers and 'X-RateLimit-Remaining' in r.headers:
                if self.rate_limited_count > 2:
                    raise ApiCredentialsError(
                        'API requests were denied after retrying {} times'.format(
                            self.rate_limited_count)
                    )
                remaining = int(r.headers['X-RateLimit-Remaining'])
                # 1 sec to account for skewed clock between GitHub and client
                wait_for = float(r.headers['X-RateLimit-Reset']) - time.time() + 1.0
                wait_for = math.ceil(wait_for)
                if not remaining:
                    # got 403, likely due to used quota
                    if wait_for < 300:
                        if wait_for < 0:
                            log.warning(
                                'Exceeded API quota. Repeating request because quota is about to '
                                'be reinstated'
                            )
                        else:
                            w = 'Waiting {} seconds for API quota reinstatement.'.format(wait_for)
                            if "GITHUB_API_TOKEN" not in os.environ \
                                    and 'GITHUB_TOKEN' not in os.environ:
                                w = "{} {}".format(w, TOKEN_PRO_TIP)
                            log.warning(w)
                            time.sleep(wait_for)
                        self.rate_limited_count = self.rate_limited_count + 1
                        return self.get(url)
                    raise ApiCredentialsError(
                        'Exceeded API rate limit after waiting: {}'.format(
                            r.json()['message'])
                    )
            return self.get(url)

        if r.status_code == 403 and url != self.get_rate_limit_url():
            self.rate_limited_count = 0
        return r

    def rate_limit(self):
        url = '{}/rate_limit'.format(self.api_base)
        return self.get(url)

    def repo_query(self, uri):
        url = '{}/repos/{}{}'.format(self.api_base, self.repo, uri)
        return self.get(url)

    def repo_license(self, tag):
        r = self.repo_query('/license?ref={}'.format(tag))
        if r.status_code == 200:
            # unfortunately, unlike /readme, API always returns *latest* license, ignoring tag
            # we have to double check whether the license file exists "at release tag"
            license_data = r.json()
            license_path = license_data['path']
            license_r = self.repo_query('/contents/{}?ref={}'.format(license_path, tag))
            if license_r.status_code == 200:
                return license_data
        return None

    def repo_readme(self, tag):
        r = self.repo_query('/readme?ref={}'.format(tag))
        if r.status_code == 200:
            return r.json()
        return None

    def find_in_tags_via_graphql(self, ret, pre_ok, major):
        """GraphQL allows for faster search across many tags.
        We aggregate the highest semantic version among batches of 100 records.
        In this way --major filtering results in much fewer requests compared to traditional API
        use.

        Args:
            ret (dict): currently selected release object
            pre_ok (bool): whether betas are acceptable
            major (str): the major filter

        Returns: currently selected release object

        """
        query_fmt = """
        {
          rateLimit {
            cost
            remaining
          }
          repository(owner: "%s", name: "%s") {
            tags: refs(refPrefix: "refs/tags/", first: 100, after: "%s",
              orderBy: {field: TAG_COMMIT_DATE, direction: DESC}) {
              edges {
                cursor,
                node {
                  ...refInfo
                }
              }
            }
          }
        }
        
        fragment refInfo on Ref {
          name
          target {
            sha: oid
            commitResourcePath
            __typename
            ... on Tag {
              target {
                ... on Commit {
                  ...commitInfo
                }
              }
              tagger {
                name
                email
                date
              }
            }
            ... on Commit {
              ...commitInfo
            }
          }
        }
        
        fragment commitInfo on Commit {
          zipballUrl
          tarballUrl
          author {
            name
            email
            date
          }
        }
        
        """
        cursor = ''

        while not ret:
            # testing on php/php-src
            owner, name = self.repo.split('/')
            query = query_fmt % (owner, name, cursor)
            log.info('Running query {}'.format(query))
            r = self.post('{}/graphql'.format(self.api_base), json={'query': query})
            log.info('Requested graphql with cursor "{}"'.format(cursor))
            if r.status_code != 200:
                log.info("query returned non 200 response code {}".format(r.status_code))
                return ret
            j = r.json()
            if 'errors' in j and j['errors'][0]['type'] == 'NOT_FOUND':
                raise BadProjectError(
                    'No such project found on GitHub: {}'.format(self.repo)
                )
            if not j['data']['repository']['tags']['edges']:
                log.info('No tags in GraphQL response: {}'.format(r.text))
                break
            for edge in j['data']['repository']['tags']['edges']:
                node = edge['node']
                cursor = edge['cursor']
                tag_name = node['name']
                version = self.sanitize_version(tag_name, pre_ok, major)
                if not version:
                    continue
                if 'tagger' in node['target']:
                    # use date of annotated tag as it better corresponds to "release date"
                    log.info('Using annotated tag date')
                    d = node['target']['tagger']['date']
                else:
                    # using commit date because the tag is not annotated
                    log.info('Using commit date')
                    d = node['target']['author']['date']
                tag_date = parser.parse(d)
                if ret and tag_date + timedelta(days=365) < ret['tag_date']:
                    log.info('The version {} is newer, but is too old!'.format(version))
                    break
                if not ret or version > ret['version'] or tag_date > ret['tag_date']:
                    # we always want to return formal release if it exists, cause it has useful
                    # data grab formal release via APi to check for pre-release mark
                    formal_release = self.get_formal_release_for_tag(tag_name)
                    if formal_release:
                        ret = self.set_matching_formal_release(ret, formal_release, version, pre_ok)
                    else:
                        if not self.having_asset:
                            ret = {
                                'tag_name': tag_name,
                                'tag_date': tag_date,
                                'version': version,
                                'type': 'graphql'
                            }
        return ret

    def get_formal_release_for_tag(self, tag):
        r = self.repo_query('/releases/tags/{}'.format(tag))
        if r.status_code == 200:
            # noinspection SpellCheckingInspection
            return r.json()
        return None

    # finding in tags requires paging through ALL of them, because the API does not list them
    # in order of recency, thus this is very slow
    # in: current release to be returned, output: newer release to be returned
    def find_in_tags(self, ret, pre_ok, major):
        r = self.repo_query('/tags?per_page=100')
        if r.status_code != 200:
            return None
        tags = r.json()
        while 'next' in r.links.keys():
            r = self.get(r.links['next']['url'])
            tags.extend(r.json())

        for t in tags:
            tag_name = t['name']
            version = self.sanitize_version(tag_name, pre_ok, major)
            if not version:
                continue
            c = self.repo_query('/git/commits/{}'.format(t['commit']['sha']))
            d = c.json()['committer']['date']
            d = parser.parse(d)

            if not ret or version > ret['version'] or d > ret['tag_date']:
                # rare case: if upstream filed formal pre-release that passes as stable
                # version (tag is 1.2.3 instead of 1.2.3b) double check if pre-release
                # TODO handle API failure here as it may result in "false positive"?
                release_for_tag = self.get_formal_release_for_tag(tag_name)
                if release_for_tag:
                    ret = self.set_matching_formal_release(ret, release_for_tag, version, pre_ok)
                else:
                    ret = t
                    ret['tag_name'] = tag_name
                    ret['tag_date'] = d
                    ret['version'] = version
                    ret['type'] = 'tag'
        return ret

    def get_releases_feed_contents(self, rename_checked=False):
        """
        Fetch contents of repository's releases.atom feed.
        # The releases.atom and tags.atom don't differ much except releases having more data.
        # The releases.atom feed includes non-formal releases which are just tags, so we are good.
        # Based on testing, edited old releases don't jump forward in the list and stay behind (good).
        # The only downside is they don't bear pre-release mark (unlike API), and have limited data.
        # We work around these by checking pre-release flag and get full release data via API.
        """
        r = self.get('https://{}/{}/releases.atom'.format(self.hostname, self.repo))
        # API requests are varied by cookie, we don't want serializer for cache fail because of that
        self.cookies.clear()
        if r.status_code == 404 and not rename_checked:
            # #44: in some network locations, GitHub returns 404 (as opposed to 301 redirect) for the renamed
            # repositories /releases.atom. When we get a 404, we lazily load repo info via API, and hopefully
            # get redirect there as well as the new repo full name
            r = self.repo_query('')
            if r.status_code == 200:
                repo_data = r.json()
                if self.repo != repo_data['full_name']:
                    log.info('Detected name change from {} to {}'.format(self.repo,
                                                                         repo_data['full_name']))
                    self.set_repo(repo_data['full_name'])
                    # request the feed from the new location
                    return self.get_releases_feed_contents(rename_checked=False)
        if r.status_code == 200:
            return r.text
        return None

    def get_releases_feed_entries(self):
        """Get an array of releases.atom feed entries."""
        feed_contents = self.get_releases_feed_contents()
        if not feed_contents:
            log.info('The releases.atom feed failed to be fetched!')
            return []
        feed = feedparser.parse(feed_contents)
        if 'bozo' in feed and feed['bozo'] == 1 and 'bozo_exception' in feed:
            exc = feed.bozo_exception
            log.info("Failed to parse feed: {}".format(exc.getMessage()))
            return []
        if not feed.entries:
            log.info('Feed has no elements. Empty repo???')
            return []
        return feed.entries

    def get_latest(self, pre_ok=False, major=None):
        """
        Gets latest release satisfying "prereleases are OK" or major/branch constraints
        Strives to fetch formal API release if it exists, because it has useful information
        like assets.
        """
        # data of selected tag, always contains ['version', 'tag_name', 'tag_date', 'type'] will
        # be returned
        ret = None

        # always fetch /releases as this will allow us to quickly look up if a tag is marked as
        # pre-release

        # then always get *all* tags through pagination

        # if pre not ok, filter out tags to check

        # if major, filter out tags to check for major

        # we need to check all tags commit dates simply because the most recent wins
        # we don't check tags which:
        # * marked pre-release in releases endpoints
        # * has a beta-like, non-version tag name

        feed_entries = self.get_releases_feed_entries()
        for tag in feed_entries:
            # https://github.com/apache/incubator-pagespeed-ngx/releases/tag/v1.13.35.2-stable
            tag_name = tag['link'].split('/')[-1]
            log.info('Checking tag {}'.format(tag_name))
            version = self.sanitize_version(tag_name, pre_ok, major)
            if not version:
                log.info('We did not find a valid version in {} tag'.format(tag_name))
                continue
            if ret and ret['version'] >= version:
                log.info(
                    'Tag {} does not contain newer version than we already found'.format(tag_name)
                )
                continue
            tag_date = parser.parse(tag['updated'])
            if ret and tag_date + timedelta(days=365) < ret['tag_date']:
                log.info('The version {} is newer, but is too old!'.format(version))
                break
            # we always want to return formal release if it exists, cause it has useful data
            # grab formal release via APi to check for pre-release mark
            formal_release = self.get_formal_release_for_tag(tag_name)
            if formal_release:
                # use full release info
                ret = self.set_matching_formal_release(ret, formal_release, version, pre_ok)
            else:
                if self.having_asset:
                    continue
                log.info('No formal release for tag {}'.format(tag_name))
                tag['tag_name'] = tag_name
                tag['tag_date'] = tag_date
                tag['version'] = version
                tag['type'] = 'feed'
                # remove keys which are non-jsonable
                # TODO use those (pop returns them)
                tag.pop('updated_parsed', None)
                tag.pop('published_parsed', None)
                ret = tag
                log.info("Selected version as current selection: {}.".format(version))

        # we are good with release from feeds only without looking at the API
        # simply because feeds list stuff in order of recency
        if ret:
            return ret

        # only if we did not find desired stuff through feeds, we switch to using API :)
        # this may be required in cases
        # releases.atom has limited tags, and all those are beta / invalid / non-versions
        # likewise, we want an older branch (major), which is not there in releases.atom
        # due to limited nature of data inside it

        # releases/latest fetches only non-prerelease, non-draft, so it
        # should not be used for hunting down pre-releases assets
        if not pre_ok:
            # https://stackoverflow.com/questions/28060116/which-is-more-reliable-for-github-api-conditional-requests-etag-or-last-modifie/57309763?noredirect=1#comment101114702_57309763
            # ideally we disable ETag validation for this endpoint completely
            r = self.repo_query('/releases/latest')
            if r.status_code == 200:
                formal_release = r.json()
                version = self.sanitize_version(formal_release['tag_name'], pre_ok, major)
                if version:
                    ret = self.set_matching_formal_release(ret, formal_release, version,
                                                           pre_ok, 'releases-latest')
        else:
            r = self.repo_query('/releases')
            if r.status_code == 200:
                for release in r.json():
                    tag_name = release['tag_name']
                    version = self.sanitize_version(tag_name, pre_ok, major)
                    if not version:
                        continue
                    if not ret or version > ret['version']:
                        ret = self.set_matching_formal_release(ret, release, version, pre_ok)

        if self.having_asset:
            # only formal releases which we enumerated above already, have assets
            # so there is no point looking in the tags/graphql below
            # return whatever we got
            return ret

        # formal release may not exist at all, or be "late/old" in case
        # actual release is only a simple tag so let's try /tags
        if self.api_token:
            # GraphQL requires auth
            ret = self.find_in_tags_via_graphql(ret, pre_ok, major)
        else:
            ret = self.find_in_tags(ret, pre_ok, major)

        return ret

    def set_matching_formal_release(self, ret, formal_release, version, pre_ok,
                                    data_type='release'):
        """Set current release selection to this formal release if matching conditions."""
        if not pre_ok and formal_release['prerelease']:
            log.info(
                "Found formal release for this tag which is unwanted "
                "pre-release: {}.".format(version))
            return ret
        if self.having_asset:
            if 'assets' not in formal_release or not formal_release['assets']:
                log.info('Skipping this release due to no assets.')
                return ret
            if self.having_asset is not True:
                regex_matching = False
                search = self.having_asset
                if search.startswith('~'):
                    search = r'{}'.format(search.lstrip('~'))
                    regex_matching = True
                found_asset = False
                for asset in formal_release['assets']:
                    if asset_matches(asset, search, regex_matching=regex_matching):
                        found_asset = True
                        break
                if not found_asset:
                    log.info('Desired asset not found in the release.')
                    return ret
        # formal_release['tag_name'] = tag_name
        formal_release['tag_date'] = parser.parse(formal_release['published_at'])
        formal_release['version'] = version
        formal_release['type'] = data_type
        log.info("Selected version as current selection: {}.".format(formal_release['version']))
        return formal_release

    def try_get_official(self, repo):
        """Check existence of repo/repo

        Returns:
            str: updated repo
        """
        official_repo = "{repo}/{repo}".format(repo=repo)
        log.info('Checking existence of {}'.format(official_repo))
        url = '{}/repos/{}'.format(self.api_base, official_repo)
        r = self.get(url)
        if r.status_code == 200:
            return official_repo
        return None

