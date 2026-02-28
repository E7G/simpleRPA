__all__ = ['MainWindow', 'ActionPanel', 'ScriptEditor', 'RecorderPanel', 'PropertyPanel', 'CoordinateWidget', 'WindowSelector']

def __getattr__(name):
    if name == 'MainWindow':
        from .main_window import MainWindow
        return MainWindow
    elif name == 'ActionPanel':
        from .action_panel import ActionPanel
        return ActionPanel
    elif name == 'ScriptEditor':
        from .script_editor import ScriptEditor
        return ScriptEditor
    elif name == 'RecorderPanel':
        from .recorder_panel import RecorderPanel
        return RecorderPanel
    elif name == 'PropertyPanel':
        from .property_panel import PropertyPanel
        return PropertyPanel
    elif name in ['CoordinateWidget', 'WindowSelector']:
        from .widgets import CoordinateWidget, WindowSelector
        return CoordinateWidget if name == 'CoordinateWidget' else WindowSelector
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
