const GITHUB_REPO: &str = "toddming/simpleRPA";

pub struct UpdateChecker {
    current_version: String,
    github_repo: String,
}

pub struct UpdateInfo {
    pub available: bool,
    pub latest_version: String,
    pub download_url: String,
    pub release_notes: String,
}

impl UpdateChecker {
    pub fn new(current_version: &str) -> Self {
        Self {
            current_version: current_version.to_string(),
            github_repo: GITHUB_REPO.to_string(),
        }
    }

    pub fn check_for_update(&self) -> Option<UpdateInfo> {
        let url = format!(
            "https://api.github.com/repos/{}/releases/latest",
            self.github_repo
        );

        let client = reqwest::blocking::Client::new();
        let response = client
            .get(&url)
            .header("User-Agent", "simpleRPA-updater")
            .send()
            .ok()?;

        let body: serde_json::Value = response.json().ok()?;
        let tag_name = body.get("tag_name")?.as_str()?;
        let latest_version = tag_name.trim_start_matches('v').to_string();

        let available = Self::version_gt(&latest_version, &self.current_version);

        let download_url = body
            .get("assets")
            .and_then(|a| a.as_array())
            .and_then(|arr| arr.first())
            .and_then(|asset| asset.get("browser_download_url"))
            .and_then(|u| u.as_str())
            .unwrap_or("")
            .to_string();

        let release_notes = body
            .get("body")
            .and_then(|b| b.as_str())
            .unwrap_or("")
            .to_string();

        Some(UpdateInfo {
            available,
            latest_version,
            download_url,
            release_notes,
        })
    }

    pub fn check_for_update_async(&self) {
        let checker = Self {
            current_version: self.current_version.clone(),
            github_repo: self.github_repo.clone(),
        };

        std::thread::spawn(move || {
            if let Some(info) = checker.check_for_update() {
                if info.available {
                    crate::notification::show_notification(
                        "发现新版本",
                        &format!(
                            "新版本 {} 可用，当前版本: {}",
                            info.latest_version, checker.current_version
                        ),
                    );
                }
            }
        });
    }

    fn version_gt(a: &str, b: &str) -> bool {
        let a_parts: Vec<u32> = a.split('.').filter_map(|s| s.parse().ok()).collect();
        let b_parts: Vec<u32> = b.split('.').filter_map(|s| s.parse().ok()).collect();

        for i in 0..a_parts.len().max(b_parts.len()) {
            let a_val = a_parts.get(i).copied().unwrap_or(0);
            let b_val = b_parts.get(i).copied().unwrap_or(0);
            if a_val > b_val {
                return true;
            }
            if a_val < b_val {
                return false;
            }
        }
        false
    }
}
