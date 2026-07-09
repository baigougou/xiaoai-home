import logging
import asyncio
from typing import Dict, Any, Optional
from ..config.config import AppConfig
from ..ha_client.client import HomeAssistantClient
from .parser import CommandParser

logger = logging.getLogger(__name__)


class CommandInterceptor:
    def __init__(self, config: AppConfig, ha_client: HomeAssistantClient):
        self.config = config
        self.ha_client = ha_client
        self.parser = CommandParser(config.commands)
        self.last_processed_text = ""
        self.processing = False

    async def intercept(self, text: str) -> bool:
        if not text or text.strip() == "":
            return False

        if text == self.last_processed_text:
            return False

        parsed = self.parser.parse_command(text)
        if not parsed:
            return False

        self.last_processed_text = text
        self.processing = True

        try:
            await self._execute_command(parsed)
            return True
        finally:
            self.processing = False

    async def _execute_command(self, parsed: Dict[str, Any]):
        entity_id = parsed["entity_id"]
        action = parsed["action"]
        temperature = parsed["temperature"]
        mode = parsed["mode"]
        is_query = parsed["query"]
        device_name = parsed["name"]

        if is_query:
            await self._handle_query(entity_id, device_name)
            return

        tts_messages = []

        if action == "turn_on":
            if mode is not None:
                success = await self.ha_client.set_ac_mode(entity_id, mode)
                if success:
                    tts_messages.append(f"{device_name}已打开，{mode}模式")
            else:
                success = await self.ha_client.call_service("climate", "turn_on", entity_id)
                if success:
                    tts_messages.append(f"{device_name}已打开")

        elif action == "turn_off":
            success = await self.ha_client.call_service("climate", "turn_off", entity_id)
            if success:
                tts_messages.append(f"{device_name}已关闭")

        elif action == "adjust" or temperature is not None or mode is not None:
            if temperature is not None:
                success = await self.ha_client.set_ac_temperature(entity_id, temperature)
                if success:
                    msg = f"{device_name}已调至{temperature}度"
                    if mode is not None:
                        msg += f"，{mode}模式"
                    tts_messages.append(msg)
            elif mode is not None:
                success = await self.ha_client.set_ac_mode(entity_id, mode)
                if success:
                    tts_messages.append(f"{device_name}已设为{mode}模式")

        if self.config.tts.enabled and tts_messages:
            await self.ha_client.play_text(
                self.config.xiaomi_speaker.entity_id,
                "，".join(tts_messages)
            )

    async def _handle_query(self, entity_id: str, device_name: str):
        state = await self.ha_client.get_state(entity_id)
        if not state:
            if self.config.tts.enabled:
                await self.ha_client.play_text(
                    self.config.xiaomi_speaker.entity_id,
                    f"无法获取{device_name}的状态"
                )
            return

        state_value = state.get("state", "")
        attributes = state.get("attributes", {})

        response_text = self._format_state_response(device_name, state_value, attributes)

        if self.config.tts.enabled:
            await self.ha_client.play_text(
                self.config.xiaomi_speaker.entity_id,
                response_text
            )

    def _format_state_response(self, device_name: str, state: str, attributes: Dict[str, Any]) -> str:
        if device_name in ["冰箱"]:
            temp = attributes.get("current_temperature", attributes.get("temperature", state))
            return f"{device_name}当前温度{temp}度"

        if device_name in ["洗碗机"]:
            status_map = {
                "running": "运行中",
                "finished": "已完成",
                "idle": "待机中",
                "error": "出错了",
            }
            status = status_map.get(state.lower(), state)
            return f"{device_name}当前{status}"

        if device_name in ["空调", "格力空调", "美的空调"]:
            temp = attributes.get("current_temperature", attributes.get("temperature", ""))
            hvac_mode = attributes.get("hvac_mode", "")
            mode_map = {
                "cool": "制冷",
                "heat": "制热",
                "dry": "除湿",
                "auto": "自动",
                "fan_only": "送风",
                "off": "已关闭",
            }
            mode_text = mode_map.get(hvac_mode, hvac_mode)
            if temp:
                return f"{device_name}当前{mode_text}模式，温度{temp}度"
            return f"{device_name}当前{mode_text}模式"

        return f"{device_name}当前状态: {state}"
