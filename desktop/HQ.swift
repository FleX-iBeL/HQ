// HQ, the Mac desktop app: one window that is the HQ page (the same page as in the browser and on the phone,
// from the call line on this Mac). Nothing of its own is drawn over or above the page: the three areas, the
// texts, Status and the updates are all in the page. The window's own close, minimise and zoom buttons sit in
// the page's top left corner (the page keeps the spot the design drew them in free when opened with ?app).
//
// What the app does that a browser tab can't: the microphone and her voice without extra clicks, the sound
// bounce for Bluetooth headphones, a Mac notification and the Dock's number for a new text, and
// "Turn everything on" in the View menu (desktop/hq_control.py fix).
// The routines keep running in the background; closing the app stops nothing.
// Built by desktop/build.sh with swiftc (no Xcode project needed).
import Cocoa
import WebKit
import CoreAudio
import UserNotifications

// ?app tells the page it's inside the app: it keeps the window buttons' spot free and leaves the texts'
// notifications to the app.
// HQ_PAGE is a test's own page (a test copy of HQ on another port).
let PAGE_URL = URL(string: ProcessInfo.processInfo.environment["HQ_PAGE"] ?? "http://127.0.0.1:7860/?app=1")!
// Her direct line's thread, from this Mac's status server, for the notifications.
let DIRECT_JSON = URL(string: "http://127.0.0.1:4748/direct.json")!
// The window's top band: a press there on an empty spot of the page moves the window. (No toolbar to make a
// real band of that height: a toolbar takes every press in it, and the page's own top buttons would be dead.)
let BAR: CGFloat = 52

func hqFolder() -> String {
    if let env = ProcessInfo.processInfo.environment["HQ_HOME"], !env.isEmpty { return env }
    if let p = Bundle.main.object(forInfoDictionaryKey: "HQPath") as? String, !p.isEmpty { return p }
    return NSString(string: "~/Documents/Claude/HQ").expandingTildeInPath
}

// "normal apps you can just. Click somewhere near the top and then you can just drag it around. So I just want
// it to be like a normal app." The page fills the window up to its top edge, and WebKit inside an app ignores a
// page's drag hint. So the page itself says when a press in the top band lands on nothing that can be pressed
// (the script below), and the app then moves the window with the press it kept; a double click does what the
// Mac's own setting for a title bar says (zoom, minimise or nothing).
let DRAG_SCRIPT = """
(function () {
  function free(t) {
    if (!t || !t.closest) return false;
    if (t.closest('button,a,input,textarea,select,label,summary,[role=button],[contenteditable],[draggable=true]')) return false;
    for (var e = t; e && e.nodeType === 1; e = e.parentElement) { if (getComputedStyle(e).cursor === 'pointer') return false; }
    return true;
  }
  window.__hqDowns = [];
  document.addEventListener('mousedown', function (ev) {
    if (window.__hqDowns.length < 20) window.__hqDowns.push([Math.round(ev.clientX), Math.round(ev.clientY)]);
    if (ev.button !== 0 || ev.clientY >= (window.__hqBar || 52) || !free(ev.target)) return;
    ev.preventDefault();
    try { webkit.messageHandlers.hqWindow.postMessage({ do: ev.detail >= 2 ? 'zoom' : 'drag' }); } catch (e) {}
  }, true);
})();
"""

final class PageView: WKWebView {
    var lastDown: NSEvent?
    override func mouseDown(with event: NSEvent) {
        lastDown = event
        super.mouseDown(with: event)
    }
}

