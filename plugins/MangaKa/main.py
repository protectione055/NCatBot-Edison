from ncatbot.plugin import BasePlugin, CompatibleEnrollment, get_global_access_controller
from ncatbot.core.message import BaseMessage
from ncatbot.core import MessageChain, Image
from ncatbot.utils import get_log, config
from pathlib import Path

import os
import re
import asyncio
import time

LOG = get_log("MangaKa")

bot = CompatibleEnrollment  # 兼容回调函数注册器

class MangaKa(BasePlugin):
    name = "MangaKa" # 插件名称
    version = "0.0.9" # 插件版本
    author = "taurean_zz"
    description = "发送随机二次元图片"
    
    dependencies = {
        # "access": ">=1.0.0"
    }
    
    async def on_load(self):
        self.register_config("path", r"G:\漫画", description="漫画路径, 支持多个, 用 `;` 分割", value_type="str", metadata={
            "default": "plugins/MangaKa/manga"
        })
        self.register_config("batch", 5, description="一批发送的图片数量", value_type="int")
        self.register_config("lim_f", 3, description="不使用转发的阈值", value_type="int")   

        # self.register_admin_func("status", self.status, permission_raise=True, description="查看当前图片和路径状态", examples=["/status"], tags=["admin"])

        self.register_user_func(
            "漫画", 
            self.manga_handler, 
            prefix="漫画", 
            description="阅读漫画",
            usage="漫画 [漫画名] [话数]- 发送<漫画名>第[话数]话，如不指定话数则返回可阅读的话数列表",
            examples=["漫画", "漫画 onepiece 10", "漫画 onepiece"],
            tags=["user"]
        )

        print(f"{self.name} 插件已加载")
        print(f"插件版本: {self.version}")
    
    # async def status(self, msg:BaseMessage):
    #     await msg.reply(f"当前图片: {len(self.images)} 张, 路径: {self.data['config']['path']}\n \
    #                     普通用户一次请求最大发送数量: {self.config['lim_u']}\n \
    #                     超级用户一次请求最大发送数量: {self.config['lim_a']}\n \
    #                     不使用转发的阈值: {self.config['lim_f']} 张\n \
    #                     每批次发送图片数量: {self.config['batch']} 张\n"
    #                     )
    
    
    # 发送漫画
    async def manga_handler(self, msg:BaseMessage):
        # 解析命令
        LOG.info(f"收到消息: {msg.raw_message}")
        manga_name = None
        chapter = None
        match = re.match(r"\b漫画\b\s+([\u4e00-\u9fa5\w\d\s]+?)(?:\s+(\d+))?$", msg.raw_message)
        if match:
            manga_name = None if not match.group(1) else match.group(1).strip()
            chapter = None if not match.group(2) else int(match.group(2).strip())
        
        # 执行命令
        LOG.info(f"漫画名: {manga_name}, 话数: {chapter}")
        if manga_name is None:
            await self.send_manga_list(msg)
        elif chapter is None:
            await self.send_manga_chapter_list(msg, manga_name)
        else:
            await self.send_manga(msg, manga_name, chapter)
        
    # 获取所有漫画目录
    async def send_manga_list(self, msg:BaseMessage):
        manga_dirs = [d for d in os.listdir(self.config["path"]) if os.path.isdir(os.path.join(self.config["path"], d))]
        LOG.info(f"获取漫画目录: {self.config['path']}")
        LOG.info(f"找到漫画目录: {manga_dirs}")
        if not manga_dirs:
            await msg.reply("没有找到任何漫画目录")
            return
        
        for count in range(len(manga_dirs)):
            manga_dirs[count] = f"{count + 1}. {manga_dirs[count]}"
        manga_list = "\n".join(manga_dirs)
        await msg.reply(f"可阅读的漫画列表:\n{manga_list}")
    
    async def send_manga_chapter_list(self, msg:BaseMessage, manga_name:str):
        manga_path = os.path.join(self.config["path"], manga_name)
        if not os.path.exists(manga_path):
            await msg.reply(f"没有找到漫画 {manga_name}")
            return
        
        # 获取所有章节目录
        chapter_dirs = [int(d) for d in os.listdir(manga_path) if os.path.isdir(os.path.join(manga_path, d))]
        LOG.info(f"获取漫画 {manga_name} 的章节目录: {str(chapter_dirs)}")
        if not chapter_dirs:
            await msg.reply(f"漫画 {manga_name} 没有找到任何章节")
            return
        
        # 合并连续章节
        show_chapter_dirs = []
        last_chapter = -999
        cur_chapter_item = None  # e.g., 1-2 or 4
        for chapter in sorted(chapter_dirs):
            if chapter != last_chapter + 1:
                if cur_chapter_item is not None:
                    cur_chapter_item = f"{cur_chapter_item}-{last_chapter}" if int(cur_chapter_item) != last_chapter else cur_chapter_item
                    show_chapter_dirs.append(cur_chapter_item)
                cur_chapter_item = str(chapter)
            last_chapter = chapter
        cur_chapter_item = f"{cur_chapter_item}-{last_chapter}" if int(cur_chapter_item) != last_chapter else cur_chapter_item
        show_chapter_dirs.append(cur_chapter_item)
        chapter_list = "\n".join(map(str, show_chapter_dirs))
        await msg.reply(f"漫画 {manga_name} 可阅读的章节:\n{chapter_list}")
        
    async def send_manga(self, msg:BaseMessage, manga_name:str, chapter:int):
        manga_path = os.path.join(self.config["path"], manga_name)
        if not os.path.exists(manga_path):
            await msg.reply(f"没有找到漫画 {manga_name}")
            return
        
        chapter_path = os.path.join(manga_path, str(chapter).zfill(5))
        if not os.path.exists(chapter_path):
            await msg.reply(f"漫画 {manga_name} 没有找到第 {chapter} 话")
            return
        
        # 获取所有图片文件
        image_files = [f for f in os.listdir(chapter_path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        if not image_files:
            await msg.reply(f"漫画 {manga_name} 第 {chapter} 话没有找到任何内容")
            return
        
        # 发送图片
        image_files.sort(key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else 0)
        LOG.info(f"找到漫画 {manga_name} 第 {chapter} 话的图片: {image_files}")
        image_paths = [os.path.join(chapter_path, f) for f in image_files]
        count = len(image_paths)

        selected_images = image_paths[0:count]
        # 使用合并转发消息
        if count > self.config["lim_f"]:
            # 先发送给自己
            forward_messages = []

            data = await self.api.post_private_msg(msg.self_id, text=f"漫画：{manga_name} 第 {chapter} 话")
            forward_messages.append(data["data"]["message_id"])

            # 并发发送所有图片
            msg_chains = []
            for i in range(0, len(selected_images), self.config["batch"]):
                group = selected_images[i : i + self.config["batch"]]
                msg_chains.append(MessageChain([Image(image) for image in group]))
            tasks = [self.api.post_private_msg(msg.self_id, rtf=msg_chain) for msg_chain in msg_chains]
            results = await asyncio.gather(*tasks)
            forward_messages.extend([result["data"]["message_id"] for result in results if result["retcode"] == 0])
            
            time.sleep(count * 0.08)
            LOG.info(forward_messages)
            LOG.debug(results)
            
            # 串行版本
            # for image in selected_images:
            #     data = await self.api.post_private_msg(msg.self_id, image=image)
            #     forward_messages.append(data["data"]["message_id"])
            
            # 发送合并转发消息
            if hasattr(msg, "group_id"):
                result = await self.api.send_group_forward_msg(
                    group_id=msg.group_id,
                    messages=forward_messages,
                )
                if result["retcode"] != 0:
                    # await msg.reply(f"群聊消息转发失败T_T")
                    msg_chain = MessageChain()
                    for i in range(0, len(selected_images), self.config["batch"]):
                        group = selected_images[i : i + self.config["batch"]]
                        msg_chain += MessageChain([Image(image) for image in group])
                    if hasattr(msg, "group_id"):
                        await self.api.post_group_msg(msg.group_id, rtf=msg_chain)
                    else:
                        await self.api.post_private_msg(msg.user_id, rtf=msg_chain)
                    # await self.api.forward_group_single_msg(forward_messages[-1], msg.group_id)
                    await self.api.post_group_msg(msg.group_id, text=f"以上是漫画 {manga_name} 第 {chapter} 话的全部内容🙂")
            else:
                result = await self.api.send_private_forward_msg(
                    user_id=msg.user_id,
                    messages=forward_messages,
                )
                if result["retcode"] != 0:
                    await msg.reply(f"消息转发失败T_T")
                    await self.api.forward_friend_single_msg(forward_messages[-1], msg.user_id)
        else:
            # 少量图片直接发送
            msg_chain = MessageChain(
                [Image(image) for image in selected_images]
            )
            if hasattr(msg, "group_id"):
                await self.api.post_group_msg(msg.group_id, rtf=msg_chain)
            else:
                await self.api.post_private_msg(msg.user_id, rtf=msg_chain)
    
    async def add(self, msg:BaseMessage):
        paths = msg.raw_message.split(" ")[1:]
        if not paths:
            await msg.reply("参数错误")
            return
        if not self.config["path"].endswith(";"):
            self.config["path"] += ";"
        self.config["path"] += ";".join(paths)
        await self.load_image(msg)
