"""Mercurial repository holder."""
from lastversion.repo_holders.base import BaseProjectHolder


class MercurialRepoSession(BaseProjectHolder):
    CAN_BE_SELF_HOSTED = True
    REPO_URL_PROJECT_COMPONENTS = 1
    KNOWN_REPO_URLS = {
        "nginx.org": {
            "repo": "nginx",
            "hostname": "hg.nginx.org",
            "branches": {
                "stable": "\\.\\d?[02468]\\.",
                "mainline": "\\.\\d?[13579]\\.",
            },
            # get URL from website instead of hg. because it is "prepared" source
            "release_url_format": "https://nginx.org/download/{name}-{version}.{ext}",
        }
    }

    KNOWN_REPOS_BY_NAME = {"nginx": KNOWN_REPO_URLS["nginx.org"]}

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
        return self.find_release_in_feed(
            f"https://{self.hostname}/{self.repo}/atom-tags", pre_ok, major
        )
