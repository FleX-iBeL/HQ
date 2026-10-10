// H48: draws an SVG into a PNG with a transparent background (qlmanage gives a white one, which shows as a
// white square around the icon in the Dock). macOS reads SVG itself (NSImage). Usage: svg2png in.svg out.png size
import AppKit
let a = CommandLine.arguments
guard a.count == 4, let size = Int(a[3]), let img = NSImage(contentsOf: URL(fileURLWithPath: a[1])),
      let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: size, pixelsHigh: size, bitsPerSample: 8,
                                 samplesPerPixel: 4, hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB,
                                 bytesPerRow: 0, bitsPerPixel: 0) else { exit(1) }
NSGraphicsContext.saveGraphicsState()
NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)
NSColor.clear.set()
NSRect(x: 0, y: 0, width: size, height: size).fill()
img.draw(in: NSRect(x: 0, y: 0, width: size, height: size))
NSGraphicsContext.restoreGraphicsState()
guard let png = rep.representation(using: .png, properties: [:]) else { exit(1) }
try png.write(to: URL(fileURLWithPath: a[2]))
