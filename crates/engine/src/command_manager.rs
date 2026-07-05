use std::collections::HashMap;
use std::fs;
use std::path::PathBuf;
use serde::{Deserialize, Serialize};

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
    pub use_count: u64,
    #[serde(default)]
    pub delay_after_launch: f64,
}

pub struct CommandManager {
    commands: HashMap<String, LaunchCommand>,
    config_path: PathBuf,
}

impl CommandManager {
    pub fn new() -> Self {
        let config_dir = dirs_or_default().join(".simpleRPA");
        let _ = fs::create_dir_all(&config_dir);
        let config_path = config_dir.join("launch_commands.json");

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
        match fs::read_to_string(&self.config_path) {
            Ok(content) => {
                if let Ok(data) = serde_json::from_str::<serde_json::Value>(&content) {
                    if let Some(cmds) = data.get("commands").and_then(|v| v.as_object()) {
                        for (id, cmd_data) in cmds {
                            if let Ok(cmd) = serde_json::from_value::<LaunchCommand>(cmd_data.clone()) {
                                self.commands.insert(id.clone(), cmd);
                            }
                        }
                    }
                    true
                } else {
                    false
                }
            }
            Err(_) => false,
        }
    }

    pub fn save(&self) -> bool {
        let data = serde_json::json!({
            "commands": self.commands,
        });
        let json = serde_json::to_string_pretty(&data).unwrap_or_default();
        fs::write(&self.config_path, json).is_ok()
    }

    pub fn add_command(&mut self, name: &str, command: &str, window_title_pattern: &str, description: &str) -> LaunchCommand {
        let id = uuid::Uuid::new_v4().to_string()[..8].to_string();
        let now = chrono::Local::now().to_rfc3339();

        let cmd = LaunchCommand {
            id: id.clone(),
            name: name.to_string(),
            command: command.to_string(),
            window_title_pattern: window_title_pattern.to_string(),
            description: description.to_string(),
            created_at: now.clone(),
            last_used: now,
            use_count: 0,
            delay_after_launch: 0.0,
        };

        self.commands.insert(id.clone(), cmd.clone());
        self.save();
        cmd
    }

    pub fn delete_command(&mut self, id: &str) -> bool {
        if self.commands.remove(id).is_some() {
            self.save();
            true
        } else {
            false
        }
    }

    pub fn get_command(&self, id: &str) -> Option<&LaunchCommand> {
        self.commands.get(id)
    }

    pub fn get_all_commands(&self) -> Vec<&LaunchCommand> {
        self.commands.values().collect()
    }

    pub fn execute_command(&mut self, id: &str) -> Result<String, String> {
        let cmd = self.commands.get(id).ok_or("命令不存在")?;

        #[cfg(windows)]
        {
            use std::process::Command;
            let _ = Command::new("cmd")
                .args(["/C", &cmd.command])
                .spawn();
        }

        if let Some(cmd_mut) = self.commands.get_mut(id) {
            cmd_mut.last_used = chrono::Local::now().to_rfc3339();
            cmd_mut.use_count += 1;
        }
        self.save();

        Ok("命令执行成功".into())
    }

    pub fn check_and_launch(&mut self, id: &str) -> (bool, String, bool) {
        let cmd = match self.commands.get(id) {
            Some(c) => c.clone(),
            None => return (false, "命令不存在".into(), false),
        };

        if !cmd.window_title_pattern.is_empty() && is_window_running(&cmd.window_title_pattern) {
            return (true, "窗口已在运行".into(), true);
        }

        match self.execute_command(id) {
            Ok(msg) => (true, msg, false),
            Err(e) => (false, e, false),
        }
    }
}

fn is_window_running(pattern: &str) -> bool {
    #[cfg(windows)]
    {
        use simplerpa_winapi::window::WindowUtils;
        let utils = WindowUtils::new();
        let windows = utils.get_all_windows();
        windows.iter().any(|w| w.title.to_lowercase().contains(&pattern.to_lowercase()))
    }
    #[cfg(not(windows))]
    {
        false
    }
}

fn dirs_or_default() -> PathBuf {
    std::env::var("USERPROFILE")
        .map(PathBuf::from)
        .unwrap_or_else(|_| PathBuf::from("."))
}
