import AppKit

private func drawLibraryText(_ value: String, in rect: NSRect, size: CGFloat, color: NSColor,
                             weight: NSFont.Weight = .medium, alignment: NSTextAlignment = .left) {
    let paragraph = NSMutableParagraphStyle()
    paragraph.lineBreakMode = .byTruncatingTail
    paragraph.alignment = alignment
    (value as NSString).draw(in: rect, withAttributes: [
        .font: NSFont.monospacedSystemFont(ofSize: size, weight: weight),
        .foregroundColor: color, .paragraphStyle: paragraph
    ])
}

final class LibraryItem: NSButton {
    var number = 0 { didSet { needsDisplay = true } }
    var label = "" { didSet { needsDisplay = true } }
    var category = "" { didSet { needsDisplay = true } }
    var accent = NSColor(srgbRed: 0.54, green: 0.96, blue: 0.69, alpha: 1) { didSet { needsDisplay = true } }
    var playing = false { didSet { needsDisplay = true } }
    var cassette = false { didSet { needsDisplay = true } }

    override func mouseDown(with event: NSEvent) {
        if event.clickCount == 2 { super.mouseDown(with: event) }
    }

    override func draw(_ dirtyRect: NSRect) {
        let active = playing || isHighlighted
        let face = bounds.insetBy(dx: 2, dy: 3)
        NSColor.black.withAlphaComponent(0.7).setFill()
        NSBezierPath(roundedRect: face.offsetBy(dx: 0, dy: -2), xRadius: 5, yRadius: 5).fill()
        if cassette { drawCassette(face, active: active) }
        else { drawRecord(face, active: active) }
    }

    private func drawCassette(_ rect: NSRect, active: Bool) {
        let shell = NSBezierPath(roundedRect: rect, xRadius: 5, yRadius: 5)
        NSGradient(starting: NSColor(white: 0.12, alpha: 1), ending: NSColor(white: 0.23, alpha: 1))?.draw(in: shell, angle: 90)

        let paper = NSRect(x: rect.minX + 24, y: rect.minY + 8, width: rect.width - 94, height: rect.height - 16)
        NSColor(white: active ? 0.27 : 0.19, alpha: 1).setFill()
        NSBezierPath(roundedRect: paper, xRadius: 2, yRadius: 2).fill()
        accent.setFill()
        NSRect(x: paper.minX, y: paper.maxY - 3, width: paper.width, height: 3).fill()
        drawLibraryText(String(format: "%02d", number), in: NSRect(x: rect.minX + 6, y: rect.midY - 6, width: 17, height: 13),
             size: 9, color: accent)
        drawLibraryText(label, in: NSRect(x: paper.minX + 7, y: paper.minY + 13, width: paper.width - 14, height: 17),
             size: 11, color: .white, weight: .bold)
        drawLibraryText(playing ? "PLAYING  /  SIDE A" : category + "  /  SIDE A",
             in: NSRect(x: paper.minX + 7, y: paper.minY + 3, width: paper.width - 14, height: 10),
             size: 7, color: accent.withAlphaComponent(0.8))

        for x in [rect.maxX - 49, rect.maxX - 24] {
            let center = NSPoint(x: x, y: rect.midY)
            NSColor(white: 0.035, alpha: 1).setFill()
            NSBezierPath(ovalIn: NSRect(x: x - 10, y: center.y - 10, width: 20, height: 20)).fill()
            NSColor(white: active ? 0.85 : 0.55, alpha: 1).setStroke()
            let reel = NSBezierPath(ovalIn: NSRect(x: x - 6, y: center.y - 6, width: 12, height: 12))
            reel.lineWidth = 2
            reel.stroke()
            let spokes = NSBezierPath()
            for i in 0..<3 {
                let angle = CGFloat(i) * .pi * 2 / 3
                spokes.move(to: center)
                spokes.line(to: NSPoint(x: x + cos(angle) * 6, y: center.y + sin(angle) * 6))
            }
            spokes.stroke()
        }
        NSColor.white.withAlphaComponent(0.14).setFill()
        NSRect(x: rect.minX + 5, y: rect.maxY - 4, width: rect.width - 10, height: 1).fill()
    }

