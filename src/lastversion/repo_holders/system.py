"""Version holder based on system package repositories."""

import datetime
import logging

from lastversion.repo_holders.base import BaseProjectHolder

log = logging.getLogger(__name__)


class SystemRepoSession(BaseProjectHolder):
    """Version holder based on system package repositories."""

    # noinspection PyUnusedLocal
    def __init__(self, repo, hostname=None):
        super().__init__(repo, hostname)

    def dnf_get_available_version(self, pre_ok, major):
        """Get the latest release available via `dnf`."""
        ret = {}
        # noinspection PyUnresolvedReferences,PyPackageRequirements
        import dnf

        with dnf.Base() as base:
            releasever = dnf.rpm.detect_releasever(base.conf.installroot)
            base.conf.substitutions["releasever"] = releasever
            # Repositories are needed if we want to install anything.
            base.read_all_repos()
            # A sack is needed for querying.
            base.fill_sack()
            # A query matches all packages in sack
            q = base.sack.query()
            # https://dnf.readthedocs.io/en/latest/use_cases.html#id3
            # https: // dnf.readthedocs.io / en / latest / api_queries.html  # dnf.query.Query
            # Derived query matches only available packages
            a = q.available()
            a = a.filter(name=self.repo)
            for pkg in a:  # `a` only gets evaluated here
                version = self.sanitize_version(pkg.version, pre_ok, major)
                if not ret or ret["version"] < version:
                    ret = {
                        "version": version,
                        "tag_name": pkg.evr,
                        "tag_date": datetime.datetime.fromtimestamp(pkg.buildtime),
                    }
        return ret or None

    def yum_get_available_version(self, pre_ok, major):
        """Get the latest release available via `yum`."""
        ret = {}
        # noinspection PyUnresolvedReferences,PyPackageRequirements
        import yum

        yum_loggers = [
            "yum.filelogging.RPMInstallCallback",
            "yum.verbose.Repos",
            "yum.verbose.plugin",
            "yum.Depsolve",
            "yum.verbose",
            "yum.plugin",
            "yum.Repos",
            "yum",
            "yum.verbose.YumBase",
            "yum.filelogging",
            "yum.verbose.YumPlugins",
            "yum.RepoStorage",
            "yum.YumBase",
            "yum.filelogging.YumBase",
            "yum.verbose.Depsolve",
        ]
        for logger in yum_loggers:
            logging.getLogger(logger).setLevel(logging.CRITICAL)
        yb = yum.YumBase()
        yb.preconf.debuglevel = 0
        yb.preconf.errorlevel = 0
        yb.setCacheDir()
        pkgs = yb.pkgSack.returnNewestByNameArch(patterns=[self.repo])
        for pkg in pkgs:
            version = self.sanitize_version(pkg.vr, pre_ok, major)
            if not ret or ret["version"] < version:
                ret = {"version": version, "tag_name": pkg.vr}
        return ret or None

    def apt_get_available_version(self, pre_ok, major):
        """Get the latest release available via `apt`."""
        ret = {}
        # noinspection PyUnresolvedReferences,PyPackageRequirements
        import apt

        cache = apt.cache.Cache()
        cache.update()
        cache.open()
        if self.repo in cache:
            pkg = cache[self.repo]
            for pkg_ver in pkg.versions:
                version = pkg_ver.version.split("-")[0]
                version = self.sanitize_version(version, pre_ok, major)
                if not ret or ret["version"] < version:
                    ret = {
                        "version": version,
                        "tag_name": pkg_ver.version,
                        # 'tag_date': ?
                    }
        return ret or None

    def get_latest(self, pre_ok=False, major=None):
        """Get the latest release."""
        try:
            return self.dnf_get_available_version(pre_ok, major)
        except ImportError:
            pass
        try:
            return self.yum_get_available_version(pre_ok, major)
        except ImportError:
            pass
        try:
            return self.apt_get_available_version(pre_ok, major)
        except ImportError:
            pass
        return None
