from .ProjectHolder import ProjectHolder
import logging
import yaml
from six.moves.urllib.parse import urlparse

log = logging.getLogger(__name__)


class HelmChartRepoSession(ProjectHolder):

    def __init__(self, repo, hostname=None):
        super(HelmChartRepoSession, self).__init__()
        if not repo.endswith('Chart.yaml'):
            repo = repo.rstrip('/') + '/Chart.yaml'
        log.info('Helm Chart.yml: {}'.format(repo))
        self.url = repo

    def get_latest(self, pre_ok=False, major=None):
        # https://github.com/bitnami/charts/blob/master/bitnami/aspnet-core/Chart.yaml
        # https://raw.githubusercontent.com/bitnami/charts/master/bitnami/aspnet-core/Chart.yaml
        url = self.url
        host = urlparse(url).hostname
        if host in ['github.com']:
            url = url.replace('github.com', 'raw.githubusercontent.com').replace('/blob/', '/')
        r = self.get(url)
        chart_data = yaml.safe_load(r.text)
        return {
            'tag_name': None,
            'tag_date': None,
            'version': self.sanitize_version(chart_data['version'], pre_ok, major),
            'type': 'helm'
        }
