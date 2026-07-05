#[cfg(target_os = "windows")]
pub mod win32 {
    use winapi::shared::minwindef::{DWORD, FALSE, LONG, UINT};
    use winapi::shared::windef::{HWND, POINT, RECT};
    use winapi::um::winuser::*;

    pub type Hwnd = HWND;

    #[derive(Debug, Clone)]
    pub struct WindowInfo {
        pub hwnd: Hwnd,
        pub title: String,
        pub rect: (i32, i32, i32, i32),
        pub width: i32,
        pub height: i32,
        pub x: i32,
        pub y: i32,
    }

    pub fn get_all_windows() -> Vec<WindowInfo> {
        unsafe {
            let mut windows = Vec::new();
            EnumWindows(Some(enum_windows_callback), &mut windows as *mut _ as _);
            windows
        }
    }

    unsafe extern "system" fn enum_windows_callback(hwnd: HWND, lparam: LPARAM) -> BOOL {
        let windows = &mut *(lparam as *mut Vec<WindowInfo>);
        if IsWindowVisible(hwnd) != 0 {
            let mut title_buf = [0u16; 512];
            let len = GetWindowTextW(hwnd, title_buf.as_mut_ptr(), 512);
            if len > 0 {
                let title = String::from_utf16_lossy(&title_buf[..len as usize]);
                let mut rect = RECT { left: 0, top: 0, right: 0, bottom: 0 };
                GetWindowRect(hwnd, &mut rect);
                let width = rect.right - rect.left;
                let height = rect.bottom - rect.top;
                windows.push(WindowInfo {
                    hwnd,
                    title,
                    rect: (rect.left, rect.top, rect.right, rect.bottom),
                    width,
                    height,
                    x: rect.left,
                    y: rect.top,
                });
            }
        }
        1 // TRUE
    }

    pub fn get_window_by_title(title: &str) -> Option<WindowInfo> {
        let windows = get_all_windows();
        windows
            .into_iter()
            .find(|w| w.title.to_lowercase().contains(&title.to_lowercase()))
    }

    pub fn get_window_by_hwnd(hwnd: Hwnd) -> Option<WindowInfo> {
        unsafe {
            if IsWindow(hwnd) == 0 {
                return None;
            }
            let mut title_buf = [0u16; 512];
            let len = GetWindowTextW(hwnd, title_buf.as_mut_ptr(), 512);
            let title = if len > 0 {
                String::from_utf16_lossy(&title_buf[..len as usize])
            } else {
                String::new()
            };
            let mut rect = RECT { left: 0, top: 0, right: 0, bottom: 0 };
            GetWindowRect(hwnd, &mut rect);
            let width = rect.right - rect.left;
            let height = rect.bottom - rect.top;
            Some(WindowInfo {
                hwnd,
                title,
                rect: (rect.left, rect.top, rect.right, rect.bottom),
                width,
                height,
                x: rect.left,
                y: rect.top,
            })
        }
    }

    pub fn activate_window(hwnd: Hwnd) -> bool {
        unsafe {
            ShowWindow(hwnd, SW_RESTORE);
            SetForegroundWindow(hwnd);
            true
        }
    }

    pub fn get_cursor_pos() -> (i32, i32) {
        unsafe {
            let mut pt = POINT { x: 0, y: 0 };
            GetCursorPos(&mut pt);
            (pt.x, pt.y)
        }
    }

    pub fn screen_to_client(hwnd: Hwnd, x: i32, y: i32) -> Option<(i32, i32)> {
        unsafe {
            let mut pt = POINT { x, y };
            if ScreenToClient(hwnd, &mut pt) != 0 {
                Some((pt.x, pt.y))
            } else {
                None
            }
        }
    }

    pub fn client_to_screen(hwnd: Hwnd, x: i32, y: i32) -> Option<(i32, i32)> {
        unsafe {
            let mut pt = POINT { x, y };
            if ClientToScreen(hwnd, &mut pt) != 0 {
                Some((pt.x, pt.y))
            } else {
                None
            }
        }
    }

    pub fn get_client_rect_screen(hwnd: Hwnd) -> Option<(i32, i32, i32, i32)> {
        let tl = client_to_screen(hwnd, 0, 0)?;
        let mut rc = RECT { left: 0, top: 0, right: 0, bottom: 0 };
        unsafe { GetClientRect(hwnd, &mut rc); }
        let br = client_to_screen(hwnd, rc.right, rc.bottom)?;
        Some((tl.0, tl.1, br.0, br.1))
    }

