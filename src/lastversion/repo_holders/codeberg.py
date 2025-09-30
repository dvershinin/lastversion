"""Codeberg repository session class (Codeberg is a Gitea instance)."""

from lastversion.repo_holders.gitea import GiteaRepoSession


class CodebergRepoSession(GiteaRepoSession):
    """A class to represent a Codeberg project holder.
    
    Codeberg.org is a well-known Gitea instance, so we inherit from GiteaRepoSession
    and just override the default hostname.
    """

    DEFAULT_HOSTNAME = "codeberg.org"
    # Codeberg is the only known instance for this class
    KNOWN_GITEA_HOSTS = []

    @classmethod
    def is_matching_hostname(cls, hostname):
        """Check if given hostname matches to Codeberg hosting domain."""
        if not hostname:
            return None
        # Only match codeberg.org
        if cls.DEFAULT_HOSTNAME == hostname:
            return True
        return False
