import sys
import os
import time
import unittest
from unittest.mock import patch, MagicMock
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestAction(unittest.TestCase):
    def setUp(self):
        from core.actions import Action, ActionType
        self.Action = Action
        self.ActionType = ActionType
    
    def test_create_mouse_click_action(self):
        action = self.Action(
            action_type=self.ActionType.MOUSE_CLICK,
            params={'x': 100, 'y': 200, 'button': 'left', 'clicks': 1}
        )
        self.assertEqual(action.action_type, self.ActionType.MOUSE_CLICK)
        self.assertEqual(action.params['x'], 100)
        self.assertEqual(action.params['y'], 200)
        self.assertIn("鼠标单击", action.description)
    
    def test_create_wait_action(self):
        action = self.Action(
            action_type=self.ActionType.WAIT,
            params={'seconds': 2.5}
        )
        self.assertEqual(action.action_type, self.ActionType.WAIT)
        self.assertEqual(action.params['seconds'], 2.5)
        self.assertIn("等待", action.description)
    
    def test_action_with_name(self):
        action = self.Action(
            action_type=self.ActionType.MOUSE_CLICK,
            params={'x': 100, 'y': 200},
            name="登录按钮"
        )
        self.assertEqual(action.name, "登录按钮")
        self.assertIn("[登录按钮]", action.description)
    
    def test_action_with_delay(self):
        action = self.Action(
            action_type=self.ActionType.MOUSE_CLICK,
            params={'x': 100, 'y': 200},
            delay_before=1.5
        )
        self.assertEqual(action.delay_before, 1.5)
        self.assertIn("[等待1.50秒]", action.description)
    
    def test_action_to_dict(self):
        action = self.Action(
            action_type=self.ActionType.MOUSE_CLICK,
            params={'x': 100, 'y': 200, 'button': 'left', 'clicks': 1},
            delay_before=0.5,
            delay_after=0.3,
            name="测试动作"
        )
        data = action.to_dict()
        self.assertEqual(data['action_type'], 'mouse_click')
        self.assertEqual(data['params']['x'], 100)
        self.assertEqual(data['delay_before'], 0.5)
        self.assertEqual(data['delay_after'], 0.3)
        self.assertEqual(data['name'], "测试动作")
    
    def test_action_from_dict(self):
        data = {
            'action_type': 'mouse_click',
            'params': {'x': 100, 'y': 200, 'button': 'left', 'clicks': 1},
            'delay_before': 0.5,
            'delay_after': 0.3,
            'name': "测试动作"
        }
        action = self.Action.from_dict(data)
        self.assertEqual(action.action_type, self.ActionType.MOUSE_CLICK)
        self.assertEqual(action.params['x'], 100)
        self.assertEqual(action.delay_before, 0.5)
        self.assertEqual(action.name, "测试动作")
    
    def test_action_to_code(self):
        action = self.Action(
            action_type=self.ActionType.MOUSE_CLICK,
            params={'x': 100, 'y': 200, 'button': 'left', 'clicks': 1}
        )
        code = action.to_code()
        self.assertIn("pyautogui.click", code)
        self.assertIn("100", code)
        self.assertIn("200", code)
    
    def test_action_validate_image_click_no_path(self):
        action = self.Action(
            action_type=self.ActionType.IMAGE_CLICK,
            params={}
        )
        valid, msg = action.validate()
        self.assertFalse(valid)
        self.assertIn("未设置图片路径", msg)
    
    def test_action_validate_image_click_file_not_exist(self):
        action = self.Action(
            action_type=self.ActionType.IMAGE_CLICK,
            params={'image_path': '/nonexistent/image.png'}
        )
        valid, msg = action.validate()
        self.assertFalse(valid)
        self.assertIn("图片文件不存在", msg)
    
    def test_action_validate_wait_negative(self):
        action = self.Action(
            action_type=self.ActionType.WAIT,
            params={'seconds': -1}
        )
        valid, msg = action.validate()
        self.assertFalse(valid)
        self.assertIn("负数", msg)
    
    def test_action_validate_mouse_click_invalid_coord(self):
        action = self.Action(
            action_type=self.ActionType.MOUSE_CLICK,
            params={'x': -100, 'y': 200}
        )
        valid, msg = action.validate()
        self.assertFalse(valid)
    
    def test_action_validate_success(self):
        action = self.Action(
            action_type=self.ActionType.MOUSE_CLICK,
            params={'x': 100, 'y': 200}
        )
        valid, msg = action.validate()
        self.assertTrue(valid)
        self.assertEqual(msg, "")
    
    def test_action_with_condition(self):
        action = self.Action(
            action_type=self.ActionType.MOUSE_CLICK,
            params={'x': 100, 'y': 200},
            condition="$image_found"
        )
        self.assertEqual(action.condition, "$image_found")
    
    def test_action_check_condition_variable(self):
        from core.actions import VariableManager
        
        var_manager = VariableManager.get_instance()
        var_manager.clear()
        
        action = self.Action(
            action_type=self.ActionType.MOUSE_CLICK,
            params={'x': 100, 'y': 200},
            condition="$test_var"
        )
        
        var_manager.set("test_var", False)
        self.assertFalse(action.check_condition())
        
        var_manager.set("test_var", True)
        self.assertTrue(action.check_condition())
    
    def test_action_check_condition_equals(self):
        from core.actions import VariableManager
        
        var_manager = VariableManager.get_instance()
        var_manager.clear()
        
        action = self.Action(
            action_type=self.ActionType.MOUSE_CLICK,
            params={'x': 100, 'y': 200},
            condition="$status==ready"
        )
        
        var_manager.set("status", "ready")
        self.assertTrue(action.check_condition())
        
        var_manager.set("status", "busy")
        self.assertFalse(action.check_condition())
    
    def test_action_check_condition_not_equals(self):
        from core.actions import VariableManager
        
        var_manager = VariableManager.get_instance()
        var_manager.clear()
        
        action = self.Action(
            action_type=self.ActionType.MOUSE_CLICK,
            params={'x': 100, 'y': 200},
            condition="$status!=error"
        )
        
        var_manager.set("status", "ready")
        self.assertTrue(action.check_condition())
        
        var_manager.set("status", "error")
        self.assertFalse(action.check_condition())


