<div align="center">

<h1>JMComic 禁漫搜索下载</h1>

为 AstrBot 提供 JMComic 漫画搜索、详情浏览、随机推荐与 PDF 下载。

![AstrBot](https://img.shields.io/badge/AstrBot-%3E%3D4.9.2%20%3C5-5865f2?style=flat-square)
![Version](https://img.shields.io/badge/version-v1.0.3-22c55e?style=flat-square)
![Platform](https://img.shields.io/badge/platform-aiocqhttp-f97316?style=flat-square)
![License](https://img.shields.io/badge/license-GPL--3.0-3b82f6?style=flat-square)

<br>
<img src="logo.png" alt="JMComic 禁漫搜索下载 Logo" width="180">

</div>

插件基于 AstrBot 官方插件规范开发，功能设计参考 [FfmpegZZZ/JMComic-Api](https://github.com/FfmpegZZZ/JMComic-Api)，底层使用 [JMComic-Crawler-Python](https://github.com/hect0x7/JMComic-Crawler-Python)。详细来源见 [NOTICE](NOTICE)。

## 目录

- [功能一览](#功能一览)
- [快速开始](#快速开始)
- [指令说明](#指令说明)
- [分类参数](#分类参数)
- [推荐配置](#推荐配置)
- [缓存与自动清理](#缓存与自动清理)
- [平台与故障降级](#平台与故障降级)
- [依赖](#依赖)
- [推荐插件](#推荐插件)
- [来源与声明](#来源与声明)

## 功能一览

| 场景 | 能力 |
| --- | --- |
| 搜索与分类 | 按关键词搜索漫画，或按分类、时间范围和排序方式浏览 |
| 详情与随机 | 查看标题、作者、页数、标签和封面，也可随机推荐一本漫画 |
| 完整 PDF | 下载漫画图片并生成完整 PDF，后续请求优先复用有效缓存 |
| PDF 分片 | 按固定页数生成指定分片，适配聊天平台文件大小限制 |
| 下载控制 | 支持并发限制、超时、失败重试、JPEG 质量和发送大小限制 |
| 隐私与安全 | 可选 PDF 密码、网络代理和 JMComic 账号，并可限制管理员下载 |
| 缓存管理 | 每天自动清理漫画图片、封面和 PDF，也可关闭自动清理 |

> [!NOTE]
> 主要面向 QQ OneBot / `aiocqhttp`，要求 AstrBot `>=4.9.2,<5`。

## 快速开始

1. 在 AstrBot WebUI 的插件安装页面粘贴仓库地址：

   ```text
   https://github.com/muyikk/astrbot_plugin_jmcomic
   ```

   也可以下载仓库 ZIP 后选择“导入插件”，或将本目录复制到 AstrBot 的 `data/plugins/astrbot_plugin_jmcomic`。

2. 等待 AstrBot 根据 `requirements.txt` 安装依赖。

3. 在插件配置中按需调整客户端类型、并发数、超时、PDF 质量、分片页数、文件发送上限和代理，然后重载插件。

4. 使用中文主指令开始查询：

   ```text
   /禁漫 搜索 关键词
   /禁漫 详情 JM12345
   /禁漫 下载 JM12345
   ```

> [!IMPORTANT]
> 请仅在获得授权，并符合内容来源、聊天平台及所在地法律要求的前提下使用。本插件不提供任何漫画内容。

## 指令说明

中文主指令为 `/禁漫`，同时兼容英文根指令 `/jm`、`/JM`。根指令、子指令和分类参数可以中英文混合使用，例如 `/禁漫 搜索 30`、`/jm search 30` 和 `/jm 分类 韩漫 1 本月 浏览` 都是有效格式。

方括号包围的参数可以省略，尖括号包围的参数必须提供。漫画 ID 可以写成 `12345` 或 `JM12345`。

| 中文主指令 | 英文别名 | 说明 | 示例 |
| --- | --- | --- | --- |
| `/禁漫 帮助` | `/jm help` | 显示插件内置帮助 | `/禁漫 帮助` |
| `/禁漫 搜索 <关键词> [页码]` | `/jm search` | 按标题或关键词搜索漫画 | `/禁漫 搜索 纯爱 2` |
| `/禁漫 详情 <漫画ID>` | `/jm detail` | 查看封面、标题、作者、页数和标签 | `/禁漫 详情 JM12345` |
| `/禁漫 随机` | `/jm random` | 随机获取一本漫画的封面和详情 | `/禁漫 随机` |
| `/禁漫 分类 [分类] [页码] [时间] [排序]` | `/jm category` | 按分类、时间和排序方式浏览 | `/禁漫 分类 韩漫 1 本月 浏览` |
| `/禁漫 下载 <漫画ID>` | `/jm pdf` | 下载漫画并生成、发送完整 PDF | `/禁漫 下载 12345` |
| `/禁漫 分片 <漫画ID> <分片序号>` | `/jm shard` | 生成并发送指定 PDF 分片 | `/禁漫 分片 12345 2` |
| `/禁漫 状态` | `/jm status` | 查看客户端、运行状态和缓存占用 | `/禁漫 状态` |

### 中文别名

- `帮助`：英文别名 `help`
- `搜索`：兼容 `搜本`、`search`
- `详情`：兼容 `信息`、`detail`
- `随机`：兼容 `随机本子`、`抽一本`、`random`
- `分类`：兼容 `排行`、`category`
- `下载`：兼容 `下载本子`、`pdf`
- `分片`：兼容 `分页`、`shard`
- `状态`：兼容 `缓存`、`status`

### 使用细节

<details>
<summary><strong>搜索、详情与随机推荐</strong></summary>

- 搜索页码从 `1` 开始，省略时默认为第 1 页；展示条数由 `search_result_limit` 控制。
- `/禁漫 搜索 30` 表示搜索关键词“30”。如果 `30` 是漫画 ID，请使用 `/禁漫 详情 30` 或 `/禁漫 下载 30`。
- 详情会返回漫画标题、作者、页数和标签。`show_cover` 开启时同时发送封面；关闭后只发送文字。
- 随机指令从全部分类中随机选择一页，再从该页选择一本漫画，返回与详情指令相同的信息。
- 详情和随机指令不会下载漫画正文图片，也不会生成 PDF。

</details>

<details>
<summary><strong>完整 PDF 与 PDF 分片</strong></summary>

- 首次下载会获取漫画图片并生成 PDF，后续请求优先使用有效缓存。
- `encrypt_pdf` 开启时，PDF 密码为不带 `JM` 前缀的漫画 ID。
- 完整 PDF 超过 `max_send_file_mb` 时仍保存在缓存目录，但不会作为聊天文件发送，此时请使用 `/禁漫 分片`。
- 分片序号从 `1` 开始，每片页数由 `shard_pages` 控制，默认 250 页。
- 一本 620 页的漫画会分为 3 片：第 1 片为 1–250 页，第 2 片为 251–500 页，第 3 片为 501–620 页。
- 无需先执行完整下载；图片尚未缓存时，分片指令会自动下载并生成目标分片。
- 默认所有用户都能执行下载和分片。公开机器人建议开启 `admin_only_download`。

</details>

## 分类参数

`/禁漫 分类` 的四个参数必须保持“分类、页码、时间、排序”的顺序，省略时分别使用 `全部`、`1`、`全部` 和 `最新`。

| 参数 | 中文可选值 | 英文别名 |
| --- | --- | --- |
| 分类 | `全部`、`同人`、`单本`、`短篇`、`其他`、`韩漫`、`美漫`、`同人cosplay`、`角色扮演`、`三维`、`英文`、`英文站` | `all`、`doujin`、`single`、`short`、`another`、`hanman`、`meiman`、`doujin_cosplay`、`cosplay`、`3d`、`english_site` |
| 时间 | `今天`、`今日`、`本周`、`周`、`本月`、`月`、`全部` | `today` / `t`、`week` / `w`、`month` / `m`、`all` / `a` |
| 排序 | `最新`、`浏览`、`观看`、`图片`、`点赞`、`喜欢`、`月榜`、`周榜`、`日榜` | `latest`、`view`、`picture`、`like`、`month_rank`、`week_rank`、`day_rank` |

```text
/禁漫 分类 韩漫 1 本月 浏览
/禁漫 排行 全部 2 本周 周榜
/jm category hanman 1 month view
```

## 推荐配置

| 配置 | 建议 |
| --- | --- |
| `client_impl` | 保持默认值 `api`；需要网页客户端时再切换为 `html` |
| `admin_only_download` | 公开群聊机器人建议开启，避免磁盘和带宽被滥用 |
| `max_concurrent_downloads` | 建议保持 `2`；数值过高可能触发上游限流并增加资源占用 |
| `shard_pages` | 默认 `250`；分片仍超过平台限制时适当减小 |
| `max_send_file_mb` | 按聊天平台限制调整，默认 `100` MiB |
| `daily_auto_cleanup` | 默认开启，每天 04:00 清理下载、封面和 PDF 缓存 |

<details>
<summary><strong>完整配置项</strong></summary>

| 配置项 | 默认值 | 说明 |
| --- | ---: | --- |
| `admin_only_download` | `false` | 仅允许 AstrBot 管理员下载和生成 PDF；公开群聊机器人建议开启 |
| `client_impl` | `api` | JMComic 客户端类型，可选 `api`、`html`；推荐移动端 API |
| `timeout_seconds` | `600` | 漫画下载和 PDF 生成任务的超时时间，单位为秒 |
| `metadata_timeout_seconds` | `45` | 搜索、分类、详情和随机请求的超时时间，单位为秒 |
| `max_concurrent_downloads` | `2` | 最大同时下载任务数；过高可能触发上游限流并增加内存和带宽占用 |
| `retry_attempts` | `3` | 临时下载失败后的重试次数 |
| `image_threads` | `20` | 单个任务下载图片时使用的线程数 |
| `photo_threads` | `2` | 单个任务下载章节时使用的线程数 |
| `jpeg_quality` | `70` | PDF JPEG 质量，有效范围 1–95；设为 `0` 表示不额外指定压缩质量 |
| `encrypt_pdf` | `false` | 使用漫画 ID 加密 PDF；密码是不带 `JM` 前缀的漫画 ID |
| `shard_pages` | `250` | 每个 PDF 分片包含的页数 |
| `max_send_file_mb` | `100` | 允许作为聊天文件发送的最大文件大小，单位为 MiB |
| `search_result_limit` | `10` | 搜索和分类指令最多展示的结果条数 |
| `show_cover` | `true` | 详情和随机指令发送封面加文字；关闭后只发送文字且不下载封面 |
| `daily_auto_cleanup` | `true` | 按服务器本地时间每天 04:00 清理 `downloads`、`covers` 和 `pdf` |
| `proxy` | 空 | 可选 HTTP 代理，例如 `http://127.0.0.1:7890`；留空时不显式设置代理 |
| `username` | 空 | JMComic 登录用户名；与密码同时填写时启用登录插件 |
| `password` | 空 | JMComic 登录密码；在 AstrBot 配置中作为敏感字段保存 |

</details>

> [!TIP]
> `client_impl=api` 使用移动端 API 客户端，是默认推荐选项；`client_impl=html` 使用网页客户端，可在 API 客户端不可用或需要网页端行为时切换。

## 缓存与自动清理

插件数据保存在：

```text
data/plugin_data/astrbot_plugin_jmcomic/
├── downloads/            # 下载的漫画图片
├── covers/               # 详情和随机指令缓存的封面
├── pdf/                  # 完整 PDF 与 PDF 分片
└── option.generated.yml  # 根据 WebUI 配置生成的 jmcomic 配置
```

- 封面按漫画 ID 缓存，重复查询会优先复用；获取失败时自动降级为纯文字详情。
- PDF 使用缓存校验与原子写入，避免将未完成文件当作有效结果。
- `daily_auto_cleanup` 默认开启，按服务器本地时间每天 04:00 清空 `downloads/`、`covers/` 和 `pdf/`。
- 自动清理不会删除插件配置或 `option.generated.yml`。
- 下载、封面或 PDF 生成任务正在运行时，清理会等待任务完成。

## 平台与故障降级

> [!WARNING]
> AstrBot 的文件消息并非所有平台都支持。如果平台不能发送本地文件，PDF 仍会保存在插件数据目录中；文件超过平台发送上限时请使用 `/禁漫 分片`。

- 搜索、详情和下载分别使用可配置超时，临时下载失败会按配置重试。
- 相同漫画的下载、封面和 PDF 任务会复用锁，避免重复工作以及与自动清理冲突。
- 封面获取失败时仍返回完整文字详情，不影响详情或随机指令。
- 下载与 PDF 合并会占用网络、CPU、内存和磁盘资源，请根据服务器容量设置并发、线程数与缓存清理。

## 依赖

AstrBot 会根据 `requirements.txt` 自动安装：

| 依赖 | 版本 | 用途 |
| --- | --- | --- |
| `jmcomic` | `2.6.18` | 搜索、详情、分类、封面与漫画图片下载 |
| `Pillow` | `>=11.1.0` | 图片读取与 PDF 图像处理 |
| `pypdf` | `>=5` | PDF 合并、分片与加密 |
| `PyYAML` | `>=6.0` | 生成 JMComic 客户端配置 |

## 推荐插件

| 插件 | 功能 |
| --- | --- |
| [海克斯乱斗](https://github.com/muyikk/astrbot_plugin_hextechmayhem) | 查询《英雄联盟》海克斯大乱斗英雄报告、海克斯强化与综合强度排名 |

## 来源与声明

- AstrBot 插件模板：[Soulter/helloworld](https://github.com/Soulter/helloworld)
- 功能设计参考：[FfmpegZZZ/JMComic-Api](https://github.com/FfmpegZZZ/JMComic-Api)
- 底层 JMComic 客户端：[hect0x7/JMComic-Crawler-Python](https://github.com/hect0x7/JMComic-Crawler-Python)

本插件并非禁漫（JMComic）官方插件，与 JMComic 及上述项目均无官方关联。插件图标来源于禁漫官方图标；如相关权利人认为该图标或其他内容构成侵权，请联系删除。

插件作者不提供任何漫画内容，也不对第三方服务的可用性负责。使用者应自行确认内容授权，并遵守内容来源、聊天平台及所在地的法律与规则。

项目采用 [GNU General Public License v3.0](LICENSE)，详细的第三方来源与许可说明见 [NOTICE](NOTICE)。
