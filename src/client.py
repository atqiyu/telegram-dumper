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
from .models import Chat as ChatModel, Message as MessageModel, Comment as CommentModel

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
        
        # 提取发送者信息
        sender_id = None
        sender_name = None
        if hasattr(message, 'sender_id') and message.sender_id:
            sender_id = message.sender_id
        if hasattr(message, 'sender') and message.sender:
            sender = message.sender
            if hasattr(sender, 'first_name'):
                sender_name = f"{sender.first_name or ''} {sender.last_name or ''}".strip()
                if hasattr(sender, 'username') and sender.username:
                    sender_name = f"{sender_name} (@{sender.username})"
        
        # 提取回复信息
        is_reply = hasattr(message, 'is_reply') and message.is_reply
        reply_to_msg_id = None
        if is_reply and hasattr(message, 'reply_to') and message.reply_to:
            reply_to_msg_id = getattr(message.reply_to, 'reply_to_msg_id', None)
        
        # 提取转发信息
        is_forward = hasattr(message, 'forward') and message.forward is not None
        forward_from_chat_id = None
        forward_from_msg_id = None
        forward_from_name = None
        if is_forward and message.forward:
            forward_obj = message.forward
            if hasattr(forward_obj, 'chat'):
                forward_from_chat_id = getattr(forward_obj.chat, 'id', None)
                forward_from_name = getattr(forward_obj.chat, 'title', None)
            elif hasattr(forward_obj, 'from') or hasattr(forward_obj, 'from_name'):
                # 'from' 是关键字，需要用其他方式访问
                forward_from_name = getattr(forward_obj, 'from_name', None) or getattr(forward_obj, 'from', None)
                if forward_from_name and hasattr(forward_from_name, 'name'):
                    forward_from_name = forward_from_name.name
            if hasattr(forward_obj, 'msg_id'):
                forward_from_msg_id = forward_obj.msg_id
        
        # 提取统计信息
        views = getattr(message, 'views', None)
        forwards = getattr(message, 'forwards', None)
        
        # 提取评论信息 (频道) - replies 属性表示评论数量
        replies = getattr(message, 'replies', None)
        if replies and hasattr(replies, 'replies'):
            replies = replies.replies
        
        # 提取评论区信息
        is_discussion = getattr(message, 'is_discussion', False)
        discussion_chat_id = None
        if hasattr(message, 'discussion') and message.discussion:
            discussion_chat_id = getattr(message.discussion, 'chat', None)
            if discussion_chat_id:
                discussion_chat_id = getattr(discussion_chat_id, 'id', None)
        
        return MessageModel(
            id=message.id,
            chat_id=chat_id,
            date=message.date,
            text=message.text or "",
            raw_text=getattr(message, 'raw_text', "") or "",
            media_type=self._parse_media_type(message),
            file_name=self._extract_file_name(message),
            group_id=message.grouped_id,
            sender_id=sender_id,
            sender_name=sender_name,
            is_reply=is_reply,
            reply_to_msg_id=reply_to_msg_id,
            is_forward=is_forward,
            forward_from_chat_id=forward_from_chat_id,
            forward_from_msg_id=forward_from_msg_id,
            forward_from_name=forward_from_name,
            views=views,
            forwards=forwards,
            replies=replies,
            is_discussion=is_discussion,
            discussion_chat_id=discussion_chat_id,
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
    
    async def iter_comments(
        self,
        chat: Union[int, str],
        parent_message_id: int,
        limit: Optional[int] = None
    ) -> AsyncGenerator[CommentModel, None]:
        """
        获取评论/回复列表
        
        参数:
            chat: 聊天ID或用户名
            parent_message_id: 父消息ID
            
        返回:
            评论生成器
        """
        if not self.client:
            raise RuntimeError("Client not connected")
        
        # 转换聊天ID格式
        chat = self._convert_chat_id(chat)
        
        # 使用 reply_to 参数获取评论
        async for comment in self.client.iter_messages(
            chat,
            limit=limit,
            reply_to=parent_message_id
        ):
            yield self.comment_to_model(comment, chat)
    
    def comment_to_model(self, comment: Message, chat_id: int, parent_id: int = 0) -> CommentModel:
        """将 Telethon Message 转换为评论数据模型"""
        
        # 提取发送者信息
        sender_id = None
        sender_name = None
        if hasattr(comment, 'sender_id') and comment.sender_id:
            sender_id = comment.sender_id
        if hasattr(comment, 'sender') and comment.sender:
            sender = comment.sender
            if hasattr(sender, 'first_name'):
                sender_name = f"{sender.first_name or ''} {sender.last_name or ''}".strip()
                if hasattr(sender, 'username') and sender.username:
                    sender_name = f"{sender_name} (@{sender.username})"
        
        # 提取统计信息
        views = getattr(comment, 'views', None)
        
        return CommentModel(
            id=comment.id,
            chat_id=chat_id,
            parent_id=parent_id,
            date=comment.date,
            text=comment.text or "",
            raw_text=getattr(comment, 'raw_text', "") or "",
            media_type=self._parse_media_type(comment),
            sender_id=sender_id,
            sender_name=sender_name,
            views=views,
            raw_data=self._message_to_dict(comment)
        )
