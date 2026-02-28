import unittest
import os
import sys
import tempfile
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.actions import Action, ActionType, ActionManager
from core.action_group import ActionGroup, ActionGroupManager
from core.player import Player, PlayerState
from utils.config import Config


class TestActionGroup(unittest.TestCase):
    def setUp(self):
        self.group = ActionGroup(
            name="测试动作组",
            description="用于测试的动作组"
        )
    
    def test_create_group(self):
        self.assertEqual(self.group.name, "测试动作组")
        self.assertEqual(self.group.description, "用于测试的动作组")
        self.assertEqual(len(self.group.actions), 0)
    
    def test_add_action(self):
        action = Action(ActionType.MOUSE_CLICK, {"x": 100, "y": 200})
        self.group.actions.append(action)
        self.assertEqual(self.group.get_action_count(), 1)
    
    def test_to_dict(self):
        action = Action(ActionType.MOUSE_CLICK, {"x": 100, "y": 200})
        self.group.actions.append(action)
        
        data = self.group.to_dict()
        self.assertEqual(data['name'], "测试动作组")
        self.assertEqual(len(data['actions']), 1)
    
    def test_from_dict(self):
        data = {
            'name': '导入的动作组',
            'description': '测试导入',
            'actions': [
                {'action_type': 'mouse_click', 'params': {'x': 50, 'y': 100}}
            ]
        }
        
        group = ActionGroup.from_dict(data)
        self.assertEqual(group.name, '导入的动作组')
        self.assertEqual(group.get_action_count(), 1)
    
    def test_validate_empty_name(self):
        group = ActionGroup(name="", actions=[Action(ActionType.MOUSE_CLICK, {"x": 100, "y": 200})])
        is_valid, error = group.validate()
        self.assertFalse(is_valid)
        self.assertIn("名称", error)
    
    def test_validate_empty_actions(self):
        group = ActionGroup(name="测试组", actions=[])
        is_valid, error = group.validate()
        self.assertFalse(is_valid)
        self.assertIn("至少一个动作", error)
    
    def test_validate_valid_group(self):
        group = ActionGroup(
            name="有效组",
            actions=[Action(ActionType.MOUSE_CLICK, {"x": 100, "y": 200})]
        )
        is_valid, error = group.validate()
        self.assertTrue(is_valid)
        self.assertEqual(error, "")


class TestActionGroupManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.manager = ActionGroupManager()
        self.manager._groups_dir = self.temp_dir
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_save_and_load_group(self):
        group = ActionGroup(name="保存测试", description="测试保存功能")
        action = Action(ActionType.MOUSE_CLICK, {"x": 100, "y": 200})
        group.actions.append(action)
        
        result = self.manager.save_group(group)
        self.assertTrue(result)
        
        loaded = self.manager.get_group("保存测试")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.name, "保存测试")
    
    def test_delete_group(self):
        group = ActionGroup(name="删除测试")
        self.manager.save_group(group)
        
        result = self.manager.delete_group("删除测试")
        self.assertTrue(result)
        
        loaded = self.manager.get_group("删除测试")
        self.assertIsNone(loaded)
    
    def test_get_actions_copy(self):
        group = ActionGroup(name="复制测试")
        action = Action(ActionType.MOUSE_CLICK, {"x": 100, "y": 200})
        group.actions.append(action)
        self.manager.save_group(group)
        
        actions = self.manager.get_actions_copy("复制测试")
        self.assertEqual(len(actions), 1)
        
        actions[0].params['x'] = 999
        original = self.manager.get_group("复制测试")
        self.assertEqual(original.actions[0].params['x'], 100)


