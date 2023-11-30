import datetime
import logging
from urllib.parse import urlparse

import feedparser

from .ProjectHolder import ProjectHolder

log = logging.getLogger(__name__)


class FeedRepoSession(ProjectHolder):
    KNOWN_REPOS_BY_NAME = {
        "filezilla": {
            "repo": "filezilla",
            "hostname": "filezilla-project.org",
            "only": "FileZilla Client",
        }
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

        for f in feed_urls:
            t = f.get("type", None)
            if not t:
                continue
            if "rss" in t or "xml" in t:
                href = f.get("href", None)
                if href:
                    possible_feeds.append(href)
        parsed_url = urlparse(site)
        base = f"{parsed_url.scheme}://{parsed_url.hostname}"
        a_tags = html.findAll("a")
        for a in a_tags:
            href = a.get("href", None)
            if not href:
                continue
            if "xml" in href or "rss" in href or "feed" in href:
                possible_feeds.append(base + "/" + href.lstrip("/"))
        for url in list(set(possible_feeds)):
            f = feedparser.parse(url)
            if len(f.entries) > 0 and url not in result:
                result.append(url)
        return result

    def __init__(self, repo, hostname):
        super(FeedRepoSession, self).__init__(repo, hostname)
        self.home_soup = None
        feeds = self.find_feed("https://" + hostname + "/")
        if not feeds:
            return
        self.hostname = hostname
        log.info("Using feed URL: %s", feeds[0])
        self.feed_url = feeds[0]

    def is_instance(self):
        return self.feed_url

    def get_latest(self, pre_ok=False, major=None):
        """Get the latest release."""
        ret = None
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
        return ret
