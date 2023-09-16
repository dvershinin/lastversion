"""Version class for lastversion"""
import re
from datetime import datetime
from packaging.version import Version as PackagingVersion, InvalidVersion


class Version(PackagingVersion):
    """
    This class abstracts handling of a project's versions. It implements the
    scheme defined in PEP 440. A `Version` instance is comparison-aware and
    can be compared and sorted using the standard Python interfaces.

    This class is descendant from Version found in `packaging.version`,
    and implements some additional, "AI"-like normalization during instantiation.

    Args:
        version (str): The string representation of a version which will be
                      parsed and normalized before use.
    Raises:
        InvalidVersion: If the ``version`` does not conform to PEP 440 in
                        any way then this exception will be raised.
    """

    def fix_letter_post_release(self, match):
        self.fixed_letter_post_release = True
        return match.group(1) + '.post' + str(ord(match.group(2)))

    def is_semver(self):
        """Check if this a semantic version"""
        return self.base_version.count('.') == 2

    @staticmethod
    def part_to_pypi(part):
        """
        Convert a version part to a PyPI compatible string
        See https://peps.python.org/pep-0440/
        Helps devel releases to be correctly identified
        See https://www.python.org/dev/peps/pep-0440/#developmental-releases
        """
        if part in ['devel', 'test', 'dev']:
            part = 'dev0'
        elif part in ['alpha']:
            # "4.3.0-alpha"
            part = 'a0'
        elif part in ['beta']:
            # "4.3.0-beta"
            part = 'b0'
            # if part starts with rc<num>., discard non-relevant info while preserving RC level
        elif re.search('^rc(\\d+)\\.', part):
            # rc2.windows.1 => rc2.post1
            sub_parts = part.split('.')
            part = sub_parts[0]
            for sub in sub_parts[1:]:
                if sub.isdigit():
                    # use first numeric as post-release to RC
                    part += ".post" + sub
        else:
            # help post (patch) releases to be correctly identified (e.g. Magento 2.3.4-p2)
            # p12 => post12
            part = re.sub('^p(\\d+)$', 'post\\1', part, 1)
        if part.isalpha():
            # it's meaningless to us if it has only letters
            part = None
        return part

    @staticmethod
    def join_dashed_number_status(version):
        """
        Join status with its number when separated by dash in a version string.
        E.g., 4.27-chaos-preview-3 -> 4.27-chaos-pre3
        Helps devel releases to be correctly identified
        # https://www.python.org/dev/peps/pep-0440/#developmental-releases

        Args:
            version:

        Returns:
            str:
        """
        version = re.sub('-devel$', '-dev0', version, 1)
        # help post (patch) releases to be correctly identified (e.g., Magento 2.3.4-p2)
        version = re.sub('-p(\\d+)$', '-post\\1', version, 1)

        # 4.27-chaos-preview-3 -> 4.27-chaos-pre3
        version = re.sub('-preview-(\\d+)', '-pre\\1', version, 1)
        # 5.0.0-early-access-2 -> 5.0.0-alpha2
        version = re.sub('-early-access-(\\d+)', '-alpha\\1', version, 1)
        # v4.0.0-pre-0 -> v4.0.0-pre0
        version = re.sub('-pre-(\\d+)', '-pre\\1', version, 1)

        # v0.16.0-beta.rc4 -> v0.16.0-beta4
        # both beta and rc? :) -> beta
        version = re.sub(r'-beta[-.]rc(\d+)', '-beta\\1', version, 1)
        return version

    def __init__(self, version, char_fix_required=False):
        """Instantiate the `Version` object.

        Args:
            version (str): The version-like string
            char_fix_required (bool): Should we treat alphanumerics as part of version
        """
        self.fixed_letter_post_release = False

        # Join status with its number, e.g., preview-3 -> pre3
        version = self.join_dashed_number_status(version)

        # parse out version components separated by dash
        parts = version.split('-')

        # go through parts which were separated by dash, normalize and exclude irrelevant
        parts_n = []
        for part in parts:
            part = self.part_to_pypi(part)
            if part:
                parts_n.append(part)
        if not parts_n:
            raise InvalidVersion("Invalid version: '{0}'".format(version))
        # remove *any* non-digits which appear at the beginning of the version string
        # e.g. Rhino1_7_13_Release does not even bother to put a delimiter...
        # such string at the beginning typically do not convey stability level,
        # so we are fine to remove them (unlike the ones in the tail)
        parts_n[0] = re.sub('^[^0-9]+', '', parts_n[0], 1)

        # go back to full string parse out
        version = ".".join(parts_n)

        if char_fix_required:
            version = re.sub('(\\d)([a-z])$', self.fix_letter_post_release, version, 1)
        # release-3_0_2 is often seen on Mercurial holders
        # note that the above code removes "release-" already, so we are left with "3_0_2"
        if re.search(r'^(?:\d+_)+(?:\d+)', version):
            version = version.replace('_', '.')
        # finally, split by dot "delimiter", see if there are common words which are definitely
        # removable
        parts = version.split('.')
        version = []
        for p in parts:
            if p.lower() in ['release']:
                continue
            version.append(p)
        version = '.'.join(version)
        super(Version, self).__init__(version)

    @property
    def epoch(self):
        # type: () -> int
        """
        An integer giving the version epoch of this Version instance
        """
        _epoch = self._version.epoch  # type: int
        return _epoch

    @property
    def release(self):
        """
        A tuple of integers giving the components of the release segment
        of this Version instance; that is, the 1.2.3 part of the version
        number, including trailing zeroes but not including the epoch or
        any prerelease/development/postrelease suffixes
        """
        _release = self._version.release
        return _release

    @property
    def pre(self):
        _pre = self._version.pre
        return _pre

    @property
    def post(self):
        return self._version.post[1] if self._version.post else None

    @property
    def dev(self):
        return self._version.dev[1] if self._version.dev else None

    @property
    def local(self):
        if self._version.local:
            return ".".join(str(x) for x in self._version.local)
        return None

    @property
    def major(self):
        # type: () -> int
        return self.release[0] if len(self.release) >= 1 else 0

    @property
    def minor(self):
        # type: () -> int
        return self.release[1] if len(self.release) >= 2 else 0

    @property
    def micro(self):
        # type: () -> int
        return self.release[2] if len(self.release) >= 3 else 0

    @staticmethod
    def is_not_date(num):
        """Helper function to determine if a number is not a date"""
        num_str = str(num)
        try:
            # Attempt to parse the number as a date
            datetime.strptime(num_str, '%Y%m%d')
            return False
        except ValueError:
            # If parsing fails, the number is not a date
            return True

    @property
    def is_prerelease(self):
        """
        Version is a prerelease if it contains all the following:
        * 90+ micro component
        * no date in micro component
        """
        # type: () -> bool
        if self.major and self.minor and self.micro >= 90 and self.is_not_date(self.micro):
            return True
        return self.dev is not None or self.pre is not None

    @property
    def even(self):
        """Check if this is an even minor version"""
        return self.minor and not self.minor % 2

    def sem_extract_base(self, level=None):
        """
        Return Version with desired semantic version level base
        E.g. for 5.9.3 it will return 5.9 (patch is None)
        """
        if level == 'major':
            # get major
            return Version(str(self.major))
        if level == 'minor':
            return Version(f"{self.major}.{self.minor}")
        if level == 'patch':
            return Version(f"{self.major}.{self.minor}.{self.micro}")
        return self

    def __str__(self):
        # type: () -> str
        parts = []

        # Epoch
        if self.epoch != 0:
            parts.append("{0}!".format(self.epoch))

        # Release segment
        parts.append(".".join(str(x) for x in self.release))

        # Pre-release
        if self.pre is not None:
            parts.append("".join(str(x) for x in self.pre))

        # Post-release
        if self.post is not None:
            if self.fixed_letter_post_release:
                parts.append("{0}".format(chr(self.post)))
            else:
                parts.append(".post{0}".format(self.post))

        # Development release
        if self.dev is not None:
            parts.append(".dev{0}".format(self.dev))

        # Local version segment
        if self.local is not None:
            parts.append("+{0}".format(self.local))

        return "".join(parts)
