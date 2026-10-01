import unittest

from core.actions import ActionManager, ActionType
from core.vision.agnes import AgnesVisionProvider
from core.vision.navigator import VisualNavigator


class FakeImage:
    size = (400, 800)


class FakeProvider:
    @staticmethod
    def normalized_to_pixel(result, image_size):
        return AgnesVisionProvider.normalized_to_pixel(result, image_size)

    def __init__(self):
        self.calls = 0

    def next_action(self, image, instruction, context=""):
        self.calls += 1
        if self.calls == 1:
            return {
                "status": "continue",
                "action": "click",
                "x": 500,
                "y": 250,
                "target": "关闭",
                "confidence": 0.99,
            }
        return {"status": "done", "action": "none", "reason": "页面已可操作"}


class RewardVerifyProvider:
    @staticmethod
    def normalized_to_pixel(result, image_size):
        return AgnesVisionProvider.normalized_to_pixel(result, image_size)

    def __init__(self):
        self.calls = 0
        self.contexts = []

    def next_action(self, image, instruction, context=""):
        self.calls += 1
        self.contexts.append(context)
        if self.calls == 1:
            return {"status": "done", "action": "none", "reason": "前三天已领取"}
        if self.calls == 2:
            return {
                "status": "continue",
                "action": "click",
                "x": 800,
                "y": 450,
                "target": "D4 亮着的可领取奖励",
                "confidence": 0.96,
            }
        return {"status": "done", "action": "none", "reason": "整页无可领取奖励"}


class FocusedD4Provider:
    @staticmethod
    def normalized_to_pixel(result, image_size):
        return AgnesVisionProvider.normalized_to_pixel(result, image_size)

    def __init__(self):
        self.next_calls = 0
        self.check_calls = 0

    def next_action(self, image, instruction, context=""):
        self.next_calls += 1
        return {"status": "done", "action": "none", "reason": "误判完成"}

    def check(self, image, query, context=""):
        self.check_calls += 1
        if self.check_calls == 1:
            return {
                "found": True,
                "x": 780,
                "y": 430,
                "confidence": 0.95,
                "target": "D4",
            }
        return {"found": False, "confidence": 0.95}


class LongTaskProvider:
    @staticmethod
    def normalized_to_pixel(result, image_size):
        return AgnesVisionProvider.normalized_to_pixel(result, image_size)

    def __init__(self, clicks_before_done=6, transient_failures=0):
        self.calls = 0
        self.successful_calls = 0
        self.clicks_before_done = clicks_before_done
        self.transient_failures = transient_failures
        self.contexts = []

    def next_action(self, image, instruction, context=""):
        self.calls += 1
        self.contexts.append(context)

        if self.transient_failures > 0:
            self.transient_failures -= 1
            raise RuntimeError("temporary provider timeout")

        self.successful_calls += 1
        if self.successful_calls <= self.clicks_before_done:
            return {
                "status": "continue",
                "action": "click",
                "x": 500,
                "y": 500,
                "target": f"步骤{self.successful_calls}",
                "confidence": 0.9,
            }

        return {"status": "done", "action": "none", "reason": "任务完成"}


class CorrectionAwareProvider:
    @staticmethod
    def normalized_to_pixel(result, image_size):
        return AgnesVisionProvider.normalized_to_pixel(result, image_size)

    def __init__(self):
        self.calls = 0
        self.contexts = []

    def next_action(self, image, instruction, context=""):
        self.calls += 1
        self.contexts.append(context)
        if self.calls == 1:
            return {
                "status": "continue",
                "action": "wait",
                "reason": "等待指正",
            }
        return {"status": "done", "action": "none", "reason": "已按指正完成"}


