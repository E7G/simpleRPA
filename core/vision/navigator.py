import time
from collections import deque
from typing import Callable, Optional

from .agnes import AgnesVisionProvider


class VisualNavigator:
    """Visual-agent loop with bounded short mode and resilient long-task mode."""

    def __init__(self, provider: Optional[AgnesVisionProvider] = None):
        self.provider = provider or AgnesVisionProvider()
        self.last_session_state = {}

    @staticmethod
    def _sleep_interruptible(
        seconds: float,
        should_stop: Optional[Callable[[], bool]] = None,
    ) -> bool:
        end = time.monotonic() + max(0.0, float(seconds))
        while time.monotonic() < end:
            if should_stop and should_stop():
                return False
            time.sleep(min(0.1, max(0.0, end - time.monotonic())))
        return True

    @staticmethod
    def _is_safety_block(reason: str) -> bool:
        text = (reason or "").lower()
        safety_words = (
            "购买", "支付", "充值", "扣除", "消耗货币", "消费资源",
            "删除数据", "账号安全", "敏感权限", "高风险",
            "purchase", "payment", "recharge", "delete", "unsafe",
        )
        return any(word in text for word in safety_words)

    def _update_state(
        self,
        *,
        state: str,
        step: int,
        started_at: float,
        instruction: str,
        consecutive_errors: int = 0,
        target: str = "",
        reason: str = "",
    ):
        self.last_session_state = {
            "state": state,
            "step": step,
            "elapsed_seconds": max(0.0, time.monotonic() - started_at),
            "instruction": instruction,
            "consecutive_errors": consecutive_errors,
            "target": target,
            "reason": reason,
        }

    def run(
        self,
        instruction: str,
        capture: Callable[[], object],
        click: Callable[[int, int], bool],
        should_stop: Optional[Callable[[], bool]] = None,
        max_steps: int = 8,
        settle_seconds: float = 0.7,
        long_running: bool = False,
        max_runtime_seconds: float = 7200,
        retry_limit: int = 10,
        correction_source: Optional[Callable[[], list]] = None,
        event_callback: Optional[Callable[[str, str], None]] = None,
    ) -> bool:
        """Run a visual task.

        Short mode keeps the traditional hard step limit. Long-running mode treats
        max_steps as a checkpoint cadence only; it keeps running until the task is
        done, the user stops it, the runtime budget expires, or repeated
        unrecoverable errors exceed retry_limit.
        """

        history = deque(maxlen=12)
        max_steps = max(1, min(int(max_steps), 100))
        retry_limit = max(1, min(int(retry_limit), 50))
        max_runtime_seconds = max(60.0, float(max_runtime_seconds or 7200))

        verify_done = any(
            keyword in (instruction or "")
            for keyword in ("签到", "奖励", "领取", "战令", "元宝树", "招募", "游戏圈")
        )
        done_confirmations = 0
        consecutive_errors = 0
        transient_blocks = 0
        step = 0
        started_at = time.monotonic()

        self._update_state(
            state="running",
            step=0,
            started_at=started_at,
            instruction=instruction,
        )

        def emit(kind: str, message: str):
            if event_callback:
                try:
                    event_callback(kind, message)
                except Exception:
                    pass

        emit("start", f"开始长任务：{instruction}" if long_running else f"开始任务：{instruction}")

        while True:
            if should_stop and should_stop():
                self._update_state(
                    state="stopped",
                    step=step,
                    started_at=started_at,
                    instruction=instruction,
                )
                emit("stop", "收到停止请求，结束当前 Agent 会话。")
                return False

            if correction_source:
                try:
                    corrections = correction_source() or []
                except Exception:
                    corrections = []
                for correction in corrections:
                    correction = str(correction or "").strip()
                    if not correction:
                        continue
                    history.append(
                        "【用户中途指正】" + correction
                        + "。从下一步开始优先遵循这条新要求；"
                        "若与旧目标冲突，以最新用户指正为准。"
                    )
                    emit("correction", f"已接收指正：{correction}")

            elapsed = time.monotonic() - started_at
            if long_running:
                if elapsed >= max_runtime_seconds:
                    self._update_state(
                        state="timeout",
                        step=step,
                        started_at=started_at,
                        instruction=instruction,
                        reason="长任务达到最大运行时间",
                    )
                    raise RuntimeError(
                        f"AI长任务已持续 {elapsed / 60:.1f} 分钟，达到最大运行时间 "
                        f"{max_runtime_seconds / 60:.0f} 分钟"
                    )
            elif step >= max_steps:
                raise RuntimeError(
                    f"AI视觉任务超过最大步骤数 {max_steps}，已停止以避免误操作"
                )

            if long_running and step > 0 and step % max_steps == 0:
                history.append(
                    f"长任务检查点：已完成 {step} 个视觉循环并继续执行；"
                    "不要因为步骤数较多而提前结束，只根据当前页面和任务完成条件判断。"
                )

            step += 1
            context = "；".join(history)
            emit("observe", f"步骤 {step}：正在获取当前后台画面并分析。")

            try:
                image = capture()
                if image is None:
                    raise RuntimeError("AI视觉任务截图失败")
            except Exception as exc:
                consecutive_errors += 1
                self._update_state(
                    state="recovering",
                    step=step,
                    started_at=started_at,
                    instruction=instruction,
                    consecutive_errors=consecutive_errors,
                    reason=f"截图失败: {exc}",
                )
                if not long_running or consecutive_errors > retry_limit:
                    raise RuntimeError(
                        f"AI视觉任务连续截图失败 {consecutive_errors} 次: {exc}"
                    ) from exc
                history.append(
                    f"第{step}步：后台截图临时失败，保持当前任务状态并重试。"
                )
                emit("recover", f"步骤 {step}：后台截图失败，自动恢复中（{consecutive_errors}/{retry_limit}）：{exc}")
                if not self._sleep_interruptible(
                    min(3.0, 0.4 * consecutive_errors),
                    should_stop,
                ):
                    return False
                continue

            try:
                decision = self.provider.next_action(
                    image,
                    instruction,
                    context=context,
                )
                consecutive_errors = 0
            except Exception as exc:
                consecutive_errors += 1
                self._update_state(
                    state="recovering",
                    step=step,
                    started_at=started_at,
                    instruction=instruction,
                    consecutive_errors=consecutive_errors,
                    reason=f"视觉模型暂时失败: {exc}",
                )
                if not long_running or consecutive_errors > retry_limit:
                    raise RuntimeError(
                        f"AI视觉模型连续失败 {consecutive_errors} 次: {exc}"
                    ) from exc

                history.append(
                    f"第{step}步：视觉模型请求/解析临时失败，保持当前页面和任务上下文，"
                    "稍后继续，不要重新开始任务。"
                )
                emit("recover", f"步骤 {step}：Agnes 暂时失败，保留上下文重试（{consecutive_errors}/{retry_limit}）：{exc}")
                if not self._sleep_interruptible(
                    min(6.0, 0.7 * consecutive_errors),
                    should_stop,
                ):
                    return False
                continue

            status = str(decision.get("status", "")).lower()
            action = str(decision.get("action", "")).lower()
            target = str(decision.get("target", "")).strip()
            reason = str(decision.get("reason", "")).strip()

            self._update_state(
                state="running",
                step=step,
                started_at=started_at,
                instruction=instruction,
                target=target,
                reason=reason,
            )
            emit(
                "decision",
                f"步骤 {step}：判断={status or 'continue'}，动作={action or 'none'}"
                + (f"，目标={target}" if target else "")
                + (f"，原因={reason}" if reason else ""),
            )

            if status == "done":
                if "签到" in (instruction or "") and hasattr(self.provider, "check"):
                    d4_check = None
                    try:
                        d4_check = self.provider.check(
                            image,
                            "只检查签到页的 D4/第4天奖励：它现在是否仍亮着、高亮、"
                            "有可领取状态且尚未领取？如果可领取 found=true 并给出该奖励"
                            "格或领取按钮的中心坐标；如果已领取、灰色、未来未解锁则 found=false。",
                            context=context,
                        )
                    except Exception as exc:
                        history.append(
                            f"签到 D4 专项复核暂时失败（{exc}），保持长任务状态，"
                            "继续执行整页奖励复核。"
                        )

                    if d4_check:
                        d4_confidence = float(
                            d4_check.get("confidence", 0) or 0
                        )
                        if d4_check.get("found") and d4_confidence >= 0.35:
                            x, y = self.provider.normalized_to_pixel(
                                d4_check,
                                image.size,
                            )
                            try:
                                clicked = click(x, y)
                            except Exception as exc:
                                clicked = False
                                reason = str(exc)
                            if not clicked:
                                consecutive_errors += 1
                                if not long_running or consecutive_errors > retry_limit:
                                    raise RuntimeError(
                                        "签到 D4 复核点击失败"
                                        + (f": {reason}" if reason else "")
                                    )
                                history.append(
                                    "签到 D4 已定位但后台点击临时失败；保持任务状态并重试。"
                                )
                                if not self._sleep_interruptible(
                                    min(3.0, 0.5 * consecutive_errors),
                                    should_stop,
                                ):
                                    return False
                                continue

                            history.append(
                                f"第{step}步：收尾复核发现 D4/第4天仍可领取，已点击。"
                            )
                            emit("click", f"步骤 {step}：D4 专项复核发现仍可领取，已点击 ({x}, {y})。")
                            done_confirmations = 0
                            consecutive_errors = 0
                            if not self._sleep_interruptible(
                                max(0.2, settle_seconds),
                                should_stop,
                            ):
                                return False
                            continue

                if not verify_done:
                    self._update_state(
                        state="done",
                        step=step,
                        started_at=started_at,
                        instruction=instruction,
                    )
                    emit("done", f"任务完成，共执行 {step} 个视觉循环。")
                    return True

                done_confirmations += 1
                if done_confirmations >= 2:
                    self._update_state(
                        state="done",
                        step=step,
                        started_at=started_at,
                        instruction=instruction,
                    )
                    emit("done", f"完成复核通过，共执行 {step} 个视觉循环。")
                    return True

                emit("verify", f"步骤 {step}：模型认为完成，正在做第二次全页复核。")
                history.append(
                    f"第{step}步：模型认为完成；开始收尾复核。"
                    "请逐个扫描整个页面所有亮着/高亮/可领取但尚未领取的奖励，"
                    "签到页尤其检查 D1~D7 和右上/中上区域的 D4；"
                    "若发现任何可领取项必须继续点击，不能提前结束。"
                )
                if not self._sleep_interruptible(
                    max(0.2, settle_seconds),
                    should_stop,
                ):
                    return False
                continue

            done_confirmations = 0

            if status == "blocked":
                if self._is_safety_block(reason):
                    self._update_state(
                        state="blocked",
                        step=step,
                        started_at=started_at,
                        instruction=instruction,
                        reason=reason,
                    )
                    raise RuntimeError(
                        reason or "视觉模型判断当前任务存在高风险操作"
                    )

                transient_blocks += 1
                if not long_running or transient_blocks > retry_limit:
                    raise RuntimeError(
                        reason or "视觉模型判断当前任务无法继续"
                    )

                emit("recover", f"步骤 {step}：暂时无法继续，尝试恢复：{reason or '原因不明'}")
                history.append(
                    f"第{step}步：模型暂时无法继续（{reason or '原因不明'}）。"
                    "不要结束整个长任务；重新观察当前页面，优先关闭普通弹窗、"
                    "等待加载或按历史路径恢复到任务流程。"
                )
                if not self._sleep_interruptible(
                    min(4.0, 0.7 * transient_blocks),
                    should_stop,
                ):
                    return False
                continue

            transient_blocks = 0

            if action == "wait":
                history.append(f"第{step}步：等待界面变化")
                emit("wait", f"步骤 {step}：等待页面稳定/加载完成。")
                if not self._sleep_interruptible(
                    max(0.2, settle_seconds),
                    should_stop,
                ):
                    return False
                continue

            if action == "click":
                x, y = self.provider.normalized_to_pixel(
                    decision,
                    image.size,
                )
                try:
                    clicked = click(x, y)
                except Exception as exc:
                    clicked = False
                    reason = str(exc)

                if not clicked:
                    consecutive_errors += 1
                    if not long_running or consecutive_errors > retry_limit:
                        raise RuntimeError(
                            f"AI视觉点击连续失败 {consecutive_errors} 次: "
                            f"{target or (x, y)}"
                            + (f" ({reason})" if reason else "")
                        )

                    history.append(
                        f"第{step}步：点击 {target or (x, y)} 临时失败，"
                        "保持当前任务状态，重新截图后再决定，不盲目重复同一坐标。"
                    )
                    if not self._sleep_interruptible(
                        min(3.0, 0.5 * consecutive_errors),
                        should_stop,
                    ):
                        return False
                    continue

                consecutive_errors = 0
                history.append(
                    f"第{step}步：点击 {target or (x, y)}"
                )
                emit("click", f"步骤 {step}：后台点击 {target or '目标'} @ ({x}, {y})。")
                if not self._sleep_interruptible(
                    max(0.2, settle_seconds),
                    should_stop,
                ):
                    return False
                continue

            consecutive_errors += 1
            if long_running and consecutive_errors <= retry_limit:
                history.append(
                    f"第{step}步：模型返回不可执行动作 {action or 'none'}"
                    f"（{reason or '无说明'}），保持长任务状态并重新观察。"
                )
                if not self._sleep_interruptible(
                    min(3.0, 0.5 * consecutive_errors),
                    should_stop,
                ):
                    return False
                continue

            raise RuntimeError(
                reason or f"视觉模型返回了不可执行动作: {action}"
            )

    def recover_safe_navigation(
        self,
        capture: Callable[[], object],
        click: Callable[[int, int], bool],
        goal: str = "关闭挡住操作的公告或普通提示；如果明显处于无关子页面则返回上一层或首页，使页面恢复可操作状态",
        should_stop: Optional[Callable[[], bool]] = None,
        max_steps: int = 4,
        correction_source: Optional[Callable[[], list]] = None,
        event_callback: Optional[Callable[[str, str], None]] = None,
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
            long_running=False,
            correction_source=correction_source,
            event_callback=event_callback,
        )
