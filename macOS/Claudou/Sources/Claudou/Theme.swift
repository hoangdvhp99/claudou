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

/// Dark-orange brand palette.
enum Theme {
    static let accent = Color(hex: "#e8590c")
    static let card = Color(hex: "#241a14")
    static let cardHover = Color(hex: "#2d2018")
    static let bg = Color(hex: "#140f0b")
    static let surface = Color(hex: "#1b1410")
    static let input = Color(hex: "#100b08")
    static let border = Color(hex: "#3a2b21")
    static let text = Color(hex: "#f5ece4")
    static let dim = Color(hex: "#a38f80")
    static let success = Color(hex: "#5fb878")

    static let profileColors = ["#e8590c", "#f59f00", "#d9480f", "#c2255c",
                                "#7048e8", "#1c7ed6", "#0ca678", "#868e96"]
}

struct AccentButtonStyle: ButtonStyle {
    var color: Color = Theme.accent
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.system(size: 11, weight: .semibold))
            .foregroundStyle(.white)
            .padding(.horizontal, 10).padding(.vertical, 4)
            .background(color.opacity(configuration.isPressed ? 0.7 : 1))
    }
}

struct GhostButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.system(size: 11, weight: .medium))
            .foregroundStyle(Theme.dim)
            .padding(.horizontal, 10).padding(.vertical, 4)
            .background(configuration.isPressed ? Theme.card : Color.clear)
            .overlay(Rectangle().stroke(Theme.border))
    }
}

/// Square text-field chrome shared by the editor and settings windows.
struct InputFieldStyle: ViewModifier {
    var mono = false
    func body(content: Content) -> some View {
        content
            .textFieldStyle(.plain)
            .font(.system(size: mono ? 11 : 12, design: mono ? .monospaced : .default))
            .padding(7)
            .background(Theme.input)
            .overlay(Rectangle().stroke(Theme.border))
    }
}

extension View {
    func inputField(mono: Bool = false) -> some View { modifier(InputFieldStyle(mono: mono)) }
}
