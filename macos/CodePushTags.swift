import AppKit

struct SoundTag: Decodable {
    let id: String
    let text: String
    let file: String
    let event: String?
    let use_cases: [String]?
}

struct Manifest: Decodable {
    let tags: [SoundTag]
}

struct Repository: Codable {
    let full_name: String
    let organization: Bool
}

private let mint = NSColor(srgbRed: 0.54, green: 0.96, blue: 0.69, alpha: 1)
private let coral = NSColor(srgbRed: 1, green: 0.42, blue: 0.43, alpha: 1)
private let violet = NSColor(srgbRed: 0.69, green: 0.61, blue: 1, alpha: 1)

final class HardwareView: NSView {
    override func draw(_ dirtyRect: NSRect) {
        NSColor(srgbRed: 0.075, green: 0.08, blue: 0.09, alpha: 1).setFill()
        bounds.fill()
        NSColor.white.withAlphaComponent(0.016).setStroke()
        let lines = NSBezierPath()
        for y in stride(from: CGFloat(0), through: bounds.height, by: 5) {
            lines.move(to: NSPoint(x: 0, y: y)); lines.line(to: NSPoint(x: bounds.width, y: y))
        }
        lines.stroke()
        for point in [NSPoint(x: 11, y: 11), NSPoint(x: bounds.width - 11, y: 11),
                      NSPoint(x: 11, y: bounds.height - 11), NSPoint(x: bounds.width - 11, y: bounds.height - 11)] {
            NSColor.black.withAlphaComponent(0.7).setFill()
            NSBezierPath(ovalIn: NSRect(x: point.x - 3, y: point.y - 3, width: 6, height: 6)).fill()
            NSColor.white.withAlphaComponent(0.16).setStroke()
            let slot = NSBezierPath(); slot.move(to: NSPoint(x: point.x - 2, y: point.y)); slot.line(to: NSPoint(x: point.x + 2, y: point.y)); slot.stroke()
        }
    }
}

class HardwareButton: NSButton {
    var accent: NSColor = mint
    override func draw(_ dirtyRect: NSRect) {
        let pressed = isHighlighted || state == .on
        let rect = bounds.insetBy(dx: 1, dy: 1)
        NSColor(srgbRed: pressed ? 0.2 : 0.13, green: pressed ? 0.21 : 0.14, blue: pressed ? 0.23 : 0.16, alpha: 1).setFill()
        let path = NSBezierPath(roundedRect: rect, xRadius: 7, yRadius: 7)
        path.fill()
        accent.withAlphaComponent(pressed ? 0.9 : 0.4).setStroke(); path.lineWidth = 1; path.stroke()
        let paragraph = NSMutableParagraphStyle(); paragraph.alignment = .center
        (title as NSString).draw(in: NSRect(x: 8, y: (bounds.height - 16) / 2, width: bounds.width - 16, height: 18),
                                withAttributes: [.font: NSFont.monospacedSystemFont(ofSize: 11, weight: .semibold), .foregroundColor: accent, .paragraphStyle: paragraph])
    }
}

final class SoundPad: NSButton {
    var number = 0
    var label = ""
    var category = ""
    var accent = mint
    var playing = false { didSet { needsDisplay = true } }
    override func draw(_ dirtyRect: NSRect) {
        let active = playing || isHighlighted
        let base = bounds.insetBy(dx: 2, dy: 2)
        NSColor.black.withAlphaComponent(0.65).setFill()
        NSBezierPath(roundedRect: base.offsetBy(dx: 0, dy: -1), xRadius: 9, yRadius: 9).fill()
        let face = base.insetBy(dx: 1, dy: 1)
        let path = NSBezierPath(roundedRect: face, xRadius: 8, yRadius: 8)
        let top = active ? accent.withAlphaComponent(0.32) : NSColor(srgbRed: 0.19, green: 0.20, blue: 0.23, alpha: 1)
        let bottom = active ? accent.withAlphaComponent(0.14) : NSColor(srgbRed: 0.12, green: 0.13, blue: 0.15, alpha: 1)
        NSGradient(starting: bottom, ending: top)?.draw(in: path, angle: 90)
        accent.withAlphaComponent(active ? 1 : 0.45).setStroke(); path.lineWidth = active ? 2 : 1; path.stroke()
        (String(format: "%02d", number) as NSString).draw(at: NSPoint(x: 13, y: bounds.height - 24),
            withAttributes: [.font: NSFont.monospacedSystemFont(ofSize: 10, weight: .medium), .foregroundColor: accent.withAlphaComponent(0.75)])
        ((active ? "●" : "▸") as NSString).draw(at: NSPoint(x: bounds.width - 24, y: bounds.height - 25),
            withAttributes: [.font: NSFont.systemFont(ofSize: 12), .foregroundColor: accent])
        let paragraph = NSMutableParagraphStyle(); paragraph.alignment = .left; paragraph.lineBreakMode = .byWordWrapping
        (label as NSString).draw(in: NSRect(x: 13, y: 25, width: bounds.width - 26, height: 31),
            withAttributes: [.font: NSFont.monospacedSystemFont(ofSize: 12, weight: .bold), .foregroundColor: NSColor.white.withAlphaComponent(0.94), .paragraphStyle: paragraph])
        (category as NSString).draw(at: NSPoint(x: 13, y: 13),
            withAttributes: [.font: NSFont.monospacedSystemFont(ofSize: 8, weight: .medium), .foregroundColor: NSColor.white.withAlphaComponent(0.4)])
        accent.withAlphaComponent(active ? 1 : 0.55).setFill()
        NSBezierPath(roundedRect: NSRect(x: bounds.width - 39, y: 15, width: 25, height: 3), xRadius: 1.5, yRadius: 1.5).fill()
    }
}