class TestVariableManager(unittest.TestCase):
    def setUp(self):
        from core.actions import VariableManager
        self.VariableManager = VariableManager
    
    def test_set_and_get(self):
        manager = self.VariableManager.get_instance()
        manager.clear()
        
        manager.set("test_var", 123)
        self.assertEqual(manager.get("test_var"), 123)
    
    def test_get_default(self):
        manager = self.VariableManager.get_instance()
        manager.clear()
        
        self.assertEqual(manager.get("nonexistent", "default"), "default")
    
    def test_has_variable(self):
        manager = self.VariableManager.get_instance()
        manager.clear()
        
        manager.set("exists", True)
        self.assertTrue(manager.has("exists"))
        self.assertFalse(manager.has("not_exists"))
    
    def test_clear(self):
        manager = self.VariableManager.get_instance()
        manager.set("var1", 1)
        manager.set("var2", 2)
        
        manager.clear()
        self.assertFalse(manager.has("var1"))
        self.assertFalse(manager.has("var2"))
    
    def test_get_all(self):
        manager = self.VariableManager.get_instance()
        manager.clear()
        manager.set("var1", 1)
        manager.set("var2", 2)
        
        all_vars = manager.get_all()
        self.assertEqual(len(all_vars), 2)


class TestActionManager(unittest.TestCase):
    def setUp(self):
        from core.actions import ActionManager, ActionType
        self.ActionManager = ActionManager
        self.ActionType = ActionType
    
    def test_get_action_definition(self):
        definition = self.ActionManager.get_action_definition(self.ActionType.MOUSE_CLICK)
        self.assertIsNotNone(definition)
        self.assertEqual(definition['name'], '鼠标单击')
        self.assertIn('params', definition)
    
    def test_get_all_categories(self):
        categories = self.ActionManager.get_all_categories()
        self.assertIsInstance(categories, dict)


