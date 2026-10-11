// H27: HQ, the Mac desktop app. 10 October 2026 (call at 14:33): "a Mac desktop version of the status page and
// the [call] ... Sort of like how the website is, but also calling this included in it. We also have the statuses
// and everything in there. ... And this app can also reboot that, right? So the main watchdog thing in here."
// And: "a picture of a dog with an animation for the Watchdog service."
//
// One window: on top the watchdog strip (shell.html: the dog, the light, Status and Call, Turn everything on),
// below it the status page (localhost:4748) or the call page (127.0.0.1:7860), the same pages as in the browser
// and on the phone. Every few seconds it asks desktop/hq_control.py how everything is and shows it. The
// routines keep running in the background; closing the app stops nothing (Claude's choice).
// Built by desktop/build.sh with swiftc (no Xcode project needed).
import Cocoa
import WebKit

let SHELL_HEIGHT: CGFloat = 89
let STATUS_URL = URL(string: "http://127.0.0.1:4748/")!
// H46: ?app tells the call page it's inside the app, which has its own Status tab, so it leaves out its status button.
let CALL_URL = URL(string: "http://127.0.0.1:7860/?app=1")!

func hqFolder() -> String {
    if let env = ProcessInfo.processInfo.environment["HQ_HOME"], !env.isEmpty { return env }
    if let p = Bundle.main.object(forInfoDictionaryKey: "HQPath") as? String, !p.isEmpty { return p }
    return NSString(string: "~/Documents/Claude/HQ").expandingTildeInPath
}

final class Controller: NSObject, NSApplicationDelegate, WKScriptMessageHandler, WKNavigationDelegate, WKUIDelegate {
    var window: NSWindow!
    var shell: WKWebView!
    var status: WKWebView!
    var call: WKWebView!
    var shellHeight: NSLayoutConstraint!
    var timer: Timer?
    var shellReady = false
    var statusFailed = false
    var callLoaded = false
    var busy = false
    // H46 (11 October 2026), in the user's words: "i want the call one to be always the main default."
    var tab = "call"
    let hq = hqFolder()
    // `HQ --selftest`: the real window, never shown; once the strip has its first reading it prints what the
    // strip shows and whether the status page loaded, then quits (happy flow 46).
    let selftest = CommandLine.arguments.contains("--selftest")
    var statusLoaded = false
    var reported = false

