use std::collections::{HashMap, HashSet};
use std::fs;
use std::path::Path;
use base64::Engine;
use base64::engine::general_purpose::STANDARD as BASE64;
use chrono::Local;
use serde::{Deserialize, Serialize};

use crate::actions::{Action, ActionType};
use crate::action_group::{GlobalActionGroupManager, LocalActionGroupManager};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ScriptInfo {
    #[serde(default = "default_name")]
    pub name: String,
    #[serde(default)]
    pub author: String,
    #[serde(default)]
    pub description: String,
    pub created: String,
    #[serde(default = "default_version")]
    pub version: String,
    pub actions: Vec<Action>,
    #[serde(default)]
    pub action_groups: HashMap<String, serde_json::Value>,
    #[serde(default)]
    pub embedded_images: HashMap<String, String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub window_setup: Option<WindowSetup>,
    #[serde(default)]
    pub local_action_groups: HashMap<String, serde_json::Value>,
}

fn default_name() -> String { "RPA_Script".into() }
fn default_version() -> String { "2.1".into() }

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WindowSetup {
    pub enabled: bool,
    #[serde(default)]
    pub title: String,
    #[serde(default)]
    pub window_class: String,
    #[serde(default)]
    pub hwnd: i64,
}

pub struct Exporter {
    pub script_name: String,
    pub author: String,
    pub description: String,
    pub include_window_setup: bool,
    pub target_window_title: String,
    pub target_window_hwnd: i64,
    local_group_manager: Option<LocalActionGroupManager>,
    global_group_manager: GlobalActionGroupManager,
    used_groups: HashSet<String>,
    embedded_images: HashMap<String, String>,
}

impl Exporter {
    pub fn new() -> Self {
        Self {
            script_name: "RPA_Script".into(),
            author: String::new(),
            description: String::new(),
            include_window_setup: false,
            target_window_title: String::new(),
            target_window_hwnd: 0,
            local_group_manager: None,
            global_group_manager: GlobalActionGroupManager::new(),
            used_groups: HashSet::new(),
            embedded_images: HashMap::new(),
        }
    }

    pub fn set_local_group_manager(&mut self, manager: LocalActionGroupManager) {
        self.local_group_manager = Some(manager);
    }

    fn collect_used_groups(&mut self, actions: &[Action]) -> HashMap<String, serde_json::Value> {
        let mut action_groups = HashMap::new();

        for action in actions {
            if action.action_type == ActionType::ActionGroupRef {
                let group_name = action.params.get("group_name")
                    .and_then(|v| v.as_str())
                    .unwrap_or("");
                if group_name.is_empty() || action_groups.contains_key(group_name) {
                    continue;
                }

                let group = self.local_group_manager.as_ref()
                    .and_then(|m| m.get_group(group_name))
                    .or_else(|| self.global_group_manager.get_group(group_name));

                if let Some(group) = group {
                    self.used_groups.insert(group_name.to_string());
                    action_groups.insert(group_name.to_string(), group.to_dict());
                    let sub_actions = group.actions.clone();
                    let sub_groups = self.collect_used_groups(&sub_actions);
                    for (k, v) in sub_groups {
                        action_groups.entry(k).or_insert(v);
                    }
                }
            }
        }
        action_groups
    }

    fn collect_embedded_images(&mut self, actions: &[Action]) {
        for action in actions {
            if matches!(action.action_type, ActionType::ImageClick | ActionType::ImageWaitClick | ActionType::ImageCheck) {
                let image_path = action.params.get("image_path")
                    .and_then(|v| v.as_str())
                    .unwrap_or("");
                if !image_path.is_empty() && Path::new(image_path).exists() && !self.embedded_images.contains_key(image_path) {
                    if let Ok(data) = fs::read(image_path) {
                        self.embedded_images.insert(image_path.to_string(), BASE64.encode(&data));
                    }
                }
            }
        }
    }

    pub fn export_to_json(&mut self, actions: &[Action], filepath: &str) -> Result<(), String> {
        self.used_groups.clear();
        self.embedded_images.clear();

        let action_groups = self.collect_used_groups(actions);
        self.collect_embedded_images(actions);

        let data = ScriptInfo {
            name: self.script_name.clone(),
            author: self.author.clone(),
            description: self.description.clone(),
            created: Local::now().format("%Y-%m-%dT%H:%M:%S").to_string(),
            version: "2.1".into(),
            actions: actions.to_vec(),
            action_groups,
            embedded_images: self.embedded_images.iter()
                .map(|(k, v)| (Path::new(k).file_name().unwrap_or_default().to_string_lossy().to_string(), v.clone()))
                .collect(),
            window_setup: if self.include_window_setup {
                Some(WindowSetup {
                    enabled: true,
                    title: self.target_window_title.clone(),
                    window_class: String::new(),
                    hwnd: self.target_window_hwnd,
                })
            } else {
                None
            },
            local_action_groups: self.local_group_manager.as_ref()
                .map(|m| m.to_dict())
                .unwrap_or_default(),
        };

        let json = serde_json::to_string_pretty(&data).map_err(|e| e.to_string())?;
        fs::write(filepath, json).map_err(|e| e.to_string())
    }

