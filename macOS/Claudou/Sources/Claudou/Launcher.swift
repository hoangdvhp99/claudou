import AppKit
import Foundation

enum ClaudeError: LocalizedError {
    case notInstalled
    case launchFailed(String)

    var errorDescription: String? {
        switch self {
        case .notInstalled: return "Claude.app not found. Install Claude Desktop or set its path in Settings."
        case .launchFailed(let m): return "Could not open Claude: \(m)"
        }
    }
}

/// Everything that touches Claude Desktop. Each profile is a separate Claude
/// process started with `--user-data-dir`, so profiles run side by side and
/// Claude's original data folder is never modified.
enum ClaudeLauncher {
    static let bundleID = "com.anthropic.claudefordesktop"
    static let fm = FileManager.default

    static var appSupport: URL {
        fm.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
    }
    /// Claude's own data folder — used by the "default" profile (launched without flags).
    static var defaultDataDir: URL { appSupport.appendingPathComponent("Claude") }
    static var claudouRoot: URL { appSupport.appendingPathComponent("Claudou") }
    static var profilesDir: URL { claudouRoot.appendingPathComponent("profiles") }

    // MARK: Claude.app location (user setting)

    static let appPathKey = "claudeAppPath"
    static let defaultAppPath = "/Applications/Claude.app"

    /// Path of Claude.app: user setting, else /Applications, else Launch Services lookup.
    static var appPath: String {
        get {
            if let p = UserDefaults.standard.string(forKey: appPathKey), !p.isEmpty { return p }
            if fm.fileExists(atPath: defaultAppPath) { return defaultAppPath }
            return NSWorkspace.shared.urlForApplication(withBundleIdentifier: bundleID)?.path ?? defaultAppPath
        }
        set { UserDefaults.standard.set(newValue, forKey: appPathKey) }
    }
    static var isInstalled: Bool { fm.fileExists(atPath: appPath) }

    // MARK: Commands

    static func shellQuote(_ s: String) -> String {
        "'" + s.replacingOccurrences(of: "'", with: "'\\''") + "'"
    }

    /// `open -n -a <Claude.app> [--args --user-data-dir=<dir>]`
    static func buildCommand(dataDir: String?) -> String {
        var c = "open -n -a \(shellQuote(appPath))"
        if let dataDir { c += " --args --user-data-dir=\(shellQuote(dataDir))" }
        return c
    }

    // MARK: Process discovery

    /// Command lines of running Claude *main* processes, keyed by pid.
    /// (Helper processes live in Contents/Frameworks, so they never match.)
    static func mainProcessCommands() -> [pid_t: String] {
        let task = Process()
        task.executableURL = URL(fileURLWithPath: "/bin/ps")
        task.arguments = ["-axo", "pid=,command="]
        let pipe = Pipe()
        task.standardOutput = pipe
        task.standardError = FileHandle.nullDevice
        guard (try? task.run()) != nil else { return [:] }
        let data = pipe.fileHandleForReading.readDataToEndOfFile()
        task.waitUntilExit()

        var out: [pid_t: String] = [:]
        for line in String(decoding: data, as: UTF8.self).split(separator: "\n") {
            let t = line.drop(while: { $0 == " " })
            guard let sp = t.firstIndex(of: " "), let pid = pid_t(t[..<sp]) else { continue }
            let cmd = String(t[t.index(after: sp)...])
            if cmd.contains("/Claude.app/Contents/MacOS/Claude") { out[pid] = cmd }
        }
        return out
    }

    /// Which profile each running main process belongs to.
    static func runningPIDs(for profiles: [Profile]) -> [String: pid_t] {
        var result: [String: pid_t] = [:]
        for (pid, cmd) in mainProcessCommands() {
            let padded = cmd + " "
            if let p = profiles.first(where: { $0.id != "default" && padded.contains("--user-data-dir=\($0.dir.path) ") }) {
                result[p.id] = pid
            } else if !cmd.contains("--user-data-dir="), profiles.contains(where: { $0.id == "default" }) {
                result["default"] = pid
            }
        }
        return result
    }

    // MARK: Control

    /// Runs the profile's saved `open` command.
    static func run(command: String) async throws {
        guard isInstalled else { throw ClaudeError.notInstalled }
        let task = Process()
        task.executableURL = URL(fileURLWithPath: "/bin/zsh")
        task.arguments = ["-c", command]
        let err = Pipe()
        task.standardError = err
        task.standardOutput = FileHandle.nullDevice
        do { try task.run() } catch { throw ClaudeError.launchFailed(error.localizedDescription) }
        task.waitUntilExit()
        if task.terminationStatus != 0 {
            let msg = String(decoding: err.fileHandleForReading.readDataToEndOfFile(), as: UTF8.self)
            throw ClaudeError.launchFailed(msg.trimmingCharacters(in: .whitespacesAndNewlines))
        }
    }

    static func focus(pid: pid_t) {
        NSRunningApplication(processIdentifier: pid)?.activate()
    }

    /// Quit like ⌘Q; force-terminate if it doesn't exit within 10s.
    static func quit(pid: pid_t) async {
        guard let app = NSRunningApplication(processIdentifier: pid) else { return }
        app.terminate()
        for _ in 0..<50 {
            if app.isTerminated { return }
            try? await Task.sleep(nanoseconds: 200_000_000)
        }
        app.forceTerminate()
    }
}
