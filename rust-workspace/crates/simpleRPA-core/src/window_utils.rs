#[cfg(target_os = "windows")]
use winapi::shared::windef::RECT;

#[derive(Debug, Clone)]
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

pub struct WindowUtils {
    #[cfg(target_os = "windows")]
    win32_available: bool,
}

impl WindowUtils {
    pub fn new() -> Self {
        Self {
            #[cfg(target_os = "windows")]
            win32_available: true,
        }
    }

    pub fn is_win32_available(&self) -> bool {
        #[cfg(target_os = "windows")]
        {
            self.win32_available
        }
        #[cfg(not(target_os = "windows"))]
        {
            false
        }
    }

    pub fn get_all_windows(&self) -> Vec<WindowInfo> {
        #[cfg(target_os = "windows")]
        {
            return self.get_all_windows_win32();
        }
        #[cfg(not(target_os = "windows"))]
        {
            Vec::new()
        }
    }

    #[cfg(target_os = "windows")]
    fn get_all_windows_win32(&self) -> Vec<WindowInfo> {
        use winapi::um::winuser::*;

        let mut windows = Vec::new();

        unsafe {
            EnumWindows(Some(enum_windows_callback), &mut windows as *mut _ as isize);
        }

        windows
    }

    pub fn get_window_by_title(&self, title: &str) -> Option<WindowInfo> {
        self.get_all_windows()
            .into_iter()
            .find(|w| w.title.to_lowercase().contains(&title.to_lowercase()))
    }

    pub fn get_window_by_hwnd(&self, hwnd: i64) -> Option<WindowInfo> {
        #[cfg(target_os = "windows")]
        {
            return self.get_window_by_hwnd_win32(hwnd);
        }
        #[cfg(not(target_os = "windows"))]
        {
            None
        }
    }

