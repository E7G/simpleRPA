use crate::actions::Action;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ActionGroup {
    pub name: String,
    #[serde(default)]
    pub description: String,
    #[serde(default)]
    pub actions: Vec<Action>,
}

impl ActionGroup {
    pub fn new(name: &str) -> Self {
        Self {
            name: name.to_string(),
            description: String::new(),
            actions: Vec::new(),
        }
    }

    pub fn to_dict(&self) -> serde_json::Value {
        serde_json::json!({
            "name": self.name,
            "description": self.description,
            "actions": self.actions.iter().map(|a| a.to_dict()).collect::<Vec<_>>(),
        })
    }

    pub fn from_dict(data: &serde_json::Value) -> Option<Self> {
        let name = data.get("name")?.as_str()?.to_string();
        let description = data
            .get("description")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string();
        let actions = data
            .get("actions")
            .and_then(|v| v.as_array())
            .map(|arr| arr.iter().filter_map(|a| Action::from_dict(a)).collect())
            .unwrap_or_default();

        Some(Self {
            name,
            description,
            actions,
        })
    }

    pub fn validate(&self) -> Result<(), String> {
        if self.name.trim().is_empty() {
            return Err("动作组名称不能为空".into());
        }
        if self.actions.is_empty() {
            return Err("动作组必须包含至少一个动作".into());
        }
        for (i, action) in self.actions.iter().enumerate() {
            action
                .validate()
                .map_err(|e| format!("动作 {} 验证失败: {}", i + 1, e))?;
        }
        Ok(())
    }
}

#[derive(Debug, Clone, Default)]
pub struct LocalActionGroupManager {
    groups: HashMap<String, ActionGroup>,
}

impl LocalActionGroupManager {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn get_all_groups(&self) -> Vec<&ActionGroup> {
        self.groups.values().collect()
    }

    pub fn get_group(&self, name: &str) -> Option<&ActionGroup> {
        self.groups.get(name)
    }

    pub fn has_group(&self, name: &str) -> bool {
        self.groups.contains_key(name)
    }

    pub fn save_group(&mut self, group: ActionGroup) -> Result<(), String> {
        group.validate()?;
        self.groups.insert(group.name.clone(), group);
        Ok(())
    }

    pub fn delete_group(&mut self, name: &str) -> bool {
        self.groups.remove(name).is_some()
    }

    pub fn create_group_from_actions(
        &self,
        name: &str,
        description: &str,
        actions: &[Action],
    ) -> ActionGroup {
        ActionGroup {
            name: name.to_string(),
            description: description.to_string(),
            actions: actions.to_vec(),
        }
    }

    pub fn get_actions_copy(&self, name: &str) -> Vec<Action> {
        self.groups
            .get(name)
            .map(|g| g.actions.clone())
            .unwrap_or_default()
    }

    pub fn to_dict(&self) -> serde_json::Value {
        let map: serde_json::Map<String, serde_json::Value> = self
            .groups
            .iter()
            .map(|(name, group)| (name.clone(), group.to_dict()))
            .collect();
        serde_json::Value::Object(map)
    }

    pub fn load_from_dict(&mut self, data: &serde_json::Value) -> (i32, i32) {
        self.groups.clear();
        let mut success_count = 0;
        let mut fail_count = 0;

        if let Some(obj) = data.as_object() {
            for (name, group_data) in obj {
                if let Some(group) = ActionGroup::from_dict(group_data) {
                    if group.validate().is_ok() {
                        self.groups.insert(name.clone(), group);
                        success_count += 1;
                    } else {
                        fail_count += 1;
                    }
                } else {
                    fail_count += 1;
                }
            }
        }

        (success_count, fail_count)
    }

    pub fn clear(&mut self) {
        self.groups.clear();
    }

    pub fn ensure_group_available(
        &mut self,
        name: &str,
        global_manager: &GlobalActionGroupManager,
    ) -> Option<ActionGroup> {
        if let Some(group) = self.groups.get(name) {
            return Some(group.clone());
        }

        if let Some(group) = global_manager.get_group(name) {
            self.groups.insert(name.to_string(), group.clone());
            return Some(group.clone());
        }

        None
    }
}

pub struct GlobalActionGroupManager {
    groups: HashMap<String, ActionGroup>,
    groups_dir: PathBuf,
}

