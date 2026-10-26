# LinkDrop

**English** | [简体中文](README.zh-CN.md)

A macOS menu bar app for saving videos and image collections. Copy a share link or share text, press **Control + Option + V**, resolve the link, and save the media locally.

Supports **Douyin, Xiaohongshu (RedNote), TikTok, YouTube, and Instagram**. Douyin and Xiaohongshu use local parsers; the other platforms use yt-dlp. No third-party parsing service is involved.

## Build locally

Requires macOS, Xcode Command Line Tools, Python 3.11+, Node.js, and FFmpeg. Tested on an Apple Silicon Mac. If you already have Homebrew, install the prerequisites with:

```sh
xcode-select --install
brew install python node ffmpeg
```

From the repository directory, run:

```sh
./build.sh
open build/LinkDrop.app
```

If an executable is not on your PATH, set `PYTHON_BIN`, `NODE_BIN`, or `FFMPEG_BIN` to its absolute path.

The built app depends on this checkout's `.venv` and your local Node/FFmpeg installations. Keep the checkout in place; this build is not a portable app bundle. The app is ad-hoc signed locally and is not notarized by Apple. No binary release is currently provided.

## Usage

The app interface is currently in Chinese.

1. Launch the app, then click the download icon in the menu bar or press `Control + Option + V`.
2. Paste the full share text or link and click **解析链接** (Resolve link).
3. Click **下载全部** (Download all). Files are saved to `~/Downloads/LinkDrop`.

Images are saved individually, and image collections are also packaged into a ZIP. Closing the window keeps the app in the menu bar. The app handles one post at a time, not entire account profiles. It does not automatically read the clipboard in the background, launch at login, or update itself.

For TikTok, YouTube, and Instagram, you can optionally enable the use of your Chrome login session. This option is off by default and remembers your choice. macOS may request Keychain authorization. Login data is used by the local engine and is not sent to third-party parsing services. Resolved metadata is cached locally for five minutes. Do not commit caches, browser data, or downloaded content to GitHub.

## Verification and limitations

During development on October 26, 2026, sample downloads and media checks passed for Douyin videos/images, a Xiaohongshu video and an 11-image collection, and TikTok, Instagram, and YouTube videos. The YouTube sample required an authorized Chrome login session; two Douyin samples returned 720p video. These results apply to the tested samples, not every link or future platform version. Platform changes may break parsing. Third-party sample media and personal debugging records are not included in this repository.

The build script runs native link-validation checks and Python parser self-tests. It does not automatically contact platforms or read your Chrome login session. Platforms must be reachable from your network; the app does not change system proxy settings.

Use LinkDrop to back up your own work or content you are authorized to download. Public availability does not grant permission to download, redistribute, or use content commercially. Respect content licenses and platform rules. This is not an official product of any supported platform. It does not promise watermark-free downloads, the highest source quality, or bypassing access restrictions.

## Project files

- `src/main.swift`: AppKit interface, global shortcut, and task management
- `src/linkdrop_backend.py`: Local parsing, downloading, and yt-dlp integration
- `build.sh`: Python dependency installation, compilation, self-tests, and local signing
- `THIRD-PARTY.md`: Third-party dependencies and references

## License

Original project code is available under the [MIT License](LICENSE), allowing use, modification, and redistribution. Third-party dependencies retain their own licenses; see [THIRD-PARTY.md](THIRD-PARTY.md).