class TestPlayer(unittest.TestCase):
    def setUp(self):
        self.player = Player(tab_key="test_tab")
    
    def test_initial_state(self):
        self.assertEqual(self.player.state, PlayerState.IDLE)
        self.assertEqual(self.player.repeat_count, 1)
        self.assertFalse(self.player.infinite_loop)
    
    def test_set_speed(self):
        self.player.set_speed(2.0)
        self.assertEqual(self.player.speed, 2.0)
        
        self.player.set_speed(0.05)
        self.assertEqual(self.player.speed, 0.1)
        
        self.player.set_speed(20.0)
        self.assertEqual(self.player.speed, 10.0)
    
    def test_set_repeat_count(self):
        self.player.set_repeat_count(5)
        self.assertEqual(self.player.repeat_count, 5)
        
        self.player.set_repeat_count(0)
        self.assertEqual(self.player.repeat_count, 1)
    
    def test_set_infinite_loop(self):
        self.player.set_infinite_loop(True)
        self.assertTrue(self.player.infinite_loop)
        
        self.player.set_infinite_loop(False)
        self.assertFalse(self.player.infinite_loop)
    
    def test_set_timeout(self):
        self.player.set_timeout(60.0)
        self.assertEqual(self.player.timeout_seconds, 60.0)
        
        self.player.set_timeout(-10)
        self.assertEqual(self.player.timeout_seconds, 0)
    
    def test_toggle_pause(self):
        self.assertEqual(self.player.state, PlayerState.IDLE)
        
        result = self.player.toggle_pause()
        self.assertEqual(result, PlayerState.IDLE)


class TestConfig(unittest.TestCase):
    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        self.temp_file.close()
        
        self.config = Config()
        self.config._config_path = self.temp_file.name
    
    def tearDown(self):
        os.unlink(self.temp_file.name)
    
    def test_save_and_load(self):
        self.config.default_speed = 2.5
        self.config.default_repeat_count = 10
        self.config.infinite_loop = True
        self.config.timeout_seconds = 120.0
        self.config.bound_window = {'hwnd': 12345, 'title': '测试窗口'}
        self.config.open_tabs = [{'name': '任务 1', 'actions': []}]
        
        self.config.save()
        
        new_config = Config()
        new_config._config_path = self.temp_file.name
        new_config.load()
        
        self.assertEqual(new_config.default_speed, 2.5)
        self.assertEqual(new_config.default_repeat_count, 10)
        self.assertTrue(new_config.infinite_loop)
        self.assertEqual(new_config.timeout_seconds, 120.0)
        self.assertEqual(new_config.bound_window['hwnd'], 12345)
    
    def test_window_geometry(self):
        self.config.set_window_geometry(100, 200, 1280, 720)
        
        self.assertEqual(self.config.window_geometry['x'], 100)
        self.assertEqual(self.config.window_geometry['y'], 200)
        self.assertEqual(self.config.window_geometry['width'], 1280)
        self.assertEqual(self.config.window_geometry['height'], 720)


class TestAction(unittest.TestCase):
    def test_create_action(self):
        action = Action(ActionType.MOUSE_CLICK, {"x": 100, "y": 200})
        
        self.assertEqual(action.action_type, ActionType.MOUSE_CLICK)
        self.assertEqual(action.params['x'], 100)
        self.assertEqual(action.params['y'], 200)
    
    def test_action_to_dict(self):
        action = Action(ActionType.KEY_TYPE, {"text": "Hello"})
        action.name = "输入文本"
        action.delay_before = 0.5
        action.delay_after = 0.3
        
        data = action.to_dict()
        
        self.assertEqual(data['action_type'], 'key_type')
        self.assertEqual(data['params']['text'], "Hello")
        self.assertEqual(data['name'], "输入文本")
        self.assertEqual(data['delay_before'], 0.5)
    
    def test_action_from_dict(self):
        data = {
            'action_type': 'mouse_drag',
            'params': {'start_x': 0, 'start_y': 0, 'end_x': 100, 'end_y': 100},
            'name': '拖拽测试',
            'delay_before': 0.1,
            'delay_after': 0.2
        }
        
        action = Action.from_dict(data)
        
        self.assertEqual(action.action_type, ActionType.MOUSE_DRAG)
        self.assertEqual(action.name, "拖拽测试")
        self.assertEqual(action.delay_before, 0.1)
    
    def test_group_marker(self):
        action = Action(ActionType.MOUSE_CLICK, {"x": 100, "y": 200})
        action._is_from_group = True
        action._group_name = "测试组"
        
        self.assertTrue(getattr(action, '_is_from_group', False))
        self.assertEqual(getattr(action, '_group_name', ''), "测试组")


if __name__ == '__main__':
    unittest.main()
