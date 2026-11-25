import AppKit
import QuartzCore

final class TransportArtwork: NSView {
    enum Style { case vinyl, cassette, speaker }

    var style: Style = .cassette { didSet { needsLayout = true } }
    var accent = NSColor(srgbRed: 0.54, green: 0.96, blue: 0.69, alpha: 1) { didSet { needsLayout = true } }
    private let artwork = CALayer()
    private var rotors: [CALayer] = []
    private var running = false

    override init(frame frameRect: NSRect) {
        super.init(frame: frameRect)
        wantsLayer = true
        layer?.addSublayer(artwork)
        setAccessibilityElement(true)
    }

    required init?(coder: NSCoder) { fatalError("init(coder:) is not supported") }

    override func layout() {
        super.layout()
        CATransaction.begin()
        CATransaction.setDisableActions(true)
        artwork.sublayers?.forEach { $0.removeFromSuperlayer() }
        rotors.removeAll()
        let size: CGSize
        switch style {
        case .vinyl: size = CGSize(width: 124, height: 124)
        case .cassette: size = CGSize(width: 300, height: 135)
        case .speaker: size = CGSize(width: 180, height: 180)
        }
        let scale = min(bounds.width / size.width, bounds.height / size.height)
        artwork.bounds = CGRect(origin: .zero, size: size)
        artwork.position = CGPoint(x: bounds.midX, y: bounds.midY)
        artwork.setAffineTransform(CGAffineTransform(scaleX: scale, y: scale))
        switch style {
        case .vinyl: drawVinyl(); setAccessibilityLabel("Vinyl record")
        case .cassette: drawCassette(); setAccessibilityLabel("Cassette tape")
        case .speaker: drawSpeaker(); setAccessibilityLabel("Boombox speaker")
        }
        CATransaction.commit()
        updateMotion()
    }

    func setRunning(_ value: Bool) {
        running = value
        updateMotion()
    }

    func pulse() {
        layoutSubtreeIfNeeded()
        guard !NSWorkspace.shared.accessibilityDisplayShouldReduceMotion else { return }
        for rotor in rotors {
            let turn = CABasicAnimation(keyPath: "transform.rotation.z")
            turn.fromValue = 0
            turn.toValue = Double.pi * 2
            turn.duration = 0.8
            turn.timingFunction = CAMediaTimingFunction(name: .easeInEaseOut)
            rotor.add(turn, forKey: "selection")
        }
    }

    private func updateMotion() {
        for rotor in rotors {
            rotor.removeAnimation(forKey: "rotation")
            if !running { rotor.removeAnimation(forKey: "selection") }
            guard running, !NSWorkspace.shared.accessibilityDisplayShouldReduceMotion else { continue }
            let turn = CABasicAnimation(keyPath: "transform.rotation.z")
            turn.fromValue = 0
            turn.toValue = Double.pi * 2
            turn.duration = style == .vinyl ? 1.8 : 1.2
            turn.repeatCount = .infinity
            rotor.add(turn, forKey: "rotation")
        }
    }

    @discardableResult private func shape(_ path: CGPath, fill: NSColor, stroke: NSColor? = nil,
                                           width: CGFloat = 1, parent: CALayer? = nil) -> CAShapeLayer {
        let layer = CAShapeLayer()
        layer.path = path
        layer.fillColor = fill.cgColor
        layer.strokeColor = stroke?.cgColor
        layer.lineWidth = width
        (parent ?? artwork).addSublayer(layer)
        return layer
    }

    private func box(_ rect: CGRect, radius: CGFloat = 4, fill: NSColor, stroke: NSColor? = nil) {
        shape(CGPath(roundedRect: rect, cornerWidth: radius, cornerHeight: radius, transform: nil), fill: fill, stroke: stroke)
    }

    private func circle(_ center: CGPoint, radius: CGFloat, fill: NSColor, stroke: NSColor? = nil,
                        parent: CALayer? = nil) {
        shape(CGPath(ellipseIn: CGRect(x: center.x - radius, y: center.y - radius,
                                      width: radius * 2, height: radius * 2), transform: nil),
              fill: fill, stroke: stroke, parent: parent)
    }

    private func text(_ value: String, rect: CGRect, size: CGFloat, color: NSColor, parent: CALayer? = nil) {
        let label = CATextLayer()
        label.string = value
        label.font = NSFont.monospacedSystemFont(ofSize: size, weight: .bold)
        label.fontSize = size
        label.foregroundColor = color.cgColor
        label.alignmentMode = .center
        label.contentsScale = window?.backingScaleFactor ?? 2
        label.frame = rect
        (parent ?? artwork).addSublayer(label)
    }

    private func rotor(at point: CGPoint, radius: CGFloat) -> CALayer {
        let rotor = CALayer()
        rotor.bounds = CGRect(x: -radius, y: -radius, width: radius * 2, height: radius * 2)
        rotor.position = point
        artwork.addSublayer(rotor)
        rotors.append(rotor)
        return rotor
    }

