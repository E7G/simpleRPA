use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::{Arc, Mutex};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum ActionType {
    MouseClick,
    MouseDoubleClick,
    MouseRightClick,
    MouseMove,
    MouseDrag,
    MouseScroll,
    KeyPress,
    KeyType,
    Hotkey,
    Wait,
    Screenshot,
    MouseMoveRelative,
    MouseClickRelative,
    ImageClick,
    ImageWaitClick,
    ImageCheck,
    ActionGroupRef,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Action {
    pub action_type: ActionType,
    #[serde(default)]
    pub params: HashMap<String, serde_json::Value>,
    #[serde(default)]
    pub description: String,
    #[serde(default)]
    pub delay_before: f64,
    #[serde(default)]
    pub delay_after: f64,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub window_title: Option<String>,
    #[serde(default)]
    pub use_relative_coords: bool,
    #[serde(default)]
    pub background_mode: bool,
    #[serde(default)]
    pub name: String,
    #[serde(default)]
    pub condition: String,
    #[serde(default = "default_repeat_count")]
    pub repeat_count: i32,
}

fn default_repeat_count() -> i32 {
    1
}

impl Action {
    pub fn new(action_type: ActionType) -> Self {
        Self {
            action_type,
            params: HashMap::new(),
            description: String::new(),
            delay_before: 0.0,
            delay_after: 0.0,
            window_title: None,
            use_relative_coords: false,
            background_mode: false,
            name: String::new(),
            condition: String::new(),
            repeat_count: 1,
        }
    }

    pub fn generate_description(&self) -> String {
        let name_prefix = if self.name.is_empty() {
            String::new()
        } else {
            format!("[{}] ", self.name)
        };
        let delay_prefix = if self.delay_before > 0.05 {
            format!("[等待{:.2}秒] ", self.delay_before)
        } else {
            String::new()
        };
        let repeat_suffix = if self.repeat_count > 1 {
            format!(" (x{})", self.repeat_count)
        } else {
            String::new()
        };
        let bg_suffix = if self.background_mode {
            " [后台]"
        } else {
            ""
        };

        let desc = match self.action_type {
            ActionType::MouseClick => {
                let x = self.params.get("x").and_then(|v| v.as_i64()).unwrap_or(0);
                let y = self.params.get("y").and_then(|v| v.as_i64()).unwrap_or(0);
                format!("鼠标单击 ({}, {})", x, y)
            }
            ActionType::MouseDoubleClick => {
                let x = self.params.get("x").and_then(|v| v.as_i64()).unwrap_or(0);
                let y = self.params.get("y").and_then(|v| v.as_i64()).unwrap_or(0);
                format!("鼠标双击 ({}, {})", x, y)
            }
            ActionType::MouseRightClick => {
                let x = self.params.get("x").and_then(|v| v.as_i64()).unwrap_or(0);
                let y = self.params.get("y").and_then(|v| v.as_i64()).unwrap_or(0);
                format!("鼠标右键 ({}, {})", x, y)
            }
            ActionType::MouseMove => {
                let x = self.params.get("x").and_then(|v| v.as_i64()).unwrap_or(0);
                let y = self.params.get("y").and_then(|v| v.as_i64()).unwrap_or(0);
                format!("鼠标移动至 ({}, {})", x, y)
            }
            ActionType::MouseDrag => {
                let sx = self.params.get("start_x").and_then(|v| v.as_i64()).unwrap_or(0);
                let sy = self.params.get("start_y").and_then(|v| v.as_i64()).unwrap_or(0);
                let ex = self.params.get("end_x").and_then(|v| v.as_i64()).unwrap_or(0);
                let ey = self.params.get("end_y").and_then(|v| v.as_i64()).unwrap_or(0);
                format!("鼠标拖拽 ({}, {}) → ({}, {})", sx, sy, ex, ey)
            }
            ActionType::MouseScroll => {
                let clicks = self.params.get("clicks").and_then(|v| v.as_i64()).unwrap_or(0);
                format!("鼠标滚轮 {} 格", clicks)
            }
            ActionType::KeyPress => {
                let key = self.params.get("key").and_then(|v| v.as_str()).unwrap_or("");
                format!("按键: {}", key)
            }
            ActionType::KeyType => {
                let text = self.params.get("text").and_then(|v| v.as_str()).unwrap_or("");
                format!("输入文本: {}", text)
            }
            ActionType::Hotkey => {
                let keys: Vec<String> = self
                    .params
                    .get("keys")
                    .and_then(|v| v.as_array())
                    .map(|arr| {
                        arr.iter()
                            .filter_map(|k| k.as_str().map(String::from))
                            .collect()
                    })
                    .unwrap_or_default();
                format!("快捷键: {}", keys.join("+"))
            }
            ActionType::Wait => {
                let seconds = self.params.get("seconds").and_then(|v| v.as_f64()).unwrap_or(0.0);
                format!("等待 {} 秒", seconds)
            }
            ActionType::Screenshot => {
                let filename = self
                    .params
                    .get("filename")
                    .and_then(|v| v.as_str())
                    .unwrap_or("screenshot.png");
                format!("截图: {}", filename)
            }
            ActionType::MouseMoveRelative => {
                let x = self.params.get("x").and_then(|v| v.as_i64()).unwrap_or(0);
                let y = self.params.get("y").and_then(|v| v.as_i64()).unwrap_or(0);
                format!("窗口内移动至 ({}, {})", x, y)
            }
            ActionType::MouseClickRelative => {
                let x = self.params.get("x").and_then(|v| v.as_i64()).unwrap_or(0);
                let y = self.params.get("y").and_then(|v| v.as_i64()).unwrap_or(0);
                format!("窗口内点击 ({}, {})", x, y)
            }
            ActionType::ImageClick => {
                let path = self.params.get("image_path").and_then(|v| v.as_str()).unwrap_or("");
                format!("图片点击: {}", std::path::Path::new(path).file_name().and_then(|n| n.to_str()).unwrap_or(""))
            }
            ActionType::ImageWaitClick => {
                let path = self.params.get("image_path").and_then(|v| v.as_str()).unwrap_or("");
                format!("等待图片点击: {}", std::path::Path::new(path).file_name().and_then(|n| n.to_str()).unwrap_or(""))
            }
            ActionType::ImageCheck => {
                let path = self.params.get("image_path").and_then(|v| v.as_str()).unwrap_or("");
                format!("检查图片: {}", std::path::Path::new(path).file_name().and_then(|n| n.to_str()).unwrap_or(""))
            }
            ActionType::ActionGroupRef => {
                let group_name = self.params.get("group_name").and_then(|v| v.as_str()).unwrap_or("未知");
                format!("📁 动作组引用: {}", group_name)
            }
        };

        format!("{}{}{}{}", name_prefix, delay_prefix, desc, bg_suffix)
    }

    pub fn get_param_i64(&self, key: &str) -> i64 {
        self.params
            .get(key)
            .and_then(|v| v.as_i64())
            .unwrap_or(0)
    }

    pub fn get_param_f64(&self, key: &str) -> f64 {
        self.params
            .get(key)
            .and_then(|v| v.as_f64())
            .unwrap_or(0.0)
    }

    pub fn get_param_str(&self, key: &str) -> &str {
        self.params
            .get(key)
            .and_then(|v| v.as_str())
            .unwrap_or("")
    }

    pub fn get_param_bool(&self, key: &str) -> bool {
        self.params.get(key).and_then(|v| v.as_bool()).unwrap_or(false)
    }

    pub fn validate(&self) -> Result<(), String> {
        match self.action_type {
            ActionType::ImageClick | ActionType::ImageWaitClick | ActionType::ImageCheck => {
                let image_path = self.get_param_str("image_path");
                if image_path.is_empty() {
                    return Err("未设置图片路径".to_string());
                }
                if !std::path::Path::new(image_path).exists() {
                    return Err(format!("图片文件不存在: {}", image_path));
                }
            }
            ActionType::Wait => {
                let seconds = self.get_param_f64("seconds");
                if seconds < 0.0 {
                    return Err("等待时间不能为负数".to_string());
                }
            }
            ActionType::ActionGroupRef => {
                let group_name = self.get_param_str("group_name");
                if group_name.is_empty() {
                    return Err("未指定动作组名称".to_string());
                }
            }
            _ => {}
        }
        Ok(())
    }

    pub fn condition_marker(&self) -> Option<String> {
        if self.action_type == ActionType::ImageCheck {
            let image_name = std::path::Path::new(self.get_param_str("image_path"))
                .file_name()
                .and_then(|n| n.to_str())
                .unwrap_or("");
            if !image_name.is_empty() {
                let name_without_ext = std::path::Path::new(image_name)
                    .file_stem()
                    .and_then(|n| n.to_str())
                    .unwrap_or(image_name);
                let safe_name = name_without_ext
                    .replace(' ', "_")
                    .replace('-', "_");
                return Some(format!("${}", safe_name));
            }
        }
        None
    }
}

pub struct VariableManager {
    variables: Mutex<HashMap<String, serde_json::Value>>,
}

impl VariableManager {
    pub fn new() -> Self {
        Self {
            variables: Mutex::new(HashMap::new()),
        }
    }

    pub fn set(&self, name: &str, value: serde_json::Value) {
        self.variables.lock().unwrap().insert(name.to_string(), value);
    }

    pub fn get(&self, name: &str) -> Option<serde_json::Value> {
        self.variables.lock().unwrap().get(name).cloned()
    }

    pub fn has(&self, name: &str) -> bool {
        self.variables.lock().unwrap().contains_key(name)
    }

    pub fn clear(&self) {
        self.variables.lock().unwrap().clear();
    }

    pub fn get_all(&self) -> HashMap<String, serde_json::Value> {
        self.variables.lock().unwrap().clone()
    }
}

impl Default for VariableManager {
    fn default() -> Self {
        Self::new()
    }
}

pub struct ActionManager;

impl ActionManager {
    pub fn get_all_categories() -> Vec<(&'static str, Vec<&'static str>)> {
        vec![
            ("鼠标操作", vec!["鼠标单击", "鼠标双击", "鼠标右键", "鼠标移动", "鼠标拖拽", "鼠标滚轮"]),
            ("键盘操作", vec!["按键", "输入文本", "快捷键"]),
            ("控制", vec!["等待"]),
            ("窗口操作", vec!["窗口内点击", "窗口内移动"]),
            ("图像识别", vec!["图片点击", "等待图片点击", "检查图片"]),
            ("其他", vec!["截图", "动作组引用"]),
        ]
    }
}
