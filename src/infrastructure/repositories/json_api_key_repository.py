import json
import logging
from pathlib import Path
from typing import Any


class JsonApiKeyRepository:
    def __init__(self, config_path: Path | None = None):
        if config_path is None:
            config_path = Path.home() / ".ollama_router" / "apikeyConfig.json"

        self.config_path = config_path
        self.config_data: dict[str, Any] = {}
        self._last_mtime: float = 0.0
        self._load_or_create_config()

    def _load_or_create_config(self) -> None:
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self.config_data = json.load(f)
                self._last_mtime = self.config_path.stat().st_mtime
            except Exception as e:
                logging.warning(f"讀取配置檔案失敗: {e}，使用空配置")
                self.config_data = {}
        else:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            self.config_data = {}
            self._save_config()

    def _reload_if_changed(self) -> None:
        try:
            if not self.config_path.exists():
                return
            current_mtime = self.config_path.stat().st_mtime
            if current_mtime != self._last_mtime:
                logging.info("偵測到配置檔案已變更，重新載入...")
                self._load_or_create_config()
        except Exception as e:
            logging.warning(f"檢查配置檔案變更失敗: {e}")

    def _save_config(self) -> None:
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config_data, f, ensure_ascii=False, indent=4)
            self._last_mtime = self.config_path.stat().st_mtime
        except Exception as e:
            logging.error(f"保存配置檔案失敗: {e}")

    def get_all_config(self) -> dict[str, Any]:
        self._reload_if_changed()
        return self.config_data

    def add_teacher(self, teacher_name: str) -> None:
        if teacher_name not in self.config_data:
            self.config_data[teacher_name] = {"api_keys": []}
            self._save_config()

    def delete_teacher(self, teacher_name: str) -> bool:
        if teacher_name not in self.config_data:
            return False
        del self.config_data[teacher_name]
        self._save_config()
        return True

    def add_api_key(self, teacher_name: str, name: str, key: str, enabled: bool = True) -> None:
        if teacher_name not in self.config_data:
            self.add_teacher(teacher_name)
        self.config_data[teacher_name]["api_keys"].append(
            {"name": name, "key": key, "enabled": enabled}
        )
        self._save_config()

    def update_api_key(
        self,
        teacher_name: str,
        old_key: str,
        name: str,
        key: str,
        enabled: bool,
    ) -> bool:
        if teacher_name not in self.config_data:
            return False
        api_keys = self.config_data[teacher_name].get("api_keys", [])
        for key_info in api_keys:
            if key_info["key"] == old_key:
                key_info["name"] = name
                key_info["key"] = key
                key_info["enabled"] = enabled
                self._save_config()
                return True
        return False

    def update_api_key_status(self, teacher_name: str, key: str, enabled: bool) -> bool:
        if teacher_name not in self.config_data:
            return False
        for key_info in self.config_data[teacher_name].get("api_keys", []):
            if key_info["key"] == key:
                key_info["enabled"] = enabled
                self._save_config()
                return True
        return False

    def delete_api_key(self, teacher_name: str, key: str) -> bool:
        if teacher_name not in self.config_data:
            return False
        api_keys = self.config_data[teacher_name].get("api_keys", [])
        for i, key_info in enumerate(api_keys):
            if key_info["key"] == key:
                api_keys.pop(i)
                self._save_config()
                return True
        return False

    def verify_api_key(self, api_key: str) -> tuple[bool, str | None]:
        self._reload_if_changed()
        if not api_key:
            return False, None
        for teacher_name, teacher_data in self.config_data.items():
            for key_info in teacher_data.get("api_keys", []):
                if key_info["key"] == api_key and key_info.get("enabled", False):
                    return True, teacher_name
        return False, None

    def is_enabled(self) -> bool:
        self._reload_if_changed()
        return bool(self.config_data)
