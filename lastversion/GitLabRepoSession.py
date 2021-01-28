import logging
import os

from dateutil import parser

from .ProjectHolder import ProjectHolder

log = logging.getLogger(__name__)


class GitLabRepoSession(ProjectHolder):
    DEFAULT_HOSTNAME = 'gitlab.com'

    def __init__(self, repo, hostname):
        super(GitLabRepoSession, self).__init__()
        self.pa_token = os.getenv("GITLAB_PA_TOKEN")
        self.hostname = hostname
        if not self.hostname:
            self.hostname = self.DEFAULT_HOSTNAME
        if self.pa_token:
            log.info('Using Personal Access token.')
            self.headers.update({'Private-Token': "{}".format(self.pa_token)})
        self.api_base = 'https://{}/api/v4'.format(self.hostname)
        self.set_repo(repo)
        self.repo_id = self.repo.replace('/', '%2F')

    def repo_query(self, uri):
        url = '{}/projects/{}/repository{}'.format(self.api_base, self.repo_id, uri)
        return self.get(url)

    def get_latest(self, pre_ok=False, major=None):
        ret = None

        # gitlab returns tags by updated in desc order, this is just what we want :)
        r = self.repo_query('/tags')
        if r.status_code == 200:
            for t in r.json():
                tag = t['name']
                version = self.sanitize_version(tag, pre_ok, major)
                if not version:
                    continue
                if not ret or ret and version > ret['version']:
                    log.info("Setting version as current selection: {}.".format(version))
                    ret = t
                    ret['tag_name'] = tag
                    ret['tag_date'] = parser.parse(t['commit']['created_at'])
                    ret['version'] = version
                    ret['type'] = 'tag'
                    # stop on first tag, because gitlab is good (c)
                    break
        return ret

    def release_download_url(self, release, shorter=False):
        """Get release download URL."""
        if shorter:
            log.info('Shorter URLs are not supported for GitLab yet')
        # https://gitlab.com/onedr0p/sonarr-episode-prune/-/archive/v3.0.0/sonarr-episode-prune-v3.0.0.tar.gz
        ext = 'zip' if os.name == 'nt' else 'tar.gz'
        tag = release['tag_name']
        url_format = 'https://{}/{}/-/archive/{}/{}-{}.{}'
        return url_format.format(self.hostname, self.repo, tag, self.repo.split('/')[1], tag, ext)

    def repo_license(self, tag):
        # TODO implement
        pass
