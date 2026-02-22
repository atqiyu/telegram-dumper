"""
数据模型模块
定义消息、聊天和下载记录的数据类
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, Any, Dict, List
import json


@dataclass
class Message:
    """消息数据模型"""
    id: int                                 # 消息ID
    chat_id: int                            # 聊天ID
    date: datetime                          # 发送时间
    text: str = ""                          # 消息文本 (格式化)
    raw_text: str = ""                      # 原始消息文本 (无格式)
    media_type: str = "text"                # 媒体类型 (text/photo/video/audio/document)
    file_name: Optional[str] = None         # 文件名 (Telegram服务器命名)
    file_path: Optional[str] = None         # 本地文件路径
    group_id: Optional[int] = None          # 媒体组ID (群组消息)
    
    # 发送者信息
    sender_id: Optional[int] = None          # 发送者ID
    sender_name: Optional[str] = None        # 发送者名称
    
    # 回复信息
    is_reply: bool = False                  # 是否为回复
    reply_to_msg_id: Optional[int] = None   # 回复的消息ID
    
    # 转发信息
    is_forward: bool = False                # 是否为转发
    forward_from_chat_id: Optional[int] = None  # 转发来源聊天ID
    forward_from_msg_id: Optional[int] = None   # 转发来源消息ID
    forward_from_name: Optional[str] = None  # 转发来源名称
    
    # 统计信息
    views: Optional[int] = None              # 查看数
    forwards: Optional[int] = None           # 转发数
    replies: Optional[int] = None            # 评论数/回复数
    
    # 评论区信息 (频道)
    is_discussion: bool = False               # 是否有评论区
    discussion_chat_id: Optional[int] = None  # 评论区聊天ID
    
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
    username: Optional[str] = None          # 用户名
    last_message_id: int = 0                # 最后一条消息ID
    total_messages: int = 0                 # 总消息数
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
    chat_id: int                           # 聊天ID
    file_name: str                         # 文件名
    file_path: str                         # 本地路径
    media_type: str                        # 媒体类型
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


@dataclass
class Comment:
    """评论数据模型"""
    id: int                                 # 评论消息ID
    chat_id: int                            # 聊天ID (评论区所在聊天)
    parent_id: int                          # 父消息ID (被评论的消息)
    date: datetime                          # 发送时间
    text: str = ""                          # 评论文本 (格式化)
    raw_text: str = ""                      # 原始评论文本 (无格式)
    media_type: str = "text"                # 媒体类型
    
    # 发送者信息
    sender_id: Optional[int] = None          # 发送者ID
    sender_name: Optional[str] = None        # 发送者名称
    
    # 统计信息
    views: Optional[int] = None              # 查看数
    
    raw_data: Dict[str, Any] = field(default_factory=dict)  # 原始数据
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data["date"] = self.date.isoformat() if self.date else None
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Comment":
        """从字典创建对象"""
        if isinstance(data.get("date"), str):
            data["date"] = datetime.fromisoformat(data["date"])
        return cls(**data)
