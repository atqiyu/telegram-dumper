"""
JSON 存储模块
提供消息和元数据的 JSON 文件存储功能
"""
import json
import aiofiles
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

from ..models import Message, Chat


class JSONStorage:
    """JSON 文件存储类"""
    
    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
    
    def _get_chat_dir(self, chat_id: int) -> Path:
        """获取聊天目录路径"""
        return self.output_dir / str(chat_id)
    
    def _get_messages_file(self, chat_id: int) -> Path:
        """获取消息文件路径"""
        return self._get_chat_dir(chat_id) / "messages.json"
    
    def _get_metadata_file(self, chat_id: int) -> Path:
        """获取元数据文件路径"""
        return self._get_chat_dir(chat_id) / "metadata.json"
    
    async def save_message(self, message: Message):
        """保存单条消息到 JSON 文件"""
        chat_dir = self._get_chat_dir(message.chat_id)
        chat_dir.mkdir(parents=True, exist_ok=True)
        
        messages_file = self._get_messages_file(message.chat_id)
        
        messages = []
        if messages_file.exists():
            async with aiofiles.open(messages_file, "r", encoding="utf-8") as f:
                content = await f.read()
                if content.strip():
                    messages = json.loads(content)
        
        messages.append(message.to_dict())
        
        async with aiofiles.open(messages_file, "w", encoding="utf-8") as f:
            await f.write(json.dumps(messages, ensure_ascii=False, indent=2))
    
    async def save_messages(self, messages: List[Message]):
        """保存多条消息"""
        for msg in messages:
            await self.save_message(msg)
    
    async def get_messages(self, chat_id: int) -> List[Message]:
        """获取指定聊天的所有消息"""
        messages_file = self._get_messages_file(chat_id)
        if not messages_file.exists():
            return []
        
        async with aiofiles.open(messages_file, "r", encoding="utf-8") as f:
            content = await f.read()
            if not content.strip():
                return []
            data = json.loads(content)
            return [Message.from_dict(m) for m in data]
    
    async def message_exists(self, message_id: int, chat_id: int) -> bool:
        """检查消息是否已存在"""
        messages = await self.get_messages(chat_id)
        return any(m.id == message_id for m in messages)
    
    async def save_chat_metadata(self, chat: Chat):
        """保存聊天元数据"""
        chat_dir = self._get_chat_dir(chat.id)
        chat_dir.mkdir(parents=True, exist_ok=True)
        
        metadata_file = self._get_metadata_file(chat.id)
        async with aiofiles.open(metadata_file, "w", encoding="utf-8") as f:
            await f.write(json.dumps(chat.to_dict(), ensure_ascii=False, indent=2))
    
    async def get_chat_metadata(self, chat_id: int) -> Optional[Chat]:
        """获取聊天元数据"""
        metadata_file = self._get_metadata_file(chat_id)
        if not metadata_file.exists():
            return None
        
        async with aiofiles.open(metadata_file, "r", encoding="utf-8") as f:
            content = await f.read()
            if not content.strip():
                return None
            return Chat.from_dict(json.loads(content))
