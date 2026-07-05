use std::ffi::{CStr, CString};
use std::os::raw::c_char;
use std::ptr;

use simplerpa_core::actions::{Action, ActionType};
use simplerpa_core::action_group::LocalActionGroupManager;
use simplerpa_core::config::Config;
use simplerpa_core::exporter::Exporter;
use simplerpa_engine::player::{Player, PlayerState};
use simplerpa_engine::command_manager::CommandManager;
use simplerpa_winapi::window::WindowUtils;

/* ===== String management ===== */

#[no_mangle]
pub extern "C" fn simplerpa_string_free(s: *mut c_char) {
    if !s.is_null() {
        unsafe { drop(CString::from_raw(s)); }
    }
}

/* ===== Action ===== */

fn to_cstring(s: String) -> *mut c_char {
    CString::new(s).unwrap_or_default().into_raw()
}

#[no_mangle]
pub extern "C" fn action_new(action_type: i32) -> *mut Action {
    let at = match action_type {
        0 => ActionType::MouseClick,
        1 => ActionType::MouseDoubleClick,
        2 => ActionType::MouseRightClick,
        3 => ActionType::MouseMove,
        4 => ActionType::MouseDrag,
        5 => ActionType::MouseScroll,
        6 => ActionType::KeyPress,
        7 => ActionType::KeyType,
        8 => ActionType::Hotkey,
        9 => ActionType::Wait,
        10 => ActionType::Screenshot,
        11 => ActionType::MouseMoveRelative,
        12 => ActionType::MouseClickRelative,
        13 => ActionType::ImageClick,
        14 => ActionType::ImageWaitClick,
        15 => ActionType::ImageCheck,
        16 => ActionType::ActionGroupRef,
        _ => ActionType::Wait,
    };
    Box::into_raw(Box::new(Action::new(at)))
}

#[no_mangle]
pub extern "C" fn action_free(h: *mut Action) {
    if !h.is_null() {
        unsafe { drop(Box::from_raw(h)); }
    }
}

#[no_mangle]
pub extern "C" fn action_get_description(h: *mut Action) -> *mut c_char {
    if h.is_null() { return ptr::null_mut(); }
    let action = unsafe { &*h };
    to_cstring(action.generate_description())
}

#[no_mangle]
pub extern "C" fn action_to_json(h: *mut Action) -> *mut c_char {
    if h.is_null() { return ptr::null_mut(); }
    let action = unsafe { &*h };
    let json = serde_json::to_string(&action.to_dict()).unwrap_or_default();
    to_cstring(json)
}

#[no_mangle]
pub extern "C" fn action_from_json(json: *const c_char) -> *mut Action {
    if json.is_null() { return ptr::null_mut(); }
    let json_str = unsafe { CStr::from_ptr(json) }.to_string_lossy();
    let data: serde_json::Value = match serde_json::from_str(&json_str) {
        Ok(v) => v,
        Err(_) => return ptr::null_mut(),
    };
    match Action::from_dict(&data) {
        Ok(action) => Box::into_raw(Box::new(action)),
        Err(_) => ptr::null_mut(),
    }
}

macro_rules! param_setter {
    ($name:ident, $ftype:ty, $conv:expr) => {
        #[no_mangle]
        pub extern "C" fn $name(h: *mut Action, key: *const c_char, value: $ftype) {
            if h.is_null() || key.is_null() { return; }
            let action = unsafe { &mut *h };
            let key_str = unsafe { CStr::from_ptr(key) }.to_string_lossy();
            action.params.insert(key_str.to_string(), $conv(value));
        }
    };
}

param_setter!(action_set_param_i64, i64, |v: i64| serde_json::json!(v));
param_setter!(action_set_param_f64, f64, |v: f64| serde_json::json!(v));
param_setter!(action_set_param_bool, bool, |v: bool| serde_json::json!(v));

