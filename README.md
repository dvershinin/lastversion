# lastversion

[![Python package](https://github.com/dvershinin/lastversion/actions/workflows/pythonpackage.yml/badge.svg)](https://github.com/dvershinin/lastversion/actions/workflows/pythonpackage.yml)
[![PyPI version](https://badge.fury.io/py/lastversion.svg)](https://badge.fury.io/py/lastversion)
[![GitHub Release](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Flastversion-api.getpagespeed.com%2Fdvershinin%2Flastversion&query=version&label=Release)](https://github.com/dvershinin/lastversion/releases)
[![Documentation Status](https://readthedocs.org/projects/lastversion/badge/?version=latest)](https://lastversion.getpagespeed.com/en/latest/?badge=latest)
[![Codacy Badge](https://api.codacy.com/project/badge/Grade/380e3a38dc524112b4dcfc0492d5b816)](https://www.codacy.com/manual/GetPageSpeed/lastversion?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=dvershinin/lastversion&amp;utm_campaign=Badge_Grade)
[![Codacy Badge](https://app.codacy.com/project/badge/Coverage/380e3a38dc524112b4dcfc0492d5b816)](https://www.codacy.com/gh/dvershinin/lastversion/dashboard?utm_source=github.com&utm_medium=referral&utm_content=dvershinin/lastversion&utm_campaign=Badge_Coverage)
[![Buy Me a Coffee](https://img.shields.io/badge/dynamic/json?color=blue&label=Buy%20me%20a%20Coffee&prefix=%23&query=next_time_total&url=https%3A%2F%2Fwww.getpagespeed.com%2Fbuymeacoffee.json&logo=buymeacoffee)](https://www.buymeacoffee.com/dvershinin)

![Using lastversion in terminal](https://www.getpagespeed.com/img/lastversion.gif)

English | [简体中文](README-ZH-CN.md)

A tiny command-line utility that helps to answer a simple question:

> What is the latest *stable* version for a project?

... and, optionally, download/install it.

`lastversion` allows finding well-formatted, the latest release version of a project from these 
 supported locations:

*   [GitHub](https://github.com/dvershinin/lastversion/wiki/GitHub-specifics)
*   GitLab
*   BitBucket
*   PyPI
*   Mercurial
*   SourceForge
*   Wikipedia
*   WordPress plugin directory
*   Arbitrary software sites which publish releases in RSS/ATOM feeds

## Why you need `lastversion`

In general, quite many project authors complicate finding the latest version by:

*   Creating a formal release that is clearly a Release Candidate (`rc` in tag), but forgetting to
    mark it as a pre-release

*   Putting extraneous text in release tag e.g. `release-1.2.3` or `name-1.2.3-2019` anything fancy 
    like that

*   Putting or not putting the `v` prefix inside release tags. Today yes, tomorrow not. I'm not
    consistent about it myself :)

*   Switching from one version format to another, e.g. `v20150121` to `v2.0.1`

There is no consistency in human beings.

To deal with all this mess and simply get a well-formatted, last *stable* version (or download
 URL!) on the command line, you can use `lastversion`.

Its primary use is for build systems - whenever you want to watch specific projects for released
versions to build packages automatically.
Or otherwise require getting the latest version in your automation scripts.

[Like I do](https://www.getpagespeed.com/redhat)

`lastversion` does a little bit of AI to detect if releasers mistakenly filed a beta version as a 
stable release.
It incorporates logic for cleaning up human inconsistency from 
version information.

## Synopsis

```bash
lastversion apache/incubator-pagespeed-ngx 
#> 1.13.35.2

lastversion download apache/incubator-pagespeed-ngx 
#> downloaded incubator-pagespeed-ngx-v1.13.35.2-stable.tar.gz

lastversion download apache/incubator-pagespeed-ngx -o pagespeed.tar.gz 
#> downloads with chosen filename

lastversion https://transmissionbt.com/
#> 3.0

lastversion format "mysqld  Ver 5.6.51-91.0 for Linux"
#> 5.6.51
```

## Installation for RPM-based systems

Supported:

* CentOS/RHEL 7, 8, 9 including clones like AlmaLinux and Rocky Linux
* Amazon Linux 2
* Fedora Linux

```bash
sudo yum -y install https://extras.getpagespeed.com/release-latest.rpm
sudo yum -y install lastversion
```
   
## Installation for other systems

Installing with `pip` is easiest:

```bash
pip install lastversion
```
    
## Usage

Typically, you would just pass a repository URL (or repo owner/name to it) as the only argument, 
e.g.:

```bash
lastversion https://github.com/gperftools/gperftools
```

Equivalently accepted invocation with the same output is:

```bash
lastversion gperftools/gperftools
```    

If you're lazy to even copy-paste a project's URL, you can just type its name as argument, which 
will use repository search API (slower).
Helps to answer what is the latest Linux version:

```bash
lastversion linux
```

Or wondering what is the latest version of WordPress? 

```bash
lastversion wordpress
```
   
A special value of `self` for the main argument, will look up the last release of `lastversion` 
itself.

For more options to control output or behavior, see `--help` output:    

```text
usage: lastversion [-h] [--pre] [--sem {major,minor,patch,any}] [-v]
                   [-d [FILENAME]] [--format {version,assets,source,json,tag}]
                   [--assets] [--source] [-gt VER] [-b MAJOR] [--only REGEX]
                   [--exclude REGEX] [--filter REGEX] [--having-asset [ASSET]]
                   [-su] [--even]
                   [--at {github,gitlab,bitbucket,pip,hg,sf,website-feed,local,helm_chart,wiki,system,wp,gitea}]
                   [-y] [--version]
                   [{get,download,extract,unzip,test,format,install,update-spec}]
                   <repo URL or string>

Find the latest software release.

positional arguments:
  {get,download,extract,unzip,test,format,install,update-spec}
                        Action to run. Default: get
  <repo URL or string>  Repository in format owner/name or any URL that
                        belongs to it, or a version string

optional arguments:
  -h, --help            show this help message and exit
  --pre                 Include pre-releases in potential versions
  --sem {major,minor,patch,any}
                        Semantic versioning level base to print or compare
                        against
  -v, --verbose         Will give you an idea of what is happening under the
                        hood, -vv to increase verbosity level
  -d [FILENAME], -o [FILENAME], --download [FILENAME], --output [FILENAME]
                        Download with custom filename
  --format {version,assets,source,json,tag}
                        Output format
  --assets              Returns assets download URLs for last release
  --source              Returns only source URL for last release
  -gt VER, --newer-than VER
                        Output only if last version is newer than given
                        version
  -b MAJOR, --major MAJOR, --branch MAJOR
                        Only consider releases of a specific major version,
                        e.g. 2.1.x
  --only REGEX          Only consider releases containing this text. Useful
                        for repos with multiple projects inside
  --exclude REGEX       Only consider releases NOT containing this text.
                        Useful for repos with multiple projects inside
  --even                Only even versions like 1.[2].x, or 3.[6].x are
                        considered as stable                        
  --filter REGEX        Filters --assets result by a regular expression
  --having-asset [ASSET]
                        Only consider releases with this asset
  -su, --shorter-urls   A tiny bit shorter URLs produced
  --at {github,gitlab,bitbucket,pip,hg,sf,website-feed,local,helm_chart,wiki,system,wp,gitea}
                        If the repo argument is one word, specifies where to
                        look up the project. The default is via internal
                        lookup or GitHub Search
  -y, --assumeyes       Automatically answer yes for all questions
  --version             show program's version number and exit
```

The `--format` will affect what kind of information from the last release and in which format will
 be displayed, e.g.:

*   `version` is the default. Simply outputs well-formatted version number of the latest release

*   `assets` will output a newline-separated list of assets URLs (if any), otherwise link to
    sources archive

*   `source` will output link to source archive, no matter if the release has some assets added

*   `json` can be used by external Python modules or for debugging, it is dict/JSON output of an API
    call that satisfied last version checks

*   `tag` will emit just the latest release's tag name, which useful if you're constructing download
    URL yourself or need the tag name otherwise

An asset is a downloadable file that typically represents an executable, or otherwise 
"ready to launch" project. It's what you see filed under formal releases, and is usually a compiled 
(for specific platform), program.

Source files, are either tarballs or zipballs of sources for the source code of release. 

You can display either assets or source URLs of the latest release, by passing the corresponding
 `--format flag`, e.g. `--format source`

You also simply pass `--source` instead of `--format source`, and `--assets` instead of 
`--format assets`, as in:

```bash
lastversion --assets mautic/mautic 
#> https://github.com/mautic/mautic/archive/2.15.1/mautic-2.15.1.tar.gz
```

By default, `lastversion` filters output of `--assets` to be OS-specific. Who needs `.exe` on Linux?

To override this behavior, you can use `--filter`, which has a regular expression as its argument.
To disable OS filtering, use `--filter .`, this will match everything.

You can naturally use `--filter` in place where you would use `grep`, e.g. 
`lastversion --assets --filter win REPO`

### Use case: Work with a multi-project repository

Sometimes a single repository actually hosts many components, and creates releases that
have separate version line for each component. 

To help `lastversion` get a component's version for such repos, use `--only` and `--exclude` 
switches.
They make `lastversion` look at only those releases which are tagged (or not) with specified 
strings.

[Example](https://github.com/lastversion-test-repos/autoscaler/tags):

```bash
lastversion --only chart https://github.com/lastversion-test-repos/autoscaler
```

The above will report `9.16.0`.

```bash
lastversion --exclude chart https://github.com/lastversion-test-repos/autoscaler
```

The above will report a non-chart latest version, `1.23.0`.

Useful for hard cases, you can pass in regular expressions for both arguments, by prepending them 
with tilde, like so:

```bash
lastversion --only '~-po.-' https://github.com/lastversion-test-repos/autoscaler
```

The above will consider only releases tagged with -po*d*-, or -po*v*-, etc.

### Use case: How to download the latest version of something

You can also use `lastversion` to download assets/sources for the latest release.

Download the most recent Mautic source release:

```bash
lastversion download mautic/mautic 
```
    
Customize downloaded filename (works only for sources, which is the default):

```bash
lastversion download mautic/mautic -o mautic.tar.gz
```

You can also directly fetch and extract the latest release's file into the current working directory 
by using `extract` command:

```bash
lastversion extract wordpress
```
    
You can have `lastversion` output sources/assets URLs and have those downloaded by 
something else:    

```bash
wget $(lastversion --assets mautic/mautic)
```

This will download all assets of the newest stable Mautic, which are 2 zip files.

How this works: `lastversion` outputs all asset URLs, each on a new line, and `wget` is smart 
enough to download each URL. Magic :)

For releases that have no assets added, it will download the source archive.  

To always download source, use `--source` instead:

```bash
wget $(lastversion --source mautic/mautic)  
```

### Use case: Download specific asset under specified filename

If you want to download specific asset of the last version's release and save the downloaded file
 under a desired name, combine `-d` option (for download name) and `--filter` for specifying assets 
 filter.

Example:

```bash
lastversion --pre Aircoookie/WLED --format assets --filter ESP32.bin -d ESP32.bin
```

### Use case: Get the last version (betas are fine)

We consider the latest release is the one that is stable / not marked as beta.
If you think otherwise, then pass `--pre` switch and if the latest version of repository is a 
pre-release, then you'll get its version instead:

```bash
lastversion --pre mautic/mautic 
#> 2.15.2b0
```
    
### Use case: version of a specific branch

For some projects, there may be several stable releases available simultaneously, in different
branches. An obvious example is PHP. You can use `--major` flag to specify the major release
version to match with, to help you find the latest stable release of a branch, like so:

```bash
lastversion php/php-src --major 7.2
``` 

This will give you current stable version of PHP 7.2.x, e.g. `7.2.28`.

Branch selector is easy to be specified after semicolon, and together with the search API,
a clean invocation for the same would be:

```bash
lastversion php:7.2
```

The branch selector can also be used to get specific release details, e.g.:

```bash
lastversion php:7.2.33 --assets
```

### Use case: releases with specific assets

Sometimes a project makes nice formal releases but delay in uploading assets for releases.
And you might be interested in specific asset type always.
Then you can make `lastversion` consider as latest only the last release with specific asset name.
Easy with the `--having-asset` switch:

```bash
lastversion telegramdesktop/tdesktop --having-asset "Linux 64 bit: Binary"
```

The argument value to `--having-asset` can be made as regular expression. For this, prepend it 
with tilde sign. E.g. to get releases with macOS installers:

```bash
lastversion telegramdesktop/tdesktop --having-asset "~\.dmg$"
```

You can pass no value to `--having-asset` at all. Then `lastversion` will only return the latest 
release which has **any** assets added to it:

```bash
lastversion telegramdesktop/tdesktop --having-asset
```

### Use case: version of an operating system

The operating systems are usually *not* versioned through GitHub releases or such.
It is a challenge to get the last stable version of an OS other than from its website,
or other announcement channels.

An easy compromise that `lastversion` does about this, is hard coding well-known OS names, and using
Wikipedia behind the scenes:

```bash 
lastversion rocky #> 8.4
lastversion windows #> 10.0.19043.1081
lastversion ios #> 14.6
```

You can supply a fully-qualified URL to a Wikipedia page for an OS/software project to get version
from there, e.g.:

```bash
lastversion https://en.wikipedia.org/wiki/Rocky_Linux #> 8.4
```

### Special use case: NGINX stable vs mainline branch version

```bash
lastversion https://nginx.org --major stable #> 1.16.1
lastversion https://nginx.org --major mainline #> 1.17.9
```
    
Behind the scenes, this checks with `hg.nginx.org` which is a Mercurial web repo.
Those are supported as well, e.g.

```bash
lastversion https://hg.example.com/project/
```
    
Mercurial repositories are rather rare these days, but support has been added primarily for NGINX.

### Special use case: find the release of a PyPI project

Most Python libraries/apps are hosted on PyPI. To check versions of a project on PyPI, you can use:

```bash
lastversion https://pypi.org/project/requests/
```

If you prefer using a shorter repo name, ensure `--at pip` switch, like so:

```bash
lastversion requests --at pip
```

### Install an RPM asset

If a project provides `.rpm` assets and your system has `yum` or `dnf`, you can install the project's
 RPM directly, like so:

```bash
sudo lastversion install mailspring
```
 
This finds [MailSpring](https://github.com/Foundry376/Mailspring), gets its latest release info, 
filters assets for `.rpm` and passes it to `yum` / `dnf`. 

You can even set up an auto-updater cron job which will ensure you are on the latest version of a
 package, like so:
 
```bash
@daily /usr/bin/lastversion install mailspring -y 2>/dev/null
```

If the Mailspring GitHub repo posts a release with newer `.rpm`, then it will be automatically
 installed, making sure you are running the latest and greatest Mailspring version.
  
You'll even get an email alert after update (standard cron feature).

Needless to say, more often than not such RPM packages have no idea about all potentially missing
dependencies. Thus, only use `lastversion install ...` if the software is missing from the base
`yum` repositories.

### Install an AppImage

If a project provides `.AppImage`, you can install those directly using `lastversion`.
The `AppImage` is self-contained Linux executable file. What `lastversion` does for you, is fetch
the latest release's `AppImage`, installs it under `~/Applications/<app>` and makes it executable.
Just run:

```bash
lastversion install fluent-reader
```

### Test version parser

The `test` command can be used for troubleshooting or simply well formatting a string with version:

```bash
lastversion test 'blah-1.2.3-devel' # > 1.2.3.dev0
lastversion test '1.2.x' # > False (no clear version)
lastversion test '1.2.3-rc1' # > 1.2.3rc1
```

### Scripting with `lastversion` in `bash`

#### Semantic versioning support

Sometimes you only want to check updates for a specific semantic versioning level.
Does a project have a new minor release? Does a project have a new major release?
To print just the necessary semantic versioning base, use `--sem` option.

Acceptable values are `major`, `minor`, and `patch`.

```bash
lastversion wordpress --sem major
#> 5
```

```bash
lastversion wordpress --sem minor
#> 5.9
```

```bash
lastversion wordpress --sem patch
#> 5.9.3
```

The value `--sem patch` can be used to *normalize* a given result to semantic versioning,
if a project doesn't follow the semantics strictly. E.g. sometimes WordPress would publish an x.y
release while it's implicitly x.y.0. So let's say WordPress released "5.10":

```bash
lastversion wordpress --sem patch
#> 5.10.0
```

#### Format any version string

Say you ran `mysqld --version` and got this output:

> mysqld  Ver 5.6.51-91.0 for Linux on x86_64 (Percona Server (GPL), Release 91.0, Revision b59139e)

This is rather hard to parse in bash if you want to just extract the major MySQL server version.

`lastversion` can easily parse out and give the desired information based on desired semantic 
versioning level:

```bash
lastversion --sem major format "mysqld  Ver 5.6.51-91.0 for Linux on x86_64 (Percona Server (GPL) , Release 91.0, Revision b59139e)" 
#> 5
```

#### Compare arbitrary versions

Use `lastversion` for easy comparison of versions on the command line.
Compare two versions, the command will output the highest version:

```bash
lastversion 1.2.3 -gt 1.2.4
#> 1.2.4
```

See the exit codes below, to find whether the first argument is a higher version, or the second.

The `--sem` option described earlier will affect both what's being printed and what semantic
versioning base level is being compared, thus the result.

#### Check for NEW release

When you're building some upstream package, and you did this before, there is a known "last build" 
version.
Automatic builds become easy with:

```bash
CURRENTLY_BUILT_VER=1.2.3 # stored somewhere, e.g. spec file in my case
LASTVER=$(lastversion repo/owner -gt ${CURRENTLY_BUILT_VER})
if [[ $? -eq 0 ]]; then
  # LASTVER is newer, update and trigger build
  # ....
fi
```

Here, the `-gt` is actually a switch passed to `lastversion`, which acts in a similar fashion to
 `-gt` comparison in bash.

There is more to it, if you want to make this reliable.
See my ranting on 
[RPM auto-builds with `lastversion`](https://github.com/dvershinin/lastversion/wiki/Use-in-RPM-building)

#### Check if there is a newer kernel for your Linux machine

```bash
LATEST_KERNEL=$(lastversion linux -gt $(uname -r | cut -d '-' -f 1))
if [[ $? -eq 0 ]]; then
  echo "I better update my kernel now, because ${LATEST_KERNEL} is there"
else 
  echo "My kernel is latest and greatest."
fi 
```  

#### Exit Status codes

Exit status codes are the usual means of communicating a command's execution success or failure. 
So `lastversion` follows this: successful command returns `0` while anything else is an error of 
some kind.
For example, when the latest stable release version if found, `0` is returned.
`0` is also returned for `-gt` comparison when leftmost argument is newer than rightmost argument.
 
Exit status code `1` is returned for cases like no release tag existing for repository at all, or 
repository does not exist.

Exit status code `2` is returned for `-gt` version comparison negative lookup, that is when rightmost argument is newer
than leftmost argument.

Exit status code `3` is returned when filtering assets of last release yields empty URL set 
(no match)

## Tips

Getting the latest version is heavy on the API, because GitHub does not allow to fetch tags in 
chronological order, and some repositories switch from one version format to another, so *we can't 
just consider the highest version to be latest*.
We have to fetch every tag's commit date, and see if it's actually more recent. Thus, it's slower
with larger repositories, which have potentially a lot of tags.

Thus, `lastversion` makes use of caching API response to be fast and light on GitHub API,
It does conditional ETag validation, which, as per GitHub API will not count towards rate limit.
The cache is stored in `~/.cache/lastversion` on Linux systems.

It is *much recommended* to set up your [GitHub API token](https://github.com/settings/tokens).
Bare API token is enough, you may deselect all permissions. 
You can then increase your rate limit by adding the following `~/.bashrc` file:

```bash
export GITHUB_API_TOKEN=xxxxxxxxxxxxxxx
```

You can use either `GITHUB_API_TOKEN` or `GITHUB_TOKEN` environment variable.
The former has priority.
    
For GitLab, you can use a
[Personal Access Token](https://docs.gitlab.com/ee/user/profile/personal_access_tokens.html):

```bash
export GITLAB_PA_TOKEN=xxxxxxxxxxxxxxx
```

Then run `source ~/.bashrc`. After this, `lastversion` will use it to get larger API calls allowance
from GitHub.

## Usage in a Python module

You can use `lastversion.has_update(...)` to find whether an update for existing version of
 something is available, simply:

```python
from lastversion import has_update
latest_version = has_update(repo="mautic/mautic", current_version='1.2.3')
if latest_version:
    print(f'Newer Mautic version is available: {latest_version}')
else:
    print('No update is available')
```

The `lastversion.has_update(...)` function accepts any URL from a repository (or its short name
, e.g. `owner/name`) and you should pass an existing/current version.

If you are checking version of a project on PyPi, supply an additional `at='pip'` argument,
in order to avoid passing the full PyPI URI of a project, and remove ambiguity with GitHub hosted
 projects. For example, checking for newer Requests
library:

```python
from lastversion import has_update
latest_version = has_update(repo="requests", at='pip', current_version='1.2.3')
if latest_version:
    print('Newer Requests library is available: {latest_version}')
else:
    print('No update is available')
```

The `has_update` function returns either:

*   The [Version](https://packaging.pypa.io/en/latest/version.html#packaging.version.Version) object
*   `False` if there is no newer version than the one given

Alternatively, invoke `lastversion.latest(...)` function to get the latest version information
 for a repo.  
 
```python
from lastversion import latest
from packaging import version

latest_mautic_version = latest("mautic/mautic", output_format='version', pre_ok=True)

print(f'Latest Mautic version: {latest_mautic_version}')

if latest_mautic_version >= version.parse('1.8.1'):
    print('It is newer')
```

With `output_format='version'` (the default), the function returns a 
[Version](https://packaging.pypa.io/en/latest/version.html#packaging.version.Version) object, or
 `None`. So you can do things like above, namely version comparison, checking dev status, etc.
 
With `output_format='dict'`, a dictionary returned with the latest release information, or `False`.
The dictionary keys vary between different project locations (GitHub vs BitBucket, for example),
but are guaranteed to always have these keys:

*   `version`: [Version](https://packaging.pypa.io/en/latest/version.html#packaging.version.Version) 
 object, contains the found release version, e.g. `1.2.3`
*   `source`: string, the identifier of the project source, e.g. `github`, or `gitlab`
*   `tag_date`: datetime object, the release date, e.g. `2020-12-15 14:41:39`
*   `from`: string, contains fully qualified URL of the project
*   `tag_name`: string, version control tag name corresponding to the release

The `lastversion.latest` function accepts 3 arguments

*   `repo`, in format of `<owner>/<name>`, or any URL under this repository, e.g. `https://github.com/dvershinin/lastversion/issues`   
*   `format`, which accepts the same values as when you run `lastversion` interactively, as well as
 `dict` to return a dictionary as described above
*   `pre_ok`, boolean for whether to include pre-releases as potential versions
*   `at`, specifies project location when using one-word repo names, one of 
 `github`, `gitlab`, `bitbucket`, `pip`, `hg`, `sf`, `website-feed`, `local`

## Using in Continuous Integration

You can also use `lastversion` directly in your GitHub action workflows, 
with [`lastversion-action`](https://github.com/dvershinin/lastversion-action).

## Sponsored Message

**GetPageSpeed RPM Repository**: Enhance your server performance with our NGINX modules and performance tools. Visit [GetPageSpeed.com](https://www.getpagespeed.com/) to learn more and subscribe for access.


[![DeepSource](https://static.deepsource.io/deepsource-badge-light.svg)](https://deepsource.io/gh/dvershinin/lastversion/?ref=repository-badge)
