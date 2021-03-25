import datetime

import feedparser

from .ProjectHolder import ProjectHolder


class SourceForgeRepoSession(ProjectHolder):
    """SourceForce project holder."""

    REPO_URL_PROJECT_COMPONENTS = 1
    DEFAULT_HOSTNAME = 'sourceforge.net'
    # For project URLs, e.g. https://sourceforge.net/projects/keepass/
    # a URI does not start with a repo name, skip '/projects/'
    REPO_URL_PROJECT_OFFSET = 1

    def __init__(self, repo, hostname):
        super(SourceForgeRepoSession, self).__init__()
        self.hostname = hostname
        self.set_repo(repo)

    def get_latest(self, pre_ok=False, major=None):
        ret = None
        # to leverage cachecontrol, we fetch the feed using requests as usual
        # then feed the feed to feedparser as a raw string
        # e.g. https://sourceforge.net/projects/keepass/rss?path=/
        # TODO this could be better. Now it is actually checking versions in topmost files
        r = self.get('https://{}/projects/{}/rss?path=/'.format(self.hostname, self.repo))
        feed = feedparser.parse(r.text)
        for tag in feed.entries:
            tag_name = tag['title']
            version = self.sanitize_version(tag_name, pre_ok, major)
            if not version:
                continue
            if not ret or version > ret['version']:
                ret = tag
                tag['tag_name'] = tag['title']
                tag['version'] = version
                # converting from struct
                tag['tag_date'] = datetime.datetime(*tag['published_parsed'][:6])
        return ret
