import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from pytz import timezone

TZ_UTC8 = timezone("Asia/Taipei")


class FileRequestLogger:
    def __init__(self, log_dir: Path | None = None):
        if log_dir is None:
            log_dir = Path.home() / ".ollama_router" / "logs"
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def _get_log_file_path(self) -> Path:
        now = datetime.now(TZ_UTC8)
        date_str = now.strftime("%Y%m%d")
        return self.log_dir / f"log_{date_str}.log"

    def log_validation_result(
        self,
        teacher_name: str | None,
        api_key: str,
        model: str,
        messages: list[dict[str, Any]],
        is_valid: bool,
    ) -> None:
        validation_result = "通過" if is_valid else "拒絕"
        try:
            now = datetime.now(TZ_UTC8)
            timestamp = now.strftime("%Y-%m-%d %H:%M:%S")

            message_summary = ""
            if messages:
                last_msg = messages[-1]
                message_summary = (last_msg.get("content", "") or "")[:200]

            log_entry = {
                "timestamp": timestamp,
                "teacher": teacher_name or "未知",
                "api_key": api_key[:20] + "..." if len(api_key) > 20 else api_key,
                "model": model,
                "is_valid": is_valid,
                "validation_result": validation_result,
                "message_preview": message_summary,
            }

            log_file = self._get_log_file_path()
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logging.error(f"記錄請求失敗: {e}")

    def query_logs(
        self,
        date: str | None = None,
        teacher: str | None = None,
        model: str | None = None,
        is_valid: bool | None = None,
        keyword: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        target_date = date or datetime.now(TZ_UTC8).strftime("%Y%m%d")
        log_file = self.log_dir / f"log_{target_date}.log"
        if not log_file.exists():
            return {"items": [], "total": 0, "has_more": False}

        teacher_filter = teacher.strip() if teacher else None
        model_filter = model.strip() if model else None
        keyword_filter = keyword.strip().lower() if keyword else None

        matched: list[dict[str, Any]] = []
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                for raw_line in f:
                    line = raw_line.strip()
                    if not line:
                        continue
                    try:
                        item = json.loads(line)
                    except json.JSONDecodeError:
                        # 跳過損壞的行，避免整體查詢失敗
                        continue

                    if teacher_filter and item.get("teacher") != teacher_filter:
                        continue
                    if model_filter and item.get("model") != model_filter:
                        continue
                    if is_valid is not None and bool(item.get("is_valid")) is not is_valid:
                        continue
                    if keyword_filter:
                        preview = str(item.get("message_preview", "")).lower()
                        if keyword_filter not in preview:
                            continue

                    matched.append(item)
        except Exception as e:
            logging.error(f"讀取請求記錄失敗: {e}")
            return {"items": [], "total": 0, "has_more": False}

        matched.reverse()
        total = len(matched)
        start = max(offset, 0)
        end = start + max(limit, 1)
        items = matched[start:end]
        return {"items": items, "total": total, "has_more": end < total}
