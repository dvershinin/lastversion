# special case, private use now
# nginx version is taken as version of stable (written by rpm check script)
# to /usr/local/share/builder/nginx-stable.ver
import logging

from lastversion.repo_holders.base import BaseProjectHolder

log = logging.getLogger(__name__)


class LocalVersionSession(BaseProjectHolder):
    DEFAULT_HOSTNAME = None

    def __init__(self, repo, hostname):
        super().__init__(repo, hostname)
        self.hostname = hostname

    def get_latest(self, pre_ok=False, major=None):
        """Get the latest release."""
        if pre_ok:
            log.info("--pre is not supported for local version sources")
        if not major:
            major = "stable"
        ver_file = f"/usr/local/share/builder/{self.repo}-{major}.ver"
        with open(ver_file, "r") as f:
            version = f.read().replace("\n", "")
            return {"version": version, "tag_name": version}
