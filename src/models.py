"""
数据模型模块
定义消息、聊天和下载记录的数据类
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, Any, Dict
import json


@dataclass
class Message:
    """消息数据模型"""
    id: int                                 # 消息ID
    chat_id: int                            # 聊天ID
    date: datetime                          # 发送时间
    text: str = ""                          # 消息文本
    media_type: str = "text"                # 媒体类型 (text/photo/video/audio/document)
    file_name: Optional[str] = None        # 文件名 (Telegram服务器命名)
    file_path: Optional[str] = None        # 本地文件路径
    group_id: Optional[int] = None         # 媒体组ID (群组消息)
    raw_data: Dict[str, Any] = field(default_factory=dict)  # 原始数据
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data["date"] = self.date.isoformat() if self.date else None
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """从字典创建对象"""
        if isinstance(data.get("date"), str):
            data["date"] = datetime.fromisoformat(data["date"])
        return cls(**data)


@dataclass
class Chat:
    """聊天数据模型"""
    id: int                                 # 聊天ID
    title: str                              # 聊天标题
    type: str                               # 聊天类型 (channel/group/private)
    username: Optional[str] = None         # 用户名
    last_message_id: int = 0               # 最后一条消息ID
    total_messages: int = 0                # 总消息数
    created_at: datetime = field(default_factory=datetime.now)  # 创建时间
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Chat":
        """从字典创建对象"""
        if isinstance(data.get("created_at"), str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        return cls(**data)


@dataclass
class DownloadRecord:
    """下载记录数据模型"""
    message_id: int                         # 消息ID
    chat_id: int                            # 聊天ID
    file_name: str                          # 文件名
    file_path: str                          # 本地路径
    media_type: str                         # 媒体类型
    downloaded_at: datetime = field(default_factory=datetime.now)  # 下载时间
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data["downloaded_at"] = self.downloaded_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DownloadRecord":
        """从字典创建对象"""
        if isinstance(data.get("downloaded_at"), str):
            data["downloaded_at"] = datetime.fromisoformat(data["downloaded_at"])
        return cls(**data)
