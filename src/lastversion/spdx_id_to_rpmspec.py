"""
Maps SPDX ID from https://spdx.org/licenses/ to corresponding short name
license as recommended by Fedora
https://docs.fedoraproject.org/en-US/legal/allowed-licenses/

Note: Fedora uses SPDX identifiers directly as of Fedora 38+, but older
specs may still use legacy short names. This mapping supports both.
"""

rpmspec_licenses = {
    # Apache licenses
    "Apache-1.0": "ASL 1.0",
    "Apache-1.1": "ASL 1.1",
    "Apache-2.0": "Apache-2.0",
    # Academic Free License
    "AFL-1.1": "AFL-1.1",
    "AFL-1.2": "AFL-1.2",
    "AFL-2.0": "AFL-2.0",
    "AFL-2.1": "AFL-2.1",
    "AFL-3.0": "AFL-3.0",
    # Artistic licenses
    "Artistic-1.0": "Artistic-1.0",
    "Artistic-1.0-Perl": "Artistic-1.0-Perl",
    "Artistic-2.0": "Artistic-2.0",
    # BSD licenses
    "0BSD": "0BSD",
    "BSD-1-Clause": "BSD-1-Clause",
    "BSD-2-Clause": "BSD-2-Clause",
    "BSD-2-Clause-Patent": "BSD-2-Clause-Patent",
    "BSD-3-Clause": "BSD-3-Clause",
    "BSD-3-Clause-Clear": "BSD-3-Clause-Clear",
    "BSD-4-Clause": "BSD-4-Clause",
    # Boost
    "BSL-1.0": "BSL-1.0",
    # Creative Commons
    "CC0-1.0": "CC0-1.0",
    "CC-BY-1.0": "CC-BY-1.0",
    "CC-BY-2.0": "CC-BY-2.0",
    "CC-BY-2.5": "CC-BY-2.5",
    "CC-BY-3.0": "CC-BY-3.0",
    "CC-BY-4.0": "CC-BY-4.0",
    "CC-BY-SA-1.0": "CC-BY-SA-1.0",
    "CC-BY-SA-2.0": "CC-BY-SA-2.0",
    "CC-BY-SA-2.5": "CC-BY-SA-2.5",
    "CC-BY-SA-3.0": "CC-BY-SA-3.0",
    "CC-BY-SA-4.0": "CC-BY-SA-4.0",
    # CDDL
    "CDDL-1.0": "CDDL-1.0",
    "CDDL-1.1": "CDDL-1.1",
    # Eclipse
    "EPL-1.0": "EPL-1.0",
    "EPL-2.0": "EPL-2.0",
    # European Union Public License
    "EUPL-1.0": "EUPL-1.0",
    "EUPL-1.1": "EUPL-1.1",
    "EUPL-1.2": "EUPL-1.2",
    # GPL licenses
    "GPL-1.0-only": "GPL-1.0-only",
    "GPL-1.0-or-later": "GPL-1.0-or-later",
    "GPL-2.0-only": "GPL-2.0-only",
    "GPL-2.0-or-later": "GPL-2.0-or-later",
    "GPL-3.0-only": "GPL-3.0-only",
    "GPL-3.0-or-later": "GPL-3.0-or-later",
    # LGPL licenses
    "LGPL-2.0-only": "LGPL-2.0-only",
    "LGPL-2.0-or-later": "LGPL-2.0-or-later",
    "LGPL-2.1-only": "LGPL-2.1-only",
    "LGPL-2.1-or-later": "LGPL-2.1-or-later",
    "LGPL-3.0-only": "LGPL-3.0-only",
    "LGPL-3.0-or-later": "LGPL-3.0-or-later",
    # AGPL licenses
    "AGPL-1.0-only": "AGPL-1.0-only",
    "AGPL-1.0-or-later": "AGPL-1.0-or-later",
    "AGPL-3.0-only": "AGPL-3.0-only",
    "AGPL-3.0-or-later": "AGPL-3.0-or-later",
    # ISC
    "ISC": "ISC",
    # MIT variants
    "MIT": "MIT",
    "MIT-0": "MIT-0",
    # Mozilla Public License
    "MPL-1.0": "MPL-1.0",
    "MPL-1.1": "MPL-1.1",
    "MPL-2.0": "MPL-2.0",
    "MPL-2.0-no-copyleft-exception": "MPL-2.0-no-copyleft-exception",
    # Other common licenses
    "Beerware": "Beerware",
    "BlueOak-1.0.0": "BlueOak-1.0.0",
    "curl": "curl",
    "FSFAP": "FSFAP",
    "FSFUL": "FSFUL",
    "FSFULLR": "FSFULLR",
    "HPND": "HPND",
    "ICU": "ICU",
    "ImageMagick": "ImageMagick",
    "Info-ZIP": "Info-ZIP",
    "JSON": "JSON",
    "Libpng": "Libpng",
    "libtiff": "libtiff",
    "MulanPSL-2.0": "MulanPSL-2.0",
    "NCSA": "NCSA",
    "ODbL-1.0": "ODbL-1.0",
    "OFL-1.0": "OFL-1.0",
    "OFL-1.1": "OFL-1.1",
    "OpenSSL": "OpenSSL",
    "PostgreSQL": "PostgreSQL",
    "PSF-2.0": "PSF-2.0",
    "Python-2.0": "Python-2.0",
    "Ruby": "Ruby",
    "SGI-B-2.0": "SGI-B-2.0",
    "Sleepycat": "Sleepycat",
    "TCL": "TCL",
    "Unlicense": "Unlicense",
    "Vim": "Vim",
    "W3C": "W3C",
    "WTFPL": "WTFPL",
    "X11": "X11",
    "Zlib": "Zlib",
    "zlib-acknowledgement": "zlib-acknowledgement",
}
