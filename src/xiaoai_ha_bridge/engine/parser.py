import re
import logging
from typing import Dict, Any, Optional, Tuple
from ..config.config import CommandConfig

logger = logging.getLogger(__name__)


class CommandParser:
    def __init__(self, commands: Dict[str, CommandConfig]):
        self.commands = commands
        self.command_cache: Dict[str, str] = {}
        self._build_keyword_cache()

    def _build_keyword_cache(self):
        self.command_cache = {}
        for cmd_id, cmd_config in self.commands.items():
            for keyword in cmd_config.keywords:
                self.command_cache[keyword] = cmd_id

    def find_matching_command(self, text: str) -> Optional[str]:
        sorted_keywords = sorted(self.command_cache.keys(), key=len, reverse=True)
        for keyword in sorted_keywords:
            if keyword in text:
                return self.command_cache[keyword]
        return None

    def _parse_climate(self, text: str, result: Dict[str, Any]) -> Dict[str, Any]:
        has_turn_off = "关闭" in text or "关掉" in text or ("关" in text and "开" not in text)

        temp_match = re.search(r"(\d{1,2})[度℃°]", text)
        if temp_match:
            result["temperature"] = float(temp_match.group(1))

        mode_patterns = [
            (r"制冷", "cool"),
            (r"制热", "heat"),
            (r"除湿", "dry"),
            (r"自动", "auto"),
            (r"送风", "fan_only"),
            (r"风扇", "fan_only"),
        ]
        for pattern, mode in mode_patterns:
            if pattern in text:
                result["mode"] = mode
                break

        mode_words = ["制冷", "制热", "除湿", "自动", "送风", "风扇"]
        has_mode_only_open = False
        for mode_word in mode_words:
            if f"开{mode_word}" in text or mode_word in text and "关" not in text:
                has_mode_only_open = True
                break

        has_turn_on = "打开" in text or "开" in text or has_mode_only_open or (result["mode"] is not None and not has_turn_off)

        has_adjust = "调到" in text or "设置" in text or "调至" in text or result["temperature"] is not None

        query_patterns = [
            "是多少",
            "多少度",
            "状态",
            "运行",
            "工作",
            "温度",
        ]
        has_query = any(pattern in text for pattern in query_patterns) and not has_turn_on and not has_turn_off and not has_adjust

        fan_patterns = [
            (r"自动风", "auto"),
            (r"低速风|小风|低风", "low"),
            (r"中速风|中风|中速", "medium"),
            (r"高速风|大风|高风|强风", "high"),
        ]
        for pattern, fan_mode in fan_patterns:
            if pattern in text:
                result["fan_mode"] = fan_mode
                has_adjust = True
                break

        if has_query:
            result["query"] = True
            result["action"] = "query"
        elif has_adjust:
            result["action"] = "adjust"
        elif has_turn_off:
            result["action"] = "turn_off"
        elif has_turn_on:
            result["action"] = "turn_on"

        return result

    def _parse_vacuum(self, text: str, result: Dict[str, Any]) -> Dict[str, Any]:
        has_turn_off = any(kw in text for kw in ["关闭", "关掉", "停止", "暂停", "回去", "回充", "回去充电", "回去充电"])

        start_keywords = ["开始", "启动", "开始打扫", "开始清扫", "清扫", "打扫", "扫地", "清洁", "清理"]
        has_turn_on = any(kw in text for kw in start_keywords)

        return_home_keywords = ["回去", "回充", "回去充电", "回去充电", "回家", "回基站"]
        has_return_home = any(kw in text for kw in return_home_keywords)

        pause_keywords = ["暂停", "停一下", "先停"]
        has_pause = any(kw in text for kw in pause_keywords)

        query_patterns = ["状态", "在哪", "在哪里", "工作", "电量", "多少电"]
        has_query = any(pattern in text for pattern in query_patterns) and not has_turn_on and not has_turn_off

        if has_query:
            result["query"] = True
            result["action"] = "query"
        elif has_return_home:
            result["action"] = "return_to_base"
        elif has_pause:
            result["action"] = "pause"
        elif has_turn_off:
            result["action"] = "stop"
        elif has_turn_on:
            result["action"] = "start"
        else:
            result["action"] = "start"

        return result

    def _parse_switch_light(self, text: str, result: Dict[str, Any]) -> Dict[str, Any]:
        has_turn_off = any(kw in text for kw in ["关闭", "关掉", "关"]) and "开" not in text
        has_turn_on = any(kw in text for kw in ["打开", "开"]) or (not has_turn_off)

        query_patterns = ["状态", "开了吗", "关了吗", "是否打开"]
        has_query = any(pattern in text for pattern in query_patterns) and not has_turn_on and not has_turn_off

        if has_query:
            result["query"] = True
            result["action"] = "query"
        elif has_turn_off:
            result["action"] = "turn_off"
        elif has_turn_on:
            result["action"] = "turn_on"

        return result

    def parse_command(self, text: str) -> Optional[Dict[str, Any]]:
        cmd_id = self.find_matching_command(text)
        if not cmd_id:
            return None

        cmd_config = self.commands[cmd_id]
        device_type = getattr(cmd_config, 'device_type', 'climate')

        result = {
            "command_id": cmd_id,
            "name": cmd_config.name,
            "entity_id": cmd_config.entity_id,
            "device_type": device_type,
            "action": None,
            "temperature": None,
            "mode": None,
            "fan_mode": None,
            "query": False
        }

        if device_type == "climate":
            result = self._parse_climate(text, result)
        elif device_type == "vacuum":
            result = self._parse_vacuum(text, result)
        elif device_type in ("light", "switch", "fan"):
            result = self._parse_switch_light(text, result)
        else:
            result = self._parse_switch_light(text, result)

        logger.info(f"解析指令: {text} -> {result}")
        return result
