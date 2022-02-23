import logging

from .ProjectHolder import ProjectHolder
from .utils import BadProjectError

log = logging.getLogger(__name__)


class WordPressPluginRepoSession(ProjectHolder):
    """A class to represent a WordPress plugin  project holder."""
    DEFAULT_HOSTNAME = 'wordpress.org'
    REPO_URL_PROJECT_COMPONENTS = 1
    # For project URLs, e.g. https://wordpress.org/plugins/opcache-reset/
    # a URI does not start with a repo name, skip '/plugins/'
    REPO_URL_PROJECT_OFFSET = 1

    def get_project(self):
        """Get project JSON data."""
        project = None
        url = 'https://api.{}/plugins/info/1.0/{}.json'.format(self.hostname, self.repo)
        log.info('Requesting {}'.format(url))
        r = self.get(url)
        if r.status_code == 200:
            project = r.json()
        return project

    def __init__(self, repo, hostname=None):
        super(WordPressPluginRepoSession, self).__init__()
        if hostname:
            self.hostname = hostname
        else:
            self.hostname = WordPressPluginRepoSession.DEFAULT_HOSTNAME
        self.set_repo(repo)
        self.project = self.get_project()
        if hostname and not self.project:
            raise BadProjectError(
                'The project {} does not exist in WordPress plugin directory'.format(
                    repo
                )
            )

    def release_download_url(self, release, shorter=False):
        """Get release download URL."""
        return 'https://downloads.wordpress.org/plugin/{}.{}.zip'.format(
            self.repo, release['version'])

    def get_latest(self, pre_ok=False, major=None):
        """Get latest release for this project."""
        ret = {}
        # we are in "enriching" project dict with desired version information
        # and return None if there's no matching version
        from .Version import Version
        if not major:
            latest_ver = self.project['version']
            v = Version(latest_ver)
            ret['version'] = v
            # there are no tags, we just put version string there
            ret['tag_name'] = latest_ver
        else:
            for release_ver in self.project['versions']:
                version = self.sanitize_version(release_ver, pre_ok, major)
                if not version:
                    continue
                if 'version' not in ret or version > ret['version']:
                    ret['tag_name'] = release_ver
                    ret['version'] = version
                    log.info('Set current selection to {}'.format(version))
                else:
                    log.info('Not set {}'.format(str(version)))
        if 'tag_name' in ret:
            self.project.update(ret)
            return self.project
        return None

    @staticmethod
    def make_canonical_link(repo):
        """Make canonical link from repo."""
        return 'https://{}/plugins/{}/'.format(WordPressPluginRepoSession.DEFAULT_HOSTNAME, repo)

    def get_canonical_link(self):
        """Get canonical link from repo."""
        return 'https://{}/plugins/{}/'.format(self.hostname, self.repo)
