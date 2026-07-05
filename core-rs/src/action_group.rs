use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::path::PathBuf;

use crate::actions::Action;

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

    pub fn get_action_count(&self) -> usize {
        self.actions.len()
    }

    pub fn validate(&self) -> Result<(), String> {
        if self.name.trim().is_empty() {
            return Err("动作组名称不能为空".to_string());
        }
        if self.actions.is_empty() {
            return Err("动作组必须包含至少一个动作".to_string());
        }
        for (i, action) in self.actions.iter().enumerate() {
            action
                .validate()
                .map_err(|e| format!("动作 {} 验证失败: {}", i + 1, e))?;
        }
        Ok(())
    }
}

pub struct LocalActionGroupManager {
    groups: HashMap<String, ActionGroup>,
}

impl LocalActionGroupManager {
    pub fn new() -> Self {
        Self {
            groups: HashMap::new(),
        }
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

    pub fn to_dict(&self) -> HashMap<String, ActionGroup> {
        self.groups.clone()
    }

    pub fn load_from_dict(&mut self, data: &HashMap<String, ActionGroup>) {
        self.groups.clear();
        for (name, group) in data {
            if group.validate().is_ok() {
                self.groups.insert(name.clone(), group.clone());
            }
        }
    }

    pub fn clear(&mut self) {
        self.groups.clear();
    }

    pub fn get_group_names(&self) -> Vec<String> {
        self.groups.keys().cloned().collect()
    }
}

impl Default for LocalActionGroupManager {
    fn default() -> Self {
        Self::new()
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
                        if let Ok(group) = serde_json::from_str::<ActionGroup>(&content) {
                            if group.validate().is_ok() {
                                self.groups.insert(group.name.clone(), group);
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

    pub fn save_group(&mut self, group: ActionGroup) -> Result<(), String> {
        group.validate()?;
        let filepath = self.groups_dir.join(format!("{}.json", group.name));
        let content = serde_json::to_string_pretty(&group)
            .map_err(|e| format!("序列化失败: {}", e))?;
        fs::write(&filepath, content)
            .map_err(|e| format!("写入文件失败: {}", e))?;
        self.groups.insert(group.name.clone(), group);
        Ok(())
    }

    pub fn delete_group(&mut self, name: &str) -> Result<(), String> {
        self.groups.remove(name);
        let filepath = self.groups_dir.join(format!("{}.json", name));
        if filepath.exists() {
            fs::remove_file(&filepath)
                .map_err(|e| format!("删除文件失败: {}", e))?;
        }
        Ok(())
    }

    pub fn ensure_group_loaded(&mut self, name: &str) -> Option<ActionGroup> {
        if let Some(group) = self.groups.get(name) {
            return Some(group.clone());
        }
        let filepath = self.groups_dir.join(format!("{}.json", name));
        if filepath.exists() {
            if let Ok(content) = fs::read_to_string(&filepath) {
                if let Ok(group) = serde_json::from_str::<ActionGroup>(&content) {
                    if group.validate().is_ok() {
                        self.groups.insert(group.name.clone(), group.clone());
                        return Some(group);
                    }
                }
            }
        }
        None
    }
}
