"""
Telegram 客户端模块
封装 Telegram 客户端操作，包含 FastTelethon 并发下载支持
"""
import asyncio
import logging
from pathlib import Path
from typing import Optional, List, Union, AsyncGenerator
from datetime import datetime

from telethon import TelegramClient
from telethon.tl.types import Message, Chat, Channel, User, PeerChannel, PeerChat, PeerUser

from .config import Config
from .models import Chat as ChatModel, Message as MessageModel

log = logging.getLogger("TelegramClient")


class TelegramDumperClient:
    """Telegram Dumper 客户端封装类"""
    
    def __init__(self, config: Config):
        self.config = config
        self.client: Optional[TelegramClient] = None
        self._connected = False
    
    async def connect(self):
        """连接 Telegram 服务器"""
        if self._connected:
            return
        
        # 导入并应用 FastTelethon 补丁
        from . import fast_client
        
        self.client = TelegramClient(
            self.config.session_name,
            self.config.api_id,
            self.config.api_hash
        )
        await self.client.start()
        self._connected = True
        log.info("Telegram client connected with FastTelethon patch")
    
    async def disconnect(self):
        """断开连接"""
        if self.client and self._connected:
            await self.client.disconnect()
            self._connected = False
            log.info("Telegram client disconnected")
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.disconnect()
    
    def _get_chat_id(self, entity) -> int:
        """从实体获取聊天ID"""
        if isinstance(entity, Channel):
            return entity.id
        elif isinstance(entity, Chat):
            return entity.id
        elif isinstance(entity, User):
            return entity.id
        else:
            raise ValueError(f"Unknown entity type: {type(entity)}")
    
    def _get_chat_type(self, entity) -> str:
        """从实体获取聊天类型"""
        if isinstance(entity, Channel):
            return "channel" if entity.broadcast else "supergroup"
        elif isinstance(entity, Chat):
            return "group"
        elif isinstance(entity, User):
            return "private"
        return "unknown"
    
    async def get_entity(self, chat: Union[int, str]) -> ChatModel:
        """获取聊天实体信息"""
        if not self.client:
            raise RuntimeError("Client not connected")
        
        # 处理超级群/频道的 ID 格式
        # 超级群和频道需要 -100 前缀
        original_chat = chat
        if isinstance(chat, str) and chat.lstrip('-').isdigit():
            # 如果是纯数字字符串，转换为整数
            chat = int(chat)
        
        if isinstance(chat, int) and chat > 0:
            # 添加 -100 前缀给超级群/频道
            chat = int(f"-100{chat}")
        
        try:
            entity = await self.client.get_entity(chat)
        except ValueError:
            # 如果失败，尝试原始输入
            entity = await self.client.get_entity(original_chat)
        
        chat_id = self._get_chat_id(entity)
        chat_type = self._get_chat_type(entity)
        
        title = ""
        username = None
        
        if isinstance(entity, (Channel, Chat)):
            title = entity.title
            username = getattr(entity, 'username', None)
        elif isinstance(entity, User):
            title = f"{entity.first_name} {entity.last_name or ''}".strip()
            username = entity.username
        
        return ChatModel(
            id=chat_id,
            title=title,
            type=chat_type,
            username=username
        )
    
    async def iter_messages(
        self,
        chat: Union[int, str],
        limit: Optional[int] = None,
        offset_id: int = 0,
        min_id: int = 0,
        max_id: int = 0,
        reverse: bool = False
    ) -> AsyncGenerator[Message, None]:
        """迭代获取消息 (异步生成器)"""
        if not self.client:
            raise RuntimeError("Client not connected")
        
        # 转换超级群/频道 ID
        chat = self._convert_chat_id(chat)
        
        async for msg in self.client.iter_messages(
            chat,
            limit=limit,
            offset_id=offset_id,
            min_id=min_id,
            max_id=max_id,
            reverse=reverse
        ):
            yield msg
    
    async def get_messages(
        self,
        chat: Union[int, str],
        limit: int = 100,
        offset_id: int = 0
    ) -> List[Message]:
        """获取消息列表"""
        if not self.client:
            raise RuntimeError("Client not connected")
        
        # 转换超级群/频道 ID
        chat = self._convert_chat_id(chat)
        
        return await self.client.get_messages(
            chat,
            limit=limit,
            offset_id=offset_id
        )
    
    def _convert_chat_id(self, chat: Union[int, str]) -> int:
        """转换超级群/频道 ID 格式"""
        if isinstance(chat, str) and chat.lstrip('-').isdigit():
            chat = int(chat)
        
        if isinstance(chat, int) and chat > 0:
            return int(f"-100{chat}")
        return chat
    
    async def download_media(
        self,
        message: Message,
        file: Optional[str] = None,
        progress_callback=None
    ) -> Optional[str]:
        """下载媒体文件"""
        if not self.client:
            raise RuntimeError("Client not connected")
        
        if not message.media:
            return None
        
        if file is None:
            file = ""
        
        return await self.client.download_media(
            message,
            file=file,
            progress_callback=progress_callback
        )
    
    def _parse_media_type(self, message: Message) -> str:
        """解析媒体类型"""
        if not message.media:
            return "text"
        
        media = message.media
        
        if hasattr(media, 'photo'):
            return "photo"
        elif hasattr(media, 'video'):
            return "video"
        elif hasattr(media, 'audio'):
            return "audio"
        elif hasattr(media, 'document'):
            return "document"
        elif hasattr(media, 'web'):
            return "web"
        elif hasattr(media, 'geo'):
            return "location"
        elif hasattr(media, 'contact'):
            return "contact"
        
        return type(media).__name__.lower()
    
    def _extract_file_name(self, message: Message) -> Optional[str]:
        """提取文件名 (使用 Telegram 服务器默认命名)"""
        if not message.media:
            return None
        
        media = message.media
        
        if hasattr(media, 'document') and media.document:
            doc = media.document
            if hasattr(doc, 'attributes'):
                for attr in doc.attributes:
                    if hasattr(attr, 'file_name'):
                        return attr.file_name
        
        return None
    
    def message_to_model(self, message: Message, chat_id: int) -> MessageModel:
        """将 Telethon Message 转换为数据模型"""
        return MessageModel(
            id=message.id,
            chat_id=chat_id,
            date=message.date,
            text=message.text or "",
            media_type=self._parse_media_type(message),
            file_name=self._extract_file_name(message),
            group_id=message.grouped_id,
            raw_data=self._message_to_dict(message)
        )
    
    def _message_to_dict(self, message: Message) -> dict:
        """将 Message 转换为字典"""
        return {
            "id": message.id,
            "date": message.date.isoformat() if message.date else None,
            "text": message.text,
            "message": str(message),
        }
