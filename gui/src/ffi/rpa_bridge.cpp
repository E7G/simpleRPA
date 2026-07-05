#include "rpa_bridge.h"
#include <cstring>

RpaBridge::RpaBridge() {
    configHandle = config_load();
    windowUtilsHandle = window_utils_new();
    exporterHandle = exporter_new();
    commandManagerHandle = command_manager_new();
}

RpaBridge::~RpaBridge() {
    if (configHandle) config_free((ConfigHandle)configHandle);
    if (windowUtilsHandle) window_utils_free((WindowUtilsHandle)windowUtilsHandle);
    if (exporterHandle) exporter_free((ExporterHandle)exporterHandle);
    if (commandManagerHandle) command_manager_free((CommandManagerHandle)commandManagerHandle);
}

// Config
bool RpaBridge::loadConfig() { return configHandle != nullptr; }
void RpaBridge::saveConfig() { if (configHandle) config_save((ConfigHandle)configHandle); }
double RpaBridge::getDefaultSpeed() { return configHandle ? config_get_default_speed((ConfigHandle)configHandle) : 1.0; }
int RpaBridge::getDefaultRepeatCount() { return configHandle ? config_get_default_repeat_count((ConfigHandle)configHandle) : 1; }
void RpaBridge::setDefaultSpeed(double val) { if (configHandle) config_set_default_speed((ConfigHandle)configHandle, val); }
void RpaBridge::setDefaultRepeatCount(int val) { if (configHandle) config_set_default_repeat_count((ConfigHandle)configHandle, val); }
bool RpaBridge::getInfiniteLoop() { return configHandle ? config_get_infinite_loop((ConfigHandle)configHandle) : false; }
void RpaBridge::setInfiniteLoop(bool val) { if (configHandle) config_set_infinite_loop((ConfigHandle)configHandle, val); }
double RpaBridge::getTimeout() { return configHandle ? config_get_timeout_seconds((ConfigHandle)configHandle) : 0.0; }
void RpaBridge::setTimeout(double val) { if (configHandle) config_set_timeout_seconds((ConfigHandle)configHandle, val); }
bool RpaBridge::getMinimizeToTray() { return configHandle ? config_get_minimize_to_tray((ConfigHandle)configHandle) : true; }
void RpaBridge::setMinimizeToTray(bool val) { if (configHandle) config_set_minimize_to_tray((ConfigHandle)configHandle, val); }
bool RpaBridge::getRunWindowOffscreen() { return configHandle ? config_get_run_window_offscreen((ConfigHandle)configHandle) : false; }
void RpaBridge::setRunWindowOffscreen(bool val) { if (configHandle) config_set_run_window_offscreen((ConfigHandle)configHandle, val); }

// Actions
void* RpaBridge::createAction(int type) { return action_new(type); }
void RpaBridge::destroyAction(void* h) { if (h) action_free((ActionHandle)h); }

QString RpaBridge::getActionDescription(void* h) {
    if (!h) return {};
    auto s = action_get_description((ActionHandle)h);
    QString result(s.data);
    simplerpa_string_free(s.data);
    return result;
}

QString RpaBridge::actionToJson(void* h) {
    if (!h) return {};
    auto s = action_to_json((ActionHandle)h);
    QString result(s.data);
    simplerpa_string_free(s.data);
    return result;
}

void* RpaBridge::actionFromJson(const QString& json) {
    QByteArray bytes = json.toUtf8();
    return action_from_json(bytes.constData());
}

void RpaBridge::setActionParamI64(void* h, const char* key, int64_t val) { action_set_param_i64((ActionHandle)h, key, val); }
void RpaBridge::setActionParamF64(void* h, const char* key, double val) { action_set_param_f64((ActionHandle)h, key, val); }
void RpaBridge::setActionParamBool(void* h, const char* key, bool val) { action_set_param_bool((ActionHandle)h, key, val); }

void RpaBridge::setActionParamStr(void* h, const char* key, const char* val) {
    action_set_param_str((ActionHandle)h, key, val);
}

void RpaBridge::setActionDelayBefore(void* h, double s) { action_set_delay_before((ActionHandle)h, s); }
void RpaBridge::setActionDelayAfter(void* h, double s) { action_set_delay_after((ActionHandle)h, s); }
void RpaBridge::setActionWindowTitle(void* h, const char* t) { action_set_window_title((ActionHandle)h, t); }
void RpaBridge::setActionUseRelativeCoords(void* h, bool v) { action_set_use_relative_coords((ActionHandle)h, v); }
void RpaBridge::setActionBackgroundMode(void* h, bool v) { action_set_background_mode((ActionHandle)h, v); }
void RpaBridge::setActionName(void* h, const char* n) { action_set_name((ActionHandle)h, n); }
void RpaBridge::setActionCondition(void* h, const char* c) { action_set_condition((ActionHandle)h, c); }
void RpaBridge::setActionRepeatCount(void* h, int c) { action_set_repeat_count((ActionHandle)h, c); }

