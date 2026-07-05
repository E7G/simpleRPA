use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
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

impl ActionType {
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::MouseClick => "mouse_click",
            Self::MouseDoubleClick => "mouse_double_click",
            Self::MouseRightClick => "mouse_right_click",
            Self::MouseMove => "mouse_move",
            Self::MouseDrag => "mouse_drag",
            Self::MouseScroll => "mouse_scroll",
            Self::KeyPress => "key_press",
            Self::KeyType => "key_type",
            Self::Hotkey => "hotkey",
            Self::Wait => "wait",
            Self::Screenshot => "screenshot",
            Self::MouseMoveRelative => "mouse_move_relative",
            Self::MouseClickRelative => "mouse_click_relative",
            Self::ImageClick => "image_click",
            Self::ImageWaitClick => "image_wait_click",
            Self::ImageCheck => "image_check",
            Self::ActionGroupRef => "action_group_ref",
        }
    }

    pub fn from_str(s: &str) -> Option<Self> {
        match s {
            "mouse_click" => Some(Self::MouseClick),
            "mouse_double_click" => Some(Self::MouseDoubleClick),
            "mouse_right_click" => Some(Self::MouseRightClick),
            "mouse_move" => Some(Self::MouseMove),
            "mouse_drag" => Some(Self::MouseDrag),
            "mouse_scroll" => Some(Self::MouseScroll),
            "key_press" => Some(Self::KeyPress),
            "key_type" => Some(Self::KeyType),
            "hotkey" => Some(Self::Hotkey),
            "wait" => Some(Self::Wait),
            "screenshot" => Some(Self::Screenshot),
            "mouse_move_relative" => Some(Self::MouseMoveRelative),
            "mouse_click_relative" => Some(Self::MouseClickRelative),
            "image_click" => Some(Self::ImageClick),
            "image_wait_click" => Some(Self::ImageWaitClick),
            "image_check" => Some(Self::ImageCheck),
            "action_group_ref" => Some(Self::ActionGroupRef),
            _ => None,
        }
    }

    pub fn category(&self) -> &'static str {
        match self {
            Self::MouseClick
            | Self::MouseDoubleClick
            | Self::MouseRightClick
            | Self::MouseMove
            | Self::MouseDrag
            | Self::MouseScroll => "mouse",
            Self::KeyPress | Self::KeyType | Self::Hotkey => "keyboard",
            Self::Wait => "control",
            Self::Screenshot => "other",
            Self::MouseMoveRelative | Self::MouseClickRelative => "window",
            Self::ImageClick | Self::ImageWaitClick | Self::ImageCheck => "image",
            Self::ActionGroupRef => "group",
        }
    }

    pub fn display_name(&self) -> &'static str {
        match self {
            Self::MouseClick => "鼠标单击",
            Self::MouseDoubleClick => "鼠标双击",
            Self::MouseRightClick => "鼠标右键",
            Self::MouseMove => "鼠标移动",
            Self::MouseDrag => "鼠标拖拽",
            Self::MouseScroll => "鼠标滚轮",
            Self::KeyPress => "按键",
            Self::KeyType => "输入文本",
            Self::Hotkey => "快捷键",
            Self::Wait => "等待",
            Self::Screenshot => "截图",
            Self::MouseMoveRelative => "窗口内移动",
            Self::MouseClickRelative => "窗口内点击",
            Self::ImageClick => "图片点击",
            Self::ImageWaitClick => "等待图片点击",
            Self::ImageCheck => "检查图片",
            Self::ActionGroupRef => "动作组引用",
        }
    }
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
        let description = action_type.display_name().to_string();
        Self {
            action_type,
            params: HashMap::new(),
            description,
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

    pub fn param_i32(&self, key: &str) -> i32 {
        self.params.get(key).and_then(|v| v.as_i64()).unwrap_or(0) as i32
    }

    pub fn param_f64(&self, key: &str) -> f64 {
        self.params.get(key).and_then(|v| v.as_f64()).unwrap_or(0.0)
    }

    pub fn param_str(&self, key: &str) -> String {
        self.params
            .get(key)
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string()
    }

    pub fn param_str_slice(&self, key: &str) -> Vec<String> {
        self.params
            .get(key)
            .and_then(|v| v.as_array())
            .map(|arr| {
                arr.iter()
                    .filter_map(|v| v.as_str().map(|s| s.to_string()))
                    .collect()
            })
            .unwrap_or_default()
    }

    pub fn condition_marker(&self) -> String {
        if self.action_type == ActionType::ImageCheck {
            let image_name = self.param_str("image_path");
            if !image_name.is_empty() {
                let name = std::path::Path::new(&image_name)
                    .file_stem()
                    .and_then(|s| s.to_str())
                    .unwrap_or("");
                let safe_name = name.replace(' ', "_").replace('-', "_");
                return format!("${}", safe_name);
            }
        }
        String::new()
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
            ActionType::MouseClick => format!(
                "鼠标单击 ({}, {})",
                self.param_i32("x"),
                self.param_i32("y")
            ),
            ActionType::MouseDoubleClick => format!(
                "鼠标双击 ({}, {})",
                self.param_i32("x"),
                self.param_i32("y")
            ),
            ActionType::MouseRightClick => format!(
                "鼠标右键 ({}, {})",
                self.param_i32("x"),
                self.param_i32("y")
            ),
            ActionType::MouseMove => format!(
                "鼠标移动至 ({}, {})",
                self.param_i32("x"),
                self.param_i32("y")
            ),
            ActionType::MouseDrag => format!(
                "鼠标拖拽 ({}, {}) -> ({}, {})",
                self.param_i32("start_x"),
                self.param_i32("start_y"),
                self.param_i32("end_x"),
                self.param_i32("end_y")
            ),
            ActionType::MouseScroll => format!("鼠标滚轮 {} 格", self.param_i32("clicks")),
            ActionType::KeyPress => format!("按键: {}", self.param_str("key")),
            ActionType::KeyType => format!("输入文本: {}", self.param_str("text")),
            ActionType::Hotkey => {
                let keys = self.param_str_slice("keys");
                format!("快捷键: {}", keys.join("+"))
            }
            ActionType::Wait => format!("等待 {} 秒", self.param_f64("seconds")),
            ActionType::Screenshot => format!(
                "截图: {}",
                self.param_str("filename").if_empty("screenshot.png")
            ),
            ActionType::MouseMoveRelative => format!(
                "窗口内移动至 ({}, {})",
                self.param_i32("x"),
                self.param_i32("y")
            ),
            ActionType::MouseClickRelative => format!(
                "窗口内点击 ({}, {})",
                self.param_i32("x"),
                self.param_i32("y")
            ),
            ActionType::ImageClick => {
                let path = self.param_str("image_path");
                let name = std::path::Path::new(&path)
                    .file_name()
                    .and_then(|s| s.to_str())
                    .unwrap_or("");
                format!("图片点击: {}", name)
            }
            ActionType::ImageWaitClick => {
                let path = self.param_str("image_path");
                let name = std::path::Path::new(&path)
                    .file_name()
                    .and_then(|s| s.to_str())
                    .unwrap_or("");
                format!("等待图片点击: {}", name)
            }
            ActionType::ImageCheck => {
                let path = self.param_str("image_path");
                let name = std::path::Path::new(&path)
                    .file_name()
                    .and_then(|s| s.to_str())
                    .unwrap_or("");
                format!("检查图片: {}", name)
            }
            ActionType::ActionGroupRef => {
                format!(
                    "动作组引用: {}",
                    self.param_str("group_name").if_empty("未知")
                )
            }
        };

        format!(
            "{}{}{}{}{}",
            name_prefix, delay_prefix, desc, bg_suffix, repeat_suffix
        )
    }

    pub fn check_condition(&self, var_manager: &VariableManager) -> bool {
        if self.condition.is_empty() {
            return true;
        }

        let condition = self.condition.trim();

        if let Some(pos) = condition.find("==") {
            let left = condition[..pos].trim();
            let right = condition[pos + 2..].trim();
            let left_val = if left.starts_with('$') {
                var_manager
                    .get(&left[1..])
                    .map(|v| v.to_string())
                    .unwrap_or_default()
            } else {
                left.to_string()
            };
            let right_val = if right.starts_with('$') {
                var_manager
                    .get(&right[1..])
                    .map(|v| v.to_string())
                    .unwrap_or_default()
            } else {
                right.to_string()
            };
            return left_val == right_val;
        }

        if let Some(pos) = condition.find("!=") {
            let left = condition[..pos].trim();
            let right = condition[pos + 2..].trim();
            let left_val = if left.starts_with('$') {
                var_manager
                    .get(&left[1..])
                    .map(|v| v.to_string())
                    .unwrap_or_default()
            } else {
                left.to_string()
            };
            let right_val = if right.starts_with('$') {
                var_manager
                    .get(&right[1..])
                    .map(|v| v.to_string())
                    .unwrap_or_default()
            } else {
                right.to_string()
            };
            return left_val != right_val;
        }

        if condition.starts_with('$') {
            let var_name = &condition[1..];
            return var_manager
                .get(var_name)
                .map(|v| v.parse::<bool>().unwrap_or(false))
                .unwrap_or(false);
        }

        true
    }

    pub fn to_dict(&self) -> serde_json::Value {
        let data = serde_json::json!({
            "action_type": self.action_type.as_str(),
            "params": self.params,
            "description": self.description,
            "delay_before": self.delay_before,
            "delay_after": self.delay_after,
            "window_title": self.window_title,
            "use_relative_coords": self.use_relative_coords,
            "background_mode": self.background_mode,
            "name": self.name,
            "condition": self.condition,
            "repeat_count": self.repeat_count,
        });
        data
    }

    pub fn from_dict(data: &serde_json::Value) -> Option<Self> {
        let action_type_str = data.get("action_type")?.as_str()?;
        let action_type = ActionType::from_str(action_type_str)?;

        let params = data
            .get("params")
            .and_then(|v| v.as_object())
            .map(|obj| {
                obj.iter()
                    .map(|(k, v)| (k.clone(), v.clone()))
                    .collect::<HashMap<String, serde_json::Value>>()
            })
            .unwrap_or_default();

        Some(Self {
            action_type,
            params,
            description: data
                .get("description")
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .to_string(),
            delay_before: data
                .get("delay_before")
                .and_then(|v| v.as_f64())
                .unwrap_or(0.0),
            delay_after: data
                .get("delay_after")
                .and_then(|v| v.as_f64())
                .unwrap_or(0.0),
            window_title: data
                .get("window_title")
                .and_then(|v| v.as_str())
                .map(|s| s.to_string()),
            use_relative_coords: data
                .get("use_relative_coords")
                .and_then(|v| v.as_bool())
                .unwrap_or(false),
            background_mode: data
                .get("background_mode")
                .and_then(|v| v.as_bool())
                .unwrap_or(false),
            name: data
                .get("name")
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .to_string(),
            condition: data
                .get("condition")
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .to_string(),
            repeat_count: data
                .get("repeat_count")
                .and_then(|v| v.as_i64())
                .unwrap_or(1) as i32,
        })
    }

    pub fn validate(&self) -> Result<(), String> {
        match self.action_type {
            ActionType::ImageClick | ActionType::ImageWaitClick | ActionType::ImageCheck => {
                let image_path = self.param_str("image_path");
                if image_path.is_empty() {
                    return Err("未设置图片路径".into());
                }
                if !std::path::Path::new(&image_path).exists() {
                    return Err(format!("图片文件不存在: {}", image_path));
                }
            }
            ActionType::Wait => {
                let seconds = self.param_f64("seconds");
                if seconds < 0.0 {
                    return Err("等待时间不能为负数".into());
                }
            }
            ActionType::ActionGroupRef => {
                let group_name = self.param_str("group_name");
                if group_name.is_empty() {
                    return Err("未指定动作组名称".into());
                }
            }
            _ => {}
        }
        Ok(())
    }
}

