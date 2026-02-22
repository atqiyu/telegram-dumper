# Telegram Dumper 项目计划

## 项目目标
创建一个支持下载指定 Telegram 群组/频道所有消息及媒体数据的工具。

## 需求确认

| 项目 | 选择 |
|------|------|
| 存储方案 | 混合方案：元数据 JSON + SQLite 双份 |
| 文件名 | Telegram 服务器默认命名，使用 group 文件夹处理重复 |
| 导出格式 | JSON + SQLite 双份 |
| 功能 | 下载消息和媒体 + 增量下载 + CLI + 可拓展性 |
| 目录结构 | `output/{chat_id}/{message_id}/media/` |
| 增量下载判断 | B + C (message_id 目录存在 + SQLite 记录存在) |

## 目录结构

```
telegram-dumper/
├── src/
│   ├── __init__.py
│   ├── __main__.py
│   ├── config.py          # 配置管理
│   ├── client.py          # Telegram 客户端封装 + FastTelethon
│   ├── downloader.py     # 媒体下载逻辑
│   ├── models.py         # 数据模型定义
│   ├── main.py           # CLI 入口
│   ├── FastTelethon.py   # 并发下载模块
│   ├── fast_client.py    # 补丁文件
│   └── storage/
│       ├── __init__.py
│       ├── json_storage.py   # JSON 存储
│       └── sqlite_storage.py # SQLite 存储
├── tests/
├── requirements.txt
├── config.yaml.example
└── PROJECT_PLAN.md
```

## 输出目录结构

```
output/
└── {chat_id}/
    ├── metadata.json          # 聊天基本信息
    ├── messages.json          # 所有消息 (JSON)
    ├── messages.db            # SQLite 数据库
    └── messages/
        └── {message_id}/
            └── media/        # 该消息的媒体文件
```

## 实现步骤

### Step 1: 项目基础架构
- [x] 创建目录结构
- [x] 编写 requirements.txt
- [x] 实现 config.py 配置管理

### Step 2: 数据模型
- [x] 定义 Message/Chat 数据类
- [x] 设计 SQLite 表结构

### Step 3: 存储层
- [x] 实现 JSONStorage (增量写入)
- [x] 实现 SQLiteStorage (upsert 模式)

### Step 4: FastTelethon 集成
- [x] 从 trans/ 复制 FastTelethon.py
- [x] 创建 fast_client.py 补丁

### Step 5: Telegram 客户端
- [x] 封装 client.py
- [x] 集成 FastTelethon

### Step 6: 下载器
- [x] 实现消息遍历 + 增量检查
- [x] 实现媒体下载 (支持 group 文件夹)

### Step 7: CLI 入口
- [x] 实现命令行参数解析
- [x] 进度显示

## 数据模型设计

### Message
- id: int (主键)
- chat_id: int
- date: datetime
- text: str
- media_type: str (photo, video, audio, document, etc.)
- file_name: str (TG 服务器命名)
- file_path: str (本地路径)
- group_id: int (媒体组ID，可选)
- raw_data: dict (完整原始数据 JSON)

### Chat
- id: int (主键)
- title: str
- type: str (channel, group, private)
- username: str (可选)
- last_message_id: int
- total_messages: int
- created_at: datetime

### DownloadRecord
- message_id: int
- chat_id: int
- file_name: str
- file_path: str
- media_type: str
- downloaded_at: datetime

## 增量下载逻辑

1. 检查 `output/{chat_id}/messages/{message_id}/` 目录是否存在
2. 检查 SQLite 数据库中是否存在该 message_id 的记录
3. 如果两者都存在，跳过；否则下载

## 依赖

- telethon>=1.24.0
- aiofiles>=23.0.0
- aiosqlite>=0.19.0
- python-dotenv>=1.0.0
- pyyaml>=6.0.0
