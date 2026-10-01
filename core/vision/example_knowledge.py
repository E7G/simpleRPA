"""Task-aware example knowledge distilled from E7G/simpleRPAexample.

These are historical demonstrations, not hard-coded instructions. Agnes should
use them as priors about navigation/order/regions, while visually verifying the
current UI before every action.
"""

import json
import os
from pathlib import Path
from typing import List


GENERAL = """
历史示例总则（三国杀微信小程序）：
- 旧脚本几乎所有实际点击都以 background_mode=true 后台执行；不要为了执行任务激活或前置游戏窗口。
- 历史客户端大约是 430×820 的竖屏客户区；下面坐标只是旧版本的区域提示，UI 可能变化，必须先看当前截图确认语义目标，不能盲点。
- 多个活动入口过去常从左上区域约 (x=33~47,y=150~162) 进入。
- 多个流程结束后过去常从左下区域约 (x=37~51,y=796~805) 返回上一层/首页。
- 广告/活动关闭按钮过去经常位于右上区域约 (x=350~422,y=83~99)，但必须以当前截图的 X/关闭/返回语义为准。
- “领取免费奖励”允许点击已经可领取的免费奖励；奖励物品本身即使是珍宝招募令、货币或可消耗道具，也不等于发生购买。
- 未来日期、未解锁、条件不足、灰色不可领取项应跳过；没有当前可领取项时任务正常 done。
- 如果旧脚本和当前截图冲突，以当前截图为准；历史示例只用于理解页面路径和动作节奏。
""".strip()


EXAMPLES = [
    {
        "keywords": ("公告", "弹窗", "提示", "关闭"),
        "title": "关闭公告",
        "text": """
旧“关闭公告”示例：先用图片模板检查/点击公告关闭目标（confidence≈0.7），之后曾在右上区域约 (386,166) 再点一次关闭。说明该流程应优先识别遮挡层/X/关闭/我知道了，而不是进入业务页面。
""".strip(),
    },
    {
        "keywords": ("签到", "签到有礼", "每日签到"),
        "title": "签到有礼",
        "text": """
旧“签到有礼”示例全程后台：约 (37,157) 进入活动入口，约 (242,734) 进入签到；随后按多行奖励格从左到右/从上到下处理，历史奖励格区域包括 y≈320、467、577、602，领取/确认按钮常在右下区域 x≈337~364,y≈673~734；最后约 (37,796) 返回。新 Agent 应理解为“进入签到页→只点击当前可领取的奖励→每次领取后重新观察→未来/未解锁跳过→无可领项后返回”。
""".strip(),
    },
    {
        "keywords": ("元宝树", "浇水", "收获", "一键成熟"),
        "title": "元宝树",
        "text": """
旧“元宝树”示例：约 (35,150) 进入活动入口，约 (106,731) 进入元宝树。流程不是一次点击，而是循环：
1) 用图像检查是否可“收获”，可收获才执行收获；
2) 用 water_button_template 检查是否可“浇水”，可浇水才执行；
3) 多轮“浇水→再检查收获”；
4) 一键成熟按钮存在时再处理；
5) 没有可操作项才结束并约 (37,803) 返回。
历史“收获”主按钮区域约 (237,641)，确认/后续约 (351,518)；广告关闭曾在右上约 (376~422,85~90)。必须视觉确认后再操作。
""".strip(),
    },
    {
        "keywords": ("战令", "礼盒"),
        "title": "战令",
        "text": """
旧“战令自动领取”示例全程后台：约 (47,162) 进入活动区，约 (44,725) 进入战令；曾先用图片模板定位可领取入口。战令顶部有多个阶段/页签，历史横向区域约 x=141/202/260/322/376,y≈160；每个阶段都执行“检查当前是否有可领取礼盒→领取→若是免费广告奖励则等待广告结束并关闭→重新观察”，最后约 (40,801) 返回。不能把未解锁礼盒当错误；没有可领项应 done。
""".strip(),
    },
    {
        "keywords": ("游戏圈", "社区"),
        "title": "游戏圈",
        "text": """
旧“游戏圈自动领取”示例全程后台：约 (33,159) 进入活动入口，之后历史路径经过底部/右下区域 (341,815)、(112,732)，再在页面中部/下部完成领取，最终约 (40,800) 返回。应优先按“游戏圈/社区→可领取→领取/确认→返回”的语义路径视觉导航。
""".strip(),
    },
    {
        "keywords": ("招募", "免费招募", "珍宝招募令"),
        "title": "招募",
        "text": """
旧“招募自动领取”示例：先进入招募页，然后对“免费”按钮做 image_check + image_click，只有检测到免费状态才点击；部分免费次数会触发广告，旧流程等待广告后关闭。重要：免费领取/免费招募是允许动作；如果按钮显示需要元宝、货币或购买则不要点。历史最终约 (51,799) 返回。
""".strip(),
    },
    {
        "keywords": ("上上签", "抽签", "幸运"),
        "title": "幸运上上签",
        "text": """
旧“幸运上上签”示例：约 (45,155) 进入活动入口，约 (171,734) 进入抽签；免费广告流程曾重复多次，广告播放后再关闭并回到活动页，最后约 (38,805) 返回。只处理明确免费的次数。
""".strip(),
    },
    {
        "keywords": ("全部", "所有", "今天", "每日", "奖励都领", "能领"),
        "title": "每日奖励总流程",
        "text": """
旧主任务“三国杀小程序自动领取每日奖励”按顺序串联：关闭公告 → 商店/免费项 → 幸运上上签 → 签到有礼 → 元宝树 → 游戏圈 → 招募 → 战令 → 完成后关闭，并且主任务配置 offscreen=true、hide_taskbar=true。对于“把今天能领的东西都领了”之类宽泛目标，应把它理解为多个子任务逐个完成，而不是只在当前页面随便找一个领取按钮。
注意：历史“商店自动购买”包含可能消费资源的动作，只能作为页面导航参考，不能自动执行购买；除非用户明确授权具体购买行为。
""".strip(),
    },
]


