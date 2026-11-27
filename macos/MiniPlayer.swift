import AppKit

final class MiniPlayerView: NSView {
    var onExpand: (() -> Void)?
    var onToggleMute: (() -> Void)?

    private let titleLabel = NSTextField(labelWithString: "READY FOR THE DROP")
    private let subtitleLabel = NSTextField(labelWithString: "One time for the runtime.")
    private let statusLabel = NSTextField(labelWithString: "SFX / STANDBY")
    private let muteButton = NSButton(title: "MUTE", target: nil, action: nil)
    private let pixels = MiniPlayerLEDView()
    private var playing = false
    private var muted = false
    private let accent = NSColor(srgbRed: 0.54, green: 0.96, blue: 0.69, alpha: 1)

    override init(frame frameRect: NSRect) {
        super.init(frame: frameRect)
        wantsLayer = true
        layer?.backgroundColor = NSColor(srgbRed: 0.075, green: 0.08, blue: 0.09, alpha: 1).cgColor
        layer?.cornerRadius = 12

        titleLabel.font = .monospacedSystemFont(ofSize: 12, weight: .bold)
        titleLabel.textColor = .white
        titleLabel.lineBreakMode = .byTruncatingTail
        titleLabel.setContentCompressionResistancePriority(.defaultLow, for: .horizontal)
        subtitleLabel.font = .monospacedSystemFont(ofSize: 9, weight: .medium)
        subtitleLabel.textColor = .secondaryLabelColor
        subtitleLabel.lineBreakMode = .byTruncatingTail
        statusLabel.font = .monospacedSystemFont(ofSize: 9, weight: .semibold)
        statusLabel.textColor = accent

        let expand = NSButton(title: "FULL PLAYER", target: self, action: #selector(expandPlayer))
        expand.setAccessibilityLabel("Open full player")
        muteButton.target = self
        muteButton.action = #selector(toggleMute)
        for button in [expand, muteButton] {
            button.font = .monospacedSystemFont(ofSize: 9, weight: .semibold)
            button.bezelStyle = .roundRect
            button.contentTintColor = accent
            button.setContentHuggingPriority(.required, for: .horizontal)
            button.heightAnchor.constraint(equalToConstant: 24).isActive = true
        }
        let header = NSStackView(views: [titleLabel, expand])
        header.spacing = 12
        let spacer = NSView()
        spacer.setContentHuggingPriority(.defaultLow, for: .horizontal)
        let footer = NSStackView(views: [statusLabel, spacer, muteButton])
        footer.spacing = 8
        let stack = NSStackView(views: [header, subtitleLabel, pixels, footer])
        stack.orientation = .vertical
        stack.alignment = .leading
        stack.spacing = 6
        stack.translatesAutoresizingMaskIntoConstraints = false
        addSubview(stack)
        NSLayoutConstraint.activate([
            stack.leadingAnchor.constraint(equalTo: leadingAnchor, constant: 14),
            stack.trailingAnchor.constraint(equalTo: trailingAnchor, constant: -14),
            stack.topAnchor.constraint(equalTo: topAnchor, constant: 12),
            stack.bottomAnchor.constraint(equalTo: bottomAnchor, constant: -12),
            header.widthAnchor.constraint(equalTo: stack.widthAnchor),
            subtitleLabel.widthAnchor.constraint(equalTo: stack.widthAnchor),
            pixels.widthAnchor.constraint(equalTo: stack.widthAnchor),
            pixels.heightAnchor.constraint(greaterThanOrEqualToConstant: 42),
            footer.widthAnchor.constraint(equalTo: stack.widthAnchor)
        ])
        refreshStatus()
    }

    required init?(coder: NSCoder) { fatalError("init(coder:) is not supported") }

    func setStatus(title: String, subtitle: String, muted: Bool) {
        titleLabel.stringValue = title
        titleLabel.toolTip = title
        subtitleLabel.stringValue = subtitle
        self.muted = muted
        refreshStatus()
    }

    func setPlaying(_ playing: Bool) {
        self.playing = playing
        refreshStatus()
    }

    private func refreshStatus() {
        muteButton.title = muted ? "UNMUTE" : "MUTE"
        muteButton.setAccessibilityLabel(muted ? "Turn all sounds on" : "Mute all sounds")
        statusLabel.stringValue = muted ? "GLOBAL MUTE" : playing ? "SFX / PLAYING" : "SFX / STANDBY"
        statusLabel.textColor = muted ? .systemRed : accent
        pixels.setActive(playing && !muted)
    }

    @objc private func expandPlayer() { onExpand?() }
    @objc private func toggleMute() { onToggleMute?() }
}

private final class MiniPlayerLEDView: NSView {
    private var active = false
    private var phase = 0.0
    private var timer: Timer?
    private var displayObserver: NSObjectProtocol?
    private let green = NSColor(srgbRed: 0.54, green: 0.96, blue: 0.69, alpha: 1)