    private func drawCassette() {
        box(CGRect(x: 3, y: 3, width: 294, height: 129), radius: 12,
            fill: NSColor(white: 0.14, alpha: 1), stroke: NSColor(white: 0.42, alpha: 1))
        box(CGRect(x: 12, y: 12, width: 276, height: 111), radius: 8,
            fill: NSColor(white: 0.08, alpha: 1), stroke: NSColor(white: 0.25, alpha: 1))
        box(CGRect(x: 23, y: 91, width: 254, height: 21), radius: 2, fill: accent)
        text("PUSH TAGS     /     SIDE A", rect: CGRect(x: 27, y: 95, width: 246, height: 13),
             size: 10, color: NSColor(white: 0.09, alpha: 1))
        box(CGRect(x: 27, y: 38, width: 246, height: 47), radius: 21,
            fill: NSColor(white: 0.025, alpha: 1), stroke: NSColor(white: 0.35, alpha: 1))
        box(CGRect(x: 117, y: 48, width: 66, height: 27), radius: 3, fill: NSColor(white: 0.22, alpha: 1))
        for x: CGFloat in [72, 228] {
            circle(CGPoint(x: x, y: 61), radius: 29, fill: NSColor(white: 0.06, alpha: 1), stroke: NSColor(white: 0.36, alpha: 1))
            let reel = rotor(at: CGPoint(x: x, y: 61), radius: 19)
            circle(.zero, radius: 18, fill: NSColor(white: 0.76, alpha: 1), parent: reel)
            circle(.zero, radius: 12, fill: NSColor(white: 0.12, alpha: 1), parent: reel)
            for i in 0..<6 {
                let angle = CGFloat(i) * .pi / 3
                circle(CGPoint(x: cos(angle) * 12, y: sin(angle) * 12), radius: 3,
                       fill: NSColor(white: 0.76, alpha: 1), parent: reel)
            }
            circle(.zero, radius: 5, fill: accent, parent: reel)
        }
        let tape = CGMutablePath()
        tape.move(to: CGPoint(x: 85, y: 14)); tape.addLine(to: CGPoint(x: 95, y: 30))
        tape.addLine(to: CGPoint(x: 205, y: 30)); tape.addLine(to: CGPoint(x: 215, y: 14)); tape.closeSubpath()
        shape(tape, fill: NSColor(white: 0.19, alpha: 1), stroke: NSColor(white: 0.35, alpha: 1))
        for x: CGFloat in [106, 194] {
            circle(CGPoint(x: x, y: 20), radius: 3, fill: .black)
        }
        for point in [CGPoint(x: 13, y: 13), CGPoint(x: 287, y: 13), CGPoint(x: 13, y: 122), CGPoint(x: 287, y: 122)] {
            circle(point, radius: 2.5, fill: NSColor(white: 0.55, alpha: 1))
        }
    }

    private func drawVinyl() {
        let center = CGPoint(x: 62, y: 62)
        circle(center, radius: 60, fill: NSColor(white: 0.3, alpha: 1))
        let disc = rotor(at: center, radius: 55)
        circle(.zero, radius: 55, fill: NSColor(white: 0.025, alpha: 1), parent: disc)
        for radius in stride(from: CGFloat(23), through: 51, by: 4) {
            circle(.zero, radius: radius, fill: .clear, stroke: NSColor(white: 0.15, alpha: 1), parent: disc)
        }
        circle(.zero, radius: 18, fill: accent, parent: disc)
        text("P / T", rect: CGRect(x: -15, y: -5, width: 30, height: 12), size: 9,
             color: NSColor(white: 0.08, alpha: 1), parent: disc)
        circle(CGPoint(x: 0, y: 12), radius: 2, fill: .white, parent: disc)
        circle(center, radius: 2, fill: .white)
        let arm = CGMutablePath()
        arm.move(to: CGPoint(x: 115, y: 116)); arm.addLine(to: CGPoint(x: 115, y: 67))
        arm.addLine(to: CGPoint(x: 88, y: 46))
        shape(arm, fill: .clear, stroke: NSColor(white: 0.72, alpha: 1), width: 3)
        box(CGRect(x: 82, y: 43, width: 10, height: 6), radius: 2, fill: .white)
        circle(CGPoint(x: 115, y: 116), radius: 4, fill: accent)
    }

    private func drawSpeaker() {
        let center = CGPoint(x: 90, y: 90)
        circle(center, radius: 88, fill: NSColor(white: 0.08, alpha: 1), stroke: NSColor(white: 0.42, alpha: 1))
        circle(center, radius: 81, fill: NSColor(white: 0.18, alpha: 1), stroke: .black)
        for radius in stride(from: CGFloat(30), through: 76, by: 4) {
            circle(center, radius: radius, fill: .clear, stroke: NSColor(white: 0.08, alpha: 1))
        }
        circle(center, radius: 29, fill: NSColor(white: 0.06, alpha: 1), stroke: accent.withAlphaComponent(0.7))
        circle(center, radius: 22, fill: NSColor(white: 0.13, alpha: 1))
        text("P / T", rect: CGRect(x: 64, y: 84, width: 52, height: 13), size: 11, color: accent)
    }
}
