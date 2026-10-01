import time
from typing import Callable, Optional

from .agnes import AgnesVisionProvider


class VisualNavigator:
    """Bounded visual-agent loop used by AI visual actions."""

    def __init__(self, provider: Optional[AgnesVisionProvider] = None):
        self.provider = provider or AgnesVisionProvider()

    def run(
        self,
        instruction: str,
        capture: Callable[[], object],
        click: Callable[[int, int], bool],
        should_stop: Optional[Callable[[], bool]] = None,
        max_steps: int = 8,
        settle_seconds: float = 0.7,
    ) -> bool:
        history = []
        max_steps = max(1, min(int(max_steps), 40))
        verify_done = any(
            keyword in (instruction or "")
            for keyword in ("签到", "奖励", "领取", "战令", "元宝树", "招募", "游戏圈")
        )
        done_confirmations = 0

        for step in range(max_steps):
            if should_stop and should_stop():
                return False

            image = capture()
            if image is None:
                raise RuntimeError("AI视觉任务截图失败")

            context = "；".join(history[-4:])
            decision = self.provider.next_action(image, instruction, context=context)
            status = str(decision.get("status", "")).lower()
            action = str(decision.get("action", "")).lower()
            target = str(decision.get("target", "")).strip()
            reason = str(decision.get("reason", "")).strip()

            if status == "done":
                if not verify_done:
                    return True

                done_confirmations += 1
                if done_confirmations >= 2:
                    return True

                # Multi-reward pages are easy to finish too early when one bright
                # cell remains. Force a fresh full-page verification before
                # accepting "done".
                history.append(
                    f"第{step + 1}步：模型认为完成；开始收尾复核。"
                    "请逐个扫描整个页面所有亮着/高亮/可领取但尚未领取的奖励，"
                    "签到页尤其检查 D1~D7 和右上/中上区域的 D4；"
                    "若发现任何可领取项必须继续点击，不能提前结束。"
                )
                time.sleep(max(0.2, settle_seconds))
                continue

            done_confirmations = 0
            if status == "blocked":
                raise RuntimeError(reason or "视觉模型判断当前任务无法安全继续")

            if action == "wait":
                time.sleep(max(0.2, settle_seconds))
                history.append(f"第{step + 1}步：等待界面变化")
                continue

            if action == "click":
                x, y = self.provider.normalized_to_pixel(decision, image.size)
                if not click(x, y):
                    raise RuntimeError(f"AI视觉点击失败: {target or (x, y)}")
                history.append(f"第{step + 1}步：点击 {target or (x, y)}")
                time.sleep(max(0.2, settle_seconds))
                continue

            raise RuntimeError(reason or f"视觉模型返回了不可执行动作: {action}")

        raise RuntimeError(f"AI视觉任务超过最大步骤数 {max_steps}，已停止以避免误操作")

    def recover_safe_navigation(
        self,
        capture: Callable[[], object],
        click: Callable[[int, int], bool],
        goal: str = "关闭挡住操作的公告或普通提示；如果明显处于无关子页面则返回上一层或首页，使页面恢复可操作状态",
        should_stop: Optional[Callable[[], bool]] = None,
        max_steps: int = 4,
    ) -> bool:
        instruction = (
            "执行低风险界面整理。"
            + goal
            + "。如果页面已经干净并可继续业务任务，立即返回 done。"
            "不要领取或购买任何付费/消耗资源的内容。"
        )
        return self.run(
            instruction=instruction,
            capture=capture,
            click=click,
            should_stop=should_stop,
            max_steps=max_steps,
            settle_seconds=0.5,
        )
