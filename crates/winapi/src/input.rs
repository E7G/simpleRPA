#[cfg(windows)]
use windows_sys::Win32::UI::WindowsAndMessaging::*;
#[cfg(windows)]
use windows_sys::Win32::Foundation::*;
#[cfg(windows)]
use windows_sys::Win32::UI::Input::KeyboardAndMouse::*;

const MK_LBUTTON: u32 = 0x0001;
const MK_RBUTTON: u32 = 0x0002;
const MK_MBUTTON: u32 = 0x0010;

pub struct InputSimulator;

impl InputSimulator {
    pub fn new() -> Self { Self }

    #[cfg(windows)]
    pub fn click(&self, x: i32, y: i32, button: &str) -> bool {
        unsafe {
            SetCursorPos(x, y);
            std::thread::sleep(std::time::Duration::from_millis(50));

            let (down_msg, up_msg, mk_flag) = match button {
                "right" => (WM_RBUTTONDOWN, WM_RBUTTONUP, MK_RBUTTON as u32),
                "middle" => (WM_MBUTTONDOWN, WM_MBUTTONUP, MK_MBUTTON as u32),
                _ => (WM_LBUTTONDOWN, WM_LBUTTONUP, MK_LBUTTON as u32),
            };

            let lparam = ((y as usize) << 16) | ((x as usize) & 0xFFFF);
            let foreground = GetForegroundWindow();
            SendMessageW(foreground, down_msg, mk_flag as WPARAM, lparam as LPARAM);
            std::thread::sleep(std::time::Duration::from_millis(50));
            SendMessageW(foreground, up_msg, 0, lparam as LPARAM);
            true
        }
    }

    #[cfg(not(windows))]
    pub fn click(&self, _x: i32, _y: i32, _button: &str) -> bool { false }

    #[cfg(windows)]
    pub fn double_click(&self, x: i32, y: i32) -> bool {
        self.click(x, y, "left")
            && {
                std::thread::sleep(std::time::Duration::from_millis(80));
                self.click(x, y, "left")
            }
    }

    #[cfg(not(windows))]
    pub fn double_click(&self, _x: i32, _y: i32) -> bool { false }

    #[cfg(windows)]
    pub fn move_to(&self, x: i32, y: i32) -> bool {
        unsafe { SetCursorPos(x, y) != 0 }
    }

    #[cfg(not(windows))]
    pub fn move_to(&self, _x: i32, _y: i32) -> bool { false }

    #[cfg(windows)]
    pub fn scroll(&self, x: i32, y: i32, clicks: i32) -> bool {
        unsafe {
            SetCursorPos(x, y);
            std::thread::sleep(std::time::Duration::from_millis(30));
            let foreground = GetForegroundWindow();
            let lparam = ((y as usize) << 16) | ((x as usize) & 0xFFFF);
            let wparam = (clicks * 120) as isize;
            SendMessageW(foreground, WM_MOUSEWHEEL, wparam as WPARAM, lparam as LPARAM);
            true
        }
    }

    #[cfg(not(windows))]
    pub fn scroll(&self, _x: i32, _y: i32, _clicks: i32) -> bool { false }

    #[cfg(windows)]
    pub fn key_press(&self, key: &str) -> bool {
        use std::collections::HashMap;

        let vk_map: HashMap<&str, u16> = HashMap::from([
            ("enter", VK_RETURN), ("tab", VK_TAB), ("space", VK_SPACE),
            ("backspace", VK_BACK), ("delete", VK_DELETE), ("escape", VK_ESCAPE),
            ("up", VK_UP), ("down", VK_DOWN), ("left", VK_LEFT), ("right", VK_RIGHT),
            ("home", VK_HOME), ("end", VK_END),
            ("pageup", VK_PRIOR), ("pagedown", VK_NEXT),
            ("capslock", VK_CAPITAL),
            ("f1", VK_F1), ("f2", VK_F2), ("f3", VK_F3), ("f4", VK_F4),
            ("f5", VK_F5), ("f6", VK_F6), ("f7", VK_F7), ("f8", VK_F8),
            ("f9", VK_F9), ("f10", VK_F10), ("f11", VK_F11), ("f12", VK_F12),
            ("ctrl", VK_CONTROL), ("alt", VK_MENU), ("shift", VK_SHIFT),
            ("win", VK_LWIN),
        ]);

        if let Some(&vk) = vk_map.get(key) {
            unsafe {
                let mut inputs: [INPUT; 2] = std::mem::zeroed();
                inputs[0].r#type = INPUT_KEYBOARD;
                inputs[0].Anonymous.ki.wVk = vk;
                inputs[1].r#type = INPUT_KEYBOARD;
                inputs[1].Anonymous.ki.wVk = vk;
                inputs[1].Anonymous.ki.dwFlags = KEYEVENTF_KEYUP;
                SendInput(2, inputs.as_ptr(), std::mem::size_of::<INPUT>() as i32);
            }
            return true;
        }

        if key.len() == 1 {
            let ch = key.chars().next().unwrap();
            let vk = ch as u16;
            unsafe {
                let mut inputs: [INPUT; 2] = std::mem::zeroed();
                inputs[0].r#type = INPUT_KEYBOARD;
                inputs[0].Anonymous.ki.wVk = vk;
                inputs[1].r#type = INPUT_KEYBOARD;
                inputs[1].Anonymous.ki.wVk = vk;
                inputs[1].Anonymous.ki.dwFlags = KEYEVENTF_KEYUP;
                SendInput(2, inputs.as_ptr(), std::mem::size_of::<INPUT>() as i32);
            }
            return true;
        }

        false
    }

    #[cfg(not(windows))]
    pub fn key_press(&self, _key: &str) -> bool { false }

    #[cfg(windows)]
    pub fn type_text(&self, text: &str, interval_ms: u64) -> bool {
        for ch in text.chars() {
            self.key_press(&ch.to_string());
            if interval_ms > 0 {
                std::thread::sleep(std::time::Duration::from_millis(interval_ms));
            }
        }
        true
    }

    #[cfg(not(windows))]
    pub fn type_text(&self, _text: &str, _interval_ms: u64) -> bool { false }

    #[cfg(windows)]
    pub fn hotkey(&self, keys: &[&str]) -> bool {
        let mut vks: Vec<u16> = Vec::new();
        for key in keys {
            match *key {
                "ctrl" => vks.push(VK_CONTROL),
                "alt" => vks.push(VK_MENU),
                "shift" => vks.push(VK_SHIFT),
                "win" => vks.push(VK_LWIN),
                _ => {
                    if key.len() == 1 {
                        vks.push(key.chars().next().unwrap() as u16);
                    }
                }
            }
        }

        unsafe {
            let mut inputs: Vec<INPUT> = Vec::new();
            for &vk in &vks {
                let mut inp: INPUT = std::mem::zeroed();
                inp.r#type = INPUT_KEYBOARD;
                inp.Anonymous.ki.wVk = vk;
                inputs.push(inp);
            }
            for &vk in vks.iter().rev() {
                let mut inp: INPUT = std::mem::zeroed();
                inp.r#type = INPUT_KEYBOARD;
                inp.Anonymous.ki.wVk = vk;
                inp.Anonymous.ki.dwFlags = KEYEVENTF_KEYUP;
                inputs.push(inp);
            }
            SendInput(inputs.len() as u32, inputs.as_ptr(), std::mem::size_of::<INPUT>() as i32);
        }
        true
    }

    #[cfg(not(windows))]
    pub fn hotkey(&self, _keys: &[&str]) -> bool { false }
}