    func applicationDidFinishLaunching(_ note: Notification) {
        buildMenu()
        window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 1180, height: 860),
                          styleMask: [.titled, .closable, .miniaturizable, .resizable, .fullSizeContentView],
                          backing: .buffered, defer: false)
        window.title = "HQ"
        window.titlebarAppearsTransparent = true
        window.titleVisibility = .hidden
        window.minSize = NSSize(width: 720, height: 520)
        window.setFrameAutosaveName("HQMain")
        if !window.setFrameUsingName("HQMain") { window.center() }

        let content = NSView()
        window.contentView = content

        let shellConf = WKWebViewConfiguration()
        shellConf.userContentController.add(self, name: "hq")
        shell = WKWebView(frame: .zero, configuration: shellConf)
        shell.setValue(false, forKey: "drawsBackground")
        status = page()
        let saved = UserDefaults.standard.double(forKey: "statusZoom")
        if saved >= 0.5 && saved <= 2.0 { status.pageZoom = CGFloat(saved) }
        call = page(call: true)
        status.isHidden = true
        for v in [status!, call!, shell!] {
            v.translatesAutoresizingMaskIntoConstraints = false
            content.addSubview(v)
        }
        shellHeight = shell.heightAnchor.constraint(equalToConstant: SHELL_HEIGHT)
        NSLayoutConstraint.activate([
            shell.topAnchor.constraint(equalTo: content.topAnchor),
            shell.leadingAnchor.constraint(equalTo: content.leadingAnchor),
            shell.trailingAnchor.constraint(equalTo: content.trailingAnchor),
            shellHeight,
        ])
        for v in [status!, call!] {
            NSLayoutConstraint.activate([
                v.topAnchor.constraint(equalTo: content.topAnchor, constant: SHELL_HEIGHT),
                v.leadingAnchor.constraint(equalTo: content.leadingAnchor),
                v.trailingAnchor.constraint(equalTo: content.trailingAnchor),
                v.bottomAnchor.constraint(equalTo: content.bottomAnchor),
            ])
        }

        let shellFile = URL(fileURLWithPath: hq + "/desktop/shell.html")
        shell.loadFileURL(shellFile, allowingReadAccessTo: shellFile.deletingLastPathComponent())
        status.load(URLRequest(url: STATUS_URL))
        callLoaded = true  // the microphone is only asked for when a call starts, not when the page loads
        call.load(URLRequest(url: CALL_URL))

        if selftest {
            DispatchQueue.main.asyncAfter(deadline: .now() + 40) { print("{\"selftest\": \"timed out\"}"); exit(1) }
        } else {
            window.makeKeyAndOrderFront(nil)
            NSApp.activate(ignoringOtherApps: true)
            window.makeFirstResponder(call)  // H49: the space bar reaches the call page from the start
        }
        timer = Timer.scheduledTimer(withTimeInterval: 5, repeats: true) { [weak self] _ in self?.poll() }
    }

    func page(call: Bool = false) -> WKWebView {
        let conf = WKWebViewConfiguration()
        conf.mediaTypesRequiringUserActionForPlayback = []  // her voice plays without an extra click
        if call { showRealAddress(conf.preferences) }
        let v = WKWebView(frame: .zero, configuration: conf)
        v.navigationDelegate = self
        v.uiDelegate = self
        v.allowsBackForwardNavigationGestures = false
        return v
    }

    // H46: calls from the app never connected. Inside an app, WebKit hides this MacBook's network address from
    // the call (a made-up name.local instead), and the call line can't look that name up, so the connection timed
    // out after a few seconds. This switch (WebKit's own, not public) lets the call page show the real address, as
    // Safari does once the microphone is allowed. Only for the call page, which only talks to this MacBook.
    func showRealAddress(_ prefs: WKPreferences) {
        let sel = Selector(("_setICECandidateFilteringEnabled:"))
        guard prefs.responds(to: sel) else { return }
        typealias Setter = @convention(c) (AnyObject, Selector, Bool) -> Void
        unsafeBitCast(prefs.method(for: sel), to: Setter.self)(prefs, sel, false)
    }

    // H47: the status page bigger or smaller, with + and − on the strip and Cmd +, Cmd − and Cmd 0. In steps
    // like Safari's; remembered for next time. Only the status page, not the call (Claude's choice).
    let ZOOMS: [CGFloat] = [0.5, 0.67, 0.75, 0.8, 0.9, 1.0, 1.1, 1.25, 1.5, 1.75, 2.0]
    func zoom(_ by: Int) {
        let now = status.pageZoom
        var next: CGFloat = 1.0
        if by > 0 { next = ZOOMS.first { $0 > now + 0.001 } ?? ZOOMS.last! }
        if by < 0 { next = ZOOMS.last { $0 < now - 0.001 } ?? ZOOMS.first! }
        status.pageZoom = next
        UserDefaults.standard.set(Double(next), forKey: "statusZoom")
        showZoom()
    }
    func showZoom() {
        shell.evaluateJavaScript("hq.zoom(\(Int((status.pageZoom * 100).rounded())))", completionHandler: nil)
    }
    @objc func zoomIn() { zoom(1) }
    @objc func zoomOut() { zoom(-1) }
    @objc func zoomReset() { zoom(0) }

    func applicationShouldTerminateAfterLastWindowClosed(_ app: NSApplication) -> Bool { true }

    // MARK: the watchdog part

    func runControl(_ args: [String], done: @escaping (String) -> Void) {
        let hq = self.hq
        DispatchQueue.global(qos: .utility).async {
            let p = Process()
            p.executableURL = URL(fileURLWithPath: "/usr/bin/python3")
            p.arguments = [hq + "/desktop/hq_control.py"] + args
            p.currentDirectoryURL = URL(fileURLWithPath: hq)
            let out = Pipe()
            p.standardOutput = out
            p.standardError = FileHandle.nullDevice
            var text = ""
            do {
                try p.run()
                let data = out.fileHandleForReading.readDataToEndOfFile()
                p.waitUntilExit()
                text = String(data: data, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
            } catch {
                text = ""
            }
            DispatchQueue.main.async { done(text) }
        }
    }

    func poll() {
        guard shellReady, !busy else { return }
        busy = true
        runControl(["health"]) { [weak self] json in
            guard let self = self else { return }
            self.busy = false
            guard json.hasPrefix("{") else { return }
            self.shell.evaluateJavaScript("hq.update(\(json))") { _, _ in if self.selftest { self.report() } }
            // The status page came back after it was down: load it again.
            if self.statusFailed && !json.contains("\"mood\": \"sleep\"") {
                self.statusFailed = false
                self.status.load(URLRequest(url: STATUS_URL))
            }
        }
    }

    func report() {
        guard !reported else { return }
        if !statusLoaded && !statusFailed {  // wait for the status page a little longer
            DispatchQueue.main.asyncAfter(deadline: .now() + 1) { self.report() }
            return
        }
        reported = true
        shell.evaluateJavaScript("JSON.stringify(hq.state())") { state, _ in
            self.status.evaluateJavaScript("document.title") { title, _ in
                let s = (state as? String) ?? "null"
                let t = String(data: try! JSONSerialization.data(withJSONObject: [(title as? String) ?? ""]), encoding: .utf8)!
                print("{\"strip\": \(s), \"status_loaded\": \(self.statusLoaded), \"status_title\": \(t)}")
                fflush(stdout)
                exit(0)
            }
        }
    }

    func webView(_ v: WKWebView, didFinish nav: WKNavigation!) {
        if v === status && v.url?.port == 4748 { statusLoaded = true }
        // H49: the space bar talks on the call page (app/web/index.html), so it gets the keys once it's loaded.
        if v === call && tab == "call" && !selftest { window.makeFirstResponder(call) }
    }

    func fix() {
        runControl(["fix"]) { [weak self] json in
            guard let self = self else { return }
            var said = "Nothing was off."
            if let data = json.data(using: .utf8),
               let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
               let fixed = obj["fixed"] as? [[String: Any]], !fixed.isEmpty {
                said = fixed.map { ($0["what"] as? String ?? "") + ((($0["ok"] as? Bool) ?? false) ? "" : " (didn't work)") }
                    .joined(separator: " · ")
            }
            let quoted = String(data: try! JSONSerialization.data(withJSONObject: [said], options: []), encoding: .utf8)!
            // Keep the dog running a little while things start, then look again.
            DispatchQueue.main.asyncAfter(deadline: .now() + 6) {
                self.shell.evaluateJavaScript("hq.fixing(false, \(quoted)[0])", completionHandler: nil)
                self.status.load(URLRequest(url: STATUS_URL))
                if self.callLoaded { self.call.load(URLRequest(url: CALL_URL)) }
                self.poll()
            }
        }
    }

    func show(_ which: String) {
        tab = which
        status.isHidden = which != "status"
        call.isHidden = which != "call"
        if which == "call" && !callLoaded {
            callLoaded = true  // only now, so the microphone isn't asked for before he wants to call
            call.load(URLRequest(url: CALL_URL))
        }
        shell.evaluateJavaScript("hq.tab('\(which)')", completionHandler: nil)
        window.makeFirstResponder(which == "call" ? call : status)
    }

    func userContentController(_ ucc: WKUserContentController, didReceive message: WKScriptMessage) {
        guard let m = message.body as? [String: Any], let what = m["do"] as? String else { return }
        switch what {
        case "ready":
            shellReady = true
            shell.evaluateJavaScript("hq.tab('\(tab)')", completionHandler: nil)
            showZoom()
            poll()
        case "tab":
            show(m["tab"] as? String ?? "status")
        case "fix":
            fix()
        case "zoom":
            zoom((m["by"] as? NSNumber)?.intValue ?? 0)
        case "height":
            let px = CGFloat((m["px"] as? NSNumber)?.doubleValue ?? Double(SHELL_HEIGHT))
            shellHeight.constant = max(SHELL_HEIGHT, min(px, 480))
        default:
            break
        }
    }

    // MARK: pages

    func webView(_ v: WKWebView, didFailProvisionalNavigation nav: WKNavigation!, withError error: Error) {
        let words = v === call ? "The call line doesn't answer yet." : "The status page doesn't answer yet."
        v.loadHTMLString("""
            <html><body style="font:15px -apple-system;color:#888;display:flex;align-items:center;justify-content:center;height:90vh;background:transparent">
            <div style="text-align:center"><p>\(words)</p><p>On Status, the dog can turn it on: Turn everything on.</p></div></body></html>
            """, baseURL: nil)
        if v === status { statusFailed = true } else { callLoaded = false }
    }

    // The call page asks for the microphone; only the call line on this MacBook gets it.
    @available(macOS 12.0, *)
    func webView(_ v: WKWebView, requestMediaCapturePermissionFor origin: WKSecurityOrigin,
                 initiatedByFrame frame: WKFrameInfo, type: WKMediaCaptureType,
                 decisionHandler: @escaping (WKPermissionDecision) -> Void) {
        decisionHandler(origin.host == "127.0.0.1" || origin.host == "localhost" ? .grant : .deny)
    }

    // Links that open a new window (for example a mail link on the status page) go to the browser.
    func webView(_ v: WKWebView, createWebViewWith conf: WKWebViewConfiguration, for action: WKNavigationAction,
                 windowFeatures: WKWindowFeatures) -> WKWebView? {
        if let url = action.request.url { NSWorkspace.shared.open(url) }
        return nil
    }

    func webView(_ v: WKWebView, runJavaScriptConfirmPanelWithMessage message: String, initiatedByFrame frame: WKFrameInfo,
                 completionHandler: @escaping (Bool) -> Void) {
        let a = NSAlert()
        a.messageText = message
        a.addButton(withTitle: "OK")
        a.addButton(withTitle: "Cancel")
        completionHandler(a.runModal() == .alertFirstButtonReturn)
    }

    func webView(_ v: WKWebView, runJavaScriptAlertPanelWithMessage message: String, initiatedByFrame frame: WKFrameInfo,
                 completionHandler: @escaping () -> Void) {
        let a = NSAlert()
        a.messageText = message
        a.runModal()
        completionHandler()
    }

    // MARK: menu

    @objc func showStatus() { show("status") }
    @objc func showCall() { show("call") }
    @objc func reloadPage() {
        if tab == "call" { call.load(URLRequest(url: CALL_URL)); callLoaded = true } else { status.load(URLRequest(url: STATUS_URL)) }
    }
    @objc func fixAll() {
        shell.evaluateJavaScript("hq.fixing(true, 'Turning on what\\u2019s off…')", completionHandler: nil)
        fix()
    }

    func buildMenu() {
        let main = NSMenu()
        func sub(_ title: String, _ items: [NSMenuItem]) {
            let it = NSMenuItem(title: title, action: nil, keyEquivalent: "")
            let m = NSMenu(title: title)
            items.forEach { m.addItem($0) }
            it.submenu = m
            main.addItem(it)
        }
        func item(_ t: String, _ a: Selector?, _ k: String, _ target: AnyObject? = nil) -> NSMenuItem {
            let i = NSMenuItem(title: t, action: a, keyEquivalent: k)
            i.target = target
            return i
        }
        func hidden(_ i: NSMenuItem) -> NSMenuItem {  // Cmd = as well as Cmd + (no Shift needed), not shown twice
            i.isHidden = true
            i.allowsKeyEquivalentWhenHidden = true
            return i
        }
        sub("HQ", [item("Hide HQ", #selector(NSApplication.hide(_:)), "h"), .separator(),
                   item("Quit HQ", #selector(NSApplication.terminate(_:)), "q")])
        sub("Edit", [item("Undo", Selector(("undo:")), "z"), item("Redo", Selector(("redo:")), "Z"), .separator(),
                     item("Cut", #selector(NSText.cut(_:)), "x"), item("Copy", #selector(NSText.copy(_:)), "c"),
                     item("Paste", #selector(NSText.paste(_:)), "v"), item("Select All", #selector(NSText.selectAll(_:)), "a")])
        sub("View", [item("Status", #selector(showStatus), "1", self), item("Call", #selector(showCall), "2", self), .separator(),
                     item("Bigger", #selector(zoomIn), "+", self), hidden(item("Bigger", #selector(zoomIn), "=", self)),
                     item("Smaller", #selector(zoomOut), "-", self), item("Actual Size", #selector(zoomReset), "0", self), .separator(),
                     item("Reload", #selector(reloadPage), "r", self), item("Turn everything on", #selector(fixAll), "t", self)])
        sub("Window", [item("Minimize", #selector(NSWindow.performMiniaturize(_:)), "m"),
                       item("Close", #selector(NSWindow.performClose(_:)), "w")])
        NSApp.mainMenu = main
    }
}

// `HQ --check`: the paths it would use and whether its files are there, without a window (happy flow 46).
if CommandLine.arguments.contains("--check") {
    let hq = hqFolder()
    let fm = FileManager.default
    let shellOK = fm.fileExists(atPath: hq + "/desktop/shell.html")
    let controlOK = fm.fileExists(atPath: hq + "/desktop/hq_control.py")
    print("{\"hq\": \"\(hq)\", \"shell\": \(shellOK), \"control\": \(controlOK), \"status\": \"\(STATUS_URL)\", \"call\": \"\(CALL_URL)\"}")
    exit(shellOK && controlOK ? 0 : 1)
}

let app = NSApplication.shared
let controller = Controller()
app.delegate = controller
app.setActivationPolicy(.regular)
app.run()
