"""
Maps SPDX ID from https://spdx.org/licenses/ to corresponding short name
license as recommended by Fedora
https://fedoraproject.org/wiki/Licensing:Main?rd=Licensing#Good_Licenses
"""
rpmspec_licenses = {
    "Apache-1.0": "ASL 1.0",
    "Apache-1.1": "ASL 1.1",
    "Apache-2.0": "ASL 2.0",
    "AFL-1.1": "AFL",
    "AFL-1.2": "AFL",
    "AFL-2.0": "AFL",
    "AFL-2.1": "AFL",
    "AFL-3.0": "AFL",
    "Beerware": "Beerware",
    "BSD-2-Clause": "BSD",
    "BSD-2-Clause-Patent": "BSD-2-Clause-Patent",
    "GPL-2.0-only": "GPLv2",
    "GPL-2.0-or-later": "GPLv2+",
    "GPL-3.0-only": "GPLv3",
    "GPL-3.0-or-later": "GPLv3+",
    "MIT": "MIT",
    "OpenSSL": "OpenSSL",
    "Zlib": "zlib",
}