    pub fn move_window_offscreen(hwnd: Hwnd) -> Option<serde_json::Value> {
        unsafe {
            if IsWindow(hwnd) == 0 {
                return None;
            }
            let mut rect = RECT { left: 0, top: 0, right: 0, bottom: 0 };
            GetWindowRect(hwnd, &mut rect);
            let width = (rect.right - rect.left).max(1);
            let height = (rect.bottom - rect.top).max(1);
            if IsIconic(hwnd) != 0 {
                ShowWindow(hwnd, SW_SHOWNOACTIVATE);
            }
            let virtual_left = GetSystemMetrics(76);
            let virtual_top = GetSystemMetrics(77);
            let virtual_width = GetSystemMetrics(78);
            let virtual_height = GetSystemMetrics(79);
            let offscreen_x = virtual_left + virtual_width + 120;
            let max_top = virtual_top + (virtual_height - height - 40).max(0);
            let offscreen_y = rect.top.max(virtual_top + 40).min(max_top);
            SetWindowPos(hwnd, std::ptr::null_mut(), offscreen_x, offscreen_y, width, height, SWP_NOZORDER | SWP_NOACTIVATE);
            UpdateWindow(hwnd);
            Some(serde_json::json!({
                "rect": [rect.left, rect.top, rect.right, rect.bottom],
            }))
        }
    }

    pub fn restore_window_placement(hwnd: Hwnd, info: &serde_json::Value) -> bool {
        unsafe {
            if IsWindow(hwnd) == 0 {
                return false;
            }
            if let Some(rect_arr) = info.get("rect").and_then(|v| v.as_array()) {
                if rect_arr.len() == 4 {
                    let x = rect_arr[0].as_i64().unwrap_or(0) as i32;
                    let y = rect_arr[1].as_i64().unwrap_or(0) as i32;
                    let w = (rect_arr[2].as_i64().unwrap_or(0) as i32 - x).max(1);
                    let h = (rect_arr[3].as_i64().unwrap_or(0) as i32 - y).max(1);
                    SetWindowPos(hwnd, std::ptr::null_mut(), x, y, w, h, SWP_NOZORDER | SWP_NOACTIVATE);
                }
            }
            ShowWindow(hwnd, SW_SHOWNOACTIVATE);
            UpdateWindow(hwnd);
            true
        }
    }

    pub fn set_window_taskbar_visibility(hwnd: Hwnd, visible: bool) -> Option<serde_json::Value> {
        unsafe {
            if IsWindow(hwnd) == 0 {
                return None;
            }
            let gwls = GetWindowLongW(hwnd, GWL_EXSTYLE) as u32;
            let mut desired = gwls;
            if visible {
                desired |= WS_EX_APPWINDOW as u32;
                desired &= !(WS_EX_TOOLWINDOW as u32);
            } else {
                desired &= !(WS_EX_APPWINDOW as u32);
                desired |= WS_EX_TOOLWINDOW as u32;
            }
            if desired != gwls {
                SetWindowLongW(hwnd, GWL_EXSTYLE, desired as i32);
                SetWindowPos(hwnd, std::ptr::null_mut(), 0, 0, 0, 0,
                    SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED);
                UpdateWindow(hwnd);
            }
            Some(serde_json::json!({ "exstyle": gwls }))
        }
    }

    pub fn restore_window_taskbar_visibility(hwnd: Hwnd, state: &serde_json::Value) -> bool {
        unsafe {
            if IsWindow(hwnd) == 0 {
                return false;
            }
            if let Some(exstyle) = state.get("exstyle").and_then(|v| v.as_i64()) {
                SetWindowLongW(hwnd, GWL_EXSTYLE, exstyle as i32);
                SetWindowPos(hwnd, std::ptr::null_mut(), 0, 0, 0, 0,
                    SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED);
                UpdateWindow(hwnd);
                return true;
            }
            false
        }
    }

    pub fn send_notify_message(hwnd: Hwnd, msg: UINT, wparam: WPARAM, lparam: LPARAM) {
        unsafe {
            SendNotifyMessageW(hwnd, msg, wparam, lparam);
        }
    }

    pub fn make_lparam(x: i32, y: i32) -> LPARAM {
        ((y as u32) << 16 | (x as u32 & 0xFFFF)) as LPARAM
    }

    pub fn get_idle_seconds() -> f64 {
        unsafe {
            #[repr(C)]
            struct LASTINPUTINFO {
                cb_size: UINT,
                dw_time: DWORD,
            }
            let mut lii = LASTINPUTINFO { cb_size: std::mem::size_of::<LASTINPUTINFO>() as UINT, dw_time: 0 };
            if GetLastInputInfo(&mut lii as *mut _ as _) != 0 {
                let tick = GetTickCount();
                let millis = tick.wrapping_sub(lii.dw_time);
                return millis as f64 / 1000.0;
            }
            0.0
        }
    }
}

#[cfg(not(target_os = "windows"))]
pub mod win32 {
    pub type Hwnd = *mut std::ffi::c_void;

    #[derive(Debug, Clone)]
    pub struct WindowInfo {
        pub hwnd: Hwnd,
        pub title: String,
        pub rect: (i32, i32, i32, i32),
        pub width: i32,
        pub height: i32,
        pub x: i32,
        pub y: i32,
    }

    pub fn get_all_windows() -> Vec<WindowInfo> { Vec::new() }
    pub fn get_cursor_pos() -> (i32, i32) { (0, 0) }
    pub fn get_idle_seconds() -> f64 { 0.0 }
}
