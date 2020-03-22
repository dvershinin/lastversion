* BREAKING release. Some flags may work differently, please double check/see below.
* Added test command to see how a given tag would be parsed as version:
`lastversion test 'release-3_0_2'`
* GitLab support
* Limited Mercurial web repos support
* Partial BitBucket support
* Use feeds where available, thus much much faster and still precise
* Ability to pass `.yml` with `repo:` value inside. Other elements are merged into `--format json` 
output.   
More on the wiki on how useful it is
* The `latest` Python function now returns `Version` object instead of string, by default