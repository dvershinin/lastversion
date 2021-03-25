# special case, private use now
# nginx version is taken as version of stable (written by rpm check script)
# to /usr/local/share/builder/nginx-stable.ver
import logging

from .ProjectHolder import ProjectHolder

log = logging.getLogger(__name__)


class LocalVersionSession(ProjectHolder):
    DEFAULT_HOSTNAME = None

    def __init__(self, repo, hostname):
        super(LocalVersionSession, self).__init__()
        self.set_repo(repo)
        self.hostname = hostname

    def get_latest(self, pre_ok=False, major=None):
        if pre_ok:
            log.info('--pre is not supported for local version sources')
        if not major:
            major = 'stable'
        ver_file = '/usr/local/share/builder/{}-{}.ver'.format(self.repo, major)
        with open(ver_file, 'r') as file:
            version = file.read().replace('\n', '')
            return {
                'version': version,
                'tag_name': version
            }
