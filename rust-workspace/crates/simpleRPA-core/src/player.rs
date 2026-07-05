use crate::action_group::{GlobalActionGroupManager, LocalActionGroupManager};
use crate::actions::{Action, ActionType};
use std::sync::{
    atomic::{AtomicBool, Ordering},
    Arc, Mutex,
};
use std::time::{Duration, Instant};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PlayerState {
    Idle,
    Playing,
    Paused,
    Stopped,
}

pub struct PlayerCallbackContext {
    pub action: Action,
    pub index: usize,
    pub success: bool,
    pub error: String,
}

pub struct Player {
    state: Arc<Mutex<PlayerState>>,
    actions: Vec<Action>,
    pub current_index: usize,
    pub current_repeat: i32,
    pub speed: f64,
    pub repeat_count: i32,
    pub infinite_loop: bool,
    pub timeout_seconds: f64,
    window_offset: Option<(i32, i32)>,
    window_title: String,
    window_hwnd: i64,
    window_run_mode: String,
    stop_flag: Arc<AtomicBool>,
    pause_event: Arc<Mutex<bool>>,
    local_group_manager: Option<LocalActionGroupManager>,

    on_action_start: Option<Box<dyn Fn(&Action, usize) + Send>>,
    on_action_end: Option<Box<dyn Fn(&Action, usize, bool) + Send>>,
    on_state_changed: Option<Box<dyn Fn(PlayerState) + Send>>,
    on_progress: Option<Box<dyn Fn(f64, usize, i32) + Send>>,
    on_error: Option<Box<dyn Fn(&Action, usize, &str) + Send>>,
    on_finished: Option<Box<dyn Fn(bool) + Send>>,
    on_window_error: Option<Box<dyn Fn(&Action, usize, &str) + Send>>,
}

impl Player {
    pub fn new() -> Self {
        Self {
            state: Arc::new(Mutex::new(PlayerState::Idle)),
            actions: Vec::new(),
            current_index: 0,
            current_repeat: 0,
            speed: 1.0,
            repeat_count: 1,
            infinite_loop: false,
            timeout_seconds: 0.0,
            window_offset: None,
            window_title: String::new(),
            window_hwnd: 0,
            window_run_mode: "normal".into(),
            stop_flag: Arc::new(AtomicBool::new(false)),
            pause_event: Arc::new(Mutex::new(true)),
            local_group_manager: None,
            on_action_start: None,
            on_action_end: None,
            on_state_changed: None,
            on_progress: None,
            on_error: None,
            on_finished: None,
            on_window_error: None,
        }
    }

    pub fn state(&self) -> PlayerState {
        *self.state.lock().unwrap()
    }

    pub fn set_state(&self, state: PlayerState) {
        *self.state.lock().unwrap() = state;
    }

    pub fn set_actions(&mut self, actions: Vec<Action>) {
        if self.state() != PlayerState::Idle {
            return;
        }
        self.actions = actions;
    }

    pub fn set_speed(&mut self, speed: f64) {
        self.speed = speed.clamp(0.1, 10.0);
    }

    pub fn set_repeat_count(&mut self, count: i32) {
        self.repeat_count = count.max(1);
    }

    pub fn set_infinite_loop(&mut self, enabled: bool) {
        self.infinite_loop = enabled;
    }

    pub fn set_timeout(&mut self, seconds: f64) {
        self.timeout_seconds = seconds.max(0.0);
    }

    pub fn set_window_offset(&mut self, offset: Option<(i32, i32)>) {
        self.window_offset = offset;
    }

    pub fn set_window_title(&mut self, title: &str) {
        self.window_title = title.to_string();
    }

    pub fn set_window_hwnd(&mut self, hwnd: i64) {
        self.window_hwnd = hwnd;
    }

    pub fn set_window_run_mode(&mut self, mode: &str) {
        let allowed = [
            "normal",
            "offscreen",
            "hidden_taskbar",
            "offscreen_hidden_taskbar",
        ];
        if allowed.contains(&mode) {
            self.window_run_mode = mode.to_string();
        }
    }

    pub fn set_local_group_manager(&mut self, manager: LocalActionGroupManager) {
        self.local_group_manager = Some(manager);
    }

    pub fn get_local_group_manager(&self) -> Option<&LocalActionGroupManager> {
        self.local_group_manager.as_ref()
    }

    pub fn action_count(&self) -> usize {
        self.actions.len()
    }