#[no_mangle]
pub extern "C" fn action_set_param_str(h: *mut Action, key: *const c_char, value: *const c_char) {
    if h.is_null() || key.is_null() || value.is_null() { return; }
    let action = unsafe { &mut *h };
    let key_str = unsafe { CStr::from_ptr(key) }.to_string_lossy();
    let val_str = unsafe { CStr::from_ptr(value) }.to_string_lossy();
    action.params.insert(key_str.to_string(), serde_json::json!(val_str.to_string()));
}

#[no_mangle]
pub extern "C" fn action_set_delay_before(h: *mut Action, seconds: f64) {
    if h.is_null() { return; }
    unsafe { (*h).delay_before = seconds; }
}

#[no_mangle]
pub extern "C" fn action_set_delay_after(h: *mut Action, seconds: f64) {
    if h.is_null() { return; }
    unsafe { (*h).delay_after = seconds; }
}

#[no_mangle]
pub extern "C" fn action_set_window_title(h: *mut Action, title: *const c_char) {
    if h.is_null() || title.is_null() { return; }
    let t = unsafe { CStr::from_ptr(title) }.to_string_lossy().to_string();
    unsafe { (*h).window_title = Some(t); }
}

#[no_mangle]
pub extern "C" fn action_set_use_relative_coords(h: *mut Action, val: bool) {
    if h.is_null() { return; }
    unsafe { (*h).use_relative_coords = val; }
}

#[no_mangle]
pub extern "C" fn action_set_background_mode(h: *mut Action, val: bool) {
    if h.is_null() { return; }
    unsafe { (*h).background_mode = val; }
}

#[no_mangle]
pub extern "C" fn action_set_name(h: *mut Action, name: *const c_char) {
    if h.is_null() || name.is_null() { return; }
    let n = unsafe { CStr::from_ptr(name) }.to_string_lossy().to_string();
    unsafe { (*h).name = n; }
}

#[no_mangle]
pub extern "C" fn action_set_condition(h: *mut Action, condition: *const c_char) {
    if h.is_null() || condition.is_null() { return; }
    let c = unsafe { CStr::from_ptr(condition) }.to_string_lossy().to_string();
    unsafe { (*h).condition = c; }
}

#[no_mangle]
pub extern "C" fn action_set_repeat_count(h: *mut Action, count: i32) {
    if h.is_null() { return; }
    unsafe { (*h).repeat_count = count; }
}

#[no_mangle]
pub extern "C" fn action_validate(h: *mut Action) -> *mut c_char {
    if h.is_null() { return to_cstring("".into()); }
    let action = unsafe { &*h };
    match action.validate() {
        Ok(()) => to_cstring("".into()),
        Err(e) => to_cstring(e),
    }
}

#[no_mangle]
pub extern "C" fn action_check_condition(h: *mut Action) -> bool {
    if h.is_null() { return true; }
    let action = unsafe { &*h };
    action.check_condition(&std::collections::HashMap::new())
}

#[no_mangle]
pub extern "C" fn action_type_value(h: *mut Action) -> i32 {
    if h.is_null() { return -1; }
    let action = unsafe { &*h };
    match action.action_type {
        ActionType::MouseClick => 0,
        ActionType::MouseDoubleClick => 1,
        ActionType::MouseRightClick => 2,
        ActionType::MouseMove => 3,
        ActionType::MouseDrag => 4,
        ActionType::MouseScroll => 5,
        ActionType::KeyPress => 6,
        ActionType::KeyType => 7,
        ActionType::Hotkey => 8,
        ActionType::Wait => 9,
        ActionType::Screenshot => 10,
        ActionType::MouseMoveRelative => 11,
        ActionType::MouseClickRelative => 12,
        ActionType::ImageClick => 13,
        ActionType::ImageWaitClick => 14,
        ActionType::ImageCheck => 15,
        ActionType::ActionGroupRef => 16,
    }
}

/* ===== Player ===== */

#[no_mangle]
pub extern "C" fn player_new() -> *mut Player {
    Box::into_raw(Box::new(Player::new()))
}

#[no_mangle]
pub extern "C" fn player_free(h: *mut Player) {
    if !h.is_null() {
        unsafe { drop(Box::from_raw(h)); }
    }
}

