use std::collections::HashMap;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
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
    pub fn display_name(&self) -> &str {
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

    pub fn category(&self) -> &str {
        match self {
            Self::MouseClick | Self::MouseDoubleClick | Self::MouseRightClick
            | Self::MouseMove | Self::MouseDrag | Self::MouseScroll => "鼠标操作",
            Self::KeyPress | Self::KeyType | Self::Hotkey => "键盘操作",
            Self::Wait => "控制",
            Self::MouseMoveRelative | Self::MouseClickRelative => "窗口操作",
            Self::ImageClick | Self::ImageWaitClick | Self::ImageCheck => "图像操作",
            Self::Screenshot => "其他",
            Self::ActionGroupRef => "其他",
        }
    }

    pub fn can_run_offscreen(&self) -> bool {
        matches!(
            self,
            Self::MouseMoveRelative
                | Self::MouseClickRelative
                | Self::ImageClick
                | Self::ImageWaitClick
                | Self::ImageCheck
                | Self::Screenshot
        )
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
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub group_name: Option<String>,
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
            group_name: None,
        }
    }

    pub fn generate_description(&self) -> String {
        let mut parts = Vec::new();

        if !self.name.is_empty() {
            parts.push(format!("[{}]", self.name));
        }
        if self.delay_before > 0.05 {
            parts.push(format!("[等待{:.2}秒]", self.delay_before));
        }

        let main_desc = match self.action_type {
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
                let keys: Vec<&str> = self.params.get("keys")
                    .and_then(|v| v.as_array())
                    .map(|arr| arr.iter().filter_map(|k| k.as_str()).collect())
                    .unwrap_or_default();
                format!("快捷键: {}", keys.join("+"))
            }
            ActionType::Wait => {
                let secs = self.params.get("seconds").and_then(|v| v.as_f64()).unwrap_or(0.0);
                format!("等待 {} 秒", secs)
            }
            ActionType::Screenshot => {
                let fname = self.params.get("filename").and_then(|v| v.as_str()).unwrap_or("screenshot.png");
                format!("截图: {}", fname)
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
            ActionType::ImageClick | ActionType::ImageWaitClick | ActionType::ImageCheck => {
                let path = self.params.get("image_path").and_then(|v| v.as_str()).unwrap_or("");
                let name = std::path::Path::new(path)
                    .file_name()
                    .and_then(|n| n.to_str())
                    .unwrap_or("");
                match self.action_type {
                    ActionType::ImageClick => format!("图片点击: {}", name),
                    ActionType::ImageWaitClick => format!("等待图片点击: {}", name),
                    ActionType::ImageCheck => format!("检查图片: {}", name),
                    _ => unreachable!(),
                }
            }
            ActionType::ActionGroupRef => {
                let gn = self.params.get("group_name").and_then(|v| v.as_str()).unwrap_or("未知");
                format!("动作组引用: {}", gn)
            }
        };
        parts.push(main_desc);

        if self.background_mode {
            parts.push(" [后台]".to_string());
        }
        if self.repeat_count > 1 {
            parts.push(format!(" (x{})", self.repeat_count));
        }

        parts.join("")
    }

    pub fn condition_marker(&self) -> Option<String> {
        if self.action_type == ActionType::ImageCheck {
            let image_path = self.params.get("image_path").and_then(|v| v.as_str())?;
            let image_name = std::path::Path::new(image_path)
                .file_stem()
                .and_then(|n| n.to_str())?;
            let safe_name = image_name.replace(' ', "_").replace('-', "_");
            Some(format!("${}", safe_name))
        } else {
            None
        }
    }

    pub fn check_condition(&self, variables: &HashMap<String, serde_json::Value>) -> bool {
        if self.condition.is_empty() {
            return true;
        }

        let condition = self.condition.trim();

        if let Some(pos) = condition.find("==") {
            let left_str = condition[..pos].trim();
            let right_str = condition[pos + 2..].trim();
            let left_val = resolve_var_value(left_str, variables);
            let right_val = resolve_var_value(right_str, variables);
            return left_val == right_val;
        }

        if let Some(pos) = condition.find("!=") {
            let left_str = condition[..pos].trim();
            let right_str = condition[pos + 2..].trim();
            let left_val = resolve_var_value(left_str, variables);
            let right_val = resolve_var_value(right_str, variables);
            return left_val != right_val;
        }

        if condition.starts_with('$') {
            let var_name = &condition[1..];
            return variables
                .get(var_name)
                .map(|v| v.as_bool().unwrap_or(false))
                .unwrap_or(false);
        }

        true
    }

    pub fn validate(&self) -> Result<(), String> {
        match self.action_type {
            ActionType::ImageClick | ActionType::ImageWaitClick | ActionType::ImageCheck => {
                let image_path = self.params.get("image_path").and_then(|v| v.as_str()).unwrap_or("");
                if image_path.is_empty() {
                    return Err("未设置图片路径".to_string());
                }
                if !std::path::Path::new(image_path).exists() {
                    return Err(format!("图片文件不存在: {}", image_path));
                }
            }
            ActionType::Wait => {
                let seconds = self.params.get("seconds").and_then(|v| v.as_f64()).unwrap_or(0.0);
                if seconds < 0.0 {
                    return Err("等待时间不能为负数".to_string());
                }
            }
            ActionType::ActionGroupRef => {
                let group_name = self.params.get("group_name").and_then(|v| v.as_str()).unwrap_or("");
                if group_name.is_empty() {
                    return Err("未指定动作组名称".to_string());
                }
            }
            _ => {}
        }
        Ok(())
    }

    pub fn to_dict(&self) -> serde_json::Value {
        serde_json::to_value(self).unwrap_or(serde_json::Value::Null)
    }

    pub fn from_dict(data: &serde_json::Value) -> Result<Self, String> {
        serde_json::from_value(data.clone()).map_err(|e| format!("解析动作失败: {}", e))
    }
}