final class Controller: NSObject, NSApplicationDelegate, WKScriptMessageHandler, WKNavigationDelegate,
                        WKUIDelegate, UNUserNotificationCenterDelegate {
    var window: NSWindow!
    var page: PageView!
    var timer: Timer?
    var pageFailed = false
    var pageLoaded = false
    var directBusy = false
    var directRead = false  // the selftest: her thread was read once
    var chatOpen = ""       // whose chat the page shows right now ("" when none), asked before each look at her thread
    let hq = hqFolder()
    // `HQ --selftest`: the real window, never seen; once the page is up it prints what it found (the page, the
    // window buttons and the spot kept free for them, a press on an empty spot and on a button), then quits.
    let selftest = CommandLine.arguments.contains("--selftest")
    var drags: [String] = []

    func applicationDidFinishLaunching(_ note: Notification) {
        buildMenu()
        window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 1180, height: 860),
                          styleMask: [.titled, .closable, .miniaturizable, .resizable, .fullSizeContentView],
                          backing: .buffered, defer: false)
        window.title = "HQ"
        window.titlebarAppearsTransparent = true
        window.titleVisibility = .hidden
        window.titlebarSeparatorStyle = .none
        window.minSize = NSSize(width: 720, height: 520)
        window.setFrameAutosaveName("HQMain")
        if !window.setFrameUsingName("HQMain") { window.center() }

        let conf = WKWebViewConfiguration()
        conf.mediaTypesRequiringUserActionForPlayback = []  // her voice plays without an extra click
        showRealAddress(conf.preferences)
        conf.userContentController.add(self, name: "hqAudio")   // the page asks for the sound bounce
        conf.userContentController.add(self, name: "hqWindow")  // a press on an empty spot of the top band
        conf.userContentController.addUserScript(WKUserScript(source: DRAG_SCRIPT, injectionTime: .atDocumentEnd, forMainFrameOnly: true))
        page = PageView(frame: .zero, configuration: conf)
        page.navigationDelegate = self
        page.uiDelegate = self
        page.allowsBackForwardNavigationGestures = false
        let saved = UserDefaults.standard.double(forKey: "pageZoom")
        if saved >= 0.5 && saved <= 2.0 { page.pageZoom = CGFloat(saved) }
        page.translatesAutoresizingMaskIntoConstraints = false
        let content = NSView()
        window.contentView = content
        content.addSubview(page)
        NSLayoutConstraint.activate([
            page.topAnchor.constraint(equalTo: content.topAnchor),
            page.leadingAnchor.constraint(equalTo: content.leadingAnchor),
            page.trailingAnchor.constraint(equalTo: content.trailingAnchor),
            page.bottomAnchor.constraint(equalTo: content.bottomAnchor),
        ])
        page.load(URLRequest(url: PAGE_URL))  // the microphone is only asked for when a call starts

        if selftest {
            window.alphaValue = 0
            window.orderFront(nil)
            DispatchQueue.main.asyncAfter(deadline: .now() + 40) { print("{\"selftest\": \"timed out\"}"); exit(1) }
        } else {
            let nc = UNUserNotificationCenter.current()  // her texts as Mac notifications; macOS asks once
            nc.delegate = self
            nc.requestAuthorization(options: [.alert, .sound, .badge]) { _, _ in }
            window.makeKeyAndOrderFront(nil)
            NSApp.activate(ignoringOtherApps: true)
            window.makeFirstResponder(page)  // the space bar reaches the page from the start
        }
        timer = Timer.scheduledTimer(withTimeInterval: 5, repeats: true) { [weak self] _ in self?.tick() }
    }

    // Every 5 seconds: a page that didn't load is tried again, and her thread is looked at.
    func tick() {
        if pageFailed { pageFailed = false; page.load(URLRequest(url: PAGE_URL)) }
        pollDirect()
    }

    // H198: Bluetooth headphones whose own mic was opened stay in call quality (low) until the Mac's sound output
    // is chosen again. His workaround, done for him: once the call listens with the MacBook's own mic, the sound
    // goes to the MacBook's speakers for a moment and straight back to the headphones, and they come back in
    // high quality. Only when the sound is on Bluetooth and the MacBook has speakers of its own.
    func bounceSound() {
        func prop(_ sel: AudioObjectPropertySelector, _ scope: AudioObjectPropertyScope = kAudioObjectPropertyScopeGlobal) -> AudioObjectPropertyAddress {
            AudioObjectPropertyAddress(mSelector: sel, mScope: scope, mElement: kAudioObjectPropertyElementMain)
        }
        func getDefault() -> AudioDeviceID? {
            var id = AudioDeviceID(0), size = UInt32(MemoryLayout<AudioDeviceID>.size)
            var a = prop(kAudioHardwarePropertyDefaultOutputDevice)
            return AudioObjectGetPropertyData(AudioObjectID(kAudioObjectSystemObject), &a, 0, nil, &size, &id) == noErr ? id : nil
        }
        func setDefault(_ dev: AudioDeviceID) {
            var id = dev
            var a = prop(kAudioHardwarePropertyDefaultOutputDevice)
            _ = AudioObjectSetPropertyData(AudioObjectID(kAudioObjectSystemObject), &a, 0, nil, UInt32(MemoryLayout<AudioDeviceID>.size), &id)
        }
        func transport(_ dev: AudioDeviceID) -> UInt32 {
            var t = UInt32(0), size = UInt32(MemoryLayout<UInt32>.size)
            var a = prop(kAudioDevicePropertyTransportType)
            return AudioObjectGetPropertyData(dev, &a, 0, nil, &size, &t) == noErr ? t : 0
        }
        func hasOutput(_ dev: AudioDeviceID) -> Bool {
            var size = UInt32(0)
            var a = prop(kAudioDevicePropertyStreams, kAudioObjectPropertyScopeOutput)
            return AudioObjectGetPropertyDataSize(dev, &a, 0, nil, &size) == noErr && size > 0
        }
        var size = UInt32(0)
        var all = prop(kAudioHardwarePropertyDevices)
        guard AudioObjectGetPropertyDataSize(AudioObjectID(kAudioObjectSystemObject), &all, 0, nil, &size) == noErr, size > 0 else { return }
        var devs = [AudioDeviceID](repeating: 0, count: Int(size) / MemoryLayout<AudioDeviceID>.size)
        guard AudioObjectGetPropertyData(AudioObjectID(kAudioObjectSystemObject), &all, 0, nil, &size, &devs) == noErr else { return }
        guard let now = getDefault() else { return }
        let bt = transport(now)
        guard bt == kAudioDeviceTransportTypeBluetooth || bt == kAudioDeviceTransportTypeBluetoothLE else { return }
        guard let own = devs.first(where: { transport($0) == kAudioDeviceTransportTypeBuiltIn && hasOutput($0) }) else { return }
        setDefault(own)
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.6) { setDefault(now) }
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

    // The page bigger or smaller, with Cmd +, Cmd − and Cmd 0. In steps like Safari's; remembered for next time.
    let ZOOMS: [CGFloat] = [0.5, 0.67, 0.75, 0.8, 0.9, 1.0, 1.1, 1.25, 1.5, 1.75, 2.0]
    func zoom(_ by: Int) {
        let now = page.pageZoom
        var next: CGFloat = 1.0
        if by > 0 { next = ZOOMS.first { $0 > now + 0.001 } ?? ZOOMS.last! }
        if by < 0 { next = ZOOMS.last { $0 < now - 0.001 } ?? ZOOMS.first! }
        page.pageZoom = next
        UserDefaults.standard.set(Double(next), forKey: "pageZoom")
        tellBar()
    }
    // The top band in the page's own points (they grow and shrink with the zoom).
    func tellBar() { page.evaluateJavaScript("window.__hqBar = \(Double(BAR / page.pageZoom))", completionHandler: nil) }
    @objc func zoomIn() { zoom(1) }
    @objc func zoomOut() { zoom(-1) }
    @objc func zoomReset() { zoom(0) }

    func applicationShouldTerminateAfterLastWindowClosed(_ app: NSApplication) -> Bool { true }

    // MARK: turning on what's off

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

    // View > Turn everything on: the status page, the helper, the watchdog, the call line. It only turns on
    // what's off; it never stops or restarts what runs. What it did is said in the page's own line at the bottom.
    func fix() {
        say("Turning on what\u{2019}s off\u{2026}")
        runControl(["fix"]) { [weak self] json in
            guard let self = self else { return }
            var said = "Nothing was off."
            if let data = json.data(using: .utf8),
               let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
               let fixed = obj["fixed"] as? [[String: Any]], !fixed.isEmpty {
                said = fixed.map { ($0["what"] as? String ?? "") + ((($0["ok"] as? Bool) ?? false) ? "" : " (didn't work)") }
                    .joined(separator: " · ")
            }
            // Things need a moment to start. A page that hadn't loaded is loaded now; one that works is left alone
            // (a call may be on).
            DispatchQueue.main.asyncAfter(deadline: .now() + 6) {
                if self.pageFailed || !self.pageLoaded { self.pageFailed = false; self.page.load(URLRequest(url: PAGE_URL)) }
                else { self.say(said) }
            }
        }
    }

    func say(_ text: String) {
        let quoted = String(data: try! JSONSerialization.data(withJSONObject: [text], options: []), encoding: .utf8)!
        page.evaluateJavaScript("window.HQ && HQ.component && HQ.component.say && HQ.component.say(\(quoted)[0])", completionHandler: nil)
    }

    // MARK: her texts

    // Every 5 seconds: her thread from the status server. A text that's new gets a Mac notification, once, also
    // after a restart (the first time everything already there counts as read); the Dock shows how many are
    // unread. Never while her chat is the one in front of him. Nothing is sent from here: the phone gets its
    // push from the routine as before.
    var looking: Bool {
        chatOpen == "donna" && NSApp.isActive && window.isVisible && !window.isMiniaturized
    }

    func pollDirect() {
        guard pageLoaded, !directBusy else { return }
        directBusy = true
        let whose = "(function () { var a = window.HQ && HQ.component; if (!a || document.hidden) return ''; var s = a.state || {};" +
            " if (s.screen === 'chat') return s.chatAgent || '';" +
            " if (s.design === 'thread' && a.device === 'mac') return (s.screen === 'call' || s.screen === 'transcript') ? '' : (s.space || '');" +
            " return ''; })()"
        page.evaluateJavaScript(whose) { [weak self] out, _ in
            guard let self = self else { return }
            self.chatOpen = (out as? String) ?? ""
            var req = URLRequest(url: DIRECT_JSON)
            req.cachePolicy = .reloadIgnoringLocalCacheData
            req.timeoutInterval = 4
            URLSession.shared.dataTask(with: req) { [weak self] data, resp, _ in
                DispatchQueue.main.async {
                    guard let self = self else { return }
                    self.directBusy = false
                    guard let data = data, (resp as? HTTPURLResponse)?.statusCode == 200,
                          let d = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else { return }
                    self.directRead = true
                    if self.selftest { return }  // the selftest reads, never marks or notifies
                    self.inbox(d)
                }
            }.resume()
        }
    }

    // `seen` is the newest text he had in front of him, `told` the newest a notification was shown for.
    func inbox(_ d: [String: Any]) {
        func at(_ m: [String: Any]) -> Double { (m["at"] as? NSNumber)?.doubleValue ?? 0 }
        let msgs = d["messages"] as? [[String: Any]] ?? []
        let name = ((d["agent"] as? [String: Any])?["name"] as? String).flatMap { $0.isEmpty ? nil : $0 } ?? "HQ"
        let newest = msgs.map(at).max() ?? 0
        let ud = UserDefaults.standard
        var seen = ud.double(forKey: "directSeen"), told = ud.double(forKey: "directTold")
        if ud.object(forKey: "directSeen") == nil || ud.object(forKey: "directTold") == nil { seen = newest; told = newest }
        if looking { seen = max(seen, newest) }
        // her note for herself never reaches him
        let hers = msgs.filter { ($0["from"] as? String) != "me" && !(($0["quiet"] as? NSNumber)?.boolValue ?? false) }
        let fresh = looking ? [] : Array(hers.filter { at($0) > told }.suffix(3))
        told = max(told, newest)
        ud.set(seen, forKey: "directSeen")
        ud.set(told, forKey: "directTold")
        let unread = hers.filter { at($0) > seen }.count
        NSApp.dockTile.badgeLabel = unread > 0 ? String(unread) : nil
        for m in fresh { notify(name, m["text"] as? String ?? "", at: at(m)) }
    }

    func notify(_ name: String, _ text: String, at: Double) {
        let c = UNMutableNotificationContent()
        c.title = name
        c.body = text
        c.sound = .default
        c.userInfo = ["open": "direct"]
        // One id per text: the same text is never shown twice, even if asked again.
        UNUserNotificationCenter.current().add(UNNotificationRequest(identifier: "direct-\(at)", content: c, trigger: nil))
    }

    // Shown also while the app is in front, unless he's already looking at her chat.
    func userNotificationCenter(_ c: UNUserNotificationCenter, willPresent n: UNNotification,
                                withCompletionHandler done: @escaping (UNNotificationPresentationOptions) -> Void) {
        DispatchQueue.main.async { done(self.looking ? [] : [.banner, .sound, .list]) }
    }

    // A click on her text opens her chat in the page (the same move as a tapped text on the phone).
    func userNotificationCenter(_ c: UNUserNotificationCenter, didReceive r: UNNotificationResponse,
                                withCompletionHandler done: @escaping () -> Void) {
        DispatchQueue.main.async {
            NSApp.activate(ignoringOtherApps: true)
            self.window.makeKeyAndOrderFront(nil)
            self.page.evaluateJavaScript("(function () { var a = window.HQ && HQ.component; if (!a || !a.go) return;" +
                " if (a.state && a.state.design === 'thread') a.go('donna', { space: 'donna' }); else a.go('chat', { chatAgent: 'donna', space: 'donna' }); })()") { _, _ in
                self.pollDirect()
            }
            done()
        }
    }

    func applicationDidBecomeActive(_ note: Notification) { pollDirect() }

    // MARK: the page

    func webView(_ v: WKWebView, didFinish nav: WKNavigation!) {
        if v.url?.host == PAGE_URL.host && v.url?.port == PAGE_URL.port { pageLoaded = true }
        tellBar()
        if selftest { report(0) } else { window.makeFirstResponder(page) }
    }

    func userContentController(_ ucc: WKUserContentController, didReceive message: WKScriptMessage) {
        guard let m = message.body as? [String: Any], let what = m["do"] as? String else { return }
        if message.name == "hqAudio" {
            if what == "bounce" { bounceSound() }
            return
        }
        drags.append(what)
        if selftest { return }
        if what == "drag", let e = page.lastDown { window.performDrag(with: e) }
        if what == "zoom" {
            switch UserDefaults.standard.string(forKey: "AppleActionOnDoubleClick") ?? "Maximize" {
            case "Minimize": window.miniaturize(nil)
            case "None": break
            default: window.zoom(nil)
            }
        }
    }

    func webView(_ v: WKWebView, didFailProvisionalNavigation nav: WKNavigation!, withError error: Error) {
        v.loadHTMLString("""
            <html><body style="font:15px -apple-system;color:#888;display:flex;align-items:center;justify-content:center;height:90vh;background:transparent">
            <div style="text-align:center"><p>HQ doesn't answer yet.</p><p>In the menu bar: View, Turn everything on.</p></div></body></html>
            """, baseURL: nil)
        pageLoaded = false
        pageFailed = true
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

    // MARK: the selftest

    // A made-up mouse press never reaches a web page in a window nobody sees, so the selftest checks the two
    // halves apart: which view AppKit gives a press at a spot (the page, or the title bar), and what the page's
    // own script does with a press there.
    func whoGets(_ x: CGFloat, _ y: CGFloat) -> String {
        guard let frame = window.contentView?.superview else { return "?" }
        let p = frame.convert(NSPoint(x: x, y: window.contentView!.bounds.height - y), from: window.contentView)
        guard let v = frame.hitTest(p) else { return "nothing" }
        return v === page || v.isDescendant(of: page) ? "page" : String(describing: type(of: v))
    }
    func press(_ x: CGFloat, _ y: CGFloat) {
        page.evaluateJavaScript("(function () { var t = document.elementFromPoint(\(Double(x)), \(Double(y))); if (t) t.dispatchEvent(new MouseEvent('mousedown', { clientX: \(Double(x)), clientY: \(Double(y)), button: 0, detail: 1, bubbles: true, cancelable: true })); })()", completionHandler: nil)
    }

    func report(_ tries: Int) {
        // Wait for the page's own start (its three designs) and her thread.
        let ask = "JSON.stringify((function () { var a = window.HQ && HQ.component; var sp = document.querySelector('[data-window-buttons]');" +
            " if (!a || !document.querySelector('button')) return null;" +
            " var r = sp ? sp.getBoundingClientRect() : null;" +
            " var b = [].slice.call(document.querySelectorAll('button')).map(function (e) { return e.getBoundingClientRect(); })" +
            "   .filter(function (q) { return q.width > 8 && q.top < 52 && q.bottom > 0 && q.left > 110; })[0];" +
            " return { title: document.title, device: a.device, design: a.state && a.state.design," +
            "   spot: r ? [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)] : null," +
            "   button: b ? [Math.round(b.left + b.width / 2), Math.round(b.top + b.height / 2)] : null," +
            "   old_strip: !!document.querySelector('.tabs, #dog, #tab-status') }; })())"
        page.evaluateJavaScript(ask) { out, _ in
            guard let text = out as? String, text != "null", self.directRead || tries > 20 else {
                if tries > 60 { print("{\"selftest\": \"the page didn't start\"}"); exit(1) }
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) { self.pollDirect(); self.report(tries + 1) }
                return
            }
            let found = (try? JSONSerialization.jsonObject(with: Data(text.utf8)) as? [String: Any]) ?? [:]
            // The window's own buttons, from the window's top left.
            let h = self.window.contentView!.bounds.height
            let lights = [NSWindow.ButtonType.closeButton, .miniaturizeButton, .zoomButton].compactMap { t -> [Int]? in
                guard let b = self.window.standardWindowButton(t) else { return nil }
                let f = b.convert(b.bounds, to: nil)
                return [Int(f.minX.rounded()), Int((h - f.maxY).rounded()), Int(f.width.rounded()), Int(f.height.rounded())]
            }
            // A press on an empty spot of the top band asks to move the window; a press on a button doesn't.
            let w = self.window.contentView!.bounds.width
            self.drags = []
            self.press(w / 2, h / 2)  // a press in the middle of the page, to know presses arrive at all
            self.press(w / 2, 6)
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.6) {
                let empty = self.drags
                self.drags = []
                let spot = (found["button"] as? [NSNumber]).map { [$0[0].doubleValue, $0[1].doubleValue] }
                if let s = spot { self.press(CGFloat(s[0]), CGFloat(s[1])) }
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.6) {
                    self.page.evaluateJavaScript("JSON.stringify(window.__hqDowns || [])") { downs, _ in
                        var o: [String: Any] = found
                        o["page_loaded"] = self.pageLoaded
                        o["window_buttons"] = lights
                        o["views_in_window"] = self.window.contentView!.subviews.count
                        o["empty_spot_moves"] = empty.contains("drag")
                        o["button_moves"] = self.drags.contains("drag")
                        o["page_got_presses"] = (downs as? String) ?? "[]"
                        o["who_gets"] = ["empty_top": self.whoGets(w / 2, 6), "middle": self.whoGets(w / 2, h / 2),
                                         "top_button": spot.map { self.whoGets(CGFloat($0[0]), CGFloat($0[1])) } ?? "none",
                                         "beside_window_buttons": self.whoGets(100, 14), "close_button": self.whoGets(14, 14)]
                        o["direct_read"] = self.directRead
                        let data = try! JSONSerialization.data(withJSONObject: o, options: [.sortedKeys])
                        print(String(data: data, encoding: .utf8)!)
                        fflush(stdout)
                        exit(0)
                    }
                }
            }
        }
    }

    // MARK: menu

    @objc func reloadPage() { pageFailed = false; page.load(URLRequest(url: PAGE_URL)) }
    @objc func fixAll() { fix() }

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
        sub("View", [item("Bigger", #selector(zoomIn), "+", self), hidden(item("Bigger", #selector(zoomIn), "=", self)),
                     item("Smaller", #selector(zoomOut), "-", self), item("Actual Size", #selector(zoomReset), "0", self), .separator(),
                     item("Reload", #selector(reloadPage), "r", self), item("Turn everything on", #selector(fixAll), "t", self)])
        sub("Window", [item("Minimize", #selector(NSWindow.performMiniaturize(_:)), "m"),
                       item("Close", #selector(NSWindow.performClose(_:)), "w")])
        NSApp.mainMenu = main
    }
}

// `HQ --check`: the paths it would use and whether its file is there, without a window.
if CommandLine.arguments.contains("--check") {
    let hq = hqFolder()
    let controlOK = FileManager.default.fileExists(atPath: hq + "/desktop/hq_control.py")
    print("{\"hq\": \"\(hq)\", \"control\": \(controlOK), \"page\": \"\(PAGE_URL)\"}")
    exit(controlOK ? 0 : 1)
}

let app = NSApplication.shared
let controller = Controller()
app.delegate = controller
app.setActivationPolicy(.regular)
app.run()
