"""Helm Chart repo holder."""

import logging

import yaml

from lastversion.repo_holders.base import BaseProjectHolder

log = logging.getLogger(__name__)


class HelmChartRepoSession(BaseProjectHolder):
    """Helm Chart repo session."""

    # Any URI identifies a project
    REPO_IS_URI = True

    # noinspection PyUnusedLocal
    def __init__(self, repo, hostname=None):
        super().__init__(repo, hostname)
        if not repo.endswith("Chart.yaml"):
            self.repo = repo.rstrip("/") + "/Chart.yaml"
        log.info("Helm Chart.yml: %s", repo)

    def get_latest(self, pre_ok=False, major=None):
        """Get the latest release."""
        # https://github.com/bitnami/charts/blob/master/bitnami/aspnet-core/Chart.yaml
        # https://raw.githubusercontent.com/bitnami/charts/master/bitnami/aspnet-core/Chart.yaml
        url = f"https://{self.hostname}/{self.repo}"
        if self.hostname in ["github.com"]:
            url = f"https://raw.githubusercontent.com/{self.repo.replace('/blob/', '/')}"
        r = self.get(url)
        chart_data = yaml.safe_load(r.text)
        return {
            "tag_name": None,
            "tag_date": None,
            "version": self.sanitize_version(chart_data["version"], pre_ok, major),
            "type": "helm",
        }
