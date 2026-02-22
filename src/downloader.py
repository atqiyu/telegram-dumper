"""
下载器模块
实现消息和媒体的下载逻辑，包含增量下载支持
"""
import asyncio
import logging
import os
from pathlib import Path
from typing import Optional, List, Callable, Set
from datetime import datetime

from telethon.tl.types import Message

from .client import TelegramDumperClient
from .config import Config
from .models import Message as MessageModel, Chat as ChatModel, DownloadRecord
from .storage.json_storage import JSONStorage
from .storage.sqlite_storage import SQLiteStorage

log = logging.getLogger("Downloader")


class ProgressTracker:
    """进度跟踪器"""
    
    def __init__(self, total: int, callback: Optional[Callable] = None):
        self.total = total              # 总数
        self.current = 0               # 当前进度
        self.downloaded_media = 0       # 已下载媒体数
        self.skipped = 0                # 跳过数
        self.errors = 0                 # 错误数
        self.callback = callback        # 回调函数
    
    def update(self, downloaded: int = 0, skipped: int = 0, error: int = 0):
        """更新进度"""
        self.current += 1
        self.downloaded_media += downloaded
        self.skipped += skipped
        self.errors += error
        
        if self.callback:
            self.callback(self)
    
    def get_progress_str(self) -> str:
        """获取进度字符串"""
        return (f"Progress: {self.current}/{self.total} | "
                f"Downloaded: {self.downloaded_media} | "
                f"Skipped: {self.skipped} | "
                f"Errors: {self.errors}")


