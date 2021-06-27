# lastversion

[![Build Status](https://travis-ci.org/dvershinin/lastversion.svg?branch=master)](https://travis-ci.org/dvershinin/lastversion)
[![PyPI version](https://badge.fury.io/py/lastversion.svg)](https://badge.fury.io/py/lastversion)
[![Documentation Status](https://readthedocs.org/projects/lastversion/badge/?version=latest)](https://lastversion.getpagespeed.com/en/latest/?badge=latest) 
[![Codacy Badge](https://api.codacy.com/project/badge/Grade/380e3a38dc524112b4dcfc0492d5b816)](https://www.codacy.com/manual/GetPageSpeed/lastversion?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=dvershinin/lastversion&amp;utm_campaign=Badge_Grade)

![Using lastversion in terminal](https://www.getpagespeed.com/img/lastversion.gif)

[English](README.md) | 简体中文

一个轻巧的命令行工具，帮助你下载或安装一个项目的稳定版本。

`lastversion` 可以从下面的网站找到一个项目的格式良好的最新版本：

*   [GitHub](https://github.com/dvershinin/lastversion/wiki/GitHub-specifics)
*   GitLab
*   BitBucket
*   PyPI
*   Mercurial
*   SourceForge
*   任何以 RSS/ATOM 订阅方式发布软件网站。

## 为什么需要 `lastversion`？

通常情况下，许多项目作者的一些做法会让我们难以寻找一个项目的最新版本。

*   发布一个候选版本的时候忘记将其标记为预发布版本，而是作为一个正式版本去发布。比如版本标签为 `v2.0.1-rc` 但是在发布时并未标记为预发布版本。
*   在版本标签中加入无关的文本，例如 `release-1.2.3` 或 `name-1.2.3-2019`，或者其它类似的文本。
*   版本标签是否带有 `v` 前缀？今天可能带，但明天可能就不带了。我也是这样的 :)。
*   切换到另一种版本标签格式，例如从 `v20150121` 切换到 `v2.0.1`。

人与人之间难以保持一致。

如果你要应对这种麻烦的情况，你可以使用 `lastversion`，它可以让你轻松地获取某个项目的格式良好的版本标签（或下载链接）。

`lastversion` 主要用于 build systems。无论何时，
你都可以用它获取某个项目的版本信息去自动构建你的 packages，
或者用于在你的脚本中获取某个项目的最新版本。

[就像我这么做](https://www.getpagespeed.com/redhat)

lastversion 使用了一小点 AI 以检测发布者是否将测试版误发布为稳定版，
也可以清理一些版本信息中那些带有发布者个性文本。

## 简介

```bash
lastversion apache/incubator-pagespeed-ngx 
#> 1.13.35.2

lastversion apache/incubator-pagespeed-ngx -d 
#> downloaded incubator-pagespeed-ngx-v1.13.35.2-stable.tar.gz

lastversion apache/incubator-pagespeed-ngx -d pagespeed.tar.gz 
#> downloads with chosen filename

lastversion https://transmissionbt.com/
#> 3.0
```

## 在 CentOS/RHEL 7, 8 或 Amazon Linux 2 上安装 `lastversion`

```bash
sudo yum -y install https://extras.getpagespeed.com/release-latest.rpm
sudo yum install lastversion
```
   
## 在其它系统上安装 `lastversion`

用 `pip` 安装是最简单的方法。

```bash
pip install lastversion
```
    
## 使用方法

一般来说，`lastversion` 只需要一个参数，即一个仓库的 URL（或 用户名/仓库名），例如：

```bash
lastversion https://github.com/gperftools/gperftools
```

与之等价的命令为

```bash
lastversion gperftools/gperftools
```    

如果你想偷懒，不想复制粘贴项目的 URL，
你可以直接使用项目的名字作为参数，这将会使用仓库搜索 API（速度比较慢）。

下面的这条命令可以让你知道 Linux 的最新版本。

```bash
lastversion linux
```

或者查询 Wordpress 的最新版本。

```bash
lastversion wordpress
```

`self` 是主参数中的一个特殊值，它可以查找 `lastversion` 的最新版本，例如：

```bash
lastversion self
```

你可以通过 `--help` 查看和输出控制（行为）相关的选项。 

```text
usage: lastversion [-h] [--pre] [--verbose] [-d [FILENAME]]
                   [--format {version,assets,source,json,tag}] [--assets]
                   [--source] [-gt VER] [-b MAJOR] [--only ONLY]
                   [--filter REGEX] [-su]
                   [--at {github,gitlab,bitbucket,pip,hg,sf,website-feed,local}]
                   [-y] [--version]
                   [action] <repo or URL>

Find the latest software release.

positional arguments:
  action                Special action to run, e.g. download, install, test
  <repo or URL>         GitHub/GitLab/BitBucket/etc. repository in format
                        owner/name or any URL that belongs to it

optional arguments:
  -h, --help            show this help message and exit
  --pre                 Include pre-releases in potential versions
  --verbose             Will give you an idea of what is happening under the hood
  -d [FILENAME], --download [FILENAME]
                        Download with custom filename
  --format {version,assets,source,json,tag}
                        Output format
  --assets              Returns assets download URLs for last release
  --source              Returns only source URL for last release
  -gt VER, --newer-than VER
                        Output only if last version is newer than given
                        version
  -b MAJOR, --major MAJOR, --branch MAJOR
                        Only consider releases of a specific major version,
                        e.g. 2.1.x
  --only ONLY           Only consider releases containing this text. Useful
                        for repos with multiple projects inside
  --filter REGEX        Filters --assets result by a regular expression
  -su, --shorter-urls   A tiny bit shorter URLs produced
  --at {github,gitlab,bitbucket,pip,hg,sf,website-feed,local}
                        If the repo argument is one word, specifies where to
                        look up the project. The default is via internal
                        lookup or GitHub Search
  -y, --assumeyes       Automatically answer yes for all questions
  --version             show program's version number and exit
```

`--format` 选项将会指定输出的信息的格式，这些信息是关于某个项目的最后一次发布的版本的信息。

*   `version` 为默认值，输出格式最新的，格式良好的版本号。
*   `assets` 会以换行分割的最新版本的 asset 的 URL（如果有多个 asset 的话），否则将为最新源码链接（通常为 *.tar.gz 或 *.zip）。
*   `source` 将输出最新源码的链接（通常为 *.tar.gz 或 *.zip），即使最新版本同时发布了其它的 asset。
*   `json` 可以被外部 Python 模块使用或用来调试，它是一个 API 的 dict/JSON 的输出，可以满足最后的版本检查。
*   `tag` 只输出最新版本的标签名。

`asset` 在本文是指一个可下载的文件，
一般为可执行文件。例如一个项目发布的时候会连带发布各个平台的可执行程序，让用户无需编译源代码即可使用。

你可以查看最新版本的 asset 或源代码文件的 URL 通过选择适当的 `--format flag`。

你也可以使用 `--source` 去代替 `--format source`，用 `--assets` 代替 `--format assets`，例如：

```bash
lastversion --assets mautic/mautic 
#> https://github.com/mautic/mautic/archive/2.15.1/mautic-2.15.1.tar.gz
```

默认情况下， `lastversion` 会根据不同的 OS 过滤掉一些 `--assets` 的输出。
在 Linux 上谁需要 `.exe` 呢？

你可以使用 `--filter` 来覆盖掉这一行为，
它使用一个正则表达式作为参数。
如果你不想根据 OS 过滤掉 asset，你可以直接使用 `--filter` 来匹配所有的asset。

你你可以很优雅地使用 `--filter` 来代替 `grep` 命令，例如：
```bash
lastversion --assets --filter win REPO
```

### 用例: 下载最新版本

你可以使用 `lastversion` 来下载最新版本的 asset 和源代码。

下载最新的 Mautic 源码：

```bash
lastversion mautic/mautic --download 
```
    
自定义下载的文件名（只对下载源代码有效并且此为默认设置）：

```bash
lastversion mautic/mautic --download mautic.tar.gz
```  

你也可以使用 `lastversion` 输出源代码或者 asset 的 URL 并下载它，例如：

```bash
wget $(lastversion --assets mautic/mautic)
```

上面这行命令会下载所有的最新的稳定版的 asset，即两个 `.zip` 文件。

为什么会这样能够？
因为 `lastversion` 会输出在两个 `.zip` 文件的 URL 并通过换行分割，`wget` 也很聪明地下载每行的 URL，很神奇吧 :)。

如果最新发布中没有 asset，则会直接下载源代码。

如果你只想下载源代码，你可以使用 `--source`，例如：
```bash
wget $(lastversion --source mautic/mautic)  
```

### 用例: 获取最新版本（含测试版）

`lastversion` 认为最新版本是稳定版本或者没有被标记为测试的版本。
如果你不这么认为，你可以使用 `--pre` 将预发布版本作为最新版。

```bash
lastversion --pre mautic/mautic 
#> 2.15.2b0
```

### 用例: 特定分支的版本

一些项目可能会一起在不同的分支上发布稳定版本，
典型的例子就是 PHP，你可以使用 `--major` 去指定某个主版本，例如：

```bash
lastversion php/php-src --major 7.2
``` 

这行命令会输出当前的 PHP 稳定的版本，其版本格式为 `7.2.x`。

你也可以使用下面这种简单的写法来达到几乎相同的效果，即在冒号后指定主版本。

```bash
lastversion php:7.2
```

你可以直接指定一个具体的版本，例如：

```bash
lastversion php:7.2.33 --assets
```

#### 特殊用例: NGINX 的稳定版（Stable）和主线版（Mainline）

```bash
lastversion https://nginx.org --major stable #> 1.16.1
lastversion https://nginx.org --major mainline #> 1.17.9
```

上面这行命令其实是检查 `hg.nginx.org`，它是一个 Mercurial 网络仓库。

下面这样也是可以的：

```bash
lastversion https://hg.example.com/project/
```

Mercurial 仓库现在比较少见，`lastversion` 支持它主要是为了 NGINX。

#### 特殊用例: 获取 PyPI 项目

大多数 Python 的库和应用程序都托管在 PyPI 上。要获取 PyPI 上项目的版本，你可以执行下面的命令。

```bash
lastversion https://pypi.org/project/requests/
```

如果您不想写太长的参数，只想写仓库名的话，可以使用`--at pip`，就像下面这样。

```bash
lastversion requests --at pip
```

### 安装 RPM 资源

如果一个项目提供 `.rpm` 资源且你的 OS 可以使用 `yum` 或 `dnf`，
你可以直接安装该项目的 RPM，就像下面这样：

```bash
sudo lastversion install mailspring
```

上面这行命令从 [MailSpring](https://github.com/Foundry376/Mailspring) 
的最新版本中找到 `.rpm` 并传递给 `yum` 或 `dnf`。

你甚至可以通过 cron 实现自动更新，这将确保你在某个包为最新版本，就像下面这样：
 
```bash
@daily /usr/bin/lastversion install mailspring -y 2>/dev/null
```

如果 MailSpring 的 Github 仓库发布了一个更新的 `.rpm`，
那么这个 `.rpm` 会被自动安装，以确保你的版本的最新的。

你甚至可以在更新完毕后收到邮件提醒（cron 的标准功能）。
  
不用说都知道，这种方式会导致我们不知道潜在的缺失的依赖。
所以，只有当 `yum` 库没有你所需要的东西的时候才使用 `lastversion install ...`。

### 测试「版本解析器」

`test` 命令可以用来排除故障或者简单地格式化一个版本标签。

```bash
lastversion test 'blah-1.2.3-devel' # > 1.2.3.dev0
lastversion test '1.2.x' # > False (no clear version)
lastversion test '1.2.3-rc1' # > 1.2.3rc1
```

### 在 `bash` 上用 `lastversion` 编写脚本

#### 检查更新

当你想要构建某个上游的包的时候，而且此时你也有这个包上次构建时的版本号，那么自动构建将会十分容易。

```bash
CURRENTLY_BUILT_VER=1.2.3 # 存储在其它位置比如文件中
LASTVER=$(lastversion repo/owner -gt ${CURRENTLY_BUILT_VER})
if [[ $? -eq 0 ]]; then
  # 检测到最新版本，触发构建流程。
  # ....
fi
```

注意，`-gt` 参数的功能类似于 `bash` 中的 `-gt` 比较。

还有更多内容，如果你想让这变得更靠谱的话，
请听我唠叨：
[RPM auto-builds with `lastversion`](https://github.com/dvershinin/lastversion/wiki/Use-in-RPM-building)

#### 检查你的 Linux 是否有更新的内核版本

```bash
LATEST_KERNEL=$(lastversion linux -gt $(uname -r | cut -d '-' -f 1))
if [[ $? -eq 0 ]]; then
  echo "I better update my kernel now, because ${LATEST_KERNEL} is there"
else 
  echo "My kernel is latest and greatest."
fi 
```  

#### 退出状态码

退出状态码是传递命令执行成功与否的常用手段。对于`lastversion` 来说，
如果命令执行成功则返回 `0`，其它返回值的含义：

返回值 `1` 代表仓库不存在或者没有发布过版本。

返回值 `2` 代表没有比 `-gt` 所指定的版本更新的版本。

返回值 `3` 代表 `--filter` 过滤掉了所有的 URL，即正则表达式没有匹配到任何 URL。

## 小贴士

通过 API 来获取最新版本很难，因为 Github API 不允许按照时间顺序获取 tag，
而且一些仓库会更换它的版本号格式，所以我们不能认为最高版本号代表着最新版本。

我们必须获取每个标签的提交日期，并检查它是否真的是最近提交的。
因此，对于大型仓库来说速度会比较慢，因为这些仓库可能有很多标签。

因此，`lastversion` 会缓存的 API 响应内容以提高响应速度，
它做了有条件的 ETag 验证，根据 GitHub API 的规定，ETag 验证不计入速率限制。
在 Linux 下缓存内容存储在 `~/.cache/lastversion`。

*建议*设置你的 [GitHub API token](https://github.com/settings/tokens)。
仅仅只需要 API token，你可以取消这个 Token 的所有权限，
然后你可以在 `~/.bashrc` 文件中添加下列内容来提升你的请求速度上限。

```bash
export GITHUB_API_TOKEN=xxxxxxxxxxxxxxx
```

`GITHUB_API_TOKEN` 和 `GITHUB_TOKEN` 这两个环境变量均可被识别，
且当两者同时存在时优先使用前者。
    
对于 GitLab, 你可以使用 
[Personal Access Token](https://docs.gitlab.com/ee/user/profile/personal_access_tokens.html):

```bash
export GITLAB_PA_TOKEN=xxxxxxxxxxxxxxx
```

然后运行 `source ~/.bashrc`，之后，`lastversion` 将会使用 TOKEN 来更快地调用 API。

## 在 Python 模块中的用法

你可以使用 `lastversion.has_update(...)` 来查找某个项目是否已经有更新。

```python
from lastversion import lastversion
latest_version = lastversion.has_update(repo="mautic/mautic", current_version='1.2.3')
if latest_version:
    print('Newer Mautic version is available: {}'.format(str(latest_version)))
else:
    print('No update is available')
```

`lastversion.has_update(...)` 函数接受一个仓库的 URL，或者形如 `用户名/仓库名` 这样的字符串，第二个参数为当前版本。

如果你要检查 PyPI 上的项目版本，请使用参数 `at='pip'`，
这样就不用传递一个完整的 PyPI 项目的 URL 了，并且避免错误地从其它平台如 Github 上获取信息。
下面的示例代码可以检查 `Requests` 最新的版本。

```python
from lastversion import lastversion
latest_version = lastversion.has_update(repo="requests", at='pip', current_version='1.2.3')
if latest_version:
    print('Newer Requests library is available: {}'.format(str(latest_version)))
else:
    print('No update is available')
```

然后它会返回下面的一个返回值：

*   [Version](https://packaging.pypa.io/en/latest/version.html#packaging.version.Version) 对象
*   `False` 如果没有更加新的版本

你也可以调用 `lastversion.latest(...)` 函数来获取最新版本的信息。
 
```python
from lastversion import lastversion
from packaging import version

latest_mautic_version = lastversion.latest("mautic/mautic", output_format='version', pre_ok=True)

print('Latest Mautic version: {}'.format(str(latest_mautic_version)))

if latest_mautic_version >= version.parse('1.8.1'):
    print('It is newer')
```
如果 `output_format='version'`（默认），函数会返回一个 
[Version](https://packaging.pypa.io/en/latest/version.html#packaging.version.Version) 对象
或者 `none`。所以你可以进行如版本比较等工作。

如果指定参数 `output_format='dict'`，
函数会返回一个 `dict`（字典）或 `False`，
如果函数从不同的平台（如 Github 和 BitBucket）获取同一个项目的版本信息，
那么字典的 `Key`（键）可能会不同，
但可以保证一定会有下列的 `Key`（键）。

*   `version`：[Version](https://packaging.pypa.io/en/latest/version.html#packaging.version.Version) 

 对象，包含被找到的版本，如 `1.2.3`。

*   `source`：字符串，表示来源平台, 如 `github` 或  `gitlab`。
*   `tag_date`：`datetime` 对象, 表示发布的时间，如 `2020-12-15 14:41:39`。
*   `from`：字符串, 项目的完整 URL。
*   `tag_name`：字符串，版本标签名。

`lastversion.latest` 函数接受三个参数

*   `repo`，仓库的 URL，或者形如 `用户名/仓库名` 这样的字符串，例如 `https://github.com/dvershinin/lastversion/issues`。
*   `format`，它接受的值同 `--help` 所说明的一样。不过在 `Python` 代码中还可以指定为 `dict`。
*   `pre_ok`，布尔值，表示预发布版本是否可以作为最新版本。
*   `at`，该项目所在的平台，取值仅可能为`github`，`gitlab`，`bitbucket`，`pip`，`hg`，`sf`，`website-feed`，`local`。

[![DeepSource](https://static.deepsource.io/deepsource-badge-light.svg)](https://deepsource.io/gh/dvershinin/lastversion/?ref=repository-badge)