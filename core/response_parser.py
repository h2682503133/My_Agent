import json
from core.logger import debug_log, chat_log


def _safe_token_log(self, prompt_tokens, completion_tokens):
    if prompt_tokens is None and completion_tokens is None:
        return
    msg = f"{self.agent_id} [输入]{prompt_tokens}token [输出]{completion_tokens}"
    chat_log(msg)
    debug_log(msg)


def parse_response(self, resp):
    """解析模型响应文本，并统一日志输出。"""
    try:
        data = resp.json()
    except json.JSONDecodeError:
        return resp.text.strip()
    except Exception:
        return getattr(resp, "text", "").strip()

    if not isinstance(data, dict):
        return str(data)

    # OpenAI 风格
    if "choices" in data:
        choice0 = (data.get("choices") or [{}])[0]
        raw_response = choice0.get("message", {}).get("content", "")
        usage = data.get("usage", {})
        _safe_token_log(self, usage.get("prompt_tokens"), usage.get("completion_tokens"))
        return str(raw_response).strip()

    # Ollama / 兼容 API 风格
    if "message" in data:
        raw_response = data.get("message", {}).get("content", "")
        _safe_token_log(self, data.get("prompt_eval_count"), data.get("eval_count"))
        return str(raw_response).strip()

    return str(data).strip()
