import logging
import asyncio
from typing import Optional, Callable
from ..config.config import AppConfig
from ..ha_client.client import HomeAssistantClient

logger = logging.getLogger(__name__)


class SpeakerPoller:
    def __init__(
        self,
        config: AppConfig,
        ha_client: HomeAssistantClient,
        on_command: Optional[Callable[[str], bool]] = None
    ):
        self.config = config
        self.ha_client = ha_client
        self.on_command = on_command
        self.running = False
        self.last_text = ""
        self.polling_interval = config.bridge.polling_interval
        self.retry_count = 0
        self.max_retries = 3

    async def start(self):
        self.running = True
        logger.info(f"开始轮询小爱音箱，间隔{self.polling_interval}秒")
        while self.running:
            try:
                await self._poll()
                self.retry_count = 0
            except Exception as e:
                self.retry_count += 1
                logger.error(f"轮询出错: {e}, 重试次数: {self.retry_count}")
                if self.retry_count >= self.max_retries:
                    logger.error(f"连续{self.max_retries}次轮询失败，等待{self.polling_interval * 5}秒后重试")
                    await asyncio.sleep(self.polling_interval * 5)
                    self.retry_count = 0
            await asyncio.sleep(self.polling_interval)

    async def stop(self):
        self.running = False
        logger.info("停止轮询")

    async def _poll(self):
        entity_id = self.config.xiaomi_speaker.entity_id
        state = await self.ha_client.get_state(entity_id)
        if not state:
            return

        attributes = state.get("attributes", {})

        text = ""
        if "last_text" in attributes:
            text = attributes["last_text"]
        elif "current_text" in attributes:
            text = attributes["current_text"]
        elif "text" in attributes:
            text = attributes["text"]
        elif "media_title" in attributes:
            text = attributes["media_title"]

        if not text or text.strip() == "":
            return

        if text == self.last_text:
            return

        self.last_text = text
        logger.info(f"获取到语音指令: {text}")

        if self.on_command:
            handled = await self.on_command(text)
            if handled:
                logger.info(f"指令已处理: {text}")
            else:
                logger.debug(f"指令未匹配: {text}")