fn resolve_var_value(s: &str, variables: &HashMap<String, serde_json::Value>) -> String {
    if s.starts_with('$') {
        let var_name = &s[1..];
        variables
            .get(var_name)
            .map(|v| match v {
                serde_json::Value::String(s) => s.clone(),
                other => other.to_string(),
            })
            .unwrap_or_default()
    } else {
        s.to_string()
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct ActionDef {
    pub name: String,
    pub category: String,
    pub params: Vec<ParamDef>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ParamDef {
    pub name: String,
    pub param_type: String,
    pub default: serde_json::Value,
    pub description: String,
}

pub struct ActionManager;

impl ActionManager {
    pub fn get_definitions() -> HashMap<ActionType, ActionDef> {
        let mut defs = HashMap::new();

        defs.insert(
            ActionType::MouseClick,
            ActionDef {
                name: "鼠标单击".into(),
                category: "鼠标操作".into(),
                params: vec![
                    ParamDef { name: "x".into(), param_type: "int".into(), default: 0.into(), description: "X坐标".into() },
                    ParamDef { name: "y".into(), param_type: "int".into(), default: 0.into(), description: "Y坐标".into() },
                    ParamDef { name: "button".into(), param_type: "str".into(), default: "left".into(), description: "鼠标按钮".into() },
                    ParamDef { name: "clicks".into(), param_type: "int".into(), default: 1.into(), description: "点击次数".into() },
                ],
            },
        );

        defs.insert(
            ActionType::MouseDoubleClick,
            ActionDef {
                name: "鼠标双击".into(),
                category: "鼠标操作".into(),
                params: vec![
                    ParamDef { name: "x".into(), param_type: "int".into(), default: 0.into(), description: "X坐标".into() },
                    ParamDef { name: "y".into(), param_type: "int".into(), default: 0.into(), description: "Y坐标".into() },
                ],
            },
        );

        defs.insert(
            ActionType::MouseRightClick,
            ActionDef {
                name: "鼠标右键".into(),
                category: "鼠标操作".into(),
                params: vec![
                    ParamDef { name: "x".into(), param_type: "int".into(), default: 0.into(), description: "X坐标".into() },
                    ParamDef { name: "y".into(), param_type: "int".into(), default: 0.into(), description: "Y坐标".into() },
                ],
            },
        );

        defs.insert(
            ActionType::MouseMove,
            ActionDef {
                name: "鼠标移动".into(),
                category: "鼠标操作".into(),
                params: vec![
                    ParamDef { name: "x".into(), param_type: "int".into(), default: 0.into(), description: "X坐标".into() },
                    ParamDef { name: "y".into(), param_type: "int".into(), default: 0.into(), description: "Y坐标".into() },
                    ParamDef { name: "duration".into(), param_type: "float".into(), default: 0.0.into(), description: "移动时间(秒)".into() },
                ],
            },
        );

        defs.insert(
            ActionType::MouseDrag,
            ActionDef {
                name: "鼠标拖拽".into(),
                category: "鼠标操作".into(),
                params: vec![
                    ParamDef { name: "start_x".into(), param_type: "int".into(), default: 0.into(), description: "起始X坐标".into() },
                    ParamDef { name: "start_y".into(), param_type: "int".into(), default: 0.into(), description: "起始Y坐标".into() },
                    ParamDef { name: "end_x".into(), param_type: "int".into(), default: 0.into(), description: "结束X坐标".into() },
                    ParamDef { name: "end_y".into(), param_type: "int".into(), default: 0.into(), description: "结束Y坐标".into() },
                    ParamDef { name: "duration".into(), param_type: "float".into(), default: 0.5.into(), description: "拖拽时间(秒)".into() },
                ],
            },
        );

        defs.insert(
            ActionType::MouseScroll,
            ActionDef {
                name: "鼠标滚轮".into(),
                category: "鼠标操作".into(),
                params: vec![
                    ParamDef { name: "clicks".into(), param_type: "int".into(), default: 0.into(), description: "滚动量(正数向上,负数向下)".into() },
                    ParamDef { name: "x".into(), param_type: "int".into(), default: 0.into(), description: "X坐标".into() },
                    ParamDef { name: "y".into(), param_type: "int".into(), default: 0.into(), description: "Y坐标".into() },
                ],
            },
        );

        defs.insert(
            ActionType::KeyPress,
            ActionDef {
                name: "按键".into(),
                category: "键盘操作".into(),
                params: vec![
                    ParamDef { name: "key".into(), param_type: "str".into(), default: "".into(), description: "按键名称".into() },
                ],
            },
        );

        defs.insert(
            ActionType::KeyType,
            ActionDef {
                name: "输入文本".into(),
                category: "键盘操作".into(),
                params: vec![
                    ParamDef { name: "text".into(), param_type: "str".into(), default: "".into(), description: "要输入的文本".into() },
                    ParamDef { name: "interval".into(), param_type: "float".into(), default: 0.0.into(), description: "按键间隔(秒)".into() },
                ],
            },
        );

        defs.insert(
            ActionType::Hotkey,
            ActionDef {
                name: "快捷键".into(),
                category: "键盘操作".into(),
                params: vec![
                    ParamDef { name: "keys".into(), param_type: "list".into(), default: serde_json::json!([]), description: "按键列表".into() },
                ],
            },
        );

        defs.insert(
            ActionType::Wait,
            ActionDef {
                name: "等待".into(),
                category: "控制".into(),
                params: vec![
                    ParamDef { name: "seconds".into(), param_type: "float".into(), default: 1.0.into(), description: "等待时间(秒)".into() },
                ],
            },
        );

        defs.insert(
            ActionType::Screenshot,
            ActionDef {
                name: "截图".into(),
                category: "其他".into(),
                params: vec![
                    ParamDef { name: "filename".into(), param_type: "str".into(), default: "screenshot.png".into(), description: "文件名".into() },
                ],
            },
        );

        defs.insert(
            ActionType::MouseClickRelative,
            ActionDef {
                name: "窗口内点击".into(),
                category: "窗口操作".into(),
                params: vec![
                    ParamDef { name: "x".into(), param_type: "int".into(), default: 0.into(), description: "相对X坐标".into() },
                    ParamDef { name: "y".into(), param_type: "int".into(), default: 0.into(), description: "相对Y坐标".into() },
                    ParamDef { name: "button".into(), param_type: "str".into(), default: "left".into(), description: "鼠标按钮".into() },
                ],
            },
        );

        defs.insert(
            ActionType::MouseMoveRelative,
            ActionDef {
                name: "窗口内移动".into(),
                category: "窗口操作".into(),
                params: vec![
                    ParamDef { name: "x".into(), param_type: "int".into(), default: 0.into(), description: "相对X坐标".into() },
                    ParamDef { name: "y".into(), param_type: "int".into(), default: 0.into(), description: "相对Y坐标".into() },
                    ParamDef { name: "duration".into(), param_type: "float".into(), default: 0.0.into(), description: "移动时间(秒)".into() },
                ],
            },
        );

        defs.insert(
            ActionType::ImageClick,
            ActionDef {
                name: "图片点击".into(),
                category: "图像操作".into(),
                params: vec![
                    ParamDef { name: "image_path".into(), param_type: "str".into(), default: "".into(), description: "图片路径".into() },
                    ParamDef { name: "confidence".into(), param_type: "float".into(), default: 0.9.into(), description: "置信度".into() },
                ],
            },
        );

        defs.insert(
            ActionType::ImageWaitClick,
            ActionDef {
                name: "等待图片点击".into(),
                category: "图像操作".into(),
                params: vec![
                    ParamDef { name: "image_path".into(), param_type: "str".into(), default: "".into(), description: "图片路径".into() },
                    ParamDef { name: "confidence".into(), param_type: "float".into(), default: 0.9.into(), description: "置信度".into() },
                    ParamDef { name: "timeout".into(), param_type: "float".into(), default: 10.0.into(), description: "超时时间(秒)".into() },
                ],
            },
        );

        defs.insert(
            ActionType::ImageCheck,
            ActionDef {
                name: "检查图片".into(),
                category: "图像操作".into(),
                params: vec![
                    ParamDef { name: "image_path".into(), param_type: "str".into(), default: "".into(), description: "图片路径".into() },
                    ParamDef { name: "confidence".into(), param_type: "float".into(), default: 0.9.into(), description: "置信度".into() },
                ],
            },
        );

        defs.insert(
            ActionType::ActionGroupRef,
            ActionDef {
                name: "动作组引用".into(),
                category: "其他".into(),
                params: vec![
                    ParamDef { name: "group_name".into(), param_type: "str".into(), default: "".into(), description: "动作组名称".into() },
                ],
            },
        );

        defs
    }
}
