#pragma once

#include <cstddef>
#include <cstdint>

#ifdef __cplusplus
extern "C" {
#endif

// Opaque handle types
typedef struct FfiPlayer FfiPlayer;
typedef struct FfiRecorder FfiRecorder;
typedef struct FfiConfig FfiConfig;
typedef struct FfiExporter FfiExporter;
typedef struct FfiCommandManager FfiCommandManager;
typedef struct FfiWindowUtils FfiWindowUtils;
typedef struct FfiActionGroupManager FfiActionGroupManager;

// Config
FfiConfig* config_new();
void config_free(FfiConfig* ptr);
int config_save(const FfiConfig* ptr);
double config_get_default_speed(const FfiConfig* ptr);
void config_set_default_speed(const FfiConfig* ptr, double speed);
int config_get_default_repeat_count(const FfiConfig* ptr);
void config_set_default_repeat_count(const FfiConfig* ptr, int count);
int config_get_infinite_loop(const FfiConfig* ptr);
void config_set_infinite_loop(const FfiConfig* ptr, int val);
double config_get_timeout_seconds(const FfiConfig* ptr);
void config_set_timeout_seconds(const FfiConfig* ptr, double val);
int config_get_minimize_to_tray(const FfiConfig* ptr);
void config_set_minimize_to_tray(const FfiConfig* ptr, int val);
int config_get_run_window_offscreen(const FfiConfig* ptr);
void config_set_run_window_offscreen(const FfiConfig* ptr, int val);

// WindowUtils
FfiWindowUtils* window_utils_new();
void window_utils_free(FfiWindowUtils* ptr);
char* window_utils_get_all_windows_json(const FfiWindowUtils* ptr);
void window_utils_free_string(char* ptr);

// Player
typedef void (*PlayerEventCallback)(int event, int index, int total, int repeat, int value, void* user_data);

FfiPlayer* player_new();
void player_free(FfiPlayer* ptr);
int player_set_actions_json(const FfiPlayer* ptr, const char* json_str);
void player_set_speed(const FfiPlayer* ptr, double speed);
void player_set_repeat_count(const FfiPlayer* ptr, int count);
void player_set_infinite_loop(const FfiPlayer* ptr, int val);
void player_set_timeout(const FfiPlayer* ptr, double seconds);
void player_set_window_title(const FfiPlayer* ptr, const char* title);
void player_set_window_hwnd(const FfiPlayer* ptr, int64_t hwnd);
void player_set_window_run_mode(const FfiPlayer* ptr, const char* mode);
void player_set_window_offset(const FfiPlayer* ptr, int x, int y, int enabled);
int player_set_local_groups_json(const FfiPlayer* ptr, const char* local_groups_json);
void player_set_event_callback(const FfiPlayer* ptr, PlayerEventCallback callback, void* user_data);
void player_play(const FfiPlayer* ptr);
int player_execute_single_action(const FfiPlayer* ptr, int index, int offset_x, int offset_y, int has_offset);
void player_stop(const FfiPlayer* ptr);
int player_toggle_pause(const FfiPlayer* ptr);
int player_get_state(const FfiPlayer* ptr);

// Recorder
FfiRecorder* recorder_new();
void recorder_free(FfiRecorder* ptr);
void recorder_start(const FfiRecorder* ptr);
char* recorder_stop(const FfiRecorder* ptr);
int recorder_is_recording(const FfiRecorder* ptr);
void recorder_set_config(const FfiRecorder* ptr, int record_mouse_click, int record_mouse_scroll, int record_keyboard, int record_mouse_move, int min_move_distance, double move_sample_interval, int ignore_last_click);
void recorder_on_mouse_click(const FfiRecorder* ptr, int x, int y, const char* button);
void recorder_on_key_press(const FfiRecorder* ptr, char key);

// Exporter
FfiExporter* exporter_new();
void exporter_free(FfiExporter* ptr);
void exporter_set_script_info(const FfiExporter* ptr, const char* name, const char* author, const char* description);
int exporter_set_local_groups_json(const FfiExporter* ptr, const char* local_groups_json);
int exporter_export_to_json(const FfiExporter* ptr, const char* actions_json, const char* filepath);
int exporter_export_to_python(const FfiExporter* ptr, const char* actions_json, const char* filepath);
char* exporter_actions_to_python_code(const char* actions_json, const char* indent);
char* exporter_actions_to_python_code_with_groups(const char* actions_json, const char* local_groups_json, const char* indent);
char* exporter_import_from_json(const char* filepath);

// Action
char* action_new(const char* action_type_str);
char* action_manager_get_catalog_json();
char* action_from_dict(const char* json_str);
char* action_get_description(const char* json_str);
void action_free_string(char* ptr);

// CommandManager
FfiCommandManager* command_manager_new();
void command_manager_free(FfiCommandManager* ptr);
char* command_manager_get_all_json(const FfiCommandManager* ptr);
char* command_manager_add_command(const FfiCommandManager* ptr, const char* name, const char* command, const char* window_title_pattern, const char* description, double delay);
int command_manager_delete_command(const FfiCommandManager* ptr, const char* cmd_id);
int command_manager_update_command(const FfiCommandManager* ptr, const char* cmd_id, const char* updates_json);
char* command_manager_test_command(const char* command);
char* command_manager_check_and_launch(const FfiCommandManager* ptr, const char* cmd_id);

// ActionGroupManager
FfiActionGroupManager* action_group_manager_new();
void action_group_manager_free(FfiActionGroupManager* ptr);
char* action_group_manager_get_all_json(const FfiActionGroupManager* ptr);
char* action_group_manager_to_json(const FfiActionGroupManager* ptr);
int action_group_manager_load_json(const FfiActionGroupManager* ptr, const char* local_groups_json);
int action_group_manager_save_group(const FfiActionGroupManager* ptr, const char* name, const char* description, const char* actions_json);
int action_group_manager_delete_group(const FfiActionGroupManager* ptr, const char* name);
char* action_group_manager_get_group_actions_json(const FfiActionGroupManager* ptr, const char* name);
char* global_action_group_manager_get_all_json();
char* global_action_group_manager_get_group_actions_json(const char* name);
int global_action_group_manager_delete_group(const char* name);
int global_action_group_manager_save_group(const char* name, const char* description, const char* actions_json);

#ifdef __cplusplus
}
#endif
