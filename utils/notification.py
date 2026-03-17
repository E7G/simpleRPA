import sys
import os


def send_notification(title: str, message: str, app_name: str = "SimpleRPA"):
    if sys.platform != 'win32':
        return False
    
    try:
        from win10toast import ToastNotifier
        toaster = ToastNotifier()
        toaster.show_toast(title, message, duration=5, threaded=True)
        return True
    except ImportError:
        pass
    
    try:
        import subprocess
        powershell_script = f'''
        [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
        [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
        
        $template = @"
        <toast>
            <visual>
                <binding template="ToastText02">
                    <text id="1">{title}</text>
                    <text id="2">{message}</text>
                </binding>
            </visual>
        </toast>
"@
        
        $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
        $xml.LoadXml($template)
        $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
        [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("{app_name}").Show($toast)
        '''
        subprocess.run(['powershell', '-Command', powershell_script], capture_output=True, timeout=10)
        return True
    except Exception:
        pass
    
    try:
        import ctypes
        MB_OK = 0x0
        MB_ICONINFORMATION = 0x40
        MB_SYSTEMMODAL = 0x1000
        ctypes.windll.user32.MessageBoxW(0, message, title, MB_OK | MB_ICONINFORMATION | MB_SYSTEMMODAL)
        return True
    except Exception:
        return False
