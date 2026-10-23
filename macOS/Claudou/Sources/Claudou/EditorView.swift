import SwiftUI

struct EditorView: View {
    @EnvironmentObject var store: ProfileStore
    @Environment(\.dismiss) private var dismiss

    @State private var name = ""
    @State private var colorHex = Theme.profileColors[0]
    @State private var dataDir = ""
    @State private var command = ""
    @State private var commandEdited = false

    private var isDefault: Bool { store.editing?.isDefault ?? false }

    /// Folder that will be used for this profile.
    private var resolvedDir: String? {
        if isDefault { return nil }
        let d = dataDir.trimmingCharacters(in: .whitespaces)
        if !d.isEmpty { return d }
        return ClaudeLauncher.profilesDir.appendingPathComponent(store.editing?.id ?? ProfileStore.slug(name)).path
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(store.editing == nil ? "New profile" : "Edit profile")
                .font(.system(size: 15, weight: .bold)).foregroundStyle(Theme.text)

            section("NAME") {
                field("e.g. Personal, Company A", text: $name).onSubmit(save)
            }

            section("COLOR") {
                HStack(spacing: 10) {
                    ForEach(Theme.profileColors, id: \.self) { c in
                        Button { colorHex = c } label: {
                            Rectangle().fill(Color(hex: c)).frame(width: 22, height: 22)
                                .overlay(Rectangle().stroke(Theme.text, lineWidth: colorHex == c ? 2 : 0))
                        }.buttonStyle(.plain)
                    }
                }
            }

            if !isDefault {
                section("DATA FOLDER (--user-data-dir)") {
                    HStack(spacing: 8) {
                        field("Leave empty to create one in Claudou/profiles", text: $dataDir, mono: true)
                        Button("Choose…", action: pickFolder).buttonStyle(GhostButtonStyle())
                    }
                }
            }

            section("LAUNCH COMMAND") {
                field("", text: $command, mono: true)
                    .onChange(of: command) { v in
                        if v != generated { commandEdited = true }
                    }
                HStack {
                    Text(commandEdited ? "Edited by hand — used exactly as written."
                                       : "Generated from the Claude.app path and data folder.")
                        .font(.system(size: 10)).foregroundStyle(Theme.dim)
                    Spacer()
                    if commandEdited {
                        Button("Regenerate") { commandEdited = false; command = generated }
                            .buttonStyle(.plain).font(.system(size: 10, weight: .semibold))
                            .foregroundStyle(Theme.accent)
                    }
                }
            }

            HStack {
                Button("Cancel") { dismiss() }.buttonStyle(GhostButtonStyle())
                    .keyboardShortcut(.cancelAction)
                Spacer()
                Button("Save", action: save).buttonStyle(AccentButtonStyle())
                    .keyboardShortcut(.defaultAction)
                    .disabled(name.trimmingCharacters(in: .whitespaces).isEmpty)
            }
            .padding(.top, 4)
        }
        .padding(18)
        .frame(width: 460)
        .background(Theme.bg)
        .onAppear(perform: load)
        .onChange(of: store.editing) { _ in load() }
        .onChange(of: name) { _ in syncCommand() }
        .onChange(of: dataDir) { _ in syncCommand() }
    }

    private var generated: String { ClaudeLauncher.buildCommand(dataDir: resolvedDir) }

    private func syncCommand() { if !commandEdited { command = generated } }

    private func field(_ placeholder: String, text: Binding<String>, mono: Bool = false) -> some View {
        TextField(placeholder, text: text).inputField(mono: mono)
    }

    private func section<C: View>(_ title: String, @ViewBuilder _ content: () -> C) -> some View {
        VStack(alignment: .leading, spacing: 5) {
            Text(title).font(.system(size: 10, weight: .bold)).foregroundStyle(Theme.dim)
            content()
        }
    }

    private func pickFolder() {
        let panel = NSOpenPanel()
        panel.canChooseDirectories = true
        panel.canChooseFiles = false
        panel.canCreateDirectories = true
        panel.showsHiddenFiles = true
        panel.prompt = "Choose"
        if panel.runModal() == .OK, let url = panel.url { dataDir = url.path }
    }

    private func load() {
        let p = store.editing
        name = p?.name ?? ""
        colorHex = p?.colorHex ?? Theme.profileColors[0]
        dataDir = p?.dataDir ?? ""
        commandEdited = p?.commandEdited ?? false
        command = p?.effectiveCommand ?? ClaudeLauncher.buildCommand(dataDir: resolvedDir)
    }

    private func save() {
        let n = name.trimmingCharacters(in: .whitespaces)
        guard !n.isEmpty else { return }
        let dir = dataDir.trimmingCharacters(in: .whitespaces)
        let cmd = commandEdited ? command : nil
        if var p = store.editing {
            p.name = n; p.colorHex = colorHex
            if !p.isDefault { p.dataDir = dir.isEmpty ? nil : dir }
            p.command = cmd; p.commandEdited = commandEdited
            store.update(p)
        } else {
            store.create(name: n, colorHex: colorHex,
                         dataDir: dir.isEmpty ? nil : dir, command: cmd, commandEdited: commandEdited)
        }
        dismiss()
    }
}
