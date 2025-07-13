from ncatbot.plugin import BasePlugin, CompatibleEnrollment, get_global_access_controller
from ncatbot.core.message import BaseMessage
from ncatbot.core import MessageChain, Image, Video, Text
from ncatbot.utils import get_log, config
from pathlib import Path

import os
import re
import asyncio
import time
import json
import requests
import subprocess
from bs4 import BeautifulSoup

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
    bvcode_regex = r"^BV[1-9][A-Za-z0-9]{9}$"

    dependencies = {
        # "access": ">=1.0.0"
        # "beautifulsoup4": ">=4.6.0"
    }

    async def on_load(self):
        self.register_config(
            key="preview",
            default=True,
            value_type="bool"
        )
        self.register_user_func(
            name="cqcard_handler",
            handler=self.bilibili_cqjson_handler,
            regex=r"\[CQ:json,data=(.*b23\.tv.*)\]",
            tags=["user"],
        )

        self.register_user_func(
            name="bvcode_handler",
            handler=self.bilibili_bvcode_handler,
            regex=self.bvcode_regex,
            tags=["user"],
        )
        
        if not os.path.exists(self.tmp_dir):
            os.makedirs(self.tmp_dir)

        print(f"{self.name} 插件已加载")
        print(f"插件版本: {self.version}")

    async def bilibili_cqjson_handler(self, msg: BaseMessage):
        # 解析消息卡片中的Bilibili链接
        match = re.search(r'\[CQ:json,data=(.*)\]', msg.raw_message)
        qqdocurl = ""
        if match:
            content = match.group(1).replace("&#44;", ",")
            LOG.debug(f"Extracted JSON string: {content}")
            data = json.loads(content)
            LOG.debug(f"Received Bilibili data: {json.dumps(data, ensure_ascii=False, indent=2)}")
            qqdocurl = data['meta']['detail_1']['qqdocurl']
            bv_code = re.search(self.bvcode_regex, qqdocurl)
            if bv_code:
                bv_code = bv_code.group(0)
            # 获取并发送视频
            await self.__send_video_by_url(msg, qqdocurl, bv_code)
        else:
            LOG.warning("No valid Bilibili CQ card found in the message.")

    async def bilibili_bvcode_handler(self, msg: BaseMessage):
        """
        处理Bilibili视频链接或BV号
        """
        # 提取BV号或AV号
        bv_code = re.search(self.bvcode_regex, msg.raw_message)
        if bv_code:
            bv_code = bv_code.group(0)
            url = f"https://www.bilibili.com/video/{bv_code}"
            LOG.info(f"Extracted Bilibili URL: {url}")
            await self.__send_video_by_url(msg, url, bv_code)
        else:
            LOG.warning("No valid Bilibili video code found in the message.")

    async def __send_video_by_url(self, msg: BaseMessage, url: str, video_id: str):
        """
        通过Bilibili视频链接发送视频
        """
        content = await self.__request_content(url)
        
        # 拼接文字简介
        desc = "\n".join([
            f"标题：{content['title']}",
            f"简介：{content['description']}"
        ])

        # 合并视频和音频数据
        merged_video_path = await self.__merge_video_audio(video_id, content)

        # 发送消息
        video_msg = MessageChain([
            Video(file=merged_video_path)
        ])

        if hasattr(msg, "group_id"):
            await self.api.post_group_msg(msg.group_id, text=desc)
            await self.api.post_group_msg(msg.group_id, rtf=video_msg)
        else:
            await self.api.post_private_msg(msg.user_id, text=desc)
            await self.api.post_private_msg(msg.user_id, rtf=video_msg)
    
    async def __request_content(self, url: str):
        '''从url获取内容'''
        content  = {}
        response = None
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                LOG.error(f"Failed to get urls, response content: {response.text}")
        except requests.RequestException as e:
            LOG.error(f"Request url: {url} failed with error: {e}")

        """
        获取视频简介
        """
        soup = BeautifulSoup(response.text, "html.parser")
        
        content["title"] = re.split(r'_哔哩哔哩_', soup.title.string)[0] if soup.title else None
        
        desc_tag = soup.find("meta", attrs={"name": "description"})
        description = desc_tag["content"] if desc_tag and "content" in desc_tag.attrs else ""
        short_desc = re.split(r'作者简介', description)[0].strip()
        content["description"] = '\n'.join(short_desc.split(', '))
        
        
        """
        获取视频和音频的下载链接
        """
        json_data = json.loads(
            re.findall(
                "<script>window\.__playinfo__=(.*?)</script>", response.text
            )[0]
        )
        content["video_urls"] = json_data["data"]["dash"]["video"][0]["backupUrl"]
        content["audio_urls"] = json_data["data"]["dash"]["audio"][0]["backupUrl"]

        return content

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
            return None, None

        # 内容写入临时文件
        with open(video_path, "wb") as video_file:
            video_file.write(video_data)
        with open(audio_path, "wb") as audio_file:
            audio_file.write(audio_data)

        return video_path, audio_path

    async def __merge_video_audio(self, video_id: str, content: dict):
        """
        合并视频和音频数据
        返回完整视频的文件名
        """
        video_path = os.path.join(self.tmp_dir, f"{video_id}.mp4")
        if os.path.exists(video_path):
            return os.path.realpath(video_path)

        try:
            # TODO: 获取视频封面
            # 获取视频和音频
            video_urls = content["video_urls"]
            audio_urls = content["audio_urls"]
            if video_urls is None or audio_urls is None:
                LOG.warning("No video or audio URLs found in the provided URL.")
                return ""

            video_data, audio_data = await self.__get_media(video_urls, audio_urls)
            if video_data is None or audio_data is None:
                LOG.error("Failed to download video or audio.")
                return ""

            cmd = f"ffmpeg -y -i {video_data} -i {audio_data} -c:v h264_nvenc -c:a aac -strict experimental {video_path}"
            subprocess.run(cmd, shell=True, check=True)

            os.remove(video_data)  # 删除临时视频文件
            os.remove(audio_data)  # 删除临时音频文件
        except subprocess.CalledProcessError as e:
            LOG.error(f"FFmpeg command failed: {e}")
            return ""

        return os.path.realpath(video_path)
