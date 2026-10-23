import SwiftUI

struct SettingsView: View {
    @EnvironmentObject var store: ProfileStore
    @Environment(\.openWindow) private var openWindow

    @State private var path = ClaudeLauncher.appPath
    @State private var pendingDelete: Profile?

    private var exists: Bool { FileManager.default.fileExists(atPath: path) }
    private let rowHeight: CGFloat = 46

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            appSection
            Rectangle().fill(Theme.border).frame(height: 1)
            profilesSection
        }
        .padding(18).frame(width: 500).background(Theme.bg)
        .onAppear { path = ClaudeLauncher.appPath }
        .confirmationDialog(
            pendingDelete.map { store.isOwnedFolder($0) ? "Delete “\($0.name)”?" : "Remove “\($0.name)”?" } ?? "",
            isPresented: Binding(get: { pendingDelete != nil }, set: { if !$0 { pendingDelete = nil } }),
            presenting: pendingDelete
        ) { p in
            Button(store.isOwnedFolder(p) ? "Delete permanently" : "Remove from list", role: .destructive) {
                store.delete(p)
            }
        } message: { p in
            Text(store.isOwnedFolder(p)
                 ? "Sessions and chat history in this profile will be erased."
                 : "The data folder is kept; it is only removed from Claudou.")
        }
    }

    // MARK: Claude.app

    private var appSection: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("CLAUDE.APP").font(.system(size: 10, weight: .bold)).foregroundStyle(Theme.dim)
            HStack(spacing: 6) {
                TextField(ClaudeLauncher.defaultAppPath, text: $path)
                    .inputField(mono: true)
                    .onChange(of: path) { v in
                        ClaudeLauncher.appPath = v.trimmingCharacters(in: .whitespaces)
                    }
                Button("Browse…", action: browse).buttonStyle(GhostButtonStyle())
                Button("Reset") { path = ClaudeLauncher.defaultAppPath }.buttonStyle(GhostButtonStyle())
            }
            HStack(spacing: 5) {
                Image(systemName: exists ? "checkmark.circle.fill" : "exclamationmark.triangle.fill")
                Text(exists ? "Claude.app found" : "Not found at this path")
            }
            .font(.system(size: 10)).foregroundStyle(exists ? Theme.success : Theme.accent)
        }
    }

    // MARK: Profiles (CRUD)

    private var profilesSection: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text("PROFILES").font(.system(size: 10, weight: .bold)).foregroundStyle(Theme.dim)
                Spacer()
                Button("+ New profile") { openEditor(nil) }.buttonStyle(AccentButtonStyle())
            }

            ScrollView {
                VStack(spacing: 0) {
                    ForEach(store.profiles) { p in
                        profileRow(p).frame(height: rowHeight)
                        Rectangle().fill(Theme.border).frame(height: 1)
                    }
                }
            }
            .frame(height: min(CGFloat(store.profiles.count) * (rowHeight + 1), 280))
            .overlay(Rectangle().stroke(Theme.border, lineWidth: 1))
        }
    }

    private func profileRow(_ p: Profile) -> some View {
        HStack(spacing: 10) {
            Text(p.initial).font(.system(size: 13, weight: .bold)).foregroundStyle(.white)
                .frame(width: 28, height: 28).background(Color(hex: p.colorHex))
            VStack(alignment: .leading, spacing: 1) {
                HStack(spacing: 6) {
                    Text(p.name).font(.system(size: 12, weight: .semibold)).foregroundStyle(Theme.text)
                    if store.running[p.id] != nil {
                        Text("RUNNING").font(.system(size: 8, weight: .bold)).foregroundStyle(Theme.success)
                    }
                    if p.isDefault {
                        Text("DEFAULT").font(.system(size: 8, weight: .bold)).foregroundStyle(Theme.dim)
                    }
                }
                Text(p.dir.path.replacingOccurrences(of: NSHomeDirectory(), with: "~"))
                    .font(.system(size: 10, design: .monospaced)).foregroundStyle(Theme.dim)
                    .lineLimit(1).truncationMode(.middle)
            }
            Spacer(minLength: 4)
            Button { NSWorkspace.shared.activateFileViewerSelecting([p.dir]) } label: { Image(systemName: "folder") }
                .buttonStyle(.plain).foregroundStyle(Theme.dim).help("Reveal data folder")
            Button("Edit") { openEditor(p) }.buttonStyle(GhostButtonStyle())
            Button { pendingDelete = p } label: { Image(systemName: "trash") }
                .buttonStyle(.plain)
                .foregroundStyle(store.canDelete(p) ? Theme.accent : Theme.border)
                .disabled(!store.canDelete(p))
                .help(p.isDefault ? "The default profile cannot be deleted"
                      : store.running[p.id] != nil ? "Quit this Claude before deleting" : "Delete")
        }
        .padding(.horizontal, 10)
    }

    private func openEditor(_ p: Profile?) {
        store.editing = p
        openWindow(id: "editor")
        NSApp.activate(ignoringOtherApps: true)
    }

    private func browse() {
        let panel = NSOpenPanel()
        panel.allowedContentTypes = [.application]
        panel.directoryURL = URL(fileURLWithPath: "/Applications")
        panel.prompt = "Choose"
        if panel.runModal() == .OK, let url = panel.url { path = url.path }
    }
}