class Downloader:
    """下载器主类"""
    
    def __init__(self, config: Config, output_dir: str = "output"):
        self.config = config
        self.output_dir = Path(output_dir)
        self.json_storage = JSONStorage(str(self.output_dir))
        self.sqlite_storage = SQLiteStorage(str(self.output_dir))
    
    def _get_message_dir(self, chat_id: int, message_id: int) -> Path:
        """获取消息目录路径"""
        return self.output_dir / str(chat_id) / "messages" / str(message_id)
    
    def _get_media_dir(self, chat_id: int, message_id: int, group_id: Optional[int] = None) -> Path:
        """获取媒体目录路径"""
        if group_id:
            # 媒体组使用 group 文件夹
            return self.output_dir / str(chat_id) / "messages" / f"group_{group_id}"
        return self.output_dir / str(chat_id) / "messages" / str(message_id) / "media"
    
    async def _check_message_exists(self, chat_id: int, message_id: int) -> bool:
        """检查消息是否已存在 (目录 + 数据库双重检查)"""
        dir_exists = self._get_message_dir(chat_id, message_id).exists()
        db_exists = await self.sqlite_storage.message_exists(message_id, chat_id)
        return dir_exists and db_exists
    
    async def _download_media(
        self,
        client: TelegramDumperClient,
        message: Message,
        chat_id: int,
        progress: Optional[ProgressTracker] = None
    ) -> Optional[str]:
        """
        下载媒体文件
        使用 Telegram 服务器默认文件名
        支持 group 文件夹处理文件名重复
        """
        if not message.media:
            return None
        
        group_id = message.grouped_id
        media_dir = self._get_media_dir(chat_id, message.id, group_id)
        media_dir.mkdir(parents=True, exist_ok=True)
        
        file_name = client._extract_file_name(message)
        
        # 检查文件是否已存在 (防止重复下载)
        if file_name:
            existing_files = list(media_dir.glob("*"))
            existing_names = [f.name for f in existing_files]
            
            if file_name in existing_names:
                log.debug(f"File already exists: {file_name}")
                if progress:
                    progress.update(downloaded=0, skipped=1)
                return str(media_dir / file_name)
        
        def progress_callback(current: int, total: int):
            """进度回调函数"""
            if progress and total > 0:
                percent = current / total * 100
                log.debug(f"Downloading: {percent:.1f}%")
        
        try:
            file_path = await client.download_media(
                message,
                file=str(media_dir),
                progress_callback=progress_callback
            )
            
            if file_path:
                # 保存下载记录
                record = DownloadRecord(
                    message_id=message.id,
                    chat_id=chat_id,
                    file_name=os.path.basename(file_path),
                    file_path=file_path,
                    media_type=client._parse_media_type(message)
                )
                await self.sqlite_storage.save_download_record(record)
                
                if progress:
                    progress.update(downloaded=1, skipped=0)
                
                return file_path
        except Exception as e:
            log.error(f"Failed to download media for message {message.id}: {e}")
            if progress:
                progress.update(downloaded=0, skipped=0, error=1)
        
        return None
    
    async def download_chat(
        self,
        client: TelegramDumperClient,
        chat: Union[int, str],
        limit: Optional[int] = None,
        skip_media: bool = False,
        progress_callback: Optional[Callable] = None
    ) -> dict:
        """
        下载聊天消息和媒体
        
        参数:
            client: Telegram 客户端
            chat: 聊天ID或用户名
            limit: 最大消息数 (None 表示全部)
            skip_media: 是否跳过媒体下载
            progress_callback: 进度回调函数
        
        返回:
            下载结果统计字典
        """
        entity = await client.get_entity(chat)
        chat_id = entity.id
        
        log.info(f"Starting download for chat: {entity.title} (ID: {chat_id})")
        
        # 保存元数据
        await self.json_storage.save_chat_metadata(entity)
        await self.sqlite_storage.save_chat(entity)
        
        # 获取已存在的消息ID集合
        existing_ids = await self.sqlite_storage.get_all_message_ids(chat_id)
        log.info(f"Found {len(existing_ids)} existing messages in database")
        
        messages_downloaded = 0
        media_downloaded = 0
        messages_skipped = 0
        errors = 0
        
        offset_id = 0
        batch_size = 100
        total_processed = 0
        
        # 分批获取消息
        while True:
            messages = await client.get_messages(chat, limit=batch_size, offset_id=offset_id)
            
            if not messages:
                break
            
            for msg in messages:
                # 增量下载检查: 目录存在 + 数据库记录存在
                if msg.id in existing_ids:
                    dir_exists = self._get_message_dir(chat_id, msg.id).exists()
                    if dir_exists:
                        messages_skipped += 1
                        continue
                
                # 转换为数据模型
                msg_model = client.message_to_model(msg, chat_id)
                
                # 下载媒体
                if msg.media and not skip_media:
                    file_path = await self._download_media(client, msg, chat_id, None)
                    msg_model.file_path = file_path
                    if file_path:
                        media_downloaded += 1
                
                # 保存到存储
                await self.json_storage.save_message(msg_model)
                await self.sqlite_storage.save_message(msg_model)
                
                messages_downloaded += 1
                total_processed += 1
                
                if progress_callback:
                    progress_callback(total_processed, msg.id)
                
                offset_id = msg.id
            
            # 检查是否达到限制
            if limit and total_processed >= limit:
                break
            
            # 检查是否已获取全部消息
            if len(messages) < batch_size:
                break
        
        # 更新聊天元数据
        entity.last_message_id = offset_id
        entity.total_messages = messages_downloaded
        await self.json_storage.save_chat_metadata(entity)
        await self.sqlite_storage.save_chat(entity)
        
        result = {
            "chat_id": chat_id,
            "chat_title": entity.title,
            "messages_downloaded": messages_downloaded,
            "messages_skipped": messages_skipped,
            "media_downloaded": media_downloaded,
            "errors": errors
        }
        
        log.info(f"Download complete: {result}")
        return result
    
    async def download_all(
        self,
        client: TelegramDumperClient,
        chats: List[Union[int, str]],
        progress_callback: Optional[Callable] = None
    ) -> List[dict]:
        """批量下载多个聊天"""
        results = []
        
        for chat in chats:
            try:
                result = await self.download_chat(
                    client,
                    chat,
                    progress_callback=progress_callback
                )
                results.append(result)
            except Exception as e:
                log.error(f"Failed to download chat {chat}: {e}")
                results.append({
                    "chat": str(chat),
                    "error": str(e)
                })
        
        return results


from typing import Union
