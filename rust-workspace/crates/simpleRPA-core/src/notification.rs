use std::thread;
use std::time::Duration;

pub fn show_notification(title: &str, message: &str) {
    #[cfg(target_os = "windows")]
    {
        show_windows_notification(title, message);
    }
    #[cfg(not(target_os = "windows"))]
    {
        println!("[{}] {}", title, message);
    }
}

#[cfg(target_os = "windows")]
fn show_windows_notification(title: &str, message: &str) {
    use std::ffi::OsStr;
    use std::os::windows::ffi::OsStrExt;
    use winapi::um::winuser::{MessageBoxW, MB_ICONINFORMATION, MB_OK};

    let title_wide: Vec<u16> = OsStr::new(title)
        .encode_wide()
        .chain(std::iter::once(0))
        .collect();
    let msg_wide: Vec<u16> = OsStr::new(message)
        .encode_wide()
        .chain(std::iter::once(0))
        .collect();

    unsafe {
        MessageBoxW(
            std::ptr::null_mut(),
            msg_wide.as_ptr(),
            title_wide.as_ptr(),
            MB_OK | MB_ICONINFORMATION,
        );
    }
}

pub fn show_notification_async(title: String, message: String, timeout_secs: u64) {
    thread::spawn(move || {
        if timeout_secs > 0 {
            thread::sleep(Duration::from_secs(timeout_secs));
        }
        show_notification(&title, &message);
    });
}
