from __future__ import annotations

import contextvars
import time
from collections.abc import Callable
from copy import deepcopy
from typing import Any
from urllib.parse import urlparse

import httpx


DEFAULT_ROUTE_FORWARDING_CONFIG: dict[str, Any] = {
    "enabled": False,
    "hook_all_posts": True,
    "failover_enabled": True,
    "rotate_keys": True,
    "retry_attempts": 3,
    "strategy": "priority",
    "providers": [],
}

RETRY_STATUS_CODES = {408, 409, 425, 429}
KNOWN_ENDPOINT_SUFFIXES = (
    "chat/completions",
    "messages",
    "embeddings",
    "rerank",
    "rerank/compress",
)
_hook_depth: contextvars.ContextVar[int] = contextvars.ContextVar("route_forwarding_hook_depth", default=0)


def _clamp_int(value: Any, min_value: int, max_value: int, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(min_value, min(max_value, parsed))


def _clean_text(value: Any, limit: int = 500) -> str:
    return str(value or "").strip()[:limit]


def sanitize_provider(raw: Any, index: int) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    name = _clean_text(raw.get("name"), 80) or f"Provider {index + 1}"
    base_url = _clean_text(raw.get("base_url"), 500)
    model = _clean_text(raw.get("model"), 160)
    keys_raw = raw.get("keys")
    keys: list[str] = []
    if isinstance(keys_raw, list):
        keys = [_clean_text(item, 500) for item in keys_raw if _clean_text(item, 500)]
    elif isinstance(keys_raw, str):
        keys = [_clean_text(item, 500) for item in keys_raw.replace(",", "\n").splitlines() if _clean_text(item, 500)]
    legacy_key = _clean_text(raw.get("api_key"), 500)
    if legacy_key and legacy_key not in keys:
        keys.insert(0, legacy_key)
    if not base_url and not keys:
        return None
    provider_id = _clean_text(raw.get("id"), 80) or f"provider-{index + 1}"
    return {
        "id": provider_id,
        "name": name,
        "base_url": base_url,
        "model": model,
        "keys": keys[:200],
        "enabled": bool(raw.get("enabled", True)),
        "priority": _clamp_int(raw.get("priority"), 1, 999, index + 1),
        "weight": _clamp_int(raw.get("weight"), 1, 100, 1),
        "tags": [_clean_text(item, 40) for item in raw.get("tags", []) if _clean_text(item, 40)]
        if isinstance(raw.get("tags"), list)
        else [],
    }


def sanitize_route_forwarding_config(raw: Any) -> dict[str, Any]:
    source = raw if isinstance(raw, dict) else {}
    providers = [
        provider
        for index, item in enumerate(source.get("providers") if isinstance(source.get("providers"), list) else [])
        if (provider := sanitize_provider(item, index)) is not None
    ]
    strategy = _clean_text(source.get("strategy"), 20)
    if strategy not in {"priority", "round_robin"}:
        strategy = "priority"
    config = dict(DEFAULT_ROUTE_FORWARDING_CONFIG)
    config.update(
        {
            "enabled": bool(source.get("enabled", config["enabled"])),
            "hook_all_posts": bool(source.get("hook_all_posts", config["hook_all_posts"])),
            "failover_enabled": bool(source.get("failover_enabled", config["failover_enabled"])),
            "rotate_keys": bool(source.get("rotate_keys", config["rotate_keys"])),
            "retry_attempts": _clamp_int(source.get("retry_attempts"), 1, 10, config["retry_attempts"]),
            "strategy": strategy,
            "providers": providers,
        }
    )
    return config


def should_retry_status_code(status_code: int) -> bool:
    return status_code in RETRY_STATUS_CODES or status_code >= 500


def endpoint_suffix_from_url(url: str) -> str:
    path = urlparse(str(url)).path.strip("/")
    if not path:
        return ""
    lowered = path.lower()
    for suffix in KNOWN_ENDPOINT_SUFFIXES:
        if lowered.endswith(suffix):
            return suffix
    if "/v1/" in lowered:
        return path[lowered.rfind("/v1/") + 4 :].strip("/")
    parts = path.split("/")
    return "/".join(parts[-2:]) if len(parts) >= 2 else parts[-1]


def build_forward_url(provider_base_url: str, original_url: str) -> str:
    clean_base = provider_base_url.strip().rstrip("/")
    if not clean_base:
        return str(original_url)
    parsed = urlparse(clean_base)
    base_path = parsed.path.strip("/").lower()
    if any(base_path.endswith(suffix) for suffix in KNOWN_ENDPOINT_SUFFIXES):
        return clean_base
    suffix = endpoint_suffix_from_url(str(original_url))
    return f"{clean_base}/{suffix}" if suffix else clean_base


def is_external_http_url(url: Any) -> bool:
    parsed = urlparse(str(url))
    host = (parsed.hostname or "").lower()
    if host in {"localhost", "127.0.0.1", "::1", "0.0.0.0", "testserver"}:
        return False
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def provider_keys(provider: dict[str, Any]) -> list[str]:
    keys = provider.get("keys")
    return [str(item).strip() for item in keys if str(item).strip()] if isinstance(keys, list) else []


class RouteForwardingRuntime:
    def __init__(self, get_config: Callable[[], dict[str, Any]]) -> None:
        self.get_config = get_config
        self._installed = False
        self._original_async_post: Any = None
        self._original_async_request: Any = None
        self._original_async_stream: Any = None
        self._original_sync_post: Any = None
        self._original_sync_request: Any = None
        self._rr_index = 0
        self._key_index: dict[str, int] = {}
        self.stats: dict[str, Any] = {
            "total_posts": 0,
            "routed_posts": 0,
            "failovers": 0,
            "last_provider": "",
            "last_url": "",
            "current_provider": "",
            "current_provider_id": "",
            "current_url": "",
            "providers": {},
            "events": [],
        }

    def install(self) -> None:
        if self._installed:
            return
        self._installed = True
        self._original_async_post = httpx.AsyncClient.post
        self._original_async_request = httpx.AsyncClient.request
        self._original_async_stream = httpx.AsyncClient.stream
        self._original_sync_post = httpx.Client.post
        self._original_sync_request = httpx.Client.request
        runtime = self

        async def patched_async_post(client: httpx.AsyncClient, url: Any, *args: Any, **kwargs: Any) -> httpx.Response:
            return await runtime.async_post(client, url, *args, **kwargs)

        async def patched_async_request(
            client: httpx.AsyncClient,
            method: str,
            url: Any,
            *args: Any,
            **kwargs: Any,
        ) -> httpx.Response:
            return await runtime.async_request(client, method, url, *args, **kwargs)

        def patched_async_stream(client: httpx.AsyncClient, method: str, url: Any, *args: Any, **kwargs: Any) -> Any:
            return runtime.async_stream(client, method, url, *args, **kwargs)

        def patched_sync_post(client: httpx.Client, url: Any, *args: Any, **kwargs: Any) -> httpx.Response:
            return runtime.sync_post(client, url, *args, **kwargs)

        def patched_sync_request(
            client: httpx.Client,
            method: str,
            url: Any,
            *args: Any,
            **kwargs: Any,
        ) -> httpx.Response:
            return runtime.sync_request(client, method, url, *args, **kwargs)

        httpx.AsyncClient.post = patched_async_post
        httpx.AsyncClient.request = patched_async_request
        httpx.AsyncClient.stream = patched_async_stream
        httpx.Client.post = patched_sync_post
        httpx.Client.request = patched_sync_request

    def snapshot(self) -> dict[str, Any]:
        config = sanitize_route_forwarding_config(self.get_config())
        self._sync_provider_statuses(config.get("providers", []))
        snapshot = deepcopy(self.stats)
        current_id = str(snapshot.get("current_provider_id", "") or "")
        for provider_id, status in snapshot.get("providers", {}).items():
            if isinstance(status, dict):
                status["current"] = provider_id == current_id
        return snapshot

    def _provider_id(self, provider: dict[str, Any]) -> str:
        return str(provider.get("id") or provider.get("name") or "").strip()

    def _provider_status(self, provider: dict[str, Any]) -> dict[str, Any]:
        provider_id = self._provider_id(provider)
        providers = self.stats.setdefault("providers", {})
        status = providers.setdefault(
            provider_id,
            {
                "state": "ready",
                "failures": 0,
                "last_error": "",
                "last_status": None,
                "last_used_at": 0,
                "last_test_at": 0,
                "last_test_ok": None,
                "circuit_opened_at": 0,
            },
        )
        status["name"] = str(provider.get("name", "") or "")
        status["priority"] = _clamp_int(provider.get("priority"), 1, 999, 999)
        status["enabled"] = bool(provider.get("enabled", True))
        if not status["enabled"] and status.get("state") != "circuit_open":
            status["state"] = "disabled"
        elif status["enabled"] and status.get("state") == "disabled":
            status["state"] = "ready"
        return status

    def _sync_provider_statuses(self, providers: list[Any]) -> None:
        known_ids: set[str] = set()
        for provider in providers:
            if not isinstance(provider, dict):
                continue
            provider_id = self._provider_id(provider)
            if not provider_id:
                continue
            known_ids.add(provider_id)
            self._provider_status(provider)
        statuses = self.stats.setdefault("providers", {})
        for provider_id in list(statuses):
            if provider_id not in known_ids:
                del statuses[provider_id]

    def _is_circuit_open(self, provider: dict[str, Any]) -> bool:
        return self._provider_status(provider).get("state") == "circuit_open"

    def _providers(self, config: dict[str, Any]) -> list[dict[str, Any]]:
        raw_providers = [item for item in config.get("providers", []) if isinstance(item, dict)]
        self._sync_provider_statuses(raw_providers)
        providers = [
            item
            for item in raw_providers
            if item.get("enabled") and not self._is_circuit_open(item)
        ]
        providers.sort(key=lambda item: (_clamp_int(item.get("priority"), 1, 999, 999), str(item.get("name", ""))))
        if config.get("strategy") == "round_robin" and providers:
            start = self._rr_index % len(providers)
            self._rr_index += 1
            providers = providers[start:] + providers[:start]
        return providers

    def _candidate_requests(self, url: Any, kwargs: dict[str, Any]) -> list[tuple[dict[str, Any], str, dict[str, Any]]]:
        config = sanitize_route_forwarding_config(self.get_config())
        if (
            not config.get("enabled")
            or not config.get("hook_all_posts")
            or _hook_depth.get() > 0
            or not is_external_http_url(url)
        ):
            return []
        candidates: list[tuple[dict[str, Any], str, dict[str, Any]]] = []
        for provider in self._providers(config):
            forward_url = build_forward_url(str(provider.get("base_url", "")), str(url))
            provider_keys_list = provider_keys(provider)
            selected_keys = provider_keys_list or [""]
            if config.get("rotate_keys") and provider_keys_list:
                key_start = self._key_index.get(str(provider.get("id")), 0) % len(provider_keys_list)
                self._key_index[str(provider.get("id"))] = key_start + 1
                selected_keys = [provider_keys_list[key_start]]
            for key in selected_keys:
                candidate_kwargs = self._rewrite_kwargs(kwargs, provider, key)
                candidates.append((provider, forward_url, candidate_kwargs))
        return candidates

    def _rewrite_kwargs(self, kwargs: dict[str, Any], provider: dict[str, Any], api_key: str) -> dict[str, Any]:
        candidate = deepcopy(kwargs)
        headers = dict(candidate.get("headers") or {})
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        else:
            headers.pop("Authorization", None)
        headers.setdefault("Content-Type", "application/json")
        candidate["headers"] = headers
        model = str(provider.get("model", "") or "").strip()
        payload = candidate.get("json")
        if model and isinstance(payload, dict) and "model" in payload:
            payload = deepcopy(payload)
            payload["model"] = model
            candidate["json"] = payload
        return candidate

    def _record(
        self,
        provider: dict[str, Any],
        url: str,
        *,
        failed: bool = False,
        status_code: int | None = None,
        error: str = "",
    ) -> None:
        self.stats["routed_posts"] += 1
        self.stats["last_provider"] = str(provider.get("name", ""))
        self.stats["last_url"] = url
        self.stats["current_provider"] = str(provider.get("name", ""))
        self.stats["current_provider_id"] = self._provider_id(provider)
        self.stats["current_url"] = url
        status = self._provider_status(provider)
        status["last_used_at"] = int(time.time())
        status["last_url"] = url
        status["last_status"] = status_code
        if failed:
            status["state"] = "retrying" if status.get("state") != "circuit_open" else "circuit_open"
            status["last_error"] = error or (f"HTTP {status_code}" if status_code else "")
        else:
            status["state"] = "ready"
            status["failures"] = 0
            status["last_error"] = ""
            status["circuit_opened_at"] = 0
        event = {
            "time": int(time.time()),
            "provider": self.stats["last_provider"],
            "url": url,
            "failed": failed,
            "status_code": status_code,
            "error": error,
        }
        events = self.stats.setdefault("events", [])
        events.insert(0, event)
        del events[20:]

    def _open_circuit(self, provider: dict[str, Any], detail: str) -> None:
        status = self._provider_status(provider)
        status["state"] = "circuit_open"
        status["failures"] = self._retry_attempts()
        status["last_error"] = detail[:500]
        status["circuit_opened_at"] = int(time.time())
        self.stats["failovers"] += 1

    def _retry_attempts(self) -> int:
        return _clamp_int(
            sanitize_route_forwarding_config(self.get_config()).get("retry_attempts"),
            1,
            10,
            DEFAULT_ROUTE_FORWARDING_CONFIG["retry_attempts"],
        )

    async def test_provider(self, provider_id: str) -> dict[str, Any]:
        config = sanitize_route_forwarding_config(self.get_config())
        provider = next((item for item in config.get("providers", []) if self._provider_id(item) == provider_id), None)
        if not provider:
            return {"ok": False, "provider_id": provider_id, "error": "Provider not found."}
        if not str(provider.get("base_url", "") or "").strip():
            return {"ok": False, "provider_id": provider_id, "error": "Provider URL is empty."}

        keys = provider_keys(provider)
        test_url = build_forward_url(str(provider.get("base_url", "")), "https://fantareal.test/v1/chat/completions")
        payload = {
            "model": str(provider.get("model", "") or "test").strip(),
            "messages": [{"role": "user", "content": "ping"}],
            "max_tokens": 1,
            "stream": False,
        }
        request_kwargs = self._rewrite_kwargs({"json": payload, "timeout": 20}, provider, keys[0] if keys else "")
        status = self._provider_status(provider)
        status["state"] = "testing"
        status["last_test_at"] = int(time.time())
        token = _hook_depth.set(_hook_depth.get() + 1)
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                post = self._original_async_post or httpx.AsyncClient.post
                response = await post(client, test_url, **request_kwargs)
                response_text = ""
                try:
                    response_text = (await response.aread()).decode("utf-8", errors="ignore")[:500]
                finally:
                    await response.aclose()
                ok = 200 <= response.status_code < 300
                status["last_status"] = response.status_code
                status["last_test_ok"] = ok
                if ok:
                    status["state"] = "ready"
                    status["failures"] = 0
                    status["last_error"] = ""
                    status["circuit_opened_at"] = 0
                    return {
                        "ok": True,
                        "provider_id": provider_id,
                        "provider": str(provider.get("name", "")),
                        "status_code": response.status_code,
                    }
                detail = f"HTTP {response.status_code}"
                if response_text:
                    detail = f"{detail}: {response_text}"
                status["state"] = "circuit_open"
                status["last_error"] = detail[:500]
                return {
                    "ok": False,
                    "provider_id": provider_id,
                    "provider": str(provider.get("name", "")),
                    "status_code": response.status_code,
                    "error": detail[:500],
                }
        except httpx.HTTPError as exc:
            detail = str(exc)[:500]
            status["state"] = "circuit_open"
            status["last_test_ok"] = False
            status["last_error"] = detail
            return {
                "ok": False,
                "provider_id": provider_id,
                "provider": str(provider.get("name", "")),
                "error": detail,
            }
        finally:
            _hook_depth.reset(token)

    async def async_post(self, client: httpx.AsyncClient, url: Any, *args: Any, **kwargs: Any) -> httpx.Response:
        self.stats["total_posts"] += 1
        candidates = self._candidate_requests(url, kwargs)
        if not candidates:
            return await self._original_async_post(client, url, *args, **kwargs)
        failover_enabled = bool(sanitize_route_forwarding_config(self.get_config()).get("failover_enabled", True))
        retry_attempts = self._retry_attempts() if failover_enabled else 1
        token = _hook_depth.set(_hook_depth.get() + 1)
        last_error: Exception | None = None
        try:
            for index, (provider, forward_url, candidate_kwargs) in enumerate(candidates):
                for attempt in range(1, retry_attempts + 1):
                    try:
                        response = await self._original_async_post(client, forward_url, *args, **candidate_kwargs)
                        failed = should_retry_status_code(response.status_code)
                        self._record(provider, forward_url, failed=failed, status_code=response.status_code)
                        if not failover_enabled or not failed:
                            return response
                        if attempt == retry_attempts:
                            self._open_circuit(provider, f"HTTP {response.status_code} after {retry_attempts} attempts.")
                            if index == len(candidates) - 1:
                                return response
                            await response.aread()
                            await response.aclose()
                            break
                        await response.aread()
                        await response.aclose()
                    except httpx.HTTPError as exc:
                        last_error = exc
                        self._record(provider, forward_url, failed=True, error=str(exc))
                        if not failover_enabled:
                            raise
                        if attempt == retry_attempts:
                            self._open_circuit(provider, f"{exc} after {retry_attempts} attempts.")
                            if index == len(candidates) - 1:
                                raise
                            break
            if last_error:
                raise last_error
            return await self._original_async_post(client, url, *args, **kwargs)
        finally:
            _hook_depth.reset(token)

    async def async_request(
        self,
        client: httpx.AsyncClient,
        method: str,
        url: Any,
        *args: Any,
        **kwargs: Any,
    ) -> httpx.Response:
        if str(method).upper() != "POST" or _hook_depth.get() > 0:
            return await self._original_async_request(client, method, url, *args, **kwargs)
        self.stats["total_posts"] += 1
        candidates = self._candidate_requests(url, kwargs)
        if not candidates:
            return await self._original_async_request(client, method, url, *args, **kwargs)
        failover_enabled = bool(sanitize_route_forwarding_config(self.get_config()).get("failover_enabled", True))
        retry_attempts = self._retry_attempts() if failover_enabled else 1
        token = _hook_depth.set(_hook_depth.get() + 1)
        last_error: Exception | None = None
        try:
            for index, (provider, forward_url, candidate_kwargs) in enumerate(candidates):
                for attempt in range(1, retry_attempts + 1):
                    try:
                        response = await self._original_async_request(
                            client,
                            method,
                            forward_url,
                            *args,
                            **candidate_kwargs,
                        )
                        failed = should_retry_status_code(response.status_code)
                        self._record(provider, forward_url, failed=failed, status_code=response.status_code)
                        if not failover_enabled or not failed:
                            return response
                        if attempt == retry_attempts:
                            self._open_circuit(provider, f"HTTP {response.status_code} after {retry_attempts} attempts.")
                            if index == len(candidates) - 1:
                                return response
                            await response.aread()
                            await response.aclose()
                            break
                        await response.aread()
                        await response.aclose()
                    except httpx.HTTPError as exc:
                        last_error = exc
                        self._record(provider, forward_url, failed=True, error=str(exc))
                        if not failover_enabled:
                            raise
                        if attempt == retry_attempts:
                            self._open_circuit(provider, f"{exc} after {retry_attempts} attempts.")
                            if index == len(candidates) - 1:
                                raise
                            break
            if last_error:
                raise last_error
            return await self._original_async_request(client, method, url, *args, **kwargs)
        finally:
            _hook_depth.reset(token)

    def async_stream(self, client: httpx.AsyncClient, method: str, url: Any, *args: Any, **kwargs: Any) -> Any:
        if str(method).upper() != "POST" or _hook_depth.get() > 0:
            return self._original_async_stream(client, method, url, *args, **kwargs)
        self.stats["total_posts"] += 1
        candidates = self._candidate_requests(url, kwargs)
        if not candidates:
            return self._original_async_stream(client, method, url, *args, **kwargs)
        provider, forward_url, candidate_kwargs = candidates[0]
        self._record(provider, forward_url)
        return self._original_async_stream(client, method, forward_url, *args, **candidate_kwargs)

    def sync_post(self, client: httpx.Client, url: Any, *args: Any, **kwargs: Any) -> httpx.Response:
        self.stats["total_posts"] += 1
        candidates = self._candidate_requests(url, kwargs)
        if not candidates:
            return self._original_sync_post(client, url, *args, **kwargs)
        failover_enabled = bool(sanitize_route_forwarding_config(self.get_config()).get("failover_enabled", True))
        retry_attempts = self._retry_attempts() if failover_enabled else 1
        token = _hook_depth.set(_hook_depth.get() + 1)
        last_error: Exception | None = None
        try:
            for index, (provider, forward_url, candidate_kwargs) in enumerate(candidates):
                for attempt in range(1, retry_attempts + 1):
                    try:
                        response = self._original_sync_post(client, forward_url, *args, **candidate_kwargs)
                        failed = should_retry_status_code(response.status_code)
                        self._record(provider, forward_url, failed=failed, status_code=response.status_code)
                        if not failover_enabled or not failed:
                            return response
                        if attempt == retry_attempts:
                            self._open_circuit(provider, f"HTTP {response.status_code} after {retry_attempts} attempts.")
                            if index == len(candidates) - 1:
                                return response
                            response.close()
                            break
                        response.close()
                    except httpx.HTTPError as exc:
                        last_error = exc
                        self._record(provider, forward_url, failed=True, error=str(exc))
                        if not failover_enabled:
                            raise
                        if attempt == retry_attempts:
                            self._open_circuit(provider, f"{exc} after {retry_attempts} attempts.")
                            if index == len(candidates) - 1:
                                raise
                            break
            if last_error:
                raise last_error
            return self._original_sync_post(client, url, *args, **kwargs)
        finally:
            _hook_depth.reset(token)

    def sync_request(
        self,
        client: httpx.Client,
        method: str,
        url: Any,
        *args: Any,
        **kwargs: Any,
    ) -> httpx.Response:
        if str(method).upper() != "POST" or _hook_depth.get() > 0:
            return self._original_sync_request(client, method, url, *args, **kwargs)
        self.stats["total_posts"] += 1
        candidates = self._candidate_requests(url, kwargs)
        if not candidates:
            return self._original_sync_request(client, method, url, *args, **kwargs)
        failover_enabled = bool(sanitize_route_forwarding_config(self.get_config()).get("failover_enabled", True))
        retry_attempts = self._retry_attempts() if failover_enabled else 1
        token = _hook_depth.set(_hook_depth.get() + 1)
        last_error: Exception | None = None
        try:
            for index, (provider, forward_url, candidate_kwargs) in enumerate(candidates):
                for attempt in range(1, retry_attempts + 1):
                    try:
                        response = self._original_sync_request(
                            client,
                            method,
                            forward_url,
                            *args,
                            **candidate_kwargs,
                        )
                        failed = should_retry_status_code(response.status_code)
                        self._record(provider, forward_url, failed=failed, status_code=response.status_code)
                        if not failover_enabled or not failed:
                            return response
                        if attempt == retry_attempts:
                            self._open_circuit(provider, f"HTTP {response.status_code} after {retry_attempts} attempts.")
                            if index == len(candidates) - 1:
                                return response
                            response.close()
                            break
                        response.close()
                    except httpx.HTTPError as exc:
                        last_error = exc
                        self._record(provider, forward_url, failed=True, error=str(exc))
                        if not failover_enabled:
                            raise
                        if attempt == retry_attempts:
                            self._open_circuit(provider, f"{exc} after {retry_attempts} attempts.")
                            if index == len(candidates) - 1:
                                raise
                            break
            if last_error:
                raise last_error
            return self._original_sync_request(client, method, url, *args, **kwargs)
        finally:
            _hook_depth.reset(token)
