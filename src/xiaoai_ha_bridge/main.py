import asyncio
import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config.config import ConfigManager, AppConfig
from .ha_client.client import HomeAssistantClient
from .engine.interceptor import CommandInterceptor
from .miservice.poller import SpeakerPoller
from .logging.logger import setup_logging
from .web.routes import router

logger = logging.getLogger(__name__)

app = FastAPI(
    title="XiaoAI Home Assistant Bridge",
    description="通过小爱音箱语音控制第三方智能家居设备",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

ha_client: HomeAssistantClient = None
interceptor: CommandInterceptor = None
poller: SpeakerPoller = None
config: AppConfig = None


@app.on_event("startup")
async def startup_event():
    global ha_client, interceptor, poller, config

    setup_logging("INFO", "config/app.log")
    logger.info("XiaoAI Home Assistant Bridge 启动中...")

    config_manager = ConfigManager()
    try:
        config = config_manager.load()
        setup_logging(config.bridge.log_level, "config/app.log")
    except FileNotFoundError:
        logger.warning("配置文件不存在，请访问 Web 界面进行配置")
        config = None
        return

    ha_client = HomeAssistantClient(config.home_assistant)
    interceptor = CommandInterceptor(config, ha_client)

    success = await ha_client.test_connection()
    if success:
        logger.info("成功连接到 Home Assistant")
    else:
        logger.warning("连接 Home Assistant 失败，请检查配置")

    poller = SpeakerPoller(config, ha_client, on_command=interceptor.intercept)
    asyncio.create_task(poller.start())

    logger.info(f"服务已启动，监听 http://{config.bridge.host}:{config.bridge.port}")


@app.on_event("shutdown")
async def shutdown_event():
    global poller, ha_client
    logger.info("服务关闭中...")

    if poller:
        await poller.stop()

    if ha_client:
        await ha_client.close()

    logger.info("服务已关闭")


if __name__ == "__main__":
    import uvicorn
    config_manager = ConfigManager()
    try:
        cfg = config_manager.load()
        uvicorn.run(
            "xiaoai_ha_bridge.main:app",
            host=cfg.bridge.host,
            port=cfg.bridge.port,
            reload=cfg.bridge.debug
        )
    except FileNotFoundError:
        print("配置文件不存在，请复制 config/config-example.json 为 config/config.json")
        uvicorn.run(
            "xiaoai_ha_bridge.main:app",
            host="0.0.0.0",
            port=8000,
            reload=True
        )
