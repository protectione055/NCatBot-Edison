from ncatbot.plugin import BasePlugin, CompatibleEnrollment
from ncatbot.core import GroupMessage, PrivateMessage, BaseMessage

from .getter import InfoGetter

bot = CompatibleEnrollment  # 兼容回调函数注册器


class SystemStatus(BasePlugin):
    name = "SystemStatus"  # 插件名称
    version = "0.0.1"  # 插件版本
    author = "Isaaczhr"  # 插件作者
    description = "用来获取您的系统及运行状态信息的简单插件，兼容了联合国六大工作语言（用来水代码长度）"  # 插件描述
    dependencies = {}  # 插件依赖，格式: {"插件名": "版本要求"}

    async def on_load(self):
        # 插件加载时执行的操作

        self.register_admin_func(
            name="status",
            handler=self.status_handler,
            prefix="/status",
            description="获取系统信息",
            usage="/status",
            examples=["/status"],
            tags=["status", "example"],
            metadata={"category": "utility"}
        )

        self.register_admin_func(
            name="system",
            handler=self.system_handler,
            prefix="/system",
            description="获取状态信息",
            usage="/system",
            examples=["/system"],
            tags=["system", "example"],
            metadata={"category": "utility"}
        )
        
        # 注册配置项示例
        self.register_config(
            key="include_ip",
            default=False,
            description="系统信息输出是否包含 IP 地址，请自行斟酌",
            value_type="bool",
        )

    async def status_handler(self, msg: BaseMessage):
        status_info = InfoGetter.get_status_info()
        res = "\n".join([f"{k}: {v}" for k, v in status_info.items()])
        await msg.reply_text(res)

    async def system_handler(self, msg: BaseMessage):
        system_info = InfoGetter.get_system_info(include_ip=self.config["include_ip"])
        res = "\n".join([f"{k}: {v}" for k, v in system_info.items()])
        await msg.reply_text(res)
