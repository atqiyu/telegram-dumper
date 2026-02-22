"""
配置管理模块
提供配置加载、保存和环境变量读取功能
"""
import os
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Config:
    """Telegram Dumper 配置类"""
    api_id: int = 0                       # Telegram API ID
    api_hash: str = ""                     # Telegram API Hash
    session_name: str = "telegram_dumper" # 会话名称
    output_dir: str = "output"             # 输出目录
    download_concurrency: int = 8          # 下载并发数
    progress_update_interval: float = 0.5  # 进度更新间隔(秒)
    
    @classmethod
    def load_from_file(cls, path: str = "config.yaml") -> "Config":
        """从 YAML 文件加载配置"""
        config_path = Path(path)
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            return cls(**{k: v for k, v in data.items() if hasattr(cls, k)})
        return cls()
    
    def save_to_file(self, path: str = "config.yaml"):
        """保存配置到 YAML 文件"""
        data = {
            "api_id": self.api_id,
            "api_hash": self.api_hash,
            "session_name": self.session_name,
            "output_dir": self.output_dir,
            "download_concurrency": self.download_concurrency,
            "progress_update_interval": self.progress_update_interval,
        }
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True)


def load_env_config() -> Config:
    """从环境变量加载配置"""
    config = Config()
    config.api_id = int(os.getenv("TG_API_ID", 0))
    config.api_hash = os.getenv("TG_API_HASH", "")
    config.session_name = os.getenv("TG_SESSION_NAME", "telegram_dumper")
    config.output_dir = os.getenv("TG_OUTPUT_DIR", "output")
    return config