    pub fn set_on_action_start<F: Fn(&Action, usize) + Send + 'static>(&mut self, f: F) {
        self.on_action_start = Some(Box::new(f));
    }

    pub fn set_on_action_end<F: Fn(&Action, usize, bool) + Send + 'static>(&mut self, f: F) {
        self.on_action_end = Some(Box::new(f));
    }

    pub fn set_on_state_changed<F: Fn(PlayerState) + Send + 'static>(&mut self, f: F) {
        self.on_state_changed = Some(Box::new(f));
    }

    pub fn set_on_progress<F: Fn(f64, usize, i32) + Send + 'static>(&mut self, f: F) {
        self.on_progress = Some(Box::new(f));
    }

    pub fn set_on_error<F: Fn(&Action, usize, &str) + Send + 'static>(&mut self, f: F) {
        self.on_error = Some(Box::new(f));
    }

    pub fn set_on_finished<F: Fn(bool) + Send + 'static>(&mut self, f: F) {
        self.on_finished = Some(Box::new(f));
    }

    pub fn set_on_window_error<F: Fn(&Action, usize, &str) + Send + 'static>(&mut self, f: F) {
        self.on_window_error = Some(Box::new(f));
    }

    fn emit_state_changed(&self, state: PlayerState) {
        if let Some(ref f) = self.on_state_changed {
            f(state);
        }
    }

    pub fn play(&mut self) {
        if self.state() == PlayerState::Playing {
            return;
        }
        if self.actions.is_empty() {
            return;
        }

        if self.state() == PlayerState::Paused {
            self.set_state(PlayerState::Playing);
            *self.pause_event.lock().unwrap() = true;
            self.emit_state_changed(PlayerState::Playing);
            return;
        }

        self.stop_flag.store(false, Ordering::SeqCst);
        *self.pause_event.lock().unwrap() = true;
        self.set_state(PlayerState::Playing);
        self.emit_state_changed(PlayerState::Playing);

        let window_utils = crate::window_utils::WindowUtils::new();
        let restore_taskbar_state = if self.window_hwnd != 0
            && matches!(
                self.window_run_mode.as_str(),
                "hidden_taskbar" | "offscreen_hidden_taskbar"
            ) {
            window_utils.set_window_taskbar_visibility(self.window_hwnd, false)
        } else {
            None
        };
        let restore_placement = if self.window_hwnd != 0
            && matches!(
                self.window_run_mode.as_str(),
                "offscreen" | "offscreen_hidden_taskbar"
            ) {
            window_utils.move_window_offscreen(self.window_hwnd)
        } else {
            None
        };
        let restore_hwnd = self.window_hwnd;
        let mut actions = self.actions.clone();
        let force_background = self.window_run_mode != "normal";
        if self.window_hwnd != 0 {
            for action in &mut actions {
                action.params.insert(
                    "_runtime_window_hwnd".into(),
                    serde_json::json!(self.window_hwnd),
                );
                if force_background {
                    action.background_mode = true;
                }
            }
        }
        let speed = self.speed;
        let repeat_count = self.repeat_count;
        let infinite_loop = self.infinite_loop;
        let timeout_seconds = self.timeout_seconds;
        let window_offset = self.window_offset;
        let runtime_hwnd = self.window_hwnd;
        let local_group_manager = self.local_group_manager.clone();
        let stop_flag = self.stop_flag.clone();
        let pause_event = self.pause_event.clone();
        let state = self.state.clone();
        let on_action_start = self.on_action_start.take();
        let on_action_end = self.on_action_end.take();
        let on_error = self.on_error.take();
        let on_progress = self.on_progress.take();
        let on_finished = self.on_finished.take();
        let on_state_changed = self.on_state_changed.take();
        let _on_window_error = self.on_window_error.take();

        std::thread::spawn(move || {
            let finish = |success: bool| {
                if let Some(ref taskbar_state) = restore_taskbar_state {
                    let _ = crate::window_utils::WindowUtils::new()
                        .restore_window_taskbar_visibility(restore_hwnd, taskbar_state);
                }
                if let Some(ref placement) = restore_placement {
                    let _ = crate::window_utils::WindowUtils::new()
                        .restore_window_placement(restore_hwnd, placement);
                }
                *state.lock().unwrap() = PlayerState::Idle;
                if let Some(ref f) = on_state_changed {
                    f(PlayerState::Idle);
                }
                if let Some(ref f) = on_finished {
                    f(success);
                }
            };
            let start_time = Instant::now();
            let mut repeat_count_actual = 0;

            loop {
                if stop_flag.load(Ordering::SeqCst) {
                    finish(false);
                    return;
                }

                if timeout_seconds > 0.0 {
                    let elapsed = start_time.elapsed().as_secs_f64();
                    if elapsed >= timeout_seconds {
                        finish(false);
                        return;
                    }
                }

                if !infinite_loop && repeat_count_actual >= repeat_count {
                    break;
                }

                for (i, action) in actions.iter().enumerate() {
                    if stop_flag.load(Ordering::SeqCst) {
                        finish(false);
                        return;
                    }

                    let _ = *pause_event.lock().unwrap();
                    while !*pause_event.lock().unwrap() {
                        std::thread::sleep(Duration::from_millis(50));
                        if stop_flag.load(Ordering::SeqCst) {
                            finish(false);
                            return;
                        }
                    }

                    let adjusted_delay_before = action.delay_before / speed;
                    if adjusted_delay_before > 0.0 {
                        let end = Instant::now() + Duration::from_secs_f64(adjusted_delay_before);
                        while Instant::now() < end {
                            if stop_flag.load(Ordering::SeqCst) {
                                finish(false);
                                return;
                            }
                            std::thread::sleep(Duration::from_millis(50));
                        }
                    }

                    if let Some(ref f) = on_action_start {
                        f(action, i);
                    }

                    let mut visited_groups = std::collections::HashSet::new();
                    let success = execute_action_with_groups(
                        action,
                        window_offset,
                        &stop_flag,
                        local_group_manager.as_ref(),
                        speed,
                        force_background,
                        runtime_hwnd,
                        &mut visited_groups,
                    );
                    if !success {
                        if let Some(ref f) = on_error {
                            f(action, i, "执行失败");
                        }
                    }

                    if let Some(ref f) = on_action_end {
                        f(action, i, success);
                    }

                    if let Some(ref f) = on_progress {
                        f(-1.0, i, repeat_count_actual);
                    }

                    let adjusted_delay_after = action.delay_after / speed;
                    if adjusted_delay_after > 0.0 {
                        std::thread::sleep(Duration::from_secs_f64(adjusted_delay_after));
                    }
                }

                repeat_count_actual += 1;
            }

            finish(true);
        });
    }

    pub fn stop(&self) {
        if self.state() == PlayerState::Playing || self.state() == PlayerState::Paused {
            self.stop_flag.store(true, Ordering::SeqCst);
            *self.pause_event.lock().unwrap() = true;
            self.set_state(PlayerState::Stopped);
            self.emit_state_changed(PlayerState::Stopped);
        }
    }

    pub fn toggle_pause(&self) -> PlayerState {
        let current = self.state();
        if current == PlayerState::Playing {
            self.set_state(PlayerState::Paused);
            *self.pause_event.lock().unwrap() = false;
            self.emit_state_changed(PlayerState::Paused);
        } else if current == PlayerState::Paused {
            self.set_state(PlayerState::Playing);
            *self.pause_event.lock().unwrap() = true;
            self.emit_state_changed(PlayerState::Playing);
        }
        self.state()
    }

    pub fn execute_single_action(
        &mut self,
        index: usize,
        window_offset: Option<(i32, i32)>,
    ) -> bool {
        if index >= self.actions.len() {
            return false;
        }

        self.stop_flag.store(false, Ordering::SeqCst);
        *self.pause_event.lock().unwrap() = true;
        self.current_index = index;
        self.set_state(PlayerState::Playing);

        let mut action = self.actions[index].clone();
        if self.window_hwnd != 0 {
            action.params.insert(
                "_runtime_window_hwnd".into(),
                serde_json::json!(self.window_hwnd),
            );
            if self.window_run_mode != "normal" {
                action.background_mode = true;
            }
        }
        let mut visited_groups = std::collections::HashSet::new();
        let success = execute_action_with_groups(
            &action,
            window_offset.or(self.window_offset),
            &self.stop_flag,
            self.local_group_manager.as_ref(),
            self.speed,
            self.window_run_mode != "normal",
            self.window_hwnd,
            &mut visited_groups,
        );

        self.set_state(PlayerState::Idle);
        if let Some(ref f) = self.on_finished {
            f(success);
        }

        success
    }
}

