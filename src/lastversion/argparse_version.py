"""Provides a custom argparse action to show the program's version and exit."""

import logging
import sys as _sys
from argparse import SUPPRESS, Action

import lastversion

from .__about__ import __self__, __version__
from .exceptions import ApiCredentialsError

log = logging.getLogger(__name__)


class VersionAction(Action):
    """Custom argparse action to show the program's version and exit."""

    def __init__(self, **kwargs):
        # Set default values if not provided in kwargs
        kwargs.setdefault("dest", SUPPRESS)
        kwargs.setdefault("default", SUPPRESS)
        kwargs.setdefault("nargs", 0)
        kwargs.setdefault("help", "show program's version number and exit")
        super().__init__(**kwargs)
        self.version = kwargs.get("version2")

    def __call__(self, parser, namespace, values, option_string=None):
        version = f"%(prog)s {__version__}"
        try:
            last_version = lastversion.latest(__self__)
            if __version__ == str(last_version):
                version += ", up to date"
            else:
                version += f", newer version {last_version} available"
        except ApiCredentialsError as e:
            logging.warning(e)
        formatter = parser.formatter_class(prog=parser.prog)
        formatter.add_text(version)
        _sys.stdout.write(formatter.format_help())
        parser.exit()
