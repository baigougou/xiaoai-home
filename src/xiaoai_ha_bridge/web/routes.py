from fastapi import APIRouter, HTTPException, Body
from fastapi.responses import HTMLResponse, FileResponse
from typing import Dict, Any, Optional
import os
import json
from ..config.config import AppConfig, ConfigManager, HomeAssistantConfig, XiaomiSpeakerConfig
from ..ha_client.client import HomeAssistantClient

router = APIRouter()
config_manager = ConfigManager()

_poller = None
_interceptor = None

def set_services(poller, interceptor):
    global _poller, _interceptor
    _poller = poller
    _interceptor = interceptor


@router.get("/", response_class=HTMLResponse)
async def index():
    index_file = os.path.join(os.path.dirname(__file__), "index.html")
    if not os.path.exists(index_file):
        web_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "web")
        index_file = os.path.join(web_dir, "index.html")
    
    with open(index_file, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@router.get("/api/config")
async def get_config():
    try:
        config = config_manager.load()
        return config.dict()
    except FileNotFoundError:
        return {
            "home_assistant": {"url": "", "api_token": ""},
            "xiaomi_speakers": [],
            "bridge": {
                "host": "0.0.0.0",
                "port": 18015,
                "debug": False,
                "log_level": "INFO",
                "polling_interval": 3
            },
            "tts": {"enabled": True, "volume": 50},
            "commands": {}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/config")
async def save_config(config_data: Dict[str, Any] = Body(...)):
    try:
        if "xiaomi_speaker" in config_data and "xiaomi_speakers" not in config_data:
            config_data["xiaomi_speakers"] = [config_data.pop("xiaomi_speaker")]
        
        if "xiaomi_speakers" in config_data:
            speakers = []
            for sp in config_data["xiaomi_speakers"]:
                if isinstance(sp, str):
                    speakers.append({"entity_id": sp})
                elif isinstance(sp, dict) and sp.get("entity_id"):
                    speakers.append(sp)
            config_data["xiaomi_speakers"] = speakers
        
        if "commands" in config_data:
            for cmd_id, cmd in config_data["commands"].items():
                if "device_type" not in cmd or not cmd["device_type"]:
                    entity_id = cmd.get("entity_id", "")
                    if entity_id.startswith("vacuum."):
                        cmd["device_type"] = "vacuum"
                    elif entity_id.startswith("light."):
                        cmd["device_type"] = "light"
                    elif entity_id.startswith("switch."):
                        cmd["device_type"] = "switch"
                    elif entity_id.startswith("fan."):
                        cmd["device_type"] = "fan"
                    else:
                        cmd["device_type"] = "climate"

        config = AppConfig(**config_data)
        config_manager.save(config)
        
        if _interceptor and _poller:
            _interceptor.update_config(config)
            _poller.update_config(config)
        
        return {"message": "配置保存成功"}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/test/ha")
async def test_ha_connection(config: Dict[str, Any] = Body(...)):
    from ..ha_client.client import HomeAssistantClient
    from ..config.config import HomeAssistantConfig

    try:
        ha_config = HomeAssistantConfig(**config)
        client = HomeAssistantClient(ha_config)
        success = await client.test_connection()
        await client.close()
        return {"success": success}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/api/execute")
async def execute_command(text: str = Body(..., embed=True)):
    from ..engine.parser import CommandParser

    try:
        config = config_manager.load()
        parser = CommandParser(config.commands)
        parsed = parser.parse_command(text)
        if not parsed:
            return {"handled": False, "message": "未匹配到指令"}

        from ..ha_client.client import HomeAssistantClient
        from ..engine.interceptor import CommandInterceptor

        ha_client = HomeAssistantClient(config.home_assistant)
        interceptor = CommandInterceptor(config, ha_client)
        handled = await interceptor.intercept(text)
        await ha_client.close()

        return {"handled": handled, "parsed": parsed}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/discover")
async def discover_entities():
    try:
        config = config_manager.load()
    except FileNotFoundError:
        raise HTTPException(status_code=400, detail="请先配置 Home Assistant 连接信息")
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"加载配置失败: {str(e)}")

    # 清理 URL 中的反引号
    ha_url = config.home_assistant.url.strip().strip('`')
    if not ha_url or not ha_url.startswith('http'):
        raise HTTPException(status_code=400, detail="Home Assistant URL 格式不正确，请检查配置")

    try:
        ha_client = HomeAssistantClient(config.home_assistant)
        entities = await ha_client.discover_entities()
        await ha_client.close()
        return entities
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"发现实体失败: {str(e)}")


@router.post("/api/discover/test")
async def discover_with_config(config_data: Dict[str, Any] = Body(...)):
    try:
        ha_config = HomeAssistantConfig(
            url=config_data["url"],
            api_token=config_data["api_token"]
        )
        ha_client = HomeAssistantClient(ha_config)
        success = await ha_client.test_connection()
        if not success:
            await ha_client.close()
            return {"success": False, "error": "无法连接到 Home Assistant"}
        entities = await ha_client.discover_entities()
        await ha_client.close()
        return {"success": True, "entities": entities}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/api/command/test")