    pub fn import_from_json(filepath: &str) -> Result<ScriptInfo, String> {
        let content = fs::read_to_string(filepath).map_err(|e| format!("读取文件失败: {}", e))?;
        let data: serde_json::Value = serde_json::from_str(&content).map_err(|e| format!("解析JSON失败: {}", e))?;

        let script: ScriptInfo = serde_json::from_value(data).map_err(|e| format!("解析脚本失败: {}", e))?;
        Ok(script)
    }

    pub fn export_to_python(&self, actions: &[Action], filepath: &str) -> Result<(), String> {
        let mut lines = vec![
            "#!/usr/bin/env python3".into(),
            "# -*- coding: utf-8 -*-".into(),
            "".into(),
            format!("\"\"\"RPA Script: {}\"\"\"", self.script_name),
            format!("Generated: {}", Local::now().format("%Y-%m-%d %H:%M:%S")),
            "\"\"\"".into(),
            "".into(),
            "import pyautogui".into(),
            "import time".into(),
            "".into(),
            "pyautogui.FAILSAFE = True".into(),
            "pyautogui.PAUSE = 0.1".into(),
            "".into(),
            "def main():".into(),
            "    print('Starting RPA script execution...')".into(),
        ];

        for (i, action) in actions.iter().enumerate() {
            lines.push(format!("    # Action {}: {}", i + 1, action.description));
            let code = self.action_to_code(action);
            for line in code.lines() {
                lines.push(format!("    {}", line));
            }
            lines.push("".into());
        }

        lines.push("    print('RPA script execution completed.')".into());
        lines.push("".into());
        lines.push("if __name__ == '__main__':".into());
        lines.push("    try:".into());
        lines.push("        main()".into());
        lines.push("    except KeyboardInterrupt:".into());
        lines.push("        print('\\nScript interrupted by user.')".into());
        lines.push("    except Exception as e:".into());
        lines.push("        print(f'Script error: {e}')".into());

        fs::write(filepath, lines.join("\n")).map_err(|e| e.to_string())
    }

