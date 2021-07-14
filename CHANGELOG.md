# Changelog
All notable changes to this project will be documented in this file.

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
* Use feeds where available, thus much much faster while still precise
* Ability to pass `.yml` with `repo:` value inside. Other elements are merged into `--format json` 
output. More on the [wiki](https://github.com/dvershinin/lastversion/wiki/Use-in-automatic-RPM-building) 
on how useful it is
