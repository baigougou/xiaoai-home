import pytest
from src.xiaoai_ha_bridge.engine.parser import CommandParser
from src.xiaoai_ha_bridge.config.config import CommandConfig


def create_test_commands():
    return {
        "gree_ac": CommandConfig(
            name="格力空调",
            entity_id="climate.gree_air_conditioner",
            keywords=["格力空调", "主卧空调"]
        ),
        "midea_ac": CommandConfig(
            name="美的空调",
            entity_id="climate.midea_air_conditioner",
            keywords=["美的空调", "客厅空调"]
        ),
        "refrigerator": CommandConfig(
            name="冰箱",
            entity_id="sensor.refrigerator_temperature",
            keywords=["冰箱"]
        ),
        "dishwasher": CommandConfig(
            name="洗碗机",
            entity_id="sensor.dishwasher_status",
            keywords=["洗碗机"]
        )
    }


class TestCommandParser:
    def test_parse_turn_on(self):
        parser = CommandParser(create_test_commands())
        parsed = parser.parse_command("打开格力空调")
        assert parsed is not None
        assert parsed["action"] == "turn_on"
        assert parsed["name"] == "格力空调"
        assert parsed["entity_id"] == "climate.gree_air_conditioner"

    def test_parse_turn_off(self):
        parser = CommandParser(create_test_commands())
        parsed = parser.parse_command("关闭美的空调")
        assert parsed is not None
        assert parsed["action"] == "turn_off"
        assert parsed["name"] == "美的空调"

    def test_parse_temperature(self):
        parser = CommandParser(create_test_commands())
        parsed = parser.parse_command("格力空调调到25度")
        assert parsed is not None
        assert parsed["temperature"] == 25.0
        assert parsed["action"] == "adjust"

    def test_parse_mode(self):
        parser = CommandParser(create_test_commands())
        parsed = parser.parse_command("美的空调开制热模式")
        assert parsed is not None
        assert parsed["mode"] == "制热"
        assert parsed["action"] == "turn_on"

    def test_parse_query(self):
        parser = CommandParser(create_test_commands())
        parsed = parser.parse_command("冰箱温度是多少")
        assert parsed is not None
        assert parsed["query"] is True
        assert parsed["name"] == "冰箱"

    def test_parse_complex_command(self):
        parser = CommandParser(create_test_commands())
        parsed = parser.parse_command("格力空调调到26度开制冷")
        assert parsed is not None
        assert parsed["temperature"] == 26.0
        assert parsed["mode"] == "制冷"

    def test_no_match(self):
        parser = CommandParser(create_test_commands())
        parsed = parser.parse_command("打开电视")
        assert parsed is None

    def test_keyword_match(self):
        parser = CommandParser(create_test_commands())
        parsed = parser.parse_command("主卧空调打开")
        assert parsed is not None
        assert parsed["name"] == "格力空调"

    def test_parse_mode_only(self):
        parser = CommandParser(create_test_commands())
        parsed = parser.parse_command("格力空调开除湿")
        assert parsed is not None
        assert parsed["mode"] == "除湿"
        assert parsed["action"] == "turn_on"
