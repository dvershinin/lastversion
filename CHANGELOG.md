# Changelog
All notable changes to this project will be documented in this file.

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