fn sleep_with_stop(seconds: f64, stop_flag: &Arc<AtomicBool>) -> bool {
    if seconds <= 0.0 {
        return true;
    }

    let end = Instant::now() + Duration::from_secs_f64(seconds);
    while Instant::now() < end {
        if stop_flag.load(Ordering::SeqCst) {
            return false;
        }
        std::thread::sleep(Duration::from_millis(50));
    }
    true
}

fn execute_action_with_groups(
    action: &Action,
    window_offset: Option<(i32, i32)>,
    stop_flag: &Arc<AtomicBool>,
    local_group_manager: Option<&LocalActionGroupManager>,
    speed: f64,
    inherited_background: bool,
    runtime_hwnd: i64,
    visited_groups: &mut std::collections::HashSet<String>,
) -> bool {
    if action.action_type != ActionType::ActionGroupRef {
        return execute_action(action, window_offset, stop_flag);
    }

    let group_name = action.param_str("group_name");
    if group_name.is_empty() || visited_groups.contains(&group_name) {
        return false;
    }

    let group = local_group_manager
        .and_then(|manager| manager.get_group(&group_name).cloned())
        .or_else(|| GlobalActionGroupManager::new().get_group(&group_name).cloned());
    let Some(group) = group else {
        return false;
    };

    visited_groups.insert(group_name.clone());
    let speed = speed.max(0.1);
    let next_background = inherited_background || action.background_mode;

    for group_action in &group.actions {
        if stop_flag.load(Ordering::SeqCst) {
            visited_groups.remove(&group_name);
            return false;
        }

        if !sleep_with_stop(group_action.delay_before / speed, stop_flag) {
            visited_groups.remove(&group_name);
            return false;
        }

        let mut child = group_action.clone();
        if runtime_hwnd != 0 {
            child.params.insert(
                "_runtime_window_hwnd".into(),
                serde_json::json!(runtime_hwnd),
            );
        }
        if next_background {
            child.background_mode = true;
        }

        if !execute_action_with_groups(
            &child,
            window_offset,
            stop_flag,
            local_group_manager,
            speed,
            next_background,
            runtime_hwnd,
            visited_groups,
        ) {
            visited_groups.remove(&group_name);
            return false;
        }

        if !sleep_with_stop(group_action.delay_after / speed, stop_flag) {
            visited_groups.remove(&group_name);
            return false;
        }
    }

    visited_groups.remove(&group_name);
    true
}

