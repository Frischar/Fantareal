from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

app = FastAPI(title="Scene Forge")

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent.parent if BASE_DIR.parent.name.lower() == "mods" else BASE_DIR.parent
CARD_WRITER_SETTINGS_PATH = PROJECT_ROOT / "data" / "card_writer" / "settings.json"
STATIC_DIR = BASE_DIR / "static"
TEMPLATE_DIR = BASE_DIR / "templates"

LLM_BASE_URL_ENV = "LLM_BASE_URL"
LLM_API_KEY_ENV = "LLM_API_KEY"
LLM_MODEL_ENV = "LLM_MODEL"
LLM_TIMEOUT_ENV = "LLM_REQUEST_TIMEOUT"
DEFAULT_LLM_TIMEOUT = 18
MAX_LLM_TIMEOUT = 24
DEFAULT_LLM_TEMPERATURE = 0.8


class SceneCompletePayload(BaseModel):
    brief: str = Field(default="", max_length=4000)
    prompt: str = Field(default="", max_length=12000)


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def index(request: Request) -> HTMLResponse:
    html_content = (TEMPLATE_DIR / "index.html").read_text(encoding="utf-8")
    mod_base_path = str(request.scope.get("root_path") or "").rstrip("/")
    html_content = html_content.replace("__MOD_BASE_PATH__", mod_base_path)
    return HTMLResponse(content=html_content, status_code=200)


@app.post("/api/complete")
async def api_complete_scene(payload: SceneCompletePayload) -> dict[str, Any]:
    brief = normalize_text(payload.brief)
    current_prompt = normalize_text(payload.prompt)
    if not brief and not current_prompt:
        raise HTTPException(status_code=400, detail="请先输入一个场景想法。")

    config = get_runtime_llm_config()
    if config["base_url"] and config["model"]:
        try:
            prompt = await call_scene_llm(brief=brief, current_prompt=current_prompt, config=config)
            return {"ok": True, "mode": "ai", "prompt": prompt}
        except HTTPException as exc:
            return {
                "ok": True,
                "mode": "local",
                "warning": str(exc.detail),
                "prompt": build_local_prompt(brief, current_prompt),
            }

    return {"ok": True, "mode": "local", "prompt": build_local_prompt(brief, current_prompt)}


def normalize_text(value: Any) -> str:
    return str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()


def read_card_writer_settings() -> dict[str, Any]:
    if not CARD_WRITER_SETTINGS_PATH.exists():
        return {}
    try:
        payload = json.loads(CARD_WRITER_SETTINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def as_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def get_runtime_llm_config() -> dict[str, Any]:
    settings = read_card_writer_settings()
    timeout_raw = normalize_text(os.getenv(LLM_TIMEOUT_ENV, ""))
    timeout = as_int(timeout_raw, DEFAULT_LLM_TIMEOUT) if timeout_raw else DEFAULT_LLM_TIMEOUT
    settings_timeout = as_int(settings.get("request_timeout"), timeout)
    temperature = as_float(settings.get("temperature"), DEFAULT_LLM_TEMPERATURE)
    return {
        "base_url": (normalize_text(settings.get("base_url")) or normalize_text(os.getenv(LLM_BASE_URL_ENV, ""))).rstrip("/"),
        "api_key": normalize_text(settings.get("api_key")) or normalize_text(os.getenv(LLM_API_KEY_ENV, "")),
        "model": normalize_text(settings.get("model")) or normalize_text(os.getenv(LLM_MODEL_ENV, "")),
        "request_timeout": min(max(settings_timeout, 4), MAX_LLM_TIMEOUT),
        "temperature": max(0.0, min(2.0, temperature)),
    }


def build_chat_completions_url(base_url: str) -> str:
    clean_base = base_url.strip().rstrip("/")
    if not clean_base:
        raise HTTPException(status_code=400, detail="未配置 LLM_BASE_URL。")
    if clean_base.endswith("/chat/completions"):
        return clean_base
    return f"{clean_base}/chat/completions"


def build_headers(api_key: str) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    key = api_key.strip()
    if key:
        try:
            key.encode("ascii")
        except UnicodeEncodeError as exc:
            raise HTTPException(status_code=400, detail="API Key 只能包含 ASCII 字符。") from exc
        headers["Authorization"] = f"Bearer {key}"
    return headers


async def call_scene_llm(*, brief: str, current_prompt: str, config: dict[str, Any]) -> str:
    request_payload = {
        "model": config["model"],
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是 Fantareal 的场景 Prompt 编排助手。"
                    "你的任务是把用户的一句话场景想法补全为可直接注入角色扮演聊天的场景 Prompt。"
                    "只返回一个 JSON 对象，格式为 {\"prompt\": \"...\"}。"
                    "Prompt 要具体、可执行、便于模型遵守；不要写模板说明，不要分很多可填字段。"
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "scene_idea": brief,
                        "current_prompt": current_prompt,
                        "requirements": [
                            "保留用户的核心想法，补足地点、时间、氛围、当前冲突、可互动元素和隐藏线索。",
                            "写成一段用户可继续修改的 Prompt，适合放入 system/context/director note。",
                            "不要替用户决定行动，不要一次性揭示全部秘密。",
                        ],
                    },
                    ensure_ascii=False,
                ),
            },
        ],
        "temperature": float(config.get("temperature") or DEFAULT_LLM_TEMPERATURE),
        "response_format": {"type": "json_object"},
    }
    try:
        async with httpx.AsyncClient(timeout=float(config["request_timeout"])) as client:
            response = await client.post(
                build_chat_completions_url(config["base_url"]),
                headers=build_headers(config["api_key"]),
                json=request_payload,
            )
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text.strip()[:500] if exc.response is not None else str(exc)
        raise HTTPException(status_code=502, detail=f"AI 请求失败：{detail}") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"AI 请求失败：{exc}") from exc

    try:
        raw_reply = str(response.json()["choices"][0]["message"]["content"])
    except (KeyError, IndexError, TypeError) as exc:
        raise HTTPException(status_code=502, detail="AI 返回格式无效。") from exc

    try:
        parsed = json.loads(raw_reply)
    except ValueError:
        parsed = {"prompt": raw_reply}
    prompt = normalize_text(parsed.get("prompt") if isinstance(parsed, dict) else "")
    if not prompt:
        raise HTTPException(status_code=502, detail="AI 没有返回可用 Prompt。")
    return prompt[:12000]


def build_local_prompt(brief: str, current_prompt: str) -> str:
    seed = brief or current_prompt or "一个尚未命名的场景"
    return (
        "请在接下来的角色扮演中使用以下场景上下文。\n\n"
        f"核心想法：{seed}\n\n"
        "场景要求：\n"
        "1. 明确当前地点、时间、光线、声音、气味或触感，让角色能自然观察到环境。\n"
        "2. 设置一个正在发生的小冲突或异常点，但不要立刻解释真相。\n"
        "3. 保留 2-3 个可互动元素，例如门、纸条、设备、伤口、屏幕、旧物或天气变化。\n"
        "4. 让隐藏线索先以细节出现，只有当用户主动检查、追问或靠近时才逐步揭示。\n"
        "5. 不要替用户做决定；优先描写非用户角色、环境反馈和当前场景变化。\n\n"
        "开场承接：从一个可见、可听或可触碰的细节开始，让用户能立刻选择下一步行动。"
    )
