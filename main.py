import os
import requests
import json
import re
import requests

from ncatbot.core import BotClient
from ncatbot.core import GroupMessage
from ncatbot.utils import config
from ncatbot.utils import get_log

LOG = get_log("Edison")

bot = BotClient()

@bot.group_event()
async def on_group_message(msg:GroupMessage):
    if msg.raw_message == "你好":
        await bot.api.post_group_msg(msg.group_id, text="你好呀，有什么需要我帮忙的吗？")


bot.run()
