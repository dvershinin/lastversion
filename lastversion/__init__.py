"""
lastversion
==========
License: BSD, see LICENSE for more details.
"""

__author__ = "Danila Vershinin"

from .lastversion import main
from .__about__ import (
    __version__,
)

import logging
# https://realpython.com/python-logging-source-code/#library-vs-application-logging-what-is-nullhandler
# when used as library, we default to opt-in approach, whereas library user have to enable logging
# from lastversion
logging.getLogger(__name__).addHandler(logging.NullHandler())
# patch up https://github.com/ionrock/cachecontrol/issues/230
logging.getLogger('cachecontrol.controller').addHandler(logging.NullHandler())
logging.getLogger('pip._vendor.cachecontrol.controller').addHandler(logging.NullHandler())
