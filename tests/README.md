## Tests for `lastversion`

*   `libmozjpeg.spec` is used in a test where lastversion should *refuse* to update the spec file
even there is a newer version available. This is because we want to retain ABI compatibility for
existing builds, by default. In other words, if current package version is X.Y.Z (as currently in
 the .spec file), `lastversion` will only update the file with newer minor or patch versions of
  the major X version.

*  `brotli.spec` is a simple test where no initial version is set, and `lastversion` updates the
 file with the latest information. 
 In this test `lastversion` uses project as specified by `%upstream_github` macro and `Name:` tag.
The test succeeds when RPM file is successfully built from the updated spec.
 
*  `nginx=module-immutable.spec` is a test where no initial version is set, and `lastversion
` updates it with the correct information by detecting that this is a "module build" and using
 different macros for setting version information: `%upstream_version` instead of the `Version
 :` tag.
 In this test `lastversion` uses project as specified by `%upstream_github` and `%upstream_name
 ` macros, since the actual project name is `ngx_immutable` on GitHub. 
 
* `nginx.spec` is a test where initial version is set, and `lastversion`  updates it with the
 latest version. In this test `lastversion` discovers actual project from `%lastversion_repo
 ` within the spec file

* `test_lastversion.py` has all the Python module tests as well as some for CLI 