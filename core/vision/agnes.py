import base64
import io
import json
import os
import re
import urllib.error
import urllib.request
from typing import Any, Dict, Optional


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
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise AgnesVisionError(f"Agnes HTTP {exc.code}: {body[:500]}") from exc
        except Exception as exc:
            raise AgnesVisionError(f"Agnes 请求失败: {exc}") from exc

        try:
            response = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise AgnesVisionError(f"Agnes 返回不是 JSON: {raw[:300]}") from exc
        return self._parse_json(self._extract_text(response))

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
        result = self._request(
            image,
            instruction,
            '{"status":"continue|done|blocked","action":"click|wait|none","x":0-1000,"y":0-1000,"target":"要操作的控件","confidence":0-1,"reason":"简短原因"}',
            context=context,
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
