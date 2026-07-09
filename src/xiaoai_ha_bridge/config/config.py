import json
import os
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class HomeAssistantConfig(BaseModel):
    url: str = Field(..., description="Home Assistant URL")
    api_token: str = Field(..., description="Long-lived access token")


class XiaomiSpeakerConfig(BaseModel):
    entity_id: str = Field(..., description="小爱音箱实体ID")
    execute_text_service: str = Field(default="xiaomi_miot_raw.execute_text", description="执行文本指令服务")
    play_text_service: str = Field(default="xiaomi_miot_raw.play_text", description="播放文本服务")


class BridgeConfig(BaseModel):
    host: str = Field(default="0.0.0.0", description="服务监听地址")
    port: int = Field(default=8000, description="服务监听端口")
    debug: bool = Field(default=False, description="调试模式")
    log_level: str = Field(default="INFO", description="日志级别")
    polling_interval: int = Field(default=3, description="轮询间隔（秒）")


class CommandConfig(BaseModel):
    name: str = Field(..., description="设备名称")
    entity_id: str = Field(..., description="Home Assistant实体ID")
    keywords: list = Field(..., description="触发关键词列表")


class TTSConfig(BaseModel):
    enabled: bool = Field(default=True, description="是否启用TTS")
    volume: int = Field(default=50, description="音量（0-100）")


class AppConfig(BaseModel):
    home_assistant: HomeAssistantConfig
    xiaomi_speaker: XiaomiSpeakerConfig
    bridge: BridgeConfig
    commands: Dict[str, CommandConfig]
    tts: TTSConfig = Field(default_factory=TTSConfig)


class ConfigManager:
    def __init__(self, config_path: str = "config/config.json"):
        self.config_path = config_path
        self.config: Optional[AppConfig] = None

    def load(self) -> AppConfig:
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")

        with open(self.config_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.config = AppConfig(**data)
        return self.config

    def save(self, config: AppConfig):
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(config.dict(), f, ensure_ascii=False, indent=2)

    def reload(self) -> AppConfig:
        return self.load()
