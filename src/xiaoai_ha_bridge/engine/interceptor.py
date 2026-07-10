import logging
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

    def update_config(self, config: AppConfig):
        self.config = config
        self.parser = CommandParser(config.commands)

    async def intercept(self, text: str, source_speaker_entity_id: str = None) -> bool:
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
            await self._execute_command(parsed, source_speaker_entity_id)
            return True
        finally:
            self.processing = False

    def _get_tts_speaker(self, source_entity_id: str = None) -> str:
        if source_entity_id:
            speaker_ids = self.config.get_speaker_entity_ids()
            if source_entity_id in speaker_ids:
                return source_entity_id
        if self.config.xiaomi_speakers:
            return self.config.xiaomi_speakers[0].entity_id
        return ""

    async def _execute_command(self, parsed: Dict[str, Any], source_speaker_entity_id: str = None):
        entity_id = parsed["entity_id"]
        action = parsed["action"]
        temperature = parsed["temperature"]
        mode = parsed["mode"]
        is_query = parsed["query"]
        device_name = parsed["name"]
        device_type = parsed["device_type"]

        tts_speaker = self._get_tts_speaker(source_speaker_entity_id)

        if is_query:
            await self._handle_query(entity_id, device_name, device_type, tts_speaker)
            return

        tts_messages = []

        if device_type == "climate":
            tts_messages = await self._execute_climate(entity_id, action, temperature, mode, device_name)
        elif device_type == "vacuum":
            tts_messages = await self._execute_vacuum(entity_id, action, device_name)
        elif device_type in ("light", "switch", "fan"):
            tts_messages = await self._execute_switch_light(entity_id, action, device_name, device_type)

        if self.config.tts.enabled and tts_messages and tts_speaker:
            await self.ha_client.play_text(
                tts_speaker,
                "，".join(tts_messages)
            )

    async def _execute_climate(self, entity_id: str, action: str, temperature: float, mode: str, device_name: str):
        messages = []

        if action == "turn_on":
            success = await self.ha_client.turn_on_ac(entity_id)
            if success:
                if mode:
                    await self.ha_client.set_ac_mode(entity_id, mode)
                    mode_map = {"cool": "制冷", "heat": "制热", "dry": "除湿", "auto": "自动", "fan_only": "送风"}
                    mode_text = mode_map.get(mode, mode)
                    messages.append(f"{device_name}已打开，{mode_text}模式")
                else:
                    messages.append(f"{device_name}已打开")

        elif action == "turn_off":
            success = await self.ha_client.turn_off_ac(entity_id)
            if success:
                messages.append(f"{device_name}已关闭")

        elif action == "adjust":
            need_turn_on = False
            state = await self.ha_client.get_state(entity_id)
            if state and state.get("state") == "off":
                need_turn_on = True
                await self.ha_client.turn_on_ac(entity_id)

            if temperature is not None:
                success = await self.ha_client.set_ac_temperature(entity_id, temperature)
                if success:
                    msg = f"{device_name}已调至{temperature}度"
                    if mode:
                        await self.ha_client.set_ac_mode(entity_id, mode)
                        mode_map = {"cool": "制冷", "heat": "制热", "dry": "除湿", "auto": "自动", "fan_only": "送风"}
                        mode_text = mode_map.get(mode, mode)
                        msg += f"，{mode_text}模式"
                    messages.append(msg)
            elif mode is not None:
                success = await self.ha_client.set_ac_mode(entity_id, mode)
                if success:
                    mode_map = {"cool": "制冷", "heat": "制热", "dry": "除湿", "auto": "自动", "fan_only": "送风"}
                    mode_text = mode_map.get(mode, mode)
                    messages.append(f"{device_name}已设为{mode_text}模式")

        return messages

    async def _execute_vacuum(self, entity_id: str, action: str, device_name: str):
        messages = []

        if action == "start":
            success = await self.ha_client.vacuum_start(entity_id)
            if success:
                messages.append(f"{device_name}开始清扫")
        elif action == "stop":
            success = await self.ha_client.vacuum_stop(entity_id)
            if success:
                messages.append(f"{device_name}已停止")
        elif action == "pause":
            success = await self.ha_client.vacuum_pause(entity_id)
            if success:
                messages.append(f"{device_name}已暂停")
        elif action == "return_to_base":
            success = await self.ha_client.vacuum_return_to_base(entity_id)
            if success:
                messages.append(f"{device_name}开始回充")

        return messages

    async def _execute_switch_light(self, entity_id: str, action: str, device_name: str, device_type: str):
        messages = []
        domain = device_type

        if action == "turn_on":
            success = await self.ha_client.generic_turn_on(domain, entity_id)
            if success:
                messages.append(f"{device_name}已打开")
        elif action == "turn_off":
            success = await self.ha_client.generic_turn_off(domain, entity_id)
            if success:
                messages.append(f"{device_name}已关闭")

        return messages

    async def _handle_query(self, entity_id: str, device_name: str, device_type: str, tts_speaker: str):
        state = await self.ha_client.get_state(entity_id)
        if not state:
            if self.config.tts.enabled and tts_speaker:
                await self.ha_client.play_text(
                    tts_speaker,
                    f"无法获取{device_name}的状态"
                )
            return

        state_value = state.get("state", "")
        attributes = state.get("attributes", {})

        response_text = self._format_state_response(device_name, device_type, state_value, attributes)

        if self.config.tts.enabled and tts_speaker:
            await self.ha_client.play_text(
                tts_speaker,
                response_text
            )

    def _format_state_response(self, device_name: str, device_type: str, state: str, attributes: Dict[str, Any]) -> str:
        if device_type == "vacuum":
            status_map = {
                "cleaning": "正在清扫",
                "docked": "已回充",
                "idle": "待机中",
                "paused": "已暂停",
                "returning": "正在回充",
                "error": "出错了",
                "off": "已关闭",
            }
            status = status_map.get(state.lower(), state)
            battery = attributes.get("battery_level", "")
            if battery and state.lower() not in ("docked", "charging"):
                return f"{device_name}当前{status}，电量{battery}%"
            return f"{device_name}当前{status}"

        if device_type == "climate":
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
            if state == "off":
                return f"{device_name}当前已关闭"
            if temp:
                return f"{device_name}当前{mode_text}模式，温度{temp}度"
            return f"{device_name}当前{mode_text}模式"

        if device_type in ("light", "switch", "fan"):
            if state == "on":
                return f"{device_name}当前已打开"
            elif state == "off":
                return f"{device_name}当前已关闭"

        return f"{device_name}当前状态: {state}"
