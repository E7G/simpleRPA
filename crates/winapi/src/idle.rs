#[cfg(windows)]
use std::mem;

#[cfg(windows)]
#[repr(C)]
struct LASTINPUTINFO {
    cb_size: u32,
    dw_time: u32,
}

#[cfg(windows)]
extern "system" {
    fn GetLastInputInfo(plii: *mut LASTINPUTINFO) -> i32;
    fn GetTickCount() -> u32;
}

pub fn get_idle_seconds() -> f64 {
    #[cfg(windows)]
    unsafe {
        let mut lii: LASTINPUTINFO = mem::zeroed();
        lii.cb_size = mem::size_of::<LASTINPUTINFO>() as u32;
        if GetLastInputInfo(&mut lii) != 0 {
            let tick = GetTickCount();
            let millis = tick.wrapping_sub(lii.dw_time);
            return millis as f64 / 1000.0;
        }
    }
    0.0
}
