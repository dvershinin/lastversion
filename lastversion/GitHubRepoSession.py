import logging as log  # for verbose output
import os
import re

import feedparser
from dateutil import parser

from .ProjectHolder import ProjectHolder
from .utils import asset_does_not_belong_to_machine, ApiCredentialsError


class GitHubRepoSession(ProjectHolder):
    DEFAULT_HOSTNAME = 'github.com'
    DEFAULT_HOLDER = True

    def __init__(self, repo, hostname):
        super(GitHubRepoSession, self).__init__()
        self.api_token = os.getenv("GITHUB_API_TOKEN")
        self.hostname = hostname
        if not self.hostname:
            self.hostname = self.DEFAULT_HOSTNAME
        # Explicitly specify API version we want:
        # headers['Accept'] = "application/vnd.github.v3+json"
        if self.api_token:
            log.info('Using API token.')
            self.headers.update({'Authorization': "token {}".format(self.api_token)})
        if self.hostname != self.DEFAULT_HOSTNAME:
            self.api_base = 'https://{}/api/v3'.format(self.hostname)
        else:
            self.api_base = 'https://api.{}'.format(self.DEFAULT_HOSTNAME)
        if '/' not in repo:
            r = self.get(
                '{}/search/repositories?q={}+in:name'.format(self.api_base, repo))
            self.repo = r.json()['items'][0]['full_name']
        else:
            self.repo = repo
        self.rate_limited_wait_so_far = 0

    def get_rate_limit_url(self):
        return '{}/rate_limit'.format(self.api_base)

    def get(self, url, **kwargs):
        r = super(GitHubRepoSession, self).get(url, **kwargs)
        if r.status_code == 401:
            if self.api_token:
                raise ApiCredentialsError('API request was denied despite using an API token. '
                                          'Missing scopes?')
            raise ApiCredentialsError('Denied API access. Please set GITHUB_API_TOKEN env var '
                                      'as per https://github.com/dvershinin/lastversion#tips')
        if r.status_code == 403:
            if self.rate_limited_wait_so_far > 3600:
                raise ApiCredentialsError(
                    'Exceeded API rate limit after waiting: {}'.format(
                        r.json()['message'])
                )
            # get rate limit info
            r_limit = self.rate_limit().json()
            import time
            wait_for = r_limit['resources']['core']['reset'] - time.time()
            if wait_for < 0:
                wait_for = 10
            log.warning('Waiting for {} seconds to regain API quota...'.format(wait_for))
            time.sleep(wait_for)
            self.rate_limited_wait_so_far = self.rate_limited_wait_so_far + wait_for
            # try again
            return self.get(url)

        if r.status_code == 200 and url != self.get_rate_limit_url():
            self.rate_limited_wait_so_far = 0
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
            return r.json()
        return None

    def repo_readme(self, tag):
        r = self.repo_query('/readme?ref={}'.format(tag))
        if r.status_code == 200:
            return r.json()
        return None

    def get_latest(self, pre_ok=False, major=None):
        """
        Gets latest release satisfying "prereleases are OK" or major/branch constraints
        Strives to fetch formal API release if it exists, because it has useful information
        like assets
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

        # releases.atom and tags.atom don't differ much except releases having more data
        # yes, releases.atom include non-formal releases which are just tags, so we are good
        # based on testing, edited old releases don't jump forward and stay behind so they are great
        # the only downside is they don't bear pre-release mark (unlike API), and limited data
        # we work around both so we are fine to to use them for speed!
        r = self.get('https://{}/{}/releases.atom'.format(self.hostname, self.repo))
        feed = feedparser.parse(r.text)
        # TODO choose topmost (most recent), but do a doble check whether the edit was released (
        #  tag api)
        for tag in feed.entries:
            # https://github.com/apache/incubator-pagespeed-ngx/releases/tag/v1.13.35.2-stable
            tag_name = tag['link'].split('/')[-1]
            version = self.sanitize_version(tag_name, pre_ok, major)
            if version:
                # we always want to return formal release if it exists, cause it has useful data
                # grab formal release via APi to check for pre-release mark
                r = self.repo_query('/releases/tags/{}'.format(tag_name))
                if r.status_code == 200:
                    formal_release = r.json()
                    if not pre_ok and formal_release['prerelease']:
                        log.info(
                            "Found formal release for this tag which is unwanted "
                            "pre-release: {}.".format(version))
                        continue
                    # use full release info
                    ret = formal_release
                    ret['tag_name'] = tag_name
                    ret['tag_date'] = parser.parse(tag['updated'])
                    ret['version'] = version
                    ret['type'] = 'feed'
                else:
                    ret = tag
                    ret['tag_name'] = tag_name
                    ret['tag_date'] = parser.parse(tag['updated'])
                    ret['version'] = version
                    ret['type'] = 'feed'
                    # remove keys which are non-jsonable
                    # TODO use those (pop returns them)
                    ret.pop('updated_parsed', None)
                    ret.pop('published_parsed', None)
                log.info("Selected version as current selection: {}.".format(version))
                break
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
                tag_name = r.json()['tag_name']
                version = self.sanitize_version(tag_name, pre_ok, major)
                if version:
                    log.info("Selected version as current selection: {}.".format(version))
                    ret = r.json()
                    ret['tag_name'] = tag_name
                    ret['tag_date'] = parser.parse(r.json()['published_at'])
                    ret['version'] = version
                    ret['type'] = 'releases-latest'
        else:
            r = self.repo_query('/releases')
            if r.status_code == 200:
                for release in r.json():
                    tag_name = release['tag_name']
                    version = self.sanitize_version(tag_name, pre_ok, major)
                    if not version:
                        continue
                    if not ret or version > ret['version']:
                        log.info("Selected version as current selection: {}.".format(version))
                        ret = release
                        ret['tag_name'] = tag_name
                        ret['tag_date'] = parser.parse(release['published_at'])
                        ret['version'] = version
                        ret['type'] = 'release'

        # formal release may not exist at all, or be "late/old" in case
        # actual release is only a simple tag so let's try /tags
        r = self.repo_query('/tags?per_page=100')
        if r.status_code == 200:
            for t in r.json():
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
                    release_for_tag = None
                    if not pre_ok:
                        r = self.repo_query('/releases/tags/{}'.format(tag_name))
                        if r.status_code == 200:
                            # noinspection SpellCheckingInspection
                            if r.json()['prerelease']:
                                log.info(
                                    "Found formal release for this tag which is unwanted "
                                    "pre-release: {}.".format(version))
                                continue
                            else:
                                release_for_tag = r.json()

                    log.info("Setting version as current selection: {}.".format(version))
                    if release_for_tag:
                        ret = release_for_tag
                        ret['tag_name'] = tag_name
                        ret['tag_date'] = parser.parse(release_for_tag['published_at'])
                        ret['version'] = version
                        ret['type'] = 'release'
                    else:
                        ret = t
                        ret['tag_name'] = tag_name
                        ret['tag_date'] = d
                        ret['version'] = version
                        ret['type'] = 'tag'

        return ret

    def release_download_url(self, release, shorter=False):
        """ The following format will benefit from:
        1) not using API, so is not subject to its rate limits
        2) likely has been accessed by someone in CDN and thus faster
        3) provides more or less unique filenames once the stuff is downloaded
        See https://fedoraproject.org/wiki/Packaging:SourceURL#Git_Tags
        We use variation of this: it does not need a parsed version (thus works for --pre better)
        and it is not broken on fancy release tags like v1.2.3-stable
        https://github.com/OWNER/PROJECT/archive/%{gittag}/%{gittag}-%{version}.tar.gz
        """
        ext = 'zip' if os.name == 'nt' else 'tar.gz'
        tag = release['tag_name']
        url_format = 'https://{}/{}/archive/{}/{}-{}.{}'
        if shorter:
            url_format = 'https://{}/{}/archive/{}.{}'
            return url_format.format(self.hostname, self.repo, tag, ext)
        return url_format.format(self.hostname, self.repo, tag, self.repo.split('/')[1], tag, ext)

    def get_assets(self, release, short_urls, assets_filter=None):
        urls = []
        if 'assets' in release and release['assets']:
            for asset in release['assets']:
                if assets_filter:
                    if not re.search(assets_filter, asset['name']):
                        continue
                else:
                    if asset_does_not_belong_to_machine(asset['name']):
                        continue
                urls.append(asset['browser_download_url'])
        else:
            download_url = self.release_download_url(release, short_urls)
            if not assets_filter or re.search(assets_filter, download_url):
                urls.append(download_url)
        return urls
