use std::collections::HashMap;
use std::sync::{Arc, atomic::{AtomicBool, Ordering}, Mutex};
use std::thread;
use std::time::{Duration, Instant};

use simplerpa_core::actions::{Action, ActionType};
use simplerpa_core::action_group::LocalActionGroupManager;
use simplerpa_core::config::Config;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PlayerState {
    Idle,
    Playing,
    Paused,
    Stopped,
}

pub struct Player {
    state: Arc<Mutex<PlayerState>>,
    actions: Vec<Action>,
    pub current_index: usize,
    pub current_repeat: usize,
    pub speed: f64,
    pub repeat_count: i32,
    pub infinite_loop: bool,
    pub timeout_seconds: f64,

    window_offset: Option<(i32, i32)>,
    window_title: String,
    window_hwnd: i64,
    window_run_mode: String,
    local_group_manager: Option<Arc<Mutex<LocalActionGroupManager>>>,

    stop_flag: Arc<AtomicBool>,
    pause_event: Arc<(std::sync::Condvar, std::sync::Mutex<bool>)>,
    start_time: Instant,
    thread_handle: Option<thread::JoinHandle<()>>,

    callbacks: HashMap<String, Vec<Box<dyn Fn(&str) + Send + Sync>>>,
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
            local_group_manager: None,
            stop_flag: Arc::new(AtomicBool::new(false)),
            pause_event: Arc::new((std::sync::Condvar::new(), std::sync::Mutex::new(true))),
            start_time: Instant::now(),
            thread_handle: None,
            callbacks: HashMap::new(),
        }
    }

    pub fn state(&self) -> PlayerState {
        *self.state.lock().unwrap()
    }

    pub fn set_actions(&mut self, actions: Vec<Action>) {
        if self.state() == PlayerState::Idle {
            self.actions = actions;
        }
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
        let allowed = ["normal", "offscreen", "hidden_taskbar", "offscreen_hidden_taskbar"];
        self.window_run_mode = if allowed.contains(&mode) { mode.to_string() } else { "normal".into() };
    }

    pub fn set_local_group_manager(&mut self, manager: LocalActionGroupManager) {
        self.local_group_manager = Some(Arc::new(Mutex::new(manager)));
    }

    pub fn play(&mut self) {
        if self.state() == PlayerState::Playing {
            return;
        }
        if self.actions.is_empty() {
            return;
        }

        if self.state() == PlayerState::Paused {
            let (cv, lock) = &*self.pause_event;
            let mut paused = lock.lock().unwrap();
            *paused = true;
            cv.notify_all();
            *self.state.lock().unwrap() = PlayerState::Playing;
            return;
        }

        self.stop_flag.store(false, Ordering::SeqCst);
        {
            let (cv, lock) = &*self.pause_event;
            let mut paused = lock.lock().unwrap();
            *paused = true;
            cv.notify_all();
        }
        *self.state.lock().unwrap() = PlayerState::Playing;
        self.start_time = Instant::now();

        let state = Arc::clone(&self.state);
        let stop_flag = Arc::clone(&self.stop_flag);
        let pause_event = Arc::clone(&self.pause_event);
        let actions = self.actions.clone();
        let speed = self.speed;
        let repeat_count = self.repeat_count;
        let infinite_loop = self.infinite_loop;
        let timeout_seconds = self.timeout_seconds;
        let start_time = self.start_time;

        self.thread_handle = Some(thread::spawn(move || {
            run_loop(state, stop_flag, pause_event, actions, speed, repeat_count, infinite_loop, timeout_seconds, start_time);
        }));
    }

    pub fn pause(&mut self) {
        if self.state() == PlayerState::Playing {
            let (cv, lock) = &*self.pause_event;
            let mut paused = lock.lock().unwrap();
            *paused = false;
            *self.state.lock().unwrap() = PlayerState::Paused;
        }
    }

    pub fn resume(&mut self) {
        if self.state() == PlayerState::Paused {
            self.play();
        }
    }

    pub fn toggle_pause(&mut self) -> PlayerState {
        match self.state() {
            PlayerState::Playing => {
                self.pause();
                self.state()
            }
            PlayerState::Paused => {
                self.resume();
                self.state()
            }
            other => other,
        }
    }

    pub fn stop(&mut self) {
        if matches!(self.state(), PlayerState::Playing | PlayerState::Paused) {
            self.stop_flag.store(true, Ordering::SeqCst);
            let (cv, lock) = &*self.pause_event;
            let paused = lock.lock().unwrap();
            cv.notify_all();
            *self.state.lock().unwrap() = PlayerState::Stopped;
        }
    }

    pub fn stop_and_wait(&mut self, timeout: Duration) -> bool {
        if matches!(self.state(), PlayerState::Playing | PlayerState::Paused) {
            self.stop_flag.store(true, Ordering::SeqCst);
            let (cv, lock) = &*self.pause_event;
            let _paused = lock.lock().unwrap();
            cv.notify_all();

            if let Some(handle) = self.thread_handle.take() {
                if handle.join().is_err() {
                    return false;
                }
            }
            *self.state.lock().unwrap() = PlayerState::Idle;
            true
        } else {
            true
        }
    }

    pub fn is_playing(&self) -> bool {
        self.state() == PlayerState::Playing
    }

    pub fn is_paused(&self) -> bool {
        self.state() == PlayerState::Paused
    }
}

