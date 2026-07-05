use crate::actions::{Action, ActionType};
use std::sync::{Arc, Mutex};
use std::time::Instant;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RecordState {
    Idle,
    Recording,
    Paused,
}

pub struct RecordConfig {
    pub record_mouse_move: bool,
    pub record_mouse_click: bool,
    pub record_mouse_scroll: bool,
    pub record_keyboard: bool,
    pub min_move_distance: i32,
    pub move_sample_interval: f64,
    pub ignore_last_click: bool,
}

impl Default for RecordConfig {
    fn default() -> Self {
        Self {
            record_mouse_move: false,
            record_mouse_click: true,
            record_mouse_scroll: true,
            record_keyboard: true,
            min_move_distance: 10,
            move_sample_interval: 0.1,
            ignore_last_click: true,
        }
    }
}

pub struct Recorder {
    config: RecordConfig,
    state: Arc<Mutex<RecordState>>,
    actions: Arc<Mutex<Vec<Action>>>,
    last_mouse_pos: Arc<Mutex<Option<(i32, i32)>>>,
    last_move_time: Arc<Mutex<Instant>>,
    start_time: Arc<Mutex<Instant>>,
    last_action_time: Arc<Mutex<Instant>>,
    recorded_keys: Arc<Mutex<Vec<char>>>,
    is_recording_text: Arc<Mutex<bool>>,

    on_action_recorded: Option<Box<dyn Fn(&Action) + Send>>,
    on_state_changed: Option<Box<dyn Fn(RecordState) + Send>>,
}

impl Recorder {
    pub fn new(config: Option<RecordConfig>) -> Self {
        let now = Instant::now();
        Self {
            config: config.unwrap_or_default(),
            state: Arc::new(Mutex::new(RecordState::Idle)),
            actions: Arc::new(Mutex::new(Vec::new())),
            last_mouse_pos: Arc::new(Mutex::new(None)),
            last_move_time: Arc::new(Mutex::new(now)),
            start_time: Arc::new(Mutex::new(now)),
            last_action_time: Arc::new(Mutex::new(now)),
            recorded_keys: Arc::new(Mutex::new(Vec::new())),
            is_recording_text: Arc::new(Mutex::new(false)),
            on_action_recorded: None,
            on_state_changed: None,
        }
    }