SCRIPT_HINTS = {
    "公告": ("公告", "关闭"),
    "签到": ("签到",),
    "元宝树": ("元宝树", "浇水", "收获"),
    "游戏圈": ("游戏圈", "社区"),
    "招募": ("招募",),
    "战令": ("战令", "礼盒"),
    "上上签": ("上上签", "抽签", "幸运"),
    "俸禄": ("俸禄",),
}

BROAD_TASK_WORDS = ("全部", "所有", "今天", "每日", "都领", "能领")


def _find_local_example_dir():
    candidates = []
    configured = os.getenv("SIMPLERPA_EXAMPLE_DIR")
    if configured:
        candidates.append(Path(configured))

    repo_root = Path(__file__).resolve().parents[2]
    candidates.extend([
        repo_root.parent / "simpleRPAexample",
        Path("D:/Data/Github/simpleRPAexample"),
    ])

    for candidate in candidates:
        try:
            if candidate.is_dir():
                return candidate
        except OSError:
            continue
    return None


def _matching_script_paths(instruction: str, max_scripts: int = 4):
    root = _find_local_example_dir()
    if root is None:
        return []

    text = (instruction or "").lower()
    broad = any(word in text for word in BROAD_TASK_WORDS)
    scored = []

    for path in root.glob("*.rpa.json"):
        name = path.stem.lower()
        if "商店自动购买" in name and not any(k in text for k in ("商店", "购买")):
            # Purchasing scripts are not relevant to ordinary free-reward tasks.
            continue

        score = 0
        for group_name, keywords in SCRIPT_HINTS.items():
            if any(keyword in text for keyword in keywords) and group_name.lower() in name:
                score += 5
            elif broad and group_name.lower() in name:
                score += 1

        if any(keyword in name for keyword in ("关闭公告",)) and any(
            keyword in text for keyword in ("公告", "弹窗", "关闭", "提示")
        ):
            score += 5

        if score:
            scored.append((score, path.name, path))

    scored.sort(key=lambda item: (-item[0], item[1]))
    return [item[2] for item in scored[:max_scripts]]


