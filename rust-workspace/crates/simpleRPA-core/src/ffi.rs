use crate::action_group::{ActionGroup, GlobalActionGroupManager, LocalActionGroupManager};
use crate::actions::{Action, ActionManager, ActionType};
use crate::command_manager::CommandManager;
use crate::config::Config;
use crate::exporter::Exporter;
use crate::player::{Player, PlayerState};
use crate::recorder::{RecordConfig, Recorder};
use crate::window_utils::WindowUtils;
use std::ffi::{CStr, CString};
use std::os::raw::{c_char, c_double, c_int, c_void};
use std::sync::Mutex;

// Opaque handle types
pub struct FfiPlayer {
    inner: Mutex<Player>,
}

pub struct FfiRecorder {
    inner: Mutex<Recorder>,
}

pub struct FfiConfig {
    inner: Mutex<Config>,
}

pub struct FfiExporter {
    inner: Exporter,
}

pub struct FfiCommandManager {
    inner: Mutex<CommandManager>,
}

pub struct FfiWindowUtils {
    inner: WindowUtils,
}

pub struct FfiActionGroupManager {
    inner: Mutex<LocalActionGroupManager>,
}

type PlayerEventCallback = Option<
    extern "C" fn(
        event: c_int,
        index: c_int,
        total: c_int,
        repeat: c_int,
        value: c_int,
        user_data: *mut c_void,
    ),
>;

fn player_state_to_int(state: PlayerState) -> c_int {
    match state {
        PlayerState::Idle => 0,
        PlayerState::Playing => 1,
        PlayerState::Paused => 2,
        PlayerState::Stopped => 3,
    }
}

// Helper to convert C string to Rust string
unsafe fn cstr_to_string(ptr: *const c_char) -> String {
    if ptr.is_null() {
        return String::new();
    }
    CStr::from_ptr(ptr).to_str().unwrap_or("").to_string()
}

fn actions_from_json(json: &str) -> Option<Vec<Action>> {
    let actions_data: serde_json::Value = serde_json::from_str(json).ok()?;
    Some(
        actions_data
            .as_array()
            .map(|arr| arr.iter().filter_map(|a| Action::from_dict(a)).collect())
            .unwrap_or_default(),
    )
}

fn local_group_manager_from_json(json: &str) -> LocalActionGroupManager {
    let groups_data: serde_json::Value =
        serde_json::from_str(json).unwrap_or_else(|_| serde_json::json!({}));
    let mut manager = LocalActionGroupManager::new();
    manager.load_from_dict(&groups_data);
    manager
}

// ============ Config FFI ============

#[no_mangle]
pub extern "C" fn config_new() -> *mut FfiConfig {
    let config = Config::load();
    Box::into_raw(Box::new(FfiConfig {
        inner: Mutex::new(config),
    }))
}

#[no_mangle]
pub extern "C" fn config_free(ptr: *mut FfiConfig) {
    if !ptr.is_null() {
        unsafe {
            drop(Box::from_raw(ptr));
        }
    }
}

