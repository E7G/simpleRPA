#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import faulthandler

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crash.log")
log_f = open(LOG_FILE, "w", encoding="utf-8")
faulthandler.enable(file=log_f)

def _flush(*args):
    log_f.flush()
    log_f.write(f"flushed\n")
    log_f.flush()

import traceback

def exception_hook(exc_type, exc_value, exc_traceback):
    error_msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    log_f.write(f"\nUnhandled exception:\n{error_msg}\n")
    log_f.flush()
    sys.__excepthook__(exc_type, exc_value, exc_traceback)

sys.excepthook = exception_hook

import atexit
atexit.register(lambda: log_f.write("atexit\n") or log_f.flush())

from gui.app import run_app

if __name__ == '__main__':
    log_f.write(f"__main__ entered\n")
    log_f.flush()
    try:
        run_app()
    except Exception as e:
        log_f.write(f"run_app exception: {e}\n")
        log_f.flush()
        raise
