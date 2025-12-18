"""Test SourceForge repository."""

from urllib.parse import urlparse, urlunparse

from lastversion.repo_holders.base import BaseProjectHolder


class SourceForgeRepoSession(BaseProjectHolder):
    """SourceForce project holder."""

    REPO_URL_PROJECT_COMPONENTS = 1
    DEFAULT_HOSTNAME = "sourceforge.net"
    # For project URLs, e.g. https://sourceforge.net/projects/keepass/
    # a URI does not start with a repo name, skip '/projects/'
    REPO_URL_PROJECT_OFFSET = 1

    def __init__(self, repo, hostname):
        super().__init__(repo, hostname)
        self.hostname = hostname

    @staticmethod
    def get_normalized_url(download_url):
        """Get normalized URL for a download URL, without /download suffix."""
        parsed_url = urlparse(download_url)

        if parsed_url.netloc == "sourceforge.net" and "projects" in parsed_url.path and "files" in parsed_url.path:
            path_parts = parsed_url.path.strip("/").split("/")
            project_name = path_parts[1]
            file_name = path_parts[3]

            new_scheme = "https"
            new_netloc = "downloads.sourceforge.net"
            new_path = f"/{project_name}/{file_name}"

            transformed_url = urlunparse((new_scheme, new_netloc, new_path, "", "", ""))
            return transformed_url

        return None

    def get_latest(self, pre_ok=False, major=None):
        """
        Get the latest release.
        E.g. https://sourceforge.net/projects/keepass/rss?path=/
        """
        return self.find_release_in_feed(f"https://{self.hostname}/projects/{self.repo}/rss?path=/", pre_ok, major)

    def release_download_url(self, release, shorter=False):
        """Get download URL for a release."""
        return self.get_normalized_url(release["link"])
