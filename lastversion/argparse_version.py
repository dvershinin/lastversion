import sys as _sys
from argparse import SUPPRESS, Action

import lastversion
from .__about__ import __version__


class VersionAction(Action):

    def __init__(self,
                 option_strings,
                 version=None,
                 dest=SUPPRESS,
                 default=SUPPRESS,
                 help="show program's version number and exit"):
        super(VersionAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            default=default,
            nargs=0,
            help=help)
        self.version = version

    def __call__(self, parser, namespace, values, option_string=None):
        version = '%(prog)s {version}'.format(version=__version__)
        last_version = lastversion.latest(lastversion.__self__)
        if __version__ == str(last_version):
            version += ', up to date'
        else:
            version += ', newer version {} available'.format(last_version)
        formatter = parser._get_formatter()
        formatter.add_text(version)
        parser._print_message(formatter.format_help(), _sys.stdout)
        parser.exit()