fn run_loop(
    state: Arc<Mutex<PlayerState>>,
    stop_flag: Arc<AtomicBool>,
    pause_event: Arc<(std::sync::Condvar, std::sync::Mutex<bool>)>,
    actions: Vec<Action>,
    speed: f64,
    repeat_count: i32,
    infinite_loop: bool,
    timeout_seconds: f64,
    start_time: Instant,
) {
    let mut repeat = 0;

    loop {
        if stop_flag.load(Ordering::SeqCst) {
            break;
        }

        if timeout_seconds > 0.0 {
            if start_time.elapsed().as_secs_f64() >= timeout_seconds {
                break;
            }
        }

        if !infinite_loop && repeat >= repeat_count as usize {
            break;
        }

        for (i, action) in actions.iter().enumerate() {
            if stop_flag.load(Ordering::SeqCst) {
                break;
            }

            {
                let (cv, lock) = &*pause_event;
                let mut paused = lock.lock().unwrap();
                while !*paused {
                    if stop_flag.load(Ordering::SeqCst) {
                        break;
                    }
                    paused = cv.wait(paused).unwrap();
                }
                if stop_flag.load(Ordering::SeqCst) {
                    break;
                }
            }

            if timeout_seconds > 0.0 && start_time.elapsed().as_secs_f64() >= timeout_seconds {
                break;
            }

            if !action.check_condition(&HashMap::new()) {
                continue;
            }

            let delay_before = if speed > 0.0 { action.delay_before / speed } else { action.delay_before };
            if delay_before > 0.0 {
                interruptible_sleep(Duration::from_secs_f64(delay_before), &stop_flag);
            }

            if stop_flag.load(Ordering::SeqCst) {
                break;
            }

            let _ = execute_action(action);

            let delay_after = if speed > 0.0 { action.delay_after / speed } else { action.delay_after };
            if delay_after > 0.0 {
                interruptible_sleep(Duration::from_secs_f64(delay_after), &stop_flag);
            }
        }

        repeat += 1;
    }

    *state.lock().unwrap() = PlayerState::Idle;
}

fn interruptible_sleep(duration: Duration, stop_flag: &AtomicBool) {
    let end = Instant::now() + duration;
    while Instant::now() < end {
        if stop_flag.load(Ordering::SeqCst) {
            return;
        }
        let remaining = end.saturating_duration_since(Instant::now());
        let sleep_time = remaining.min(Duration::from_millis(50));
        if !sleep_time.is_zero() {
            thread::sleep(sleep_time);
        }
    }
}

