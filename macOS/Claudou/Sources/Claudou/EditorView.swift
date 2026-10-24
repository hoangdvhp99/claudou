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
        VStack(alignment: .leading, spacing: 14) {
            Text(store.editing == nil ? "New profile" : "Edit profile")
                .font(.system(size: 22, weight: .bold))

            Card {
                VStack(alignment: .leading, spacing: 14) {
                    section("Name") { field("e.g. Personal, Company A", text: $name).onSubmit(save) }

                    section("Color") {
                        HStack(spacing: 12) {
                            ForEach(Theme.profileColors, id: \.self) { c in
                                Button { colorHex = c } label: {
                                    Circle().fill(Color(hex: c)).frame(width: 24, height: 24)
                                        .overlay(Circle().stroke(Color.primary, lineWidth: colorHex == c ? 2 : 0).padding(-3))
                                }.buttonStyle(.plain)
                            }
                        }
                        .padding(.vertical, 3)
                    }

                    if !isDefault {
                        section("Data folder (--user-data-dir)") {
                            HStack(spacing: 8) {
                                field("Leave empty to create one in Claudou/profiles", text: $dataDir, mono: true)
                                Button("Choose…", action: pickFolder).buttonStyle(.bordered).controlSize(.large)
                            }
                        }
                    }

                    section("Launch command") {
                        field("", text: $command, mono: true)
                            .onChange(of: command) { v in
                                if v != generated { commandEdited = true }
                            }
                        HStack {
                            Text(commandEdited ? "Edited by hand — used exactly as written."
                                               : "Generated from the Claude.app path and data folder.")
                                .font(.system(size: 11)).foregroundStyle(.secondary)
                            Spacer()
                            if commandEdited {
                                Button("Regenerate") { commandEdited = false; command = generated }
                                    .buttonStyle(.borderless).font(.system(size: 11, weight: .semibold))
                            }
                        }
                    }
                }
            }

            HStack {
                Button("Cancel") { dismiss() }.buttonStyle(.bordered)
                    .keyboardShortcut(.cancelAction)
                Spacer()
                Button("Save", action: save).buttonStyle(.borderedProminent).tint(Theme.accent)
                    .keyboardShortcut(.defaultAction)
                    .disabled(name.trimmingCharacters(in: .whitespaces).isEmpty)
            }
            .controlSize(.large)
        }
        .padding(.horizontal, 24).padding(.top, 34).padding(.bottom, 22)
        .frame(width: 520)
        .background(WindowBackground().ignoresSafeArea())
        .onAppear(perform: load)
        .onChange(of: store.editing) { _ in load() }
        .onChange(of: name) { _ in syncCommand() }
        .onChange(of: dataDir) { _ in syncCommand() }
    }

    private var generated: String { ClaudeLauncher.buildCommand(dataDir: resolvedDir) }

    private func syncCommand() { if !commandEdited { command = generated } }

    private func field(_ placeholder: String, text: Binding<String>, mono: Bool = false) -> some View {
        TextField(placeholder, text: text)
            .textFieldStyle(.roundedBorder)
            .controlSize(.large)
            .font(.system(size: mono ? 12 : 13, design: mono ? .monospaced : .default))
            .labelsHidden()
    }

    private func section<C: View>(_ title: String, @ViewBuilder _ content: () -> C) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(title).font(.system(size: 13, weight: .semibold))
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
