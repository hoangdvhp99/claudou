import SwiftUI

@main
struct ClaudouApp: App {
    @StateObject private var store = ProfileStore()

    var body: some Scene {
        MenuBarExtra {
            MenuView()
                .environmentObject(store)
        } label: {
            MenuBarIcon()
        }
        .menuBarExtraStyle(.window)

        Window("Profile", id: "editor") {
            EditorView()
                .environmentObject(store)
        }
        .windowResizability(.contentSize)

        Window("Settings", id: "settings") {
            SettingsView()
                .environmentObject(store)
        }
        .windowResizability(.contentSize)
    }
}

/// Logo in the menu bar (falls back to an SF Symbol when run outside the .app bundle).
struct MenuBarIcon: View {
    var body: some View {
        if let url = Bundle.main.url(forResource: "menubar", withExtension: "png"),
           let img = NSImage(contentsOf: url) {
            let _ = img.size = NSSize(width: 20, height: 20)
            let _ = img.isTemplate = true  // follows menu bar light/dark
            Image(nsImage: img)
        } else {
            Image(systemName: "person.2.fill")
        }
    }
}