fn execute_action(action: &Action) -> Result<(), String> {
    use simplerpa_winapi::input::InputSimulator;
    use simplerpa_winapi::background::BackgroundClicker;

    let simulator = InputSimulator::new();

    match action.action_type {
        ActionType::MouseClick => {
            let x = action.params.get("x").and_then(|v| v.as_i64()).unwrap_or(0) as i32;
            let y = action.params.get("y").and_then(|v| v.as_i64()).unwrap_or(0) as i32;
            let button = action.params.get("button").and_then(|v| v.as_str()).unwrap_or("left");

            if action.background_mode {
                let clicker = BackgroundClicker::new(Some(action.window_title.as_ref().map(|_| 0).unwrap_or(0)), action.window_title.as_deref());
                if clicker.is_available() {
                    let result = clicker.click(x, y, button, true);
                    if result.success { return Ok(()) }
                }
            }
            simulator.click(x, y, button);
            Ok(())
        }
        ActionType::MouseDoubleClick => {
            let x = action.params.get("x").and_then(|v| v.as_i64()).unwrap_or(0) as i32;
            let y = action.params.get("y").and_then(|v| v.as_i64()).unwrap_or(0) as i32;
            simulator.double_click(x, y);
            Ok(())
        }
        ActionType::MouseRightClick => {
            let x = action.params.get("x").and_then(|v| v.as_i64()).unwrap_or(0) as i32;
            let y = action.params.get("y").and_then(|v| v.as_i64()).unwrap_or(0) as i32;
            simulator.click(x, y, "right");
            Ok(())
        }
        ActionType::MouseMove => {
            let x = action.params.get("x").and_then(|v| v.as_i64()).unwrap_or(0) as i32;
            let y = action.params.get("y").and_then(|v| v.as_i64()).unwrap_or(0) as i32;
            simulator.move_to(x, y);
            Ok(())
        }
        ActionType::MouseScroll => {
            let x = action.params.get("x").and_then(|v| v.as_i64()).unwrap_or(0) as i32;
            let y = action.params.get("y").and_then(|v| v.as_i64()).unwrap_or(0) as i32;
            let clicks = action.params.get("clicks").and_then(|v| v.as_i64()).unwrap_or(0) as i32;
            simulator.scroll(x, y, clicks);
            Ok(())
        }
        ActionType::KeyPress => {
            let key = action.params.get("key").and_then(|v| v.as_str()).unwrap_or("");
            simulator.key_press(key);
            Ok(())
        }
        ActionType::KeyType => {
            let text = action.params.get("text").and_then(|v| v.as_str()).unwrap_or("");
            let interval = action.params.get("interval").and_then(|v| v.as_f64()).unwrap_or(0.0);
            simulator.type_text(text, (interval * 1000.0) as u64);
            Ok(())
        }
        ActionType::Hotkey => {
            let keys: Vec<&str> = action.params.get("keys")
                .and_then(|v| v.as_array())
                .map(|arr| arr.iter().filter_map(|k| k.as_str()).collect())
                .unwrap_or_default();
            simulator.hotkey(&keys);
            Ok(())
        }
        ActionType::Wait => {
            let seconds = action.params.get("seconds").and_then(|v| v.as_f64()).unwrap_or(1.0);
            thread::sleep(Duration::from_secs_f64(seconds));
            Ok(())
        }
        ActionType::MouseMoveRelative | ActionType::MouseClickRelative => {
            let x = action.params.get("x").and_then(|v| v.as_i64()).unwrap_or(0) as i32;
            let y = action.params.get("y").and_then(|v| v.as_i64()).unwrap_or(0) as i32;

            if action.background_mode {
                let clicker = BackgroundClicker::new(None, action.window_title.as_deref());
                if clicker.is_available() {
                    if action.action_type == ActionType::MouseMoveRelative {
                        let result = clicker.move_mouse(x, y, true);
                        if result.success { return Ok(()) }
                    } else {
                        let button = action.params.get("button").and_then(|v| v.as_str()).unwrap_or("left");
                        let result = clicker.click(x, y, button, true);
                        if result.success { return Ok(()) }
                    }
                }
            }
            Err("相对坐标操作需要窗口偏移量".into())
        }
        ActionType::ImageClick | ActionType::ImageWaitClick | ActionType::ImageCheck => {
            Err("图片识别需要 GUI 层的图像匹配支持".into())
        }
        ActionType::Screenshot => {
            Err("截图需要 GUI 层支持".into())
        }
        ActionType::ActionGroupRef => {
            let group_name = action.params.get("group_name").and_then(|v| v.as_str()).unwrap_or("");
            if group_name.is_empty() {
                return Err("未指定动作组名称".into());
            }
            // Action group execution needs to be handled by the GUI layer
            // as it requires access to the group manager and recursive execution
            Ok(())
        }
        ActionType::MouseDrag => {
            let sx = action.params.get("start_x").and_then(|v| v.as_i64()).unwrap_or(0) as i32;
            let sy = action.params.get("start_y").and_then(|v| v.as_i64()).unwrap_or(0) as i32;
            let ex = action.params.get("end_x").and_then(|v| v.as_i64()).unwrap_or(0) as i32;
            let ey = action.params.get("end_y").and_then(|v| v.as_i64()).unwrap_or(0) as i32;
            simulator.move_to(sx, sy);
            thread::sleep(Duration::from_millis(50));
            // Simple drag: move step by step with button held
            let steps = 10;
            for i in 1..=steps {
                let cx = sx + (ex - sx) * i / steps;
                let cy = sy + (ey - sy) * i / steps;
                simulator.move_to(cx, cy);
                thread::sleep(Duration::from_millis(20));
            }
            Ok(())
        }
    }
}
