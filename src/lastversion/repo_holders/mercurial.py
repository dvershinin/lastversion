"""Mercurial repository holder."""

from lastversion.repo_holders.base import BaseProjectHolder


class MercurialRepoSession(BaseProjectHolder):
    """Mercurial repository holder."""

    CAN_BE_SELF_HOSTED = True
    REPO_URL_PROJECT_COMPONENTS = 1

    # http://hg.nginx.org/nginx/archive/release-1.19.2.tar.gz
    RELEASE_URL_FORMAT = "https://{hostname}/{repo}/archive/{tag}.{ext}"

    # Domains hg.example.com
    SUBDOMAIN_INDICATOR = "hg"

    def __init__(self, repo, hostname):
        super().__init__(repo, hostname)
        self.hostname = hostname

    def get_latest(self, pre_ok=False, major=None):
        """
        Get the latest release.
        E.g. https://hg.nginx.org/nginx/atom-tags
        """
        return self.find_release_in_feed(f"https://{self.hostname}/{self.repo}/atom-tags", pre_ok, major)