async def test_command(text: str = Body(..., embed=True)):
    try:
        config = config_manager.load()
        from ..engine.parser import CommandParser
        parser = CommandParser(config.commands)
        parsed = parser.parse_command(text)
        return {
            "text": text,
            "matched": parsed is not None,
            "parsed": parsed
        }
    except Exception as e:
        return {"error": str(e)}


@router.post("/api/command/execute")
async def execute_test_command(data: Dict[str, Any] = Body(...)):
    try:
        text = data.get("text", "")
        source_speaker = data.get("source_speaker", "")
        
        if not text:
            return {"success": False, "error": "text 参数不能为空"}

        config = config_manager.load()
        from ..ha_client.client import HomeAssistantClient
        from ..engine.interceptor import CommandInterceptor

        ha_client = HomeAssistantClient(config.home_assistant)
        interceptor = CommandInterceptor(config, ha_client)
        handled = await interceptor.intercept(text, source_speaker)
        await ha_client.close()

        return {
            "success": handled,
            "message": "指令执行成功，已发送TTS播报和手机通知" if handled else "未匹配到指令或执行失败"
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


@router.get("/api/health")
async def health_check():
    return {"status": "ok", "version": "0.2.4"}


@router.get("/api/vacuum/rooms")
async def get_vacuum_rooms(entity_id: str):
    try:
        config = config_manager.load()
        ha_client = HomeAssistantClient(config.home_assistant)
        rooms = await ha_client.get_vacuum_rooms(entity_id)
        await ha_client.close()
        return {"success": True, "rooms": rooms}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e), "rooms": []}


@router.get("/api/commands/list")
async def get_commands_list():
    try:
        config = config_manager.load()
        commands = config.commands
        
        result = {
            "categories": {
                "climate": [],
                "vacuum": [],
                "light": [],
                "switch": [],
                "fan": [],
                "refrigerator": [],
                "dishwasher": [],
                "washing_machine": [],
                "dryer": [],
                "stove": [],
                "range_hood": [],
                "water_heater": [],
                "air_purifier": [],
                "humidifier": [],
                "cover": [],
                "other": [],
            },
            "all_commands": []
        }
        
        type_labels = {
            "climate": "空调",
            "vacuum": "扫地机器人",
            "light": "灯",
            "switch": "开关",
            "fan": "风扇",
            "refrigerator": "冰箱",
            "dishwasher": "洗碗机",
            "washing_machine": "洗衣机",
            "dryer": "烘干机",
            "stove": "灶台",
            "range_hood": "油烟机",
            "water_heater": "热水器",
            "air_purifier": "空气净化器",
            "humidifier": "加湿器",
            "cover": "窗帘",
        }
        
        for cmd_id, cmd in commands.items():
            device_type = getattr(cmd, 'device_type', 'climate')
            category = device_type if device_type in result["categories"] else "other"
            
            rooms = {}
            if hasattr(cmd, 'rooms') and cmd.rooms:
                for room_key, room_config in cmd.rooms.items():
                    room_name = room_config.name if hasattr(room_config, 'name') else room_config.get('name', room_key)
                    rooms[room_name] = {
                        "segment_id": room_config.segment_id if hasattr(room_config, 'segment_id') else room_config.get('segment_id'),
                        "clean_mode": room_config.clean_mode if hasattr(room_config, 'clean_mode') else room_config.get('clean_mode', 'sweep_and_mop'),
                        "repeats": room_config.repeats if hasattr(room_config, 'repeats') else room_config.get('repeats', 1),
                    }
            
            cmd_info = {
                "command_id": cmd_id,
                "name": cmd.name,
                "entity_id": cmd.entity_id,
                "device_type": device_type,
                "device_type_label": type_labels.get(device_type, device_type),
                "keywords": list(cmd.keywords) if hasattr(cmd, 'keywords') else [],
                "rooms": rooms,
            }
            
            result["categories"][category].append(cmd_info)
            result["all_commands"].append(cmd_info)
        
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/speakers/discover")
async def discover_speakers():
    try:
        config = config_manager.load()
        ha_client = HomeAssistantClient(config.home_assistant)
        speakers = await ha_client.discover_speakers()
        await ha_client.close()
        return {"success": True, "speakers": speakers}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e), "speakers": []}


@router.get("/api/notify/services")
async def get_notify_services():
    try:
        config = config_manager.load()
        ha_client = HomeAssistantClient(config.home_assistant)
        services = await ha_client.discover_notify_services()
        await ha_client.close()
        return {"success": True, "services": services}
    except Exception as e:
        return {"success": False, "error": str(e), "services": []}


