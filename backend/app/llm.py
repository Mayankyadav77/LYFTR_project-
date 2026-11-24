import os
import time
import json
import hashlib
from typing import List, Dict, Any, Optional, Tuple
import litellm
from litellm.caching.caching import Cache

# Enable litellm in-memory cache
try:
    litellm.cache = Cache(type="local")
except Exception:
    pass

class LLMService:
    def __init__(self):
        self.default_model = os.getenv("LLM_MODEL", "gemini/gemini-2.5-flash")
        self.keys = self._load_keys()
        self.enable_failure_simulation = os.getenv("ENABLE_FAILURE_SIMULATION", "false").lower() in ("true", "1", "yes")

    def _load_keys(self) -> List[Tuple[str, str]]:
        raw_keys = os.getenv("LLM_API_KEYS", "")
        keys = []
        if raw_keys:
            parts = [k.strip() for k in raw_keys.split(",") if k.strip()]
            for idx, key in enumerate(parts):
                keys.append((f"key_{idx+1}", key))
        return keys

    def get_configured_keys_count(self) -> int:
        return len(self.keys)

    def is_cache_enabled(self) -> bool:
        return litellm.cache is not None

    def _get_cache_key(self, model: str, messages: List[Dict[str, str]]) -> str:
        """
        Per assignment:
        Cache key: model + the full message list sent to the LLM (system prompt + history + new message).
        """
        data = {
            "model": model,
            "messages": [{"role": m["role"], "content": m["content"]} for m in messages]
        }
        canonical = json.dumps(data, sort_keys=True)
        return "lyftr_cache:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def _get_cached_item(self, cache_key: str) -> Optional[Dict[str, Any]]:
        if not litellm.cache:
            return None
        try:
            if hasattr(litellm.cache, "cache") and hasattr(litellm.cache.cache, "get_cache"):
                return litellm.cache.cache.get_cache(cache_key)
            elif hasattr(litellm.cache, "get_cache"):
                return litellm.cache.get_cache(cache_key)
        except Exception:
            return None
        return None

    def _set_cached_item(self, cache_key: str, value: Dict[str, Any]):
        if not litellm.cache:
            return
        try:
            if hasattr(litellm.cache, "cache") and hasattr(litellm.cache.cache, "set_cache"):
                litellm.cache.cache.set_cache(cache_key, value)
            elif hasattr(litellm.cache, "set_cache"):
                litellm.cache.set_cache(cache_key, value)
        except Exception:
            pass

    def _parse_simulated_failures(self, sim_header: Optional[str]) -> Dict[str, int]:
        if not sim_header or not self.enable_failure_simulation:
            return {}
        
        sim_map = {}
        parts = [p.strip() for p in sim_header.split(",") if p.strip()]
        for p in parts:
            if "=" in p:
                k, v = p.split("=", 1)
                k = k.strip()
                v = v.strip()
                try:
                    sim_map[k] = int(v)
                except ValueError:
                    pass
        return sim_map

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        sim_header: Optional[str] = None
    ) -> Dict[str, Any]:
        start_time = time.time()
        model = self.default_model
        cache_key = self._get_cache_key(model, messages)

        # 1. Check LiteLLM cache first
        cached_data = self._get_cached_item(cache_key)
        if cached_data:
            latency_ms = int((time.time() - start_time) * 1000)
            return {
                "reply": cached_data["reply"],
                "metadata": {
                    "resolution_source": "LLM_CACHE",
                    "model": cached_data.get("model", model),
                    "latency_ms": latency_ms,
                    "input_tokens": cached_data.get("input_tokens", 0),
                    "output_tokens": cached_data.get("output_tokens", 0),
                    "key_id": None,
                    "fallback_attempts": 0
                }
            }

        # 2. Live Inference with Key Failover
        sim_map = self._parse_simulated_failures(sim_header)
        fallback_attempts = 0

        if not self.keys:
            raise RuntimeError("No LLM API keys configured.")

        last_error = None

        for key_id, api_key in self.keys:
            sim_status = None
            if "*" in sim_map:
                sim_status = sim_map["*"]
            elif key_id in sim_map:
                sim_status = sim_map[key_id]

            if sim_status in (429, 500, 502, 503):
                fallback_attempts += 1
                last_error = f"Simulated error {sim_status} on {key_id}"
                continue

            try:
                response = litellm.completion(
                    model=model,
                    messages=messages,
                    api_key=api_key,
                    caching=False
                )

                latency_ms = int((time.time() - start_time) * 1000)
                reply = response.choices[0].message.content or ""
                
                usage = getattr(response, "usage", None)
                input_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
                output_tokens = getattr(usage, "completion_tokens", 0) if usage else 0

                if input_tokens == 0:
                    try:
                        input_tokens = litellm.token_counter(model=model, messages=messages)
                    except Exception:
                        input_tokens = sum(len(m.get("content", "").split()) for m in messages) * 2

                if output_tokens == 0:
                    try:
                        output_tokens = litellm.token_counter(model=model, text=reply)
                    except Exception:
                        output_tokens = len(reply.split()) * 2

                # Store in LiteLLM cache
                self._set_cached_item(
                    cache_key,
                    {
                        "reply": reply,
                        "model": model,
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens
                    }
                )

                return {
                    "reply": reply,
                    "metadata": {
                        "resolution_source": "LIVE_INFERENCE",
                        "model": model,
                        "latency_ms": latency_ms,
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "key_id": key_id,
                        "fallback_attempts": fallback_attempts
                    }
                }

            except Exception as e:
                print(
                    f"LLM failure on {key_id}: {type(e).__name__}: {e}",
                    flush=True
                )
                fallback_attempts += 1
                last_error = e
                continue

        raise AllKeysFailedException(f"All providers unavailable. Last error: {last_error}")

class AllKeysFailedException(Exception):
    pass