    private func drawRecord(_ rect: NSRect, active: Bool) {
        let center = NSPoint(x: rect.maxX - 28, y: rect.midY)
        let diameter = rect.height - 2
        let disc = NSRect(x: center.x - diameter / 2, y: center.y - diameter / 2, width: diameter, height: diameter)
        NSColor(white: 0.025, alpha: 1).setFill()
        NSBezierPath(ovalIn: disc).fill()
        NSColor(white: 0.24, alpha: 1).setStroke()
        for inset in stride(from: CGFloat(2), through: diameter * 0.33, by: 4) {
            NSBezierPath(ovalIn: disc.insetBy(dx: inset, dy: inset)).stroke()
        }
        accent.withAlphaComponent(active ? 1 : 0.7).setFill()
        NSBezierPath(ovalIn: disc.insetBy(dx: diameter * 0.34, dy: diameter * 0.34)).fill()
        NSColor.white.setFill()
        NSBezierPath(ovalIn: NSRect(x: center.x - 1, y: center.y - 1, width: 2, height: 2)).fill()

        let jacket = NSRect(x: rect.minX, y: rect.minY, width: rect.width - 38, height: rect.height)
        let path = NSBezierPath(roundedRect: jacket, xRadius: 3, yRadius: 3)
        NSGradient(starting: NSColor(white: 0.12, alpha: 1), ending: NSColor(white: active ? 0.27 : 0.2, alpha: 1))?.draw(in: path, angle: 30)
        accent.withAlphaComponent(active ? 0.9 : 0.55).setFill()
        NSRect(x: jacket.minX + 2, y: jacket.minY + 3, width: 4, height: jacket.height - 6).fill()
        drawLibraryText(String(format: "%02d", number), in: NSRect(x: jacket.minX + 13, y: jacket.minY + 17, width: 23, height: 16),
             size: 11, color: accent)
        drawLibraryText(label, in: NSRect(x: jacket.minX + 42, y: jacket.minY + 25, width: jacket.width - 52, height: 17),
             size: 11, color: .white, weight: .bold)
        drawLibraryText(playing ? "●  NOW PLAYING" : category + "  /  45 RPM",
             in: NSRect(x: jacket.minX + 42, y: jacket.minY + 10, width: jacket.width - 52, height: 12),
             size: 8, color: accent.withAlphaComponent(0.8))
    }
}

final class LibraryStack: NSStackView {
    override var isFlipped: Bool { true }
}

final class SoundGroupHeader: NSButton {
    var cassette = false { didSet { needsDisplay = true } }
    var accent = NSColor(srgbRed: 0.54, green: 0.96, blue: 0.69, alpha: 1) { didSet { needsDisplay = true } }
    var expanded = false { didSet { needsDisplay = true } }
    var detail = "" { didSet { needsDisplay = true } }
    var isCategory = false { didSet { needsDisplay = true } }
    var canExpand = true { didSet { needsDisplay = true } }

    override func draw(_ dirtyRect: NSRect) {
        let face = bounds.insetBy(dx: 1, dy: 2)
        let shell = NSBezierPath(roundedRect: face, xRadius: 6, yRadius: 6)
        let shade: CGFloat = isCategory ? 0.15 : 0.11
        NSGradient(starting: NSColor(white: shade + (isHighlighted ? 0.07 : 0), alpha: 1),
                   ending: NSColor(white: shade - 0.035, alpha: 1))?.draw(in: shell, angle: 90)
        if canExpand && expanded {
            accent.withAlphaComponent(0.6).setFill()
            NSRect(x: face.minX + 3, y: face.minY + 8, width: 2, height: face.height - 16).fill()
        }
        let compact = face.width < 320
        let icon = NSRect(x: face.minX + (compact ? 8 : 13), y: face.midY - 16, width: 48, height: 32)
        if cassette { drawTapeStack(icon) } else { drawRecordStack(icon) }

        if compact {
            let titleX = face.minX + 64
            let width = max(0, face.maxX - titleX - (canExpand ? 25 : 9))
            drawLibraryText(isCategory ? title.uppercased() : title,
                     in: NSRect(x: titleX, y: face.midY + 1, width: width, height: 16),
                     size: isCategory ? 11 : 10, color: .white, weight: isCategory ? .bold : .semibold)
            drawLibraryText(detail, in: NSRect(x: titleX, y: face.midY - 13, width: width, height: 13),
                     size: 8, color: accent.withAlphaComponent(0.85))
        } else {
            let detailWidth = min(180, max(80, face.width * 0.24))
            let detailX = face.maxX - detailWidth - (canExpand ? 35 : 13)
            let titleX = face.minX + 76
            drawLibraryText(isCategory ? title.uppercased() : title,
                     in: NSRect(x: titleX, y: face.midY - 8, width: max(0, detailX - titleX - 12), height: 18),
                     size: isCategory ? 12 : 11, color: .white, weight: isCategory ? .bold : .semibold)
            drawLibraryText(detail, in: NSRect(x: detailX, y: face.midY - 6, width: detailWidth, height: 14),
                     size: 9, color: accent.withAlphaComponent(0.85), alignment: .right)
        }

        guard canExpand else { return }
        let center = NSPoint(x: face.maxX - 18, y: face.midY)
        let disclosure = NSBezierPath()
        if expanded {
            disclosure.move(to: NSPoint(x: center.x - 4, y: center.y + 2))
            disclosure.line(to: NSPoint(x: center.x + 4, y: center.y + 2))
            disclosure.line(to: NSPoint(x: center.x, y: center.y - 3))
        } else {
            disclosure.move(to: NSPoint(x: center.x - 2, y: center.y + 4))
            disclosure.line(to: NSPoint(x: center.x + 3, y: center.y))
            disclosure.line(to: NSPoint(x: center.x - 2, y: center.y - 4))
        }
        disclosure.close()
        accent.setFill()
        disclosure.fill()
    }

