import ServiceManagement
import SwiftUI

struct SettingsView: View {
    @EnvironmentObject var store: ProfileStore
    @Environment(\.openWindow) private var openWindow

    @State private var path = ClaudeLauncher.appPath
    @State private var pendingDelete: Profile?
    @State private var launchAtLogin = SMAppService.mainApp.status == .enabled
    @State private var loginNote: String?

    private var exists: Bool { FileManager.default.fileExists(atPath: path) }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                header
                appSection
                startupSection
                profilesSection
            }
            .padding(.horizontal, 24).padding(.top, 34).padding(.bottom, 24)
        }
        .frame(width: 560, height: min(390 + CGFloat(store.profiles.count) * 82, 700))
        .background(WindowBackground().ignoresSafeArea())
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

    private var header: some View {
        HStack(spacing: 16) {
            LogoView().frame(width: 56, height: 56)
                .clipShape(RoundedRectangle(cornerRadius: 13, style: .continuous))
            VStack(alignment: .leading, spacing: 3) {
                Text("Claudou").font(.system(size: 26, weight: .bold))
                Text("Run several Claude accounts side by side.")
                    .font(.system(size: 14)).foregroundStyle(.secondary)
            }
        }
    }

    // MARK: Claude.app

    private var appSection: some View {
        VStack(alignment: .leading, spacing: 10) {
            Card {
                VStack(alignment: .leading, spacing: 10) {
                    Text("Claude.app").font(.system(size: 15, weight: .semibold))
                    HStack(spacing: 8) {
                        TextField(ClaudeLauncher.defaultAppPath, text: $path)
                            .textFieldStyle(.roundedBorder)
                            .font(.system(size: 12, design: .monospaced))
                            .labelsHidden()
                            .onChange(of: path) { v in
                                ClaudeLauncher.appPath = v.trimmingCharacters(in: .whitespaces)
                            }
                        Button("Browse…", action: browse)
                        Button("Reset") { path = ClaudeLauncher.defaultAppPath }
                    }
                    .buttonStyle(.bordered).controlSize(.large)
                }
            }
            statusBanner
        }
    }

    private var statusBanner: some View {
        let color = exists ? Theme.success : Color.orange
        return HStack(spacing: 10) {
            Image(systemName: exists ? "checkmark.circle.fill" : "exclamationmark.triangle.fill")
                .font(.system(size: 18)).foregroundStyle(color)
            Text(exists ? "Claude.app found" : "Not found at this path")
                .font(.system(size: 14, weight: .medium))
            Spacer()
        }
        .padding(.horizontal, 16).padding(.vertical, 12)
        .background(color.opacity(0.18), in: RoundedRectangle(cornerRadius: 16, style: .continuous))
    }

    // MARK: Startup

    private var startupSection: some View {
        Card {
            VStack(alignment: .leading, spacing: 6) {
                HStack {
                    VStack(alignment: .leading, spacing: 2) {
                        Text("Launch at startup").font(.system(size: 15, weight: .semibold))
                        Text("Start Claudou in the menu bar when your computer starts.")
                            .font(.system(size: 12)).foregroundStyle(.secondary)
                    }
                    Spacer()
                    Toggle("Launch at startup", isOn: $launchAtLogin)
                        .toggleStyle(.switch).labelsHidden().tint(Theme.accent)
                }
                if let loginNote {
                    Text(loginNote).font(.system(size: 11)).foregroundStyle(Color.orange)
                }
            }
        }
        .onChange(of: launchAtLogin) { on in setLaunchAtLogin(on) }
        .onAppear { launchAtLogin = SMAppService.mainApp.status == .enabled }
    }

    private func setLaunchAtLogin(_ on: Bool) {
        guard on != (SMAppService.mainApp.status == .enabled) else { return }
        do {
            if on { try SMAppService.mainApp.register() } else { try SMAppService.mainApp.unregister() }
            loginNote = SMAppService.mainApp.status == .requiresApproval
                ? "Approve Claudou in System Settings → General → Login Items." : nil
        } catch {
            loginNote = "Could not change the login item: \(error.localizedDescription)"
            launchAtLogin = SMAppService.mainApp.status == .enabled
        }
    }

    // MARK: Profiles (CRUD)

    private var profilesSection: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Text("Profiles").font(.system(size: 17, weight: .bold))
                Spacer()
                Button("+ New profile") { openEditor(nil) }
                    .buttonStyle(.borderedProminent).tint(Theme.accent).controlSize(.large)
            }
            ForEach(store.profiles) { p in
                Card(padding: 12, radius: 16) { profileRow(p) }
            }
        }
    }

    private func profileRow(_ p: Profile) -> some View {
        HStack(spacing: 12) {
            AvatarView(initial: p.initial, color: Color(hex: p.colorHex), size: 40)
            VStack(alignment: .leading, spacing: 2) {
                HStack(spacing: 6) {
                    Text(p.name).font(.system(size: 14, weight: .semibold))
                    if store.running[p.id] != nil {
                        tag("RUNNING", Theme.success)
                    }
                    if p.isDefault {
                        tag("DEFAULT", .secondary)
                    }
                }
                Text(p.dir.path.replacingOccurrences(of: NSHomeDirectory(), with: "~"))
                    .font(.system(size: 11, design: .monospaced)).foregroundStyle(.secondary)
                    .lineLimit(1).truncationMode(.middle)
            }
            Spacer(minLength: 4)
            Button { NSWorkspace.shared.activateFileViewerSelecting([p.dir]) } label: { Image(systemName: "folder") }
                .buttonStyle(.borderless).help("Reveal data folder")
            Button("Edit") { openEditor(p) }.buttonStyle(.bordered).controlSize(.regular)
            Button { pendingDelete = p } label: { Image(systemName: "trash") }
                .buttonStyle(.borderless)
                .foregroundStyle(store.canDelete(p) ? Color.red : Color.secondary.opacity(0.4))
                .disabled(!store.canDelete(p))
                .help(p.isDefault ? "The default profile cannot be deleted"
                      : store.running[p.id] != nil ? "Quit this Claude before deleting" : "Delete")
        }
    }

    private func tag(_ text: String, _ color: some ShapeStyle) -> some View {
        Text(text).font(.system(size: 9, weight: .bold)).foregroundStyle(color)
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
