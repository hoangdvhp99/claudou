import SwiftUI

/// Menu-style popover, modelled on a native macOS status-item menu.
struct MenuView: View {
    @EnvironmentObject var store: ProfileStore
    @Environment(\.openWindow) private var openWindow

    private let rowHeight: CGFloat = 48

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            header
            divider

            // ScrollView has no intrinsic height inside MenuBarExtra: size it to the rows.
            ScrollView {
                VStack(spacing: 2) {
                    ForEach(store.profiles) { p in
                        ProfileRow(profile: p, height: rowHeight)
                    }
                }
                .padding(.horizontal, 8).padding(.vertical, 6)
            }
            .frame(height: min(CGFloat(store.profiles.count) * (rowHeight + 2) + 10, 330))

            divider
            VStack(spacing: 0) {
                MenuItem(title: "Settings…") {
                    openWindow(id: "settings"); NSApp.activate(ignoringOtherApps: true)
                }
                MenuItem(title: "Quit", shortcut: "⌘Q") { NSApplication.shared.terminate(nil) }
                    .keyboardShortcut("q")
            }
            .padding(.horizontal, 6).padding(.vertical, 6)
        }
        .frame(width: 340)
        .alert("Error", isPresented: Binding(
            get: { store.errorMessage != nil },
            set: { if !$0 { store.errorMessage = nil } })
        ) {
            Button("OK") { store.errorMessage = nil }
        } message: { Text(store.errorMessage ?? "") }
    }

    private var header: some View {
        HStack(spacing: 10) {
            LogoView().frame(width: 30, height: 30)
                .clipShape(RoundedRectangle(cornerRadius: 7, style: .continuous))
            VStack(alignment: .leading, spacing: 1) {
                Text("Claudou").font(.system(size: 14, weight: .semibold))
                Text(store.anyRunning ? "\(store.running.count) running" : "Idle")
                    .font(.system(size: 12, weight: .medium))
                    .foregroundStyle(store.anyRunning ? Theme.success : Color.secondary)
            }
            Spacer()
        }
        .padding(.horizontal, 14).padding(.top, 14).padding(.bottom, 12)
    }

    private var divider: some View {
        Rectangle().fill(Color.primary.opacity(0.12)).frame(height: 1).padding(.horizontal, 14)
    }
}

/// Plain full-width menu row with the rounded hover highlight of a native menu.
struct MenuItem: View {
    let title: String
    var shortcut: String? = nil
    let action: () -> Void
    @State private var hover = false

    var body: some View {
        Button(action: action) {
            HStack {
                Text(title).font(.system(size: 13))
                Spacer()
                if let shortcut { Text(shortcut).font(.system(size: 13)).foregroundStyle(.secondary) }
            }
            .padding(.horizontal, 10).frame(height: 28)
            .background(hover ? Color.primary.opacity(0.12) : Color.clear,
                        in: RoundedRectangle(cornerRadius: 8, style: .continuous))
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .onHover { hover = $0 }
    }
}

/// Small filled pill, like the "Tap to open" badge in a status-item menu.
struct PillButtonStyle: ButtonStyle {
    var color: Color
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.system(size: 12, weight: .semibold))
            .foregroundStyle(.white)
            .frame(width: 52).padding(.vertical, 4)
            .background(color.opacity(configuration.isPressed ? 0.7 : 1), in: Capsule())
    }
}

struct ProfileRow: View {
    @EnvironmentObject var store: ProfileStore
    let profile: Profile
    let height: CGFloat
    @State private var hover = false

    private var isRunning: Bool { store.running[profile.id] != nil }
    private var tint: Color { Color(hex: profile.colorHex) }

    private var subtitle: String {
        if isRunning { return "Running" }
        guard let d = profile.lastUsed else { return "Never opened" }
        return "Opened " + d.formatted(.dateTime.month(.abbreviated).day()) + ", "
            + d.formatted(date: .omitted, time: .shortened)
    }

    var body: some View {
        HStack(spacing: 10) {
            AvatarView(initial: profile.initial, color: tint, size: 30)

            VStack(alignment: .leading, spacing: 1) {
                Text(profile.name).font(.system(size: 13, weight: .medium)).lineLimit(1)
                Text(subtitle).font(.system(size: 11))
                    .foregroundStyle(isRunning ? Theme.success : Color.secondary).lineLimit(1)
            }
            Spacer(minLength: 4)

            Group {
                if store.launchingID == profile.id {
                    ProgressView().controlSize(.small)
                } else {
                    Button(isRunning ? "Show" : "Open") { store.open(profile) }
                        .buttonStyle(PillButtonStyle(color: isRunning ? Theme.successStrong : Theme.accent))
                        .disabled(store.launchingID != nil)
                }
            }
            .frame(width: 52)

            // Fixed slot so Open/Show line up whether or not the quit button is shown.
            Color.clear.frame(width: 16, height: 16)
                .overlay {
                    if isRunning {
                        Button { store.quit(profile) } label: { Image(systemName: "xmark") }
                            .buttonStyle(.borderless).foregroundStyle(.secondary).help("Quit this Claude")
                    }
                }
        }
        .padding(.horizontal, 12)
        .frame(height: height)  // before the background, so the hover highlight fills the whole row
        .background(hover ? Color.primary.opacity(0.1) : Color.clear,
                    in: RoundedRectangle(cornerRadius: 8, style: .continuous))
        .contentShape(Rectangle())
        .onHover { hover = $0 }
        .onTapGesture(count: 2) { store.open(profile) }
    }
}

struct LogoView: View {
    var body: some View {
        Group {
            if let url = Bundle.main.url(forResource: "logo", withExtension: "png"),
               let img = NSImage(contentsOf: url) {
                Image(nsImage: img).resizable().interpolation(.none).scaledToFill()
            } else {
                Theme.accent
            }
        }
        .clipShape(RoundedRectangle(cornerRadius: 6, style: .continuous))
    }
}
