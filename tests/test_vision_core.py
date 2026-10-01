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