    override init(frame frameRect: NSRect) {
        super.init(frame: frameRect)
        setAccessibilityElement(true)
        setAccessibilityRole(.image)
        setAccessibilityLabel("Sound activity LED display")
        displayObserver = NSWorkspace.shared.notificationCenter.addObserver(
            forName: NSWorkspace.accessibilityDisplayOptionsDidChangeNotification,
            object: nil, queue: .main
        ) { [weak self] _ in
            self?.updateMotion()
            self?.needsDisplay = true
        }
    }

    required init?(coder: NSCoder) { fatalError("init(coder:) is not supported") }

    deinit {
        timer?.invalidate()
        if let observer = displayObserver { NSWorkspace.shared.notificationCenter.removeObserver(observer) }
    }

    func setActive(_ value: Bool) {
        guard active != value else { return }
        active = value
        phase = 0
        setAccessibilityValue(active ? "Playing" : "Idle")
        updateMotion()
        needsDisplay = true
    }

    override func viewDidMoveToWindow() {
        super.viewDidMoveToWindow()
        updateMotion()
    }

    override func viewWillDraw() {
        super.viewWillDraw()
        updateMotion()
    }

    private func updateMotion() {
        let animate = active && window?.isVisible == true && !isHiddenOrHasHiddenAncestor &&
            !NSWorkspace.shared.accessibilityDisplayShouldReduceMotion
        guard animate else { timer?.invalidate(); timer = nil; return }
        guard timer == nil else { return }
        let animation = Timer(timeInterval: 0.08, repeats: true) { [weak self] _ in
            guard let self = self else { return }
            self.updateMotion()
            guard self.timer != nil else { return }
            self.phase += 0.6
            self.needsDisplay = true
        }
        timer = animation
        RunLoop.main.add(animation, forMode: .common)
    }

    override func draw(_ dirtyRect: NSRect) {
        NSColor(white: 0.025, alpha: 1).setFill()
        NSBezierPath(roundedRect: bounds, xRadius: 5, yRadius: 5).fill()
        let columns = 52
        let rows = 6
        let pitch = min((bounds.width - 16) / CGFloat(columns), (bounds.height - 10) / CGFloat(rows))
        let pixel = max(1, floor(pitch - 2))
        let origin = NSPoint(x: (bounds.width - CGFloat(columns) * pitch) / 2,
                             y: (bounds.height - CGFloat(rows) * pitch) / 2)
        for column in 0..<columns {
            let height = active ? 1 + Int((sin(Double(column) * 0.7 + phase) + 1) * 2.5) : 0
            for row in 0..<rows {
                let color = row == rows - 1 ? NSColor.systemRed : row > 3 ? NSColor.systemOrange : green
                color.withAlphaComponent(row < height ? 0.95 : 0.08).setFill()
                NSRect(x: origin.x + CGFloat(column) * pitch, y: origin.y + CGFloat(row) * pitch,
                       width: pixel, height: pixel).fill()
            }
        }
    }
}
