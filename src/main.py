"""
主入口模块
提供命令行界面 (CLI) 供用户操作
"""
import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

try:
    from tqdm import tqdm
except ImportError:
    tqdm = None

from .config import Config, load_env_config
from .client import TelegramDumperClient
from .downloader import Downloader
from .fast_client import set_connection_count


def setup_logging(verbose: bool = False):
    """设置日志级别"""
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s" if not verbose else "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )


async def run_download(args):
    """执行下载命令"""
    # 加载配置 (优先 config.yaml，其次环境变量)
    config = load_env_config()
    
    if args.config:
        config = Config.load_from_file(args.config)
    
    # 检查必要配置
    if config.api_id == 0 or not config.api_hash:
        print("Error: API_ID and API_HASH must be set via config file or environment variables")
        print("Set TG_API_ID and TG_API_HASH environment variables, or create config.yaml")
        sys.exit(1)
    
    setup_logging(args.verbose)
    
    output_dir = args.output or config.output_dir
    
    print(f"📥 Starting download for chat: {args.chat}")
    print(f"   Output directory: {output_dir}")
    if args.limit:
        print(f"   Message limit: {args.limit}")
    print("-" * 50)
    
    async with TelegramDumperClient(config) as client:
        downloader = Downloader(config, output_dir)
        
        # 进度条
        pbar = None
        if tqdm and not args.quiet:
            pbar = tqdm(total=args.limit if args.limit else 0, 
                       unit="msg", 
                       desc="Downloading",
                       ncols=80,
                       bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]")
        
        def progress_callback(current, message_id, is_group=False, media_type="text", is_downloading=False):
            """
            进度回调函数
            参数:
                current: 当前处理的消息数
                message_id: 消息ID
                is_group: 是否为group消息
                media_type: 媒体类型
                is_downloading: 是否正在下载媒体
            """
            status_text = ""
            if is_group:
                status_text = "[GROUP]"
            elif is_downloading:
                status_text = f"[{media_type.upper()}]"
            else:
                status_text = "[TEXT]"
            
            if pbar:
                if pbar.total == 0:
                    pbar.total = current + 100
                pbar.update(1)
                pbar.set_postfix_str(f"ID:{message_id} {status_text}")
            elif not args.quiet:
                print(f"\r  [{current}] ID:{message_id} {status_text}", end="", flush=True)
        
        result = await downloader.download_chat(
            client,
            args.chat,
            limit=args.limit,
            skip_media=args.skip_media,
            progress_callback=progress_callback
        )
        
        if pbar:
            pbar.close()
        
        print("\n" + "=" * 50)
        print(f"✅ Download completed!")
        print(f"   Chat: {result['chat_title']}")
        print(f"   Messages: {result['messages_downloaded']} downloaded, {result['messages_skipped']} skipped")
        print(f"   Media: {result['media_downloaded']} files")
        print("=" * 50)


async def run_list_chats(args):
    """执行列出聊天命令"""
    config = load_env_config()
    
    if args.config:
        config = Config.load_from_file(args.config)
    
    set_connection_count(config.download_concurrency)
    
    if config.api_id == 0 or not config.api_hash:
        print("Error: API_ID and API_HASH must be set")
        sys.exit(1)
    
    setup_logging(args.verbose)
    
    async with TelegramDumperClient(config) as client:
        print("📋 Available chats:")
        print("-" * 50)
        async for dialog in client.client.iter_dialogs():
            entity = dialog.entity
            chat_id = client._get_chat_id(entity)
            chat_type = client._get_chat_type(entity)
            title = getattr(entity, 'title', '') or f"{entity.first_name} {entity.last_name or ''}"
            
            type_emoji = {
                "channel": "📢",
                "supergroup": "👥",
                "group": "💬",
                "private": "👤"
            }.get(chat_type, "❓")
            
            print(f"  {type_emoji} [{chat_type}] {title} (ID: {chat_id})")
        print("-" * 50)


def main():
    """主函数 - 命令行入口"""
    parser = argparse.ArgumentParser(
        description="Telegram Message Dumper - Download messages and media from Telegram",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s download 3347926724                    Download all messages
  %(prog)s download 3347926724 -l 1000           Download 1000 messages
  %(prog)s download 3347926724 --skip-media       Text only
  %(prog)s list                                   List available chats
        """
    )
    parser.add_argument("-c", "--config", help="Path to config file")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    
    # 子命令
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # 下载命令
    download_parser = subparsers.add_parser("download", help="Download messages from a chat")
    download_parser.add_argument("chat", help="Chat ID or username")
    download_parser.add_argument("-o", "--output", help="Output directory")
    download_parser.add_argument("-l", "--limit", type=int, help="Maximum number of messages to download")
    download_parser.add_argument("--skip-media", action="store_true", help="Skip downloading media")
    download_parser.add_argument("-q", "--quiet", action="store_true", help="Quiet mode (no progress output)")
    
    # 列出聊天命令
    list_parser = subparsers.add_parser("list", help="List available chats")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # 根据子命令执行相应操作
    if args.command == "download":
        asyncio.run(run_download(args))
    elif args.command == "list":
        asyncio.run(run_list_chats(args))


if __name__ == "__main__":
    main()
