# lastversion

[![Build Status](https://travis-ci.org/dvershinin/lastversion.svg?branch=master)](https://travis-ci.org/dvershinin/lastversion)
[![PyPI version](https://badge.fury.io/py/lastversion.svg)](https://badge.fury.io/py/lastversion)
[![Codacy Badge](https://api.codacy.com/project/badge/Grade/380e3a38dc524112b4dcfc0492d5b816)](https://www.codacy.com/manual/GetPageSpeed/lastversion?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=dvershinin/lastversion&amp;utm_campaign=Badge_Grade)

A tiny command-line utility that helps to answer one simple question:

> What is the latest *stable* version for a GitHub project?

... and, optionally, download it.

GitHub has an API endpoint [here](https://developer.github.com/v3/repos/releases/#get-the-latest-release). But if you're here, then you know how it sucks:

A release would show up in this API response *only* if it was filed formally using the GitHub release interface.
Sometimes project authors use formal releases, and next thing you know, for the next release they won't.
There is no consistency in human beings.

OK, you think you could use another API endpoint to [list tags](https://developer.github.com/v3/repos/#list-tags).
Tags *usually* represent a release, however, the API does not sort them chronologically. 
Moreover, you might get something like "latest-stable" for a tag name's value.

In general, quite many project authors complicate things further by:

*   Creating a formal release that is clearly a Release Candidate (`rc` in tag), but forget to mark it as a pre-release
*   Putting extraneous text in release tag e.g. `release-1.2.3` or `name-1.2.3-2019` anything fancy like that
*   Putting or not putting the `v` prefix inside release tags. Today yes, tomorrow not. I'm not
 consistent about it myself :)
*   Switching from one version format to another, e.g. `v20150121` to `v2.0.1`

To deal with all this mess and simply get well-formatted, last *stable* version (or download URL!) on the command line, you can use `lastversion`.

Its primary use is for build systems - whenever you want to watch specific repositories for released versions to build packages automatically.
Or otherwise require getting latest version in your automation scripts.

[Like I do](https://www.getpagespeed.com/redhat)

`lastversion` does a little bit of AI to detect if releasers mistakenly filed a beta version as a stable release.
It uses both of the API endpoints and incorporates logic for cleaning up human inconsistency from version information.

## Synopsis

    lastversion apache/incubator-pagespeed-ngx #> 1.13.35.2
    lastversion apache/incubator-pagespeed-ngx -d #> downloaded incubator-pagespeed-ngx-v1.13.35.2-stable.tar.gz
    lastversion apache/incubator-pagespeed-ngx -d pagespeed.tar.gz #> downloads with chosen filename

## Installation for CentOS/RHEL 7, 8

    sudo yum -y install https://extras.getpagespeed.com/release-latest.rpm
    sudo yum install lastversion
   
## Installation for other systems

Installing with `pip` is easiest:

    pip install lastversion
    
## Usage

 Typically, you would just pass a repository URL (or repo owner/name to it) as the only argument, e.g.:

    lastversion https://github.com/gperftools/gperftools

Equivalently accepted invocation with same output is:

    lastversion gperftools/gperftools    

If you're lazy to even copy paste a project's URL, you can just type its name as argument, which will use repository search API (slower).
Helps to answer what is the latest Linux version:

    lastversion linux     

Or wondering what is the latest version of Wordpress? :

    lastversion wordpress
   
A special value of `self` for the main argument, will lookup the last release of `lastversion` itself.

For more options to control output or behavior, see `--help` output:    

    usage: lastversion [-h] [--pre] [--verbose] [-d [DOWNLOAD]]
                       [--format {version,assets,source,json}] [--assets]
                       [--source] [--version] [-gt VER] [-b MAJOR]
                       [--filter REGEX] [-su]
                       REPO
    
    Get latest release from GitHub.
    
    positional arguments:
      REPO                  GitHub repository in format owner/name
    
    optional arguments:
      -h, --help            show this help message and exit
      --pre                 Include pre-releases in potential versions
      --verbose
      -d [DOWNLOAD], --download [DOWNLOAD]
      --format {version,assets,source,json}
                            Output format
      --assets              Returns assets download URLs for last release
      --source              Returns only source URL for last release
      --version             show program's version number and exit
      -gt VER, --newer-than VER
                            Output only if last version is newer than given
                            version
      -b MAJOR, --major MAJOR
                            Only consider releases of specific major version, e.g.
                            2.1.x
      --filter REGEX        Filters --assets result by a regular expression
      -su, --shorter-urls   A tiny bit shorter URLs produced


The `--format` will affect what kind of information from last release and in which format will be displayed, e.g.:

*   `version` is the default. Just outputs well format version number
*   `assets` will output newline-separated list of assets URLs (if any), otherwise link to sources archive
*   `source` will output link to source archive, no matter if the release has some assets added
*   `json` can be used by external Python modules or for debugging, it is dict/JSON output of an API
 call that satisfied last version checks

You can use shortcuts `--source` instead of `--format source`, and `--assets` instead of `--format assets`, as in the above examples.

    lastversion --source mautic/mautic #> https://github.com/mautic/mautic/archive/2.15.1/mautic-2.15.1.tar.gz

By default, `lastversion` filters output of `--assets` to be OS specific. Who needs `.exe` on Linux?

To override this behavior, you can use `--filter`, which has a regular expression as its argument.
To disable OS filtering, use `--filter .`, this will match everything.

You can naturally use `--filter` in place where you would use `grep`, e.g. `lastversion --assets --filter win REPO`

### Use case: How to download latest version of something     

You can also use `lastversion` to download assets/sources for the latest release.

Download the most recent Mautic:

    lastversion mautic/mautic --download 
    
Customize downloaded filename (works only for sources, which is the default):

    lastversion mautic/mautic --download mautic.tar.gz
    
Or you can just have `lastversion` output sources/assets URLs and have those downloaded by something else:    

    wget $(lastversion --assets mautic/mautic)

This will download all assets of the newest stable Mautic, which are 2 zip files.

How this works: `lastversion` outputs all asset URLs, each on a new line, and `wget` is smart enough to download each URL. Magic :)

For releases which have no assets added, it will download source archive.  

To always download source, use `--source` instead:

    wget $(lastversion --source mautic/mautic)  

An asset is a downloadable file that typically represents an executable, or otherwise "ready to launch" project. It's what you see filed under formal releases, and is usually a compiled (for specific platform), program.

Source files, are either tarballs or zipballs of sources for the source code of release. 

### Use case: Get last version (betas are fine)

We consider latest release is the one which is stable / not marked as beta.
If you think otherwise, then pass `--pre` switch and if the latest version of repository is a pre-release, then you'll get its version instead:

    lastversion --pre mautic/mautic #> 2.15.2b0
    
### Use case: version of a specific branch

For some projects, there may be several stable releases available simultaneously, in different
branches. An obvious example is PHP. You can use `--major` flag to specify the major release
version to match with, to help you find latest stable release of a branch, like so:

    lastversion php/php-src --major 7.2 

This will give you current stable version of PHP 7.2.x, e.g. `7.2.28`.

### Test version parser

The `test` command can be used for troubleshooting or simply well formatting a string with version:

    lastversion test 'blah-1.2.3-devel' # > 1.2.3.dev0
    lastversion test '1.2.x' # > False (no clear version)
    lastversion test '1.2.3-rc1' # > 1.2.3rc1

### Scripting with lastversion

#### Check for NEW release

When you're building some upstream package, and you did this before, there is a known "last build" version.
Automatic builds become easy with:

    CURRENTLY_BUILT_VER=1.2.3 # stored somewhere, e.g. spec file in my case
    LASTVER=$(lastversion repo/owner -gt $CURRENTLY_BUILT_VER)
    if [ $? -eq 0 ]; then
      # LASTVER is newer, update and trigger build
      ....


There is more to it, if you want to make this reliable.
See my ranting on [RPM auto-builds with `lastversion`](https://github.com/dvershinin/lastversion/wiki/Use-in-RPM-building)

#### Exit Status codes

Exit status codes are the usual means of communicating a command's execution success or failure. 
So `lastversion` follows this: successful command returns `0` while anything else is an error of some kind:
 
Exit status code `1` is returned for cases like no release tag existing for repository at all, or repository does not exist.

Exit status code `2` is returned for `-gt` version comparison negative lookup.

Exit status code `3` is returned when filtering assets of last release yields empty URL set (no match)

## Tips

Getting latest version is heavy on the API, because GitHub does not allow to fetch tags in chronological order, 
and some repositories switch from one version format to another, so *we can't just consider highest version to be latest*.
We have to fetch every tag's commit date, and see if it's actually more recent. Thus it's slower with larger repositories, 
which have potentially a lot of tags.

Thus, `lastversion` makes use of caching API response to be fast and light on GitHub API,
It does conditional ETag validation, which, as per GitHub API will not count towards rate limit.
The cache is stored in `~/.cache/lastversion` on Linux systems.

It is *much recommended* to setup your [GitHub API token](https://github.com/settings/tokens) in `~/.bashrc` like this, to increase your rate limit:

    export GITHUB_API_TOKEN=xxxxxxxxxxxxxxx

Then run `source ~/.bashrc`. After this, `lastversion` will use it to get larger API calls allowance from GitHub.

## Usage in a Python module

    from lastversion import lastversion
    repo = "mautic/mautic"
    lastVersion = lastversion.latest(repo, 'version', True)
    print(lastVersion)

Will yield: `2.15.2b0`.

The `lastversion.latest` function accepts 3 arguments

*   `repo`, in format of `<owner>/<name>`, or any URL under this repository, e.g. `https://github.com/dvershinin/lastversion/issues`   
*   `format`, which accepts same values as when you run `lastversion` interactively
*   `pre_ok`, boolean for whether to include pre-releases as potential versions

### Check if there is a newer kernel for your Linux machine

```bash
LATEST_KERNEL=$(lastversion linux -gt $(uname -r | cut -d '-' -f 1))
if [[ $? -eq 0 ]]; then
  echo "I better update my kernel now, because ${LATEST_KERNEL} is there"
else 
  echo "My kernel is latest and greatest."
fi 
```  

[![DeepSource](https://static.deepsource.io/deepsource-badge-light.svg)](https://deepsource.io/gh/dvershinin/lastversion/?ref=repository-badge)