#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::Manager;
use tauri_plugin_shell::{process::CommandChild, ShellExt};
use std::sync::Mutex;

struct Sidecar(Mutex<Option<CommandChild>>);

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(Sidecar(Mutex::new(None)))
        .setup(|app| {
            match app.shell().sidecar("sprachboot-server").and_then(|s| s.spawn()) {
                Ok((_rx, child)) => {
                    *app.state::<Sidecar>().0.lock().unwrap() = Some(child);
                }
                Err(e) => {
                    // Sidecar failed to start (common cause: quarantine when running
                    // directly from DMG — user must install to /Applications first and
                    // run: xattr -cr /Applications/SprachBoot.app).
                    // Log and continue; the frontend shows errors for each failed API call.
                    eprintln!("[SprachBoot] backend sidecar failed to start: {e}");
                }
            }
            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::Destroyed = event {
                if let Some(child) = window.state::<Sidecar>().0.lock().unwrap().take() {
                    let _ = child.kill();
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running SprachBoot");
}
