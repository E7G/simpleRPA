#[cfg(windows)]
use windows_sys::Win32::UI::WindowsAndMessaging::*;
#[cfg(windows)]
use windows_sys::Win32::Foundation::*;
#[cfg(windows)]
use windows_sys::Win32::Graphics::Gdi::*;

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WindowInfo {
    pub hwnd: i64,
    pub title: String,
    pub x: i32,
    pub y: i32,
    pub width: i32,
    pub height: i32,
}

impl WindowInfo {
    pub fn center(&self) -> (i32, i32) {
        (self.x + self.width / 2, self.y + self.height / 2)
    }
}

pub struct WindowUtils;

impl WindowUtils {
    pub fn new() -> Self {
        Self
    }

    #[cfg(windows)]
    pub fn get_all_windows(&self) -> Vec<WindowInfo> {
        unsafe {
            let mut windows = Vec::new();
            let param = &mut windows as *mut Vec<WindowInfo> as isize;
            EnumWindows(Some(enum_windows_callback), param);
            windows
        }
    }

    #[cfg(not(windows))]
    pub fn get_all_windows(&self) -> Vec<WindowInfo> {
        Vec::new()
    }

    pub fn get_window_by_title(&self, title: &str) -> Option<WindowInfo> {
        self.get_all_windows()
            .into_iter()
            .find(|w| w.title.to_lowercase().contains(&title.to_lowercase()))
    }

    #[cfg(windows)]
    pub fn get_window_by_hwnd(&self, hwnd: i64) -> Option<WindowInfo> {
        unsafe {
            if IsWindow(hwnd as HWND) == 0 {
                return None;
            }
            let mut title_buf = [0u16; 512];
            let len = GetWindowTextW(hwnd as HWND, title_buf.as_mut_ptr(), 512);
            let title = String::from_utf16_lossy(&title_buf[..len as usize]);

            let mut rect = RECT { left: 0, top: 0, right: 0, bottom: 0 };
            GetWindowRect(hwnd as HWND, &mut rect);

            Some(WindowInfo {
                hwnd,
                title,
                x: rect.left,
                y: rect.top,
                width: rect.right - rect.left,
                height: rect.bottom - rect.top,
            })
        }
    }

    #[cfg(not(windows))]
    pub fn get_window_by_hwnd(&self, _hwnd: i64) -> Option<WindowInfo> {
        None
    }

    #[cfg(windows)]
    pub fn activate_window(&self, hwnd: i64) -> bool {
        unsafe {
            ShowWindow(hwnd as HWND, SW_RESTORE);
            SetForegroundWindow(hwnd as HWND) != 0
        }
    }

    #[cfg(not(windows))]
    pub fn activate_window(&self, _hwnd: i64) -> bool {
        false
    }

    #[cfg(windows)]
    pub fn move_window_offscreen(&self, hwnd: i64) -> Option<serde_json::Value> {
        unsafe {
            if IsWindow(hwnd as HWND) == 0 {
                return None;
            }

            let mut rect = RECT { left: 0, top: 0, right: 0, bottom: 0 };
            GetWindowRect(hwnd as HWND, &mut rect);
            let width = (rect.right - rect.left).max(1);
            let height = (rect.bottom - rect.top).max(1);

            if IsIconic(hwnd as HWND) != 0 {
                ShowWindow(hwnd as HWND, SW_SHOWNOACTIVATE);
            }

            let virtual_left = GetSystemMetrics(76);
            let virtual_top = GetSystemMetrics(77);
            let virtual_width = GetSystemMetrics(78);
            let virtual_height = GetSystemMetrics(79);

            let offscreen_x = virtual_left + virtual_width + 120;
            let max_top = virtual_top + (virtual_height - height - 40).max(0);
            let offscreen_y = rect.top.clamp(virtual_top + 40, max_top);

            SetWindowPos(
                hwnd as HWND,
                0 as HWND,
                offscreen_x,
                offscreen_y,
                width,
                height,
                SWP_NOZORDER | SWP_NOACTIVATE,
            );

            Some(serde_json::json!({
                "rect": [rect.left, rect.top, rect.right, rect.bottom],
            }))
        }
    }

    #[cfg(not(windows))]
    pub fn move_window_offscreen(&self, _hwnd: i64) -> Option<serde_json::Value> {
        None
    }

    #[cfg(windows)]
    pub fn set_window_taskbar_visibility(&self, hwnd: i64, visible: bool) -> Option<serde_json::Value> {
        unsafe {
            if IsWindow(hwnd as HWND) == 0 {
                return None;
            }

            let gwlexstyle: i32 = -20;
            let ws_ex_appwindow: u32 = 0x00040000;
            let ws_ex_toolwindow: u32 = 0x00000080;

            let current_exstyle = GetWindowLongW(hwnd as HWND, gwlexstyle) as u32;
            let mut desired_exstyle = current_exstyle;

            if visible {
                desired_exstyle |= ws_ex_appwindow;
                desired_exstyle &= !ws_ex_toolwindow;
            } else {
                desired_exstyle &= !ws_ex_appwindow;
                desired_exstyle |= ws_ex_toolwindow;
            }

            if desired_exstyle != current_exstyle {
                SetWindowLongW(hwnd as HWND, gwlexstyle, desired_exstyle as i32);
                SetWindowPos(
                    hwnd as HWND,
                    0 as HWND,
                    0, 0, 0, 0,
                    SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED,
                );
                UpdateWindow(hwnd as HWND);
            }

            Some(serde_json::json!({"exstyle": current_exstyle}))
        }
    }

