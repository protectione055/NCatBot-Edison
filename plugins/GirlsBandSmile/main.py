import os
import random
import re
import asyncio
import time

from pathlib import Path

from ncatbot.plugin import BasePlugin, CompatibleEnrollment, get_global_access_controller
from ncatbot.core.message import BaseMessage
from ncatbot.core import MessageChain, Image
from ncatbot.utils import get_log


LOG = get_log("GirlsBandSmile")

bot = CompatibleEnrollment  # 兼容回调函数注册器

class GirlsBandSmile(BasePlugin):
    name = "GirlsBandSmile" # 插件名称
    version = "0.0.9" # 插件版本
    author = "huan-yp"
    description = "来组建属于你的乐队吧！"

    dependencies = {
        # "access": ">=1.0.0"
    }

    async def _load_image(self):
        paths = self.config["path"].split(";")
        self.images = []
        valid_paths = []

        for path in paths:
            path = path.strip()
            if not path:
                continue

            if not os.path.exists(path):
                LOG.warning(f"图片路径 {path} 不存在")
                continue

            valid_paths.append(path)
            if self.config["recursive"]:
                # 递归遍历目录
                for root, _, files in os.walk(path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        self.images.append(file_path)
            else:
                # 只遍历顶层目录
                for file in os.listdir(path):
                    file_path = os.path.join(path, file)
                    if os.path.isfile(file_path):
                        self.images.append(file_path)

        if not valid_paths:
            LOG.warning("所有配置的图片路径都不存在")
            return 0

        LOG.info(f"从 {len(valid_paths)} 个有效路径中加载了 {len(self.images)} 张图片")
        LOG.info(f"有效路径: {'\n'.join(valid_paths)}")
        return len(self.images)

    async def on_load(self):
        # self.register_config("path", r"C:\Users\zzm\OneDrive\Gallery\Girls Band Cry", description="图片路径, 支持多个, 用 `;` 分割", value_type="str", metadata={
        #     "default": "plugins/GirlsBandSmile/images"
        # })
        self.register_config("path", r"C:\Users\zzm\OneDrive\Gallery\Girls Band Cry", description="图片路径, 支持多个, 用 `;` 分割", value_type="str")
        self.register_config("recursive", False, description="是否递归加载子目录中的图片", value_type="bool")
        self.register_config("batch", 5, description="一批发送的图片数量", value_type="int")
        self.register_config("lim_f", 3, description="不使用转发的阈值", value_type="int")
        self.register_config("lim_u", 10, description="普通用户一次请求最大发送数量", value_type="int")
        self.register_config("lim_a", 30, description="超级用户一次请求最大发送数量", value_type="int")        

        self.register_admin_func("load_image", self.load_image, permission_raise=True, description="从配置的路径中加载图片", examples=["/load_image"], tags=["admin"])
        self.register_admin_func("status", self.status, permission_raise=True, description="查看当前图片和路径状态", examples=["/status"], tags=["admin"])
        self.register_admin_func("add", self.add, permission_raise=True, description="添加图片搜索路径", examples=["/add /dir/to/image/"], tags=["admin"])
        self.register_user_func(
            "我要组乐队！", 
            self.send_gbc_image, 
            prefix="我要组乐队", 
            description="发送随机乐队成员图片",
            usage="我要组乐队 [数量] - 发送若干张随机图片，默认为1张",
            examples=["我要组乐队", "我要组乐队 3", "我要组乐队 10"],
            tags=["user"]
        )
        self.images = []
        await self._load_image()
        print(f"{self.name} 插件已加载")
        print(f"插件版本: {self.version}")

    async def status(self, msg:BaseMessage):
        await msg.reply(f"当前图片: {len(self.images)} 张, 路径: {self.data['config']['path']}\n \
                        普通用户一次请求最大发送数量: {self.config['lim_u']}\n \
                        超级用户一次请求最大发送数量: {self.config['lim_a']}\n \
                        不使用转发的阈值: {self.config['lim_f']} 张\n \
                        每批次发送图片数量: {self.config['batch']} 张\n"
                        )

    async def send_image(self, msg:BaseMessage, count: int):
        # 随机选择指定数量的图片
        selected_images = random.sample(self.images, count)

        # 使用合并转发消息
        if count > self.config["lim_f"]:
            # 先发送给自己
            forward_messages = []

            # 并发发送所有图片
            msg_chains = []
            for i in range(0, len(selected_images), self.config["batch"]):
                group = selected_images[i : i + self.config["batch"]]
                msg_chains.append(MessageChain([Image(image) for image in group]))
            tasks = [self.api.post_private_msg(msg.self_id, rtf=msg_chain) for msg_chain in msg_chains]
            results = await asyncio.gather(*tasks)
            forward_messages = [result["data"]["message_id"] for result in results if result["retcode"] == 0]

            # 补充信息
            data = await self.api.post_private_msg(msg.self_id, text="Star NcatBot 谢谢喵: https://github.com/liyihao1110/ncatbot")
            forward_messages.append(data["data"]["message_id"])
            # data = await self.api.post_private_msg(msg.self_id, text=f"图片文件名: {','.join([Path(image).stem for image in selected_images])}")
            # forward_messages.append(data["data"]["message_id"])

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
                    await msg.reply(f"太涩了, 图片被吞哩")
                    await self.api.forward_group_single_msg(forward_messages[-1], msg.group_id)
            else:
                result = await self.api.send_private_forward_msg(
                    user_id=msg.user_id,
                    messages=forward_messages,
                )
                if result["retcode"] != 0:
                    await msg.reply(f"太涩了, 图片被吞哩")
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

    async def send_gbc_image(self, msg:BaseMessage):
        # 解析参数
        LOG.info(f"收到消息: {msg.raw_message}")
        count = 1  # 默认发送1张
        match = re.match(r"^我要组乐队(?:\s+(\d+))?$", msg.raw_message)
        if match:
            try:
                count = int(match.group(1))
                # 限制图片数量
                count = max(1, min(self.config["lim_a"] if get_global_access_controller().user_has_role(str(msg.user_id), "root") else self.config["lim_u"], count))
            except ValueError:
                count = 1

        LOG.debug(f"解析到数量: {count}")
        # 如果没有足够的图片
        if len(self.images) < count:
            await msg.reply(f"图片数量不足，当前只有 {len(self.images)} 张图片")
            return

        await self.send_image(msg, count)

    async def add(self, msg:BaseMessage):
        paths = msg.raw_message.split(" ")[1:]
        if not paths:
            await msg.reply("参数错误")
            return
        if not self.config["path"].endswith(";"):
            self.config["path"] += ";"
        self.config["path"] += ";".join(paths)
        await self.load_image(msg)

    async def on_change_load_image(self, paths, msg: BaseMessage):
        await self.load_image(msg)

    async def load_image(self, msg:BaseMessage):
        count = await self._load_image()
        await msg.reply(f"从 {self.config['path']} 加载 {count} 张图片")
