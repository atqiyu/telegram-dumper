"""
FastTelethon 补丁模块
通过 Monkey Patch 方式为 Telethon 添加并发下载支持
"""
import io
import pathlib
import logging
from telethon import TelegramClient, helpers
from telethon.errors import FileMigrateError

from . import FastTelethon

log = logging.getLogger("FastTelethon.Patch")

# 保存原始的 _download_file 方法
original_download_file = TelegramClient._download_file


async def fast_download_file(
        self: TelegramClient,
        input_location,
        file=None,
        *,
        part_size_kb=None,
        file_size=None,
        progress_callback=None,
        dc_id=None,
        key=None,
        iv=None,
        msg_data=None,
        cdn_redirect=None
):
    """
    快速下载补丁函数
    
    特点:
    - 支持并发下载 (FastTelethon)
    - 自动回退到原生下载 (加密文件、CDN重定向)
    - 支持 DC 迁移错误处理
    """
    # 加密文件 (Secret Chat) 或 CDN 重定向，回退到原生下载
    if key or iv or cdn_redirect:
        return await original_download_file(
            self, input_location, file, part_size_kb=part_size_kb,
            file_size=file_size, progress_callback=progress_callback,
            dc_id=dc_id, key=key, iv=iv, msg_data=msg_data, cdn_redirect=cdn_redirect
        )

    # 处理文件路径
    if isinstance(file, pathlib.Path):
        file = str(file.absolute())

    # 确定写入目标 (内存/文件)
    in_memory = file is None or file is bytes
    if in_memory:
        f = io.BytesIO()
    elif isinstance(file, str):
        helpers.ensure_parent_dir_exists(file)
        f = open(file, 'wb')
    else:
        f = file

    try:
        # 使用 FastTelethon 并发下载
        await FastTelethon.download_file(
            self,
            input_location,
            f,
            file_size=file_size,
            progress_callback=progress_callback,
            dc_id=dc_id
        )

        if callable(getattr(f, 'flush', None)):
            f.flush()

        if in_memory:
            return f.getvalue()
    finally:
        if isinstance(file, str) or in_memory:
            f.close()


# 注入补丁 - 替换 TelegramClient 的底层下载方法
TelegramClient._download_file = fast_download_file