QString RpaBridge::validateAction(void* h) {
    auto s = action_validate((ActionHandle)h);
    QString result(s.data);
    simplerpa_string_free(s.data);
    return result;
}

int RpaBridge::getActionType(void* h) { return action_type_value((ActionHandle)h); }

// Player
void* RpaBridge::createPlayer() { return player_new(); }
void RpaBridge::destroyPlayer(void* h) { if (h) player_free((PlayerHandle)h); }
void RpaBridge::playerSetSpeed(void* h, double s) { player_set_speed((PlayerHandle)h, s); }
void RpaBridge::playerSetRepeatCount(void* h, int c) { player_set_repeat_count((PlayerHandle)h, c); }
void RpaBridge::playerSetInfiniteLoop(void* h, bool v) { player_set_infinite_loop((PlayerHandle)h, v); }
void RpaBridge::playerSetTimeout(void* h, double s) { player_set_timeout((PlayerHandle)h, s); }
void RpaBridge::playerSetWindowHwnd(void* h, int64_t hwnd) { player_set_window_hwnd((PlayerHandle)h, hwnd); }
void RpaBridge::playerSetWindowTitle(void* h, const char* t) { player_set_window_title((PlayerHandle)h, t); }
void RpaBridge::playerSetWindowOffset(void* h, int32_t x, int32_t y) { player_set_window_offset((PlayerHandle)h, x, y); }
void RpaBridge::playerSetWindowRunMode(void* h, const char* m) { player_set_window_run_mode((PlayerHandle)h, m); }
void RpaBridge::playerPlay(void* h) { player_play((PlayerHandle)h); }
void RpaBridge::playerPause(void* h) { player_pause((PlayerHandle)h); }
void RpaBridge::playerResume(void* h) { player_resume((PlayerHandle)h); }
void RpaBridge::playerStop(void* h) { player_stop((PlayerHandle)h); }
int RpaBridge::playerGetState(void* h) { return player_get_state((PlayerHandle)h); }
int RpaBridge::playerGetCurrentIndex(void* h) { return player_get_current_index((PlayerHandle)h); }
int RpaBridge::playerGetCurrentRepeat(void* h) { return player_get_current_repeat((PlayerHandle)h); }
int RpaBridge::playerGetTotalActions(void* h) { return player_get_total_actions((PlayerHandle)h); }

// Windows
QVector<WindowInfo> RpaBridge::getAllWindows() {
    QVector<WindowInfo> result;
    if (!windowUtilsHandle) return result;

    int count = window_utils_get_all_windows_count((WindowUtilsHandle)windowUtilsHandle);
    for (int i = 0; i < count; ++i) {
        auto ffi = window_utils_get_window_at((WindowUtilsHandle)windowUtilsHandle, i);
        WindowInfo info;
        info.hwnd = ffi.hwnd;
        info.title = QString(ffi.title);
        info.x = ffi.x;
        info.y = ffi.y;
        info.width = ffi.width;
        info.height = ffi.height;
        if (ffi.title) simplerpa_string_free(ffi.title);
        result.append(info);
    }
    return result;
}

int64_t RpaBridge::findWindowByTitle(const QString& title) {
    if (!windowUtilsHandle) return 0;
    QByteArray bytes = title.toUtf8();
    return window_utils_find_by_title((WindowUtilsHandle)windowUtilsHandle, bytes.constData());
}

bool RpaBridge::activateWindow(int64_t hwnd) {
    if (!windowUtilsHandle) return false;
    return window_utils_activate_window((WindowUtilsHandle)windowUtilsHandle, hwnd);
}

// Commands
QString RpaBridge::getAllCommandsJson() {
    if (!commandManagerHandle) return "[]";
    auto s = command_manager_get_all_commands_json((CommandManagerHandle)commandManagerHandle);
    QString result(s.data);
    simplerpa_string_free(s.data);
    return result;
}

QString RpaBridge::addCommand(const QString& name, const QString& cmd, const QString& pattern, const QString& desc) {
    if (!commandManagerHandle) return "{}";
    QByteArray n = name.toUtf8(), c = cmd.toUtf8(), p = pattern.toUtf8(), d = desc.toUtf8();
    auto s = command_manager_add_command((CommandManagerHandle)commandManagerHandle,
        n.constData(), c.constData(), p.constData(), d.constData());
    QString result(s.data);
    simplerpa_string_free(s.data);
    return result;
}

bool RpaBridge::deleteCommand(const QString& id) {
    if (!commandManagerHandle) return false;
    QByteArray bytes = id.toUtf8();
    return command_manager_delete_command((CommandManagerHandle)commandManagerHandle, bytes.constData());
}

QString RpaBridge::executeCommand(const QString& id) {
    if (!commandManagerHandle) return "命令管理器未初始化";
    QByteArray bytes = id.toUtf8();
    auto s = command_manager_execute_command((CommandManagerHandle)commandManagerHandle, bytes.constData());
    QString result(s.data);
    simplerpa_string_free(s.data);
    return result;
}
