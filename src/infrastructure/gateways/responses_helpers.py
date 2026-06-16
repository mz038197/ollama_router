from copy import deepcopy
from typing import Any

VALID_REASONING_EFFORTS = frozenset({"none", "minimal", "low", "medium", "high", "xhigh"})


def sanitize_responses_request(body: dict[str, Any], supports_thinking: bool) -> dict[str, Any]:
    """Prepare an Ollama /v1/responses body; strip reasoning when the model cannot think."""
    out = deepcopy(body)

    reasoning = out.get("reasoning")
    if not isinstance(reasoning, dict):
        if not supports_thinking:
            out.pop("reasoning", None)
        return out

    if not supports_thinking:
        out.pop("reasoning", None)
        return out

    effort = reasoning.get("effort")
    if effort is not None and effort not in VALID_REASONING_EFFORTS:
        out.pop("reasoning", None)

    return out


def responses_input_for_log(body: dict[str, Any]) -> list[dict[str, Any]]:
    """Best-effort conversion of Responses `input` to role/content pairs for audit logs."""
    raw_input = body.get("input")
    if isinstance(raw_input, str):
        return [{"role": "user", "content": raw_input}]
    if not isinstance(raw_input, list):
        return []

    messages: list[dict[str, Any]] = []
    for item in raw_input:
        if isinstance(item, str):
            messages.append({"role": "user", "content": item})
            continue
        if not isinstance(item, dict):
            continue

        role = item.get("role")
        if role in ("user", "assistant", "system", "developer"):
            content = item.get("content", "")
            if isinstance(content, list):
                text_parts = []
                for part in content:
                    if isinstance(part, dict) and part.get("type") in ("input_text", "output_text", "text"):
                        text_parts.append(str(part.get("text", "")))
                    elif isinstance(part, str):
                        text_parts.append(part)
                content = "\n".join(text_parts)
            messages.append({"role": role, "content": content if isinstance(content, str) else str(content)})
            continue

        item_type = item.get("type")
        if item_type == "message" and isinstance(item.get("content"), list):
            text_parts = []
            for part in item["content"]:
                if isinstance(part, dict) and part.get("type") in ("input_text", "output_text", "text"):
                    text_parts.append(str(part.get("text", "")))
            messages.append({"role": item.get("role", "assistant"), "content": "\n".join(text_parts)})
        elif item_type == "function_call":
            messages.append(
                {
                    "role": "assistant",
                    "content": f"[function_call] {item.get('name', '')}({item.get('arguments', '')})",
                }
            )
        elif item_type == "function_call_output":
            messages.append({"role": "tool", "content": str(item.get("output", ""))})

    return messages
