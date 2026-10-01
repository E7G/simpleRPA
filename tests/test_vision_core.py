import unittest

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


class VisionCoreTests(unittest.TestCase):
    def test_normalized_to_pixel(self):
        point = AgnesVisionProvider.normalized_to_pixel({"x": 500, "y": 250}, (400, 800))
        self.assertEqual(point, (200, 200))

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
