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
        holder_class = HolderFactory.HOLDERS['github']
        hostname = None
        known_repo = None
        for k, sc in HolderFactory.HOLDERS.items():
            known_repo = sc.is_official_for_repo(repo)
            if known_repo:
                holder_class = sc
                log.info('Using {} adapter'.format(k))
                break
            # TODO now easy multiple default hostnames per holder
            hostname = sc.get_matching_hostname(repo)
            if hostname:
                holder_class = sc
                break
        if known_repo:
            repo = known_repo['repo']
            # known repo tells us hosted domain of e.g. mercurical web
            if 'hostname' in known_repo:
                hostname = known_repo['hostname']
        elif repo.startswith(('https://', 'http://')):
            # parse hostname for passing to whatever holder selected
            url_parts = repo.split('/')
            hostname = url_parts[2]
            repo = "/".join(url_parts[3:3 + holder_class.REPO_URL_PROJECT_COMPONENTS])
        holder = holder_class(repo, hostname)
        if known_repo and 'branches' in known_repo:
            holder.set_branches(known_repo['branches'])
        return holder