def _compact_action(action):
    action_type = str(action.get("action_type", ""))
    params = action.get("params") or {}
    delay = float(action.get("delay_before", 0) or 0)
    repeat = int(action.get("repeat_count", 1) or 1)
    condition = str(action.get("condition", "") or "")

    if action_type == "mouse_click_relative":
        detail = f"后台相对点击({params.get('x')},{params.get('y')})"
    elif action_type in ("image_check", "image_click", "image_wait_click"):
        image_name = os.path.basename(str(params.get("image_path", "")))
        detail = (
            f"{action_type}({image_name}, confidence={params.get('confidence', '')})"
        )
    elif action_type == "action_group_ref":
        detail = f"动作组<{params.get('group_name', '')}>"
    else:
        detail = action_type

    suffix = []
    if delay >= 0.3:
        suffix.append(f"前等待≈{delay:.1f}s")
    if repeat > 1:
        suffix.append(f"重复×{repeat}")
    if condition:
        suffix.append(f"条件={condition}")

    if suffix:
        detail += " [" + ", ".join(suffix) + "]"
    return detail


def _summarize_local_script(path: Path, max_actions: int = 14, max_groups: int = 5):
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return ""

    actions = payload.get("actions") or []
    action_lines = [_compact_action(a) for a in actions[:max_actions]]
    if len(actions) > max_actions:
        action_lines.append(f"…另有 {len(actions) - max_actions} 个动作")

    group_lines = []
    groups = payload.get("action_groups") or {}
    for index, (name, group) in enumerate(groups.items()):
        if index >= max_groups:
            group_lines.append(f"…另有 {len(groups) - max_groups} 个动作组")
            break
        group_actions = group.get("actions") or []
        summary = " → ".join(_compact_action(a) for a in group_actions[:8])
        if len(group_actions) > 8:
            summary += f" → …({len(group_actions)}步)"
        group_lines.append(f"动作组<{name}>：{summary}")

    chunks = [
        f"【本机历史脚本：{payload.get('name') or path.name}】",
        "主流程：" + " → ".join(action_lines),
    ]
    if group_lines:
        chunks.append("\n".join(group_lines))
    chunks.append(
        "使用原则：这是用户已有的实际 RPA 示例，只用于理解路径/区域/节奏；"
        "当前截图与旧脚本不一致时，以当前截图的语义识别为准。"
    )
    return "\n".join(chunks)


def _local_example_context(instruction: str, max_scripts: int = 4):
    summaries = []
    for path in _matching_script_paths(instruction, max_scripts=max_scripts):
        summary = _summarize_local_script(path)
        if summary:
            summaries.append(summary)

    if not summaries:
        return ""

    return (
        "下面是从用户本机 simpleRPAexample 自动读取的相关历史脚本摘要；"
        "它们比通用猜测优先级更高，但仍需视觉确认：\n\n"
        + "\n\n".join(summaries)
    )


def select_example_context(instruction: str, max_examples: int = 4) -> str:
    text = (instruction or "").lower()
    scored: List[tuple] = []

    for index, item in enumerate(EXAMPLES):
        score = sum(1 for kw in item["keywords"] if kw.lower() in text)
        if score:
            scored.append((score, -index, item))

    scored.sort(reverse=True, key=lambda x: (x[0], x[1]))
    selected = [entry[2] for entry in scored[:max_examples]]

    # Navigation/cleanup tasks still benefit from the announcement example.
    if not selected and any(k in text for k in ("返回", "首页", "大厅", "整理", "遮挡")):
        selected = [EXAMPLES[0]]

    chunks = [GENERAL]
    if selected:
        chunks.append("与当前任务最相关的历史示例：")
        for item in selected:
            chunks.append(f"【{item['title']}】\n{item['text']}")

    local_examples = _local_example_context(instruction, max_scripts=max_examples)
    if local_examples:
        chunks.append(local_examples)

    return "\n\n".join(chunks)
