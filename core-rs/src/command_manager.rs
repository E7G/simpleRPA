use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::{Arc, Mutex};

use crate::actions::Action;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LaunchCommand {
    pub id: String,
    pub name: String,
    pub command: String,
    #[serde(default)]
    pub window_title_pattern: String,
    #[serde(default)]
    pub description: String,
    #[serde(default)]
    pub created_at: String,
    #[serde(default)]
    pub last_used: String,
    #[serde(default)]
    pub use_count: i32,
    #[serde(default)]
    pub delay_after_launch: f64,
}

pub struct CommandManager {
    commands: HashMap<String, LaunchCommand>,
    config_path: std::path::PathBuf,
}

impl CommandManager {
    pub fn new() -> Self {
        let config_path = dirs::home_dir()
            .unwrap_or_else(|| std::path::PathBuf::from("."))
            .join(".simpleRPA")
            .join("launch_commands.json");
        let _ = std::fs::create_dir_all(config_path.parent().unwrap());
        let mut mgr = Self {
            commands: HashMap::new(),
            config_path,
        };
        mgr.load();
        mgr
    }

    pub fn load(&mut self) -> bool {
        if !self.config_path.exists() {
            return false;
        }
        if let Ok(content) = std::fs::read_to_string(&self.config_path) {
            if let Ok(data) = serde_json::from_str::<serde_json::Value>(&content) {
                if let Some(cmds) = data.get("commands").and_then(|v| v.as_object()) {
                    for (id, cmd_data) in cmds {
                        if let Ok(cmd) = serde_json::from_value::<LaunchCommand>(cmd_data.clone()) {
                            self.commands.insert(id.clone(), cmd);
                        }
                    }
                }
                return true;
            }
        }
        false
    }

    pub fn save(&self) -> bool {
        let mut map = serde_json::Map::new();
        for (id, cmd) in &self.commands {
            if let Ok(val) = serde_json::to_value(cmd) {
                map.insert(id.clone(), val);
            }
        }
        let data = serde_json::json!({ "commands": map });
        if let Ok(content) = serde_json::to_string_pretty(&data) {
            std::fs::write(&self.config_path, content).is_ok()
        } else {
            false
        }
    }

    pub fn add_command(
        &mut self,
        name: &str,
        command: &str,
        window_title_pattern: &str,
        description: &str,
        delay_after_launch: f64,
    ) -> LaunchCommand {
        use uuid::Uuid;
        let id = Uuid::new_v4().to_string()[..8].to_string();
        let now = chrono::Utc::now().to_rfc3339();
        let cmd = LaunchCommand {
            id: id.clone(),
            name: name.to_string(),
            command: command.to_string(),
            window_title_pattern: window_title_pattern.to_string(),
            description: description.to_string(),
            created_at: now.clone(),
            last_used: now,
            use_count: 0,
            delay_after_launch,
        };
        self.commands.insert(id.clone(), cmd.clone());
        self.save();
        cmd
    }

    pub fn get_command(&self, id: &str) -> Option<&LaunchCommand> {
        self.commands.get(id)
    }

    pub fn get_all_commands(&self) -> Vec<&LaunchCommand> {
        self.commands.values().collect()
    }

    pub fn delete_command(&mut self, id: &str) -> bool {
        if self.commands.remove(id).is_some() {
            self.save();
            true
        } else {
            false
        }
    }

    pub fn execute_command(&self, id: &str) -> Result<(), String> {
        let cmd = self.commands.get(id).ok_or("命令不存在")?;
        #[cfg(target_os = "windows")]
        {
            use std::process::Command;
            Command::new("cmd")
                .args(["/C", &cmd.command])
                .spawn()
                .map_err(|e| format!("执行失败: {}", e))?;
        }
        #[cfg(not(target_os = "windows"))]
        {
            use std::process::Command;
            Command::new("sh")
                .args(["-c", &cmd.command])
                .spawn()
                .map_err(|e| format!("执行失败: {}", e))?;
        }
        Ok(())
    }
}
