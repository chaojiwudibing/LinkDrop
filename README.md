# LinkDrop

Mac 菜单栏视频与图集下载工具。复制分享文案，按 **Control + Option + V** 呼出，解析后保存到本机。

支持抖音、小红书、TikTok、YouTube 和 Instagram。抖音、小红书由本机解析器处理，其余平台使用 yt-dlp；不使用第三方解析中转服务。

## 本机构建

需要 macOS、Xcode Command Line Tools、Python 3.11+、Node.js 和 FFmpeg。已在 Apple Silicon Mac 上验证。安装依赖示例（已有 Homebrew）：

```sh
xcode-select --install
brew install python node ffmpeg
```

在仓库目录运行：

```sh
./build.sh
open build/LinkDrop.app
```

若命令不在 PATH，可通过 `PYTHON_BIN`、`NODE_BIN`、`FFMPEG_BIN` 指定可执行文件绝对路径。

构建结果依赖本仓库的 `.venv` 和本机 Node/FFmpeg，请保留仓库位置，不要将此构建当作可移植安装包分发。应用采用本地 ad-hoc 签名，未经过 Apple 公证。本仓库暂不提供二进制 Release。

## 使用

1. 启动应用，点击菜单栏下载图标或按 `Control + Option + V`。
2. 粘贴完整分享文案，点击「解析链接」。
3. 点击「下载全部」，文件保存到 `~/Downloads/LinkDrop`。

图集逐张保存并自动生成 ZIP；关闭窗口后保留菜单栏图标。只处理单条作品链接，不抓取账号主页。不会后台自动读取剪贴板，没有开机自启和自动更新。

TikTok / YouTube / Instagram 需要时可手动勾选使用 Chrome 登录状态。此选项默认关闭、记住用户选择；可能触发 macOS 钥匙串授权。登录数据由本机引擎使用，不发送给第三方解析网站。解析结果在本机缓存五分钟。不要将缓存、浏览器数据或下载结果提交到 GitHub。

## 验证与限制

2026-10-26 开发阶段，抖音视频/图片、小红书视频/11 张图集以及 TikTok、Instagram、YouTube 样例均完成下载和媒体检查。YouTube 样例需要已授权的 Chrome 登录状态；两条抖音视频返回 720p。样例成功不保证所有链接或未来接口永久可用，平台更新可能导致解析失败。第三方样例和个人调试记录不包含在仓库中。

构建脚本运行原生链接校验与 Python 解析器自检；不自动访问平台或读取 Chrome 登录状态。海外平台需要可用网络，程序不修改系统代理。

仅用于备份本人作品及已获授权内容。公开视频不等同于获准下载、转载或商用。请遵守内容授权与平台规则。本项目不是相关平台官方产品，不承诺无水印、最高画质或绕过访问限制。

## 文件

- `src/main.swift`：AppKit 界面、全局快捷键、任务管理
- `src/linkdrop_backend.py`：本地解析与下载、yt-dlp 调用
- `build.sh`：安装 Python 依赖、编译、自检、本地签名
- `THIRD-PARTY.md`：第三方依赖与参考来源

项目自有代码采用 [MIT License](LICENSE)，允许使用、修改与再分发。第三方依赖保留各自许可证，详见 [THIRD-PARTY.md](THIRD-PARTY.md)。
