// Usage: swift scripts/make_menubar.swift <in.png> <out.png> [pixels=40]
// Turns a black-on-white glyph into a transparent, tightly cropped, square template image.
import AppKit

let a = CommandLine.arguments
guard a.count >= 3, let src = NSImage(contentsOfFile: a[1]),
      let cg = src.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
    FileHandle.standardError.write(Data("usage: make_menubar <in> <out> [px]\n".utf8)); exit(1)
}
let size = a.count > 3 ? Int(a[3]) ?? 40 : 40
let w = cg.width, h = cg.height

// 1. Read as RGBA, ink = darkness.
var px = [UInt8](repeating: 0, count: w * h * 4)
let cs = CGColorSpaceCreateDeviceRGB()
let ctx = CGContext(data: &px, width: w, height: h, bitsPerComponent: 8, bytesPerRow: w * 4, space: cs,
                    bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
ctx.setFillColor(NSColor.white.cgColor); ctx.fill(CGRect(x: 0, y: 0, width: w, height: h))
ctx.draw(cg, in: CGRect(x: 0, y: 0, width: w, height: h))

var ink = [UInt8](repeating: 0, count: w * h)
var minX = w, minY = h, maxX = 0, maxY = 0
for y in 0..<h { for x in 0..<w {
    let i = (y * w + x) * 4
    let lum = (Int(px[i]) * 3 + Int(px[i + 1]) * 6 + Int(px[i + 2])) / 10
    let v = UInt8(max(0, min(255, 255 - lum)))
    ink[y * w + x] = v
    if v > 100 { minX = min(minX, x); maxX = max(maxX, x); minY = min(minY, y); maxY = max(maxY, y) }
} }

// 1b. "Solid" mode: fill enclosed regions (hair, face, claws) but keep small ones
// (eyes, headband gem) and the headband stripe as cut-outs.
let solid = ProcessInfo.processInfo.environment["MENUBAR_OUTLINE"] == nil
if solid {
    let thr = 128
    var label = [Int32](repeating: 0, count: w * h)   // 0 unvisited, -1 ink, -2 outside, >0 enclosed comp
    for i in 0..<(w * h) where Int(ink[i]) > thr { label[i] = -1 }
    func flood(_ start: Int, _ id: Int32) -> (count: Int, minX: Int, maxX: Int, minY: Int, maxY: Int) {
        var stack = [start]; label[start] = id
        var n = 0, x0 = w, x1 = 0, y0 = h, y1 = 0
        while let p = stack.popLast() {
            n += 1; let x = p % w, y = p / w
            x0 = min(x0, x); x1 = max(x1, x); y0 = min(y0, y); y1 = max(y1, y)
            for (dx, dy) in [(1, 0), (-1, 0), (0, 1), (0, -1)] {
                let nx = x + dx, ny = y + dy
                if nx >= 0, nx < w, ny >= 0, ny < h, label[ny * w + nx] == 0 { label[ny * w + nx] = id; stack.append(ny * w + nx) }
            }
        }
        return (n, x0, x1, y0, y1)
    }
    for x in 0..<w { for y in [0, h - 1] where label[y * w + x] == 0 { _ = flood(y * w + x, -2) } }
    for y in 0..<h { for x in [0, w - 1] where label[y * w + x] == 0 { _ = flood(y * w + x, -2) } }
    let silhouetteArea = label.filter { $0 != -2 }.count
    var next: Int32 = 1
    for i in 0..<(w * h) where label[i] == 0 {
        let c = flood(i, next)
        let ratio = Double(c.count) / Double(silhouetteArea)
        let bw = c.maxX - c.minX + 1, bh = c.maxY - c.minY + 1
        let aspect = Double(max(bw, bh)) / Double(max(1, min(bw, bh)))
        // cut-out if small (eyes, gem) or a thin horizontal stripe (headband)
        let keep = ratio < 0.015 || (aspect > 4 && ratio < 0.12)
        if ProcessInfo.processInfo.environment["MENUBAR_DEBUG"] != nil {
            print("comp \(next): ratio \(String(format: "%.4f", ratio)) box \(bw)x\(bh) aspect \(String(format: "%.1f", aspect)) -> \(keep ? "cutout" : "fill")")
        }
        if !keep { for j in 0..<(w * h) where label[j] == next { ink[j] = 255 } }
        next += 1
    }
    // Isolated ink blobs (the eyes) become cut-outs inside the now-solid face.
    var seen = [Bool](repeating: false, count: w * h)
    var blobs: [[Int]] = []
    for i in 0..<(w * h) where label[i] == -1 && !seen[i] {
        var stack = [i], cells: [Int] = []; seen[i] = true
        while let p = stack.popLast() {
            cells.append(p); let x = p % w, y = p / w
            for (dx, dy) in [(1, 0), (-1, 0), (0, 1), (0, -1)] {
                let nx = x + dx, ny = y + dy
                if nx >= 0, nx < w, ny >= 0, ny < h, label[ny * w + nx] == -1, !seen[ny * w + nx] { seen[ny * w + nx] = true; stack.append(ny * w + nx) }
            }
        }
        blobs.append(cells)
    }
    if let biggest = blobs.map({ $0.count }).max() {
        for b in blobs where b.count < biggest / 20 { for p in b { ink[p] = 0 } }
    }
}

// 2. Tight square crop, centered.
let cw = maxX - minX + 1, ch = maxY - minY + 1, side = max(cw, ch)
let ox = minX - (side - cw) / 2, oy = minY - (side - ch) / 2

// 3. Black glyph with alpha = ink, cropped onto a square canvas.
var glyph = [UInt8](repeating: 0, count: side * side * 4)
for y in 0..<side { for x in 0..<side {
    let sx = ox + x, sy = oy + y
    if sx >= 0, sx < w, sy >= 0, sy < h { glyph[(y * side + x) * 4 + 3] = ink[sy * w + sx] }
} }
let gctx = CGContext(data: &glyph, width: side, height: side, bitsPerComponent: 8, bytesPerRow: side * 4,
                     space: cs, bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
let glyphImg = gctx.makeImage()!

// 4. Downscale with a 1px margin.
let out = CGContext(data: nil, width: size, height: size, bitsPerComponent: 8, bytesPerRow: 0, space: cs,
                    bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
out.interpolationQuality = .high
out.draw(glyphImg, in: CGRect(x: 1, y: 1, width: size - 2, height: size - 2))
let rep = NSBitmapImageRep(cgImage: out.makeImage()!)
try! rep.representation(using: .png, properties: [:])!.write(to: URL(fileURLWithPath: a[2]))