    private func drawRecordStack(_ rect: NSRect) {
        for index in stride(from: 2, through: 0, by: -1) {
            let offset = CGFloat(index) * (expanded ? 2 : 3)
            let jacket = NSRect(x: rect.minX + offset, y: rect.minY + offset,
                                width: 28, height: 27)
            NSColor(white: 0.19 + CGFloat(index) * 0.055, alpha: 1).setFill()
            NSBezierPath(roundedRect: jacket, xRadius: 2, yRadius: 2).fill()
            accent.withAlphaComponent(0.35).setFill()
            NSRect(x: jacket.minX + 2, y: jacket.minY + 3, width: 2, height: jacket.height - 6).fill()
        }
        let disc = NSRect(x: rect.minX + 21, y: rect.minY + 1, width: 26, height: 26)
        NSColor(white: 0.025, alpha: 1).setFill()
        NSBezierPath(ovalIn: disc).fill()
        NSColor(white: 0.28, alpha: 1).setStroke()
        for inset in [CGFloat(2), 5, 8] { NSBezierPath(ovalIn: disc.insetBy(dx: inset, dy: inset)).stroke() }
        accent.setFill()
        NSBezierPath(ovalIn: disc.insetBy(dx: 10, dy: 10)).fill()
        NSColor(white: 0.18, alpha: 1).setFill()
        NSBezierPath(roundedRect: NSRect(x: rect.minX, y: rect.minY, width: 26, height: 27),
                     xRadius: 2, yRadius: 2).fill()
        accent.withAlphaComponent(0.7).setFill()
        NSRect(x: rect.minX + 3, y: rect.minY + 3, width: 2, height: 21).fill()
        accent.withAlphaComponent(0.2).setFill()
        NSRect(x: rect.minX + 8, y: rect.minY + 15, width: 14, height: 7).fill()
    }

    private func drawTapeStack(_ rect: NSRect) {
        for index in stride(from: 2, through: 0, by: -1) {
            let offset = CGFloat(index) * (expanded ? 1.5 : 2)
            let box = NSRect(x: rect.minX + offset, y: rect.minY + offset + 2,
                             width: 43, height: 25)
            NSColor(white: 0.17 + CGFloat(index) * 0.07, alpha: 1).setFill()
            NSBezierPath(roundedRect: box, xRadius: 3, yRadius: 3).fill()
        }
        accent.withAlphaComponent(0.65).setFill()
        NSRect(x: rect.minX + 4, y: rect.minY + 21, width: 35, height: 3).fill()
        for x in [rect.minX + 12, rect.minX + 31] {
            let center = NSPoint(x: x, y: rect.minY + 12)
            NSColor(white: 0.035, alpha: 1).setFill()
            NSBezierPath(ovalIn: NSRect(x: x - 6, y: center.y - 6, width: 12, height: 12)).fill()
            NSColor(white: 0.65, alpha: 1).setStroke()
            NSBezierPath(ovalIn: NSRect(x: x - 3, y: center.y - 3, width: 6, height: 6)).stroke()
            let spoke = NSBezierPath()
            spoke.move(to: NSPoint(x: x - 4, y: center.y))
            spoke.line(to: NSPoint(x: x + 4, y: center.y))
            spoke.stroke()
        }
    }
}
