# Changelog
All notable changes to this project will be documented in this file.

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
