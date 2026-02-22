"""
SQLite 存储模块
提供消息和元数据的 SQLite 数据库存储功能
"""
import aiosqlite
import json
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

from ..models import Message, Chat, DownloadRecord, Comment


class SQLiteStorage:
    """SQLite 数据库存储类"""
    
    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self._db_path = None
    
    def _get_db_path(self, chat_id: int) -> Path:
        """获取数据库文件路径"""
        return self.output_dir / str(chat_id) / "messages.db"
    
    async def _get_connection(self, chat_id: int):
        """获取数据库连接"""
        db_path = self._get_db_path(chat_id)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = await aiosqlite.connect(str(db_path))
        conn.row_factory = aiosqlite.Row
        return conn
    
    async def init_db(self, chat_id: int):
        """初始化数据库表结构"""
        conn = await self._get_connection(chat_id)
        try:
            # 消息表 (增强版)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY,
                    chat_id INTEGER NOT NULL,
                    date TEXT NOT NULL,
                    text TEXT DEFAULT '',
                    raw_text TEXT DEFAULT '',
                    media_type TEXT DEFAULT 'text',
                    file_name TEXT,
                    file_path TEXT,
                    group_id INTEGER,
                    sender_id INTEGER,
                    sender_name TEXT,
                    is_reply INTEGER DEFAULT 0,
                    reply_to_msg_id INTEGER,
                    is_forward INTEGER DEFAULT 0,
                    forward_from_chat_id INTEGER,
                    forward_from_msg_id INTEGER,
                    forward_from_name TEXT,
                    views INTEGER,
                    forwards INTEGER,
                    replies INTEGER,
                    is_discussion INTEGER DEFAULT 0,
                    discussion_chat_id INTEGER
                )
            """)
            # 聊天表
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS chats (
                    id INTEGER PRIMARY KEY,
                    title TEXT NOT NULL,
                    type TEXT NOT NULL,
                    username TEXT,
                    last_message_id INTEGER DEFAULT 0,
                    total_messages INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL
                )
            """)
            # 下载记录表
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS download_records (
                    message_id INTEGER NOT NULL,
                    chat_id INTEGER NOT NULL,
                    file_name TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    media_type TEXT NOT NULL,
                    downloaded_at TEXT NOT NULL,
                    PRIMARY KEY (chat_id, message_id, file_name)
                )
            """)
            # 评论表
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS comments (
                    id INTEGER NOT NULL,
                    chat_id INTEGER NOT NULL,
                    parent_id INTEGER NOT NULL,
                    date TEXT NOT NULL,
                    text TEXT DEFAULT '',
                    raw_text TEXT DEFAULT '',
                    media_type TEXT DEFAULT 'text',
                    sender_id INTEGER,
                    sender_name TEXT,
                    views INTEGER,
                    PRIMARY KEY (chat_id, id)
                )
            """)
            # 创建索引
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_chat_id ON messages(chat_id)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_download_records_chat_id ON download_records(chat_id)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_comments_chat_id ON comments(chat_id)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_comments_parent_id ON comments(parent_id)
            """)
            await conn.commit()
        finally:
            await conn.close()
    
    async def save_message(self, message: Message):
        """保存单条消息 (upsert 模式)"""
        await self.init_db(message.chat_id)
        conn = await self._get_connection(message.chat_id)
        try:
            await conn.execute("""
                INSERT OR REPLACE INTO messages 
                (id, chat_id, date, text, raw_text, media_type, file_name, file_path, group_id,
                 sender_id, sender_name, is_reply, reply_to_msg_id, is_forward,
                 forward_from_chat_id, forward_from_msg_id, forward_from_name,
                 views, forwards, replies, is_discussion, discussion_chat_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                message.id,
                message.chat_id,
                message.date.isoformat() if message.date else datetime.now().isoformat(),
                message.text,
                message.raw_text,
                message.media_type,
                message.file_name,
                message.file_path,
                message.group_id,
                message.sender_id,
                message.sender_name,
                int(message.is_reply),
                message.reply_to_msg_id,
                int(message.is_forward),
                message.forward_from_chat_id,
                message.forward_from_msg_id,
                message.forward_from_name,
                message.views,
                message.forwards,
                message.replies if hasattr(message, 'replies') else None,
                int(message.is_discussion),
                message.discussion_chat_id
            ))
            await conn.commit()
        finally:
            await conn.close()
    
    async def save_messages(self, messages: List[Message]):
        """批量保存消息"""
        if not messages:
            return
        
        chat_id = messages[0].chat_id
        await self.init_db(chat_id)
        conn = await self._get_connection(chat_id)
        try:
            for message in messages:
                await conn.execute("""
                    INSERT OR REPLACE INTO messages 
                    (id, chat_id, date, text, raw_text, media_type, file_name, file_path, group_id,
                     sender_id, sender_name, is_reply, reply_to_msg_id, is_forward,
                     forward_from_chat_id, forward_from_msg_id, forward_from_name,
                     views, forwards, replies, is_discussion, discussion_chat_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    message.id,
                    message.chat_id,
                    message.date.isoformat() if message.date else datetime.now().isoformat(),
                    message.text,
                    message.raw_text,
                    message.media_type,
                    message.file_name,
                    message.file_path,
                    message.group_id,
                    message.sender_id,
                    message.sender_name,
                    int(message.is_reply),
                    message.reply_to_msg_id,
                    int(message.is_forward),
                    message.forward_from_chat_id,
                    message.forward_from_msg_id,
                    message.forward_from_name,
                    message.views,
                    message.forwards,
                    message.replies if hasattr(message, 'replies') else None,
                    int(message.is_discussion),
                    message.discussion_chat_id
                ))
            await conn.commit()
        finally:
            await conn.close()
    
    async def get_messages(self, chat_id: int) -> List[Message]:
        """获取指定聊天的所有消息"""
        await self.init_db(chat_id)
        conn = await self._get_connection(chat_id)
        try:
            async with conn.execute(
                "SELECT * FROM messages WHERE chat_id = ? ORDER BY id", (chat_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                messages = []
                for row in rows:
                    messages.append(Message(
                        id=row["id"],
                        chat_id=row["chat_id"],
                        date=datetime.fromisoformat(row["date"]),
                        text=row["text"],
                        raw_text=row["raw_text"] or "",
                        media_type=row["media_type"],
                        file_name=row["file_name"],
                        file_path=row["file_path"],
                        group_id=row["group_id"],
                        sender_id=row["sender_id"],
                        sender_name=row["sender_name"],
                        is_reply=bool(row["is_reply"]),
                        reply_to_msg_id=row["reply_to_msg_id"],
                        is_forward=bool(row["is_forward"]),
                        forward_from_chat_id=row["forward_from_chat_id"],
                        forward_from_msg_id=row["forward_from_msg_id"],
                        forward_from_name=row["forward_from_name"],
                        views=row["views"],
                        forwards=row["forwards"],
                        replies=row["replies"],
                        is_discussion=bool(row["is_discussion"]),
                        discussion_chat_id=row["discussion_chat_id"]
                    ))
                return messages
        finally:
            await conn.close()
    
    async def message_exists(self, message_id: int, chat_id: int) -> bool:
        """检查消息是否已存在"""
        await self.init_db(chat_id)
        conn = await self._get_connection(chat_id)
        try:
            async with conn.execute(
                "SELECT 1 FROM messages WHERE id = ? AND chat_id = ? LIMIT 1",
                (message_id, chat_id)
            ) as cursor:
                return await cursor.fetchone() is not None
        finally:
            await conn.close()
    
    async def get_all_message_ids(self, chat_id: int) -> set:
        """获取所有消息ID集合"""
        await self.init_db(chat_id)
        conn = await self._get_connection(chat_id)
        try:
            async with conn.execute(
                "SELECT id FROM messages WHERE chat_id = ?", (chat_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                return {row["id"] for row in rows}
        finally:
            await conn.close()
    
    async def save_chat(self, chat: Chat):
        """保存聊天信息"""
        await self.init_db(chat.id)
        conn = await self._get_connection(chat.id)
        try:
            await conn.execute("""
                INSERT OR REPLACE INTO chats 
                (id, title, type, username, last_message_id, total_messages, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                chat.id,
                chat.title,
                chat.type,
                chat.username,
                chat.last_message_id,
                chat.total_messages,
                chat.created_at.isoformat()
            ))
            await conn.commit()
        finally:
            await conn.close()
    
    async def get_chat(self, chat_id: int) -> Optional[Chat]:
        """获取聊天信息"""
        await self.init_db(chat_id)
        conn = await self._get_connection(chat_id)
        try:
            async with conn.execute(
                "SELECT * FROM chats WHERE id = ?", (chat_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return None
                return Chat(
                    id=row["id"],
                    title=row["title"],
                    type=row["type"],
                    username=row["username"],
                    last_message_id=row["last_message_id"],
                    total_messages=row["total_messages"],
                    created_at=datetime.fromisoformat(row["created_at"])
                )
        finally:
            await conn.close()
    
    async def save_download_record(self, record: DownloadRecord):
        """保存下载记录"""
        await self.init_db(record.chat_id)
        conn = await self._get_connection(record.chat_id)
        try:
            await conn.execute("""
                INSERT OR REPLACE INTO download_records 
                (message_id, chat_id, file_name, file_path, media_type, downloaded_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                record.message_id,
                record.chat_id,
                record.file_name,
                record.file_path,
                record.media_type,
                record.downloaded_at.isoformat()
            ))
            await conn.commit()
        finally:
            await conn.close()
    
    async def download_record_exists(self, message_id: int, chat_id: int, file_name: str) -> bool:
        """检查下载记录是否存在"""
        await self.init_db(chat_id)
        conn = await self._get_connection(chat_id)
        try:
            async with conn.execute(
                "SELECT 1 FROM download_records WHERE message_id = ? AND chat_id = ? AND file_name = ?",
                (message_id, chat_id, file_name)
            ) as cursor:
                return await cursor.fetchone() is not None
        finally:
            await conn.close()
    
    async def save_comment(self, comment: Comment):
        """保存评论"""
        await self.init_db(comment.chat_id)
        conn = await self._get_connection(comment.chat_id)
        try:
            await conn.execute("""
                INSERT OR REPLACE INTO comments 
                (id, chat_id, parent_id, date, text, raw_text, media_type, sender_id, sender_name, views)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                comment.id,
                comment.chat_id,
                comment.parent_id,
                comment.date.isoformat() if comment.date else datetime.now().isoformat(),
                comment.text,
                comment.raw_text,
                comment.media_type,
                comment.sender_id,
                comment.sender_name,
                comment.views
            ))
            await conn.commit()
        finally:
            await conn.close()
    
    async def get_comments(self, chat_id: int, parent_message_id: int) -> List[Comment]:
        """获取指定消息的所有评论"""
        await self.init_db(chat_id)
        conn = await self._get_connection(chat_id)
        try:
            async with conn.execute(
                "SELECT * FROM comments WHERE chat_id = ? AND parent_id = ? ORDER BY id",
                (chat_id, parent_message_id)
            ) as cursor:
                rows = await cursor.fetchall()
                comments = []
                for row in rows:
                    comments.append(Comment(
                        id=row["id"],
                        chat_id=row["chat_id"],
                        parent_id=row["parent_id"],
                        date=datetime.fromisoformat(row["date"]),
                        text=row["text"],
                        raw_text=row["raw_text"] or "",
                        media_type=row["media_type"],
                        sender_id=row["sender_id"],
                        sender_name=row["sender_name"],
                        views=row["views"]
                    ))
                return comments
        finally:
            await conn.close()
