"""API 金鑰驗證與配置管理"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
from pytz import timezone

# UTC+8 時區
TZ_UTC8 = timezone("Asia/Taipei")


class ApiKeyConfig:
    """API 金鑰配置管理"""

    def __init__(self, config_path: Optional[Path] = None):
        if config_path is None:
            config_path = Path.home() / ".ollama_router" / "apikeyConfig.json"

        self.config_path = config_path
        self.config_data = {}
        self._load_or_create_config()

    def _load_or_create_config(self):
        """加載或建立配置檔案"""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self.config_data = json.load(f)
            except Exception as e:
                logging.warning(f"讀取配置檔案失敗: {e}，使用空配置")
                self.config_data = {}
        else:
            # 建立路徑和預設配置
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            self.config_data = {}
            self._save_config()

    def _save_config(self):
        """保存配置到檔案"""
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config_data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            logging.error(f"保存配置檔案失敗: {e}")

    def add_teacher(self, teacher_name: str):
        """添加新教師"""
        if teacher_name not in self.config_data:
            self.config_data[teacher_name] = {"api_keys": []}
            self._save_config()

    def add_api_key(self, teacher_name: str, name: str, key: str, enabled: bool = True):
        """為教師添加 API 金鑰"""
        if teacher_name not in self.config_data:
            self.add_teacher(teacher_name)

        self.config_data[teacher_name]["api_keys"].append(
            {
                "name": name,
                "key": key,
                "enabled": enabled,
            }
        )
        self._save_config()

    def verify_api_key(self, api_key: str) -> tuple[bool, Optional[str]]:
        """
        驗證 API 金鑰
        
        Return: (is_valid, teacher_name)
        """
        if not api_key:
            return False, None

        for teacher_name, teacher_data in self.config_data.items():
            for key_info in teacher_data.get("api_keys", []):
                if key_info["key"] == api_key and key_info.get("enabled", False):
                    return True, teacher_name

        return False, None

    def is_enabled(self) -> bool:
        """檢查是否有任何 API 金鑰配置"""
        return bool(self.config_data)


class RequestLogger:
    """請求日誌記錄器"""

    def __init__(self, log_dir: Optional[Path] = None):
        if log_dir is None:
            log_dir = Path.home() / ".ollama_router"

        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def _get_log_file_path(self) -> Path:
        """根據日期獲取日誌檔案路徑 (UTC+8)"""
        now = datetime.now(TZ_UTC8)
        date_str = now.strftime("%Y%m%d")
        return self.log_dir / f"log_{date_str}.log"

    def log_request(
        self,
        teacher_name: Optional[str],
        api_key: str,
        model: str,
        messages: list,
        is_valid: bool,
        validation_result: str,
    ):
        """記錄請求"""
        try:
            now = datetime.now(TZ_UTC8)
            timestamp = now.strftime("%Y-%m-%d %H:%M:%S")

            # 提取最後一條訊息內容作為摘要
            message_summary = ""
            if messages and len(messages) > 0:
                last_msg = messages[-1]
                if isinstance(last_msg, dict):
                    message_summary = last_msg.get("content", "")[:200]

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

    def log_validation_result(
        self, teacher_name: Optional[str], api_key: str, model: str, messages: list, is_valid: bool
    ):
        """簡化版：記錄驗證結果"""
        validation_result = "通過" if is_valid else "拒絕"
        self.log_request(
            teacher_name=teacher_name,
            api_key=api_key,
            model=model,
            messages=messages,
            is_valid=is_valid,
            validation_result=validation_result,
        )