    fn action_to_code(&self, action: &Action) -> String {
        let mut code_lines = Vec::new();

        if action.delay_before > 0.0 {
            code_lines.push(format!("time.sleep({})", action.delay_before));
        }

        match action.action_type {
            ActionType::MouseClick => {
                let x = action.params.get("x").and_then(|v| v.as_i64()).unwrap_or(0);
                let y = action.params.get("y").and_then(|v| v.as_i64()).unwrap_or(0);
                let button = action.params.get("button").and_then(|v| v.as_str()).unwrap_or("left");
                let clicks = action.params.get("clicks").and_then(|v| v.as_i64()).unwrap_or(1);
                code_lines.push(format!("pyautogui.click(x={}, y={}, button='{}', clicks={})", x, y, button, clicks));
            }
            ActionType::MouseDoubleClick => {
                let x = action.params.get("x").and_then(|v| v.as_i64()).unwrap_or(0);
                let y = action.params.get("y").and_then(|v| v.as_i64()).unwrap_or(0);
                code_lines.push(format!("pyautogui.doubleClick(x={}, y={})", x, y));
            }
            ActionType::MouseRightClick => {
                let x = action.params.get("x").and_then(|v| v.as_i64()).unwrap_or(0);
                let y = action.params.get("y").and_then(|v| v.as_i64()).unwrap_or(0);
                code_lines.push(format!("pyautogui.rightClick(x={}, y={})", x, y));
            }
            ActionType::MouseMove => {
                let x = action.params.get("x").and_then(|v| v.as_i64()).unwrap_or(0);
                let y = action.params.get("y").and_then(|v| v.as_i64()).unwrap_or(0);
                let d = action.params.get("duration").and_then(|v| v.as_f64()).unwrap_or(0.0);
                code_lines.push(format!("pyautogui.moveTo(x={}, y={}, duration={})", x, y, d));
            }
            ActionType::MouseDrag => {
                let sx = action.params.get("start_x").and_then(|v| v.as_i64()).unwrap_or(0);
                let sy = action.params.get("start_y").and_then(|v| v.as_i64()).unwrap_or(0);
                let ex = action.params.get("end_x").and_then(|v| v.as_i64()).unwrap_or(0);
                let ey = action.params.get("end_y").and_then(|v| v.as_i64()).unwrap_or(0);
                let d = action.params.get("duration").and_then(|v| v.as_f64()).unwrap_or(0.5);
                code_lines.push(format!("pyautogui.moveTo({}, {})", sx, sy));
                code_lines.push(format!("pyautogui.drag({}, {}, duration={})", ex - sx, ey - sy, d));
            }
            ActionType::MouseScroll => {
                let clicks = action.params.get("clicks").and_then(|v| v.as_i64()).unwrap_or(0);
                let x = action.params.get("x").and_then(|v| v.as_i64()).unwrap_or(0);
                let y = action.params.get("y").and_then(|v| v.as_i64()).unwrap_or(0);
                code_lines.push(format!("pyautogui.scroll({}, x={}, y={})", clicks, x, y));
            }
            ActionType::KeyPress => {
                let key = action.params.get("key").and_then(|v| v.as_str()).unwrap_or("");
                code_lines.push(format!("pyautogui.press('{}')", key));
            }
            ActionType::KeyType => {
                let text = action.params.get("text").and_then(|v| v.as_str()).unwrap_or("");
                let interval = action.params.get("interval").and_then(|v| v.as_f64()).unwrap_or(0.0);
                let escaped = text.replace('\'', "\\'");
                code_lines.push(format!("pyautogui.typewrite('{}', interval={})", escaped, interval));
            }
            ActionType::Hotkey => {
                let keys: Vec<String> = action.params.get("keys")
                    .and_then(|v| v.as_array())
                    .map(|arr| arr.iter().filter_map(|k| k.as_str().map(|s| format!("'{}'", s))).collect())
                    .unwrap_or_default();
                code_lines.push(format!("pyautogui.hotkey({})", keys.join(", ")));
            }
            ActionType::Wait => {
                let seconds = action.params.get("seconds").and_then(|v| v.as_f64()).unwrap_or(1.0);
                code_lines.push(format!("time.sleep({})", seconds));
            }
            ActionType::Screenshot => {
                let fname = action.params.get("filename").and_then(|v| v.as_str()).unwrap_or("screenshot.png");
                code_lines.push(format!("pyautogui.screenshot('{}')", fname));
            }
            ActionType::MouseClickRelative | ActionType::MouseMoveRelative => {
                let x = action.params.get("x").and_then(|v| v.as_i64()).unwrap_or(0);
                let y = action.params.get("y").and_then(|v| v.as_i64()).unwrap_or(0);
                if action.action_type == ActionType::MouseMoveRelative {
                    let d = action.params.get("duration").and_then(|v| v.as_f64()).unwrap_or(0.0);
                    code_lines.push(format!("pyautogui.moveTo(x=window_x + {}, y=window_y + {}, duration={})", x, y, d));
                } else {
                    code_lines.push(format!("pyautogui.click(x=window_x + {}, y=window_y + {})", x, y));
                }
            }
            ActionType::ImageClick => {
                let path = action.params.get("image_path").and_then(|v| v.as_str()).unwrap_or("");
                let confidence = action.params.get("confidence").and_then(|v| v.as_f64()).unwrap_or(0.9);
                let escaped = path.replace('\\', "\\\\");
                code_lines.push(format!("location = pyautogui.locateOnScreen(r'{}', confidence={})", escaped, confidence));
                code_lines.push("if location:".into());
                code_lines.push("    center = pyautogui.center(location)".into());
                code_lines.push("    pyautogui.click(center.x, center.y)".into());
            }
            ActionType::ImageWaitClick => {
                let path = action.params.get("image_path").and_then(|v| v.as_str()).unwrap_or("");
                let confidence = action.params.get("confidence").and_then(|v| v.as_f64()).unwrap_or(0.9);
                let timeout = action.params.get("timeout").and_then(|v| v.as_i64()).unwrap_or(10);
                let escaped = path.replace('\\', "\\\\");
                code_lines.push(format!("location = pyautogui.locateOnScreen(r'{}', confidence={})", escaped, confidence));
                code_lines.push("start_time = time.time()".into());
                code_lines.push(format!("while location is None and (time.time() - start_time) < {}:", timeout));
                code_lines.push("    time.sleep(0.5)".into());
                code_lines.push(format!("    location = pyautogui.locateOnScreen(r'{}', confidence={})", escaped, confidence));
                code_lines.push("if location:".into());
                code_lines.push("    center = pyautogui.center(location)".into());
                code_lines.push("    pyautogui.click(center.x, center.y)".into());
            }
            ActionType::ImageCheck => {
                let path = action.params.get("image_path").and_then(|v| v.as_str()).unwrap_or("");
                let confidence = action.params.get("confidence").and_then(|v| v.as_f64()).unwrap_or(0.9);
                let marker = action.condition_marker().unwrap_or_else(|| "${image_found}".into());
                let var_name = &marker[1..];
                let escaped = path.replace('\\', "\\\\");
                code_lines.push(format!("location = pyautogui.locateOnScreen(r'{}', confidence={})", escaped, confidence));
                code_lines.push(format!("{} = location is not None", var_name));
            }
            ActionType::ActionGroupRef => {
                let group_name = action.params.get("group_name").and_then(|v| v.as_str()).unwrap_or("");
                code_lines.push(format!("execute_action_group('{}')", group_name));
            }
        }

        if action.delay_after > 0.0 {
            code_lines.push(format!("time.sleep({})", action.delay_after));
        }

        code_lines.join("\n")
    }
}
