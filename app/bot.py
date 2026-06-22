import logging
import threading

import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType

from .config import VK_TOKEN, GROUP_ID
from .database import init_db, seed_data, get_bot_setting
from .handlers import handle_message_new, handle_callback

logger = logging.getLogger(__name__)


def resolve_group_id(vk, group_id_from_config):
    if group_id_from_config:
        return int(group_id_from_config)
    groups = vk.groups.getById()
    if groups:
        gid = groups[0]["id"]
        logger.info(f"Resolved group_id from API: {gid}")
        return gid
    raise ValueError("GROUP_ID not set and could not be resolved from API")


def start_bot(token=None, group_id=None, stop_event=None):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    fh = logging.FileHandler("bot_err.log", encoding="utf-8")
    fh.setLevel(logging.ERROR)
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    logging.getLogger().addHandler(fh)

    logger.info("Initializing database...")
    init_db()
    seed_data()

    if not token:
        token = get_bot_setting("vk_token") or VK_TOKEN
    if not group_id:
        group_id = get_bot_setting("group_id") or GROUP_ID

    logger.info("Connecting to VK...")
    vk_session = vk_api.VkApi(token=token)
    vk = vk_session.get_api()

    resolved_group_id = resolve_group_id(vk, group_id)
    logger.info(f"Bot started for group_id={resolved_group_id}")

    longpoll = VkBotLongPoll(vk_session, resolved_group_id, wait=5)

    logger.info("Long Poll started. Waiting for events...")

    for event in longpoll.listen():
        if stop_event and stop_event.is_set():
            logger.info("Stop event received, exiting bot loop")
            break
        try:
            event_type = event.type
            if event_type == VkBotEventType.MESSAGE_NEW:
                handle_message_new(vk, event)
            elif event_type == VkBotEventType.MESSAGE_EVENT:
                handle_callback(vk, event)
        except Exception as e:
            logger.exception(f"Error processing event: {e}")
