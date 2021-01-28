import logging

from dateutil import parser

from .ProjectHolder import ProjectHolder
from .utils import BadProjectError

log = logging.getLogger(__name__)


class PypiRepoSession(ProjectHolder):
    """
    A class to represent a Pypi project holder.
    """
    DEFAULT_HOSTNAME = 'pypi.org'
    REPO_URL_PROJECT_COMPONENTS = 1
    # For project URLs, e.g. https://pypi.org/project/lastversion/
    # a URI does not start with a repo name, skip '/project/'
    REPO_URL_PROJECT_OFFSET = 1

    def get_project(self):
        project = None
        url = 'https://{}/pypi/{}/json'.format(self.hostname, self.repo)
        log.info('Requesting {}'.format(url))
        r = self.get(url)
        if r.status_code == 200:
            project = r.json()
        return project

    def __init__(self, repo, hostname=None):
        super(PypiRepoSession, self).__init__()
        if hostname:
            self.hostname = hostname
        else:
            self.hostname = PypiRepoSession.DEFAULT_HOSTNAME
        self.set_repo(repo)
        self.project = self.get_project()
        if hostname and not self.project:
            raise BadProjectError(
                'The project {} does not exist on Pypi'.format(
                    repo
                )
            )

    def release_download_url(self, release, shorter=False):
        """Get release download URL."""
        for f in release['files']:
            if f['packagetype'] == 'sdist':
                return f['url']
        return None

    def get_latest(self, pre_ok=False, major=None):
        ret = self.project
        # we are in "enriching" project dict with desired version information
        # and return None if there's no matching version
        from .Version import Version
        if not major:
            latest_ver = self.project['info']['version']
            v = Version(latest_ver)
            ret['version'] = v
            # there are no tags, we just put version string there
            ret['tag_name'] = latest_ver
        else:
            for release_ver in self.project['releases']:
                version = self.sanitize_version(release_ver, pre_ok, major)
                if not version:
                    continue
                if 'version' not in ret or version > ret['version']:
                    ret['tag_name'] = release_ver
                    ret['version'] = version
        if 'tag_name' in ret:
            # consider tag_date as upload time of the selected release first file
            ret['files'] = self.project['releases'][ret['tag_name']]
            ret['tag_date'] = parser.parse(ret['files'][0]['upload_time'])
            return ret
        return None

    @staticmethod
    def make_canonical_link(repo):
        return 'https://{}/project/{}/'.format(PypiRepoSession.DEFAULT_HOSTNAME, repo)

    def get_canonical_link(self):
        return 'https://{}/project/{}/'.format(self.hostname, self.repo)