final class AppDelegate: NSObject, NSApplicationDelegate, NSSoundDelegate {
    private let events = [("push", "Successful push"), ("merge", "PR merged"), ("ci", "PR CI failure")]
    private var tags: [SoundTag] = []
    private var popups: [String: NSPopUpButton] = [:]
    private var switches: [String: NSButton] = [:]
    private let status = NSTextField(wrappingLabelWithString: "Choose your sounds. Enable the tool when you are ready.")
    private let muteButton = HardwareButton(title: "MUTE ALL", target: nil, action: nil)
    private let powerStatus = NSTextField(labelWithString: "●  SOUNDS ON")
    private let scopeStatus = NSTextField(labelWithString: "ALL ACCESSIBLE REPOSITORIES")
    private let previewStatus = NSTextField(labelWithString: "READY TO PLAY")
    private var pads: [String: SoundPad] = [:]
    private let padGrid = NSStackView()
    private let bankCount = NSTextField(labelWithString: "")
    private var filterButtons: [String: HardwareButton] = [:]
    private var soundFilter = "all"
    private let transportHost = NSStackView()
    private var transportArt: [String: TransportArtwork] = [:]
    private var layoutStyle = "dj"
    private var previewSound: NSSound?
    private var previewID: String?
    private var window: NSWindow!
    private var statusItem: NSStatusItem!
    private var muted = false
    private var timer: Timer?
    private var repositorySheet: RepositorySheet?
    private var repositoryCatalog: [Repository]?
    private var catalogLoading = false
    private let queue = DispatchQueue(label: "code-push-tags.commands")
    private let muteQueue = DispatchQueue(label: "code-push-tags.mute", qos: .userInteractive)
    private let githubQueue = DispatchQueue(label: "code-push-tags.github", qos: .userInitiated)
    private var kit: URL { Bundle.main.resourceURL!.appendingPathComponent("kit") }
    private var state: URL {
        if let path = ProcessInfo.processInfo.environment["PUSH_TAGS_STATE_DIR"] {
            return URL(fileURLWithPath: path)
        }
        return FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Library/Application Support/Code Push Tags")
    }
    private var environment: [String: String] {
        var values = ProcessInfo.processInfo.environment
        values["PATH"] = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:" + (values["PATH"] ?? "")
        values["PYTHONDONTWRITEBYTECODE"] = "1"
        return values
    }

