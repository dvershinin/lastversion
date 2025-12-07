`lastversion` is capable of directly updating RPM .spec files with the latest release version:

```bash
lastversion foo.spec
```

It will update your .spec file with the newer project version, if available.

This feature allows creating an easy automation for rebuilding package updates.
You can set up a simple build pipeline via e.g. cron, to automatically build packages for new
 versions.

In general, you may not have to do any special changes in your `.spec` files. `lastversion` will
 look at the `URL:` tag and check the latest release from that location, and update the `Version:` 
 tag if a more recent version is found.

However, if you are working with projects hosted on GitHub, it is highly recommended to prepare
 your `.spec` files in a special way.
 
The recommended changes below will allow `lastversion` to work with your `.spec` file and discover
 the GitHub repository in question, the current version *and* release tag. The release tag is very
  important to be part of your build, because it helps to avoid breaking builds.
 
## lastversion-friendly spec changes

There are only a couple of modifications you must make to your `.spec` file in order to make it
 `lastversion` friendly.

### For GitHub projects

The header of the .spec file must have the following macros defined:

```rpmspec
%global upstream_github <repository owner>
```

The `%upstream_github` is static and defines the owner of a GitHub repository, e.g. for `google/brotli` repository, you will have:

```rpmspec
%global upstream_github google
```

`lastversion` constructs the complete GitHub repo name by looking at the values of the `upstream_github` macro and the `Name:` tag.
If the package name and GitHub repository `Name:` of your package do not match, then specify another global with the GitHub repo name:

```rpmspec
%global upstream_name brotli
```

When you run `lastversion foo.spec`, it will automatically add `lastversion_tag` and `lastversion_dir` macros. 
These globals, as well as `Version:` tag, are updated by `lastversion` with the proper values for the last release.

The `URL:` and `Source0:` tags of your spec file must be put to the following form:

```rpmspec
%global upstream_github <repository owner>
%global lastversion_tag x
%global lastversion_dir x
Name:           <name>
URL:            https://github.com/%{upstream_github}/%{name}
Source0:        %{url}/archive/%{lastversion_tag}/%{name}-%{lastversion_tag}.tar.gz
```

Finally, use `lastversion_dir` macro in the `%prep` section to properly specify extracted name directory:

Example:

```rpmspec
%prep
%autosetup -n %{lastversion_dir}
```

And reference it in the spec file appropriately, if needed.

These simple changes will guarantee that no matter what tag schemes the upstream uses, your new version builds will be successful!

### For non-GitHub projects

Specify `lastversion_repo` macro inside the spec file so that `lastversion` knows which project
to check for latest version and subsequently update the `Version:` tag for it.

Example:

```rpmspec
%global lastversion_repo monit
```

## Spec changes for module builds

When you build a *module* of software, slightly different spec changes are required. You can find the example under `tests/nginx-module-immutable`,
which is a spec file for building the immutable NGINX module

```rpmspec
#############################################
%global upstream_github GetPageSpeed
%global upstream_name ngx_immutable
#############################################
%global upstream_version x
############################################
```

Here, we defined `upstream_name` global, because the package name is `nginx-module-immutable` while the short name of the GitHub repo is `ngx_immutable`.

The notable change when building a module is an extra `upstream_version` macro. For module spec files, this is where `lastversion` will write the new version.
Your `Version:` tag will stay static between different versions, and must have the form that includes macros for the version of the parent software and the module, e.g.:

```rpmspec
%global upstream_version x  # <-- filled by `lastversion`
Version: %{nginx_version}+%{upstream_version}
```

Updating the parent software version is not in the scope of this article. But you can also use `lastversion` to e.g. create a `-devel` package where the parent software's version is written to the appropriate (in this case, `nginx_version`) macro.

## Specifying command-line arguments within `.spec` files

`lastversion` will read some `.spec` defined globals and treat them as command-line
arguments, including:

* `lastversion_having_asset` is treated same as `--having-asset` command line argument
* `lastversion_only` is treated same as `--only` command line argument
* `lastversion_major` is treated same as `--major` command line argument
* `lastversion_formal` when set to `1`, `true`, `yes`, or `on` is same as `--formal`
* `lastversion_sem` specifies semver constraint: `major`, `minor`, or `patch`

Example:

```rpmspec
%global lastversion_having_asset "Linux 64 bit: Binary"
```

In this example, "Linux 64 bit: Binary" is the asset name as it appears on 
GitHub release page.

### Semver constraints in spec files

You can specify a semver constraint directly in your spec file to control which 
version updates are allowed:

```rpmspec
%global upstream_github nginx
%global lastversion_sem patch    # Only allow patch updates (1.26.x → 1.26.y)

Name:    nginx
Version: 1.26.0
```

Valid values for `lastversion_sem`:

* `major` - allow any version update
* `minor` - only allow updates within the same major version (1.x.y → 1.z.w)
* `patch` - only allow patch updates within same minor version (1.2.x → 1.2.y)

When a newer version is found but violates the semver constraint, `lastversion` 
exits with code 4.
