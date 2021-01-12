import logging
import os
import re

import requests
# this class basically corresponds to something (often a website) which holds
# projects (usually a bunch). often this is a github-like website, so we subclass session
# but this also maybe something special, which either way can be used as a source of version
# information for a project based on its URL or name (see LocalVersionSession)
# it is instantiated with a particular project in mind/set, but also has some methods for
# stuff like searching one
from .utils import asset_does_not_belong_to_machine
from .Version import Version
from packaging.version import InvalidVersion

from .__about__ import __version__

log = logging.getLogger(__name__)


class ProjectHolder(requests.Session):
    # web accessible project holders may have single well-known domain usable by everyone
    # in case of GitHub, that is github.com, for Mercurial web gui - here isn't one, etc.
    DEFAULT_HOSTNAME = None
    DEFAULT_HOLDER = False
    KNOWN_REPO_URLS = {}
    KNOWN_REPOS_BY_NAME = {}
    # e.g. owner/project, but mercurial just /project together with hostname
    # adapter array should list how many elements make up "repo", e.g. for hg.nginx.com/repo it
    # is only one instead of 2
    # or a "format" specifier for matching
    REPO_URL_PROJECT_COMPONENTS = 2
    # if URI starts with project name, 0. Otherwise skip through this many URI dirs
    REPO_URL_PROJECT_OFFSET = 0
    RELEASE_URL_FORMAT = None
    SHORT_RELEASE_URL_FORMAT = None

    def set_repo(self, repo):
        self.repo = repo
        self.name = repo.split('/')[-1]

    def __init__(self):
        super(ProjectHolder, self).__init__()
        self.headers.update({'User-Agent': 'lastversion/{}'.format(__version__)})
        log.info('Created instance of {}'.format(type(self).__name__))
        self.branches = None
        self.only = None
        self.hostname = None
        # identifies project on a given hostname
        self.repo = None
        # short name for "repo", useful in URLs
        self.name = None
        # in some case we do not specify repo, but feed is discovered, no repo is given then
        self.feed_url = None

    def is_valid(self):
        return self.feed_url or self.name

    def set_branches(self, branches):
        self.branches = branches

    def set_only(self, only):
        log.info('Only considering tags with "{}"'.format(only))
        self.only = only

    @classmethod
    def get_host_repo_for_link(cls, repo):
        hostname = None
        # return repo modified to result of extraction
        if repo.startswith(('https://', 'http://')):
            # parse hostname for passing to whatever holder selected
            url_parts = repo.split('/')
            hostname = url_parts[2]
            offset = 3 + cls.REPO_URL_PROJECT_OFFSET
            repo = "/".join(url_parts[offset:offset + cls.REPO_URL_PROJECT_COMPONENTS])
        return hostname, repo

    @classmethod
    def is_official_for_repo(cls, repo):
        if repo.startswith(('https://', 'http://')):
            for url in cls.KNOWN_REPO_URLS:
                if repo.startswith((url, "https://{}".format(url), "http://{}".format(url))):
                    log.info('{} Starts with {}'.format(repo, url))
                    return cls.KNOWN_REPO_URLS[url]
        else:
            if repo in cls.KNOWN_REPOS_BY_NAME:
                log.info('Selecting known repo {}'.format(repo))
                return cls.KNOWN_REPOS_BY_NAME[repo]
        return False

    @classmethod
    def get_matching_hostname(cls, repo):
        if not cls.DEFAULT_HOSTNAME:
            return None
        if repo.startswith('http://{}'.format(cls.DEFAULT_HOSTNAME)):
            return cls.DEFAULT_HOSTNAME
        if repo.startswith('https://{}'.format(cls.DEFAULT_HOSTNAME)):
            return cls.DEFAULT_HOSTNAME
        return None

    def matches_major_filter(self, version, major):
        if self.branches and major in self.branches:
            if re.search(r"{}".format(self.branches[major]), str(version)):
                log.info('{} matches major {}'.format(version, self.branches[major]))
                return True
        elif str(version).startswith('{}.'.format(major)):
            log.info('{} is under the desired major {}'.format(
                version, major))
            return True
        elif str(version) == major:
            return True
        return False

    def sanitize_version(self, version, pre_ok=False, major=None):
        """extract version from tag name"""
        log.info("Checking tag {} as version.".format(version))
        res = False
        try:
            v = Version(version)
            if not v.is_prerelease or pre_ok:
                log.info("Parsed as Version OK")
                log.info("String representation of version is {}.".format(v))
                res = v
            else:
                log.info("Parsed as unwanted pre-release version: {}.".format(v))
        except InvalidVersion:
            log.info("Failed to parse {} as Version.".format(version))
            # attempt to remove extraneous chars and revalidate
            # we use findall for cases where "tag" may be 'foo/2.x/2.45'
            matches = re.findall(r'([0-9]+([.][0-9x]+)+(rc[0-9]?)?)', version)
            for s in matches:
                version = s[0]
                log.info("Sanitized tag name value to {}.".format(version))
                # 1.10.x is a dev release without clear version, so even pre ok will not get it
                if not version.endswith('.x'):
                    # we know regex is valid version format, so no need to try catch
                    res = Version(version)
            if not matches:
                log.info("Did not find anything that looks like a version in the tag")
                # as a last resort, let's try to convert underscores to dots, while stripping out
                # any "alphanumeric_". many hg repos do this, e.g. PROJECT_1_2_3
                parts = version.split('_')
                if len(parts) >= 2 and parts[0].isalpha():
                    # gets list except first item, joins by dot
                    version = '.'.join(parts[1:])
                    try:
                        v = Version(version)
                        if not v.is_prerelease or pre_ok:
                            log.info("Parsed as Version OK")
                            log.info("String representation of version is {}.".format(v))
                            res = v
                        else:
                            log.info("Parsed as unwanted pre-release version: {}.".format(v))
                    except InvalidVersion:
                        log.info('Still not a valid version after applying underscores fix')
        # apply --major filter
        if res and major and not self.matches_major_filter(res, major):
            log.info('{} is not under the desired major {}'.format(
                version, major))
            res = False
        return res

    def _type(self):
        return self.__class__.__name__

    def release_download_url(self, release, shorter=False):
        if not self.RELEASE_URL_FORMAT:
            raise NotImplementedError(
                'Getting release URL for {} is not implemented'.format(self._type()))
        ext = 'zip' if os.name == 'nt' else 'tar.gz'

        fmt = self.SHORT_RELEASE_URL_FORMAT if shorter and self.SHORT_RELEASE_URL_FORMAT else \
            self.RELEASE_URL_FORMAT

        return fmt.format(
            hostname=self.hostname,
            repo=self.repo,
            name=self.name,
            tag=release['tag_name'],
            ext=ext,
            version=release['version']
        )

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