    #[cfg(not(windows))]
    pub fn set_window_taskbar_visibility(&self, _hwnd: i64, _visible: bool) -> Option<serde_json::Value> {
        None
    }

    #[cfg(windows)]
    pub fn restore_window_taskbar_visibility(&self, hwnd: i64, state: &serde_json::Value) -> bool {
        unsafe {
            if IsWindow(hwnd as HWND) == 0 {
                return false;
            }

            let gwlexstyle: i32 = -20;
            let original_exstyle = state.get("exstyle").and_then(|v: &serde_json::Value| v.as_u64()).unwrap_or(0) as i32;

            SetWindowLongW(hwnd as HWND, gwlexstyle, original_exstyle);
            SetWindowPos(
                hwnd as HWND,
                0 as HWND,
                0, 0, 0, 0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED,
            );
            UpdateWindow(hwnd as HWND);
            true
        }
    }

    #[cfg(not(windows))]
    pub fn restore_window_taskbar_visibility(&self, _hwnd: i64, _state: &serde_json::Value) -> bool {
        false
    }

    #[cfg(windows)]
    pub fn restore_window_placement(&self, hwnd: i64, placement: &serde_json::Value) -> bool {
        unsafe {
            if IsWindow(hwnd as HWND) == 0 {
                return false;
            }

            if let Some(serde_json::Value::Array(rect_arr)) = placement.get("rect") {
                if rect_arr.len() == 4 {
                    let left = rect_arr[0].as_i64().unwrap_or(0) as i32;
                    let top = rect_arr[1].as_i64().unwrap_or(0) as i32;
                    let right = rect_arr[2].as_i64().unwrap_or(0) as i32;
                    let bottom = rect_arr[3].as_i64().unwrap_or(0) as i32;
                    let width = (right - left).max(1);
                    let height = (bottom - top).max(1);
                    SetWindowPos(
                        hwnd as HWND,
                        0 as HWND,
                        left, top, width, height,
                        SWP_NOZORDER | SWP_NOACTIVATE,
                    );
                }
            }

            ShowWindow(hwnd as HWND, SW_SHOWNOACTIVATE);
            true
        }
    }

    #[cfg(not(windows))]
    pub fn restore_window_placement(&self, _hwnd: i64, _placement: &serde_json::Value) -> bool {
        false
    }

    #[cfg(windows)]
    pub fn screen_to_client_coords(&self, hwnd: i64, screen_x: i32, screen_y: i32) -> Option<(i32, i32)> {
        unsafe {
            let mut point = POINT { x: screen_x, y: screen_y };
            if ScreenToClient(hwnd as HWND, &mut point) != 0 {
                Some((point.x, point.y))
            } else {
                None
            }
        }
    }

    #[cfg(not(windows))]
    pub fn screen_to_client_coords(&self, _hwnd: i64, _screen_x: i32, _screen_y: i32) -> Option<(i32, i32)> {
        None
    }

    #[cfg(windows)]
    pub fn client_to_screen_coords(&self, hwnd: i64, client_x: i32, client_y: i32) -> Option<(i32, i32)> {
        unsafe {
            let mut point = POINT { x: client_x, y: client_y };
            if ClientToScreen(hwnd as HWND, &mut point) != 0 {
                Some((point.x, point.y))
            } else {
                None
            }
        }
    }

    #[cfg(not(windows))]
    pub fn client_to_screen_coords(&self, _hwnd: i64, _client_x: i32, _client_y: i32) -> Option<(i32, i32)> {
        None
    }

    #[cfg(windows)]
    pub fn get_client_rect_screen(&self, hwnd: i64) -> Option<(i32, i32, i32, i32)> {
        unsafe {
            let mut rect = RECT { left: 0, top: 0, right: 0, bottom: 0 };
            GetClientRect(hwnd as HWND, &mut rect);

            let top_left = self.client_to_screen_coords(hwnd, rect.left, rect.top)?;
            let bottom_right = self.client_to_screen_coords(hwnd, rect.right, rect.bottom)?;

            Some((top_left.0, top_left.1, bottom_right.0, bottom_right.1))
        }
    }

    #[cfg(not(windows))]
    pub fn get_client_rect_screen(&self, _hwnd: i64) -> Option<(i32, i32, i32, i32)> {
        None
    }
}

#[cfg(windows)]
unsafe extern "system" fn enum_windows_callback(hwnd: HWND, lparam: LPARAM) -> BOOL {
    unsafe {
        if IsWindowVisible(hwnd) != 0 {
            let mut title_buf = [0u16; 512];
            let len = GetWindowTextW(hwnd, title_buf.as_mut_ptr(), 512);
            if len > 0 {
                let title = String::from_utf16_lossy(&title_buf[..len as usize]);
                let mut rect = RECT { left: 0, top: 0, right: 0, bottom: 0 };
                GetWindowRect(hwnd, &mut rect);

                let windows = &mut *(lparam as *mut Vec<WindowInfo>);
                windows.push(WindowInfo {
                    hwnd: hwnd as i64,
                    title,
                    x: rect.left,
                    y: rect.top,
                    width: rect.right - rect.left,
                    height: rect.bottom - rect.top,
                });
            }
        }
        1
    }
}
