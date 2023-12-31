"""
lastversion
==========
License: BSD, see LICENSE for more details.
"""

__author__ = "Danila Vershinin"

import logging

from .__about__ import (
    __version__,
)

# Intentionally import for export here, so it is ok to silence DeepSource test
# skipcq: PY-W2000
from .lastversion import __self__

# skipcq: PY-W2000
from .lastversion import check_version

# skipcq: PY-W2000
from .lastversion import has_update

# skipcq: PY-W2000
from .lastversion import latest

# skipcq: PY-W2000
from .lastversion import main

# https://realpython.com/python-logging-source-code/#library-vs-application-logging-what-is-nullhandler
# When used as a library, we default to opt-in approach, whereas library user
# has to enable logging
# from lastversion
logging.getLogger(__name__).addHandler(logging.NullHandler())
# patch up https://github.com/ionrock/cachecontrol/issues/230
logging.getLogger("cachecontrol.controller").addHandler(logging.NullHandler())
logging.getLogger("pip._vendor.cachecontrol.controller").addHandler(
    logging.NullHandler()
)
