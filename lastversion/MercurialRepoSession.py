import feedparser
import datetime

from .ProjectHolder import ProjectHolder


class MercurialRepoSession(ProjectHolder):
    REPO_URL_PROJECT_COMPONENTS = 1
    KNOWN_REPO_URLS = {
        'nginx.org': {
            'repo': 'nginx',
            'hostname': 'hg.nginx.org',
            'branches': {
                'stable': '\\.\\d?[02468]\\.',
                'mainline': '\\.\\d?[13579]\\.'
            }
        }
    }

    @classmethod
    def matches_default_hostnames(cls, hostname):
        return hostname.startswith('hg.')

    def __init__(self, repo, hostname):
        super(MercurialRepoSession, self).__init__()
        self.hostname = hostname
        self.repo = repo

    def get_latest(self, pre_ok=False, major=None):
        ret = None
        # to leverage cachecontrol, we fetch the feed using requests as usual
        # then feed the feed to feedparser as a raw string
        # e.g. https://hg.nginx.org/nginx/atom-tags
        # https://pythonhosted.org/feedparser/common-atom-elements.html
        r = self.get('https://{}/{}/atom-tags'.format(self.hostname, self.repo))
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
