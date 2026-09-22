# astrbot_plugin_jmcomic

提供一个用于与禁漫天堂（JMComic）交互的插件。

## 功能

- 按关键词搜索漫画并查看专辑详情
- 按分类、时间范围和热度浏览
- 下载图片并生成完整 PDF
- 按固定页数生成 PDF 分片，适配聊天平台文件大小限制
- PDF 缓存校验、原子写入、下载失败重试和并发限制
- 可选每天自动清理漫画图片和 PDF 缓存
- 可选 JPEG 压缩质量、PDF 密码、代理和 JMComic 账号
- 可配置为仅允许 AstrBot 管理员执行下载命令

## 安装

将本目录复制到 AstrBot 的 `data/plugins/astrbot_plugin_jmcomic`，或者将仓库地址粘贴到 AstrBot WebUI 的插件安装页面。AstrBot 会根据 `requirements.txt` 安装依赖。

安装后在 WebUI 中打开插件配置，按需调整并发数、超时、PDF 质量、分片页数、文件发送上限和代理，然后重载插件。

插件数据保存在：

```text
data/plugin_data/astrbot_plugin_jmcomic/
├── downloads/            # 下载的图片
├── pdf/                  # 生成的 PDF
└── option.generated.yml  # 根据 WebUI 配置生成的 jmcomic 配置
```

配置项 `daily_auto_cleanup` 默认开启。启用后，插件会按服务器本地时间每天 04:00 清空 `downloads/` 和 `pdf/`；不会删除插件配置或 `option.generated.yml`。如果当时有下载或 PDF 生成任务，清理会等待任务完成；不需要自动清理时可在 WebUI 中关闭。

## 指令说明

根指令支持 `/jm`、`/JM` 和 `/禁漫`。根指令、子指令与参数可以中英文混合使用，例如 `/jm 搜索 30`、`/禁漫 search 30` 和 `/jm 分类 韩漫 1 本月 浏览` 都是有效格式。

方括号包围的参数可以省略；尖括号包围的参数必须提供。漫画 ID 可以写成 `12345` 或 `JM12345`。

| 英文指令 | 中文指令 | 用途 |
| --- | --- | --- |
| `/jm help` | `/禁漫 帮助` | 显示插件内置帮助 |
| `/jm search <关键词> [页码]` | `/禁漫 搜索 <关键词> [页码]` | 按关键词搜索漫画 |
| `/jm detail <漫画ID>` | `/禁漫 详情 <漫画ID>` | 查看标题、作者、页数和标签 |
| `/jm category [分类] [页码] [时间] [排序]` | `/禁漫 分类 [分类] [页码] [时间] [排序]` | 按分类、时间和排序方式浏览 |
| `/jm pdf <漫画ID>` | `/禁漫 下载 <漫画ID>` | 下载漫画并生成、发送完整 PDF |
| `/jm shard <漫画ID> <分片序号>` | `/禁漫 分片 <漫画ID> <分片序号>` | 生成并发送指定 PDF 分片 |
| `/jm status` | `/禁漫 状态` | 查看插件运行状态和缓存占用 |

子指令别名：

- `help`：`帮助`
- `search`：`搜索`、`搜本`
- `detail`：`详情`、`信息`
- `category`：`分类`、`排行`
- `pdf`：`下载`、`下载本子`
- `shard`：`分片`、`分页`
- `status`：`状态`、`缓存`

### 搜索

```text
/jm search <关键词> [页码]
/jm 搜索 <关键词> [页码]
```

按标题或关键词搜索，返回漫画 ID 和标题。页码从 `1` 开始，省略时默认为第 1 页；单次最多展示的条数由 `search_result_limit` 配置决定。

```text
/jm 搜索 30
/禁漫 搜本 纯爱 2
```

注意：`/jm 搜索 30` 表示搜索关键词“30”。如果 `30` 是漫画 ID，请使用 `/jm 详情 30` 或 `/jm 下载 30`。

### 详情

```text
/jm detail <漫画ID>
/jm 详情 <漫画ID>
```

