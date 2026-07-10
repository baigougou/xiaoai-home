import logging
import asyncio
from typing import Optional, Callable, Dict
from ..config.config import AppConfig
from ..ha_client.client import HomeAssistantClient

logger = logging.getLogger(__name__)


class SpeakerPoller:
    def __init__(
        self,
        config: AppConfig,
        ha_client: HomeAssistantClient,
        on_command: Optional[Callable[[str, str], bool]] = None,
        on_poll: Optional[Callable] = None
    ):
        self.config = config
        self.ha_client = ha_client
        self.on_command = on_command
        self.on_poll = on_poll
        self.running = False
        self.last_texts: Dict[str, str] = {}
        self.polling_interval = config.bridge.polling_interval
        self.retry_count = 0
        self.max_retries = 3
        self.poll_count = 0

    def update_config(self, config: AppConfig):
        self.config = config
        new_speaker_ids = set(config.get_speaker_entity_ids())
        for eid in list(self.last_texts.keys()):
            if eid not in new_speaker_ids:
                del self.last_texts[eid]

    async def start(self):
        self.running = True
        speaker_count = len(self.config.get_speaker_entity_ids())
        logger.info(f"开始轮询{speaker_count}个小爱音箱，间隔{self.polling_interval}秒")
        while self.running:
            try:
                await self._poll_all()
                self.poll_count += 1
                if self.on_poll and self.poll_count % 5 == 0:
                    try:
                        await self.on_poll()
                    except Exception as e:
                        logger.debug(f"轮询回调出错: {e}")
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

    async def _poll_all(self):
        speaker_entity_ids = self.config.get_speaker_entity_ids()
        for entity_id in speaker_entity_ids:
            try:
                await self._poll_speaker(entity_id)
            except Exception as e:
                logger.error(f"轮询音箱{entity_id}出错: {e}")

    async def _poll_speaker(self, entity_id: str):
        state = await self.ha_client.get_state(entity_id)
        if not state:
            return

        attributes = state.get("attributes", {})

        text = ""
        for key in ["last_text", "current_text", "text", "media_title", "conversation_content", "last_command"]:
            if key in attributes and attributes[key]:
                text = str(attributes[key]).strip()
                if text:
                    break

        if not text:
            return

        last_text = self.last_texts.get(entity_id, "")
        if text == last_text:
            return

        self.last_texts[entity_id] = text
        logger.info(f"[{entity_id}] 获取到语音指令: {text}")

        if self.on_command:
            handled = await self.on_command(text, entity_id)
            if handled:
                logger.info(f"指令已处理: {text} (来自{entity_id})")
            else:
                logger.debug(f"指令未匹配: {text}")