#[no_mangle]
pub extern "C" fn player_set_speed(h: *mut Player, speed: f64) {
    if h.is_null() { return; }
    unsafe { (*h).set_speed(speed); }
}

#[no_mangle]
pub extern "C" fn player_set_repeat_count(h: *mut Player, count: i32) {
    if h.is_null() { return; }
    unsafe { (*h).set_repeat_count(count); }
}

#[no_mangle]
pub extern "C" fn player_set_infinite_loop(h: *mut Player, val: bool) {
    if h.is_null() { return; }
    unsafe { (*h).set_infinite_loop(val); }
}

#[no_mangle]
pub extern "C" fn player_set_timeout(h: *mut Player, seconds: f64) {
    if h.is_null() { return; }
    unsafe { (*h).set_timeout(seconds); }
}

#[no_mangle]
pub extern "C" fn player_set_window_hwnd(h: *mut Player, hwnd: i64) {
    if h.is_null() { return; }
    unsafe { (*h).set_window_hwnd(hwnd); }
}

#[no_mangle]
pub extern "C" fn player_set_window_title(h: *mut Player, title: *const c_char) {
    if h.is_null() || title.is_null() { return; }
    let t = unsafe { CStr::from_ptr(title) }.to_string_lossy().to_string();
    unsafe { (*h).set_window_title(&t); }
}

#[no_mangle]
pub extern "C" fn player_set_window_offset(h: *mut Player, x: i32, y: i32) {
    if h.is_null() { return; }
    unsafe { (*h).set_window_offset(Some((x, y))); }
}

#[no_mangle]
pub extern "C" fn player_set_window_run_mode(h: *mut Player, mode: *const c_char) {
    if h.is_null() || mode.is_null() { return; }
    let m = unsafe { CStr::from_ptr(mode) }.to_string_lossy().to_string();
    unsafe { (*h).set_window_run_mode(&m); }
}

#[no_mangle]
pub extern "C" fn player_play(h: *mut Player) {
    if h.is_null() { return; }
    unsafe { (*h).play(); }
}

#[no_mangle]
pub extern "C" fn player_pause(h: *mut Player) {
    if h.is_null() { return; }
    unsafe { (*h).pause(); }
}

#[no_mangle]
pub extern "C" fn player_resume(h: *mut Player) {
    if h.is_null() { return; }
    unsafe { (*h).resume(); }
}

#[no_mangle]
pub extern "C" fn player_stop(h: *mut Player) {
    if h.is_null() { return; }
    unsafe { (*h).stop(); }
}

#[no_mangle]
pub extern "C" fn player_get_state(h: *mut Player) -> i32 {
    if h.is_null() { return 0; }
    match unsafe { (*h).state() } {
        PlayerState::Idle => 0,
        PlayerState::Playing => 1,
        PlayerState::Paused => 2,
        PlayerState::Stopped => 3,
    }
}

#[no_mangle]
pub extern "C" fn player_get_current_index(h: *mut Player) -> i32 {
    if h.is_null() { return 0; }
    unsafe { (*h).current_index as i32 }
}

#[no_mangle]
pub extern "C" fn player_get_current_repeat(h: *mut Player) -> i32 {
    if h.is_null() { return 0; }
    unsafe { (*h).current_repeat as i32 }
}

#[no_mangle]
pub extern "C" fn player_get_total_actions(h: *mut Player) -> i32 {
    if h.is_null() { return 0; }
    unsafe { (*h).actions.len() as i32 }
}

/* ===== Config ===== */

#[no_mangle]
pub extern "C" fn config_load() -> *mut Config {
    Box::into_raw(Box::new(Config::load()))
}

#[no_mangle]
pub extern "C" fn config_free(h: *mut Config) {
    if !h.is_null() { unsafe { drop(Box::from_raw(h)); } }
}

#[no_mangle]
pub extern "C" fn config_save(h: *mut Config) {
    if h.is_null() { return; }
    let _ = unsafe { (*h).save() };
}

