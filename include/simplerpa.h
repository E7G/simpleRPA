#ifndef SIMPLERPA_FFI_H
#define SIMPLERPA_FFI_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Opaque handles */
typedef void* ActionHandle;
typedef void* PlayerHandle;
typedef void* ConfigHandle;
typedef void* WindowUtilsHandle;
typedef void* ExporterHandle;
typedef void* LocalGroupManagerHandle;
typedef void* CommandManagerHandle;

/* Result strings - caller must call simplerpa_string_free() */
typedef struct {
    char* data;
    uint32_t length;
} SString;

/* Window info */
typedef struct {
    int64_t hwnd;
    const char* title;
    int32_t x;
    int32_t y;
    int32_t width;
    int32_t height;
} WindowInfoFFI;

/* Player state enum */
typedef enum {
    PLAYER_IDLE = 0,
    PLAYER_PLAYING = 1,
    PLAYER_PAUSED = 2,
    PLAYER_STOPPED = 3,
} PlayerStateFFI;

/* ===== String management ===== */
void simplerpa_string_free(SString s);
const char* simplerpa_string_data(SString s);
uint32_t simplerpa_string_len(SString s);

/* ===== Action ===== */
ActionHandle action_new(int action_type);
void action_free(ActionHandle h);
SString action_get_description(ActionHandle h);
SString action_to_json(ActionHandle h);
ActionHandle action_from_json(const char* json);
void action_set_param_i64(ActionHandle h, const char* key, int64_t value);
void action_set_param_f64(ActionHandle h, const char* key, double value);
void action_set_param_str(ActionHandle h, const char* key, const char* value);
void action_set_param_bool(ActionHandle h, const char* key, bool value);
void action_set_delay_before(ActionHandle h, double seconds);
void action_set_delay_after(ActionHandle h, double seconds);
void action_set_window_title(ActionHandle h, const char* title);
void action_set_use_relative_coords(ActionHandle h, bool val);
void action_set_background_mode(ActionHandle h, bool val);
void action_set_name(ActionHandle h, const char* name);
void action_set_condition(ActionHandle h, const char* condition);
void action_set_repeat_count(ActionHandle h, int count);
SString action_validate(ActionHandle h);
bool action_check_condition(ActionHandle h);
int action_type_value(ActionHandle h);

/* ===== Player ===== */
PlayerHandle player_new(void);
void player_free(PlayerHandle h);
void player_set_actions_json(PlayerHandle h, const char* json);
void player_set_speed(PlayerHandle h, double speed);
void player_set_repeat_count(PlayerHandle h, int count);
void player_set_infinite_loop(PlayerHandle h, bool val);
void player_set_timeout(PlayerHandle h, double seconds);
void player_set_window_hwnd(PlayerHandle h, int64_t hwnd);
void player_set_window_title(PlayerHandle h, const char* title);
void player_set_window_offset(PlayerHandle h, int32_t x, int32_t y);
void player_set_window_run_mode(PlayerHandle h, const char* mode);
void player_play(PlayerHandle h);
void player_pause(PlayerHandle h);
void player_resume(PlayerHandle h);
PlayerStateFFI player_get_state(PlayerHandle h);
int player_get_current_index(PlayerHandle h);
int player_get_current_repeat(PlayerHandle h);
int player_get_total_actions(PlayerHandle h);
void player_stop(PlayerHandle h);

/* ===== Config ===== */
ConfigHandle config_load(void);
void config_free(ConfigHandle h);
void config_save(ConfigHandle h);
double config_get_default_speed(ConfigHandle h);
int config_get_default_repeat_count(ConfigHandle h);
void config_set_default_speed(ConfigHandle h, double val);
void config_set_default_repeat_count(ConfigHandle h, int val);
bool config_get_infinite_loop(ConfigHandle h);
double config_get_timeout_seconds(ConfigHandle h);
void config_set_infinite_loop(ConfigHandle h, bool val);
void config_set_timeout_seconds(ConfigHandle h, double val);
bool config_get_minimize_to_tray(ConfigHandle h);
void config_set_minimize_to_tray(ConfigHandle h, bool val);
bool config_get_run_window_offscreen(ConfigHandle h);
void config_set_run_window_offscreen(ConfigHandle h, bool val);

/* ===== Window Utils ===== */
WindowUtilsHandle window_utils_new(void);
void window_utils_free(WindowUtilsHandle h);
int32_t window_utils_get_all_windows_count(WindowUtilsHandle h);
WindowInfoFFI window_utils_get_window_at(WindowUtilsHandle h, int32_t index);
int64_t window_utils_find_by_title(WindowUtilsHandle h, const char* title);
bool window_utils_activate_window(WindowUtilsHandle h, int64_t hwnd);
SString window_utils_screen_to_client(WindowUtilsHandle h, int64_t hwnd, int32_t sx, int32_t sy);
SString window_utils_client_to_screen(WindowUtilsHandle h, int64_t hwnd, int32_t cx, int32_t cy);

/* ===== Exporter ===== */
ExporterHandle exporter_new(void);
void exporter_free(ExporterHandle h);
void exporter_set_script_name(ExporterHandle h, const char* name);
void exporter_set_window_setup(ExporterHandle h, bool include, const char* title, int64_t hwnd);
SString exporter_export_to_json(ExporterHandle h, const char* actions_json, const char* filepath);
SString exporter_export_to_python(ExporterHandle h, const char* actions_json, const char* filepath);
SString exporter_import_from_json(const char* filepath);

/* ===== Command Manager ===== */
CommandManagerHandle command_manager_new(void);
void command_manager_free(CommandManagerHandle h);
SString command_manager_get_all_commands_json(CommandManagerHandle h);
SString command_manager_add_command(CommandManagerHandle h, const char* name, const char* command, const char* window_pattern, const char* description);
SString command_manager_delete_command(CommandManagerHandle h, const char* id);
SString command_manager_execute_command(CommandManagerHandle h, const char* id);

/* ===== Action Types enum values ===== */
enum ActionTypeFFI {
    AT_MOUSE_CLICK = 0,
    AT_MOUSE_DOUBLE_CLICK = 1,
    AT_MOUSE_RIGHT_CLICK = 2,
    AT_MOUSE_MOVE = 3,
    AT_MOUSE_DRAG = 4,
    AT_MOUSE_SCROLL = 5,
    AT_KEY_PRESS = 6,
    AT_KEY_TYPE = 7,
    AT_HOTKEY = 8,
    AT_WAIT = 9,
    AT_SCREENSHOT = 10,
    AT_MOUSE_MOVE_RELATIVE = 11,
    AT_MOUSE_CLICK_RELATIVE = 12,
    AT_IMAGE_CLICK = 13,
    AT_IMAGE_WAIT_CLICK = 14,
    AT_IMAGE_CHECK = 15,
    AT_ACTION_GROUP_REF = 16,
};

#ifdef __cplusplus
}
#endif

#endif /* SIMPLERPA_FFI_H */
