import logging as log  # for verbose output
import os

from .ProjectHolder import ProjectHolder


class BitBucketRepoSession(ProjectHolder):
    DEFAULT_HOSTNAME = 'bitbucket.org'
    KNOWN_REPO_URLS = {
        'mmonit.com': {'repo': 'tildeslash/monit'}
    }

    def __init__(self, repo, hostname):
        super(BitBucketRepoSession, self).__init__()
        self.api_token = os.getenv("GITHUB_API_TOKEN")
        self.tags_cache = {}
        self.hostname = hostname
        if not self.hostname:
            self.hostname = self.DEFAULT_HOSTNAME
        # Explicitly specify API version we want:
        # headers['Accept'] = "application/vnd.github.v3+json"
        if self.api_token:
            log.info('Using API token.')
            self.headers.update({'Authorization': "token {}".format(self.api_token)})
        if self.hostname != self.DEFAULT_HOSTNAME:
            self.api_base = 'https://{}/api/v3'.format(self.hostname)
        else:
            self.api_base = 'https://api.{}'.format(self.DEFAULT_HOSTNAME)
        if '/' not in repo:
            r = self.get(
                '{}/search/repositories?q={}+in:name'.format(self.api_base, repo))
            self.repo = r.json()['items'][0]['full_name']
        else:
            self.repo = repo

    def get_latest(self, pre_ok=False, major=None):
        response = self.get("https://api.bitbucket.org/2.0/repositories/{}/downloads".format(
            "tildeslash/monit"))
        data = response.json()
        release = data['values'][0]
        version = self.sanitize_version(release['name'], pre_ok, major)
        release['version'] = version
        release['tag_name'] = release['name']
        return release