class TestActionGroup(unittest.TestCase):
    def setUp(self):
        from core.action_group import ActionGroup
        from core.actions import Action, ActionType
        self.ActionGroup = ActionGroup
        self.Action = Action
        self.ActionType = ActionType
    
    def test_create_action_group(self):
        actions = [
            self.Action(action_type=self.ActionType.MOUSE_CLICK, params={'x': 100, 'y': 200}),
            self.Action(action_type=self.ActionType.WAIT, params={'seconds': 1})
        ]
        group = self.ActionGroup(
            name="测试组",
            description="测试描述",
            actions=actions
        )
        self.assertEqual(group.name, "测试组")
        self.assertEqual(group.description, "测试描述")
        self.assertEqual(group.get_action_count(), 2)
    
    def test_action_group_to_dict(self):
        actions = [
            self.Action(action_type=self.ActionType.MOUSE_CLICK, params={'x': 100, 'y': 200})
        ]
        group = self.ActionGroup(name="测试组", actions=actions)
        data = group.to_dict()
        self.assertEqual(data['name'], "测试组")
        self.assertEqual(len(data['actions']), 1)
    
    def test_action_group_from_dict(self):
        data = {
            'name': '测试组',
            'description': '测试描述',
            'actions': [
                {'action_type': 'mouse_click', 'params': {'x': 100, 'y': 200}}
            ]
        }
        group = self.ActionGroup.from_dict(data)
        self.assertEqual(group.name, "测试组")
        self.assertEqual(group.get_action_count(), 1)


class TestActionGroupManager(unittest.TestCase):
    def setUp(self):
        from core.action_group import ActionGroup, ActionGroupManager
        from core.actions import Action, ActionType
        
        self.ActionGroup = ActionGroup
        self.Action = Action
        self.ActionType = ActionType
        
        self.temp_dir = tempfile.mkdtemp()
        self.manager = ActionGroupManager()
        self.manager._groups_dir = self.temp_dir
        self.manager._groups = {}
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_save_and_get_group(self):
        actions = [self.Action(action_type=self.ActionType.MOUSE_CLICK, params={'x': 100, 'y': 200})]
        group = self.ActionGroup(name="测试组", actions=actions)
        
        result = self.manager.save_group(group)
        self.assertTrue(result)
        
        retrieved = self.manager.get_group("测试组")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.name, "测试组")
    
    def test_delete_group(self):
        actions = [self.Action(action_type=self.ActionType.MOUSE_CLICK, params={'x': 100, 'y': 200})]
        group = self.ActionGroup(name="待删除组", actions=actions)
        self.manager.save_group(group)
        
        result = self.manager.delete_group("待删除组")
        self.assertTrue(result)
        
        retrieved = self.manager.get_group("待删除组")
        self.assertIsNone(retrieved)
    
    def test_get_all_groups(self):
        actions = [self.Action(action_type=self.ActionType.MOUSE_CLICK, params={'x': 100, 'y': 200})]
        group1 = self.ActionGroup(name="组1", actions=actions)
        group2 = self.ActionGroup(name="组2", actions=actions)
        
        self.manager.save_group(group1)
        self.manager.save_group(group2)
        
        all_groups = self.manager.get_all_groups()
        self.assertEqual(len(all_groups), 2)
    
    def test_get_actions_copy(self):
        actions = [self.Action(action_type=self.ActionType.MOUSE_CLICK, params={'x': 100, 'y': 200})]
        group = self.ActionGroup(name="测试组", actions=actions)
        self.manager.save_group(group)
        
        copied = self.manager.get_actions_copy("测试组")
        self.assertEqual(len(copied), 1)
        self.assertIsNot(copied[0], actions[0])


