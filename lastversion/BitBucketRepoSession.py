"""BitBucket repository session."""
from dateutil import parser

from .ProjectHolder import ProjectHolder


class BitBucketRepoSession(ProjectHolder):
    DEFAULT_HOSTNAME = "bitbucket.org"
    CAN_BE_SELF_HOSTED = True
    KNOWN_REPO_URLS = {
        "mmonit.com": {
            "repo": "tildeslash/monit",
            # get URL from the official website because it is a "prepared"
            # source that has the `./configure` script available
            "release_url_format": "https://mmonit.com/{name}/dist/{name}-"
            "{version}.tar.gz",
        }
    }

    KNOWN_REPOS_BY_NAME = {"monit": KNOWN_REPO_URLS["mmonit.com"]}

    def __init__(self, repo, hostname):
        super(BitBucketRepoSession, self).__init__(repo, hostname)
        self.hostname = hostname
        if not self.hostname:
            self.hostname = self.DEFAULT_HOSTNAME

    def get_latest(self, pre_ok=False, major=None):
        """Get the latest release."""
        response = self.get(
            f"https://api.bitbucket.org/2.0/repositories/{self.repo}/downloads"
        )
        data = response.json()
        release = data["values"][0]
        version = self.sanitize_version(release["name"], pre_ok, major)
        release["version"] = version
        release["tag_name"] = release["name"]
        release["tag_date"] = parser.parse(release["created_on"])
        return release
