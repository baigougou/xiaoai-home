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

    async def execute_text(self, entity_id: str, text: str, service: str = None) -> bool:
        """执行文本指令，支持自定义服务名"""
        if service and "." in service:
            domain, svc = service.split(".", 1)
            return await self.call_service(domain, svc, entity_id, {"text": text})
        return await self.call_service("xiaomi_miot_raw", "execute_text", entity_id, {"text": text})

    async def send_command_to_speaker(self, entity_id: str, text: str) -> bool:
        """直接发送指令给小爱音箱执行（绕过小爱自身的指令处理）"""
        logger.info(f"直接发送指令给音箱 {entity_id}: {text}")
        return await self.execute_text(entity_id, text)

    async def play_text(self, entity_id: str, text: str, service: str = None) -> bool:
        """播放TTS文本，支持自定义服务名"""
        if service and "." in service:
            domain, svc = service.split(".", 1)
            return await self.call_service(domain, svc, entity_id, {"text": text})
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

    async def vacuum_start(self, entity_id: str) -> bool:
        return await self.call_service("vacuum", "start", entity_id)

    async def vacuum_stop(self, entity_id: str) -> bool:
        return await self.call_service("vacuum", "stop", entity_id)

    async def vacuum_pause(self, entity_id: str) -> bool:
        return await self.call_service("vacuum", "pause", entity_id)

    async def vacuum_return_to_base(self, entity_id: str) -> bool:
        return await self.call_service("vacuum", "return_to_base", entity_id)

    async def vacuum_clean_segment(self, entity_id: str, segment_ids: List[int], repeats: int = 1, clean_mode: str = "sweep_and_mop") -> bool:
        clean_mode_map = {
            "sweep": 0,
            "sweep_and_mop": 1,
            "mop": 2,
        }
        mop_mode = clean_mode_map.get(clean_mode, 1)
        params = [{"segments": segment_ids, "repeat": repeats, "clean_mode": mop_mode}]
        return await self.call_service("vacuum", "send_command", entity_id, {
            "command": "app_segment_clean",
            "params": params
        })

    async def get_vacuum_rooms(self, entity_id: str) -> List[Dict[str, Any]]:
        rooms = []
        seen_ids = set()
        
        state = await self.get_state(entity_id)
        if state:
            attributes = state.get("attributes", {})
            
            for key in ["rooms", "segments", "room_list", "segment_list"]:
                if key in attributes and isinstance(attributes[key], (list, dict)):
                    data = attributes[key]
                    if isinstance(data, dict):
                        for map_name, map_rooms in data.items():
                            if isinstance(map_rooms, list):
                                for item in map_rooms:
                                    if isinstance(item, dict):
                                        room_id = item.get("id") or item.get("segment_id") or item.get("uid")
                                        room_name = item.get("name") or item.get("room_name") or f"区域{room_id}"
                                        if room_id is not None and int(room_id) not in seen_ids:
                                            seen_ids.add(int(room_id))
                                            rooms.append({"id": int(room_id), "name": str(room_name), "map": map_name})
                            elif isinstance(map_rooms, dict):
                                for rid, rname in map_rooms.items():
                                    try:
                                        rid_int = int(rid)
                                        if rid_int not in seen_ids:
                                            seen_ids.add(rid_int)
                                            if isinstance(rname, str):
                                                rooms.append({"id": rid_int, "name": str(rname), "map": map_name})
                                            elif isinstance(rname, dict):
                                                rn = rname.get("name", f"区域{rid}")
                                                rooms.append({"id": rid_int, "name": str(rn), "map": map_name})
                                    except (ValueError, TypeError):
                                        pass
                    elif isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict):
                                room_id = item.get("id") or item.get("segment_id") or item.get("uid")
                                room_name = item.get("name") or item.get("room_name") or f"区域{room_id}"
                                if room_id is not None and int(room_id) not in seen_ids:
                                    seen_ids.add(int(room_id))
                                    rooms.append({"id": int(room_id), "name": str(room_name)})
                            elif isinstance(item, (int, str)):
                                try:
                                    rid_int = int(item)
                                    if rid_int not in seen_ids:
                                        seen_ids.add(rid_int)
                                        rooms.append({"id": rid_int, "name": f"区域{item}"})
                                except (ValueError, TypeError):
                                    pass
                    break
        
        return rooms

    async def discover_notify_services(self) -> List[Dict[str, str]]:
        try:
            services_resp = await self.client.get(f"{self.url}/api/services", headers=self.headers)
            if services_resp.status_code == 200:
                services = services_resp.json()
                notify_services = []
                for domain_data in services:
                    domain = domain_data.get("domain", "")
                    if domain == "notify":
                        services_dict = domain_data.get("services", {})
                        if isinstance(services_dict, dict):
                            for service_name in services_dict.keys():
                                service_id = f"notify.{service_name}"
                                if service_name.startswith("mobile_app_"):
                                    friendly_name = "📱 " + service_name.replace("mobile_app_", "").replace("_", " ").title()
                                else:
                                    friendly_name = service_name.replace("_", " ").title()
                                notify_services.append({"id": service_id, "name": friendly_name})
                logger.info(f"发现 {len(notify_services)} 个通知服务")
                return notify_services
            return []
        except Exception as e:
            logger.error(f"获取通知服务列表失败: {e}")
            import traceback
            traceback.print_exc()
            return []

    async def send_notification(self, notify_service: str, title: str, message: str) -> bool:
        if not notify_service or not notify_service.startswith("notify."):
            return False
        try:
            parts = notify_service.split(".", 1)
            domain = parts[0]
            service = parts[1]
            payload = {
                "title": title,
                "message": message
            }
            response = await self.client.post(
                f"{self.url}/api/services/{domain}/{service}",
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()
            logger.info(f"通知发送成功 {notify_service}")
            return True
        except httpx.HTTPStatusError as e:
            logger.error(f"发送通知失败 {notify_service}: {e.response.status_code} - {e.response.text}")
            return False
        except Exception as e:
            logger.error(f"发送通知异常 {notify_service}: {e}")
            return False

    async def send_notifications(self, notify_services: List[str], title: str, message: str) -> Dict[str, bool]:
        results = {}
        for service in notify_services:
            if service and service.startswith("notify."):
                results[service] = await self.send_notification(service, title, message)
        return results

    async def generic_turn_on(self, domain: str, entity_id: str) -> bool:
        return await self.call_service(domain, "turn_on", entity_id)

    async def generic_turn_off(self, domain: str, entity_id: str) -> bool:
        return await self.call_service(domain, "turn_off", entity_id)

    async def discover_entities(self) -> Dict[str, Any]:
        entities = await self.get_all_states()
        areas_map = await self.get_areas()

        categories = {
            "climate": [],
            "vacuum": [],
            "media_player": [],
            "sensor": [],
            "switch": [],
            "light": [],
            "fan": [],
            "washing_machine": [],
            "dryer": [],
            "stove": [],
            "range_hood": [],
            "bathroom_heater": [],
            "smart_socket": [],
            "notify": [],
            "cover": [],
            "humidifier": [],
            "refrigerator": [],
            "dishwasher": [],
            "water_heater": [],
            "air_purifier": [],
            "other": [],
        }

        for entity in entities:
            entity_id = entity.get("entity_id", "")
            attributes = entity.get("attributes", {})
            friendly_name = attributes.get("friendly_name", entity_id)
            state = entity.get("state", "")
            
            tags = []
            label_key = None
            for key in ["label", "labels", "device_class", "icon", "category", "tags", "device_label", "device_label_list"]:
                if key in attributes:
                    label_key = key
                    value = attributes[key]
                    if isinstance(value, list):
                        tags = [str(v) for v in value if v]
                    elif isinstance(value, dict):
                        tags = [str(k) for k in value.keys() if k]
                    else:
                        tags = [str(value)]
                    break
            
            area_id = None
            for key in ["area_id", "area", "location"]:
                if key in attributes:
                    area_id = str(attributes[key])
                    break
            if not area_id:
                device_id = attributes.get("device_id", "")
                if device_id:
                    try:
                        device_resp = await self.client.get(
                            f"{self.url}/api/config/devices/{device_id}",
                            headers=self.headers
                        )
                        if device_resp.status_code == 200:
                            device = device_resp.json()
                            area_id = device.get("area_id", "")
                    except:
                        pass
            
            area_info = None
            if area_id and area_id in areas_map:
                area_info = areas_map[area_id]
            
            entity_info = {
                "entity_id": entity_id,
                "name": friendly_name,
                "state": state,
                "domain": entity_id.split(".")[0] if "." in entity_id else "",
                "tags": tags,
                "area_id": area_id,
                "area_name": area_info.get("name", "") if area_info else "",
                "area_aliases": area_info.get("aliases", []) if area_info else [],
                "attributes": {k: v for k, v in attributes.items() if isinstance(v, (str, int, float, bool))},
            }

            domain = entity_info["domain"]
            name_lower = friendly_name.lower() if friendly_name else ""
            entity_lower = entity_id.lower()
            
            category = "other"
            
            if domain == "climate":
                category = "climate"
            elif domain == "vacuum":
                category = "vacuum"
            elif domain == "media_player":
                category = "media_player"
            elif domain == "sensor":
                category = "sensor"
            elif domain == "light":
                category = "light"
            elif domain == "fan":
                category = "fan"
            elif domain == "cover":
                category = "cover"
            elif domain == "notify":
                category = "notify"
            elif domain == "switch":
                washing_machine_keywords = ["洗衣机", "washing_machine", "washer"]
                dryer_keywords = ["烘干机", "干衣机", "dryer"]
                stove_keywords = ["灶台", "燃气灶", "煤气灶", "stove", "gas"]
                range_hood_keywords = ["抽油烟机", "油烟机", "range_hood", "hood"]
                bathroom_heater_keywords = ["浴霸"]
                smart_socket_keywords = ["插座", "smart_plug", "smart_socket"]
                humidifier_keywords = ["加湿器", "humidifier"]
                refrigerator_keywords = ["冰箱", "refrigerator", "fridge"]
                dishwasher_keywords = ["洗碗机", "dishwasher"]
                water_heater_keywords = ["热水器", "water_heater", "heater"]
                air_purifier_keywords = ["空气净化器", "净化器", "air_purifier", "purifier"]
                
                if any(kw in name_lower for kw in washing_machine_keywords):
                    category = "washing_machine"
                elif any(kw in name_lower for kw in dryer_keywords):
                    category = "dryer"
                elif any(kw in name_lower for kw in stove_keywords):
                    category = "stove"
                elif any(kw in name_lower for kw in range_hood_keywords):
                    category = "range_hood"
                elif any(kw in name_lower for kw in bathroom_heater_keywords):
                    category = "bathroom_heater"
                elif any(kw in name_lower for kw in smart_socket_keywords):
                    category = "smart_socket"
                elif any(kw in name_lower for kw in humidifier_keywords):
                    category = "humidifier"
                elif any(kw in name_lower for kw in refrigerator_keywords):
                    category = "refrigerator"
                elif any(kw in name_lower for kw in dishwasher_keywords):
                    category = "dishwasher"
                elif any(kw in name_lower for kw in water_heater_keywords):
                    category = "water_heater"
                elif any(kw in name_lower for kw in air_purifier_keywords):
                    category = "air_purifier"
                else:
                    category = "switch"
            elif domain == "humidifier":
                category = "humidifier"
            else:
                category = "other"

            categories[category].append(entity_info)

        return {
            "entities": categories,
            "areas": areas_map
        }

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

    async def get_areas(self) -> Dict[str, Dict[str, Any]]:
        try:
            response = await self.client.get(
                f"{self.url}/api/areas",
                headers=self.headers
            )
            response.raise_for_status()
            areas_data = response.json()
            areas_map = {}
            for area in areas_data:
                area_id = area.get("area_id", "")
                if area_id:
                    areas_map[area_id] = {
                        "name": area.get("name", area_id),
                        "icon": area.get("icon", ""),
                        "aliases": area.get("aliases", []),
                        "id": area_id
                    }
            return areas_map
        except Exception as e:
            logger.error(f"获取区域信息失败: {e}")
            return {}

    async def get_area_by_entity(self, entity_id: str) -> Optional[str]:
        try:
            response = await self.client.get(
                f"{self.url}/api/states/{entity_id}",
                headers=self.headers
            )
            if response.status_code == 200:
                state = response.json()
                attributes = state.get("attributes", {})
                for key in ["area_id", "area", "location"]:
                    if key in attributes:
                        return str(attributes[key])
                device_id = attributes.get("device_id", "")
                if device_id:
                    device_resp = await self.client.get(
                        f"{self.url}/api/config/devices/{device_id}",
                        headers=self.headers
                    )
                    if device_resp.status_code == 200:
                        device = device_resp.json()
                        area_id = device.get("area_id", "")
                        if area_id:
                            return area_id
            return None
        except Exception as e:
            logger.debug(f"获取实体区域信息失败 {entity_id}: {e}")
            return None

    async def discover_speakers(self) -> List[Dict[str, Any]]:
        entities = await self.get_all_states()
        speakers = []
        seen_device_ids = set()
        
        conversation_patterns = [
            "xiaomi_lx06",
            "conversation",
            "xiaoai",
            "miot_speaker",
            "xiaomi_speaker",
        ]
        
        media_player_patterns = [
            "xiaomi",
            "xiaoai",
            "lx06",
            "miot",
            "speaker",
            "小爱",
        ]
        
        for entity in entities:
            entity_id = entity.get("entity_id", "")
            attributes = entity.get("attributes", {})
            friendly_name = attributes.get("friendly_name", entity_id)
            domain = entity_id.split(".")[0] if "." in entity_id else ""
            device_id = attributes.get("device_id", "")
            
            is_conversation = (
                domain == "sensor" and
                any(pattern.lower() in entity_id.lower() for pattern in conversation_patterns)
            )
            
            is_media_player = (
                domain == "media_player" and
                any(pattern.lower() in entity_id.lower() for pattern in media_player_patterns)
            )
            
            if is_conversation or is_media_player:
                if device_id and device_id in seen_device_ids:
                    continue
                if device_id:
                    seen_device_ids.add(device_id)
                
                speaker_type = "conversation" if is_conversation else "media_player"
                entity_lower = entity_id.lower()
                is_xiaomi = any(p in entity_lower for p in ["xiaomi", "xiaoai", "lx06", "miot", "小爱"])
                
                speakers.append({
                    "entity_id": entity_id,
                    "name": friendly_name,
                    "type": speaker_type,
                    "domain": domain,
                    "is_xiaomi": is_xiaomi,
                    "device_id": device_id,
                    "state": entity.get("state", ""),
                })
        
        return sorted(speakers, key=lambda x: (not x["is_xiaomi"], x["type"], x["name"]))