#[no_mangle]
pub extern "C" fn config_get_default_speed(h: *mut Config) -> f64 {
    if h.is_null() { return 1.0; }
    unsafe { (*h).default_speed }
}

#[no_mangle]
pub extern "C" fn config_get_default_repeat_count(h: *mut Config) -> i32 {
    if h.is_null() { return 1; }
    unsafe { (*h).default_repeat_count }
}

#[no_mangle]
pub extern "C" fn config_set_default_speed(h: *mut Config, val: f64) {
    if h.is_null() { return; }
    unsafe { (*h).default_speed = val; }
}

#[no_mangle]
pub extern "C" fn config_set_default_repeat_count(h: *mut Config, val: i32) {
    if h.is_null() { return; }
    unsafe { (*h).default_repeat_count = val; }
}

#[no_mangle]
pub extern "C" fn config_get_infinite_loop(h: *mut Config) -> bool {
    if h.is_null() { return false; }
    unsafe { (*h).infinite_loop }
}

#[no_mangle]
pub extern "C" fn config_get_timeout_seconds(h: *mut Config) -> f64 {
    if h.is_null() { return 0.0; }
    unsafe { (*h).timeout_seconds }
}

#[no_mangle]
pub extern "C" fn config_set_infinite_loop(h: *mut Config, val: bool) {
    if h.is_null() { return; }
    unsafe { (*h).infinite_loop = val; }
}

#[no_mangle]
pub extern "C" fn config_set_timeout_seconds(h: *mut Config, val: f64) {
    if h.is_null() { return; }
    unsafe { (*h).timeout_seconds = val; }
}

#[no_mangle]
pub extern "C" fn config_get_minimize_to_tray(h: *mut Config) -> bool {
    if h.is_null() { return true; }
    unsafe { (*h).minimize_to_tray }
}

#[no_mangle]
pub extern "C" fn config_set_minimize_to_tray(h: *mut Config, val: bool) {
    if h.is_null() { return; }
    unsafe { (*h).minimize_to_tray = val; }
}

#[no_mangle]
pub extern "C" fn config_get_run_window_offscreen(h: *mut Config) -> bool {
    if h.is_null() { return false; }
    unsafe { (*h).run_window_offscreen }
}

#[no_mangle]
pub extern "C" fn config_set_run_window_offscreen(h: *mut Config, val: bool) {
    if h.is_null() { return; }
    unsafe { (*h).run_window_offscreen = val; }
}

/* ===== Window Utils ===== */

#[no_mangle]
pub extern "C" fn window_utils_new() -> *mut WindowUtils {
    Box::into_raw(Box::new(WindowUtils::new()))
}

#[no_mangle]
pub extern "C" fn window_utils_free(h: *mut WindowUtils) {
    if !h.is_null() { unsafe { drop(Box::from_raw(h)); } }
}

#[no_mangle]
pub extern "C" fn window_utils_get_all_windows_count(h: *mut WindowUtils) -> i32 {
    if h.is_null() { return 0; }
    unsafe { (*h).get_all_windows().len() as i32 }
}

#[repr(C)]
pub struct WindowInfoFFI {
    pub hwnd: i64,
    pub title: *mut c_char,
    pub x: i32,
    pub y: i32,
    pub width: i32,
    pub height: i32,
}

#[no_mangle]
pub extern "C" fn window_utils_get_window_at(h: *mut WindowUtils, index: i32) -> WindowInfoFFI {
    if h.is_null() {
        return WindowInfoFFI { hwnd: 0, title: ptr::null_mut(), x: 0, y: 0, width: 0, height: 0 };
    }
    let windows = unsafe { (*h).get_all_windows() };
    if let Some(w) = windows.get(index as usize) {
        WindowInfoFFI {
            hwnd: w.hwnd,
            title: to_cstring(w.title.clone()),
            x: w.x,
            y: w.y,
            width: w.width,
            height: w.height,
        }
    } else {
        WindowInfoFFI { hwnd: 0, title: ptr::null_mut(), x: 0, y: 0, width: 0, height: 0 }
    }
}

