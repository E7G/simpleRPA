use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Config {
    #[serde(default = "default_speed")]
    pub default_speed: f64,
    #[serde(default = "default_repeat_count")]
    pub default_repeat_count: i32,
    #[serde(default)]
    pub record_mouse_move: bool,
    #[serde(default = "default_true")]
    pub record_mouse_click: bool,
    #[serde(default = "default_true")]
    pub record_mouse_scroll: bool,
    #[serde(default = "default_true")]
    pub record_keyboard: bool,
    #[serde(default = "default_min_distance")]
    pub min_move_distance: i32,
    #[serde(default = "default_sample_interval")]
    pub move_sample_interval: f64,
    #[serde(default)]
    pub auto_save: bool,
    #[serde(default)]
    pub recent_files: Vec<String>,
    #[serde(default = "default_geometry")]
    pub window_geometry: HashMap<String, i32>,
    #[serde(default = "default_theme")]
    pub theme: String,
    #[serde(default = "default_language")]
    pub language: String,
    #[serde(default)]
    pub bound_window: HashMap<String, serde_json::Value>,
    #[serde(default)]
    pub open_tabs: Vec<serde_json::Value>,
    #[serde(default)]
    pub tab_files: HashMap<String, String>,
    #[serde(default)]
    pub current_tab_index: i32,
    #[serde(default)]
    pub infinite_loop: bool,
    #[serde(default)]
    pub timeout_seconds: f64,
    #[serde(default)]
    pub last_dashboard_list: String,
    #[serde(default)]
    pub schedule_enabled: bool,
    #[serde(default = "default_schedule_mode")]
    pub schedule_mode: String,
    #[serde(default = "default_schedule_time")]
    pub schedule_time: String,
    #[serde(default = "default_idle_seconds")]
    pub schedule_idle_seconds: i32,
    #[serde(default)]
    pub minimize_to_tray: bool,
    #[serde(default)]
    pub run_window_offscreen: bool,
}

fn default_speed() -> f64 { 1.0 }
fn default_repeat_count() -> i32 { 1 }
fn default_true() -> bool { true }
fn default_min_distance() -> i32 { 10 }
fn default_sample_interval() -> f64 { 0.1 }
fn default_theme() -> String { "light".to_string() }
fn default_language() -> String { "zh_CN".to_string() }
fn default_schedule_mode() -> String { "idle".to_string() }
fn default_schedule_time() -> String { "09:00".to_string() }
fn default_idle_seconds() -> i32 { 180 }

fn default_geometry() -> HashMap<String, i32> {
    let mut m = HashMap::new();
    m.insert("x".to_string(), 100);
    m.insert("y".to_string(), 100);
    m.insert("width".to_string(), 1280);
    m.insert("height".to_string(), 850);
    m
}

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
            auto_save: true,
            recent_files: Vec::new(),
            window_geometry: default_geometry(),
            theme: "light".to_string(),
            language: "zh_CN".to_string(),
            bound_window: HashMap::new(),
            open_tabs: Vec::new(),
            tab_files: HashMap::new(),
            current_tab_index: 0,
            infinite_loop: false,
            timeout_seconds: 0.0,
            last_dashboard_list: String::new(),
            schedule_enabled: false,
            schedule_mode: "idle".to_string(),
            schedule_time: "09:00".to_string(),
            schedule_idle_seconds: 180,
            minimize_to_tray: true,
            run_window_offscreen: false,
        }
    }
}

impl Config {
    pub fn get_config_path() -> PathBuf {
        dirs::home_dir()
            .unwrap_or_else(|| PathBuf::from("."))
            .join(".simpleRPA")
            .join("config.json")
    }

    pub fn load() -> Self {
        let path = Self::get_config_path();
        if !path.exists() {
            return Self::default();
        }
        fs::read_to_string(&path)
            .ok()
            .and_then(|content| serde_json::from_str(&content).ok())
            .unwrap_or_default()
    }

    pub fn save(&self) -> bool {
        let path = Self::get_config_path();
        if let Some(parent) = path.parent() {
            let _ = fs::create_dir_all(parent);
        }
        serde_json::to_string_pretty(self)
            .ok()
            .and_then(|content| fs::write(&path, content).ok())
            .is_some()
    }

    pub fn add_recent_file(&mut self, filepath: &str) {
        self.recent_files.retain(|f| f != filepath);
        self.recent_files.insert(0, filepath.to_string());
        self.recent_files.truncate(10);
    }
}