class VisionCoreTests(unittest.TestCase):
    def test_ai_actions_registered(self):
        expected = {
            ActionType.AI_VISUAL_CLICK,
            ActionType.AI_VISUAL_CHECK,
            ActionType.AI_VISUAL_NAVIGATE,
            ActionType.AI_VISUAL_TASK,
        }
        categories = ActionManager.get_all_categories()
        self.assertIn("AI视觉", categories)
        self.assertTrue(expected.issubset(set(categories["AI视觉"])))

    def test_normalized_to_pixel(self):
        point = AgnesVisionProvider.normalized_to_pixel({"x": 500, "y": 250}, (400, 800))
        self.assertEqual(point, (200, 200))

    def test_ai_task_default_budget_handles_multi_reward_pages(self):
        params = ActionManager.get_default_params(ActionType.AI_VISUAL_TASK)
        self.assertEqual(params["max_steps"], 30)

    def test_reward_task_rechecks_after_premature_done_and_clicks_d4(self):
        provider = RewardVerifyProvider()
        navigator = VisualNavigator(provider)
        clicks = []

        result = navigator.run(
            instruction="进入签到页面，把所有免费的可领取奖励领完",
            capture=lambda: FakeImage(),
            click=lambda x, y: clicks.append((x, y)) or True,
            max_steps=8,
            settle_seconds=0,
        )

        self.assertTrue(result)
        self.assertEqual(clicks, [(320, 360)])
        self.assertGreaterEqual(provider.calls, 4)
        self.assertIn("D4", provider.contexts[1])
        self.assertIn("逐个扫描", provider.contexts[1])

    def test_signin_done_runs_focused_d4_check_before_finishing(self):
        provider = FocusedD4Provider()
        navigator = VisualNavigator(provider)
        clicks = []

        result = navigator.run(
            instruction="进入签到页面，把所有免费的可领取奖励领完",
            capture=lambda: FakeImage(),
            click=lambda x, y: clicks.append((x, y)) or True,
            max_steps=6,
            settle_seconds=0,
        )

        self.assertTrue(result)
        self.assertEqual(clicks, [(312, 344)])
        self.assertGreaterEqual(provider.check_calls, 3)
        self.assertGreaterEqual(provider.next_calls, 3)

    def test_long_task_continues_beyond_soft_step_checkpoint(self):
        provider = LongTaskProvider(clicks_before_done=6)
        navigator = VisualNavigator(provider)
        clicks = []

        result = navigator.run(
            instruction="执行一个长任务",
            capture=lambda: FakeImage(),
            click=lambda x, y: clicks.append((x, y)) or True,
            max_steps=2,
            settle_seconds=0,
            long_running=True,
            max_runtime_seconds=120,
            retry_limit=5,
        )

        self.assertTrue(result)
        self.assertEqual(len(clicks), 6)
        self.assertGreater(provider.calls, 2)
        self.assertEqual(navigator.last_session_state["state"], "done")
        self.assertGreaterEqual(navigator.last_session_state["step"], 7)
        self.assertTrue(any("长任务检查点" in c for c in provider.contexts))

    def test_long_task_recovers_from_transient_provider_failures(self):
        provider = LongTaskProvider(clicks_before_done=1, transient_failures=2)
        navigator = VisualNavigator(provider)
        clicks = []

        result = navigator.run(
            instruction="执行一个长任务",
            capture=lambda: FakeImage(),
            click=lambda x, y: clicks.append((x, y)) or True,
            max_steps=2,
            settle_seconds=0,
            long_running=True,
            max_runtime_seconds=120,
            retry_limit=4,
        )

        self.assertTrue(result)
        self.assertEqual(len(clicks), 1)
        self.assertEqual(navigator.last_session_state["state"], "done")

    def test_ai_task_defaults_to_long_running_session(self):
        params = ActionManager.get_default_params(ActionType.AI_VISUAL_TASK)
        self.assertEqual(params["long_running"], 1)
        self.assertEqual(params["max_runtime_minutes"], 360)
        self.assertGreaterEqual(params["retry_limit"], 10)

    def test_live_correction_is_injected_into_next_agent_context(self):
        provider = CorrectionAwareProvider()
        navigator = VisualNavigator(provider)
        corrections = [["D4 还亮着，先点 D4"], []]
        events = []

        result = navigator.run(
            instruction="领取签到奖励",
            capture=lambda: FakeImage(),
            click=lambda x, y: True,
            max_steps=4,
            settle_seconds=0,
            long_running=True,
            correction_source=lambda: corrections.pop(0) if corrections else [],
            event_callback=lambda kind, message: events.append((kind, message)),
        )

        self.assertTrue(result)
        self.assertGreaterEqual(provider.calls, 3)
        self.assertIn("用户中途指正", provider.contexts[0])
        self.assertIn("D4 还亮着，先点 D4", provider.contexts[0])
        self.assertTrue(any(kind == "correction" for kind, _ in events))
        self.assertTrue(any(kind == "decision" for kind, _ in events))
        self.assertTrue(any(kind == "done" for kind, _ in events))

    def test_visual_navigator_bounded_click_loop(self):
        provider = FakeProvider()
        navigator = VisualNavigator(provider)
        clicks = []

        result = navigator.run(
            instruction="关闭公告",
            capture=lambda: FakeImage(),
            click=lambda x, y: clicks.append((x, y)) or True,
            max_steps=3,
            settle_seconds=0,
        )

        self.assertTrue(result)
        self.assertEqual(clicks, [(200, 200)])
        self.assertEqual(provider.calls, 2)


if __name__ == "__main__":
    unittest.main()
