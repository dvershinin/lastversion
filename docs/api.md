## `lastversion` public API

You don't need to use `lastversion` as a command line tool or install it as a 
package to use it. You can use the public web API at `lastversion-api.getpagespeed.com`.

### Usage

Make a GET request to `https://lastversion-api.getpagespeed.com/<github-repo>` to get the latest version of the repository in JSON format.

To get only the version number, append `?output_format=version` to the URL.

Examples:

* https://lastversion-api.getpagespeed.com/dvershinin/lastversion

Note that API caches results for 2 hours.

## Badges with the latest version

You can use the following badges in your project's `README.md` to show the latest version of your project:

### For GitHub projects

```markdown
![Dynamic JSON Badge](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Flastversion-api.getpagespeed.com%2Fdvershinin%2Flastversion&query=version&label=Release)
```

Just replace `dvershinin` and `lastversion` with your GitHub username and repository name.

The result will look like this:

![Dynamic JSON Badge](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Flastversion-api.getpagespeed.com%2Fdvershinin%2Flastversion&query=version&label=Release)

Alternatively, head to [Shields.io dynamic page configurator](https://shields.io/badges/dynamic-json-badge):

* Set URL to `https://lastversion-api.getpagespeed.com/<your-github-user>/<your-github-repo>`
* Set query to `version`
* Set label to `Release` or whatever you want, and set other settings as desired.

Click `Execute` to verify results and copy Markdown or desired format.
