# Telegram Dumper 使用手册

## 目录

1. [项目简介](#项目简介)
2. [环境要求](#环境要求)
3. [安装配置](#安装配置)
4. [快速开始](#快速开始)
5. [命令详解](#命令详解)
6. [输出说明](#输出说明)
7. [增量下载](#增量下载)
8. [数据字段说明](#数据字段说明)
9. [常见问题](#常见问题)

---

## 项目简介

Telegram Dumper 是一款用于下载 Telegram 群组/频道消息和媒体的工具。

### 主要功能

- 下载指定群组/频道的所有消息
- 下载所有媒体文件（照片、视频、音频、文档等）
- 支持增量下载（断点续传）
- 双格式存储（JSON + SQLite）
- 使用 FastTelethon 实现并发下载，速度更快
- 支持获取评论/回复内容
- 自动转换时区（UTC+8 东八区）
- 进度条显示

---

## 环境要求

- Python 3.8+
- Telegram API 账号（API ID 和 API Hash）

---

## 安装配置

### 1. 克隆项目

```bash
git clone https://github.com/atqiyu/telegram-dumper.git
cd telegram-dumper
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置 API

#### 方式一：创建配置文件

复制配置文件模板：

```bash
cp config.yaml.example config.yaml
```

编辑 `config.yaml`，填入你的 API 信息：

```yaml
api_id: 你的API_ID
api_hash: "你的API_HASH"
session_name: "telegram_dumper"
output_dir: "output"
download_concurrency: 8
```

#### 方式二：使用环境变量

```bash
export TG_API_ID=你的API_ID
export TG_API_HASH=你的API_HASH
export TG_SESSION_NAME=telegram_dumper
```

---

## 快速开始

### 1. 查看可用聊天

```bash
python -m src -c config.yaml list
```

输出示例：

```
📋 Available chats:
--------------------------------------------------
  👥 [supergroup] 测试群组 (ID: 3347926724)
  📢 [channel] 测试频道 (ID: 2546071409)
  👤 [private] 用户A (ID: 123456789)
--------------------------------------------------
```

### 2. 下载消息

```bash
python -m src -c config.yaml download <chat_id或username>
```

示例：

```bash
# 按 ID 下载（推荐使用原始 ID，如 3347926724）
python -m src -c config.yaml download 3347926724

# 按用户名下载
python -m src -c config.yaml download test_channel

# 限制下载数量
python -m src -c config.yaml download 3347926724 -l 1000

# 跳过媒体下载（只下载文本）
python -m src -c config.yaml download 3347926724 --skip-media
```

---

## 命令详解

### 下载命令 (download)

```bash
python -m src download <chat> [options]
```

| 参数 | 说明 |
|------|------|
| `chat` | 聊天 ID 或用户名（必填） |

| 选项 | 说明 |
|------|------|
| `-o, --output` | 输出目录（默认：config.yaml 中的 output_dir） |
| `-l, --limit` | 最大下载消息数（默认：全部） |
| `--skip-media` | 跳过媒体下载（只下载文本） |
| `-q, --quiet` | 安静模式（不显示进度条） |
| `-c, --config` | 配置文件路径 |
| `-v, --verbose` | 详细输出模式 |

### 列出聊天命令 (list)

```bash
python -m src list [options]
```

| 选项 | 说明 |
|------|------|
| `-c, --config` | 配置文件路径 |
| `-v, --verbose` | 详细输出模式 |

---

## 输出说明

### 目录结构

下载完成后，在输出目录中会创建以下结构：

```
output/
└── {chat_id}/
    ├── metadata.json          # 聊天元数据
    ├── messages.json          # 所有消息（JSON格式）
    ├── messages.db            # SQLite 数据库
    └── messages/
        ├── {message_id}/
        │   └── media/         # 该消息的媒体文件
        │       ├── photo_xxx.jpg
        │       ├── video_xxx.mp4
        │       └── document_xxx.pdf
        └── group_{group_id}/ # 媒体组共享目录
            ├── photo_xxx.jpg
            └── video_xxx.mp4
```

### 文件命名

- 使用 Telegram 服务器的默认文件名
- 同一媒体组（group_id）的文件保存在 `group_{group_id}` 目录下
- 支持增量下载，相同文件名会自动跳过

### 数据库说明

`messages.db` 包含以下表：

| 表名 | 说明 |
|------|------|
| `messages` | 消息数据 |
| `chats` | 聊天信息 |
| `download_records` | 下载记录 |
| `comments` | 评论数据 |

---

## 增量下载

### 工作原理

程序会进行双重检查判断消息是否已下载：

1. **目录检查**：检查 `output/{chat_id}/messages/{message_id}/` 目录是否存在
2. **数据库检查**：检查 SQLite 中该消息 ID 的记录是否存在

如果两者都存在，则跳过该消息；否则重新下载。

### 断点续传

下载中断后，直接重新运行相同命令即可继续：

```bash
python -m src -c config.yaml download 3347926724
```

---

## 数据字段说明

### 消息表 (messages)

| 字段 | 说明 |
|------|------|
| `id` | 消息ID |
| `chat_id` | 聊天ID |
| `date` | 发送时间（UTC+8 东八区） |
| `text` | 消息文本（格式化） |
| `raw_text` | 原始消息文本（无格式） |
| `media_type` | 媒体类型 (text/photo/video/audio/document) |
| `file_name` | 文件名 |
| `file_path` | 本地文件路径 |
| `group_id` | 媒体组ID |
| `sender_id` | 发送者ID |
| `sender_name` | 发送者名称 |
| `is_reply` | 是否为回复 |
| `reply_to_msg_id` | 回复的消息ID |
| `is_forward` | 是否为转发 |
| `forward_from_chat_id` | 转发来源聊天ID |
| `forward_from_msg_id` | 转发来源消息ID |
| `forward_from_name` | 转发来源名称 |
| `views` | 查看数 |
| `forwards` | 转发数 |
| `replies` | 评论数 |
| `is_discussion` | 是否有评论区 |
| `discussion_chat_id` | 评论区聊天ID |

### 评论表 (comments)

| 字段 | 说明 |
|------|------|
| `id` | 评论ID |
| `chat_id` | 聊天ID |
| `parent_id` | 父消息ID |
| `date` | 发送时间（UTC+8 东八区） |
| `text` | 评论文本 |
| `raw_text` | 原始评论文本 |
| `media_type` | 媒体类型 |
| `sender_id` | 发送者ID |
| `sender_name` | 发送者名称 |
| `views` | 查看数 |

---

## 常见问题

### Q1: 提示 "API_ID and API_HASH must be set"

需要配置 API 信息，详见「配置 API」部分。

### Q2: 首次运行需要手机验证码

是的，首次运行会提示登录。登录成功后，会自动保存会话（session）文件，后续运行无需再次验证。

### Q3: 下载速度慢

项目已集成 FastTelethon 并发下载，默认 8 并发。如需调整，可修改 `config.yaml` 中的 `download_concurrency` 参数。

### Q4: 如何只下载文本不下载媒体

使用 `--skip-media` 选项：

```bash
python -m src -c config.yaml download <chat> --skip-media
```

### Q5: 如何查看已下载的聊天列表

```bash
python -m src -c config.yaml list
```

### Q6: 输入的 Chat ID 格式

推荐使用原始数字 ID（如 `3347926724`），程序会自动处理 Telegram 所需的格式转换。

---

## 技术支持

如有问题，请提交 Issue 或查看项目文档。

GitHub: https://github.com/atqiyu/telegram-dumper
