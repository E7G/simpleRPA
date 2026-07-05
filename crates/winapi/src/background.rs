#[cfg(windows)]
use windows_sys::Win32::UI::WindowsAndMessaging::*;
#[cfg(windows)]
use windows_sys::Win32::Foundation::*;

use serde::{Deserialize, Serialize};

const WM_LBUTTONDOWN: u32 = 0x0201;
const WM_LBUTTONUP: u32 = 0x0202;
const WM_RBUTTONDOWN: u32 = 0x0204;
const WM_RBUTTONUP: u32 = 0x0205;
const WM_MOUSEMOVE: u32 = 0x0200;
const WM_MBUTTONDOWN: u32 = 0x0207;
const WM_MBUTTONUP: u32 = 0x0208;
const MK_LBUTTON: u32 = 0x0001;
const MK_RBUTTON: u32 = 0x0002;
const MK_MBUTTON: u32 = 0x0010;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BackgroundClickResult {
    pub success: bool,
    pub message: String,
    pub used_background: bool,
}

pub struct BackgroundClicker {
    main_hwnd: Option<i64>,
    render_hwnd: Option<i64>,
    title: String,
}

impl BackgroundClicker {
    pub fn new(hwnd: Option<i64>, window_title: Option<&str>) -> Self {
        let mut clicker = Self {
            main_hwnd: None,
            render_hwnd: None,
            title: String::new(),
        };

        if let Some(h) = hwnd {
            clicker.attach_by_hwnd(h);
        } else if let Some(title) = window_title {
            clicker.attach(title);
        }

        clicker
    }

    pub fn is_available(&self) -> bool {
        self.main_hwnd.is_some()
    }

    pub fn hwnd(&self) -> Option<i64> {
        self.main_hwnd
    }

    #[cfg(windows)]
    pub fn attach(&mut self, title_keyword: &str) -> bool {
        use crate::window::WindowUtils;

        let utils = WindowUtils::new();
        let windows = utils.get_all_windows();
        if let Some(w) = windows.into_iter().find(|w| w.title.to_lowercase().contains(&title_keyword.to_lowercase())) {
            self.main_hwnd = Some(w.hwnd);
            self.title = w.title;
            self.find_render_window();
            true
        } else {
            false
        }
    }

    #[cfg(not(windows))]
    pub fn attach(&mut self, _title_keyword: &str) -> bool {
        false
    }

    #[cfg(windows)]
    pub fn attach_by_hwnd(&mut self, hwnd: i64) -> bool {
        unsafe {
            if IsWindow(hwnd as HWND) == 0 {
                return false;
            }
            let mut title_buf = [0u16; 512];
            let len = GetWindowTextW(hwnd as HWND, title_buf.as_mut_ptr(), 512);
            self.main_hwnd = Some(hwnd);
            self.title = String::from_utf16_lossy(&title_buf[..len as usize]);
            self.find_render_window();
            true
        }
    }

    #[cfg(not(windows))]
    pub fn attach_by_hwnd(&mut self, _hwnd: i64) -> bool {
        false
    }

    #[cfg(windows)]
    fn find_render_window(&mut self) {
        unsafe {
            self.render_hwnd = None;
            let hwnd = self.main_hwnd.unwrap_or(0) as HWND;

            unsafe extern "system" fn enum_child_callback(child_hwnd: HWND, lparam: LPARAM) -> BOOL {
                unsafe {
                    let mut class_buf = [0u16; 256];
                    GetClassNameW(child_hwnd, class_buf.as_mut_ptr(), 256);
                    let class_name = String::from_utf16_lossy(&class_buf);
                    let result = &mut *(lparam as *mut Option<i64>);
                    if class_name.contains("Chrome_RenderWidgetHostHWND") {
                        *result = Some(child_hwnd as i64);
                    }
                    1
                }
            }

            let mut render_hwnd: Option<i64> = None;
            EnumChildWindows(hwnd, Some(enum_child_callback), &mut render_hwnd as *mut Option<i64> as LPARAM);
            self.render_hwnd = render_hwnd;
        }
    }

    #[cfg(not(windows))]
    fn find_render_window(&mut self) {}

    fn target_hwnd(&self) -> Option<i64> {
        self.render_hwnd.or(self.main_hwnd)
    }

    fn make_lparam(x: i32, y: i32) -> usize {
        ((y as usize) << 16) | ((x as usize) & 0xFFFF)
    }

    #[cfg(windows)]
    pub fn click(&self, x: i32, y: i32, button: &str, background: bool) -> BackgroundClickResult {
        if !background {
            return BackgroundClickResult {
                success: false,
                message: "前台点击需要 GUI 层处理".into(),
                used_background: false,
            };
        }

        let target = match self.target_hwnd() {
            Some(h) => h,
            None => return BackgroundClickResult {
                success: false,
                message: "未附加到窗口".into(),
                used_background: false,
            },
        };

        let lparam = Self::make_lparam(x, y);

        unsafe {
            match button {
                "right" => {
                    SendNotifyMessageW(target as HWND, WM_MOUSEMOVE, 0, lparam as LPARAM);
                    SendNotifyMessageW(target as HWND, WM_RBUTTONDOWN, MK_RBUTTON as WPARAM, lparam as LPARAM);
                    SendNotifyMessageW(target as HWND, WM_RBUTTONUP, 0, lparam as LPARAM);
                }
                "middle" => {
                    SendNotifyMessageW(target as HWND, WM_MOUSEMOVE, 0, lparam as LPARAM);
                    SendNotifyMessageW(target as HWND, WM_MBUTTONDOWN, MK_MBUTTON as WPARAM, lparam as LPARAM);
                    SendNotifyMessageW(target as HWND, WM_MBUTTONUP, 0, lparam as LPARAM);
                }
                _ => {
                    SendNotifyMessageW(target as HWND, WM_MOUSEMOVE, 0, lparam as LPARAM);
                    SendNotifyMessageW(target as HWND, WM_LBUTTONDOWN, MK_LBUTTON as WPARAM, lparam as LPARAM);
                    SendNotifyMessageW(target as HWND, WM_LBUTTONUP, 0, lparam as LPARAM);
                }
            }
        }

        BackgroundClickResult {
            success: true,
            message: "后台点击成功".into(),
            used_background: true,
        }
    }

    #[cfg(not(windows))]
    pub fn click(&self, _x: i32, _y: i32, _button: &str, _background: bool) -> BackgroundClickResult {
        BackgroundClickResult {
            success: false,
            message: "仅支持 Windows".into(),
            used_background: false,
        }
    }

    #[cfg(windows)]
    pub fn move_mouse(&self, x: i32, y: i32, background: bool) -> BackgroundClickResult {
        if !background {
            return BackgroundClickResult {
                success: false,
                message: "前台移动需要 GUI 层处理".into(),
                used_background: false,
            };
        }

        let target = match self.target_hwnd() {
            Some(h) => h,
            None => return BackgroundClickResult {
                success: false,
                message: "未附加到窗口".into(),
                used_background: false,
            },
        };

        let lparam = Self::make_lparam(x, y);
        unsafe {
            SendNotifyMessageW(target as HWND, WM_MOUSEMOVE, 0, lparam as LPARAM);
        }

        BackgroundClickResult {
            success: true,
            message: "后台移动成功".into(),
            used_background: true,
        }
    }

    #[cfg(not(windows))]
    pub fn move_mouse(&self, _x: i32, _y: i32, _background: bool) -> BackgroundClickResult {
        BackgroundClickResult {
            success: false,
            message: "仅支持 Windows".into(),
            used_background: false,
        }
    }
}
