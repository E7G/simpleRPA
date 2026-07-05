use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Config {
    #[serde(default = "default_speed")]
    pub default_speed: f64,
    #[serde(default = "default_repeat_count")]
    pub default_repeat_count: i32,
    #[serde(default = "default_true")]
    pub record_mouse_click: bool,
    #[serde(default = "default_true")]
    pub record_mouse_scroll: bool,
    #[serde(default = "default_true")]
    pub record_keyboard: bool,
    #[serde(default)]
    pub record_mouse_move: bool,
    #[serde(default = "default_min_move_distance")]
    pub min_move_distance: i32,
    #[serde(default = "default_move_sample_interval")]
    pub move_sample_interval: f64,
    #[serde(default)]
    pub auto_save: bool,
    #[serde(default)]
    pub recent_files: Vec<String>,
    #[serde(default = "default_window_geometry")]
    pub window_geometry: WindowGeometry,
    #[serde(default)]
    pub theme: String,
    #[serde(default)]
    pub language: String,
    #[serde(default)]
    pub bound_window: Option<BoundWindow>,
    #[serde(default)]
    pub open_tabs: Vec<TabData>,
    #[serde(default)]
    pub tab_files: std::collections::HashMap<String, String>,
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
    #[serde(default = "default_schedule_idle_seconds")]
    pub schedule_idle_seconds: i32,
    #[serde(default)]
    pub schedule_require_idle: bool,
    #[serde(default = "default_schedule_prompt_countdown")]
    pub schedule_prompt_countdown: i32,
    #[serde(default)]
    pub schedule_last_run_date: String,
    #[serde(default = "default_true")]
    pub minimize_to_tray: bool,
    #[serde(default)]
    pub run_window_offscreen: bool,
    #[serde(default)]
    pub run_window_hide_taskbar: bool,

    #[serde(skip)]
    config_path: Option<PathBuf>,
}

fn default_speed() -> f64 {
    1.0
}
fn default_repeat_count() -> i32 {
    1
}
fn default_true() -> bool {
    true
}
fn default_min_move_distance() -> i32 {
    10
}
fn default_move_sample_interval() -> f64 {
    0.1
}
fn default_schedule_mode() -> String {
    "idle".into()
}
fn default_schedule_time() -> String {
    "09:00".into()
}
fn default_schedule_idle_seconds() -> i32 {
    180
}
fn default_schedule_prompt_countdown() -> i32 {
    15
}

fn default_window_geometry() -> WindowGeometry {
    WindowGeometry {
        x: 100,
        y: 100,
        width: 1280,
        height: 850,
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WindowGeometry {
    pub x: i32,
    pub y: i32,
    pub width: i32,
    pub height: i32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BoundWindow {
    pub hwnd: i64,
    pub title: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TabData {
    #[serde(default)]
    pub name: String,
    #[serde(default)]
    pub actions: Vec<serde_json::Value>,
    #[serde(default)]
    pub local_action_groups: Option<serde_json::Value>,
}

impl Config {
    pub fn new() -> Self {
        Self::default()
    }

    fn get_default_config_path() -> PathBuf {
        let config_dir = dirs::home_dir()
            .unwrap_or_else(|| PathBuf::from("."))
            .join(".simpleRPA");
        let _ = fs::create_dir_all(&config_dir);
        config_dir.join("config.json")
    }

    pub fn load() -> Self {
        let path = Self::get_default_config_path();
        let mut config = if path.exists() {
            fs::read_to_string(&path)
                .ok()
                .and_then(|content| serde_json::from_str::<Config>(&content).ok())
                .unwrap_or_else(Config::default)
        } else {
            Config::default()
        };
        config.config_path = Some(path);
        config
    }

    pub fn save(&self) -> Result<(), String> {
        let path = self
            .config_path
            .clone()
            .unwrap_or_else(Self::get_default_config_path);

        let json =
            serde_json::to_string_pretty(self).map_err(|e| format!("JSON序列化失败: {}", e))?;
        fs::write(&path, json).map_err(|e| format!("写入配置文件失败: {}", e))
    }

    pub fn add_recent_file(&mut self, filepath: &str) {
        self.recent_files.retain(|f| f != filepath);
        self.recent_files.insert(0, filepath.to_string());
        self.recent_files.truncate(10);
    }

    pub fn clear_recent_files(&mut self) {
        self.recent_files.clear();
    }

    pub fn set_window_geometry(&mut self, x: i32, y: i32, width: i32, height: i32) {
        self.window_geometry = WindowGeometry {
            x,
            y,
            width,
            height,
        };
    }
}

impl Default for Config {
    fn default() -> Self {
        Self {
            default_speed: 1.0,
            default_repeat_count: 1,
            record_mouse_click: true,
            record_mouse_scroll: true,
            record_keyboard: true,
            record_mouse_move: false,
            min_move_distance: 10,
            move_sample_interval: 0.1,
            auto_save: true,
            recent_files: Vec::new(),
            window_geometry: default_window_geometry(),
            theme: "light".into(),
            language: "zh_CN".into(),
            bound_window: None,
            open_tabs: Vec::new(),
            tab_files: std::collections::HashMap::new(),
            current_tab_index: 0,
            infinite_loop: false,
            timeout_seconds: 0.0,
            last_dashboard_list: String::new(),
            schedule_enabled: false,
            schedule_mode: "idle".into(),
            schedule_time: "09:00".into(),
            schedule_idle_seconds: 180,
            schedule_require_idle: false,
            schedule_prompt_countdown: 15,
            schedule_last_run_date: String::new(),
            minimize_to_tray: true,
            run_window_offscreen: false,
            run_window_hide_taskbar: false,
            config_path: None,
        }
    }
}
