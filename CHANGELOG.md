# Changelog
All notable changes to this project will be documented in this file.

## [3.4.3] - 2023-12-11
### Fixed
* Added `--formal` switch to allow for formal releases only

## [3.4.2] - 2023-12-10
### Fixed
* `--format source` did not include valid links
### Added
* `source_url` is now included in `--format json` output
* [Web API!](https://lastversion.getpagespeed.com/api/) Hooray! 

## [3.4.1] - 2023-12-07
### Fixed
* GitLab `--format json` failed when no assets were present

## [3.4.0] - 2023-12-02
### Added
* `lastversion_only` global is respected in `.spec` files
* `lastversion_having_asset` global is respected in `.spec` files
### Fixed
* Reworked search across different project locations to be more consistent

## [3.3.2] - 2023-09-25
### Fixed
* Fix regression in semver preference

## [3.3.1] - 2023-09-22
### Fixed
* Fixed AppImage installation #107

## [3.3.0] - 2023-09-19
### Added
* Ability to fetch `--source` URLs for SourceForge projects

## [3.1.2] - 2023-09-16
### Fixed
* Fixed AppImage installation #107

## [3.1.2] - 2023-09-16
### Fixed
* Fixed AppImage installation #107

## [3.1.1] - 2023-09-16
### Changed
* Some code refactoring and better identifying of pre-releases

## [3.1.1] - 2023-09-14
### Changed
* GitHub: when a semver version is detected, it is now used as a constraint #109

## [3.0.1] - 2023-07-15
### Changed
* Relaxed CacheControl dependency versions constraints
* Fixed "1.2.3-alpha" unnumbered pre-release detection

## [3.0.0] - 2023-06-22
### Changed
* Python 2 no longer supported
### Fixed
* Wrong version parsing with number in name #102
* 90+ versions that look like dates triggered pre-release detection

## [2.4.15] - 2023-05-08
### Fixed
* Pinned some dependency versions to avoid breakage
* Removed unnecessary warnings

## [2.4.14] - 2023-04-24
### Fixed
* Fix URL encoded tag names #99

## [2.4.13] - 2023-03-28
### Fixed
* Downloading GitLab `--assets` is now possible
* Fixed `--exclude` option not working
* Fixes detecting of some pre-releases

## [2.4.12] - 2023-03-11
### Fixed
* Fixes an issue where release feed contains identical tag versions #92

## [2.4.11] - 2023-02-16
### Fixed
* Don't treat 0.0.90+ as pre-releases #90

## [2.4.10] - 2023-01-24
### Fixed
* Fatal failure regression from release 2.4.9 on some packaging library versions
* More intelligent search in GitLab tags

## [2.4.9] - 2023-01-22
### Added
* New `--even` switch to target software that uses odd/even versioning where even is stable
### Fixed
* Micro-releases 90+ are treated as non-stable versions (old Linux software)

## [2.4.8] - 2022-12-05
### Fixed
* Better detection of x86_64 arch for `install` command

## [2.4.7] - 2022-11-10
### Added
* Added quictls/openssl repo shortcut
* Updated `Accept:` API header reflecting current state of GitHub docs
### Fixed
* Use stars instead of best-match for GitHub repo search as it seems more consistent
* Minor optimization to GitHub repositories search

## [2.4.6] - 2022-10-26
### Added
* More licenses for matching to RPM license field #74
* Added quictls/openssl for special version handling

## [2.4.5] - 2022-05-22
### Added
* Officially supporting Gitea repos #73

## [2.4.4] - 2022-05-08
### Added
* Allow extracting version from an arbitrary string (CLI)

## [2.4.3] - 2022-04-29
### Fixed
* Allow using --at with any non-URL repository specifier

## [2.4.2] - 2022-04-10
### Fixed
* Detection of self-hosted GitLab via gitlab. subdomain

## [2.4.1] - 2022-04-10
### Fixed
* Fixed regression from previous release where `--tag` CLI failed

## [2.4.0] - 2022-04-09
### Added
* Added better semantic versioning support via `--sem` option

## [2.3.0] - 2022-04-05
### Fixed
* Removed unnecessary API calls, performance improvement

## [2.2.2] - 2022-03-18
### Fixed
* `rpmspec_license` failed output when no license

## [2.2.1] - 2022-02-27
### Added
* `--only` now accepts regex via `~` prefix and negation via `!` prefix
* new `--exclude` argument allows for negative filtering
* `dict` or `json` output: added `rpmspec_license` field

## [2.2.0] - 2022-02-27
### Added
* `unzip` command to extract project directly to the current directory

## [2.1.0] - 2022-02-23
### Added
* Several extra repo shortcuts: kodi for Kodi, sles for SUSE Enterprise 
* Refactored code so that caching can be better used
* Extra detection of beta via preview and early-access delimiters
* `--at wordpress` for WordPress plugins

## [2.0.1] - 2021-10-28
### Fixed
* GitHub has empty `releases.atom` in tag-only repos #63, #65
* Fix for some repos where `releases.atom` contains old releases only

## [2.0.0] - 2021-10-21
### Changed
* The "install" action operates against releases with respective assets #60
### Fixed
* The `releases.atom` w/o authorization, fixes behavior of GitHub returning empty feeds

## [1.6.0] - 2021-09-04
### Added
* For .spec file updates, look for URL: tag as well, to use as repo argument
* `--at system` will query last version from package managers
* Various performance optimizations

## [1.5.1] - 2021-08-07
### Added
* `--having-asset` accepts regular expression if tilde prepended
* For one-word repo argument, check word/word official GitHub repo first, then search

## [1.5.0] - 2021-08-06
### Added
* New `--having-asset` switch to consider only formal releases with given asset name
### Fixed
* Unnecessary parsing of repo argument as version (performance)

## [1.4.5] - 2021-07-16
### Fixed
* Fixed RPM builds rpmlint changelog-time-in-future by having changelog in UTC

## [1.4.4] - 2021-07-16
### Added
* Print latest version from .spec file every time

## [1.4.3] - 2021-07-16
### Fixed
* Fixed installation on some systems

## [1.4.2] - 2021-07-15
### Added
* Experimental: updating .spec files for RPM auto-builds #26

## [1.4.1] - 2021-07-08
### Fixed
* `--download` option works for asset downloads, as long as there is one asset

## [1.4.0] - 2021-06-27
### Added
* Now it's easy get OS versions. Just run `lastversion ubuntu` or something

## [1.3.5] - 2021-06-09
### Added
* Ability to parse/check Helm chart repository metadata #50
### Fixed
* Ensure the `--only` switch works consistently across different project hosting

## [1.3.4] - 2021-05-25
### Added
* Arbitrary versions comparison in CLI: `lastversion 1.2.3 -gt 1.2.4`
* `lastversion --version` reports available updates for `lastversion`
* Clean up cancelled download on Ctrl+C

## [1.3.3] - 2021-02-03
### Added
* More requests logging in `--verbose` mode
* Log failed feed parsing
* Raising `BadProjectError` from GraphQL find method if repo arg is invalid
### Fixed
* Work around GitHub servers' inconsistency with feed redirects #44
* Using all tags in GraphQL find method, instead of annotated only #44

## [1.3.2] - 2021-01-12
### Fixed
* GraphQL method for finding release tags was not reliable on repos
  with tags having no tagger field
* Strip all extraneous alphanumerics from beginning of tags to improve 
  detection

## [1.3.1] - 2021-01-17
### Added
* `output_format='dict` for the `lastversion.latest()` function
* Honour `GITHUB_TOKEN` env var in addition to `GITHUB_API_TOKEN`

## [1.3.0] - 2021-01-16
### Added
* `--at` switch (and function argument) to explicitly specify project provider 
* PyPI support

## [1.2.6] - 2021-01-13
### Fixed
* Ensure compatibility with older python packaging module found in CentOS 7

## [1.2.5] - 2021-01-12
### Fixed
* Version checks and output for odd non-semantic tags, e.g. 1.1.1i (OpenSSL)

## [1.2.4] - 2020-12-19
### Fixed
* Fixed waiting API quota reinstatement
* Cache info about non-existent GitHub repositories

## [1.2.3] - 2020-10-02
### Fixed
* Fixed `lastversion URL` introduced by regression from 1.2.1

## [1.2.2] - 2020-09-29
### Fixed
* `--format json` and `--format assets` work for Non-GitHub projects 

## [1.2.1] - 2020-09-29
### Added
* `lastversion repo:branch` syntax, e.g. `lastversion php:7.2` or `lastversion nginx:mainline`
### Fixed
* require feedparser version that works with Python 2

## [1.2.0] - 2020-09-06
### Added
* New switch `--only` allows filtering projects in repos with multiple actual projects
* Ability to sniff version from a software website which publishes releases in RSS/ATOM feeds #23
* Ability to sniff version by discovering GitHub repository links on a software website #23
### Fixed
* No longer messing with root logger, playing safe as a library (opt-in behavior when used as
 module)

## [1.1.8] - 2020-08-13
### Added
* Fixed up `--major` constraint to work more correctly
* Use GraphQL API (GitHub) when deep searching tags is required (faster `--major`)
* Paginate across tags when a release matching constraints is not present in the feed (GitHub) #12
* Simple Python interface for update checks: `lastversion.has_update(repo, current_version)`
* Various fixes

## [1.1.7] - 2020-08-07
### Added
* Aggregate older tags, up to one year, for better latest release detection (feed only)

## [1.1.6] - 2020-07-18
### Added
* General improvements for releases detection
* SourceForge projects support

## [1.1.5] - 2020-05-04
### Added
* Better detection of post-releases, e.g. Magento 2.3.4-p2 is the latest *stable* release for the
`--major 2.3.4`
* Added new `--format tag` switch to get just the latest release's tag name. Proven to be useful in
 some cases

## [1.1.4] - 2020-04-23
### Fixed
* Fixed detecting non-GitHub repos and known URLs
* Improved RPM install by checking with RPM db and avoiding unnecessary downloads absent updates

## [1.1.3] - 2020-04-15
### Fixed
* Show error when no repo found (no results from search)
* Added spec_tag_no_prefix to JSON output
* Returning Null for license when it doesn't exist at release tag

## [1.1.2] - 2020-04-04
### Fixed
* Require requests>=2.6.1 to compensate for cachecontrol bug

## [1.1.1] - 2020-03-31
### Fixed
* Do not output progressbar when downloading and no TTY available, e.g. for log output

## [1.1.0] - 2020-03-24
### Added
* Install action
* Progressbar for download action, when download size is known

## [1.0.1] - 2020-03-23
### Fixed
* Compatibility with older PyYAML

## [1.0.0] - 2020-03-23

### Changed
* BREAKING release for Python consumers:  
The `latest` Python function now returns `Version` object instead of string, by default

### Added

* `test` command to see how a given tag would be parsed as version:
`lastversion test 'release-3_0_2'`
* Limited GitLab support
* Limited Mercurial web repos support
* Limited BitBucket support
* Use feeds where available, thus much, much faster while still precise
* Ability to pass `.yml` with `repo:` value inside. Other elements are merged into `--format json` 
output. More on the [wiki](https://github.com/dvershinin/lastversion/wiki/Use-in-automatic-RPM-building) 
on how useful it is
