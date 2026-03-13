import json
import logging
from datetime import datetime
from pathlib import Path

from pytz import timezone

TZ_UTC8 = timezone("Asia/Taipei")


class FileRequestLogger:
    def __init__(self, log_dir: Path | None = None):
        if log_dir is None:
            log_dir = Path.home() / ".ollama_router"
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
        messages: list[dict[str, str]],
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
