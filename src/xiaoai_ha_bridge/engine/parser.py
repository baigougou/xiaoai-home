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
        for cmd_id, cmd_config in self.commands.items():
            for keyword in cmd_config.keywords:
                self.command_cache[keyword] = cmd_id

    def find_matching_command(self, text: str) -> Optional[str]:
        for keyword, cmd_id in self.command_cache.items():
            if keyword in text:
                return cmd_id
        return None

    def parse_command(self, text: str) -> Optional[Dict[str, Any]]:
        cmd_id = self.find_matching_command(text)
        if not cmd_id:
            return None

        cmd_config = self.commands[cmd_id]
        result = {
            "command_id": cmd_id,
            "name": cmd_config.name,
            "entity_id": cmd_config.entity_id,
            "action": None,
            "temperature": None,
            "mode": None,
            "query": False
        }

        has_turn_off = "关闭" in text or "关掉" in text or ("关" in text and "开" not in text)

        temp_match = re.search(r"(\d{1,2})[度℃°]", text)
        if temp_match:
            result["temperature"] = float(temp_match.group(1))

        mode_patterns = [
            (r"制冷", "制冷"),
            (r"制热", "制热"),
            (r"除湿", "除湿"),
            (r"自动", "自动"),
            (r"送风", "送风"),
            (r"风扇", "送风"),
        ]
        for pattern, mode in mode_patterns:
            if pattern in text:
                result["mode"] = mode
                break

        mode_words = ["制冷", "制热", "除湿", "自动", "送风", "风扇"]
        has_mode_only_open = False
        for mode_word in mode_words:
            if f"开{mode_word}" in text:
                has_mode_only_open = True
                break

        has_turn_on = "打开" in text or "开" in text or has_mode_only_open or (result["mode"] is not None and not has_turn_off)

        has_adjust = "调到" in text or "设置" in text or "调至" in text or result["temperature"] is not None or (result["temperature"] is not None and result["mode"] is not None)

        query_patterns = [
            "是多少",
            "多少度",
            "状态",
            "运行",
            "工作",
            "进度",
            "完成",
        ]
        has_query = any(pattern in text for pattern in query_patterns) and not has_turn_on and not has_turn_off and not has_adjust

        if has_query:
            result["query"] = True
        elif has_adjust:
            result["action"] = "adjust"
        elif has_turn_off:
            result["action"] = "turn_off"
        elif has_turn_on:
            result["action"] = "turn_on"

        logger.info(f"解析指令: {text} -> {result}")
        return result

    def parse_temperature(self, text: str) -> Optional[float]:
        temp_match = re.search(r"(\d{1,2})[度℃°]", text)
        if temp_match:
            return float(temp_match.group(1))
        return None

    def parse_mode(self, text: str) -> Optional[str]:
        mode_map = {
            "制冷": "制冷",
            "制热": "制热",
            "除湿": "除湿",
            "自动": "自动",
            "送风": "送风",
            "风扇": "送风",
        }
        for keyword, mode in mode_map.items():
            if keyword in text:
                return mode
        return None

    def is_query_command(self, text: str) -> bool:
        query_patterns = [
            "是多少",
            "多少度",
            "状态",
            "温度",
            "运行",
            "工作",
        ]
        return any(pattern in text for pattern in query_patterns)
