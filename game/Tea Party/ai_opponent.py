"""AI 对手逻辑 — 调用 LLM 获取游戏决策。

此模块依赖项目现有的 LLM 调用函数（request_json）。
"""

from __future__ import annotations

import re
import random
from typing import Any, Callable

from .ai_instructions import build_ai_system_prompt, build_ai_user_message


# ═══════════════════════════════════════════
# LLM 响应解析
# ═══════════════════════════════════════════

_VALID_ITEM_NAMES = {
    "candy_lens", "bubble_soda", "cat_paw_ribbon", "double_glitter",
    "strawberry_cake", "whisper_conch", "miracle_wand",
    "phantom_cat_gloves", "kiwi_juice",
}


def _parse_ai_response(content: str) -> dict:
    """从 LLM 响应文本中解析 DECISION 和 DIALOGUE。

    支持的格式（由 AI 说明书约定）：
    DECISION:
    - items_to_use: [item1, item2]
    - target: opponent

    DIALOGUE:
    (对话内容)

    解析失败时返回随机 fallback。
    """
    result = {
        "items_to_use": [],
        "target": "opponent",
        "dialogue": "",
    }

    if not content:
        return _fallback_decision()

    # 提取 DECISION 块
    decision_match = re.search(
        r'items_to_use\s*:\s*\[(.*?)\]',
        content,
        re.IGNORECASE,
    )
    if decision_match:
        items_str = decision_match.group(1)
        items = re.findall(r'[a-z_]+', items_str)
        result["items_to_use"] = [it for it in items if it in _VALID_ITEM_NAMES]

    target_match = re.search(
        r'target\s*:\s*(self|opponent)',
        content,
        re.IGNORECASE,
    )
    if target_match:
        result["target"] = target_match.group(1).lower()

    # 提取 DIALOGUE 块
    dialogue_match = re.search(
        r'DIALOGUE\s*:\s*\n(.*?)(?:```|$)',
        content,
        re.DOTALL | re.IGNORECASE,
    )
    if dialogue_match:
        result["dialogue"] = dialogue_match.group(1).strip()
    else:
        # 尝试匹配 DECISION 之后的文字
        after_decision = re.split(r'DECISION\s*:', content, flags=re.IGNORECASE)
        if len(after_decision) > 1:
            dialogue_part = re.split(r'DIALOGUE\s*:', after_decision[1], flags=re.IGNORECASE)
            if len(dialogue_part) > 1:
                result["dialogue"] = dialogue_part[1].strip().rstrip("```").strip()

    if not result["dialogue"]:
        result["dialogue"] = "轮到我了！"

    return result


def _fallback_decision() -> dict:
    """LLM 调用失败或解析失败时的随机 fallback。"""
    return {
        "items_to_use": [],
        "target": random.choice(["self", "opponent"]),
        "dialogue": "嗯…让我想想该怎么办…",
    }


# ═══════════════════════════════════════════
# AI 对手请求
# ═══════════════════════════════════════════

async def request_ai_action(
    sanitized_state: dict,
    persona: dict,
    llm_config: dict,
    request_json_func: Callable[..., Any],
) -> dict:
    """调用 LLM 获取 AI 对手的游戏决策。

    Args:
        sanitized_state: get_sanitized_state() 的输出
        persona: 角色卡 persona 字典（含 name, system_prompt, greeting）
        llm_config: get_runtime_chat_config() 的输出（含 base_url, api_key, model, temperature, request_timeout）
        request_json_func: app.request_json 协程（或兼容的 request_json 函数）

    Returns:
        {"items_to_use": [...], "target": "opponent"|"self", "dialogue": "..."}
    """
    system_prompt = build_ai_system_prompt(persona)
    user_message = build_ai_user_message(sanitized_state)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    try:
        base_url = llm_config.get("base_url", "").rstrip("/")
        url = f"{base_url}/chat/completions" if base_url else ""

        payload = {
            "model": llm_config.get("model", ""),
            "messages": messages,
            "temperature": float(llm_config.get("temperature", 0.85)),
        }

        api_key = llm_config.get("api_key", "")
        timeout = int(llm_config.get("request_timeout", 30))

        data = await request_json_func(
            url=url,
            api_key=api_key,
            payload=payload,
            request_timeout=timeout,
        )

        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return _parse_ai_response(content)

    except Exception:
        return _fallback_decision()
