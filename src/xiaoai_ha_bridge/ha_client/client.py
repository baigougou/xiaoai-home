import httpx
import logging
from typing import Dict, Any, Optional, List
from ..config.config import HomeAssistantConfig

logger = logging.getLogger(__name__)


class HomeAssistantClient:
    def __init__(self, config: HomeAssistantConfig):
        self.url = config.url.rstrip("/")
        self.api_token = config.api_token
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        await self.client.aclose()

    async def get_state(self, entity_id: str) -> Optional[Dict[str, Any]]:
        try:
            response = await self.client.get(
                f"{self.url}/api/states/{entity_id}",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"获取实体状态失败 {entity_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"获取实体状态异常 {entity_id}: {e}")
            return None

    async def call_service(self, domain: str, service: str, entity_id: str, data: Dict[str, Any] = None) -> bool:
        try:
            payload = {
                "entity_id": entity_id
            }
            if data:
                payload.update(data)

            response = await self.client.post(
                f"{self.url}/api/services/{domain}/{service}",
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()
            logger.info(f"调用服务成功 {domain}.{service} - {entity_id}")
            return True
        except httpx.HTTPStatusError as e:
            logger.error(f"调用服务失败 {domain}.{service} - {entity_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"调用服务异常 {domain}.{service} - {entity_id}: {e}")
            return False

    async def turn_on_ac(self, entity_id: str) -> bool:
        return await self.call_service("climate", "turn_on", entity_id)

    async def turn_off_ac(self, entity_id: str) -> bool:
        return await self.call_service("climate", "turn_off", entity_id)

    async def set_ac_temperature(self, entity_id: str, temperature: float) -> bool:
        return await self.call_service("climate", "set_temperature", entity_id, {"temperature": temperature})

    async def set_ac_mode(self, entity_id: str, mode: str) -> bool:
        mode_map = {
            "制冷": "cool",
            "制热": "heat",
            "除湿": "dry",
            "自动": "auto",
            "送风": "fan_only"
        }
        hvac_mode = mode_map.get(mode, "auto")
        return await self.call_service("climate", "set_hvac_mode", entity_id, {"hvac_mode": hvac_mode})

    async def execute_text(self, entity_id: str, text: str) -> bool:
        return await self.call_service("xiaomi_miot_raw", "execute_text", entity_id, {"text": text})

    async def play_text(self, entity_id: str, text: str) -> bool:
        return await self.call_service("xiaomi_miot_raw", "play_text", entity_id, {"text": text})

    async def get_all_states(self) -> List[Dict[str, Any]]:
        try:
            response = await self.client.get(
                f"{self.url}/api/states",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"获取实体列表失败: {e}")
            return []

    async def get_entities_by_domain(self, domain: str) -> List[Dict[str, Any]]:
        entities = await self.get_all_states()
        return [
            e for e in entities
            if e.get("entity_id", "").startswith(f"{domain}.")
        ]

    async def discover_entities(self) -> Dict[str, List[Dict[str, Any]]]:
        entities = await self.get_all_states()

        categories = {
            "climate": [],
            "media_player": [],
            "sensor": [],
            "switch": [],
            "light": [],
            "fan": [],
        }

        for entity in entities:
            entity_id = entity.get("entity_id", "")
            attributes = entity.get("attributes", {})
            friendly_name = attributes.get("friendly_name", entity_id)

            entity_info = {
                "entity_id": entity_id,
                "name": friendly_name,
                "state": entity.get("state", ""),
                "domain": entity_id.split(".")[0] if "." in entity_id else "",
            }

            domain = entity_info["domain"]
            if domain in categories:
                categories[domain].append(entity_info)
            else:
                if "other" not in categories:
                    categories["other"] = []
                categories["other"].append(entity_info)

        return categories

    async def test_connection(self) -> bool:
        try:
            response = await self.client.get(
                f"{self.url}/api/",
                headers=self.headers
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"连接测试失败: {e}")
            return False
