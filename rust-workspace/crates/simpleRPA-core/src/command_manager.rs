use std::collections::HashMap;

#[derive(Debug, Clone)]
pub struct LaunchCommand {
    pub id: String,
    pub name: String,
    pub command: String,
    pub window_title_pattern: String,
    pub description: String,
    pub created_at: String,
    pub last_used: String,
    pub use_count: i32,
    pub delay_after_launch: f64,
}

impl LaunchCommand {
    pub fn to_dict(&self) -> serde_json::Value {
        serde_json::json!({
            "id": self.id,
            "name": self.name,
            "command": self.command,
            "window_title_pattern": self.window_title_pattern,
            "description": self.description,
            "created_at": self.created_at,
            "last_used": self.last_used,
            "use_count": self.use_count,
            "delay_after_launch": self.delay_after_launch,
        })
    }

    pub fn from_dict(data: &serde_json::Value) -> Option<Self> {
        Some(Self {
            id: data.get("id")?.as_str()?.to_string(),
            name: data.get("name")?.as_str()?.to_string(),
            command: data.get("command")?.as_str()?.to_string(),
            window_title_pattern: data
                .get("window_title_pattern")
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .to_string(),
            description: data
                .get("description")
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .to_string(),
            created_at: data
                .get("created_at")
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .to_string(),
            last_used: data
                .get("last_used")
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .to_string(),
            use_count: data.get("use_count").and_then(|v| v.as_i64()).unwrap_or(0) as i32,
            delay_after_launch: data
                .get("delay_after_launch")
                .and_then(|v| v.as_f64())
                .unwrap_or(0.0),
        })
    }
}

pub struct CommandManager {
    commands: HashMap<String, LaunchCommand>,
    config_path: std::path::PathBuf,
}

impl CommandManager {
    pub fn new() -> Self {
        let config_dir = dirs::home_dir()
            .unwrap_or_else(|| std::path::PathBuf::from("."))
            .join(".simpleRPA");
        let _ = std::fs::create_dir_all(&config_dir);
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

        let content = match std::fs::read_to_string(&self.config_path) {
            Ok(c) => c,
            Err(_) => return false,
        };

        let data: serde_json::Value = match serde_json::from_str(&content) {
            Ok(d) => d,
            Err(_) => return false,
        };

        if let Some(obj) = data.get("commands").and_then(|v| v.as_object()) {
            for (id, cmd_data) in obj {
                if let Some(cmd) = LaunchCommand::from_dict(cmd_data) {
                    self.commands.insert(id.clone(), cmd);
                }
            }
        }

        true
    }

    pub fn save(&self) -> bool {
        let data = serde_json::json!({
            "commands": self.commands.iter()
                .map(|(id, cmd)| (id.clone(), cmd.to_dict()))
                .collect::<serde_json::Map<String, serde_json::Value>>(),
        });

        let json = match serde_json::to_string_pretty(&data) {
            Ok(j) => j,
            Err(_) => return false,
        };

        std::fs::write(&self.config_path, json).is_ok()
    }

    pub fn add_command(
        &mut self,
        name: &str,
        command: &str,
        window_title_pattern: &str,
        description: &str,
        delay_after_launch: f64,
    ) -> LaunchCommand {
        let cmd_id = uuid::Uuid::new_v4().to_string()[..8].to_string();
        let now = chrono::Utc::now().to_rfc3339();

        let launch_cmd = LaunchCommand {
            id: cmd_id.clone(),
            name: name.to_string(),
            command: command.to_string(),
            window_title_pattern: window_title_pattern.to_string(),
            description: description.to_string(),
            created_at: now.clone(),
            last_used: now,
            use_count: 0,
            delay_after_launch,
        };

        self.commands.insert(cmd_id, launch_cmd.clone());
        self.save();
        launch_cmd
    }

    pub fn update_command(&mut self, cmd_id: &str, updates: &serde_json::Value) -> bool {
        if let Some(cmd) = self.commands.get_mut(cmd_id) {
            if let Some(name) = updates.get("name").and_then(|v| v.as_str()) {
                cmd.name = name.to_string();
            }
            if let Some(command) = updates.get("command").and_then(|v| v.as_str()) {
                cmd.command = command.to_string();
            }
            if let Some(pattern) = updates.get("window_title_pattern").and_then(|v| v.as_str()) {
                cmd.window_title_pattern = pattern.to_string();
            }
            if let Some(desc) = updates.get("description").and_then(|v| v.as_str()) {
                cmd.description = desc.to_string();
            }
            if let Some(delay) = updates.get("delay_after_launch").and_then(|v| v.as_f64()) {
                cmd.delay_after_launch = delay;
            }
            self.save();
            true
        } else {
            false
        }
    }

    pub fn delete_command(&mut self, cmd_id: &str) -> bool {
        if self.commands.remove(cmd_id).is_some() {
            self.save();
            true
        } else {
            false
        }
    }

    pub fn get_command(&self, cmd_id: &str) -> Option<&LaunchCommand> {
        self.commands.get(cmd_id)
    }

    pub fn get_all_commands(&self) -> Vec<&LaunchCommand> {
        self.commands.values().collect()
    }

    pub fn execute_command(&mut self, cmd_id: &str) -> Result<String, String> {
        let (command, delay_after_launch) = {
            let cmd = self.commands.get(cmd_id).ok_or("命令不存在")?;
            (cmd.command.clone(), cmd.delay_after_launch)
        };

        #[cfg(target_os = "windows")]
        {
            use std::process::Command;
            Command::new("cmd")
                .args(["/C", &command])
                .spawn()
                .map_err(|e| format!("执行失败: {}", e))?;
        }

        if delay_after_launch.is_finite() && delay_after_launch > 0.0 {
            std::thread::sleep(std::time::Duration::from_secs_f64(delay_after_launch));
        }

        if let Some(cmd) = self.commands.get_mut(cmd_id) {
            cmd.last_used = chrono::Utc::now().to_rfc3339();
            cmd.use_count += 1;
            self.save();
        }

        Ok("命令执行成功".into())
    }

    pub fn check_and_launch(&mut self, cmd_id: &str) -> (bool, String, bool) {
        let cmd = match self.commands.get(cmd_id) {
            Some(c) => c.clone(),
            None => return (false, "命令不存在".into(), false),
        };

        if !cmd.window_title_pattern.is_empty() && self.is_window_running(&cmd.window_title_pattern)
        {
            return (true, "窗口已在运行".into(), true);
        }

        match self.execute_command(cmd_id) {
            Ok(msg) => (true, msg, false),
            Err(msg) => (false, msg, false),
        }
    }

    fn is_window_running(&self, window_title_pattern: &str) -> bool {
        if window_title_pattern.is_empty() {
            return false;
        }

        let utils = crate::window_utils::WindowUtils::new();
        let windows = utils.get_all_windows();
        windows.iter().any(|w| {
            w.title
                .to_lowercase()
                .contains(&window_title_pattern.to_lowercase())
        })
    }
}