fn execute_action(
    action: &Action,
    window_offset: Option<(i32, i32)>,
    stop_flag: &Arc<AtomicBool>,
) -> bool {
    let (x, y) = if action.use_relative_coords {
        if let Some(offset) = window_offset {
            (
                action.param_i32("x") + offset.0,
                action.param_i32("y") + offset.1,
            )
        } else {
            (action.param_i32("x"), action.param_i32("y"))
        }
    } else {
        (action.param_i32("x"), action.param_i32("y"))
    };

    match action.action_type {
        ActionType::Wait => {
            let seconds = action.param_f64("seconds");
            let end = Instant::now() + Duration::from_secs_f64(seconds);
            while Instant::now() < end {
                if stop_flag.load(Ordering::SeqCst) {
                    return false;
                }
                std::thread::sleep(Duration::from_millis(50));
            }
            true
        }
        ActionType::MouseMove => {
            let duration = action.param_f64("duration");
            let _ = rdev::simulate(&rdev::EventType::MouseMove {
                x: x as f64,
                y: y as f64,
            });
            if duration > 0.0 {
                std::thread::sleep(Duration::from_secs_f64(duration));
            }
            true
        }
        ActionType::MouseClick => {
            let _ = rdev::simulate(&rdev::EventType::MouseMove {
                x: x as f64,
                y: y as f64,
            });
            std::thread::sleep(Duration::from_millis(50));
            let _ = rdev::simulate(&rdev::EventType::ButtonPress(rdev::Button::Left));
            let _ = rdev::simulate(&rdev::EventType::ButtonRelease(rdev::Button::Left));
            true
        }
        ActionType::MouseDoubleClick => {
            let _ = rdev::simulate(&rdev::EventType::MouseMove {
                x: x as f64,
                y: y as f64,
            });
            std::thread::sleep(Duration::from_millis(50));
            let _ = rdev::simulate(&rdev::EventType::ButtonPress(rdev::Button::Left));
            let _ = rdev::simulate(&rdev::EventType::ButtonRelease(rdev::Button::Left));
            std::thread::sleep(Duration::from_millis(50));
            let _ = rdev::simulate(&rdev::EventType::ButtonPress(rdev::Button::Left));
            let _ = rdev::simulate(&rdev::EventType::ButtonRelease(rdev::Button::Left));
            true
        }
        ActionType::MouseRightClick => {
            let _ = rdev::simulate(&rdev::EventType::MouseMove {
                x: x as f64,
                y: y as f64,
            });
            std::thread::sleep(Duration::from_millis(50));
            let _ = rdev::simulate(&rdev::EventType::ButtonPress(rdev::Button::Right));
            let _ = rdev::simulate(&rdev::EventType::ButtonRelease(rdev::Button::Right));
            true
        }
        ActionType::MouseScroll => {
            let clicks = action.param_i32("clicks");
            let _ = rdev::simulate(&rdev::EventType::MouseMove {
                x: x as f64,
                y: y as f64,
            });
            let _ = rdev::simulate(&rdev::EventType::Wheel {
                delta_x: 0,
                delta_y: clicks as i64,
            });
            true
        }
        ActionType::KeyPress => {
            let key_str = action.param_str("key");
            if let Some(key) = parse_key(&key_str) {
                let _ = rdev::simulate(&rdev::EventType::KeyPress(key));
                let _ = rdev::simulate(&rdev::EventType::KeyRelease(key));
            }
            true
        }
        ActionType::KeyType => {
            let text = action.param_str("text");
            let interval = action.param_f64("interval");
            for ch in text.chars() {
                if stop_flag.load(Ordering::SeqCst) {
                    return false;
                }
                if let Some(key) = char_to_key(ch) {
                    let _ = rdev::simulate(&rdev::EventType::KeyPress(key));
                    let _ = rdev::simulate(&rdev::EventType::KeyRelease(key));
                }
                if interval > 0.0 {
                    std::thread::sleep(Duration::from_secs_f64(interval));
                }
            }
            true
        }
        ActionType::Hotkey => {
            let keys = action.param_str_slice("keys");
            let mut rdev_keys = Vec::new();
            for k in &keys {
                if let Some(key) = parse_key(k) {
                    rdev_keys.push(key);
                }
            }
            for key in &rdev_keys {
                let _ = rdev::simulate(&rdev::EventType::KeyPress(*key));
            }
            for key in rdev_keys.iter().rev() {
                let _ = rdev::simulate(&rdev::EventType::KeyRelease(*key));
            }
            true
        }
        ActionType::Screenshot => {
            let _filename = action.param_str("filename").if_empty("screenshot.png");
            true
        }
        ActionType::ImageClick | ActionType::ImageWaitClick | ActionType::ImageCheck => {
            let image_path = action.param_str("image_path");
            let confidence = action.param_f64("confidence");
            let timeout = action.param_f64("timeout");

            if image_path.is_empty() || !std::path::Path::new(&image_path).exists() {
                return false;
            }

            let start = Instant::now();
            loop {
                if let Ok(img) = image::open(&image_path) {
                    if let Ok(screen) = capture_screen() {
                        if let Some(pos) = find_image_on_screen(&img, &screen, confidence) {
                            let center_x = pos.0 + pos.2 / 2;
                            let center_y = pos.1 + pos.3 / 2;
                            let _ = rdev::simulate(&rdev::EventType::MouseMove {
                                x: center_x as f64,
                                y: center_y as f64,
                            });
                            std::thread::sleep(Duration::from_millis(50));
                            let _ =
                                rdev::simulate(&rdev::EventType::ButtonPress(rdev::Button::Left));
                            let _ =
                                rdev::simulate(&rdev::EventType::ButtonRelease(rdev::Button::Left));
                            return true;
                        }
                    }
                }

                if action.action_type != ActionType::ImageWaitClick {
                    return false;
                }

                if start.elapsed().as_secs_f64() > timeout {
                    return false;
                }

                if stop_flag.load(Ordering::SeqCst) {
                    return false;
                }

                std::thread::sleep(Duration::from_millis(500));
            }
        }
        ActionType::MouseMoveRelative | ActionType::MouseClickRelative => {
            if action.background_mode {
                let clicker = crate::background_click::BackgroundClicker::new(
                    action.window_title.as_deref(),
                    Some(
                        action
                            .params
                            .get("_runtime_window_hwnd")
                            .and_then(|v| v.as_i64())
                            .unwrap_or(0),
                    ),
                );
                if let Some(clicker) = clicker {
                    if action.action_type == ActionType::MouseClickRelative {
                        let button = action.param_str("button");
                        let result = clicker.click(x, y, &button, true);
                        return result.success;
                    } else {
                        let result = clicker.move_mouse(x, y, true);
                        return result.success;
                    }
                }
            }
            let _ = rdev::simulate(&rdev::EventType::MouseMove {
                x: x as f64,
                y: y as f64,
            });
            if action.action_type == ActionType::MouseClickRelative {
                let _ = rdev::simulate(&rdev::EventType::ButtonPress(rdev::Button::Left));
                let _ = rdev::simulate(&rdev::EventType::ButtonRelease(rdev::Button::Left));
            }
            true
        }
        ActionType::ActionGroupRef => {
            let group_name = action.param_str("group_name");
            let _ = group_name;
            true
        }
        ActionType::MouseDrag => {
            let start_x = action.param_i32("start_x") as f64;
            let start_y = action.param_i32("start_y") as f64;
            let end_x = action.param_i32("end_x") as f64;
            let end_y = action.param_i32("end_y") as f64;
            let _ = rdev::simulate(&rdev::EventType::MouseMove {
                x: start_x,
                y: start_y,
            });
            std::thread::sleep(Duration::from_millis(50));
            let _ = rdev::simulate(&rdev::EventType::ButtonPress(rdev::Button::Left));
            let _ = rdev::simulate(&rdev::EventType::MouseMove { x: end_x, y: end_y });
            std::thread::sleep(Duration::from_millis(50));
            let _ = rdev::simulate(&rdev::EventType::ButtonRelease(rdev::Button::Left));
            true
        }
    }
}

