import logging
from urllib.parse import urlparse
from collections import OrderedDict
from .BitBucketRepoSession import BitBucketRepoSession
from .FeedRepoSession import FeedRepoSession
from .GitHubRepoSession import GitHubRepoSession
from .GitLabRepoSession import GitLabRepoSession
from .GiteaRepoSession import GiteaRepoSession
from .HelmChartRepoSession import HelmChartRepoSession
from .LocalVersionSession import LocalVersionSession
from .MercurialRepoSession import MercurialRepoSession
from .PypiRepoSession import PypiRepoSession
from .SourceForgeRepoSession import SourceForgeRepoSession
from .SystemRepoSession import SystemRepoSession
from .WikipediaRepoSession import WikipediaRepoSession
from .WordPressPluginRepoSession import WordPressPluginRepoSession
from .exceptions import BadProjectError

log = logging.getLogger(__name__)


class HolderFactory:
    # Holders are order in a way that the ones that can be matched by domain and can't be self-hosted go first
    # With the last ones being dynamic (feed lookup, etc.)
    HOLDERS = OrderedDict(
        {
            # non self-hosted
            "wp": WordPressPluginRepoSession,
            "sf": SourceForgeRepoSession,
            "wiki": WikipediaRepoSession,
            "helm_chart": HelmChartRepoSession,
            # self-hosted possible but primary domain exists (or subdomain marker)
            "github": GitHubRepoSession,
            "gitlab": GitLabRepoSession,
            "bitbucket": BitBucketRepoSession,
            "pip": PypiRepoSession,
            "hg": MercurialRepoSession,
            "gitea": GiteaRepoSession,
            # misc
            "website-feed": FeedRepoSession,
            "local": LocalVersionSession,
            "system": SystemRepoSession,
        }
    )

    DEFAULT_HOLDER = "github"

    @staticmethod
    def guess_from_homepage(repo, hostname):
        """
        Try to guess the right holder for a given repo and domain.
        Args:
            repo:
            hostname:

        Returns:

        """
        # repo auto-discovery failed for detected/default provider
        # now we simply try website provider based on the hostname/RSS feeds
        # in HTML or GitHub links
        holder = FeedRepoSession(repo, hostname)
        if holder.is_instance():
            return holder

        # re-use soup from the feed holder object
        log.info("Have not found any RSS feed for the website %s", hostname)
        github_link = holder.home_soup.select_one("a[href*='github.com']")
        if github_link:
            hostname, repo = GitHubRepoSession.get_host_repo_for_link(
                github_link["href"]
            )
            # log that we found GitHub link on the website
            log.info("Found GitHub link on the website %s: %s", hostname, repo)
            return GitHubRepoSession(repo, hostname)

        return None

    @staticmethod
    def create_holder_from_known_repo(known_repo, project_hosting_class):
        """Create a holder from a known repo."""
        repo = known_repo["repo"]
        # Known repo tells us hosted domain of e.g., mercurial web
        hostname = known_repo.get("hostname")
        holder = project_hosting_class(repo, hostname)
        if "branches" in known_repo:
            holder.set_branches(known_repo["branches"])

        if "only" in known_repo:
            holder.set_only(known_repo["only"])

        if "release_url_format" in known_repo:
            holder.RELEASE_URL_FORMAT = known_repo["release_url_format"]
        return holder

    @staticmethod
    def try_match_with_holder_class(
        project_hosting_name, project_hosting_class, repo, hostname
    ):
        # only try if there is hostname
        if not hostname:
            return None
        if not project_hosting_class.CAN_BE_SELF_HOSTED:
            # nothing to sniff
            return None
        log.info("Trying to sniff %s adapter", project_hosting_name)

        try:
            sc_repo = project_hosting_class.get_base_repo_from_repo_arg(repo)
            h = project_hosting_class(sc_repo, hostname)
            if h.is_instance():
                return h
        except ValueError as e:
            log.debug("Could not get base repo from %s: %s", repo, e)

        return None

    @staticmethod
    # go through subclasses in order to find the one that is holding a given project
    # repo is either complete URL or a name allowing to identify a single project
    def get_instance_for_repo(repo, at=None):
        """Find the right hosting for this repo."""
        hostname = None
        # if repo is a link, get the hostname by parsing as URL
        if repo.startswith(("http:", "https:")):
            parsed = urlparse(repo)
            hostname = parsed.hostname
            repo = parsed.path.lstrip("/")
            if not repo:
                repo = None
        # when we were explicit about the hosting, we don't try to guess
        if at:
            return HolderFactory.HOLDERS[at](repo, hostname=hostname)

        holder = None

        # match by default domains and known host first as this allows to skip sniffing tests
        for (
            project_hosting_name,
            project_hosting_class,
        ) in HolderFactory.HOLDERS.items():
            # TODO now easy multiple default hostnames per holder
            if project_hosting_class.is_matching_hostname(hostname):
                return project_hosting_class(repo, hostname)
            known_repo = project_hosting_class.is_official_for_repo(repo, hostname)
            if known_repo:
                return HolderFactory.create_holder_from_known_repo(
                    known_repo, project_hosting_class
                )

        for (
            project_hosting_name,
            project_hosting_class,
        ) in HolderFactory.HOLDERS.items():
            holder = HolderFactory.try_match_with_holder_class(
                project_hosting_name, project_hosting_class, repo, hostname
            )
            if holder:
                return holder

        # It no holder is found, we try to guess from the homepage
        if hostname:
            holder = HolderFactory.guess_from_homepage(repo, hostname)
            if holder:
                return holder

        if not holder and hostname:
            raise BadProjectError(
                f"Could not find a holder for the {repo} at {hostname}"
            )

        if not holder and not hostname:
            return GitHubRepoSession(repo)

        raise BadProjectError(f"Could not find a holder for the repo {repo}")