class TestRecorder(unittest.TestCase):
    def setUp(self):
        from core.recorder import Recorder, RecordConfig
        self.Recorder = Recorder
        self.RecordConfig = RecordConfig
    
    def test_create_recorder(self):
        config = self.RecordConfig(
            record_mouse_click=True,
            record_keyboard=True
        )
        recorder = self.Recorder(config)
        self.assertEqual(recorder.config.record_mouse_click, True)
        self.assertEqual(recorder.config.record_keyboard, True)
    
    def test_recorder_initial_state(self):
        from core.recorder import RecordState
        recorder = self.Recorder()
        self.assertEqual(recorder.state, RecordState.IDLE)
        self.assertEqual(len(recorder.actions), 0)
    
    def test_recorder_config_image_click(self):
        config = self.RecordConfig(
            record_as_image_click=True,
            image_capture_size=50
        )
        self.assertTrue(config.record_as_image_click)
        self.assertEqual(config.image_capture_size, 50)


class TestPlayer(unittest.TestCase):
    def setUp(self):
        from core.player import Player, PlayerState
        self.Player = Player
        self.PlayerState = PlayerState
    
    def test_create_player(self):
        player = self.Player()
        player.speed = 1.5
        player.repeat_count = 2
        self.assertEqual(player.speed, 1.5)
        self.assertEqual(player.repeat_count, 2)
    
    def test_player_initial_state(self):
        player = self.Player()
        self.assertEqual(player.state, self.PlayerState.IDLE)
    
    def test_player_set_actions(self):
        from core.actions import Action, ActionType
        player = self.Player()
        actions = [
            Action(action_type=ActionType.MOUSE_CLICK, params={'x': 100, 'y': 200})
        ]
        player.actions = actions
        self.assertEqual(len(player.actions), 1)


