use crate::action_group::{
    encode_image_to_base64, GlobalActionGroupManager, LocalActionGroupManager,
};
use crate::actions::{Action, ActionType};
use std::collections::{HashMap, HashSet};
use std::fs;
use std::path::Path;

pub struct Exporter {
    pub script_name: String,
    pub author: String,
    pub description: String,
    pub include_window_setup: bool,
    pub target_window_title: String,
    local_group_manager: Option<LocalActionGroupManager>,
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
            local_group_manager: None,
            used_groups: HashSet::new(),
            embedded_images: HashMap::new(),
        }
    }

    pub fn set_script_info(&mut self, name: &str, author: &str, description: &str) {
        self.script_name = if name.is_empty() {
            "RPA_Script".into()
        } else {
            name.into()
        };
        self.author = author.into();
        self.description = description.into();
    }

    pub fn set_window_setup(&mut self, include: bool, window_title: &str) {
        self.include_window_setup = include;
        self.target_window_title = window_title.into();
    }

    pub fn set_local_group_manager(&mut self, manager: LocalActionGroupManager) {
        self.local_group_manager = Some(manager);
    }

    fn collect_used_groups(&mut self, actions: &[Action]) -> serde_json::Value {
        let mut action_groups = serde_json::Map::new();

        for action in actions {
            if action.action_type == ActionType::ActionGroupRef {
                let group_name = action.param_str("group_name");
                if group_name.is_empty() || action_groups.contains_key(&group_name) {
                    continue;
                }

                let mut group_data = None;
                if let Some(ref mgr) = self.local_group_manager {
                    if let Some(group) = mgr.get_group(&group_name) {
                        group_data = Some(group.to_dict());
                    }
                }
                if group_data.is_none() {
                    let global = GlobalActionGroupManager::new();
                    if let Some(group) = global.get_group(&group_name) {
                        group_data = Some(group.to_dict());
                    }
                }

                if let Some(data) = group_data {
                    self.used_groups.insert(group_name.clone());
                    action_groups.insert(group_name, data);
                }
            }
        }

        serde_json::Value::Object(action_groups)
    }

    fn collect_embedded_images(&mut self, actions: &[Action]) {
        for action in actions {
            if matches!(
                action.action_type,
                ActionType::ImageClick | ActionType::ImageWaitClick | ActionType::ImageCheck
            ) {
                let image_path = action.param_str("image_path");
                if !image_path.is_empty() && Path::new(&image_path).exists() {
                    if !self.embedded_images.contains_key(&image_path) {
                        if let Some(data) = encode_image_to_base64(&image_path) {
                            self.embedded_images.insert(image_path, data);
                        }
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

        let embedded: serde_json::Map<String, serde_json::Value> = self
            .embedded_images
            .iter()
            .map(|(path, data)| {
                let name = std::path::Path::new(path)
                    .file_name()
                    .and_then(|n| n.to_str())
                    .unwrap_or("");
                (name.to_string(), serde_json::Value::String(data.clone()))
            })
            .collect();

        let mut data = serde_json::json!({
            "name": self.script_name,
            "author": self.author,
            "description": self.description,
            "version": "2.1",
            "actions": actions.iter().map(|a| a.to_dict()).collect::<Vec<_>>(),
            "action_groups": action_groups,
            "embedded_images": embedded,
        });

        if self.include_window_setup {
            data["window_setup"] = serde_json::json!({
                "enabled": true,
                "title": self.target_window_title,
            });
        }

        if let Some(ref mgr) = self.local_group_manager {
            let local_groups = mgr.to_dict();
            if !local_groups.is_null() {
                data["local_action_groups"] = local_groups;
            }
        }

        let json =
            serde_json::to_string_pretty(&data).map_err(|e| format!("JSON序列化失败: {}", e))?;
        fs::write(filepath, json).map_err(|e| format!("写入文件失败: {}", e))
    }

    pub fn import_from_json(
        filepath: &str,
        local_group_manager: Option<&mut LocalActionGroupManager>,
    ) -> Result<Vec<Action>, String> {
        let content = fs::read_to_string(filepath).map_err(|e| format!("读取文件失败: {}", e))?;
        let data: serde_json::Value =
            serde_json::from_str(&content).map_err(|e| format!("JSON解析失败: {}", e))?;

        let embedded_images = data
            .get("embedded_images")
            .and_then(|v| v.as_object())
            .cloned()
            .unwrap_or_default();

        let script_dir = Path::new(filepath).parent().unwrap_or(Path::new("."));
        let temp_dir = script_dir.join(".images");
        let mut image_path_map = HashMap::new();

        for (image_name, base64_data) in &embedded_images {
            if let Some(data_str) = base64_data.as_str() {
                use base64::Engine;
                if let Ok(bytes) = base64::engine::general_purpose::STANDARD.decode(data_str) {
                    let _ = fs::create_dir_all(&temp_dir);
                    let image_path = temp_dir.join(image_name);
                    let _ = fs::write(&image_path, &bytes);
                    image_path_map
                        .insert(image_name.clone(), image_path.to_string_lossy().to_string());
                }
            }
        }

        if let Some(mgr) = local_group_manager {
            let local_groups = data
                .get("local_action_groups")
                .or_else(|| data.get("action_groups"))
                .cloned()
                .unwrap_or(serde_json::Value::Object(serde_json::Map::new()));
            mgr.load_from_dict(&local_groups);
        }

        let actions: Vec<Action> = data
            .get("actions")
            .and_then(|v| v.as_array())
            .map(|arr| {
                arr.iter()
                    .filter_map(|a| {
                        let mut action = Action::from_dict(a)?;
                        if matches!(
                            action.action_type,
                            ActionType::ImageClick
                                | ActionType::ImageWaitClick
                                | ActionType::ImageCheck
                        ) {
                            let original_path = action.param_str("image_path");
                            let image_name = std::path::Path::new(&original_path)
                                .file_name()
                                .and_then(|n| n.to_str())
                                .unwrap_or("");
                            if let Some(new_path) = image_path_map.get(image_name) {
                                action
                                    .params
                                    .insert("image_path".into(), serde_json::json!(new_path));
                            }
                        }
                        Some(action)
                    })
                    .collect()
            })
            .unwrap_or_default();

        Ok(actions)
    }

    pub fn export_to_python(&self, actions: &[Action], filepath: &str) -> Result<(), String> {
        let mut lines = Vec::new();

        lines.push("#!/usr/bin/env python3".into());
        lines.push("# -*- coding: utf-8 -*-".into());
        lines.push("".into());
        lines.push(format!("\"\"\""));
        lines.push(format!("RPA Script: {}", self.script_name));
        if !self.author.is_empty() {
            lines.push(format!("Author: {}", self.author));
        }
        lines.push(format!("Generated by simpleRPA (Rust)"));
        lines.push(format!("\"\"\""));
        lines.push("".into());
        lines.push("import pyautogui".into());
        lines.push("import time".into());
        lines.push("".into());

        lines.push("def main():".into());
        lines.push("    pyautogui.FAILSAFE = True".into());
        lines.push("    pyautogui.PAUSE = 0.1".into());
        lines.push("    print('Starting RPA script execution...')".into());
        lines.push("".into());

        for (i, action) in actions.iter().enumerate() {
            lines.push(format!("    # Action {}: {}", i + 1, action.description));
            let mut visited_groups = HashSet::new();
            let code = action_to_python_code_with_groups(
                action,
                self.local_group_manager.as_ref(),
                &mut visited_groups,
            );
            for line in code.lines() {
                lines.push(format!("    {}", line));
            }
            lines.push("".into());
        }

        lines.push("    print('RPA script execution completed.')".into());
        lines.push("".into());
        lines.push("if __name__ == '__main__':".into());
        lines.push("    main()".into());

        let code = lines.join("\n");
        fs::write(filepath, code).map_err(|e| format!("写入文件失败: {}", e))
    }

    pub fn actions_to_python_code(actions: &[Action], indent: &str) -> String {
        Self::actions_to_python_code_with_groups(actions, indent, None)
    }

    pub fn actions_to_python_code_with_groups(
        actions: &[Action],
        indent: &str,
        local_group_manager: Option<&LocalActionGroupManager>,
    ) -> String {
        let mut lines = Vec::new();
        let mut visited_groups = HashSet::new();
        for (i, action) in actions.iter().enumerate() {
            lines.push(format!("{}# Action {}: {}", indent, i + 1, action.description));
            let code = action_to_python_code_with_groups(
                action,
                local_group_manager,
                &mut visited_groups,
            );
            for line in code.lines() {
                lines.push(format!("{}{}", indent, line));
            }
            lines.push(String::new());
        }
        lines.join("\n")
    }
}

fn action_to_python_code_with_groups(
    action: &Action,
    local_group_manager: Option<&LocalActionGroupManager>,
    visited_groups: &mut HashSet<String>,
) -> String {
    let mut lines = Vec::new();

    if action.delay_before > 0.0 {
        lines.push(format!("time.sleep({})", action.delay_before));
    }

    match action.action_type {
        ActionType::MouseClick => {
            let x = action.param_i32("x");
            let y = action.param_i32("y");
            let button = action.param_str("button").if_empty("left");
            let clicks = action.param_i32("clicks").max(1);
            lines.push(format!(
                "pyautogui.click(x={}, y={}, button='{}', clicks={})",
                x, y, button, clicks
            ));
        }
        ActionType::MouseDoubleClick => {
            let x = action.param_i32("x");
            let y = action.param_i32("y");
            lines.push(format!("pyautogui.doubleClick(x={}, y={})", x, y));
        }
        ActionType::MouseRightClick => {
            let x = action.param_i32("x");
            let y = action.param_i32("y");
            lines.push(format!("pyautogui.rightClick(x={}, y={})", x, y));
        }
        ActionType::MouseMove => {
            let x = action.param_i32("x");
            let y = action.param_i32("y");
            let duration = action.param_f64("duration");
            lines.push(format!(
                "pyautogui.moveTo(x={}, y={}, duration={})",
                x, y, duration
            ));
        }
        ActionType::MouseDrag => {
            let sx = action.param_i32("start_x");
            let sy = action.param_i32("start_y");
            let ex = action.param_i32("end_x");
            let ey = action.param_i32("end_y");
            let duration = action.param_f64("duration");
            lines.push(format!("pyautogui.moveTo({}, {})", sx, sy));
            lines.push(format!(
                "pyautogui.drag({}, {}, duration={})",
                ex - sx,
                ey - sy,
                duration
            ));
        }
        ActionType::MouseScroll => {
            let clicks = action.param_i32("clicks");
            let x = action.param_i32("x");
            let y = action.param_i32("y");
            lines.push(format!("pyautogui.scroll({}, x={}, y={})", clicks, x, y));
        }
        ActionType::KeyPress => {
            let key = action.param_str("key");
            lines.push(format!("pyautogui.press({})", py_string_literal(&key)));
        }
        ActionType::KeyType => {
            let text = action.param_str("text");
            let interval = action.param_f64("interval");
            lines.push(format!(
                "pyautogui.typewrite({}, interval={})",
                py_string_literal(&text),
                interval
            ));
        }
        ActionType::Hotkey => {
            let keys = action.param_str_slice("keys");
            let keys_str: Vec<String> = keys.iter().map(|k| py_string_literal(k)).collect();
            lines.push(format!("pyautogui.hotkey({})", keys_str.join(", ")));
        }
        ActionType::Wait => {
            let seconds = action.param_f64("seconds");
            lines.push(format!("time.sleep({})", seconds));
        }
        ActionType::Screenshot => {
            let filename = action.param_str("filename").if_empty("screenshot.png");
            lines.push(format!("pyautogui.screenshot({})", py_string_literal(&filename)));
        }
        ActionType::MouseMoveRelative => {
            let x = action.param_i32("x");
            let y = action.param_i32("y");
            let duration = action.param_f64("duration");
            lines.push("try:".into());
            lines.push("    wx, wy = window_x, window_y".into());
            lines.push("except NameError:".into());
            lines.push("    wx, wy = 0, 0".into());
            lines.push(format!(
                "pyautogui.moveTo(x=wx + {}, y=wy + {}, duration={})",
                x, y, duration
            ));
        }
        ActionType::MouseClickRelative => {
            let x = action.param_i32("x");
            let y = action.param_i32("y");
            let button = action.param_str("button").if_empty("left");
            let clicks = action.param_i32("clicks").max(1);
            lines.push("try:".into());
            lines.push("    wx, wy = window_x, window_y".into());
            lines.push("except NameError:".into());
            lines.push("    wx, wy = 0, 0".into());
            lines.push(format!(
                "pyautogui.click(x=wx + {}, y=wy + {}, button={}, clicks={})",
                x,
                y,
                py_string_literal(&button),
                clicks
            ));
        }
        ActionType::ImageClick => {
            let path = action.param_str("image_path");
            let confidence = action.param_f64("confidence");
            lines.push("try:".into());
            lines.push(format!(
                "    location = pyautogui.locateOnScreen({}, confidence={})",
                py_string_literal(&path),
                confidence
            ));
            lines.push("    if location:".into());
            lines.push("        center = pyautogui.center(location)".into());
            lines.push("        pyautogui.click(center)".into());
            lines.push("    else:".into());
            lines.push(format!(
                "        print({})",
                py_string_literal(&format!("未找到图片: {}", file_basename(&path)))
            ));
            lines.push("except Exception as e:".into());
            lines.push("    print(f'图片点击失败: {e}')".into());
        }
        ActionType::ImageWaitClick => {
            let path = action.param_str("image_path");
            let confidence = action.param_f64("confidence");
            let timeout = action.param_f64("timeout");
            let checks = (timeout.max(0.5) * 2.0).ceil() as i32;
            lines.push("location = None".into());
            lines.push(format!("for _ in range({}):", checks.max(1)));
            lines.push("    try:".into());
            lines.push(format!(
                "        location = pyautogui.locateOnScreen({}, confidence={})",
                py_string_literal(&path),
                confidence
            ));
            lines.push("        if location:".into());
            lines.push("            break".into());
            lines.push("    except Exception:".into());
            lines.push("        pass".into());
            lines.push("    time.sleep(0.5)".into());
            lines.push("if location:".into());
            lines.push("    center = pyautogui.center(location)".into());
            lines.push("    pyautogui.click(center)".into());
            lines.push("else:".into());
            lines.push(format!(
                "    print({})",
                py_string_literal(&format!("等待图片超时: {}", file_basename(&path)))
            ));
        }
        ActionType::ImageCheck => {
            let path = action.param_str("image_path");
            let confidence = action.param_f64("confidence");
            lines.push("try:".into());
            lines.push(format!(
                "    location = pyautogui.locateOnScreen({}, confidence={})",
                py_string_literal(&path),
                confidence
            ));
            lines.push("    if location:".into());
            lines.push("        print('图片检查: 找到')".into());
            lines.push("    else:".into());
            lines.push("        print('图片检查: 未找到')".into());
            lines.push("except Exception as e:".into());
            lines.push("    print(f'图片检查失败: {e}')".into());
        }
        ActionType::ActionGroupRef => {
            let group_name = action.param_str("group_name").if_empty("未知");
            if let Some(manager) = local_group_manager {
                if visited_groups.contains(&group_name) {
                    lines.push(format!(
                        "print({})",
                        py_string_literal(&format!("跳过循环动作组引用: {}", group_name))
                    ));
                } else if let Some(group) = manager.get_group(&group_name) {
                    visited_groups.insert(group_name.clone());
                    lines.push(format!("# 执行动作组: {}", group_name));
                    for group_action in &group.actions {
                        let code = action_to_python_code_with_groups(
                            group_action,
                            local_group_manager,
                            visited_groups,
                        );
                        for line in code.lines() {
                            lines.push(line.to_string());
                        }
                    }
                    visited_groups.remove(&group_name);
                } else {
                    lines.push(format!(
                        "print({})",
                        py_string_literal(&format!("动作组不存在: {}", group_name))
                    ));
                }
            } else {
                lines.push(format!(
                    "print({})",
                    py_string_literal(&format!("动作组引用需要在 simpleRPA 中执行: {}", group_name))
                ));
            }
        }
    }

    if action.delay_after > 0.0 {
        lines.push(format!("time.sleep({})", action.delay_after));
    }

    lines.join("\n")
}

fn py_string_literal(value: &str) -> String {
    let escaped = value
        .replace('\\', "\\\\")
        .replace('\'', "\\'")
        .replace('\n', "\\n")
        .replace('\r', "\\r");
    format!("'{}'", escaped)
}

fn file_basename(path: &str) -> String {
    std::path::Path::new(path)
        .file_name()
        .and_then(|name| name.to_str())
        .unwrap_or(path)
        .to_string()
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