查询指定漫画的标题、作者、页数和标签，不会下载图片或生成 PDF。

```text
/jm detail JM12345
/禁漫 信息 12345
```

### 分类浏览

```text
/jm category [分类] [页码] [时间] [排序]
/jm 分类 [分类] [页码] [时间] [排序]
```

四个参数必须保持顺序。省略时分别使用 `all`、`1`、`all` 和 `latest`。

| 参数 | 英文可选值 | 中文可选值 |
| --- | --- | --- |
| 分类 | `all`、`doujin`、`single`、`short`、`another`、`hanman`、`meiman`、`doujin_cosplay`、`cosplay`、`3d`、`english_site` | `全部`、`同人`、`单本`、`短篇`、`其他`、`韩漫`、`美漫`、`同人cosplay`、`角色扮演`、`三维`、`英文`、`英文站` |
| 时间 | `today` 或 `t`、`week` 或 `w`、`month` 或 `m`、`all` 或 `a` | `今天`、`今日`、`本周`、`周`、`本月`、`月`、`全部` |
| 排序 | `latest`、`view`、`picture`、`like`、`month_rank`、`week_rank`、`day_rank` | `最新`、`浏览`、`观看`、`图片`、`点赞`、`喜欢`、`月榜`、`周榜`、`日榜` |

```text
/jm category hanman 1 month view
/jm 分类 韩漫 1 本月 浏览
/禁漫 排行 全部 2 本周 周榜
```

### 下载完整 PDF

```text
/jm pdf <漫画ID>
/jm 下载 <漫画ID>
```

首次执行时下载漫画图片并生成 PDF，后续请求会优先使用有效缓存。如果开启 `encrypt_pdf`，PDF 密码为不带 `JM` 前缀的漫画 ID。

完整 PDF 超过 `max_send_file_mb` 设置的发送上限时，文件仍会保存在缓存目录，但不会作为聊天文件发送。此时应使用 `shard/分片` 指令。

```text
/jm pdf 12345
/禁漫 下载 JM12345
```

默认配置下，所有用户都可以执行 `pdf` 和 `shard`。如需限制为仅 AstrBot 管理员可用，请开启 `admin_only_download`。

### 获取 PDF 分片

```text
/jm shard <漫画ID> <分片序号>
/jm 分片 <漫画ID> <分片序号>
```

将漫画按固定页数划分后，生成并发送指定序号的 PDF。分片序号从 `1` 开始，每片页数由 `shard_pages` 配置决定，默认每片 250 页。例如一本 620 页的漫画会分为 3 片：第 1 片为 1–250 页，第 2 片为 251–500 页，第 3 片为 501–620 页。

```text
/jm shard 12345 1
/jm 分页 12345 2
/禁漫 分片 JM12345 3
```

不需要先执行 `pdf`：如果图片尚未缓存，`shard` 会自动下载后生成指定分片。如果分片仍超过发送上限，请在插件配置中减小 `shard_pages`。

### 状态

```text
/jm status
/jm 状态
```

显示当前客户端类型、已缓存的漫画目录数量、PDF 文件数量、PDF 总大小和插件数据目录。该指令不会清理或修改缓存。

```text
/jm status
/禁漫 缓存
```

## 平台注意事项

AstrBot 的文件消息并非所有平台都支持。如果平台不能发送本地文件，PDF 仍会保存在插件数据目录中。完整 PDF 超过配置的发送上限时，请改用 `/jm shard`。

下载与 PDF 合并会消耗较多网络、CPU、内存和磁盘资源。公开机器人建议保持“仅管理员下载”开启，并定期清理缓存目录。

## 来源与声明

插件基于 AstrBot 官方插件规范开发，功能设计参考 [FfmpegZZZ/JMComic-Api](https://github.com/FfmpegZZZ/JMComic-Api)，底层使用 [JMComic-Crawler-Python](https://github.com/hect0x7/JMComic-Crawler-Python)。详细来源见 `NOTICE`。

请仅在获得授权并符合内容来源、聊天平台及所在地法律要求的前提下使用。插件作者不提供任何内容，也不对第三方服务的可用性负责。