trait StrExt {
    fn if_empty(self, fallback: &str) -> String;
}

impl StrExt for String {
    fn if_empty(self, fallback: &str) -> String {
        if self.is_empty() {
            fallback.to_string()
        } else {
            self
        }
    }
}

#[derive(Debug, Clone, Default)]
pub struct VariableManager {
    variables: HashMap<String, String>,
}

impl VariableManager {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn set(&mut self, name: &str, value: &str) {
        self.variables.insert(name.to_string(), value.to_string());
    }

    pub fn get(&self, name: &str) -> Option<&str> {
        self.variables.get(name).map(|s| s.as_str())
    }

    pub fn has(&self, name: &str) -> bool {
        self.variables.contains_key(name)
    }

    pub fn clear(&mut self) {
        self.variables.clear();
    }

    pub fn get_all(&self) -> &HashMap<String, String> {
        &self.variables
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ActionDefinition {
    pub name: String,
    pub category: String,
    pub params: Vec<ActionParamDef>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ActionParamDef {
    pub name: String,
    pub param_type: String,
    pub default: serde_json::Value,
    pub description: String,
}

pub struct ActionManager;

impl ActionManager {
    pub fn get_all_categories() -> Vec<String> {
        vec![
            "mouse".into(),
            "keyboard".into(),
            "control".into(),
            "other".into(),
            "window".into(),
            "image".into(),
            "group".into(),
        ]
    }

    pub fn get_actions_for_category(category: &str) -> Vec<ActionType> {
        match category {
            "mouse" => vec![
                ActionType::MouseClick,
                ActionType::MouseDoubleClick,
                ActionType::MouseRightClick,
                ActionType::MouseMove,
                ActionType::MouseDrag,
                ActionType::MouseScroll,
            ],
            "keyboard" => vec![
                ActionType::KeyPress,
                ActionType::KeyType,
                ActionType::Hotkey,
            ],
            "control" => vec![ActionType::Wait],
            "other" => vec![ActionType::Screenshot],
            "window" => vec![
                ActionType::MouseMoveRelative,
                ActionType::MouseClickRelative,
            ],
            "image" => vec![
                ActionType::ImageClick,
                ActionType::ImageWaitClick,
                ActionType::ImageCheck,
            ],
            "group" => vec![ActionType::ActionGroupRef],
            _ => vec![],
        }
    }

    pub fn get_definition(action_type: &ActionType) -> ActionDefinition {
        let (name, category, params) = match action_type {
            ActionType::MouseClick => (
                "鼠标单击".into(),
                "mouse".into(),
                vec![
                    ActionParamDef {
                        name: "x".into(),
                        param_type: "int".into(),
                        default: serde_json::json!(0),
                        description: "X坐标".into(),
                    },
                    ActionParamDef {
                        name: "y".into(),
                        param_type: "int".into(),
                        default: serde_json::json!(0),
                        description: "Y坐标".into(),
                    },
                    ActionParamDef {
                        name: "button".into(),
                        param_type: "string".into(),
                        default: serde_json::json!("left"),
                        description: "鼠标按钮".into(),
                    },
                    ActionParamDef {
                        name: "clicks".into(),
                        param_type: "int".into(),
                        default: serde_json::json!(1),
                        description: "点击次数".into(),
                    },
                ],
            ),
            ActionType::MouseDoubleClick => (
                "鼠标双击".into(),
                "mouse".into(),
                vec![
                    ActionParamDef {
                        name: "x".into(),
                        param_type: "int".into(),
                        default: serde_json::json!(0),
                        description: "X坐标".into(),
                    },
                    ActionParamDef {
                        name: "y".into(),
                        param_type: "int".into(),
                        default: serde_json::json!(0),
                        description: "Y坐标".into(),
                    },
                ],
            ),
            ActionType::MouseRightClick => (
                "鼠标右键".into(),
                "mouse".into(),
                vec![
                    ActionParamDef {
                        name: "x".into(),
                        param_type: "int".into(),
                        default: serde_json::json!(0),
                        description: "X坐标".into(),
                    },
                    ActionParamDef {
                        name: "y".into(),
                        param_type: "int".into(),
                        default: serde_json::json!(0),
                        description: "Y坐标".into(),
                    },
                ],
            ),
            ActionType::MouseMove => (
                "鼠标移动".into(),
                "mouse".into(),
                vec![
                    ActionParamDef {
                        name: "x".into(),
                        param_type: "int".into(),
                        default: serde_json::json!(0),
                        description: "X坐标".into(),
                    },
                    ActionParamDef {
                        name: "y".into(),
                        param_type: "int".into(),
                        default: serde_json::json!(0),
                        description: "Y坐标".into(),
                    },
                    ActionParamDef {
                        name: "duration".into(),
                        param_type: "float".into(),
                        default: serde_json::json!(0.0),
                        description: "移动时间(秒)".into(),
                    },
                ],
            ),
            ActionType::MouseDrag => (
                "鼠标拖拽".into(),
                "mouse".into(),
                vec![
                    ActionParamDef {
                        name: "start_x".into(),
                        param_type: "int".into(),
                        default: serde_json::json!(0),
                        description: "起始X坐标".into(),
                    },
                    ActionParamDef {
                        name: "start_y".into(),
                        param_type: "int".into(),
                        default: serde_json::json!(0),
                        description: "起始Y坐标".into(),
                    },
                    ActionParamDef {
                        name: "end_x".into(),
                        param_type: "int".into(),
                        default: serde_json::json!(0),
                        description: "结束X坐标".into(),
                    },
                    ActionParamDef {
                        name: "end_y".into(),
                        param_type: "int".into(),
                        default: serde_json::json!(0),
                        description: "结束Y坐标".into(),
                    },
                    ActionParamDef {
                        name: "duration".into(),
                        param_type: "float".into(),
                        default: serde_json::json!(0.5),
                        description: "拖拽时间(秒)".into(),
                    },
                ],
            ),
            ActionType::MouseScroll => (
                "鼠标滚轮".into(),
                "mouse".into(),
                vec![
                    ActionParamDef {
                        name: "clicks".into(),
                        param_type: "int".into(),
                        default: serde_json::json!(0),
                        description: "滚动量".into(),
                    },
                    ActionParamDef {
                        name: "x".into(),
                        param_type: "int".into(),
                        default: serde_json::json!(0),
                        description: "X坐标".into(),
                    },
                    ActionParamDef {
                        name: "y".into(),
                        param_type: "int".into(),
                        default: serde_json::json!(0),
                        description: "Y坐标".into(),
                    },
                ],
            ),
            ActionType::KeyPress => (
                "按键".into(),
                "keyboard".into(),
                vec![ActionParamDef {
                    name: "key".into(),
                    param_type: "string".into(),
                    default: serde_json::json!(""),
                    description: "按键名称".into(),
                }],
            ),
            ActionType::KeyType => (
                "输入文本".into(),
                "keyboard".into(),
                vec![
                    ActionParamDef {
                        name: "text".into(),
                        param_type: "string".into(),
                        default: serde_json::json!(""),
                        description: "要输入的文本".into(),
                    },
                    ActionParamDef {
                        name: "interval".into(),
                        param_type: "float".into(),
                        default: serde_json::json!(0.0),
                        description: "按键间隔(秒)".into(),
                    },
                ],
            ),
            ActionType::Hotkey => (
                "快捷键".into(),
                "keyboard".into(),
                vec![ActionParamDef {
                    name: "keys".into(),
                    param_type: "list".into(),
                    default: serde_json::json!([]),
                    description: "按键列表".into(),
                }],
            ),
            ActionType::Wait => (
                "等待".into(),
                "control".into(),
                vec![ActionParamDef {
                    name: "seconds".into(),
                    param_type: "float".into(),
                    default: serde_json::json!(1.0),
                    description: "等待时间(秒)".into(),
                }],
            ),
            ActionType::Screenshot => (
                "截图".into(),
                "other".into(),
                vec![
                    ActionParamDef {
                        name: "filename".into(),
                        param_type: "string".into(),
                        default: serde_json::json!("screenshot.png"),
                        description: "文件名".into(),
                    },
                    ActionParamDef {
                        name: "region".into(),
                        param_type: "tuple".into(),
                        default: serde_json::json!(null),
                        description: "截图区域".into(),
                    },
                ],
            ),
            ActionType::MouseMoveRelative | ActionType::MouseClickRelative => (
                "窗口内操作".into(),
                "window".into(),
                vec![
                    ActionParamDef {
                        name: "x".into(),
                        param_type: "int".into(),
                        default: serde_json::json!(0),
                        description: "相对X坐标".into(),
                    },
                    ActionParamDef {
                        name: "y".into(),
                        param_type: "int".into(),
                        default: serde_json::json!(0),
                        description: "相对Y坐标".into(),
                    },
                ],
            ),
            ActionType::ImageClick => (
                "图片点击".into(),
                "image".into(),
                vec![
                    ActionParamDef {
                        name: "image_path".into(),
                        param_type: "string".into(),
                        default: serde_json::json!(""),
                        description: "图片路径".into(),
                    },
                    ActionParamDef {
                        name: "confidence".into(),
                        param_type: "float".into(),
                        default: serde_json::json!(0.9),
                        description: "置信度".into(),
                    },
                ],
            ),
            ActionType::ImageWaitClick => (
                "等待图片点击".into(),
                "image".into(),
                vec![
                    ActionParamDef {
                        name: "image_path".into(),
                        param_type: "string".into(),
                        default: serde_json::json!(""),
                        description: "图片路径".into(),
                    },
                    ActionParamDef {
                        name: "confidence".into(),
                        param_type: "float".into(),
                        default: serde_json::json!(0.9),
                        description: "置信度".into(),
                    },
                    ActionParamDef {
                        name: "timeout".into(),
                        param_type: "float".into(),
                        default: serde_json::json!(10.0),
                        description: "超时(秒)".into(),
                    },
                ],
            ),
            ActionType::ImageCheck => (
                "检查图片".into(),
                "image".into(),
                vec![
                    ActionParamDef {
                        name: "image_path".into(),
                        param_type: "string".into(),
                        default: serde_json::json!(""),
                        description: "图片路径".into(),
                    },
                    ActionParamDef {
                        name: "confidence".into(),
                        param_type: "float".into(),
                        default: serde_json::json!(0.9),
                        description: "置信度".into(),
                    },
                ],
            ),
            ActionType::ActionGroupRef => (
                "动作组引用".into(),
                "group".into(),
                vec![ActionParamDef {
                    name: "group_name".into(),
                    param_type: "string".into(),
                    default: serde_json::json!(""),
                    description: "动作组名称".into(),
                }],
            ),
        };

        ActionDefinition {
            name,
            category,
            params,
        }
    }
}

pub fn can_actions_run_offscreen(
    actions: &[Action],
    local_group_manager: Option<&crate::action_group::LocalActionGroupManager>,
) -> bool {
    actions.iter().all(|a| {
        _can_action_run_offscreen(
            a,
            local_group_manager,
            false,
            &mut std::collections::HashSet::new(),
        )
    })
}

fn _can_action_run_offscreen(
    action: &Action,
    local_group_manager: Option<&crate::action_group::LocalActionGroupManager>,
    inherited_background: bool,
    visited_groups: &mut std::collections::HashSet<String>,
) -> bool {
    let effective_background = action.background_mode || inherited_background;

    match action.action_type {
        ActionType::Wait => true,
        ActionType::MouseMoveRelative
        | ActionType::MouseClickRelative
        | ActionType::ImageClick
        | ActionType::ImageWaitClick
        | ActionType::ImageCheck
        | ActionType::Screenshot => effective_background,
        ActionType::ActionGroupRef => {
            let group_name = action.param_str("group_name");
            if group_name.is_empty() {
                return false;
            }
            if visited_groups.contains(&group_name) {
                return false;
            }
            visited_groups.insert(group_name.clone());

            if let Some(mgr) = local_group_manager {
                if let Some(group) = mgr.get_group(&group_name) {
                    let next_bg = action.background_mode || inherited_background;
                    return group.actions.iter().all(|sub| {
                        _can_action_run_offscreen(sub, local_group_manager, next_bg, visited_groups)
                    });
                }
            }
            false
        }
        _ => false,
    }
}
