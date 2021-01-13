import re

from packaging.version import Version as PackagingVersion


class Version(PackagingVersion):

    def fix_letter_post_release(self, match):
        self.fixed_letter_post_release = True
        return match.group(1) + '.post' + str(ord(match.group(2)))

    def __init__(self, version):

        self.fixed_letter_post_release = False

        # many times they would tag foo-1.2.3 which would parse to LegacyVersion
        # we can avoid this, by reassigning to what comes after the dash:
        parts = version.split('-', 1)

        if len(parts) == 2 and parts[0].isalpha():
            version = parts[1]
        # help devel releases to be correctly identified
        # https://www.python.org/dev/peps/pep-0440/#developmental-releases
        version = re.sub('-devel$', '.dev0', version, 1)
        version = re.sub('-test$', '.dev0', version, 1)
        # help post (patch) releases to be correctly identified (e.g. Magento 2.3.4-p2)
        version = re.sub('-p(\\d+)$', '.post\\1', version, 1)
        version = re.sub('(\\d)([a-z])$', self.fix_letter_post_release, version, 1)
        # release-3_0_2 is often seen on Mercurial holders
        # note that above code removes "release-" already so we are left with "3_0_2"
        if re.search(r'^(?:\d+_)+(?:\d+)', version):
            version = version.replace('_', '.')

        super(Version, self).__init__(version)

    @property
    def epoch(self):
        # type: () -> int
        _epoch = self._version.epoch  # type: int
        return _epoch

    @property
    def release(self):
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
        else:
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
