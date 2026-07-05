#[derive(Debug, Clone)]
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
    pub fn new(window_title: Option<&str>, hwnd: Option<i64>) -> Option<Self> {
        let mut clicker = Self {
            main_hwnd: None,
            render_hwnd: None,
            title: String::new(),
        };

        if let Some(h) = hwnd {
            if clicker.attach_by_hwnd(h) {
                Some(clicker)
            } else {
                None
            }
        } else if let Some(title) = window_title {
            if clicker.attach(title) {
                Some(clicker)
            } else {
                None
            }
        } else {
            None
        }
    }

    pub fn is_available(&self) -> bool {
        self.main_hwnd.is_some()
    }

    pub fn hwnd(&self) -> i64 {
        self.main_hwnd.unwrap_or(0)
    }

    pub fn render_hwnd(&self) -> i64 {
        self.render_hwnd
            .unwrap_or_else(|| self.main_hwnd.unwrap_or(0))
    }

    pub fn title(&self) -> &str {
        &self.title
    }

    pub fn attach(&mut self, title_keyword: &str) -> bool {
        #[cfg(target_os = "windows")]
        {
            use winapi::um::winuser::*;

            let boxed = Box::new(title_keyword.to_string());
            let ptr = Box::into_raw(boxed) as isize;
            unsafe {
                EnumWindows(Some(enum_windows_for_clicker), ptr);
            }
            return self.main_hwnd.is_some();
        }
        #[cfg(not(target_os = "windows"))]
        {
            false
        }
    }

    pub fn attach_by_hwnd(&mut self, hwnd: i64) -> bool {
        #[cfg(target_os = "windows")]
        {
            use winapi::um::winuser::*;

            unsafe {
                if IsWindow(hwnd as _) == 0 {
                    return false;
                }

                self.main_hwnd = Some(hwnd);

                let mut title_buf = [0u16; 512];
                let len = GetWindowTextW(hwnd as _, title_buf.as_mut_ptr(), 512);
                self.title = String::from_utf16_lossy(&title_buf[..len as usize]);

                self.find_render_window();
                return true;
            }
        }
        #[cfg(not(target_os = "windows"))]
        {
            false
        }
    }

    #[cfg(target_os = "windows")]
    fn find_render_window(&mut self) {
        use winapi::um::winuser::*;

        self.render_hwnd = None;

        if let Some(main_hwnd) = self.main_hwnd {
            unsafe {
                EnumChildWindows(
                    main_hwnd as _,
                    Some(enum_child_for_render),
                    &mut self.render_hwnd as *mut Option<i64> as isize,
                );
            }
        }
    }

    pub fn click(&self, x: i32, y: i32, button: &str, background: bool) -> BackgroundClickResult {
        if self.main_hwnd.is_none() {
            return BackgroundClickResult {
                success: false,
                message: "未附加到窗口".into(),
                used_background: false,
            };
        }

        if background {
            self.background_click(x, y, button)
        } else {
            self.foreground_click(x, y, button)
        }
    }

    #[cfg(target_os = "windows")]
    fn background_click(&self, x: i32, y: i32, button: &str) -> BackgroundClickResult {
        use winapi::um::winuser::*;

        let target = self.render_hwnd().max(self.main_hwnd.unwrap_or(0));
        let lparam = ((y as u32) << 16) | ((x as u32) & 0xFFFF);

        unsafe {
            let result = match button {
                "right" => {
                    SendNotifyMessageW(target as _, WM_MOUSEMOVE, 0, lparam as _);
                    SendNotifyMessageW(target as _, WM_RBUTTONDOWN, MK_RBUTTON as _, lparam as _);
                    SendNotifyMessageW(target as _, WM_RBUTTONUP, 0, lparam as _);
                    true
                }
                "middle" => {
                    SendNotifyMessageW(target as _, WM_MOUSEMOVE, 0, lparam as _);
                    SendNotifyMessageW(target as _, WM_MBUTTONDOWN, MK_MBUTTON as _, lparam as _);
                    SendNotifyMessageW(target as _, WM_MBUTTONUP, 0, lparam as _);
                    true
                }
                _ => {
                    SendNotifyMessageW(target as _, WM_MOUSEMOVE, 0, lparam as _);
                    SendNotifyMessageW(target as _, WM_LBUTTONDOWN, MK_LBUTTON as _, lparam as _);
                    SendNotifyMessageW(target as _, WM_LBUTTONUP, 0, lparam as _);
                    true
                }
            };

            BackgroundClickResult {
                success: result,
                message: if result {
                    "后台点击成功".into()
                } else {
                    "后台点击失败".into()
                },
                used_background: true,
            }
        }
    }

    #[cfg(not(target_os = "windows"))]
    fn background_click(&self, _x: i32, _y: i32, _button: &str) -> BackgroundClickResult {
        BackgroundClickResult {
            success: false,
            message: "后台点击仅支持Windows".into(),
            used_background: true,
        }
    }

    fn foreground_click(&self, _x: i32, _y: i32, _button: &str) -> BackgroundClickResult {
        BackgroundClickResult {
            success: false,
            message: "前台点击需要rdev支持".into(),
            used_background: false,
        }
    }

    pub fn move_mouse(&self, x: i32, y: i32, background: bool) -> BackgroundClickResult {
        if self.main_hwnd.is_none() {
            return BackgroundClickResult {
                success: false,
                message: "未附加到窗口".into(),
                used_background: false,
            };
        }

        if background {
            #[cfg(target_os = "windows")]
            {
                use winapi::um::winuser::*;
                let target = self.render_hwnd();
                let lparam = ((y as u32) << 16) | ((x as u32) & 0xFFFF);
                unsafe {
                    SendNotifyMessageW(target as _, WM_MOUSEMOVE, 0, lparam as _);
                }
                return BackgroundClickResult {
                    success: true,
                    message: "后台移动成功".into(),
                    used_background: true,
                };
            }
        }

        BackgroundClickResult {
            success: false,
            message: "前台移动需要rdev支持".into(),
            used_background: false,
        }
    }

    pub fn capture(&self, background: bool) -> Option<Vec<u8>> {
        if self.main_hwnd.is_none() {
            return None;
        }

        if background {
            self.background_capture()
        } else {
            self.foreground_capture()
        }
    }

    #[cfg(target_os = "windows")]
    fn background_capture(&self) -> Option<Vec<u8>> {
        use winapi::shared::windef::RECT;
        use winapi::um::wingdi::*;
        use winapi::um::winuser::*;

        let target = self.render_hwnd();

        unsafe {
            let mut rect = std::mem::zeroed::<RECT>();
            GetClientRect(target as _, &mut rect);
            let width = rect.right - rect.left;
            let height = rect.bottom - rect.top;
            if width <= 0 || height <= 0 {
                return None;
            }

            let hwnd_dc = GetWindowDC(target as _);
            if hwnd_dc.is_null() {
                return None;
            }

            let mfc_dc = CreateCompatibleDC(hwnd_dc);
            let bitmap = CreateCompatibleBitmap(hwnd_dc, width, height);
            let old = SelectObject(mfc_dc, bitmap as _);

            let result = PrintWindow(target as _, mfc_dc, 2);
            if result == 0 {
                SelectObject(mfc_dc, old);
                DeleteObject(bitmap as _);
                DeleteDC(mfc_dc);
                ReleaseDC(target as _, hwnd_dc);
                return None;
            }

            let mut bmp_info = std::mem::zeroed::<BITMAPINFO>();
            bmp_info.bmiHeader.biSize = std::mem::size_of::<BITMAPINFOHEADER>() as u32;
            bmp_info.bmiHeader.biWidth = width;
            bmp_info.bmiHeader.biHeight = -height;
            bmp_info.bmiHeader.biPlanes = 1;
            bmp_info.bmiHeader.biBitCount = 32;
            bmp_info.bmiHeader.biCompression = 0;

            let mut pixels = vec![0u8; (width * height * 4) as usize];
            GetDIBits(
                mfc_dc,
                bitmap,
                0,
                height as u32,
                pixels.as_mut_ptr() as _,
                &mut bmp_info,
                0,
            );

            SelectObject(mfc_dc, old);
            DeleteObject(bitmap as _);
            DeleteDC(mfc_dc);
            ReleaseDC(target as _, hwnd_dc);

            Some(pixels)
        }
    }

    #[cfg(not(target_os = "windows"))]
    fn background_capture(&self) -> Option<Vec<u8>> {
        None
    }

    fn foreground_capture(&self) -> Option<Vec<u8>> {
        None
    }
}

