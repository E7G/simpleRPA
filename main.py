#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import traceback

from PyQt5.QtCore import qInstallMessageHandler, QtMsgType

def exception_hook(exc_type, exc_value, exc_traceback):
    error_msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    print(f"未捕获的异常:\n{error_msg}")

sys.excepthook = exception_hook

def message_handler(msg_type, context, msg):
    if msg_type == QtMsgType.QtWarningMsg and "QBackingStore::endPaint" in msg:
        return
    if msg_type == QtMsgType.QtWarningMsg:
        print(f"Warning: {msg}")
    elif msg_type == QtMsgType.QtCriticalMsg:
        print(f"Critical: {msg}")
    elif msg_type == QtMsgType.QtFatalMsg:
        print(f"Fatal: {msg}")

qInstallMessageHandler(message_handler)

from gui.app import run_app

if __name__ == '__main__':
    run_app()