impl GlobalActionGroupManager {
    pub fn new() -> Self {
        let groups_dir = dirs::home_dir()
            .unwrap_or_else(|| PathBuf::from("."))
            .join(".simpleRPA")
            .join("groups");
        let _ = fs::create_dir_all(&groups_dir);

        let mut mgr = Self {
            groups: HashMap::new(),
            groups_dir,
        };
        mgr.load_all_groups();
        mgr
    }

    fn load_all_groups(&mut self) {
        if !self.groups_dir.exists() {
            return;
        }

        if let Ok(entries) = fs::read_dir(&self.groups_dir) {
            for entry in entries.flatten() {
                let path = entry.path();
                if path.extension().and_then(|e| e.to_str()) == Some("json") {
                    if let Ok(content) = fs::read_to_string(&path) {
                        if let Ok(data) = serde_json::from_str::<serde_json::Value>(&content) {
                            if let Some(group) = ActionGroup::from_dict(&data) {
                                if group.validate().is_ok() {
                                    self.groups.insert(group.name.clone(), group);
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    pub fn reload_groups(&mut self) {
        self.groups.clear();
        self.load_all_groups();
    }

    pub fn get_all_groups(&self) -> Vec<&ActionGroup> {
        self.groups.values().collect()
    }

    pub fn get_group(&self, name: &str) -> Option<&ActionGroup> {
        self.groups.get(name)
    }

    pub fn has_group(&self, name: &str) -> bool {
        self.groups.contains_key(name)
    }

    pub fn save_group(&mut self, group: &ActionGroup) -> Result<(), String> {
        group.validate()?;

        let filepath = self.groups_dir.join(format!("{}.json", group.name));
        let json = serde_json::to_string_pretty(&group.to_dict())
            .map_err(|e| format!("JSON序列化失败: {}", e))?;
        fs::write(&filepath, json).map_err(|e| format!("写入文件失败: {}", e))?;

        self.groups.insert(group.name.clone(), group.clone());
        Ok(())
    }

    pub fn delete_group(&mut self, name: &str) -> bool {
        if self.groups.remove(name).is_some() {
            let filepath = self.groups_dir.join(format!("{}.json", name));
            let _ = fs::remove_file(&filepath);
            true
        } else {
            false
        }
    }

    pub fn ensure_group_loaded(&mut self, name: &str) -> Option<ActionGroup> {
        if let Some(group) = self.groups.get(name) {
            return Some(group.clone());
        }

        let filepath = self.groups_dir.join(format!("{}.json", name));
        if filepath.exists() {
            if let Ok(content) = fs::read_to_string(&filepath) {
                if let Ok(data) = serde_json::from_str::<serde_json::Value>(&content) {
                    if let Some(group) = ActionGroup::from_dict(&data) {
                        if group.validate().is_ok() {
                            self.groups.insert(group.name.clone(), group.clone());
                            return Some(group.clone());
                        }
                    }
                }
            }
        }

        None
    }
}

pub fn ensure_action_group_available(
    group_name: &str,
    local_manager: Option<&mut LocalActionGroupManager>,
) -> Option<ActionGroup> {
    let global_manager = GlobalActionGroupManager::new();

    if let Some(ref mgr) = local_manager {
        if let Some(group) = mgr.get_group(group_name) {
            return Some(group.clone());
        }
    }

    if let Some(group) = global_manager.get_group(group_name) {
        if let Some(mgr) = local_manager {
            mgr.save_group(group.clone()).ok();
        }
        return Some(group.clone());
    }

    None
}

pub fn encode_image_to_base64(image_path: &str) -> Option<String> {
    let data = fs::read(image_path).ok()?;
    use base64::Engine;
    Some(base64::engine::general_purpose::STANDARD.encode(&data))
}

pub fn decode_base64_to_image(base64_data: &str, output_path: &str) -> Result<(), String> {
    use base64::Engine;
    let data = base64::engine::general_purpose::STANDARD
        .decode(base64_data)
        .map_err(|e| format!("Base64解码失败: {}", e))?;
    if let Some(parent) = std::path::Path::new(output_path).parent() {
        fs::create_dir_all(parent).map_err(|e| format!("创建目录失败: {}", e))?;
    }
    fs::write(output_path, data).map_err(|e| format!("写入文件失败: {}", e))
}
