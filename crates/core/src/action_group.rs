use std::collections::HashMap;
use std::fs;
use std::path::PathBuf;
use serde::{Deserialize, Serialize};
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

    pub fn action_count(&self) -> usize {
        self.actions.len()
    }

    pub fn validate(&self) -> Result<(), String> {
        if self.name.trim().is_empty() {
            return Err("动作组名称不能为空".into());
        }
        if self.actions.is_empty() {
            return Err("动作组必须包含至少一个动作".into());
        }
        for (i, action) in self.actions.iter().enumerate() {
            action.validate().map_err(|e| format!("动作 {} 验证失败: {}", i + 1, e))?;
        }
        Ok(())
    }

    pub fn to_dict(&self) -> serde_json::Value {
        serde_json::to_value(self).unwrap_or(serde_json::Value::Null)
    }

    pub fn from_dict(data: &serde_json::Value) -> Result<Self, String> {
        serde_json::from_value(data.clone()).map_err(|e| format!("解析动作组失败: {}", e))
    }
}

#[derive(Debug, Default)]
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

    pub fn create_group_from_actions(&self, name: &str, description: &str, actions: &[Action]) -> ActionGroup {
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

    pub fn to_dict(&self) -> HashMap<String, serde_json::Value> {
        self.groups
            .iter()
            .map(|(k, v)| (k.clone(), v.to_dict()))
            .collect()
    }

    pub fn load_from_dict(&mut self, data: &HashMap<String, serde_json::Value>) -> (usize, usize) {
        self.groups.clear();
        let mut success = 0;
        let mut fail = 0;
        for (name, group_data) in data {
            match ActionGroup::from_dict(group_data) {
                Ok(group) => {
                    if group.validate().is_ok() {
                        self.groups.insert(group.name.clone(), group);
                        success += 1;
                    } else {
                        fail += 1;
                    }
                }
                Err(_) => fail += 1,
            }
        }
        (success, fail)
    }

    pub fn clear(&mut self) {
        self.groups.clear();
    }
}

#[derive(Debug)]
pub struct GlobalActionGroupManager {
    groups: HashMap<String, ActionGroup>,
    groups_dir: PathBuf,
}

impl GlobalActionGroupManager {
    pub fn new() -> Self {
        let groups_dir = dirs_or_default()
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

    fn load_all_groups(&mut self) -> (usize, usize) {
        let mut success = 0;
        let mut fail = 0;

        if let Ok(entries) = fs::read_dir(&self.groups_dir) {
            for entry in entries.flatten() {
                let path = entry.path();
                if path.extension().and_then(|e| e.to_str()) == Some("json") {
                    if let Ok(content) = fs::read_to_string(&path) {
                        if let Ok(data) = serde_json::from_str::<serde_json::Value>(&content) {
                            if let Ok(group) = ActionGroup::from_dict(&data) {
                                if group.validate().is_ok() {
                                    self.groups.insert(group.name.clone(), group);
                                    success += 1;
                                } else {
                                    fail += 1;
                                }
                            } else {
                                fail += 1;
                            }
                        } else {
                            fail += 1;
                        }
                    } else {
                        fail += 1;
                    }
                }
            }
        }
        (success, fail)
    }

    pub fn reload(&mut self) -> (usize, usize) {
        self.groups.clear();
        self.load_all_groups()
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
        let filepath = self.groups_dir.join(format!("{}.json", group.name));
        let json = serde_json::to_string_pretty(&group).map_err(|e| e.to_string())?;
        fs::write(&filepath, json).map_err(|e| e.to_string())?;
        self.groups.insert(group.name.clone(), group);
        Ok(())
    }

    pub fn delete_group(&mut self, name: &str) -> bool {
        if self.groups.remove(name).is_some() {
            let filepath = self.groups_dir.join(format!("{}.json", name));
            let _ = fs::remove_file(filepath);
            true
        } else {
            false
        }
    }

    pub fn ensure_group_loaded(&mut self, name: &str) -> Option<&ActionGroup> {
        if self.groups.contains_key(name) {
            return self.groups.get(name);
        }

        let filepath = self.groups_dir.join(format!("{}.json", name));
        if filepath.exists() {
            if let Ok(content) = fs::read_to_string(&filepath) {
                if let Ok(data) = serde_json::from_str::<serde_json::Value>(&content) {
                    if let Ok(group) = ActionGroup::from_dict(&data) {
                        if group.validate().is_ok() {
                            self.groups.insert(group.name.clone(), group);
                            return self.groups.get(name);
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
    local_manager: Option<&LocalActionGroupManager>,
    global_manager: &GlobalActionGroupManager,
) -> Option<ActionGroup> {
    if let Some(local) = local_manager {
        if let Some(group) = local.get_group(group_name) {
            return Some(group.clone());
        }
    }

    if let Some(group) = global_manager.get_group(group_name) {
        return Some(group.clone());
    }

    None
}

fn dirs_or_default() -> PathBuf {
    std::env::var("USERPROFILE")
        .map(PathBuf::from)
        .unwrap_or_else(|_| PathBuf::from("."))
}