#[cfg(target_os = "windows")]
unsafe extern "system" fn enum_windows_for_clicker(
    hwnd: winapi::shared::windef::HWND,
    lparam: isize,
) -> i32 {
    use winapi::um::winuser::*;

    let keyword = &*(lparam as *const String);

    if IsWindowVisible(hwnd) != 0 {
        let mut title_buf = [0u16; 512];
        let len = GetWindowTextW(hwnd, title_buf.as_mut_ptr(), 512);
        let title = String::from_utf16_lossy(&title_buf[..len as usize]);

        if title.to_lowercase().contains(&keyword.to_lowercase()) {
            let data = &mut *(lparam as *const String as *mut (String, Option<i64>));
            data.1 = Some(hwnd as i64);
            return 0;
        }
    }

    1
}

#[cfg(target_os = "windows")]
unsafe extern "system" fn enum_child_for_render(
    hwnd: winapi::shared::windef::HWND,
    lparam: isize,
) -> i32 {
    use winapi::um::winuser::*;

    let render_hwnd = &mut *(lparam as *mut Option<i64>);

    let mut class_buf = [0u16; 256];
    let len = GetClassNameW(hwnd, class_buf.as_mut_ptr(), 256);
    let class_name = String::from_utf16_lossy(&class_buf[..len as usize]);

    if class_name.contains("Chrome_RenderWidgetHostHWND") {
        *render_hwnd = Some(hwnd as i64);
        return 0;
    }

    1
}

pub fn create_background_clicker(
    window_title: Option<&str>,
    hwnd: Option<i64>,
) -> Option<BackgroundClicker> {
    BackgroundClicker::new(window_title, hwnd)
}
