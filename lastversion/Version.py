import re

from packaging.version import Version as PackagingVersion, InvalidVersion


class Version(PackagingVersion):
    """
    This class abstracts handling of a project's versions. It implements the
    scheme defined in PEP 440. A `Version` instance is comparison
    aware and can be compared and sorted using the standard Python interfaces.

    This class is descendant from Version found in packaging.version,
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

    def __init__(self, version, char_fix_required=False):
        # type: (str) -> None
        self.fixed_letter_post_release = False

        # many times they would tag foo-1.2.3 which would parse to LegacyVersion
        # we can avoid this, by reassigning to what comes after the dash:
        parts = version.split('-')

        # TODO test v5.12-rc1-dontuse -> v5.12.rc1
        # go through parts separated by dot, detect beta level, and weed out numberless info:
        parts_n = []
        for part in parts:
            # help devel releases to be correctly identified
            # https://www.python.org/dev/peps/pep-0440/#developmental-releases
            if part in ['devel', 'test', 'dev']:
                part = 'dev0'
            else:
                # help post (patch) releases to be correctly identified (e.g. Magento 2.3.4-p2)
                # p12 => post12
                part = re.sub('^p(\\d+)$', 'post\\1', part, 1)
            if not part.isalpha():
                parts_n.append(part)

        if not parts_n:
            raise InvalidVersion("Invalid version: '{0}'".format(version))
        # remove *any* non-digits which appear at the beginning of the version string
        # e.g. Rhino1_7_13_Release does not even bother to put a delimiter...
        # such string at the beginning typically do not convey stability level
        # so we are fine to remove them (unlike the ones in the tail)
        parts_n[0] = re.sub('^[^0-9]+', '', parts_n[0], 1)

        # go back to full string parse out
        version = ".".join(parts_n)

        if char_fix_required:
            version = re.sub('(\\d)([a-z])$', self.fix_letter_post_release, version, 1)
        # release-3_0_2 is often seen on Mercurial holders
        # note that above code removes "release-" already so we are left with "3_0_2"
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
        """
        An integer giving the version epoch of this Version instance
        """
        # type: () -> int
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
