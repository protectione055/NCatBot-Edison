from ncatbot.plugin import BasePlugin, CompatibleEnrollment, get_global_access_controller
from ncatbot.core.message import BaseMessage
from ncatbot.core import MessageChain, Image, Video
from ncatbot.utils import get_log, config
from pathlib import Path

import os
import re
import asyncio
import time
import json
import requests
import subprocess

LOG = get_log("BilibiliDownloader")

bot = CompatibleEnrollment  # 兼容回调函数注册器

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36",
    "Referer": "https://www.bilibili.com",
}


class BilibiliDownloader(BasePlugin):
    name = "BilibiliDownloader" # 插件名称
    version = "0.0.1" # 插件版本
    author = "taurean_zz"
    description = "提取Bilibili分享链接视频"
    tmp_dir = Path("plugins/BilibiliDownloader/temp")  # 临时文件目录

    dependencies = {
        # "access": ">=1.0.0"
    }

    async def on_load(self):
        self.register_user_func(
            name="bilibili_handler",
            handler=self.bilibili_cqjson_handler,
            regex=r"\[CQ:json,data=(.*b23\.tv.*)\]",
            tags=["user"],
        )

        print(f"{self.name} 插件已加载")
        print(f"插件版本: {self.version}")

    async def bilibili_cqjson_handler(self, msg: BaseMessage):
        # 解析消息卡片中的Bilibili链接
        match = re.search(r'\[CQ:json,data=(.*)\]', msg.raw_message)
        video_path = None
        if match:
            content = match.group(1).replace("&#44;", ",")
            LOG.debug(f"Extracted JSON string: {content}")
            try:
                data = json.loads(content)
                LOG.debug(f"Received Bilibili data: {json.dumps(data, ensure_ascii=False, indent=2)}")
                qqdocurl = data['meta']['detail_1']['qqdocurl']
                video_urls, audio_urls = await self.__get_urls(qqdocurl)
                if video_urls is None or audio_urls is None:
                    LOG.warning("No video or audio URLs found in the data.")
                    return
                # 获取视频和音频数据
                video_id, video_path, audio_path = await self.__get_media(video_urls, audio_urls)
                if video_path is None or audio_path is None:
                    LOG.error("Failed to download video or audio.")
                    return
                # 合并视频和音频数据
                video_path = await self.__merge_video_audio(video_id, video_path, audio_path)
            except json.JSONDecodeError as e:
                LOG.error(f"JSON decode error: {e}")
            
        if video_path is not None:
            await self.__send_video(msg, video_path)

    async def __send_video(self, msg: BaseMessage, video_path: str):
        send_msg = MessageChain(
            [Video(file=video_path)]
        )

        if hasattr(msg, "group_id"):
            await self.api.post_group_msg(msg.group_id, rtf=send_msg)
        else:
            await self.api.post_private_msg(msg.user_id, rtf=send_msg)

    async def __get_urls(self, request_url: str):
        """
        获取视频和音频的下载链接
        """
        video_urls = None
        audio_urls = None
        try:
            response = requests.get(request_url, headers=headers, timeout=10)
            if response.status_code == 200:
                json_data = json.loads(
                    re.findall(
                        "<script>window\.__playinfo__=(.*?)</script>", response.text
                    )[0]
                )
                video_urls = json_data["data"]["dash"]["video"][0]["backupUrl"]
                audio_urls = json_data["data"]["dash"]["audio"][0]["backupUrl"]
            else:
                LOG.error(f"Failed to get urls, response content: {response.text}")
        except requests.RequestException as e:
            LOG.error(f"Request url: {request_url} failed with error: {e}")
        return video_urls, audio_urls

    async def __get_media(self, video_urls: list, audio_urls: list):
        # 获取临时文件名
        temp_id = str(int(time.time() * 1000))
        video_filename = f"tmp_video_{temp_id}.mp4"
        audio_filename = f"tmp_audio_{temp_id}.mp3"
        video_path = os.path.join(self.tmp_dir, video_filename)
        audio_path = os.path.join(self.tmp_dir, audio_filename)

        # 从链接下载视频和音频数据
        video_data = None
        audio_data = None
        try:
            video_data = requests.get(url=video_urls[0], headers=headers).content
            audio_data = requests.get(url=audio_urls[0], headers=headers).content
        except requests.RequestException as e:
            LOG.error(f"Failed to download media: {e}")
            return temp_id, None, None

        # 内容写入临时文件
        with open(video_path, "wb") as video_file:
            video_file.write(video_data)
        with open(audio_path, "wb") as audio_file:
            audio_file.write(audio_data)

        return temp_id, video_path, audio_path

    async def __merge_video_audio(self, video_id: str, video_data: str, audio_data: str):
        """
        合并视频和音频数据
        返回完整视频的文件名
        """
        try:
            video_path = os.path.join(self.tmp_dir, f"video_{video_id}.mp4")
            cmd = f"ffmpeg -y -i {video_data} -i {audio_data} -c:v h264_nvenc -c:a aac -strict experimental {video_path}"
            subprocess.run(cmd, shell=True, check=True)

            os.remove(video_data)  # 删除临时视频文件
            os.remove(audio_data)  # 删除临时音频文件
        except subprocess.CalledProcessError as e:
            LOG.error(f"FFmpeg command failed: {e}")
            return None

        return os.path.realpath(video_path)
