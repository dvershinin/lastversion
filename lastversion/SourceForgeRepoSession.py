import datetime
from urllib.parse import urlunparse, urlparse

import feedparser

from .ProjectHolder import ProjectHolder


class SourceForgeRepoSession(ProjectHolder):
    """SourceForce project holder."""

    REPO_URL_PROJECT_COMPONENTS = 1
    DEFAULT_HOSTNAME = "sourceforge.net"
    # For project URLs, e.g. https://sourceforge.net/projects/keepass/
    # a URI does not start with a repo name, skip '/projects/'
    REPO_URL_PROJECT_OFFSET = 1

    def __init__(self, repo, hostname):
        super(SourceForgeRepoSession, self).__init__(repo, hostname)
        self.hostname = hostname

    @staticmethod
    def get_normalized_url(download_url):
        """Get normalized URL for a download URL, without /download suffix."""
        parsed_url = urlparse(download_url)

        if (
            parsed_url.netloc == "sourceforge.net"
            and "projects" in parsed_url.path
            and "files" in parsed_url.path
        ):
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
        """Get the latest release."""
        ret = None
        # to leverage cachecontrol, we fetch the feed using requests as usual
        # then feed the feed to feedparser as a raw string
        # e.g. https://sourceforge.net/projects/keepass/rss?path=/
        # TODO this could be better. Now it is actually checking versions in topmost files
        r = self.get(
            "https://{}/projects/{}/rss?path=/".format(self.hostname, self.repo)
        )
        feed = feedparser.parse(r.text)
        for tag in feed.entries:
            tag_name = tag["title"]
            version = self.sanitize_version(tag_name, pre_ok, major)
            if not version:
                continue
            if not ret or version > ret["version"]:
                ret = tag
                tag["tag_name"] = tag["title"]
                tag["version"] = version
                # converting from struct
                tag["tag_date"] = datetime.datetime(*tag["published_parsed"][:6])
        return ret

    def release_download_url(self, release, shorter=False):
        """Get download URL for a release."""
        return self.get_normalized_url(release["link"])
