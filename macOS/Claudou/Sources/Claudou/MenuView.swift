import SwiftUI

struct MenuView: View {
    @EnvironmentObject var store: ProfileStore
    @Environment(\.openWindow) private var openWindow

    private let rowHeight: CGFloat = 44

    var body: some View {
        VStack(spacing: 0) {
            header
            Rectangle().fill(Theme.accent).frame(height: 1)

            // ScrollView has no intrinsic height inside MenuBarExtra: size it to the rows.
            ScrollView {
                VStack(spacing: 0) {
                    ForEach(store.profiles) { p in
                        ProfileRow(profile: p)
                            .frame(height: rowHeight)
                        Rectangle().fill(Theme.border).frame(height: 1)
                    }
                }
            }
            .frame(height: min(CGFloat(store.profiles.count) * (rowHeight + 1), 330))

            footer
        }
        .frame(width: 300)
        .background(Theme.bg)
        .preferredColorScheme(.dark)
        .alert("Error", isPresented: Binding(
            get: { store.errorMessage != nil },
            set: { if !$0 { store.errorMessage = nil } })
        ) {
            Button("OK") { store.errorMessage = nil }
        } message: { Text(store.errorMessage ?? "") }
    }

    private var header: some View {
        HStack(spacing: 8) {
            LogoView().frame(width: 22, height: 22)
            Text("Claudou").font(.system(size: 13, weight: .bold)).foregroundStyle(Theme.text)
            Spacer()
            HStack(spacing: 5) {
                Rectangle().fill(store.anyRunning ? Theme.success : Theme.dim).frame(width: 6, height: 6)
                Text(store.anyRunning ? "\(store.running.count) running" : "Idle")
                    .font(.system(size: 10, weight: .medium))
                    .foregroundStyle(store.anyRunning ? Theme.success : Theme.dim)
            }
        }
        .padding(.horizontal, 12).padding(.vertical, 9)
        .background(Theme.surface)
    }

    private var footer: some View {
        HStack(spacing: 10) {
            Button { openWindow(id: "settings"); NSApp.activate(ignoringOtherApps: true) } label: {
                Label("Settings", systemImage: "gearshape")
            }
            .buttonStyle(.plain).font(.system(size: 11)).foregroundStyle(Theme.dim)
            Spacer()
            Button("Quit Claudou") { NSApplication.shared.terminate(nil) }
                .buttonStyle(.plain)
                .font(.system(size: 11)).foregroundStyle(Theme.dim)
                .keyboardShortcut("q")
        }
        .padding(.horizontal, 12).padding(.vertical, 8)
        .background(Theme.surface)
    }
}

struct ProfileRow: View {
    @EnvironmentObject var store: ProfileStore
    let profile: Profile
    @State private var hover = false

    private var isRunning: Bool { store.running[profile.id] != nil }
    private var tint: Color { Color(hex: profile.colorHex) }

    private var subtitle: String {
        if isRunning { return "Running" }
        guard let d = profile.lastUsed else { return "Never opened" }
        return "Last opened " + d.formatted(.dateTime.month(.abbreviated).day().hour().minute())
    }

    var body: some View {
        HStack(spacing: 10) {
            Text(profile.initial)
                .font(.system(size: 13, weight: .bold))
                .foregroundStyle(.white)
                .frame(width: 28, height: 28)
                .background(tint)

            VStack(alignment: .leading, spacing: 1) {
                Text(profile.name).font(.system(size: 12, weight: .semibold))
                    .foregroundStyle(Theme.text).lineLimit(1)
                Text(subtitle).font(.system(size: 10))
                    .foregroundStyle(isRunning ? Theme.success : Theme.dim).lineLimit(1)
            }
            Spacer(minLength: 4)

            if store.launchingID == profile.id {
                ProgressView().controlSize(.small)
            } else {
                Button(isRunning ? "Show" : "Open") { store.open(profile) }
                    .buttonStyle(AccentButtonStyle(color: isRunning ? Theme.success : Theme.accent))
                    .disabled(store.launchingID != nil)
            }

            if isRunning {
                Button { store.quit(profile) } label: { Image(systemName: "xmark") }
                    .buttonStyle(.plain).foregroundStyle(Theme.dim).help("Quit this Claude")
            }
        }
        .padding(.horizontal, 12)
        .background(hover ? Theme.cardHover : Color.clear)
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
        .clipShape(Rectangle())
    }
}