#[no_mangle]
pub extern "C" fn window_utils_find_by_title(h: *mut WindowUtils, title: *const c_char) -> i64 {
    if h.is_null() || title.is_null() { return 0; }
    let title_str = unsafe { CStr::from_ptr(title) }.to_string_lossy();
    match unsafe { (*h).get_window_by_title(&title_str) } {
        Some(w) => w.hwnd,
        None => 0,
    }
}

#[no_mangle]
pub extern "C" fn window_utils_activate_window(h: *mut WindowUtils, hwnd: i64) -> bool {
    if h.is_null() { return false; }
    unsafe { (*h).activate_window(hwnd) }
}

/* ===== Exporter ===== */

#[no_mangle]
pub extern "C" fn exporter_new() -> *mut Exporter {
    Box::into_raw(Box::new(Exporter::new()))
}

#[no_mangle]
pub extern "C" fn exporter_free(h: *mut Exporter) {
    if !h.is_null() { unsafe { drop(Box::from_raw(h)); } }
}

#[no_mangle]
pub extern "C" fn exporter_set_script_name(h: *mut Exporter, name: *const c_char) {
    if h.is_null() || name.is_null() { return; }
    let n = unsafe { CStr::from_ptr(name) }.to_string_lossy().to_string();
    unsafe { (*h).script_name = n; }
}

/* ===== Command Manager ===== */

#[no_mangle]
pub extern "C" fn command_manager_new() -> *mut CommandManager {
    Box::into_raw(Box::new(CommandManager::new()))
}

#[no_mangle]
pub extern "C" fn command_manager_free(h: *mut CommandManager) {
    if !h.is_null() { unsafe { drop(Box::from_raw(h)); } }
}

#[no_mangle]
pub extern "C" fn command_manager_get_all_commands_json(h: *mut CommandManager) -> *mut c_char {
    if h.is_null() { return to_cstring("[]".into()); }
    let cmds = unsafe { (*h).get_all_commands() };
    let json: Vec<serde_json::Value> = cmds.iter().map(|c| serde_json::to_value(c).unwrap()).collect();
    to_cstring(serde_json::to_string(&json).unwrap_or_else(|_| "[]".into()))
}

#[no_mangle]
pub extern "C" fn command_manager_add_command(
    h: *mut CommandManager,
    name: *const c_char,
    command: *const c_char,
    window_pattern: *const c_char,
    description: *const c_char,
) -> *mut c_char {
    if h.is_null() || name.is_null() || command.is_null() {
        return to_cstring("参数错误".into());
    }
    let n = unsafe { CStr::from_ptr(name) }.to_string_lossy();
    let c = unsafe { CStr::from_ptr(command) }.to_string_lossy();
    let wp = if window_pattern.is_null() { "".into() } else { unsafe { CStr::from_ptr(window_pattern) }.to_string_lossy().to_string() };
    let d = if description.is_null() { "".into() } else { unsafe { CStr::from_ptr(description) }.to_string_lossy().to_string() };
    let cmd = unsafe { (*h).add_command(&n, &c, &wp, &d) };
    to_cstring(serde_json::to_string(&cmd).unwrap_or_default())
}

#[no_mangle]
pub extern "C" fn command_manager_delete_command(h: *mut CommandManager, id: *const c_char) -> bool {
    if h.is_null() || id.is_null() { return false; }
    let id_str = unsafe { CStr::from_ptr(id) }.to_string_lossy();
    unsafe { (*h).delete_command(&id_str) }
}

#[no_mangle]
pub extern "C" fn command_manager_execute_command(h: *mut CommandManager, id: *const c_char) -> *mut c_char {
    if h.is_null() || id.is_null() { return to_cstring("参数错误".into()); }
    let id_str = unsafe { CStr::from_ptr(id) }.to_string_lossy();
    match unsafe { (*h).execute_command(&id_str) } {
        Ok(msg) => to_cstring(msg),
        Err(e) => to_cstring(e),
    }
}
