import Cocoa
import Carbon

func extractLink(_ text: String) -> String? {
    let detector = try! NSDataDetector(types: NSTextCheckingResult.CheckingType.link.rawValue)
    let allowed = ["douyin.com", "iesdouyin.com", "xiaohongshu.com", "xhslink.com", "xhslink.cn", "tiktok.com", "youtube.com", "youtu.be", "instagram.com"]
    for match in detector.matches(in: text, range: NSRange(text.startIndex..., in: text)) {
        guard let u = match.url, ["http", "https"].contains(u.scheme ?? ""), let host = u.host?.lowercased(), u.user == nil, u.password == nil else { continue }
        if allowed.contains(where: { host == $0 || host.hasSuffix("." + $0) }) { return u.absoluteString }
    }
    return nil
}
if CommandLine.arguments.contains("--self-test") {
    assert(extractLink("复制 https://v.douyin.com/abc/ 分享") == "https://v.douyin.com/abc/")
    for site in ["www.xiaohongshu.com", "xhslink.com", "xhslink.cn", "www.tiktok.com", "youtu.be", "www.youtube.com", "www.instagram.com"] { assert(extractLink("https://\(site)/test") != nil) }
    for link in ["https://youtube.com.evil.test/x", "file:///tmp/a", "https://evil.test/youtube.com", "https://user:pass@youtube.com/x", "nothing"] { assert(extractLink(link) == nil) }
    print("PASS: platform link validation")
    exit(0)
}