#[no_mangle]
pub extern "C" fn config_save(ptr: *const FfiConfig) -> c_int {
    if ptr.is_null() {
        return 0;
    }
    let config = unsafe { &*ptr };
    let inner = config.inner.lock().unwrap();
    if inner.save().is_ok() {
        1
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn config_get_default_speed(ptr: *const FfiConfig) -> c_double {
    if ptr.is_null() {
        return 1.0;
    }
    let config = unsafe { &*ptr };
    config.inner.lock().unwrap().default_speed
}

#[no_mangle]
pub extern "C" fn config_set_default_speed(ptr: *const FfiConfig, speed: c_double) {
    if ptr.is_null() {
        return;
    }
    let config = unsafe { &*ptr };
    config.inner.lock().unwrap().default_speed = speed;
}

#[no_mangle]
pub extern "C" fn config_get_default_repeat_count(ptr: *const FfiConfig) -> c_int {
    if ptr.is_null() {
        return 1;
    }
    let config = unsafe { &*ptr };
    config.inner.lock().unwrap().default_repeat_count
}

#[no_mangle]
pub extern "C" fn config_set_default_repeat_count(ptr: *const FfiConfig, count: c_int) {
    if ptr.is_null() {
        return;
    }
    let config = unsafe { &*ptr };
    config.inner.lock().unwrap().default_repeat_count = count;
}

#[no_mangle]
pub extern "C" fn config_get_infinite_loop(ptr: *const FfiConfig) -> c_int {
    if ptr.is_null() {
        return 0;
    }
    let config = unsafe { &*ptr };
    if config.inner.lock().unwrap().infinite_loop {
        1
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn config_set_infinite_loop(ptr: *const FfiConfig, val: c_int) {
    if ptr.is_null() {
        return;
    }
    let config = unsafe { &*ptr };
    config.inner.lock().unwrap().infinite_loop = val != 0;
}

#[no_mangle]
pub extern "C" fn config_get_timeout_seconds(ptr: *const FfiConfig) -> c_double {
    if ptr.is_null() {
        return 0.0;
    }
    let config = unsafe { &*ptr };
    config.inner.lock().unwrap().timeout_seconds
}

#[no_mangle]
pub extern "C" fn config_set_timeout_seconds(ptr: *const FfiConfig, val: c_double) {
    if ptr.is_null() {
        return;
    }
    let config = unsafe { &*ptr };
    config.inner.lock().unwrap().timeout_seconds = val;
}

#[no_mangle]
pub extern "C" fn config_get_minimize_to_tray(ptr: *const FfiConfig) -> c_int {
    if ptr.is_null() {
        return 1;
    }
    let config = unsafe { &*ptr };
    if config.inner.lock().unwrap().minimize_to_tray {
        1
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn config_set_minimize_to_tray(ptr: *const FfiConfig, val: c_int) {
    if ptr.is_null() {
        return;
    }
    let config = unsafe { &*ptr };
    config.inner.lock().unwrap().minimize_to_tray = val != 0;
}

#[no_mangle]
pub extern "C" fn config_get_run_window_offscreen(ptr: *const FfiConfig) -> c_int {
    if ptr.is_null() {
        return 0;
    }
    let config = unsafe { &*ptr };
    if config.inner.lock().unwrap().run_window_offscreen {
        1
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn config_set_run_window_offscreen(ptr: *const FfiConfig, val: c_int) {
    if ptr.is_null() {
        return;
    }
    let config = unsafe { &*ptr };
    config.inner.lock().unwrap().run_window_offscreen = val != 0;
}

// ============ WindowUtils FFI ============

#[no_mangle]
pub extern "C" fn window_utils_new() -> *mut FfiWindowUtils {
    Box::into_raw(Box::new(FfiWindowUtils {
        inner: WindowUtils::new(),
    }))
}

#[no_mangle]
pub extern "C" fn window_utils_free(ptr: *mut FfiWindowUtils) {
    if !ptr.is_null() {
        unsafe {
            drop(Box::from_raw(ptr));
        }
    }
}

#[no_mangle]
pub extern "C" fn window_utils_get_all_windows_json(ptr: *const FfiWindowUtils) -> *mut c_char {
    if ptr.is_null() {
        return CString::new("[]").unwrap().into_raw();
    }
    let wu = unsafe { &*ptr };
    let windows = wu.inner.get_all_windows();
    let json: Vec<serde_json::Value> = windows
        .iter()
        .map(|w| {
            serde_json::json!({
                "hwnd": w.hwnd,
                "title": w.title,
                "x": w.x,
                "y": w.y,
                "width": w.width,
                "height": w.height,
            })
        })
        .collect();
    let s = serde_json::to_string(&json).unwrap_or_else(|_| "[]".into());
    CString::new(s).unwrap().into_raw()
}

#[no_mangle]
pub extern "C" fn window_utils_free_string(ptr: *mut c_char) {
    if !ptr.is_null() {
        unsafe {
            drop(CString::from_raw(ptr));
        }
    }
}

// ============ Player FFI ============

#[no_mangle]
pub extern "C" fn player_new() -> *mut FfiPlayer {
    Box::into_raw(Box::new(FfiPlayer {
        inner: Mutex::new(Player::new()),
    }))
}

#[no_mangle]
pub extern "C" fn player_free(ptr: *mut FfiPlayer) {
    if !ptr.is_null() {
        unsafe {
            drop(Box::from_raw(ptr));
        }
    }
}

#[no_mangle]
pub extern "C" fn player_set_actions_json(ptr: *const FfiPlayer, json_str: *const c_char) -> c_int {
    if ptr.is_null() || json_str.is_null() {
        return 0;
    }
    let player = unsafe { &*ptr };
    let json = unsafe { cstr_to_string(json_str) };

    let actions_data: serde_json::Value = match serde_json::from_str(&json) {
        Ok(v) => v,
        Err(_) => return 0,
    };

    let actions: Vec<Action> = actions_data
        .as_array()
        .map(|arr| arr.iter().filter_map(|a| Action::from_dict(a)).collect())
        .unwrap_or_default();

    let mut inner = player.inner.lock().unwrap();
    inner.set_actions(actions);
    1
}

#[no_mangle]
pub extern "C" fn player_set_local_groups_json(
    ptr: *const FfiPlayer,
    local_groups_json: *const c_char,
) -> c_int {
    if ptr.is_null() || local_groups_json.is_null() {
        return 0;
    }

    let player = unsafe { &*ptr };
    let groups_json = unsafe { cstr_to_string(local_groups_json) };
    let manager = local_group_manager_from_json(&groups_json);
    player.inner.lock().unwrap().set_local_group_manager(manager);
    1
}

#[no_mangle]
pub extern "C" fn player_set_event_callback(
    ptr: *const FfiPlayer,
    callback: PlayerEventCallback,
    user_data: *mut c_void,
) {
    if ptr.is_null() {
        return;
    }

    let player = unsafe { &*ptr };
    let mut inner = player.inner.lock().unwrap();
    let Some(callback) = callback else {
        return;
    };

    const EVENT_ACTION_START: c_int = 1;
    const EVENT_ACTION_END: c_int = 2;
    const EVENT_PROGRESS: c_int = 3;
    const EVENT_STATE_CHANGED: c_int = 4;
    const EVENT_FINISHED: c_int = 5;

    let total = inner.action_count() as c_int;
    let user_data_value = user_data as usize;

    inner.set_on_action_start(move |_action, index| {
        callback(
            EVENT_ACTION_START,
            index as c_int,
            total,
            0,
            0,
            user_data_value as *mut c_void,
        );
    });

    let user_data_value = user_data as usize;
    inner.set_on_action_end(move |_action, index, success| {
        callback(
            EVENT_ACTION_END,
            index as c_int,
            total,
            0,
            if success { 1 } else { 0 },
            user_data_value as *mut c_void,
        );
    });

    let user_data_value = user_data as usize;
    inner.set_on_progress(move |_progress, index, repeat| {
        callback(
            EVENT_PROGRESS,
            index as c_int,
            total,
            repeat as c_int,
            0,
            user_data_value as *mut c_void,
        );
    });

    let user_data_value = user_data as usize;
    inner.set_on_state_changed(move |state| {
        callback(
            EVENT_STATE_CHANGED,
            -1,
            total,
            0,
            player_state_to_int(state),
            user_data_value as *mut c_void,
        );
    });

    let user_data_value = user_data as usize;
    inner.set_on_finished(move |success| {
        callback(
            EVENT_FINISHED,
            -1,
            total,
            0,
            if success { 1 } else { 0 },
            user_data_value as *mut c_void,
        );
    });
}

#[no_mangle]
pub extern "C" fn player_set_speed(ptr: *const FfiPlayer, speed: c_double) {
    if ptr.is_null() {
        return;
    }
    let player = unsafe { &*ptr };
    player.inner.lock().unwrap().set_speed(speed);
}

#[no_mangle]
pub extern "C" fn player_set_repeat_count(ptr: *const FfiPlayer, count: c_int) {
    if ptr.is_null() {
        return;
    }
    let player = unsafe { &*ptr };
    player.inner.lock().unwrap().set_repeat_count(count);
}

#[no_mangle]
pub extern "C" fn player_set_infinite_loop(ptr: *const FfiPlayer, val: c_int) {
    if ptr.is_null() {
        return;
    }
    let player = unsafe { &*ptr };
    player.inner.lock().unwrap().set_infinite_loop(val != 0);
}

#[no_mangle]
pub extern "C" fn player_set_timeout(ptr: *const FfiPlayer, seconds: c_double) {
    if ptr.is_null() {
        return;
    }
    let player = unsafe { &*ptr };
    player.inner.lock().unwrap().set_timeout(seconds);
}

#[no_mangle]
pub extern "C" fn player_set_window_title(ptr: *const FfiPlayer, title: *const c_char) {
    if ptr.is_null() || title.is_null() {
        return;
    }
    let player = unsafe { &*ptr };
    let title = unsafe { cstr_to_string(title) };
    player.inner.lock().unwrap().set_window_title(&title);
}

#[no_mangle]
pub extern "C" fn player_set_window_hwnd(ptr: *const FfiPlayer, hwnd: i64) {
    if ptr.is_null() {
        return;
    }
    let player = unsafe { &*ptr };
    player.inner.lock().unwrap().set_window_hwnd(hwnd);
}

#[no_mangle]
pub extern "C" fn player_set_window_run_mode(ptr: *const FfiPlayer, mode: *const c_char) {
    if ptr.is_null() || mode.is_null() {
        return;
    }
    let player = unsafe { &*ptr };
    let mode = unsafe { cstr_to_string(mode) };
    player.inner.lock().unwrap().set_window_run_mode(&mode);
}

#[no_mangle]
pub extern "C" fn player_set_window_offset(
    ptr: *const FfiPlayer,
    x: c_int,
    y: c_int,
    enabled: c_int,
) {
    if ptr.is_null() {
        return;
    }
    let player = unsafe { &*ptr };
    let offset = if enabled != 0 { Some((x, y)) } else { None };
    player.inner.lock().unwrap().set_window_offset(offset);
}

#[no_mangle]
pub extern "C" fn player_play(ptr: *const FfiPlayer) {
    if ptr.is_null() {
        return;
    }
    let player = unsafe { &*ptr };
    player.inner.lock().unwrap().play();
}

#[no_mangle]
pub extern "C" fn player_execute_single_action(
    ptr: *const FfiPlayer,
    index: c_int,
    offset_x: c_int,
    offset_y: c_int,
    has_offset: c_int,
) -> c_int {
    if ptr.is_null() || index < 0 {
        return 0;
    }
    let player = unsafe { &*ptr };
    let offset = if has_offset != 0 {
        Some((offset_x, offset_y))
    } else {
        None
    };
    if player
        .inner
        .lock()
        .unwrap()
        .execute_single_action(index as usize, offset)
    {
        1
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn player_stop(ptr: *const FfiPlayer) {
    if ptr.is_null() {
        return;
    }
    let player = unsafe { &*ptr };
    player.inner.lock().unwrap().stop();
}

#[no_mangle]
pub extern "C" fn player_toggle_pause(ptr: *const FfiPlayer) -> c_int {
    if ptr.is_null() {
        return 0;
    }
    let player = unsafe { &*ptr };
    let state = player.inner.lock().unwrap().toggle_pause();
    match state {
        PlayerState::Idle => 0,
        PlayerState::Playing => 1,
        PlayerState::Paused => 2,
        PlayerState::Stopped => 3,
    }
}

#[no_mangle]
pub extern "C" fn player_get_state(ptr: *const FfiPlayer) -> c_int {
    if ptr.is_null() {
        return 0;
    }
    let player = unsafe { &*ptr };
    match player.inner.lock().unwrap().state() {
        PlayerState::Idle => 0,
        PlayerState::Playing => 1,
        PlayerState::Paused => 2,
        PlayerState::Stopped => 3,
    }
}

// ============ Recorder FFI ============

#[no_mangle]
pub extern "C" fn recorder_new() -> *mut FfiRecorder {
    Box::into_raw(Box::new(FfiRecorder {
        inner: Mutex::new(Recorder::new(None)),
    }))
}

#[no_mangle]
pub extern "C" fn recorder_free(ptr: *mut FfiRecorder) {
    if !ptr.is_null() {
        unsafe {
            drop(Box::from_raw(ptr));
        }
    }
}

#[no_mangle]
pub extern "C" fn recorder_start(ptr: *const FfiRecorder) {
    if ptr.is_null() {
        return;
    }
    let recorder = unsafe { &*ptr };
    recorder.inner.lock().unwrap().start();
}

#[no_mangle]
pub extern "C" fn recorder_stop(ptr: *const FfiRecorder) -> *mut c_char {
    if ptr.is_null() {
        return CString::new("[]").unwrap().into_raw();
    }
    let recorder = unsafe { &*ptr };
    let actions = recorder.inner.lock().unwrap().stop();
    let json: Vec<serde_json::Value> = actions.iter().map(|a| a.to_dict()).collect();
    let s = serde_json::to_string(&json).unwrap_or_else(|_| "[]".into());
    CString::new(s).unwrap().into_raw()
}

#[no_mangle]
pub extern "C" fn recorder_is_recording(ptr: *const FfiRecorder) -> c_int {
    if ptr.is_null() {
        return 0;
    }
    let recorder = unsafe { &*ptr };
    if recorder.inner.lock().unwrap().is_recording() {
        1
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn recorder_set_config(
    ptr: *const FfiRecorder,
    record_mouse_click: c_int,
    record_mouse_scroll: c_int,
    record_keyboard: c_int,
    record_mouse_move: c_int,
    min_move_distance: c_int,
    move_sample_interval: c_double,
    ignore_last_click: c_int,
) {
    if ptr.is_null() {
        return;
    }
    let recorder = unsafe { &*ptr };
    let config = RecordConfig {
        record_mouse_click: record_mouse_click != 0,
        record_mouse_scroll: record_mouse_scroll != 0,
        record_keyboard: record_keyboard != 0,
        record_mouse_move: record_mouse_move != 0,
        min_move_distance: min_move_distance.max(1),
        move_sample_interval: move_sample_interval.max(0.01),
        ignore_last_click: ignore_last_click != 0,
    };
    recorder.inner.lock().unwrap().set_config(config);
}

#[no_mangle]
pub extern "C" fn recorder_on_mouse_click(
    ptr: *const FfiRecorder,
    x: c_int,
    y: c_int,
    button: *const c_char,
) {
    if ptr.is_null() || button.is_null() {
        return;
    }
    let recorder = unsafe { &*ptr };
    let button = unsafe { cstr_to_string(button) };
    recorder.inner.lock().unwrap().on_mouse_click(x, y, &button);
}

#[no_mangle]
pub extern "C" fn recorder_on_key_press(ptr: *const FfiRecorder, key: c_char) {
    if ptr.is_null() {
        return;
    }
    let recorder = unsafe { &*ptr };
    recorder.inner.lock().unwrap().on_key_press(key as u8 as char);
}

// ============ Exporter FFI ============

#[no_mangle]
pub extern "C" fn exporter_new() -> *mut FfiExporter {
    Box::into_raw(Box::new(FfiExporter {
        inner: Exporter::new(),
    }))
}

#[no_mangle]
pub extern "C" fn exporter_free(ptr: *mut FfiExporter) {
    if !ptr.is_null() {
        unsafe {
            drop(Box::from_raw(ptr));
        }
    }
}

#[no_mangle]
pub extern "C" fn exporter_set_script_info(
    ptr: *mut FfiExporter,
    name: *const c_char,
    author: *const c_char,
    description: *const c_char,
) {
    if ptr.is_null() {
        return;
    }
    let exporter = unsafe { &mut *ptr };
    let name = unsafe { cstr_to_string(name) };
    let author = unsafe { cstr_to_string(author) };
    let description = unsafe { cstr_to_string(description) };
    exporter.inner.set_script_info(&name, &author, &description);
}

#[no_mangle]
pub extern "C" fn exporter_set_local_groups_json(
    ptr: *mut FfiExporter,
    local_groups_json: *const c_char,
) -> c_int {
    if ptr.is_null() || local_groups_json.is_null() {
        return 0;
    }

    let exporter = unsafe { &mut *ptr };
    let groups_json = unsafe { cstr_to_string(local_groups_json) };
    exporter
        .inner
        .set_local_group_manager(local_group_manager_from_json(&groups_json));
    1
}

#[no_mangle]
pub extern "C" fn exporter_export_to_json(
    ptr: *mut FfiExporter,
    actions_json: *const c_char,
    filepath: *const c_char,
) -> c_int {
    if ptr.is_null() || actions_json.is_null() || filepath.is_null() {
        return 0;
    }
    let exporter = unsafe { &mut *ptr };
    let json = unsafe { cstr_to_string(actions_json) };
    let filepath = unsafe { cstr_to_string(filepath) };

    let actions_data: serde_json::Value = match serde_json::from_str(&json) {
        Ok(v) => v,
        Err(_) => return 0,
    };

    let actions: Vec<Action> = actions_data
        .as_array()
        .map(|arr| arr.iter().filter_map(|a| Action::from_dict(a)).collect())
        .unwrap_or_default();

    match exporter.inner.export_to_json(&actions, &filepath) {
        Ok(_) => 1,
        Err(_) => 0,
    }
}

#[no_mangle]
pub extern "C" fn exporter_export_to_python(
    ptr: *mut FfiExporter,
    actions_json: *const c_char,
    filepath: *const c_char,
) -> c_int {
    if ptr.is_null() || actions_json.is_null() || filepath.is_null() {
        return 0;
    }
    let exporter = unsafe { &mut *ptr };
    let json = unsafe { cstr_to_string(actions_json) };
    let filepath = unsafe { cstr_to_string(filepath) };

    let actions_data: serde_json::Value = match serde_json::from_str(&json) {
        Ok(v) => v,
        Err(_) => return 0,
    };

    let actions: Vec<Action> = actions_data
        .as_array()
        .map(|arr| arr.iter().filter_map(|a| Action::from_dict(a)).collect())
        .unwrap_or_default();

    match exporter.inner.export_to_python(&actions, &filepath) {
        Ok(_) => 1,
        Err(_) => 0,
    }
}

#[no_mangle]
pub extern "C" fn exporter_actions_to_python_code(
    actions_json: *const c_char,
    indent: *const c_char,
) -> *mut c_char {
    if actions_json.is_null() {
        return CString::new("").unwrap().into_raw();
    }

    let json = unsafe { cstr_to_string(actions_json) };
    let indent = unsafe { cstr_to_string(indent) };
    let actions_data: serde_json::Value = match serde_json::from_str(&json) {
        Ok(v) => v,
        Err(_) => return CString::new("").unwrap().into_raw(),
    };

    let actions: Vec<Action> = actions_data
        .as_array()
        .map(|arr| arr.iter().filter_map(|a| Action::from_dict(a)).collect())
        .unwrap_or_default();

    CString::new(Exporter::actions_to_python_code(&actions, &indent))
        .unwrap_or_else(|_| CString::new("").unwrap())
        .into_raw()
}

#[no_mangle]
pub extern "C" fn exporter_actions_to_python_code_with_groups(
    actions_json: *const c_char,
    local_groups_json: *const c_char,
    indent: *const c_char,
) -> *mut c_char {
    if actions_json.is_null() {
        return CString::new("").unwrap().into_raw();
    }

    let json = unsafe { cstr_to_string(actions_json) };
    let groups_json = unsafe { cstr_to_string(local_groups_json) };
    let indent = unsafe { cstr_to_string(indent) };
    let actions_data: serde_json::Value = match serde_json::from_str(&json) {
        Ok(v) => v,
        Err(_) => return CString::new("").unwrap().into_raw(),
    };

    let actions: Vec<Action> = actions_data
        .as_array()
        .map(|arr| arr.iter().filter_map(|a| Action::from_dict(a)).collect())
        .unwrap_or_default();

    let local_group_manager = local_group_manager_from_json(&groups_json);

    CString::new(Exporter::actions_to_python_code_with_groups(
        &actions,
        &indent,
        Some(&local_group_manager),
    ))
    .unwrap_or_else(|_| CString::new("").unwrap())
    .into_raw()
}

#[no_mangle]
pub extern "C" fn exporter_import_from_json(filepath: *const c_char) -> *mut c_char {
    if filepath.is_null() {
        return CString::new(r#"{"success":false,"message":"文件路径为空","actions":[]}"#)
            .unwrap()
            .into_raw();
    }

    let filepath = unsafe { cstr_to_string(filepath) };
    let mut local_group_manager = LocalActionGroupManager::new();
    match Exporter::import_from_json(&filepath, Some(&mut local_group_manager)) {
        Ok(actions) => {
            let actions_json: Vec<serde_json::Value> =
                actions.iter().map(|a| a.to_dict()).collect();
            let payload = serde_json::json!({
                "success": true,
                "message": "",
                "actions": actions_json,
                "action_count": actions.len(),
                "local_action_groups": local_group_manager.to_dict(),
            })
            .to_string();
            CString::new(payload).unwrap().into_raw()
        }
        Err(message) => {
            let payload = serde_json::json!({
                "success": false,
                "message": message,
                "actions": [],
            })
            .to_string();
            CString::new(payload).unwrap().into_raw()
        }
    }
}

// ============ Action FFI ============

#[no_mangle]
pub extern "C" fn action_new(action_type_str: *const c_char) -> *mut c_char {
    if action_type_str.is_null() {
        return CString::new("{}").unwrap().into_raw();
    }
    let type_str = unsafe { cstr_to_string(action_type_str) };
    if let Some(action_type) = ActionType::from_str(&type_str) {
        let action = Action::new(action_type);
        let json = action.to_dict().to_string();
        CString::new(json).unwrap().into_raw()
    } else {
        CString::new("{}").unwrap().into_raw()
    }
}

#[no_mangle]
pub extern "C" fn action_manager_get_catalog_json() -> *mut c_char {
    let catalog: Vec<serde_json::Value> = ActionManager::get_all_categories()
        .into_iter()
        .map(|category| {
            let actions: Vec<serde_json::Value> = ActionManager::get_actions_for_category(&category)
                .into_iter()
                .map(|action_type| {
                    let definition = ActionManager::get_definition(&action_type);
                    serde_json::json!({
                        "type": action_type.as_str(),
                        "name": definition.name,
                    })
                })
                .collect();
            serde_json::json!({
                "category": category,
                "actions": actions,
            })
        })
        .collect();

    CString::new(serde_json::Value::Array(catalog).to_string())
        .unwrap_or_else(|_| CString::new("[]").unwrap())
        .into_raw()
}

#[no_mangle]
pub extern "C" fn action_from_dict(json_str: *const c_char) -> *mut c_char {
    if json_str.is_null() {
        return CString::new("{}").unwrap().into_raw();
    }
    let json = unsafe { cstr_to_string(json_str) };
    let data: serde_json::Value = match serde_json::from_str(&json) {
        Ok(v) => v,
        Err(_) => return CString::new("{}").unwrap().into_raw(),
    };
    match Action::from_dict(&data) {
        Some(action) => {
            let json = action.to_dict().to_string();
            CString::new(json).unwrap().into_raw()
        }
        None => CString::new("{}").unwrap().into_raw(),
    }
}

#[no_mangle]
pub extern "C" fn action_get_description(json_str: *const c_char) -> *mut c_char {
    if json_str.is_null() {
        return CString::new("").unwrap().into_raw();
    }
    let json = unsafe { cstr_to_string(json_str) };
    let data: serde_json::Value = match serde_json::from_str(&json) {
        Ok(v) => v,
        Err(_) => return CString::new("").unwrap().into_raw(),
    };
    match Action::from_dict(&data) {
        Some(action) => CString::new(action.description).unwrap().into_raw(),
        None => CString::new("").unwrap().into_raw(),
    }
}

#[no_mangle]
pub extern "C" fn action_free_string(ptr: *mut c_char) {
    if !ptr.is_null() {
        unsafe {
            drop(CString::from_raw(ptr));
        }
    }
}

// ============ CommandManager FFI ============

#[no_mangle]
pub extern "C" fn command_manager_new() -> *mut FfiCommandManager {
    Box::into_raw(Box::new(FfiCommandManager {
        inner: Mutex::new(CommandManager::new()),
    }))
}

#[no_mangle]
pub extern "C" fn command_manager_free(ptr: *mut FfiCommandManager) {
    if !ptr.is_null() {
        unsafe {
            drop(Box::from_raw(ptr));
        }
    }
}

#[no_mangle]
pub extern "C" fn command_manager_get_all_json(ptr: *const FfiCommandManager) -> *mut c_char {
    if ptr.is_null() {
        return CString::new("[]").unwrap().into_raw();
    }
    let mgr = unsafe { &*ptr };
    let inner = mgr.inner.lock().unwrap();
    let commands: Vec<serde_json::Value> = inner
        .get_all_commands()
        .iter()
        .map(|c| c.to_dict())
        .collect();
    let json = serde_json::to_string(&commands).unwrap_or_else(|_| "[]".into());
    CString::new(json).unwrap().into_raw()
}

#[no_mangle]
pub extern "C" fn command_manager_add_command(
    ptr: *const FfiCommandManager,
    name: *const c_char,
    command: *const c_char,
    window_title_pattern: *const c_char,
    description: *const c_char,
    delay: c_double,
) -> *mut c_char {
    if ptr.is_null() || name.is_null() || command.is_null() {
        return CString::new("{}").unwrap().into_raw();
    }
    let mgr = unsafe { &*ptr };
    let name = unsafe { cstr_to_string(name) };
    let command = unsafe { cstr_to_string(command) };
    let pattern = unsafe { cstr_to_string(window_title_pattern) };
    let desc = unsafe { cstr_to_string(description) };
    let mut inner = mgr.inner.lock().unwrap();
    let cmd = inner.add_command(&name, &command, &pattern, &desc, delay);
    CString::new(cmd.to_dict().to_string()).unwrap().into_raw()
}

#[no_mangle]
pub extern "C" fn command_manager_delete_command(
    ptr: *const FfiCommandManager,
    cmd_id: *const c_char,
) -> c_int {
    if ptr.is_null() || cmd_id.is_null() {
        return 0;
    }
    let mgr = unsafe { &*ptr };
    let id = unsafe { cstr_to_string(cmd_id) };
    if mgr.inner.lock().unwrap().delete_command(&id) {
        1
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn command_manager_update_command(
    ptr: *const FfiCommandManager,
    cmd_id: *const c_char,
    updates_json: *const c_char,
) -> c_int {
    if ptr.is_null() || cmd_id.is_null() || updates_json.is_null() {
        return 0;
    }
    let mgr = unsafe { &*ptr };
    let id = unsafe { cstr_to_string(cmd_id) };
    let updates_str = unsafe { cstr_to_string(updates_json) };
    let updates: serde_json::Value = match serde_json::from_str(&updates_str) {
        Ok(value) => value,
        Err(_) => return 0,
    };
    if mgr.inner.lock().unwrap().update_command(&id, &updates) {
        1
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn command_manager_test_command(command: *const c_char) -> *mut c_char {
    if command.is_null() {
        return CString::new(r#"{"success":false,"message":"命令不能为空"}"#)
            .unwrap()
            .into_raw();
    }
    let command = unsafe { cstr_to_string(command) };
    if command.trim().is_empty() {
        return CString::new(r#"{"success":false,"message":"命令不能为空"}"#)
            .unwrap()
            .into_raw();
    }

    #[cfg(target_os = "windows")]
    let result = {
        std::process::Command::new("cmd")
            .args(["/C", &command])
            .spawn()
            .map(|_| "测试命令已启动".to_string())
            .map_err(|e| format!("测试命令失败: {}", e))
    };

    #[cfg(not(target_os = "windows"))]
    let result = {
        std::process::Command::new("sh")
            .args(["-c", &command])
            .spawn()
            .map(|_| "测试命令已启动".to_string())
            .map_err(|e| format!("测试命令失败: {}", e))
    };

    let json = match result {
        Ok(message) => serde_json::json!({"success": true, "message": message}),
        Err(message) => serde_json::json!({"success": false, "message": message}),
    };
    CString::new(json.to_string()).unwrap().into_raw()
}

#[no_mangle]
pub extern "C" fn command_manager_check_and_launch(
    ptr: *const FfiCommandManager,
    cmd_id: *const c_char,
) -> *mut c_char {
    if ptr.is_null() || cmd_id.is_null() {
        return CString::new(r#"{"success":false,"message":"命令不存在","already_running":false}"#)
            .unwrap()
            .into_raw();
    }

    let mgr = unsafe { &*ptr };
    let id = unsafe { cstr_to_string(cmd_id) };
    let (success, message, already_running) = mgr.inner.lock().unwrap().check_and_launch(&id);
    let json = serde_json::json!({
        "success": success,
        "message": message,
        "already_running": already_running,
    })
    .to_string();

    CString::new(json).unwrap().into_raw()
}

// ============ ActionGroup FFI ============

#[no_mangle]
pub extern "C" fn action_group_manager_new() -> *mut FfiActionGroupManager {
    Box::into_raw(Box::new(FfiActionGroupManager {
        inner: Mutex::new(LocalActionGroupManager::new()),
    }))
}

#[no_mangle]
pub extern "C" fn action_group_manager_free(ptr: *mut FfiActionGroupManager) {
    if !ptr.is_null() {
        unsafe {
            drop(Box::from_raw(ptr));
        }
    }
}

#[no_mangle]
pub extern "C" fn action_group_manager_get_all_json(
    ptr: *const FfiActionGroupManager,
) -> *mut c_char {
    if ptr.is_null() {
        return CString::new("[]").unwrap().into_raw();
    }
    let mgr = unsafe { &*ptr };
    let inner = mgr.inner.lock().unwrap();
    let groups: Vec<serde_json::Value> =
        inner.get_all_groups().iter().map(|g| g.to_dict()).collect();
    let json = serde_json::to_string(&groups).unwrap_or_else(|_| "[]".into());
    CString::new(json).unwrap().into_raw()
}

#[no_mangle]
pub extern "C" fn action_group_manager_to_json(ptr: *const FfiActionGroupManager) -> *mut c_char {
    if ptr.is_null() {
        return CString::new("{}").unwrap().into_raw();
    }

    let mgr = unsafe { &*ptr };
    let inner = mgr.inner.lock().unwrap();
    let json = inner.to_dict().to_string();
    CString::new(json).unwrap().into_raw()
}

#[no_mangle]
pub extern "C" fn action_group_manager_load_json(
    ptr: *const FfiActionGroupManager,
    local_groups_json: *const c_char,
) -> c_int {
    if ptr.is_null() || local_groups_json.is_null() {
        return 0;
    }

    let mgr = unsafe { &*ptr };
    let groups_json = unsafe { cstr_to_string(local_groups_json) };
    let groups_data: serde_json::Value =
        serde_json::from_str(&groups_json).unwrap_or_else(|_| serde_json::json!({}));
    let (success_count, fail_count) = mgr.inner.lock().unwrap().load_from_dict(&groups_data);
    if fail_count == 0 {
        success_count.max(1)
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn action_group_manager_save_group(
    ptr: *const FfiActionGroupManager,
    name: *const c_char,
    description: *const c_char,
    actions_json: *const c_char,
) -> c_int {
    if ptr.is_null() || name.is_null() || actions_json.is_null() {
        return 0;
    }

    let mgr = unsafe { &*ptr };
    let name = unsafe { cstr_to_string(name) };
    let description = unsafe { cstr_to_string(description) };
    let actions_json = unsafe { cstr_to_string(actions_json) };
    let actions = match actions_from_json(&actions_json) {
        Some(actions) => actions,
        None => return 0,
    };

    let group = ActionGroup {
        name,
        description,
        actions,
    };

    match mgr.inner.lock().unwrap().save_group(group) {
        Ok(_) => 1,
        Err(_) => 0,
    }
}

#[no_mangle]
pub extern "C" fn action_group_manager_delete_group(
    ptr: *const FfiActionGroupManager,
    name: *const c_char,
) -> c_int {
    if ptr.is_null() || name.is_null() {
        return 0;
    }

    let mgr = unsafe { &*ptr };
    let name = unsafe { cstr_to_string(name) };
    if mgr.inner.lock().unwrap().delete_group(&name) {
        1
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn action_group_manager_get_group_actions_json(
    ptr: *const FfiActionGroupManager,
    name: *const c_char,
) -> *mut c_char {
    if ptr.is_null() || name.is_null() {
        return CString::new("[]").unwrap().into_raw();
    }

    let mgr = unsafe { &*ptr };
    let name = unsafe { cstr_to_string(name) };
    let inner = mgr.inner.lock().unwrap();
    let actions_json: Vec<serde_json::Value> = inner
        .get_actions_copy(&name)
        .iter()
        .map(|a| a.to_dict())
        .collect();
    let json = serde_json::to_string(&actions_json).unwrap_or_else(|_| "[]".into());
    CString::new(json).unwrap().into_raw()
}

#[no_mangle]
pub extern "C" fn global_action_group_manager_get_all_json() -> *mut c_char {
    let mut mgr = GlobalActionGroupManager::new();
    mgr.reload_groups();
    let groups: Vec<serde_json::Value> =
        mgr.get_all_groups().iter().map(|g| g.to_dict()).collect();
    let json = serde_json::to_string(&groups).unwrap_or_else(|_| "[]".into());
    CString::new(json).unwrap().into_raw()
}

#[no_mangle]
pub extern "C" fn global_action_group_manager_get_group_actions_json(
    name: *const c_char,
) -> *mut c_char {
    if name.is_null() {
        return CString::new("[]").unwrap().into_raw();
    }

    let name = unsafe { cstr_to_string(name) };
    let mut mgr = GlobalActionGroupManager::new();
    let actions_json: Vec<serde_json::Value> = mgr
        .ensure_group_loaded(&name)
        .map(|group| group.actions.iter().map(|a| a.to_dict()).collect())
        .unwrap_or_default();
    let json = serde_json::to_string(&actions_json).unwrap_or_else(|_| "[]".into());
    CString::new(json).unwrap().into_raw()
}

#[no_mangle]
pub extern "C" fn global_action_group_manager_delete_group(name: *const c_char) -> c_int {
    if name.is_null() {
        return 0;
    }
    let name = unsafe { cstr_to_string(name) };
    if GlobalActionGroupManager::new().delete_group(&name) {
        1
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn global_action_group_manager_save_group(
    name: *const c_char,
    description: *const c_char,
    actions_json: *const c_char,
) -> c_int {
    if name.is_null() || actions_json.is_null() {
        return 0;
    }

    let name = unsafe { cstr_to_string(name) };
    let description = unsafe { cstr_to_string(description) };
    let actions_json = unsafe { cstr_to_string(actions_json) };
    let actions = match actions_from_json(&actions_json) {
        Some(actions) => actions,
        None => return 0,
    };

    let group = ActionGroup {
        name,
        description,
        actions,
    };

    match GlobalActionGroupManager::new().save_group(&group) {
        Ok(_) => 1,
        Err(_) => 0,
    }
}
