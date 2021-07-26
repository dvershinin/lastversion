`lastversion` is capable of directly updating RPM .spec files with the latest release version:

```bash
lastversion package-name.spec
```

This feature allows building an easy automation for rebuilding package updates.

There are only a couple of modifications you must make to your `.spec` file in order to make them `lastversion` friendly.

These changes will allow `lastversion` to work with your `.spec` file and discover the GitHub repository in question and the current version.

It will rewrite your spec file with a newer version when you run `lastversion foo.spec`.

This makes it easy to set up a simple build pipeline via e.g. cron, to automatically build packages for new versions.

## lastversion-friendly spec changes

### For GitHub projects

The header of the .spec file must have the following macros defined:

```rpmspec
%global upstream_github <repository owner>
%global lastversion_tag x
%global lastversion_dir x
```

The `%upstream_github` is static and defines the owner of a GitHub repository, e.g. for `google/brotli` repository, you will have:

```rpmspec
%global upstream_github brotli
```

`lastversion` constructs the complete GitHub repo name by looking at the values of the `upstream_github` macro and the `Name:` tag.
If the package name and GitHub repository `Name:` of your package do not match, then specify another global with the GitHub repo name:

```rpmspec
%global upstream_name brotli
```

The `lastversion_tag` and `lastversion_dir` macros are not static. 
These globals, as well as `Version:` tag, are be updated by `lastversion` with the proper values for the last release, whenever you run `lastversion foo.spec`.

The `URL:` and `Source0:` tags of your spec file must be put to the following form:

```rpmspec
URL:            https://github.com/%{upstream_github}/%{name}
Source0:        %{url}/archive/%{lastversion_tag}/%{name}-%{lastversion_tag}.tar.gz
```

Wherever in the `.spec` file you unpack the tarball and have to reference the extracted directory name, use `%{lastversion_dir}`.

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
%global lastversion_tag x
%global lastversion_dir x
%global upstream_version x
############################################
```

Here, we defined `upstream_name` global, because the package name is `nginx-module-immutable` while the short name of the GitHub repo is `ngx_immutable`.

The notable change when building a module is an extra `upstream_version` macro. For module spec files, this is where `lastversion` will write the new version.
Your `Version:` tag will stay static between different versions, and must have the form that includes macros for the version of the parent software and the module, e.g.:

```rpmspec
Version: %{nginx_version}+%{upstream_version}
```

Updating the parent software version is not in the scope of this article. But you can also use `lastversion` to e.g. create a `-devel` package where the parent software's version is written to the appropriate (in this case, `nginx_version`) macro.