final class App: NSObject, NSApplicationDelegate, NSWindowDelegate {
    var item: NSStatusItem!
    var window: NSWindow!
    let input = NSTextField()
    let status = NSTextField(wrappingLabelWithString: "粘贴分享文案或视频链接，先解析，再下载。")
    let detail = NSTextView()
    let parse = NSButton(title: "解析链接", target: nil, action: nil)
    let download = NSButton(title: "下载全部", target: nil, action: nil)
    let cancel = NSButton(title: "取消", target: nil, action: nil)
    let cookies = NSButton(checkboxWithTitle: "TK / YouTube / Instagram：使用 Chrome 登录状态", target: nil, action: nil)
    var process: Process?
    var hotkey: EventHotKeyRef?
    var parsed: String?
    var job = UUID()
    var cancelled = false
    var timedOut = false
    let directory = FileManager.default.urls(for: .downloadsDirectory, in: .userDomainMask)[0].appendingPathComponent("LinkDrop")
    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.accessory)
        let mainMenu = NSMenu()
        let editItem = NSMenuItem(title: "编辑", action: nil, keyEquivalent: "")
        let editMenu = NSMenu(title: "编辑")
        for (title, selector, key) in [("复制", "copy:", "c"), ("粘贴", "paste:", "v"), ("全选", "selectAll:", "a"), ("剪切", "cut:", "x")] {
            editMenu.addItem(withTitle: title, action: Selector(selector), keyEquivalent: key)
        }
        editItem.submenu = editMenu; mainMenu.addItem(editItem); NSApp.mainMenu = mainMenu
        item = NSStatusBar.system.statusItem(withLength: NSStatusItem.squareLength)
        item.button?.image = NSImage(systemSymbolName: "arrow.down.circle", accessibilityDescription: "LinkDrop 视频下载")
        let menu = NSMenu()
        menu.addItem(withTitle: "打开 LinkDrop  ⌃⌥V", action: #selector(show), keyEquivalent: "") .target = self
        menu.addItem(withTitle: "打开下载文件夹", action: #selector(folder), keyEquivalent: "").target = self
        menu.addItem(NSMenuItem.separator())
        menu.addItem(withTitle: "退出", action: #selector(quit), keyEquivalent: "q").target = self
        item.menu = menu
        window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 580, height: 440), styleMask: [.titled, .closable, .miniaturizable], backing: .buffered, defer: false)
        window.title = "LinkDrop · 视频随手存"
        window.isReleasedWhenClosed = false
        window.delegate = self
        let root = NSStackView()
        root.orientation = .vertical; root.alignment = .leading; root.spacing = 16
        root.translatesAutoresizingMaskIntoConstraints = false
        window.contentView!.addSubview(root)
        NSLayoutConstraint.activate([root.leadingAnchor.constraint(equalTo: window.contentView!.leadingAnchor, constant: 24), root.trailingAnchor.constraint(equalTo: window.contentView!.trailingAnchor, constant: -24), root.topAnchor.constraint(equalTo: window.contentView!.topAnchor, constant: 24), root.bottomAnchor.constraint(equalTo: window.contentView!.bottomAnchor, constant: -24)])
        let title = NSTextField(labelWithString: "视频与图集，随手存。")
        title.font = .systemFont(ofSize: 23, weight: .semibold)
        root.addArrangedSubview(title)
        let subtitle = NSTextField(labelWithString: "抖音 · 小红书 · TikTok · YouTube · Instagram")
        subtitle.textColor = .secondaryLabelColor; root.addArrangedSubview(subtitle)
        input.placeholderString = "粘贴完整分享文案或 https://…"; input.font = .systemFont(ofSize: 14)
        root.addArrangedSubview(input); input.widthAnchor.constraint(equalTo: root.widthAnchor).isActive = true
        let row = NSStackView(); row.spacing = 10
        for (button, action) in [(NSButton(title: "粘贴", target: nil, action: nil), #selector(paste)), (parse, #selector(analyze)), (download, #selector(save)), (cancel, #selector(stop)), (NSButton(title: "下载文件夹", target: nil, action: nil), #selector(folder))] {
            button.target = self; button.action = action; button.bezelStyle = .rounded; row.addArrangedSubview(button)
        }
        root.addArrangedSubview(row)
        download.isEnabled = false; cancel.isEnabled = false
        cookies.state = UserDefaults.standard.bool(forKey: "useChromeCookies") ? .on : .off
        cookies.target = self; cookies.action = #selector(cookieChanged)
        cookies.toolTip = "仅供本机引擎向对应平台请求；不发送给第三方解析网站。"
        root.addArrangedSubview(cookies)
        status.font = .systemFont(ofSize: 13, weight: .medium); root.addArrangedSubview(status)
        let scroll = NSScrollView(); scroll.hasVerticalScroller = true; scroll.borderType = .bezelBorder
        detail.isEditable = false; detail.font = .monospacedSystemFont(ofSize: 11, weight: .regular); detail.autoresizingMask = [.width]; detail.textContainer?.widthTracksTextView = true
        scroll.documentView = detail; root.addArrangedSubview(scroll)
        scroll.widthAnchor.constraint(equalTo: root.widthAnchor).isActive = true
        scroll.heightAnchor.constraint(greaterThanOrEqualToConstant: 100).isActive = true
        var spec = EventTypeSpec(eventClass: OSType(kEventClassKeyboard), eventKind: UInt32(kEventHotKeyPressed))
        InstallEventHandler(GetApplicationEventTarget(), { _, _, ptr in
            let app = Unmanaged<App>.fromOpaque(ptr!).takeUnretainedValue()
            DispatchQueue.main.async { app.show() }; return noErr
        }, 1, &spec, Unmanaged.passUnretained(self).toOpaque(), nil)
        let result = RegisterEventHotKey(UInt32(kVK_ANSI_V), UInt32(controlKey | optionKey), EventHotKeyID(signature: 0x4c445250, id: 1), GetApplicationEventTarget(), 0, &hotkey)
        if result != noErr { status.stringValue = "快捷键被占用，请点击菜单栏图标打开。" }
        show()
    }
    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool { show(); return true }
    @objc func show() { window.center(); window.makeKeyAndOrderFront(nil); NSApp.activate(ignoringOtherApps: true); window.makeFirstResponder(input) }
    @objc func cookieChanged() { UserDefaults.standard.set(cookies.state == .on, forKey: "useChromeCookies") }
    @objc func paste() { input.stringValue = NSPasteboard.general.string(forType: .string) ?? ""; parsed = nil; download.isEnabled = false }
    @objc func folder() { try? FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true); NSWorkspace.shared.open(directory) }
    @objc func quit() { process?.terminate(); NSApp.terminate(nil) }
    @objc func stop() { cancelled = true; process?.terminate(); status.stringValue = "正在取消…" }
    @objc func analyze() {
        guard let link = extractLink(input.stringValue) else { status.stringValue = "没有找到支持的视频链接，请粘贴完整分享文案。"; return }
        parsed = nil; run(link, downloading: false)
    }
    @objc func save() {
        guard let link = parsed, link == extractLink(input.stringValue) else { download.isEnabled = false; status.stringValue = "链接已变更，请重新解析。"; return }
        run(link, downloading: true)
    }
    func run(_ link: String, downloading: Bool) {
        guard process == nil else { return }
        let executable = Bundle.main.resourceURL!.appendingPathComponent("yt-dlp")
        guard FileManager.default.isExecutableFile(atPath: executable.path) else { status.stringValue = "下载引擎缺失。"; return }
        do { try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true) } catch { status.stringValue = error.localizedDescription; return }
        let p = Process(); let pipe = Pipe()
        p.executableURL = executable
        var args = ["--ignore-config", "--no-playlist", "--no-colors", "--socket-timeout", "20", "--retries", "2", "--extractor-retries", "1"]
        if cookies.state == .on { args += ["--cookies-from-browser", "chrome"] }
        let ffmpeg = Bundle.main.resourceURL!.appendingPathComponent("ffmpeg").path
        if FileManager.default.isExecutableFile(atPath: ffmpeg) { args += ["--ffmpeg-location", ffmpeg] }
        let node = Bundle.main.resourceURL!.appendingPathComponent("node").path
        if FileManager.default.isExecutableFile(atPath: node) { args += ["--js-runtimes", "node:" + node] }
        let host = URL(string: link)?.host ?? ""
        if host == "youtu.be" || host == "youtube.com" || host.hasSuffix(".youtube.com") {
            args += ["-f", "bv*[vcodec^=avc1]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b"]
        }
        if downloading { args += ["--newline", "--progress", "--no-overwrites", "--restrict-filenames", "-P", directory.path, "-o", "%(title).120B [%(id)s].%(ext)s", "--merge-output-format", "mp4", "--print", "after_move:已保存：%(filepath)s"] }
        else { args += ["--dump-single-json", "--skip-download"] }
        args += ["--", link]; p.arguments = args; p.standardOutput = pipe; p.standardError = pipe
        process = p; job = UUID(); let token = job; cancelled = false; timedOut = false
        parse.isEnabled = false; download.isEnabled = false; input.isEnabled = false; cookies.isEnabled = false; cancel.isEnabled = true
        detail.string = ""; status.stringValue = downloading ? "正在下载…" : "正在解析链接…"
        do { try p.run() } catch { finish(); status.stringValue = "无法启动：\(error.localizedDescription)"; return }
        DispatchQueue.main.asyncAfter(deadline: .now() + (downloading ? 1800 : 100)) { [weak self] in
            guard let self = self, self.job == token, self.process != nil else { return }
            self.timedOut = true; self.process?.terminate()
        }
        DispatchQueue.global(qos: .userInitiated).async {
            var all = Data()
            while true {
                let bytes = pipe.fileHandleForReading.availableData
                if bytes.isEmpty { break }; all.append(bytes)
                if downloading { let text = String(decoding: bytes, as: UTF8.self); DispatchQueue.main.async { self.detail.string += text; self.detail.scrollToEndOfDocument(nil) } }
            }
            p.waitUntilExit()
            let output = String(decoding: all, as: UTF8.self)
            DispatchQueue.main.async {
                let aborted = self.cancelled; let timeout = self.timedOut
                self.finish()
                if aborted || timeout { self.status.stringValue = aborted ? "已取消。" : "请求超时，请检查网络后重试。"; self.detail.string = output; return }
                guard p.terminationStatus == 0 else {
                    self.status.stringValue = "未成功：请查看下方原因；可重试；海外平台需要时可使用 Chrome 登录状态。"
                    self.detail.string = output; return
                }
                if downloading { self.status.stringValue = "下载完成 · 已保存到 下载/LinkDrop"; self.download.isEnabled = true }
                else {
                    let jsonLine = output.components(separatedBy: .newlines).last(where: { $0.hasPrefix("{") }) ?? ""
                    guard let data = jsonLine.data(using: .utf8), let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any], let title = json["title"] as? String else { self.status.stringValue = "无法读取解析结果。"; self.detail.string = output; return }
                    self.parsed = link; self.download.isEnabled = true
                    self.status.stringValue = "解析完成 · \(json["media_type"] as? String ?? "视频") · \(json["media_count"] as? Int ?? 1) 个文件"
                    self.detail.string = "\(title)\n\n作者：\(json["uploader"] as? String ?? "未知")\n时长：\(json["duration"] ?? "未知") 秒\n平台：\(json["extractor"] ?? "未知")\n\(json["quality_note"] as? String ?? "按平台提供的最佳可用画质下载")\n\n保存位置：\(self.directory.path)"
                }
            }
        }
    }
    func finish() { process = nil; parse.isEnabled = true; input.isEnabled = true; cookies.isEnabled = true; cancel.isEnabled = false }
}
let app = NSApplication.shared
let delegate = App()
app.delegate = delegate
app.run()
