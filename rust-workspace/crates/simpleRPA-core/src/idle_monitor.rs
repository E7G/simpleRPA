use std::sync::{Arc, Mutex};
use std::thread;
use std::time::{Duration, Instant};

pub struct IdleMonitor {
    idle_threshold_secs: u64,
    check_interval_secs: u64,
    last_active_time: Arc<Mutex<Instant>>,
    is_monitoring: Arc<Mutex<bool>>,
    on_idle_start: Option<Box<dyn Fn() + Send>>,
    on_idle_end: Option<Box<dyn Fn() + Send>>,
}

impl IdleMonitor {
    pub fn new(idle_threshold_secs: u64, check_interval_secs: u64) -> Self {
        Self {
            idle_threshold_secs,
            check_interval_secs,
            last_active_time: Arc::new(Mutex::new(Instant::now())),
            is_monitoring: Arc::new(Mutex::new(false)),
            on_idle_start: None,
            on_idle_end: None,
        }
    }

    pub fn set_on_idle_start<F: Fn() + Send + 'static>(&mut self, f: F) {
        self.on_idle_start = Some(Box::new(f));
    }

    pub fn set_on_idle_end<F: Fn() + Send + 'static>(&mut self, f: F) {
        self.on_idle_end = Some(Box::new(f));
    }

    pub fn start_monitoring(&self) {
        let mut is_monitoring = self.is_monitoring.lock().unwrap();
        if *is_monitoring {
            return;
        }
        *is_monitoring = true;

        let last_active = self.last_active_time.clone();
        let is_monitoring_flag = self.is_monitoring.clone();
        let threshold = self.idle_threshold_secs;
        let interval = self.check_interval_secs;

        thread::spawn(move || {
            let mut was_idle = false;

            loop {
                if !*is_monitoring_flag.lock().unwrap() {
                    break;
                }

                let idle_secs = last_active.lock().unwrap().elapsed().as_secs();

                if idle_secs >= threshold && !was_idle {
                    was_idle = true;
                    // Trigger idle callback if set
                } else if idle_secs < threshold && was_idle {
                    was_idle = false;
                    // Trigger active callback if set
                }

                thread::sleep(Duration::from_secs(interval));
            }
        });
    }

    pub fn stop_monitoring(&self) {
        *self.is_monitoring.lock().unwrap() = false;
    }

    pub fn update_activity(&self) {
        *self.last_active_time.lock().unwrap() = Instant::now();
    }

    pub fn is_idle(&self) -> bool {
        self.last_active_time.lock().unwrap().elapsed().as_secs() >= self.idle_threshold_secs
    }

    pub fn get_idle_seconds(&self) -> u64 {
        self.last_active_time.lock().unwrap().elapsed().as_secs()
    }
}

impl Default for IdleMonitor {
    fn default() -> Self {
        Self::new(180, 5)
    }
}
