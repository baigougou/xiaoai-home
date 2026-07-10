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
                "port": 8000,
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

    try:
        ha_client = HomeAssistantClient(config.home_assistant)
        entities = await ha_client.discover_entities()
        await ha_client.close()
        return entities
    except Exception as e:
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


@router.get("/api/health")
async def health_check():
    return {"status": "ok", "version": "0.2.0"}


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
