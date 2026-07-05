use std::collections::HashMap;
use std::fs;
use std::path::PathBuf;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Config {
    #[serde(default = "default_speed")]
    pub default_speed: f64,
    #[serde(default = "default_repeat")]
    pub default_repeat_count: i32,
    #[serde(default)]
    pub record_mouse_move: bool,
    #[serde(default = "default_true")]
    pub record_mouse_click: bool,
    #[serde(default = "default_true")]
    pub record_mouse_scroll: bool,
    #[serde(default = "default_true")]
    pub record_keyboard: bool,
    #[serde(default = "default_min_dist")]
    pub min_move_distance: i32,
    #[serde(default = "default_sample_interval")]
    pub move_sample_interval: f64,
    #[serde(default)]
    pub auto_save: bool,
    #[serde(default)]
    pub recent_files: Vec<String>,
    #[serde(default = "default_geometry")]
    pub window_geometry: WindowGeometry,
    #[serde(default = "default_theme")]
    pub theme: String,
    #[serde(default = "default_lang")]
    pub language: String,
    #[serde(default)]
    pub bound_window: HashMap<String, serde_json::Value>,
    #[serde(default)]
    pub open_tabs: Vec<serde_json::Value>,
    #[serde(default)]
    pub tab_files: HashMap<String, String>,
    #[serde(default)]
    pub current_tab_index: usize,
    #[serde(default)]
    pub infinite_loop: bool,
    #[serde(default)]
    pub timeout_seconds: f64,
    #[serde(default)]
    pub minimize_to_tray: bool,
    #[serde(default)]
    pub run_window_offscreen: bool,
    #[serde(default)]
    pub run_window_hide_taskbar: bool,
    #[serde(default)]
    pub last_dashboard_list: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WindowGeometry {
    pub x: i32,
    pub y: i32,
    pub width: i32,
    pub height: i32,
}

fn default_speed() -> f64 { 1.0 }
fn default_repeat() -> i32 { 1 }
fn default_true() -> bool { true }
fn default_min_dist() -> i32 { 10 }
fn default_sample_interval() -> f64 { 0.1 }
fn default_geometry() -> WindowGeometry {
    WindowGeometry { x: 100, y: 100, width: 1280, height: 850 }
}
fn default_theme() -> String { "light".into() }
fn default_lang() -> String { "zh_CN".into() }

impl Default for Config {
    fn default() -> Self {
        Self {
            default_speed: 1.0,
            default_repeat_count: 1,
            record_mouse_move: false,
            record_mouse_click: true,
            record_mouse_scroll: true,
            record_keyboard: true,
            min_move_distance: 10,
            move_sample_interval: 0.1,
            auto_save: false,
            recent_files: Vec::new(),
            window_geometry: default_geometry(),
            theme: default_theme(),
            language: default_lang(),
            bound_window: HashMap::new(),
            open_tabs: Vec::new(),
            tab_files: HashMap::new(),
            current_tab_index: 0,
            infinite_loop: false,
            timeout_seconds: 0.0,
            minimize_to_tray: true,
            run_window_offscreen: false,
            run_window_hide_taskbar: false,
            last_dashboard_list: String::new(),
        }
    }
}

impl Config {
    pub fn config_path() -> PathBuf {
        let config_dir = home_dir().join(".simpleRPA");
        let _ = fs::create_dir_all(&config_dir);
        config_dir.join("config.json")
    }

    pub fn load() -> Self {
        let path = Self::config_path();
        if !path.exists() {
            return Self::default();
        }
        match fs::read_to_string(&path) {
            Ok(content) => serde_json::from_str(&content).unwrap_or_default(),
            Err(_) => Self::default(),
        }
    }

    pub fn save(&self) -> Result<(), String> {
        let path = Self::config_path();
        let json = serde_json::to_string_pretty(self).map_err(|e| e.to_string())?;
        fs::write(path, json).map_err(|e| e.to_string())
    }

    pub fn add_recent_file(&mut self, filepath: &str) {
        self.recent_files.retain(|f| f != filepath);
        self.recent_files.insert(0, filepath.to_string());
        self.recent_files.truncate(10);
    }

    pub fn set_window_geometry(&mut self, x: i32, y: i32, width: i32, height: i32) {
        self.window_geometry = WindowGeometry { x, y, width, height };
    }
}

fn home_dir() -> PathBuf {
    std::env::var("USERPROFILE")
        .map(PathBuf::from)
        .unwrap_or_else(|_| PathBuf::from("."))
}