fn capture_screen() -> Result<Vec<u8>, String> {
    Ok(Vec::new())
}

fn find_image_on_screen(
    _needle: &image::DynamicImage,
    _haystack: &[u8],
    _confidence: f64,
) -> Option<(i32, i32, i32, i32)> {
    None
}

fn parse_key(key_str: &str) -> Option<rdev::Key> {
    match key_str.to_lowercase().as_str() {
        "enter" | "return" => Some(rdev::Key::Return),
        "tab" => Some(rdev::Key::Tab),
        "space" => Some(rdev::Key::Space),
        "backspace" => Some(rdev::Key::Backspace),
        "delete" | "del" => Some(rdev::Key::Delete),
        "escape" | "esc" => Some(rdev::Key::Escape),
        "up" => Some(rdev::Key::UpArrow),
        "down" => Some(rdev::Key::DownArrow),
        "left" => Some(rdev::Key::LeftArrow),
        "right" => Some(rdev::Key::RightArrow),
        "home" => Some(rdev::Key::Home),
        "end" => Some(rdev::Key::End),
        "pageup" => Some(rdev::Key::PageUp),
        "pagedown" => Some(rdev::Key::PageDown),
        "capslock" => Some(rdev::Key::CapsLock),
        "f1" => Some(rdev::Key::F1),
        "f2" => Some(rdev::Key::F2),
        "f3" => Some(rdev::Key::F3),
        "f4" => Some(rdev::Key::F4),
        "f5" => Some(rdev::Key::F5),
        "f6" => Some(rdev::Key::F6),
        "f7" => Some(rdev::Key::F7),
        "f8" => Some(rdev::Key::F8),
        "f9" => Some(rdev::Key::F9),
        "f10" => Some(rdev::Key::F10),
        "f11" => Some(rdev::Key::F11),
        "f12" => Some(rdev::Key::F12),
        "ctrl" | "control" => Some(rdev::Key::ControlLeft),
        "alt" => Some(rdev::Key::Alt),
        "shift" => Some(rdev::Key::ShiftLeft),
        "win" | "cmd" | "super" => Some(rdev::Key::MetaLeft),
        _ => {
            if key_str.len() == 1 {
                key_str.chars().next().and_then(char_to_key)
            } else {
                None
            }
        }
    }
}

fn char_to_key(ch: char) -> Option<rdev::Key> {
    match ch {
        'a'..='z' => Some(rdev::Key::KeyA),
        'A' => Some(rdev::Key::KeyA),
        '0' => Some(rdev::Key::Num0),
        '1' => Some(rdev::Key::Num1),
        '2' => Some(rdev::Key::Num2),
        '3' => Some(rdev::Key::Num3),
        '4' => Some(rdev::Key::Num4),
        '5' => Some(rdev::Key::Num5),
        '6' => Some(rdev::Key::Num6),
        '7' => Some(rdev::Key::Num7),
        '8' => Some(rdev::Key::Num8),
        '9' => Some(rdev::Key::Num9),
        _ => None,
    }
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
