import base64
import io
import json
import os
import re
import urllib.error
import urllib.request
import time
from typing import Any, Dict, Optional

from .example_knowledge import select_example_context


class AgnesVisionError(RuntimeError):
    pass


class AgnesVisionProvider:
    """Small OpenAI-compatible Agnes vision client.

    Environment variables:
      AGNES_API_KEY / AGNESAI_API_KEY
      AGNES_API_BASE (default: https://apihub.agnes-ai.com/v1)
      AGNES_MODEL (default: agnes-3.0-flash)
      AGNES_TIMEOUT (seconds)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        self.api_key = api_key or os.getenv("AGNES_API_KEY") or os.getenv("AGNESAI_API_KEY")
        self.base_url = (base_url or os.getenv("AGNES_API_BASE") or "https://apihub.agnes-ai.com/v1").rstrip("/")
        self.model = model or os.getenv("AGNES_MODEL") or "agnes-3.0-flash"
        self.timeout = float(timeout or os.getenv("AGNES_TIMEOUT") or 45)
        self.retries = max(0, min(int(os.getenv("AGNES_RETRIES") or 3), 8))

    def _require_key(self):
        if not self.api_key:
            raise AgnesVisionError(
                "未配置 Agnes API Key。请设置环境变量 AGNES_API_KEY（或 AGNESAI_API_KEY）。"
            )

    @staticmethod
    def _image_data_url(image, max_side: int = 1280, quality: int = 82) -> str:
        img = image.convert("RGB")
        if max(img.size) > max_side:
            img = img.copy()
            img.thumbnail((max_side, max_side))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        encoded = base64.b64encode(buf.getvalue()).decode("ascii")
        return f"data:image/jpeg;base64,{encoded}"

    @staticmethod
    def _extract_text(response: Dict[str, Any]) -> str:
        try:
            content = response["choices"][0]["message"]["content"]
        except Exception as exc:
            raise AgnesVisionError(f"Agnes 返回格式异常: {exc}") from exc

        if isinstance(content, str):
            return content
        if isinstance(content, list):
            chunks = []
            for item in content:
                if isinstance(item, dict):
                    text = item.get("text") or item.get("content")
                    if text:
                        chunks.append(str(text))
            return "\n".join(chunks)
        return str(content)

    @staticmethod
    def _parse_json(text: str) -> Dict[str, Any]:
        cleaned = text.strip()
        cleaned = re.sub(r"^\s*```(?:json)?\s*", "", cleaned, flags=re.I)
        cleaned = re.sub(r"\s*```\s*$", "", cleaned)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", cleaned, flags=re.S)
            if not match:
                raise AgnesVisionError(f"Agnes 未返回可解析 JSON: {text[:300]}")
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError as exc:
                raise AgnesVisionError(f"Agnes JSON 解析失败: {text[:300]}") from exc

    def _request(self, image, instruction: str, schema_hint: str, context: str = "") -> Dict[str, Any]:
        self._require_key()
        image_url = self._image_data_url(image)

        system = (
            "你是 simpleRPA 的视觉定位器。只根据当前截图做判断。"
            "坐标必须使用 0~1000 的归一化客户区坐标，左上角为 (0,0)，右下角为 (1000,1000)。"
            "只输出一个 JSON 对象，不要 Markdown，不要解释性前后缀。"
            "对于自动操作，只允许低风险界面导航，例如关闭公告/提示、返回、回首页、打开用户明确要求的功能。"
            "绝对不要自动执行购买、支付、充值、消耗货币、删除数据、修改账号安全设置、授权敏感权限。"
            "但是“领取/收下/签到领取一个已经免费可领取的奖励”属于低风险动作，应当允许；"
            "不要因为奖励物品本身稀有、可付费获得、可消耗或名称像付费道具，就误判为购买/消费。"
            "真正需要阻止的是点击后会扣除货币、消耗资源、发生支付或购买。"
            "如果任务是领取当前可领取的免费奖励，遇到未来天数、未解锁、前置条件未完成或当前不可领取的奖励时应直接跳过；"
            "当已经没有当前可免费领取的奖励时，应返回 done，而不是 blocked。"
            "对于签到/多格奖励页，禁止只根据前几个格子已领取就判断完成；"
            "必须从左到右、从上到下扫描整个可见奖励区域，检查每个仍亮着、高亮、有红点、发光边框或显示可领取状态的格子。"
            "签到页特别注意 D4：历史示例中 D4/中后段奖励可能位于上方偏右或第二行起始区域，"
            "即使 D1~D3 已领取，只要 D4 仍亮着就必须继续点击；每次领取后重新看截图。"
            "只有整页所有当前可领取项都已处理，才允许返回 done。"
            "上下文里如果提供了用户已有的历史 RPA 示例，必须把它们当作 few-shot 流程经验："
            "优先参考旧流程的页面顺序、入口区域、返回路径、循环条件和等待节奏；"
            "但旧坐标只能作为区域提示，每一步仍必须用当前截图验证语义目标后再点击。"
            "不要因为用户只说一句简短目标就忽略这些示例，也不要在尚可按历史路径继续导航时过早返回 blocked。"
            "对于长任务，页面加载中、网络波动、动画未结束、暂时看不懂当前页面时，应优先返回 continue+wait，"
            "不要用 blocked 结束整个任务；blocked 只用于明确的高风险操作或确定无法继续的不可恢复状态。"
        )
        user_text = f"任务：{instruction}\n输出格式：{schema_hint}"
        if context:
            user_text += f"\n上下文：{context}"

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_text},
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ],
                },
            ],
            "temperature": 0,
            "max_tokens": 500,
            "stream": False,
        }

        last_error = None

        for attempt in range(self.retries + 1):
            req = urllib.request.Request(
                f"{self.base_url}/chat/completions",
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )

            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    raw = resp.read().decode("utf-8")

                response = json.loads(raw)
                return self._parse_json(self._extract_text(response))

            except urllib.error.HTTPError as exc:
                body = exc.read().decode("utf-8", errors="replace")
                last_error = AgnesVisionError(
                    f"Agnes HTTP {exc.code}: {body[:500]}"
                )
                retryable = exc.code in (408, 409, 425, 429, 500, 502, 503, 504)
                if not retryable or attempt >= self.retries:
                    raise last_error from exc

            except (json.JSONDecodeError, AgnesVisionError) as exc:
                last_error = AgnesVisionError(
                    f"Agnes 返回解析失败: {str(exc)[:500]}"
                )
                if attempt >= self.retries:
                    raise last_error from exc

            except Exception as exc:
                last_error = AgnesVisionError(f"Agnes 请求失败: {exc}")
                if attempt >= self.retries:
                    raise last_error from exc

            # Short exponential backoff. VisualNavigator has a second, longer
            # recovery layer so a transient provider outage does not end a long task.
            time.sleep(min(4.0, 0.5 * (2 ** attempt)))

        raise last_error or AgnesVisionError("Agnes 请求失败")

    def locate(self, image, target: str, context: str = "") -> Dict[str, Any]:
        result = self._request(
            image,
            f"在画面中定位这个目标：{target}",
            '{"found":true|false,"x":0-1000,"y":0-1000,"confidence":0-1,"target":"识别到的目标","reason":"简短原因"}',
            context=context,
        )
        result.setdefault("found", False)
        return result

    def check(self, image, query: str, context: str = "") -> Dict[str, Any]:
        result = self._request(
            image,
            f"判断下面条件是否成立，并在成立时给出最相关目标位置：{query}",
            '{"found":true|false,"x":0-1000,"y":0-1000,"confidence":0-1,"target":"相关目标","reason":"简短原因"}',
            context=context,
        )
        result.setdefault("found", False)
        return result

    def next_action(self, image, instruction: str, context: str = "") -> Dict[str, Any]:
        example_context = select_example_context(instruction)
        runtime_context = (
            example_context
            + ("\n\n当前本次执行历史：\n" + context if context else "")
        )
        result = self._request(
            image,
            instruction,
            '{"status":"continue|done|blocked","action":"click|wait|none","x":0-1000,"y":0-1000,"target":"要操作的控件","confidence":0-1,"reason":"简短原因"}',
            context=runtime_context,
        )
        result.setdefault("status", "blocked")
        result.setdefault("action", "none")
        return result

    @staticmethod
    def normalized_to_pixel(result: Dict[str, Any], image_size):
        width, height = image_size
        x = max(0.0, min(1000.0, float(result.get("x", 0))))
        y = max(0.0, min(1000.0, float(result.get("y", 0))))
        px = int(round(width * x / 1000.0))
        py = int(round(height * y / 1000.0))
        px = min(max(px, 0), max(width - 1, 0))
        py = min(max(py, 0), max(height - 1, 0))
        return px, py