    pub fn set_on_action_recorded<F: Fn(&Action) + Send + 'static>(&mut self, f: F) {
        self.on_action_recorded = Some(Box::new(f));
    }

    pub fn set_on_state_changed<F: Fn(RecordState) + Send + 'static>(&mut self, f: F) {
        self.on_state_changed = Some(Box::new(f));
    }

    pub fn set_config(&mut self, config: RecordConfig) {
        self.config = config;
    }

    pub fn start(&self) {
        let mut state = self.state.lock().unwrap();
        if *state == RecordState::Recording {
            return;
        }

        self.actions.lock().unwrap().clear();
        *state = RecordState::Recording;
        *self.start_time.lock().unwrap() = Instant::now();
        *self.last_action_time.lock().unwrap() = Instant::now();
        *self.last_mouse_pos.lock().unwrap() = None;
        self.recorded_keys.lock().unwrap().clear();
        *self.is_recording_text.lock().unwrap() = false;

        if let Some(ref f) = self.on_state_changed {
            f(RecordState::Recording);
        }
    }

    pub fn stop(&self) -> Vec<Action> {
        let mut state = self.state.lock().unwrap();
        if *state == RecordState::Idle {
            return Vec::new();
        }

        *state = RecordState::Idle;

        if *self.is_recording_text.lock().unwrap() {
            self.flush_text_input();
        }

        let mut actions = self.actions.lock().unwrap();
        if self.config.ignore_last_click {
            if let Some(last) = actions.last() {
                if matches!(
                    last.action_type,
                    ActionType::MouseClick | ActionType::ImageClick
                ) {
                    actions.pop();
                }
            }
        }

        if let Some(ref f) = self.on_state_changed {
            f(RecordState::Idle);
        }

        actions.clone()
    }

    pub fn pause(&self) {
        let mut state = self.state.lock().unwrap();
        if *state == RecordState::Recording {
            *state = RecordState::Paused;
            if let Some(ref f) = self.on_state_changed {
                f(RecordState::Paused);
            }
        }
    }

    pub fn resume(&self) {
        let mut state = self.state.lock().unwrap();
        if *state == RecordState::Paused {
            *state = RecordState::Recording;
            if let Some(ref f) = self.on_state_changed {
                f(RecordState::Recording);
            }
        }
    }

    pub fn get_actions(&self) -> Vec<Action> {
        self.actions.lock().unwrap().clone()
    }

    pub fn clear_actions(&self) {
        self.actions.lock().unwrap().clear();
        *self.last_action_time.lock().unwrap() = Instant::now();
    }

    pub fn is_recording(&self) -> bool {
        *self.state.lock().unwrap() == RecordState::Recording
    }

    pub fn on_mouse_move(&self, x: i32, y: i32) {
        if *self.state.lock().unwrap() != RecordState::Recording {
            return;
        }
        if !self.config.record_mouse_move {
            return;
        }

        let now = Instant::now();
        let last_move = *self.last_move_time.lock().unwrap();
        if now.duration_since(last_move).as_secs_f64() < self.config.move_sample_interval {
            return;
        }

        let mut last_pos = self.last_mouse_pos.lock().unwrap();
        if let Some(pos) = *last_pos {
            let distance = ((x - pos.0).pow(2) + (y - pos.1).pow(2)) as f64;
            if (distance as i32) < self.config.min_move_distance {
                return;
            }
        }
        *last_pos = Some((x, y));
        *self.last_move_time.lock().unwrap() = now;

        let mut action = Action::new(ActionType::MouseMove);
        action.params.insert("x".into(), serde_json::json!(x));
        action.params.insert("y".into(), serde_json::json!(y));
        action
            .params
            .insert("duration".into(), serde_json::json!(0.0));
        self.add_action(action);
    }

    pub fn on_mouse_click(&self, x: i32, y: i32, button: &str) {
        if *self.state.lock().unwrap() != RecordState::Recording {
            return;
        }
        if !self.config.record_mouse_click {
            return;
        }

        if *self.is_recording_text.lock().unwrap() {
            self.flush_text_input();
        }

        let elapsed = self.get_elapsed_time();
        let mut action = Action::new(ActionType::MouseClick);
        action.params.insert("x".into(), serde_json::json!(x));
        action.params.insert("y".into(), serde_json::json!(y));
        action
            .params
            .insert("button".into(), serde_json::json!(button));
        action.params.insert("clicks".into(), serde_json::json!(1));
        action.delay_before = elapsed;
        action.description = action.generate_description();
        self.actions.lock().unwrap().push(action.clone());
        *self.last_action_time.lock().unwrap() = Instant::now();

        if let Some(ref f) = self.on_action_recorded {
            f(&action);
        }
    }

    pub fn on_mouse_scroll(&self, x: i32, y: i32, _dx: i32, dy: i32) {
        if *self.state.lock().unwrap() != RecordState::Recording {
            return;
        }
        if !self.config.record_mouse_scroll {
            return;
        }

        if *self.is_recording_text.lock().unwrap() {
            self.flush_text_input();
        }

        let mut action = Action::new(ActionType::MouseScroll);
        action.params.insert("clicks".into(), serde_json::json!(dy));
        action.params.insert("x".into(), serde_json::json!(x));
        action.params.insert("y".into(), serde_json::json!(y));
        self.add_action(action);
    }

    pub fn on_key_press(&self, key: char) {
        if *self.state.lock().unwrap() != RecordState::Recording {
            return;
        }
        if !self.config.record_keyboard {
            return;
        }

        if !*self.is_recording_text.lock().unwrap() {
            *self.is_recording_text.lock().unwrap() = true;
        }
        self.recorded_keys.lock().unwrap().push(key);
    }

    fn flush_text_input(&self) {
        let keys: Vec<char> = {
            let mut recorded = self.recorded_keys.lock().unwrap();
            if recorded.is_empty() {
                *self.is_recording_text.lock().unwrap() = false;
                return;
            }
            recorded.drain(..).collect()
        };

        let text: String = keys.iter().collect();
        let mut action = Action::new(ActionType::KeyType);
        action.params.insert("text".into(), serde_json::json!(text));
        action
            .params
            .insert("interval".into(), serde_json::json!(0.0));
        self.add_action(action);

        *self.is_recording_text.lock().unwrap() = false;
    }

    fn add_action(&self, mut action: Action) {
        let state = self.state.lock().unwrap();
        if *state != RecordState::Recording {
            return;
        }

        let elapsed = self.get_elapsed_time();
        action.delay_before = elapsed;
        action.description = action.generate_description();
        self.actions.lock().unwrap().push(action.clone());
        *self.last_action_time.lock().unwrap() = Instant::now();

        drop(state);
        if let Some(ref f) = self.on_action_recorded {
            f(&action);
        }
    }

    fn get_elapsed_time(&self) -> f64 {
        self.last_action_time
            .lock()
            .unwrap()
            .elapsed()
            .as_secs_f64()
    }
}