class TestExporter(unittest.TestCase):
    def setUp(self):
        from core.exporter import Exporter
        from core.actions import Action, ActionType
        
        self.Exporter = Exporter
        self.Action = Action
        self.ActionType = ActionType
    
    def test_export_to_json(self):
        actions = [
            self.Action(action_type=self.ActionType.MOUSE_CLICK, params={'x': 100, 'y': 200}),
            self.Action(action_type=self.ActionType.WAIT, params={'seconds': 1})
        ]
        
        exporter = self.Exporter()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            result = exporter.export_to_json(actions, temp_path)
            self.assertTrue(result)
            
            imported = exporter.import_from_json(temp_path)
            self.assertEqual(len(imported), 2)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    def test_export_to_code(self):
        actions = [
            self.Action(action_type=self.ActionType.MOUSE_CLICK, params={'x': 100, 'y': 200}),
            self.Action(action_type=self.ActionType.KEY_TYPE, params={'text': 'hello'})
        ]
        
        exporter = self.Exporter()
        code = exporter._generate_python_code(actions)
        
        self.assertIn("import pyautogui", code)
        self.assertIn("pyautogui.click", code)
        self.assertIn("pyautogui.typewrite", code)
    
    def test_export_to_python_file(self):
        actions = [
            self.Action(action_type=self.ActionType.MOUSE_CLICK, params={'x': 100, 'y': 200})
        ]
        
        exporter = self.Exporter()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            temp_path = f.name
        
        try:
            result = exporter.export_to_python(actions, temp_path)
            self.assertTrue(result)
            
            with open(temp_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            self.assertIn("import pyautogui", content)
            self.assertIn("pyautogui.click", content)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


class TestConfig(unittest.TestCase):
    def setUp(self):
        from utils.config import Config
        self.Config = Config
    
    def test_default_config(self):
        config = self.Config()
        self.assertEqual(config.default_speed, 1.0)
        self.assertEqual(config.default_repeat_count, 1)
    
    def test_config_save_load(self):
        config = self.Config()
        config.default_speed = 2.0
        config.default_repeat_count = 3
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            config.save(temp_path)
            
            new_config = self.Config()
            new_config.load(temp_path)
            
            self.assertEqual(new_config.default_speed, 2.0)
            self.assertEqual(new_config.default_repeat_count, 3)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


class TestWindowUtils(unittest.TestCase):
    def setUp(self):
        from utils.window_utils import WindowUtils
        self.WindowUtils = WindowUtils
    
    @unittest.skipIf(sys.platform != 'win32', "Windows only")
    def test_get_all_windows(self):
        utils = self.WindowUtils()
        if utils.is_win32_available():
            windows = utils.get_all_windows()
            self.assertIsInstance(windows, list)
    
    @unittest.skipIf(sys.platform != 'win32', "Windows only")
    def test_get_window_rect(self):
        utils = self.WindowUtils()
        if utils.is_win32_available():
            windows = utils.get_all_windows()
            if windows:
                window = windows[0]
                rect = utils.get_window_rect(window.hwnd)
                if rect:
                    self.assertEqual(len(rect), 4)


class TestGUIComponents(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PyQt5.QtWidgets import QApplication
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()
    
    def test_coordinate_widget(self):
        from gui.widgets import CoordinateWidget
        
        widget = CoordinateWidget()
        widget.set_coordinates(100, 200)
        
        self.assertEqual(widget.get_coordinates(), (100, 200))
    
    def test_window_selector(self):
        from gui.widgets import WindowSelector
        
        selector = WindowSelector()
        selector.refresh_windows()
        
        self.assertIsNotNone(selector)
    
    def test_capture_widget_creation(self):
        from gui.widgets import CaptureWidget
        
        widget = CaptureWidget()
        self.assertIsNotNone(widget)
        self.assertIsNotNone(widget._screen_pixmap)
        widget.close()


class TestIntegration(unittest.TestCase):
    def test_full_workflow(self):
        from core.actions import Action, ActionType, ActionManager
        from core.exporter import Exporter
        
        actions = [
            Action(action_type=ActionType.MOUSE_CLICK, params={'x': 100, 'y': 200}),
            Action(action_type=ActionType.WAIT, params={'seconds': 0.5}),
            Action(action_type=ActionType.KEY_TYPE, params={'text': 'test'}),
        ]
        
        exporter = Exporter()
        code = exporter._generate_python_code(actions)
        
        self.assertIn("pyautogui.click", code)
        self.assertIn("time.sleep", code)
        self.assertIn("pyautogui.typewrite", code)
    
    def test_action_group_workflow(self):
        from core.actions import Action, ActionType
        from core.action_group import ActionGroup, ActionGroupManager
        
        actions = [
            Action(action_type=ActionType.MOUSE_CLICK, params={'x': 100, 'y': 200}, name="点击登录"),
            Action(action_type=ActionType.WAIT, params={'seconds': 0.5}),
        ]
        
        group = ActionGroup(name="登录流程", description="自动登录", actions=actions)
        
        temp_dir = tempfile.mkdtemp()
        manager = ActionGroupManager()
        manager._groups_dir = temp_dir
        manager._groups = {}
        
        manager.save_group(group)
        
        retrieved = manager.get_group("登录流程")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.get_action_count(), 2)
        
        copied_actions = manager.get_actions_copy("登录流程")
        self.assertEqual(len(copied_actions), 2)
        
        manager.delete_group("登录流程")
        self.assertIsNone(manager.get_group("登录流程"))
        
        shutil.rmtree(temp_dir, ignore_errors=True)


def run_tests():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestAction))
    suite.addTests(loader.loadTestsFromTestCase(TestVariableManager))
    suite.addTests(loader.loadTestsFromTestCase(TestActionManager))
    suite.addTests(loader.loadTestsFromTestCase(TestActionGroup))
    suite.addTests(loader.loadTestsFromTestCase(TestActionGroupManager))
    suite.addTests(loader.loadTestsFromTestCase(TestRecorder))
    suite.addTests(loader.loadTestsFromTestCase(TestPlayer))
    suite.addTests(loader.loadTestsFromTestCase(TestExporter))
    suite.addTests(loader.loadTestsFromTestCase(TestConfig))
    suite.addTests(loader.loadTestsFromTestCase(TestWindowUtils))
    suite.addTests(loader.loadTestsFromTestCase(TestGUIComponents))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
