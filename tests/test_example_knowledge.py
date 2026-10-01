import json
import os
import tempfile
import unittest
from pathlib import Path

from core.vision.example_knowledge import select_example_context


class ExampleKnowledgeTests(unittest.TestCase):
    def test_relevant_local_script_is_injected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = {
                "name": "签到有礼自动领取脚本.rpa",
                "actions": [
                    {
                        "action_type": "mouse_click_relative",
                        "params": {"x": 37, "y": 157},
                        "delay_before": 2.2,
                        "background_mode": True,
                        "repeat_count": 1,
                    },
                    {
                        "action_type": "mouse_click_relative",
                        "params": {"x": 242, "y": 734},
                        "delay_before": 2.8,
                        "background_mode": True,
                        "repeat_count": 1,
                    },
                ],
                "action_groups": {},
            }
            (root / "签到有礼自动领取脚本.rpa.json").write_text(
                json.dumps(payload, ensure_ascii=False),
                encoding="utf-8",
            )

            old = os.environ.get("SIMPLERPA_EXAMPLE_DIR")
            os.environ["SIMPLERPA_EXAMPLE_DIR"] = str(root)
            try:
                context = select_example_context("进入签到页面，把免费的奖励领完")
            finally:
                if old is None:
                    os.environ.pop("SIMPLERPA_EXAMPLE_DIR", None)
                else:
                    os.environ["SIMPLERPA_EXAMPLE_DIR"] = old

            self.assertIn("本机历史脚本", context)
            self.assertIn("签到有礼自动领取脚本", context)
            self.assertIn("后台相对点击(37,157)", context)
            self.assertIn("后台相对点击(242,734)", context)

    def test_free_reward_context_does_not_promote_store_purchase(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "商店自动购买脚本.rpa.json").write_text(
                json.dumps(
                    {
                        "name": "商店自动购买脚本.rpa",
                        "actions": [
                            {
                                "action_type": "mouse_click_relative",
                                "params": {"x": 100, "y": 200},
                                "background_mode": True,
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            old = os.environ.get("SIMPLERPA_EXAMPLE_DIR")
            os.environ["SIMPLERPA_EXAMPLE_DIR"] = str(root)
            try:
                context = select_example_context("把今天所有免费的奖励都领了")
            finally:
                if old is None:
                    os.environ.pop("SIMPLERPA_EXAMPLE_DIR", None)
                else:
                    os.environ["SIMPLERPA_EXAMPLE_DIR"] = old

            self.assertNotIn("【本机历史脚本：商店自动购买脚本", context)
            self.assertIn("商店自动购买", context)  # only the safety note in broad-flow guidance


if __name__ == "__main__":
    unittest.main()