    #[cfg(target_os = "windows")]
    fn get_window_by_hwnd_win32(&self, hwnd: i64) -> Option<WindowInfo> {
        use winapi::um::winuser::*;

        unsafe {
            if IsWindow(hwnd as _) == 0 {
                return None;
            }

            let mut title_buf = [0u16; 512];
            let len = GetWindowTextW(hwnd as _, title_buf.as_mut_ptr(), 512);
            let title = String::from_utf16_lossy(&title_buf[..len as usize]);

            let mut rect = std::mem::zeroed::<RECT>();
            GetWindowRect(hwnd as _, &mut rect);

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

    pub fn activate_window(&self, hwnd: i64) -> bool {
        #[cfg(target_os = "windows")]
        {
            return self.activate_window_win32(hwnd);
        }
        #[cfg(not(target_os = "windows"))]
        {
            false
        }
    }

    #[cfg(target_os = "windows")]
    fn activate_window_win32(&self, hwnd: i64) -> bool {
        use winapi::um::winuser::*;

        unsafe {
            ShowWindow(hwnd as _, SW_RESTORE);
            SetForegroundWindow(hwnd as _);
            true
        }
    }

    pub fn move_window_offscreen(&self, hwnd: i64) -> Option<WindowPlacement> {
        #[cfg(target_os = "windows")]
        {
            return self.move_window_offscreen_win32(hwnd);
        }
        #[cfg(not(target_os = "windows"))]
        {
            None
        }
    }

    #[cfg(target_os = "windows")]
    fn move_window_offscreen_win32(&self, hwnd: i64) -> Option<WindowPlacement> {
        use winapi::um::winuser::*;

        unsafe {
            if IsWindow(hwnd as _) == 0 {
                return None;
            }

            let mut rect = std::mem::zeroed::<RECT>();
            GetWindowRect(hwnd as _, &mut rect);
            let width = (rect.right - rect.left).max(1);
            let height = (rect.bottom - rect.top).max(1);

            let placement = WindowPlacement {
                rect: (rect.left, rect.top, rect.right, rect.bottom),
                show_cmd: SW_SHOWNORMAL,
            };

            if IsIconic(hwnd as _) != 0 {
                ShowWindow(hwnd as _, SW_SHOWNOACTIVATE);
            }

            let virtual_left = GetSystemMetrics(76);
            let virtual_top = GetSystemMetrics(77);
            let virtual_width = GetSystemMetrics(78);
            let virtual_height = GetSystemMetrics(79);

            let offscreen_x = virtual_left + virtual_width + 120;
            let max_top = virtual_top + (virtual_height - height - 40).max(0);
            let offscreen_y = rect.top.max(virtual_top + 40).min(max_top);

            SetWindowPos(
                hwnd as _,
                std::ptr::null_mut(),
                offscreen_x,
                offscreen_y,
                width,
                height,
                SWP_NOZORDER | SWP_NOACTIVATE,
            );

            Some(placement)
        }
    }

    pub fn restore_window_placement(&self, hwnd: i64, placement: &WindowPlacement) -> bool {
        #[cfg(target_os = "windows")]
        {
            return self.restore_window_placement_win32(hwnd, placement);
        }
        #[cfg(not(target_os = "windows"))]
        {
            let _ = (hwnd, placement);
            false
        }
    }

    #[cfg(target_os = "windows")]
    fn restore_window_placement_win32(&self, hwnd: i64, placement: &WindowPlacement) -> bool {
        use winapi::um::winuser::*;

        unsafe {
            if IsWindow(hwnd as _) == 0 {
                return false;
            }

            let (left, top, right, bottom) = placement.rect;
            let width = (right - left).max(1);
            let height = (bottom - top).max(1);

            ShowWindow(hwnd as _, placement.show_cmd);
            SetWindowPos(
                hwnd as _,
                std::ptr::null_mut(),
                left,
                top,
                width,
                height,
                SWP_NOZORDER | SWP_NOACTIVATE,
            ) != 0
        }
    }

    pub fn set_window_taskbar_visibility(
        &self,
        hwnd: i64,
        visible: bool,
    ) -> Option<WindowTaskbarState> {
        #[cfg(target_os = "windows")]
        {
            return self.set_window_taskbar_visibility_win32(hwnd, visible);
        }
        #[cfg(not(target_os = "windows"))]
        {
            let _ = (hwnd, visible);
            None
        }
    }

    #[cfg(target_os = "windows")]
    fn set_window_taskbar_visibility_win32(
        &self,
        hwnd: i64,
        visible: bool,
    ) -> Option<WindowTaskbarState> {
        use winapi::um::winuser::*;

        const GWL_EXSTYLE: i32 = -20;
        const WS_EX_APPWINDOW: i32 = 0x00040000;
        const WS_EX_TOOLWINDOW: i32 = 0x00000080;

        unsafe {
            if IsWindow(hwnd as _) == 0 {
                return None;
            }

            let original_exstyle = GetWindowLongW(hwnd as _, GWL_EXSTYLE);
            let mut desired_exstyle = original_exstyle;
            if visible {
                desired_exstyle |= WS_EX_APPWINDOW;
                desired_exstyle &= !WS_EX_TOOLWINDOW;
            } else {
                desired_exstyle &= !WS_EX_APPWINDOW;
                desired_exstyle |= WS_EX_TOOLWINDOW;
            }

            if desired_exstyle != original_exstyle {
                SetWindowLongW(hwnd as _, GWL_EXSTYLE, desired_exstyle);
                SetWindowPos(
                    hwnd as _,
                    std::ptr::null_mut(),
                    0,
                    0,
                    0,
                    0,
                    SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED,
                );
                UpdateWindow(hwnd as _);
            }

            Some(WindowTaskbarState { original_exstyle })
        }
    }

    pub fn restore_window_taskbar_visibility(&self, hwnd: i64, state: &WindowTaskbarState) -> bool {
        #[cfg(target_os = "windows")]
        {
            return self.restore_window_taskbar_visibility_win32(hwnd, state);
        }
        #[cfg(not(target_os = "windows"))]
        {
            let _ = (hwnd, state);
            false
        }
    }

    #[cfg(target_os = "windows")]
    fn restore_window_taskbar_visibility_win32(
        &self,
        hwnd: i64,
        state: &WindowTaskbarState,
    ) -> bool {
        use winapi::um::winuser::*;

        const GWL_EXSTYLE: i32 = -20;

        unsafe {
            if IsWindow(hwnd as _) == 0 {
                return false;
            }

            SetWindowLongW(hwnd as _, GWL_EXSTYLE, state.original_exstyle);
            SetWindowPos(
                hwnd as _,
                std::ptr::null_mut(),
                0,
                0,
                0,
                0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED,
            );
            UpdateWindow(hwnd as _);
            true
        }
    }

    pub fn screen_to_client_coords(
        &self,
        hwnd: i64,
        screen_x: i32,
        screen_y: i32,
    ) -> Option<(i32, i32)> {
        #[cfg(target_os = "windows")]
        {
            use winapi::shared::windef::POINT;
            use winapi::um::winuser::*;

            unsafe {
                let mut point = POINT {
                    x: screen_x,
                    y: screen_y,
                };
                if ScreenToClient(hwnd as _, &mut point) != 0 {
                    return Some((point.x, point.y));
                }
            }
        }
        None
    }

    pub fn client_to_screen_coords(
        &self,
        hwnd: i64,
        client_x: i32,
        client_y: i32,
    ) -> Option<(i32, i32)> {
        #[cfg(target_os = "windows")]
        {
            use winapi::shared::windef::POINT;
            use winapi::um::winuser::*;

            unsafe {
                let mut point = POINT {
                    x: client_x,
                    y: client_y,
                };
                if ClientToScreen(hwnd as _, &mut point) != 0 {
                    return Some((point.x, point.y));
                }
            }
        }
        None
    }

    pub fn get_client_rect_screen(&self, hwnd: i64) -> Option<(i32, i32, i32, i32)> {
        #[cfg(target_os = "windows")]
        {
            use winapi::um::winuser::*;

            unsafe {
                let mut rect = std::mem::zeroed::<RECT>();
                GetClientRect(hwnd as _, &mut rect);
                let top_left = self.client_to_screen_coords(hwnd, rect.left, rect.top)?;
                let bottom_right = self.client_to_screen_coords(hwnd, rect.right, rect.bottom)?;
                return Some((top_left.0, top_left.1, bottom_right.0, bottom_right.1));
            }
        }
        #[cfg(not(target_os = "windows"))]
        {
            None
        }
    }
}

#[derive(Debug, Clone)]
pub struct WindowPlacement {
    pub rect: (i32, i32, i32, i32),
    pub show_cmd: i32,
}

#[derive(Debug, Clone)]
pub struct WindowTaskbarState {
    pub original_exstyle: i32,
}

#[cfg(target_os = "windows")]
unsafe extern "system" fn enum_windows_callback(
    hwnd: winapi::shared::windef::HWND,
    lparam: isize,
) -> i32 {
    use winapi::um::winuser::*;

    let windows = &mut *(lparam as *mut Vec<WindowInfo>);

    if IsWindowVisible(hwnd) != 0 {
        let mut title_buf = [0u16; 512];
        let len = GetWindowTextW(hwnd, title_buf.as_mut_ptr(), 512);
        let title = String::from_utf16_lossy(&title_buf[..len as usize]);

        if !title.is_empty() {
            let mut rect = std::mem::zeroed::<RECT>();
            GetWindowRect(hwnd, &mut rect);

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
