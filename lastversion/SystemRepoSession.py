from .ProjectHolder import ProjectHolder
import logging


log = logging.getLogger(__name__)


class SystemRepoSession(ProjectHolder):

    def __init__(self, repo, hostname=None):
        self.set_repo(repo)

    def get_latest(self, pre_ok=False, major=None):
        from .utils import system_get_available_version
        version = system_get_available_version(self.repo)
        return version