    func applicationDidFinishLaunching(_ notification: Notification) {
        do {
            tags = try JSONDecoder().decode(Manifest.self, from: Data(contentsOf: kit.appendingPathComponent("manifest.json"))).tags
        } catch {
            alert("The sound library could not be opened.", error.localizedDescription)
            NSApp.terminate(nil)
            return
        }
        layoutStyle = readObject("appearance.json")["layout"] as? String == "boombox" ? "boombox" : "dj"
        makeMenus()
        makeWindow()
        refreshSettings()
        timer = Timer.scheduledTimer(withTimeInterval: 2, repeats: true) { [weak self] _ in self?.refreshSettings() }
        showWindow()
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { false }

    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool {
        showWindow()
        return true
    }

    private func makeMenus() {
        let main = NSMenu()
        let appItem = NSMenuItem()
        let appMenu = NSMenu()
        appMenu.addItem(withTitle: "Quit Code Push Tags", action: #selector(quit), keyEquivalent: "q").target = self
        appItem.submenu = appMenu
        main.addItem(appItem)
        NSApp.mainMenu = main

        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.squareLength)
        let menu = NSMenu()
        menu.addItem(withTitle: "Show Code Push Tags", action: #selector(showWindow), keyEquivalent: "").target = self
        menu.addItem(withTitle: "Mute all sounds", action: #selector(toggleMute), keyEquivalent: "").target = self
        menu.addItem(.separator())
        menu.addItem(withTitle: "Quit", action: #selector(quit), keyEquivalent: "").target = self
        statusItem.menu = menu
    }

    private func label(_ text: String, size: CGFloat = 10, color: NSColor = .secondaryLabelColor) -> NSTextField {
        let field = NSTextField(labelWithString: text)
        field.font = .monospacedSystemFont(ofSize: size, weight: .medium)
        field.textColor = color
        return field
    }

    private func hardwareButton(_ title: String, action: Selector, color: NSColor = mint) -> HardwareButton {
        let button = HardwareButton(title: title, target: self, action: action)
        button.accent = color
        button.isBordered = false
        button.heightAnchor.constraint(equalToConstant: 32).isActive = true
        return button
    }

    private func eventPopup(_ event: String, width: CGFloat) -> NSPopUpButton {
        let popup = NSPopUpButton(frame: .zero, pullsDown: false)
        for tag in tags {
            popup.addItem(withTitle: tag.text)
            popup.lastItem?.representedObject = tag.id
        }
        popup.identifier = NSUserInterfaceItemIdentifier(event)
        popup.target = self; popup.action = #selector(saveSelection)
        popup.font = .systemFont(ofSize: 12, weight: .medium)
        popup.widthAnchor.constraint(equalToConstant: width).isActive = true
        popups[event] = popup
        return popup
    }

    private func eventToggle(_ event: String, title: String, color: NSColor) -> NSButton {
        let enabled = NSButton(checkboxWithTitle: title, target: self, action: #selector(saveSelection))
        enabled.font = .monospacedSystemFont(ofSize: 10, weight: .semibold)
        enabled.contentTintColor = color
        enabled.identifier = NSUserInterfaceItemIdentifier(event)
        switches[event] = enabled
        return enabled
    }

    private func cueButton(_ event: String, color: NSColor) -> HardwareButton {
        let cue = hardwareButton("CUE  ▶", action: #selector(previewEvent), color: color)
        cue.identifier = NSUserInterfaceItemIdentifier(event)
        cue.setAccessibilityLabel("Preview " + event + " sound")
        return cue
    }

    private func panel(width: CGFloat, height: CGFloat) -> (NSView, NSStackView) {
        let panel = NSView()
        panel.wantsLayer = true
        panel.layer?.backgroundColor = NSColor(srgbRed: 0.10, green: 0.11, blue: 0.13, alpha: 1).cgColor
        panel.layer?.cornerRadius = 12
        panel.layer?.borderWidth = 1
        panel.layer?.borderColor = NSColor.white.withAlphaComponent(0.1).cgColor
        panel.widthAnchor.constraint(equalToConstant: width).isActive = true
        panel.heightAnchor.constraint(equalToConstant: height).isActive = true
        let stack = NSStackView()
        stack.orientation = .vertical; stack.alignment = .centerX; stack.spacing = 6
        stack.translatesAutoresizingMaskIntoConstraints = false
        panel.addSubview(stack)
        NSLayoutConstraint.activate([
            stack.leadingAnchor.constraint(equalTo: panel.leadingAnchor, constant: 12),
            stack.trailingAnchor.constraint(equalTo: panel.trailingAnchor, constant: -12),
            stack.topAnchor.constraint(equalTo: panel.topAnchor, constant: 10),
            stack.bottomAnchor.constraint(equalTo: panel.bottomAnchor, constant: -10)
        ])
        return (panel, stack)
    }

    private func eventDeck(_ event: String, title: String, color: NSColor) -> NSView {
        let boom = layoutStyle == "boombox"
        let width: CGFloat = boom ? 300 : 392
        let (deck, stack) = panel(width: width, height: 232)
        let headerSpacer = NSView(); headerSpacer.setContentHuggingPriority(.defaultLow, for: .horizontal)
        let header = NSStackView(views: [label(title, size: 11, color: color), headerSpacer, label("33⅓  /  STEREO", size: 8)])
        stack.addArrangedSubview(header)
        header.widthAnchor.constraint(equalTo: stack.widthAnchor).isActive = true
        let vinyl = TransportArtwork()
        vinyl.style = boom ? .speaker : .vinyl
        transportArt[event] = vinyl
        vinyl.accent = color
        vinyl.widthAnchor.constraint(equalToConstant: 124).isActive = true
        vinyl.heightAnchor.constraint(equalToConstant: 124).isActive = true
        stack.addArrangedSubview(vinyl)
        stack.addArrangedSubview(eventPopup(event, width: width - 24))
        let toggle = eventToggle(event, title: "AUTO-PLAY", color: color)
        let space = NSView(); space.setContentHuggingPriority(.defaultLow, for: .horizontal)
        let cue = cueButton(event, color: color)
        cue.widthAnchor.constraint(equalToConstant: 114).isActive = true
        let controls = NSStackView(views: [toggle, space, cue]); controls.spacing = 10
        stack.addArrangedSubview(controls)
        controls.widthAnchor.constraint(equalTo: stack.widthAnchor).isActive = true
        return deck
    }

    private func masterPanel() -> NSView {
        let boom = layoutStyle == "boombox"
        let width: CGFloat = boom ? 400 : 216
        let (master, stack) = panel(width: width, height: 232)
        let heading = NSStackView(views: [label(boom ? "STEREO CASSETTE" : "MASTER", size: 11, color: .white), powerStatus])
        heading.spacing = 12
        stack.addArrangedSubview(heading)
        powerStatus.font = .monospacedSystemFont(ofSize: 9, weight: .semibold)
        if boom {
            let tape = TransportArtwork()
            tape.style = .cassette; tape.accent = mint
            tape.widthAnchor.constraint(equalToConstant: 260).isActive = true
            tape.heightAnchor.constraint(equalToConstant: 76).isActive = true
            transportArt["cassette"] = tape
            stack.addArrangedSubview(tape)
        }
        muteButton.target = self; muteButton.action = #selector(toggleMute); muteButton.isBordered = false
        muteButton.translatesAutoresizingMaskIntoConstraints = false
        muteButton.heightAnchor.constraint(equalToConstant: boom ? 32 : 44).isActive = true
        stack.addArrangedSubview(muteButton)
        muteButton.widthAnchor.constraint(equalTo: stack.widthAnchor).isActive = true
        if !boom {
            let separator = NSBox(); separator.boxType = .separator
            stack.addArrangedSubview(separator)
            separator.widthAnchor.constraint(equalTo: stack.widthAnchor).isActive = true
            stack.addArrangedSubview(label("FAILURE FX", size: 9, color: coral))
        }
        let toggle = eventToggle("ci", title: "CI / CD", color: coral)
        if !boom { stack.addArrangedSubview(toggle) }
        stack.addArrangedSubview(eventPopup("ci", width: width - 24))
        let cue = cueButton("ci", color: coral)
        if boom {
            let controls = NSStackView(views: [toggle, cue]); controls.spacing = 20
            cue.widthAnchor.constraint(equalToConstant: 170).isActive = true
            stack.addArrangedSubview(controls)
        } else {
            cue.widthAnchor.constraint(equalToConstant: width - 24).isActive = true
            stack.addArrangedSubview(cue)
        }
        return master
    }

    private func rebuildTransport() {
        for artwork in transportArt.values { artwork.setRunning(false) }
        transportArt.removeAll()
        for view in transportHost.arrangedSubviews {
            transportHost.removeArrangedSubview(view); view.removeFromSuperview()
        }
        // Remove constraints from the previous layout before the shared controls move.
        NSLayoutConstraint.deactivate(muteButton.constraints)
        popups.removeAll(); switches.removeAll()
        let boom = layoutStyle == "boombox"
        transportHost.addArrangedSubview(eventDeck("push", title: boom ? "LEFT / PUSH" : "DECK A / PUSH", color: mint))
        transportHost.addArrangedSubview(masterPanel())
        transportHost.addArrangedSubview(eventDeck("merge", title: boom ? "RIGHT / MERGE" : "DECK B / MERGE", color: violet))
    }

    @objc private func changeLayout(_ sender: NSSegmentedControl) {
        let selected = sender.selectedSegment == 1 ? "boombox" : "dj"
        do {
            try FileManager.default.createDirectory(at: state, withIntermediateDirectories: true, attributes: [.posixPermissions: 0o700])
            let data = try JSONSerialization.data(withJSONObject: ["layout": selected])
            try data.write(to: state.appendingPathComponent("appearance.json"), options: .atomic)
        } catch {
            sender.selectedSegment = layoutStyle == "boombox" ? 1 : 0
            alert("Layout could not be saved.", error.localizedDescription)
            return
        }
        layoutStyle = selected
        rebuildTransport(); refreshSettings()
        if previewSound?.isPlaying == true { animateTransport(for: previewID) }
        for artwork in transportArt.values { artwork.pulse() }
        status.stringValue = "Layout saved on this Mac."
    }

    private func animateTransport(for tag: String?, event: String? = nil, pulse: Bool = false) {
        let matching = ["push", "merge"].filter { popups[$0]?.selectedItem?.representedObject as? String == tag }
        let fallback = tags.first(where: { $0.id == tag }).map { useCases($0).contains("merge") ? "merge" : "push" } ?? "push"
        for (key, artwork) in transportArt {
            let selected = key == "cassette" || key == event || (event == nil && (matching.isEmpty ? key == fallback : matching.contains(key)))
            if selected {
                if pulse { artwork.pulse() } else { artwork.setRunning(true) }
            }
        }
    }

    private func makeWindow() {
        window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 1080, height: 850),
                          styleMask: [.titled, .closable, .miniaturizable], backing: .buffered, defer: false)
        window.title = "Code Push Tags"
        window.isReleasedWhenClosed = false
        window.appearance = NSAppearance(named: .darkAqua)
        window.titlebarAppearsTransparent = true
        window.backgroundColor = NSColor(srgbRed: 0.075, green: 0.08, blue: 0.09, alpha: 1)
        window.center()
        let enclosure = HardwareView()
        window.contentView = enclosure
        let outer = NSStackView()
        outer.orientation = .vertical; outer.alignment = .leading; outer.spacing = 10
        outer.translatesAutoresizingMaskIntoConstraints = false
        enclosure.addSubview(outer)
        NSLayoutConstraint.activate([
            outer.leadingAnchor.constraint(equalTo: enclosure.leadingAnchor, constant: 28),
            outer.trailingAnchor.constraint(equalTo: enclosure.trailingAnchor, constant: -28),
            outer.topAnchor.constraint(equalTo: enclosure.topAnchor, constant: 22),
            outer.bottomAnchor.constraint(equalTo: enclosure.bottomAnchor, constant: -20)
        ])
        let wordmark = NSTextField(labelWithString: "PUSH TAGS")
        wordmark.font = .systemFont(ofSize: 27, weight: .heavy); wordmark.textColor = .white
        let brand = NSStackView(views: [wordmark, label("YOUR PERSONAL CODE DJ", size: 9)])
        brand.orientation = .vertical; brand.alignment = .leading; brand.spacing = 3
        let space = NSView(); space.setContentHuggingPriority(.defaultLow, for: .horizontal)
        previewStatus.font = .monospacedSystemFont(ofSize: 10, weight: .medium)
        previewStatus.textColor = .secondaryLabelColor
        let layout = NSSegmentedControl(labels: ["DJ DECKS", "BOOMBOX"], trackingMode: .selectOne, target: self, action: #selector(changeLayout))
        layout.selectedSegment = layoutStyle == "boombox" ? 1 : 0
        layout.setAccessibilityLabel("App layout")
        let header = NSStackView(views: [brand, space, layout, previewStatus]); header.spacing = 12
        outer.addArrangedSubview(header)
        header.widthAnchor.constraint(equalTo: outer.widthAnchor).isActive = true
        transportHost.spacing = 12
        rebuildTransport()
        outer.addArrangedSubview(transportHost)
        let bankSpacer = NSView(); bankSpacer.setContentHuggingPriority(.defaultLow, for: .horizontal)
        let filters = NSStackView(); filters.spacing = 5
        for (key, title) in [("all", "ALL"), ("push", "PUSH"), ("merge", "MERGE"), ("ci", "FAILURE")] {
            let button = HardwareButton(title: title, target: self, action: #selector(filterSounds))
            button.identifier = NSUserInterfaceItemIdentifier(key)
            button.isBordered = false; button.setButtonType(.toggle)
            button.setAccessibilityLabel("Show " + title.lowercased() + " sounds")
            button.widthAnchor.constraint(equalToConstant: 70).isActive = true
            button.heightAnchor.constraint(equalToConstant: 24).isActive = true
            button.accent = key == "ci" ? coral : (key == "merge" ? violet : mint)
            filterButtons[key] = button
            filters.addArrangedSubview(button)
        }
        bankCount.font = .monospacedSystemFont(ofSize: 9, weight: .medium)
        bankCount.textColor = .secondaryLabelColor
        let bank = NSStackView(views: [label("SAMPLE PADS", color: .white.withAlphaComponent(0.65)), bankSpacer, filters, bankCount])
        bank.spacing = 12
        outer.addArrangedSubview(bank)
        bank.widthAnchor.constraint(equalTo: outer.widthAnchor).isActive = true
        padGrid.orientation = .vertical; padGrid.spacing = 8; padGrid.alignment = .leading
        let rowCount = (tags.count + 3) / 4
        padGrid.heightAnchor.constraint(equalToConstant: CGFloat(rowCount * 74 + max(0, rowCount - 1) * 8)).isActive = true
        outer.addArrangedSubview(padGrid)
        rebuildPads()
        scopeStatus.font = .monospacedSystemFont(ofSize: 10, weight: .medium)
        scopeStatus.textColor = .white.withAlphaComponent(0.7)
        scopeStatus.lineBreakMode = .byTruncatingTail
        let scopeSpacer = NSView(); scopeSpacer.setContentHuggingPriority(.defaultLow, for: .horizontal)
        let scope = NSStackView(views: [label("SCOPE", size: 9), scopeStatus, scopeSpacer,
            hardwareButton("REPOSITORIES / ORGS…", action: #selector(chooseRepositories), color: violet)])
        scope.spacing = 10
        outer.addArrangedSubview(scope)
        scope.widthAnchor.constraint(equalTo: outer.widthAnchor).isActive = true
        let actions = NSStackView(views: [hardwareButton("ENABLE ON THIS MAC…", action: #selector(enableSetup)),
            hardwareButton("REMOVE SETUP…", action: #selector(removeSetup), color: .secondaryLabelColor),
            hardwareButton("GITHUB SIGN-IN", action: #selector(signIn), color: .secondaryLabelColor),
            hardwareButton("CHECK SETUP", action: #selector(checkSetup), color: .secondaryLabelColor)])
        actions.spacing = 8
        outer.addArrangedSubview(actions)
        status.font = .systemFont(ofSize: 11); status.textColor = .secondaryLabelColor; status.maximumNumberOfLines = 2
        outer.addArrangedSubview(status)
        status.widthAnchor.constraint(equalTo: outer.widthAnchor).isActive = true
        outer.addArrangedSubview(label("OPT-IN ONLY  ·  GLOBAL MUTE COVERS ALL EVENTS  ·  QUITTING KEEPS INSTALLED LISTENERS RUNNING", size: 8))
    }

    private func useCases(_ tag: SoundTag) -> [String] {
        if let cases = tag.use_cases { return cases }
        return tag.event == "any" || tag.event == nil ? ["push", "merge", "ci"] : [tag.event!]
    }

    @objc private func filterSounds(_ sender: NSButton) {
        soundFilter = sender.identifier?.rawValue ?? "all"
        rebuildPads()
    }

    private func rebuildPads() {
        for view in padGrid.arrangedSubviews { padGrid.removeArrangedSubview(view); view.removeFromSuperview() }
        pads.removeAll()
        for (key, button) in filterButtons { button.state = key == soundFilter ? .on : .off; button.needsDisplay = true }
        let filtered = tags.filter { soundFilter == "all" || useCases($0).contains(soundFilter) }
        bankCount.stringValue = "\(filtered.count) / \(tags.count)"
        let names = ["stackaholics": "WE BUILD DIFFERENT", "stackaholics-welcome-to-main": "WELCOME TO MAIN",
                     "stackaholics-thats-a-wrap": "THAT’S A WRAP", "wheezy-outta-here": "WHEEZY OUTTA HERE",
                     "branch-outta-here": "BRANCH OUTTA HERE", "dj-khaled-another-one": "ANOTHER ONE",
                     "lego-yoda-death": "LEGO YODA", "lego-break-apart": "LEGO DEATH", "terio-kill-em": "TERIO KILL ’EM",
                     "metal-gear-alert": "METAL GEAR ALERT", "windows-xp-error": "WINDOWS XP", "fahhh": "FAHHH"]
        for start in stride(from: 0, to: filtered.count, by: 4) {
            let row = NSStackView(); row.spacing = 8
            for offset in 0..<4 {
                let index = start + offset
                if index < filtered.count {
                    let tag = filtered[index]
                    let cases = useCases(tag)
                    let pad = SoundPad(title: tag.text, target: self, action: #selector(previewPad))
                    pad.identifier = NSUserInterfaceItemIdentifier(tag.id)
                    pad.isBordered = false
                    pad.number = (tags.firstIndex { $0.id == tag.id } ?? index) + 1
                    pad.label = names[tag.id] ?? tag.text.uppercased()
                    pad.category = cases.map { $0 == "ci" ? "FAILURE" : $0.uppercased() }.joined(separator: " / ")
                    pad.accent = cases == ["ci"] ? coral : (cases == ["merge"] ? violet : mint)
                    pad.playing = previewID == tag.id && previewSound?.isPlaying == true
                    pad.widthAnchor.constraint(equalToConstant: 250).isActive = true
                    pad.heightAnchor.constraint(equalToConstant: 74).isActive = true
                    pads[tag.id] = pad
                    row.addArrangedSubview(pad)
                } else {
                    let blank = NSView()
                    blank.widthAnchor.constraint(equalToConstant: 250).isActive = true
                    blank.heightAnchor.constraint(equalToConstant: 74).isActive = true
                    row.addArrangedSubview(blank)
                }
            }
            padGrid.addView(row, in: .top)
        }
    }

    private func readObject(_ name: String) -> [String: Any] {
        guard let data = try? Data(contentsOf: state.appendingPathComponent(name)),
              let object = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else { return [:] }
        return object
    }

    private func refreshSettings() {
        let settings = readObject("settings.json")
        let config = readObject("config.json")
        muted = settings["muted"] as? Bool ?? false
        muteButton.title = muted ? "TURN SOUNDS ON" : "MUTE ALL"
        muteButton.accent = muted ? coral : mint
        muteButton.needsDisplay = true
        powerStatus.stringValue = muted ? "●  GLOBAL MUTE" : "●  SOUNDS ON"
        powerStatus.textColor = muted ? coral : mint
        if muted { stopPreview() }
        statusItem.button?.image = NSImage(systemSymbolName: muted ? "speaker.slash.fill" : "speaker.wave.2.fill", accessibilityDescription: muted ? "Sounds muted" : "Sounds enabled")
        statusItem.menu?.items[1].title = muted ? "Turn all sounds on" : "Mute all sounds"
        let repositories = config["repositories"] as? [String]
        let organizations = config["organizations"] as? [String] ?? []
        if repositories == nil {
            scopeStatus.stringValue = "ALL ACCESSIBLE REPOSITORIES"
        } else if repositories!.isEmpty && organizations.isEmpty {
            scopeStatus.stringValue = "NO REPOSITORIES SELECTED"
        } else {
            scopeStatus.stringValue = "\(repositories!.count) REPOS  /  \(organizations.count) ORGS" +
                (organizations.isEmpty ? "" : "  ·  " + organizations.joined(separator: ", "))
        }
        let defaults = ["push": "stackaholics", "merge": "branch-outta-here", "ci": "lego-break-apart"]
        for (event, _) in events {
            switches[event]?.state = (config[event + "_enabled"] as? Bool ?? true) ? .on : .off
            let selected = config[event + "_tag"] as? String ?? defaults[event]!
            if let item = popups[event]?.itemArray.first(where: { $0.representedObject as? String == selected }) {
                popups[event]?.select(item)
            }
        }
    }

    private func invoke(_ script: String, _ arguments: [String], priority: Bool = false, completion: ((Bool) -> Void)? = nil) {
        perform(script, arguments, on: priority ? muteQueue : queue) { success, _ in completion?(success) }
    }

    private func perform(_ script: String, _ arguments: [String], on worker: DispatchQueue? = nil, reportOutput: Bool = true,
                         completion: @escaping (Bool, String) -> Void) {
        let runtime = kit
        let values = environment
        status.stringValue = "Working…"
        (worker ?? queue).async { [weak self] in
            let process = Process()
            process.executableURL = URL(fileURLWithPath: "/usr/bin/env")
            process.arguments = ["python3", runtime.appendingPathComponent(script).path] + arguments
            process.environment = values
            process.currentDirectoryURL = runtime
            let pipe = Pipe()
            process.standardOutput = pipe
            process.standardError = pipe
            var output = ""
            var success = false
            do {
                try process.run()
                let data = pipe.fileHandleForReading.readDataToEndOfFile()
                process.waitUntilExit()
                output = String(data: data, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
                success = process.terminationStatus == 0
            } catch { output = error.localizedDescription }
            DispatchQueue.main.async {
                guard let self = self else { return }
                self.status.stringValue = !reportOutput && success ? "Repository choices loaded." :
                    (output.isEmpty ? (success ? "Saved." : "The command failed. Check that Python 3 and GitHub CLI are installed.") : String(output.suffix(700)))
                self.refreshSettings()
                completion(success, output)
            }
        }
    }

    @objc private func toggleMute() {
        if !muted { stopPreview() }
        invoke("push_tags.py", [muted ? "unmute" : "mute"], priority: true)
    }

    @objc private func chooseRepositories() {
        guard repositorySheet == nil else { return }
        if repositoryCatalog == nil,
           let data = try? Data(contentsOf: state.appendingPathComponent("repository-catalog.json")),
           let cached = try? JSONDecoder().decode([Repository].self, from: data) {
            repositoryCatalog = cached
        }
        let catalog = repositoryCatalog ?? []
        let sheet = RepositorySheet(repositories: catalog.map { $0.full_name }, organizations: organizationNames(catalog),
                                    selection: readObject("config.json"), refresh: { [weak self] in self?.refreshRepositoryCatalog() }) { [weak self] args in
            guard let self = self else { return }
            self.perform("repo_preferences.py", ["set"] + args, reportOutput: false) { [weak self] success, _ in
                if success { self?.status.stringValue = "Repository and organization choices saved." }
            }
        }
        repositorySheet = sheet
        window.beginSheet(sheet.window) { [weak self, weak sheet] _ in
            sheet?.window.orderOut(nil)
            self?.repositorySheet = nil
            self?.window.deminiaturize(nil)
            self?.showWindow()
        }
        if catalogLoading {
            sheet.setLoading(true)
        } else if repositoryCatalog == nil {
            refreshRepositoryCatalog()
        } else {
            sheet.setLoading(false, message: "Cached list. Refresh to check GitHub for changes.")
        }
    }

    private func organizationNames(_ catalog: [Repository]) -> [String] {
        Array(Set(catalog.filter { $0.organization }.compactMap { $0.full_name.split(separator: "/").first.map(String.init) })).sorted()
    }

    private func refreshRepositoryCatalog() {
        guard !catalogLoading else { return }
        catalogLoading = true
        repositorySheet?.setLoading(true)
        perform("repo_preferences.py", ["list"], on: githubQueue, reportOutput: false) { [weak self] success, output in
            guard let self = self else { return }
            self.catalogLoading = false
            guard success, let data = output.data(using: .utf8),
                  let catalog = try? JSONDecoder().decode([Repository].self, from: data) else {
                self.repositorySheet?.setLoading(false, message: "Refresh failed. Check GitHub sign-in and try again.")
                return
            }
            self.repositoryCatalog = catalog
            if let encoded = try? JSONEncoder().encode(catalog) {
                try? FileManager.default.createDirectory(at: self.state, withIntermediateDirectories: true, attributes: [.posixPermissions: 0o700])
                try? encoded.write(to: self.state.appendingPathComponent("repository-catalog.json"), options: .atomic)
            }
            self.repositorySheet?.updateCatalog(repositories: catalog.map { $0.full_name }, organizations: self.organizationNames(catalog))
            self.repositorySheet?.setLoading(false, message: "Updated from GitHub. Your current choices are unchanged.")
        }
    }

    @objc private func saveSelection(_ sender: NSControl) {
        guard let event = sender.identifier?.rawValue,
              let tag = popups[event]?.selectedItem?.representedObject as? String else { return }
        invoke("push_tags.py", ["configure", "--" + event + "-tag", tag, "--" + event, switches[event]?.state == .on ? "on" : "off"]) { [weak self] success in
            if success { self?.animateTransport(for: tag, event: event, pulse: true) }
        }
    }

    @objc private func previewEvent(_ sender: NSButton) {
        guard let event = sender.identifier?.rawValue,
              let tag = popups[event]?.selectedItem?.representedObject as? String else { return }
        playPreview(tag)
    }

    @objc private func previewPad(_ sender: NSButton) {
        guard let tag = sender.identifier?.rawValue else { return }
        playPreview(tag)
    }

    private func stopPreview() {
        previewSound?.stop()
        previewSound = nil
        previewID = nil
        for pad in pads.values { pad.playing = false }
        for artwork in transportArt.values { artwork.setRunning(false) }
        previewStatus.stringValue = muted ? "PREVIEW MUTED" : "READY TO PLAY"
    }

    private func playPreview(_ identifier: String) {
        stopPreview()
        muted = readObject("settings.json")["muted"] as? Bool ?? false
        guard !muted else { refreshSettings(); status.stringValue = "Sounds are muted. Turn sounds on to preview."; return }
        guard let tag = tags.first(where: { $0.id == identifier }),
              let sound = NSSound(contentsOf: kit.appendingPathComponent(tag.file), byReference: true) else {
            status.stringValue = "The audio clip could not be opened."
            return
        }
        sound.volume = 0.45
        sound.delegate = self
        previewSound = sound
        previewID = identifier
        pads[identifier]?.playing = true
        previewStatus.stringValue = "▶  " + (pads[identifier]?.label ?? tag.text.uppercased())
        status.stringValue = "Preview: " + tag.text
        if sound.play() { animateTransport(for: identifier) }
        else { stopPreview(); status.stringValue = "The audio clip could not be played." }
    }

    func sound(_ sound: NSSound, didFinishPlaying flag: Bool) {
        DispatchQueue.main.async { [weak self] in
            if self?.previewSound === sound { self?.stopPreview() }
        }
    }

    private func installedShells() -> [URL] {
        let home = FileManager.default.homeDirectoryForCurrentUser
        return [".zshrc", ".zshenv"].map { home.appendingPathComponent($0) }.filter {
            (try? String(contentsOf: $0, encoding: .utf8).contains("# BEGIN Code Push Tags")) ?? false
        }
    }

    @objc private func enableSetup() {
        let home = FileManager.default.homeDirectoryForCurrentUser
        let parent = Bundle.main.bundleURL.deletingLastPathComponent().standardizedFileURL
        guard [URL(fileURLWithPath: "/Applications"), home.appendingPathComponent("Applications")].contains(parent) else {
            alert("Move the app first.", "Place Code Push Tags.app in Applications or your home Applications folder. Open it there, then enable sounds.")
            return
        }
        let watcher = home.appendingPathComponent("Library/LaunchAgents/local.code-push-tags.merges.plist")
        if !installedShells().isEmpty || FileManager.default.fileExists(atPath: watcher.path) {
            status.stringValue = "A local setup already exists. Your sound choices and global mute apply to it. Remove that setup before enabling this app's copy."
            return
        }
        guard confirm("Enable automatic sounds?", "This adds a source line to .zshrc and installs a background watcher for your own GitHub PRs. Open a new terminal afterward.") else { return }
        var selected = ["configure"]
        for (event, _) in events {
            guard let tag = popups[event]?.selectedItem?.representedObject as? String else { return }
            selected += ["--" + event + "-tag", tag, "--" + event, switches[event]?.state == .on ? "on" : "off"]
        }
        invoke("push_tags.py", ["doctor"]) { [weak self] success in
            guard let self = self, success else { return }
            self.invoke("push_tags.py", selected) { [weak self] success in
                guard let self = self, success else { return }
                self.invoke("install.py", ["install"]) { [weak self] success in
                    if success { self?.status.stringValue = "Enabled. Open a new terminal. Keep the app in this folder." }
                }
            }
        }
    }

    @objc private func removeSetup() {
        guard confirm("Remove local setup?", "This turns on global mute, removes the shell setup, and removes the scheduled watcher. Sound files and preferences remain.") else { return }
        invoke("push_tags.py", ["mute"]) { [weak self] success in
            guard let self = self, success else { return }
            let shells = self.installedShells()
            self.removeShells(shells.isEmpty ? [FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent(".zshrc")] : shells)
        }
    }

    private func removeShells(_ shells: [URL]) {
        guard let first = shells.first else { status.stringValue = "Removed and muted. Open a new terminal."; return }
        invoke("install.py", ["uninstall", "--shell-file", first.path]) { [weak self] success in
            if success { self?.removeShells(Array(shells.dropFirst())) }
        }
    }

    @objc private func checkSetup() { invoke("push_tags.py", ["doctor"]) }

    @objc private func signIn() {
        let command = "PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin gh auth login --web"
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/osascript")
        process.arguments = ["-e", "tell application \"Terminal\" to do script \"\(command)\"", "-e", "tell application \"Terminal\" to activate"]
        do { try process.run(); status.stringValue = "Finish GitHub sign-in in Terminal, then select Check setup." }
        catch { alert("Terminal could not be opened.", error.localizedDescription) }
    }

    @objc private func showWindow() { window.makeKeyAndOrderFront(nil); NSApp.activate(ignoringOtherApps: true) }
    @objc private func quit() { NSApp.terminate(nil) }

    private func alert(_ title: String, _ message: String) {
        let alert = NSAlert(); alert.messageText = title; alert.informativeText = message; alert.runModal()
    }

    private func confirm(_ title: String, _ message: String) -> Bool {
        let alert = NSAlert(); alert.messageText = title; alert.informativeText = message
        alert.addButton(withTitle: "Continue"); alert.addButton(withTitle: "Cancel")
        return alert.runModal() == .alertFirstButtonReturn
    }

}

final class RepositorySheet: NSObject, NSTableViewDataSource, NSTableViewDelegate {
    struct Item {
        let kind: String
        let name: String
    }
    let window: NSWindow
    private let table = NSTableView()
    private let search = NSSearchField()
    private let all = NSButton(checkboxWithTitle: "All accessible repositories", target: nil, action: nil)
    private let refreshButton = NSButton(title: "Refresh", target: nil, action: nil)
    private let progress = NSProgressIndicator()
    private let catalogStatus = NSTextField(labelWithString: "")
    private var items: [Item] = []
    private var visible: [Item] = []
    private var repositories: Set<String>
    private var organizations: Set<String>
    private let refresh: () -> Void
    private let save: ([String]) -> Void

    init(repositories: [String], organizations: [String], selection: [String: Any], refresh: @escaping () -> Void,
         save: @escaping ([String]) -> Void) {
        self.repositories = Set(selection["repositories"] as? [String] ?? [])
        self.organizations = Set(selection["organizations"] as? [String] ?? [])
        self.refresh = refresh
        self.save = save
        window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 650, height: 560),
                          styleMask: [.titled], backing: .buffered, defer: false)
        super.init()
        window.title = "Choose repositories and organizations"
        window.isReleasedWhenClosed = false
        window.appearance = NSAppearance(named: .darkAqua)
        let stack = NSStackView()
        stack.orientation = .vertical
        stack.alignment = .leading
        stack.spacing = 12
        stack.translatesAutoresizingMaskIntoConstraints = false
        window.contentView!.addSubview(stack)
        NSLayoutConstraint.activate([
            stack.leadingAnchor.constraint(equalTo: window.contentView!.leadingAnchor, constant: 20),
            stack.trailingAnchor.constraint(equalTo: window.contentView!.trailingAnchor, constant: -20),
            stack.topAnchor.constraint(equalTo: window.contentView!.topAnchor, constant: 20),
            stack.bottomAnchor.constraint(equalTo: window.contentView!.bottomAnchor, constant: -20)
        ])
        stack.addArrangedSubview(NSTextField(wrappingLabelWithString: "One selection applies to pushes, merges, and CI failures. Organizations include their accessible repositories, including new ones."))
        all.state = selection["repositories"] is NSNull || selection["repositories"] == nil ? .on : .off
        all.target = self
        all.action = #selector(filterChanged)
        let controls = NSStackView(views: [all, NSButton(title: "None", target: self, action: #selector(clearSelection))])
        controls.spacing = 14
        stack.addArrangedSubview(controls)
        refreshButton.target = self
        refreshButton.action = #selector(refreshCatalog)
        progress.style = .spinning
        progress.controlSize = .small
        progress.isDisplayedWhenStopped = false
        progress.widthAnchor.constraint(equalToConstant: 16).isActive = true
        progress.heightAnchor.constraint(equalToConstant: 16).isActive = true
        catalogStatus.font = .systemFont(ofSize: 11)
        catalogStatus.textColor = .secondaryLabelColor
        catalogStatus.lineBreakMode = .byTruncatingTail
        let refreshRow = NSStackView(views: [refreshButton, progress, catalogStatus])
        refreshRow.spacing = 8
        stack.addArrangedSubview(refreshRow)
        refreshRow.widthAnchor.constraint(equalTo: stack.widthAnchor).isActive = true
        search.placeholderString = "Find a repository or organization"
        search.target = self
        search.action = #selector(filterChanged)
        search.sendsSearchStringImmediately = true
        stack.addArrangedSubview(search)
        search.widthAnchor.constraint(equalTo: stack.widthAnchor).isActive = true
        let column = NSTableColumn(identifier: NSUserInterfaceItemIdentifier("repository"))
        column.width = 580
        table.addTableColumn(column)
        table.headerView = nil
        table.rowHeight = 28
        table.dataSource = self
        table.delegate = self
        let scroll = NSScrollView()
        scroll.documentView = table
        scroll.hasVerticalScroller = true
        scroll.borderType = .bezelBorder
        scroll.heightAnchor.constraint(greaterThanOrEqualToConstant: 300).isActive = true
        stack.addArrangedSubview(scroll)
        scroll.widthAnchor.constraint(equalTo: stack.widthAnchor).isActive = true
        let cancel = NSButton(title: "Cancel", target: self, action: #selector(close))
        cancel.keyEquivalent = "\u{1b}"
        let buttons = NSStackView(views: [NSButton(title: "Save selection", target: self, action: #selector(saveSelection)), cancel])
        buttons.spacing = 8
        stack.addArrangedSubview(buttons)
        updateCatalog(repositories: repositories, organizations: organizations)
    }

    func setLoading(_ loading: Bool, message: String = "Refreshing repositories from GitHub…") {
        refreshButton.isEnabled = !loading
        refreshButton.title = loading ? "Refreshing…" : "Refresh"
        if loading { progress.startAnimation(nil) } else { progress.stopAnimation(nil) }
        catalogStatus.stringValue = message
    }

    func updateCatalog(repositories: [String], organizations: [String]) {
        let repoNames = Set(repositories).union(self.repositories)
        let orgNames = Set(organizations).union(self.organizations)
        items = orgNames.sorted().map { Item(kind: "org", name: $0) } + repoNames.sorted().map { Item(kind: "repo", name: $0) }
        filterChanged()
    }

    @objc private func refreshCatalog() { refresh() }

    @objc private func filterChanged() {
        let query = search.stringValue.trimmingCharacters(in: .whitespacesAndNewlines)
        visible = items.filter { query.isEmpty || $0.name.localizedCaseInsensitiveContains(query) }
        table.reloadData()
    }

    @objc private func clearSelection() {
        all.state = .off
        repositories.removeAll()
        organizations.removeAll()
        table.reloadData()
    }

    @objc private func toggleItem(_ sender: NSButton) {
        let item = visible[sender.tag]
        if item.kind == "org" {
            if sender.state == .on { organizations.insert(item.name) } else { organizations.remove(item.name) }
        } else {
            if sender.state == .on { repositories.insert(item.name) } else { repositories.remove(item.name) }
        }
    }

    @objc private func saveSelection() {
        let arguments = all.state == .on ? ["--all"] :
            repositories.sorted().flatMap { ["--repo", $0] } + organizations.sorted().flatMap { ["--org", $0] }
        save(arguments)
        close()
    }

    @objc private func close() {
        guard let parent = window.sheetParent else { window.orderOut(nil); return }
        parent.endSheet(window)
        window.orderOut(nil)
        parent.deminiaturize(nil)
        parent.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }

    func numberOfRows(in tableView: NSTableView) -> Int { visible.count }

    func tableView(_ tableView: NSTableView, viewFor tableColumn: NSTableColumn?, row: Int) -> NSView? {
        let item = visible[row]
        let button = NSButton(checkboxWithTitle: (item.kind == "org" ? "Organization · " : "Repository · ") + item.name,
                              target: self, action: #selector(toggleItem))
        button.tag = row
        button.state = all.state == .on || (item.kind == "org" ? organizations.contains(item.name) : repositories.contains(item.name)) ? .on : .off
        button.isEnabled = all.state != .on
        return button
    }
}

@main
enum CodePushTagsMain {
    static func main() {
        let app = NSApplication.shared
        let delegate = AppDelegate()
        app.delegate = delegate
        app.setActivationPolicy(.regular)
        app.run()
    }
}
