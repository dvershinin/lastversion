"""
lastversion
==========
License: BSD, see LICENSE for more details.
"""

__author__ = "Danila Vershinin"

import logging

from .lastversion import check_version, clear_cache, has_update, latest

__all__ = ["check_version", "clear_cache", "has_update", "latest"]


# https://realpython.com/python-logging-source-code/#library-vs-application-logging-what-is-nullhandler
# When used as a library, we default to opt-in approach, whereas library user
# has to enable logging
logging.getLogger(__name__).addHandler(logging.NullHandler())
# patch up https://github.com/ionrock/cachecontrol/issues/230
logging.getLogger("cachecontrol.controller").addHandler(logging.NullHandler())
logging.getLogger("pip._vendor.cachecontrol.controller").addHandler(logging.NullHandler())
