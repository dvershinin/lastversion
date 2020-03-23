import logging as log
import re

import requests

# this class basically corresponds to something (often a website) which holds
# projects (usually a bunch). often this is a github-like website, so we subclass session
# but this also maybe something special, which either way can be used as a source of version
# information for a project based on its URL or name (see LocalVersionSession)
# it is instantantiated with a particular project in mind/set, but also has some methods for
# stuff like searching one
from packaging.version import InvalidVersion, Version


class ProjectHolder(requests.Session):
    # web accessible project holders may have single well-known domain usable by everyone
    # in case of GitHub, that is github.com, for Mercurial web gui - here isn't one, etc.
    DEFAULT_HOSTNAME = None
    DEFAULT_HOLDER = False
    KNOWN_REPO_URLS = {}
    # e.g. owner/project, but mercurial just /project together with hostname
    # adapter array should list how many elements make up "repo", e.g. for hg.nginx.com/repo it
    # is only one instead of 2
    # or a "format" specifier for matching
    REPO_URL_PROJECT_COMPONENTS = 2

    def __init__(self):
        super(ProjectHolder, self).__init__()
        log.info('Using {} project holder'.format(type(self).__name__))
        self.branches = None

    def set_branches(self, branches):
        self.branches = branches

    @classmethod
    def is_with_url(cls, repo):
        for url in cls.KNOWN_REPO_URLS:
            if repo.startswith((url, "https://{}".format(url), "http://{}".format(url))):
                log.info('{} Starts with {}'.format(repo, url))
                return cls.KNOWN_REPO_URLS[url]
        return False

    @classmethod
    def matches_default_hostnames(cls, hostname):
        return hostname == cls.DEFAULT_HOSTNAME

    def matches_major_filter(self, version, major):
        if self.branches and major in self.branches:
            if re.search(r"{}".format(self.branches[major]), version):
                log.info('{} matches major {}'.format(version, self.branches[major]))
                return True
        elif '{}.'.format(major) in version:
            log.info('{} is not under the desired major {}'.format(
                version, major))
            return True
        return False

    def sanitize_version(self, version, pre_ok=False, major=None):
        """extract version from tag name"""
        log.info("Checking tag {} as version.".format(version))
        if major and not self.matches_major_filter(version, major):
            log.info('{} is not under the desired major {}'.format(
                version, major))
            return False
        # many times they would tag foo-1.2.3 which would parse to LegacyVersion
        # we can avoid this, by reassigning to what comes after the dash:
        parts = version.split('-', 1)
        if len(parts) == 2 and parts[0].isalpha():
            version = parts[1]
        # help devel releases to be correctly identified
        # https://www.python.org/dev/peps/pep-0440/#developmental-releases
        version = re.sub('-devel$', '.dev0', version)
        # release-3_0_2 is often seen on Mercurial holders
        # note that above code removes "release-" already so we are left with "3_0_2"
        if re.search(r'^(?:\d+_)+(?:\d+)', version):
            version = version.replace('_', '.')
        try:
            v = Version(version)
            if not v.is_prerelease or pre_ok:
                log.info("Parsed as Version OK")
                log.info("String representation of version is {}.".format(v))
                return v
            log.info("Parsed as unwanted pre-release version: {}.".format(v))
            return False
        except InvalidVersion:
            log.info("Failed to parse {} as Version.".format(version))
            # attempt to remove extraneous chars and revalidate
            s = re.search(r'([0-9]+([.][0-9x]+)+(rc[0-9]?)?)', version)
            if s:
                version = s.group(1)
                log.info("Sanitized tag name value to {}.".format(version))
                if version.endswith('.x'):
                    # 1.10.x is a dev release without clear version, so even pre ok will not get it
                    return False
                # we know regex is valid version format, so no need to try catch
                return Version(version)
            log.info("Did not find anything that looks like a version in the tag")
            return False
