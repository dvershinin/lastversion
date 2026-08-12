"""FeedRepoSession class."""

import datetime
import logging
from urllib.parse import urljoin

import feedparser

from lastversion.repo_holders.base import BaseProjectHolder

log = logging.getLogger(__name__)

# The Varnish Cache FOSS project was renamed to Vinyl Cache in the 9.0 release
# (2026-03-16) after a trademark dispute with Varnish Software. The
# varnishcache/* GitHub org is archived; development moved to
# code.vinyl-cache.org. Varnish Software kept the trademark and now runs
# github.com/varnish/varnish as a *downstream fork* -- a different codebase,
# not what these entries should resolve to.
#
# The 6.0 and 8.0 LTS branches stayed with Vinyl Cache, so every historic
# spelling must point at vinyl-cache.org. That host also serves TLS 1.2, which
# varnish-cache.org (now Varnish Software's) does not -- and EL7 builders
# running packaging auto-bump crons cannot negotiate TLS 1.3.
#
# "repo" stays "varnish-cache": it is the display/cache label, and the tarballs
# are still named varnish-X.Y.Z.tgz.
_VINYL_CACHE = {
    "repo": "varnish-cache",
    "hostname": "vinyl-cache.org",
    "page": "https://vinyl-cache.org/releases/",
}


class FeedRepoSession(BaseProjectHolder):
    """Feed repo session."""

    KNOWN_REPO_URLS = {
        # URL-form lookups (e.g. update-spec deriving from a spec's URL:)
        # must resolve to the releases page too, not the stale homepage feed.
        "varnish-cache.org": _VINYL_CACHE,
        "vinyl-cache.org": _VINYL_CACHE,
    }
    KNOWN_REPOS_BY_NAME = {
        "filezilla": {
            "repo": "filezilla",
            "hostname": "filezilla-project.org",
            "only": "FileZilla Client",
        },
        # 6.0 LTS releases exist only as dist tarballs linked from the
        # releases page; the news feed announces them late or not at all.
        "varnish-cache": _VINYL_CACHE,
        "vinyl-cache": _VINYL_CACHE,
        # The GitHub owner/repo form must resolve here too: the org is
        # archived, so asking GitHub yields a stale 6.0.16 -- and packaging
        # cascades call it in exactly this form to stamp the version their
        # vmod builds pin against.
        "varnishcache/varnish-cache": _VINYL_CACHE,
        "vinyl-cache/vinyl-cache": _VINYL_CACHE,
        # Bare-word host invocations (e.g. `--at website-feed vinyl-cache.org`)
        # arrive as a repo name, not a hostname, so KNOWN_REPO_URLS misses.
        "varnish-cache.org": _VINYL_CACHE,
        "vinyl-cache.org": _VINYL_CACHE,
    }
    CAN_BE_SELF_HOSTED = True
    # Unlimited number of components (URI as is)
    REPO_IS_URI = True

    # https://alex.miller.im/posts/python-3-feedfinder-rss-detection-from-url/
    def find_feed(self, site):
        """Find the feed for a given site"""
        # noinspection PyPep8Naming
        from bs4 import BeautifulSoup as bs4

        raw = self.get(site).text
        result = []
        possible_feeds = []
        html = bs4(raw, "html.parser")
        self.home_soup = html
        feed_urls = html.findAll("link", rel="alternate")

        base_tag = html.find("base", href=True)
        base_url = urljoin(site, base_tag["href"]) if base_tag else site

        for f in feed_urls:
            t = f.get("type", None)
            if not t:
                continue
            if "rss" in t or "xml" in t:
                href = f.get("href", None)
                if href:
                    possible_feeds.append(urljoin(base_url, href))
        a_tags = html.findAll("a")
        for a in a_tags:
            href = a.get("href", None)
            if not href:
                continue
            if "xml" in href or "rss" in href or "feed" in href:
                possible_feeds.append(urljoin(base_url, href))
        for url in list(set(possible_feeds)):
            f = feedparser.parse(url, agent=self.user_agent)
            if len(f.entries) > 0 and url not in result:
                result.append(url)
        return result

    def __init__(self, repo, hostname):
        # A bare-word invocation like `--at website-feed varnish-cache.org`
        # arrives with hostname=None and the site in `repo`.
        if not hostname:
            hostname = repo
        super().__init__(repo, hostname)
        self.home_soup = None
        # Optional page whose hyperlinks carry versioned artifact names
        # (e.g. a releases/downloads listing); takes precedence over the
        # discovered feed because homepage feeds routinely lag or omit
        # maintenance releases. Set via a known-repo "page" entry.
        self.page_url = None
        feeds = self.find_feed("https://" + hostname + "/")
        if not feeds:
            return
        self.hostname = hostname
        log.info("Using feed URL: %s", feeds[0])
        self.feed_url = feeds[0]

    def set_page(self, page_url):
        """Use a link-listing page as the version source."""
        self.page_url = page_url

    def is_instance(self):
        return self.feed_url or self.page_url

    def get_latest_from_page_links(self, pre_ok=False, major=None):
        """Latest version among hyperlink targets/texts of the page."""
        from urllib.parse import unquote

        from bs4 import BeautifulSoup as bs4

        html = bs4(self.get(self.page_url).text, "html.parser")
        ret = {}
        for a in html.findAll("a"):
            href = a.get("href", None)
            if not href:
                continue
            candidate = unquote(href.rstrip("/").rsplit("/", 1)[-1])
            version = self.sanitize_version(candidate, pre_ok, major)
            if not version and a.text:
                version = self.sanitize_version(a.text.strip(), pre_ok, major)
            if not version:
                continue
            if not ret or version > ret["version"]:
                ret = {"tag_name": candidate, "version": version}
        return ret or None

    def get_latest(self, pre_ok=False, major=None):
        """Get the latest release."""
        if self.page_url:
            return self.get_latest_from_page_links(pre_ok=pre_ok, major=major)
        ret = {}
        # To leverage `cachecontrol`, we fetch the feed using requests as
        # usual, then feed the feed to feedparser as a raw string e.g.
        # https://hg.nginx.org/nginx/atom-tags
        # https://pythonhosted.org/feedparser/common-atom-elements.html
        r = self.get(self.feed_url)
        feed = feedparser.parse(r.text)
        for tag in feed.entries:
            tag_name = tag["title"]
            version = self.sanitize_version(tag_name, pre_ok, major)
            if not version:
                continue
            if not ret or version > ret["version"]:
                ret = tag
                tag["tag_name"] = tag["title"]
                tag["version"] = version
                if "published_parsed" in tag:
                    # converting from struct
                    tag["tag_date"] = datetime.datetime(*tag["published_parsed"][:6])
                elif "updated_parsed" in tag:
                    tag["tag_date"] = datetime.datetime(*tag["updated_parsed"][:6])
        return ret or None
