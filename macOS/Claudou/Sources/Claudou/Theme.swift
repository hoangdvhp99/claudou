import SwiftUI

extension Color {
    init(hex: String) {
        let h = hex.trimmingCharacters(in: CharacterSet(charactersIn: "#"))
        var v: UInt64 = 0
        Scanner(string: h).scanHexInt64(&v)
        self.init(red: Double((v >> 16) & 0xff) / 255,
                  green: Double((v >> 8) & 0xff) / 255,
                  blue: Double(v & 0xff) / 255)
    }
}

/// Brand colors. Surfaces, text and borders use the system's semantic colors on macOS
/// (SPEC §5.1), so only the accent, success and profile colors live here.
enum Theme {
    static let accent = Color(hex: "#e8590c")
    static let success = Color(hex: "#5fb878")
    /// Success as a fill behind white text (the plain success green is too light for that).
    static let successStrong = Color(hex: "#2f9e5b")

    static let profileColors = ["#e8590c", "#f59f00", "#d9480f", "#c2255c",
                                "#7048e8", "#1c7ed6", "#0ca678", "#868e96"]

    static let avatarRadius: CGFloat = 10
}

/// Flat translucent rounded card, like the sections of a native macOS 26 welcome sheet.
struct Card<Content: View>: View {
    var padding: CGFloat = 16
    var radius: CGFloat = 16
    @ViewBuilder var content: Content
    var body: some View {
        content
            .padding(padding)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(Color.primary.opacity(0.07),
                        in: RoundedRectangle(cornerRadius: radius, style: .continuous))
    }
}

/// Full-window translucency (vibrancy behind the window) with a transparent title bar.
struct WindowBackground: NSViewRepresentable {
    final class EffectView: NSVisualEffectView {
        override func viewDidMoveToWindow() {
            super.viewDidMoveToWindow()
            guard let w = window else { return }
            w.titlebarAppearsTransparent = true
            w.titleVisibility = .hidden
            w.styleMask.insert(.fullSizeContentView)
            w.isMovableByWindowBackground = true
        }
    }
    func makeNSView(context: Context) -> NSVisualEffectView {
        let v = EffectView()
        v.material = .underWindowBackground
        v.blendingMode = .behindWindow
        v.state = .active
        return v
    }
    func updateNSView(_ v: NSVisualEffectView, context: Context) {}
}

/// Profile avatar: rounded square, profile color, white initial.
struct AvatarView: View {
    let initial: String
    let color: Color
    var size: CGFloat = 34
    var body: some View {
        Text(initial)
            .font(.system(size: size * 0.45, weight: .bold))
            .foregroundStyle(.white)
            .frame(width: size, height: size)
            .background(color, in: RoundedRectangle(cornerRadius: Theme.avatarRadius, style: .continuous))
    }
}
