import Foundation
import SwiftUI

struct Profile: Codable, Identifiable, Equatable {
    var id: String            // folder name under profiles/ ("default" = Claude's own data)
    var name: String
    var colorHex: String
    var lastUsed: Date?
    /// user-data-dir; nil = Claudou's profiles/<id> (or Claude's own folder for "default").
    var dataDir: String?
    /// Saved launch command; used as-is only when `commandEdited` is true.
    var command: String?
    var commandEdited: Bool = false

    var initial: String { String(name.trimmingCharacters(in: .whitespaces).first ?? "?").uppercased() }
    var isDefault: Bool { id == "default" }
    /// Command that will actually run (regenerated from Claude.app path unless hand-edited).
    var effectiveCommand: String {
        if commandEdited, let command, !command.isEmpty { return command }
        return ClaudeLauncher.buildCommand(dataDir: isDefault ? nil : dir.path)
    }
    var dir: URL {
        if isDefault { return ClaudeLauncher.defaultDataDir }
        if let dataDir, !dataDir.isEmpty { return URL(fileURLWithPath: dataDir) }
        return ClaudeLauncher.profilesDir.appendingPathComponent(id)
    }
}

@MainActor
final class ProfileStore: ObservableObject {
    @Published private(set) var profiles: [Profile] = []
    /// profile id → pid of its running Claude process
    @Published private(set) var running: [String: pid_t] = [:]
    @Published var launchingID: String?
    @Published var errorMessage: String?
    /// Profile being edited in the editor window (nil = creating).
    @Published var editing: Profile?

    var anyRunning: Bool { !running.isEmpty }

    private var configURL: URL { ClaudeLauncher.claudouRoot.appendingPathComponent("config.json") }
    private var timer: Timer?

    init() {
        try? FileManager.default.createDirectory(at: ClaudeLauncher.profilesDir,
                                                 withIntermediateDirectories: true)
        load()
        if !profiles.contains(where: { $0.isDefault }) {
            profiles.insert(Profile(id: "default", name: "Default",
                                    colorHex: Theme.profileColors[0]), at: 0)
            save()
        }
        refreshState()
        timer = Timer.scheduledTimer(withTimeInterval: 2, repeats: true) { [weak self] _ in
            Task { @MainActor in self?.refreshState() }
        }
    }

    // MARK: Persistence

    private func load() {
        guard let data = try? Data(contentsOf: configURL) else { return }
        let dec = JSONDecoder(); dec.dateDecodingStrategy = .iso8601
        profiles = (try? dec.decode([Profile].self, from: data)) ?? []
    }

    private func save() {
        let enc = JSONEncoder()
        enc.dateEncodingStrategy = .iso8601
        enc.outputFormatting = [.prettyPrinted, .sortedKeys]
        if let data = try? enc.encode(profiles) { try? data.write(to: configURL, options: .atomic) }
    }

    // MARK: State

    func refreshState() {
        let snapshot = profiles
        Task.detached {
            let r = ClaudeLauncher.runningPIDs(for: snapshot)
            await MainActor.run { if self.running != r { self.running = r } }
        }
    }

    // MARK: CRUD

    @discardableResult
    func create(name: String, colorHex: String, dataDir: String? = nil,
                command: String? = nil, commandEdited: Bool = false) -> Profile {
        var slug = Self.slug(name)
        let base = slug; var i = 2
        while profiles.contains(where: { $0.id == slug }) { slug = "\(base)_\(i)"; i += 1 }
        let p = Profile(id: slug, name: name, colorHex: colorHex,
                        lastUsed: nil, dataDir: dataDir,
                        command: command, commandEdited: commandEdited)
        try? FileManager.default.createDirectory(at: p.dir, withIntermediateDirectories: true)
        profiles.append(p); save()
        return p
    }

    func update(_ p: Profile) {
        guard let i = profiles.firstIndex(where: { $0.id == p.id }) else { return }
        profiles[i] = p; save()
    }

    func isOwnedFolder(_ p: Profile) -> Bool { p.dataDir == nil }

    func canDelete(_ p: Profile) -> Bool { !p.isDefault && running[p.id] == nil }

    /// Deletes Claudou-owned data; folders you chose yourself are only un-listed, never erased.
    func delete(_ p: Profile) {
        guard canDelete(p) else { return }
        if p.dataDir == nil { try? FileManager.default.removeItem(at: p.dir) }
        profiles.removeAll { $0.id == p.id }
        save(); refreshState()
    }

    // MARK: Launch / focus / quit

    func open(_ p: Profile) {
        if let pid = running[p.id] { ClaudeLauncher.focus(pid: pid); return }
        guard launchingID == nil else { return }
        launchingID = p.id
        Task {
            do {
                try await ClaudeLauncher.run(command: p.effectiveCommand)
                var u = p; u.lastUsed = Date(); update(u)
            } catch {
                errorMessage = error.localizedDescription
            }
            // give the new process a moment to appear in `ps`
            try? await Task.sleep(nanoseconds: 1_200_000_000)
            launchingID = nil
            refreshState()
        }
    }

    func quit(_ p: Profile) {
        guard let pid = running[p.id] else { return }
        Task { await ClaudeLauncher.quit(pid: pid); refreshState() }
    }

    static func slug(_ s: String) -> String {
        let folded = s.folding(options: [.diacriticInsensitive, .caseInsensitive], locale: .current)
            .replacingOccurrences(of: "đ", with: "d")
        let out = folded.map { $0.isLetter || $0.isNumber || $0 == "-" ? String($0) : "_" }.joined()
        let t = out.trimmingCharacters(in: CharacterSet(charactersIn: "_"))
        return t.isEmpty ? "profile" : t
    }
}
