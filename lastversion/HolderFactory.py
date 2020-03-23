import logging as log  # for verbose output
from .BitBucketRepoSession import BitBucketRepoSession
from .GitHubRepoSession import GitHubRepoSession
from .GitLabRepoSession import GitLabRepoSession
from .LocalVersionSession import LocalVersionSession
from .MercurialRepoSession import MercurialRepoSession


class HolderFactory:
    HOLDERS = {
        'github': GitHubRepoSession,
        'gitlab': GitLabRepoSession,
        'bitbucket': BitBucketRepoSession,
        'hg': MercurialRepoSession,
        'local': LocalVersionSession
    }

    @staticmethod
    # go through subclasses in order to find the one that is hodling a given project
    # repo is either complete URL or a name allowing to identify a single project
    def get_instance_for_repo(repo):
        holder_class = None
        hostname = None
        known_repo = None
        if repo.startswith(('https://', 'http://')):
            url_parts = repo.split('/')
            hostname = url_parts[2]
            for k, sc in HolderFactory.HOLDERS.items():
                if len(url_parts) >= (3 + sc.REPO_URL_PROJECT_COMPONENTS):
                    repo = "/".join(url_parts[3:3 + sc.REPO_URL_PROJECT_COMPONENTS])
                known_repo = sc.is_with_url(repo)
                if known_repo:
                    holder_class = sc
                    log.info('Using {} adapter'.format(k))
                    break
                if sc.matches_default_hostnames(hostname):
                    holder_class = sc
                    break
        if not holder_class:
            # the default:
            holder_class = HolderFactory.HOLDERS['github']
        if known_repo:
            repo = known_repo['repo']
            # known repo tells us hosted domain of e.g. mercurical web
            if 'hostname' in known_repo:
                hostname = known_repo['hostname']
        holder = holder_class(repo, hostname)
        if known_repo and 'branches' in known_repo:
            holder.set_branches(known_repo['branches'])
        return holder
