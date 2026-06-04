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
            let sidecar = app.shell().sidecar("sprachboot-server")?;
            let (_rx, child) = sidecar.spawn()?;
            *app.state::<Sidecar>().0.lock().unwrap() = Some(child);
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
