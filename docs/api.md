---
title: "Public API"
description: "Use lastversion via a free public API endpoint, or the RapidAPI-backed commercial API for higher limits, stability, and more endpoints."
---

## `lastversion` public API

You don't need to use `lastversion` as a command line tool or install it as a
package to use it.

You can consume `lastversion` functionality through **two** API offerings:

1. **Free Public API** at `lastversion-api.getpagespeed.com`
2. **Production-Ready Commercial API** on [RapidAPI](https://rapidapi.com/ciapnz/api/lastversion)

### 1. Public API (Limited, Best for Small Usage)

**Free API has Limited SLA and Rate Limits:** It’s free, so heavier usage or production traffic may see performance
or reliability constraints. For use in automated workflows, we highly recommend the commercial API below.

For casual or small usage scenarios, you can directly query this free public endpoint:

    https://lastversion-api.getpagespeed.com/<github-repo>

Make a GET request to the endpoint to get the latest version of the repository in JSON format.

To get only the version number, append `?version` to the URL.

Examples:

* [https://lastversion-api.getpagespeed.com/dvershinin/lastversion](https://lastversion-api.getpagespeed.com/dvershinin/lastversion)
* [https://lastversion-api.getpagespeed.com/dvershinin/lastversion?version](https://lastversion-api.getpagespeed.com/dvershinin/lastversion?version)

Note that API caches results for 2 hours.

For faster updates of your own project, please set up a webhook for your
GitHub repo that points to:

    https://lastversion-api.getpagespeed.com/hooks/github

#### Badges with the latest version

You can use the following badges in your project's `README.md` to show the latest version of your project:

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

### 2. Production-Ready Commercial API on RapidAPI

Subscribe to the commercial API on RapidAPI for higher rate limits, guaranteed performance, or advanced features:
 [lastversion API on RapidAPI](https://rapidapi.com/ciapnz/api/lastversion)

Users of the lastversion API on RapidAPI benefit from:

* Higher rate limits and guaranteed performance
* Flexible Endpoints: Fetch just the `version`, list of `assets`, or full release details via different routes.
* Scalable Billing Plans: **Start free**, upgrade as your usage grows.
* Stability for Production: guaranteed uptime and no 2-hour forced cache if you need fresh data.

Secure your requests with API Keys provided by RapidAPI.

* Header Name: `X-RapidAPI-Key`
* Required: Yes

📌 **Endpoints**

* `/version?project=project_id` returns JSON with the version string, corresponding to the latest release
* `/source?project=project_id` returns JSON with URL to download source tarball corresponding to the latest release
* `/assets?project=project_id` returns JSON URLs corresponding to downloadable executable or other assets for the latest release
* `/release?project=project_id` returns JSON with various information about the latest release with mandatory `version` field

The `project_id` can be a single identifier like `linux` or `nginx` or a GitHub repository name, or you can even supply a URL where a project is hosted.

📌 **Text Endpoints**

* `/text/version?project=project_id` returns only text with the version string, corresponding to the latest release.
* `/text/source?project=project_id` returns only text with the URL to download source tarball corresponding to the latest release
* `/text/assets?project=project_id` returns only text with URLs corresponding to downloadable executable or other assets for the latest release

**Example Requests**:

Fetch NGINX Latest Version (GET):

```
curl -X GET "https://lastversion.p.rapidapi.com/release?project=nginx" \
     -H "X-RapidAPI-Key: YOUR_RAPIDAPI_KEY" \
     -H "X-RapidAPI-Host: lastversion.p.rapidapi.com"
```

Response:

```
{
  "version": "1.27.3",
  "type": "release",
  ...
}
```

If you want to get just the version, use the `/text/version` endpoint URL.


Fetch Linux Latest Version (GET) with Version Only:

```
curl -X GET "https://lastversion.p.rapidapi.com/text/version?project=torvalds/linux" \
     -H "X-RapidAPI-Key: YOUR_RAPIDAPI_KEY" \
     -H "X-RapidAPI-Host: lastversion.p.rapidapi.com"
```

Response: `6.12`

Every endpoint supports `major` parameter, allowing you to answer questions like:

&gt; What was the last 4.x Linux version?

```
curl -X GET "https://lastversion.p.rapidapi.com/text/version?project=torvalds/linux&major=4" \
     -H "X-RapidAPI-Key: YOUR_RAPIDAPI_KEY" \
     -H "X-RapidAPI-Host: lastversion.p.rapidapi.com"
```

Response: `4.20`

Fetch the latest release data of WordPress:

```
curl -X GET "https://lastversion.p.rapidapi.com/release?project=WordPress/WordPress" \
     -H "X-RapidAPI-Key: YOUR_RAPIDAPI_KEY" \
     -H "X-RapidAPI-Host: lastversion.p.rapidapi.com"
```

Response will include `version:` field as well as a lot of other useful information about the latest release.

Fetch download URL of the latest WordPress:

```
curl -X GET "https://lastversion.p.rapidapi.com/source?project=WordPress/WordPress" \
     -H "X-RapidAPI-Key: YOUR_RAPIDAPI_KEY" \
     -H "X-RapidAPI-Host: lastversion.p.rapidapi.com"
```

Response: `https://github.com/WordPress/WordPress/archive/6.7.1/WordPress-6.7.1.tar.gz`

The creative and useful application of this API is in fact unlimited, when you pair it with external tools like `curl` or `wget`.

For example, download the latest WordPress release:

```bash
wget $(curl -X GET "https://lastversion.p.rapidapi.com/text/source?project=WordPress/WordPress" -H "X-RapidAPI-Key: YOUR_RAPIDAPI_KEY" -H "X-RapidAPI-Host: lastversion.p.rapidapi.com")
```