@router.post("/api/notify/test")
async def test_notification(data: Dict[str, Any] = Body(...)):
    try:
        config = config_manager.load()
        notify_services = data.get("notify_services") or config.tts.notify_services
        if not notify_services:
            single_service = data.get("notify_service", "")
            if single_service:
                notify_services = [single_service]
        if not notify_services:
            return {"success": False, "error": "未配置通知服务"}
        
        import httpx
        title = data.get("title", "🧪 测试通知")
        message = data.get("message", "这是一条来自XiaoAI HA Bridge的测试消息")
        
        ha_url = config.home_assistant.url.rstrip("/")
        headers = {
            "Authorization": f"Bearer {config.home_assistant.api_token}",
            "Content-Type": "application/json"
        }
        
        results = {}
        success_count = 0
        async with httpx.AsyncClient(timeout=10.0) as client:
            for notify_service in notify_services:
                if not notify_service or not notify_service.startswith("notify."):
                    results[notify_service] = {"success": False, "error": "服务格式错误"}
                    continue
                service_name = notify_service.split(".", 1)[1]
                try:
                    resp = await client.post(
                        f"{ha_url}/api/services/notify/{service_name}",
                        headers=headers,
                        json={"title": title, "message": message}
                    )
                    if resp.status_code == 200:
                        results[notify_service] = {"success": True}
                        success_count += 1
                    else:
                        error_detail = f"HTTP {resp.status_code}"
                        try:
                            error_json = resp.json()
                            error_detail += f": {error_json.get('message', str(error_json))}"
                        except:
                            error_detail += f": {resp.text[:200]}"
                        results[notify_service] = {"success": False, "error": error_detail}
                except Exception as e:
                    results[notify_service] = {"success": False, "error": str(e)}
        
        if success_count > 0:
            return {"success": True, "message": f"已向{success_count}个设备发送测试通知，请检查手机", "results": results}
        else:
            return {"success": False, "error": "所有通知服务发送失败", "results": results}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


@router.post("/api/restart")
async def restart_service():
    import os
    import signal
    import threading

    def delayed_exit():
        import time
        time.sleep(1)
        os.kill(os.getpid(), signal.SIGTERM)

    threading.Thread(target=delayed_exit, daemon=True).start()
    return {"message": "服务正在重启..."}


@router.get("/api/export/entities")
async def export_entities():
    try:
        config = config_manager.load()
    except FileNotFoundError:
        raise HTTPException(status_code=400, detail="请先配置 Home Assistant 连接信息")
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"加载配置失败: {str(e)}")

    ha_url = config.home_assistant.url.strip().strip('`')
    if not ha_url or not ha_url.startswith('http'):
        raise HTTPException(status_code=400, detail="Home Assistant URL 格式不正确，请检查配置")

    try:
        ha_client = HomeAssistantClient(config.home_assistant)
        result = await ha_client.discover_entities()
        await ha_client.close()
        
        entities = result.get("entities", {})
        areas = result.get("areas", {})
        
        export_data = {
            "areas": areas,
            "categories": {
                "climate": entities.get("climate", []),
                "light": entities.get("light", []),
                "washing_machine": entities.get("washing_machine", []),
                "dryer": entities.get("dryer", []),
                "stove": entities.get("stove", []),
                "range_hood": entities.get("range_hood", []),
                "bathroom_heater": entities.get("bathroom_heater", []),
                "smart_socket": entities.get("smart_socket", []),
                "notify": entities.get("notify", []),
                "vacuum": entities.get("vacuum", []),
                "fan": entities.get("fan", []),
                "cover": entities.get("cover", []),
                "humidifier": entities.get("humidifier", []),
                "media_player": entities.get("media_player", []),
                "sensor": entities.get("sensor", []),
                "switch": entities.get("switch", []),
                "other": entities.get("other", []),
            },
            "summary": {
                "climate": len(entities.get("climate", [])),
                "light": len(entities.get("light", [])),
                "washing_machine": len(entities.get("washing_machine", [])),
                "dryer": len(entities.get("dryer", [])),
                "stove": len(entities.get("stove", [])),
                "range_hood": len(entities.get("range_hood", [])),
                "bathroom_heater": len(entities.get("bathroom_heater", [])),
                "smart_socket": len(entities.get("smart_socket", [])),
                "notify": len(entities.get("notify", [])),
                "vacuum": len(entities.get("vacuum", [])),
                "fan": len(entities.get("fan", [])),
                "cover": len(entities.get("cover", [])),
                "humidifier": len(entities.get("humidifier", [])),
                "media_player": len(entities.get("media_player", [])),
                "sensor": len(entities.get("sensor", [])),
                "switch": len(entities.get("switch", [])),
                "other": len(entities.get("other", [])),
                "total": sum(len(v) for v in entities.values()),
            }
        }
        
        return export_data
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"导出实体失败: {str(e)}")
