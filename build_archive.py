#!/usr/bin/env python3
"""Tumblr-style offline media archive builder (v3.3).

Đọc ảnh/video (và ghi chú .md đi kèm) từ một hoặc nhiều thư mục rồi sinh ra
MỘT file HTML tĩnh, chạy hoàn toàn offline. Cấu hình qua config.toml cạnh script (cần Python 3.11+).

Điểm mới so với v2: đọc kích thước ảnh lúc build (có cache) để trang không bị
nhảy layout, masonry thật, lightbox có zoom/pan, tìm kiếm nhanh hơn, sao lưu
bằng file... Xem `python build_archive.py --help`.
"""
from __future__ import annotations

import sys

if sys.version_info < (3, 11):
    sys.exit(f"build_archive.py cần Python 3.11 trở lên (đang chạy Python {sys.version.split()[0]}).")

import argparse
import base64
import fnmatch
import hashlib
import json
import os
import posixpath
import re
import struct
import time
import tomllib
import webbrowser
import zipfile
import zlib
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from html import escape as html_escape
from pathlib import Path
from typing import NamedTuple
from urllib.parse import quote

VERSION = "3.3"

THEMES = {
    "mocha": {"base":"#1e1e2e","mantle":"#181825","crust":"#11111b","surface0":"#313244","surface1":"#45475a","text":"#cdd6f4","subtext":"#a6adc8","mauve":"#cba6f7","pink":"#f5c2e7","red":"#f38ba8","peach":"#fab387","green":"#a6e3a1","blue":"#89b4fa","lavender":"#b4befe","scheme":"dark"},
    "frappe": {"base":"#303446","mantle":"#292c3c","crust":"#232634","surface0":"#414559","surface1":"#51576d","text":"#c6d0f5","subtext":"#a5adce","mauve":"#ca9ee6","pink":"#f4b8e4","red":"#e78284","peach":"#ef9f76","green":"#a6d189","blue":"#8caaee","lavender":"#babbf1","scheme":"dark"},
    "macchiato": {"base":"#24273a","mantle":"#1e2030","crust":"#181926","surface0":"#363a4f","surface1":"#494d64","text":"#cad3f5","subtext":"#a5adcb","mauve":"#c6a0f6","pink":"#f5bde6","red":"#ed8796","peach":"#f5a97f","green":"#a6da95","blue":"#8aadf4","lavender":"#b7bdf8","scheme":"dark"},
    "latte": {"base":"#eff1f5","mantle":"#e6e9ef","crust":"#dce0e8","surface0":"#ccd0da","surface1":"#bcc0cc","text":"#4c4f69","subtext":"#6c6f85","mauve":"#8839ef","pink":"#ea76cb","red":"#d20f39","peach":"#fe640b","green":"#40a02b","blue":"#1e66f5","lavender":"#7287fd","scheme":"light"},
    "nord": {"base":"#2e3440","mantle":"#272c36","crust":"#242933","surface0":"#3b4252","surface1":"#434c5e","text":"#eceff4","subtext":"#d8dee9","mauve":"#b48ead","pink":"#b48ead","red":"#bf616a","peach":"#d08770","green":"#a3be8c","blue":"#88c0d0","lavender":"#81a1c1","scheme":"dark"},
    "tokyo-night": {"base":"#1a1b26","mantle":"#16161e","crust":"#13131a","surface0":"#24283b","surface1":"#414868","text":"#c0caf5","subtext":"#a9b1d6","mauve":"#bb9af7","pink":"#f7768e","red":"#f7768e","peach":"#ff9e64","green":"#9ece6a","blue":"#7aa2f7","lavender":"#7dcfff","scheme":"dark"},
    "gruvbox": {"base":"#282828","mantle":"#1d2021","crust":"#1d2021","surface0":"#3c3836","surface1":"#504945","text":"#ebdbb2","subtext":"#bdae93","mauve":"#d3869b","pink":"#d3869b","red":"#fb4934","peach":"#fe8019","green":"#b8bb26","blue":"#83a598","lavender":"#8ec07c","scheme":"dark"},
    "rose-pine": {"base":"#191724","mantle":"#1f1d2e","crust":"#191724","surface0":"#26233a","surface1":"#403d52","text":"#e0def4","subtext":"#908caa","mauve":"#c4a7e7","pink":"#ebbcba","red":"#eb6f92","peach":"#f6c177","green":"#9ccfd8","blue":"#31748f","lavender":"#c4a7e7","scheme":"dark"},
    "noir-velvet": {"base":"#151116","mantle":"#1d1820","crust":"#100d12","surface0":"#302733","surface1":"#493b4b","text":"#f1eaf0","subtext":"#b9aab9","mauve":"#d7a8c7","pink":"#edbad6","red":"#e77d91","peach":"#e3b88d","green":"#a8c6ae","blue":"#9eaccf","lavender":"#c8a5d2","scheme":"dark"},
    "oxblood": {"base":"#1a1015","mantle":"#24161d","crust":"#120b10","surface0":"#38232d","surface1":"#543544","text":"#f3e7eb","subtext":"#c2aab4","mauve":"#e0a0b3","pink":"#efabc0","red":"#ec7185","peach":"#e6a16f","green":"#acc5a5","blue":"#9aaed8","lavender":"#d6a5c1","scheme":"dark"},
    "nord-light": {"base":"#eceff4","mantle":"#e5e9f0","crust":"#d8dee9","surface0":"#d8dee9","surface1":"#c4ccd8","text":"#2e3440","subtext":"#4c566a","mauve":"#8f6b91","pink":"#b45b70","red":"#bf616a","peach":"#d08770","green":"#6d8f66","blue":"#5e81ac","lavender":"#81a1c1","scheme":"light"},
    "tokyo-night-light": {"base":"#f5f6fb","mantle":"#eceef6","crust":"#e6e7ed","surface0":"#e6e7ed","surface1":"#d2d6e3","text":"#343b58","subtext":"#565f89","mauve":"#7a5ccc","pink":"#c64375","red":"#c6435f","peach":"#b15c00","green":"#587f20","blue":"#34548a","lavender":"#2c7a91","scheme":"light"},
    "gruvbox-light": {"base":"#fbf1c7","mantle":"#f2e5bc","crust":"#ebdbb2","surface0":"#ebdbb2","surface1":"#d5c4a1","text":"#3c3836","subtext":"#665c54","mauve":"#8f3f71","pink":"#b16286","red":"#9d0006","peach":"#af3a03","green":"#79740e","blue":"#076678","lavender":"#427b58","scheme":"light"},
    "rose-pine-dawn": {"base":"#faf4ed","mantle":"#fffaf3","crust":"#f2e9e1","surface0":"#f2e9e1","surface1":"#dfdad9","text":"#575279","subtext":"#797593","mauve":"#907aa9","pink":"#d7827e","red":"#b4637a","peach":"#ea9d34","green":"#56949f","blue":"#286983","lavender":"#907aa9","scheme":"light"},
    # --- mới ở v3 ---
    "dracula": {"base":"#282a36","mantle":"#21222c","crust":"#191a21","surface0":"#343746","surface1":"#44475a","text":"#f8f8f2","subtext":"#b4b8d0","mauve":"#bd93f9","pink":"#ff79c6","red":"#ff5555","peach":"#ffb86c","green":"#50fa7b","blue":"#8be9fd","lavender":"#d6acff","scheme":"dark"},
    "solarized-dark": {"base":"#002b36","mantle":"#00252f","crust":"#001f27","surface0":"#073642","surface1":"#0f4b5a","text":"#a9b7b8","subtext":"#839496","mauve":"#8a8fdc","pink":"#e0559a","red":"#e5484d","peach":"#d9622b","green":"#98a800","blue":"#3a9be0","lavender":"#2fb3a8","scheme":"dark"},
    "solarized-light": {"base":"#fdf6e3","mantle":"#f5eedb","crust":"#eee8d5","surface0":"#eee8d5","surface1":"#d9d1b8","text":"#4f646b","subtext":"#657b83","mauve":"#6c71c4","pink":"#d33682","red":"#dc322f","peach":"#cb4b16","green":"#7d8f00","blue":"#268bd2","lavender":"#2aa198","scheme":"light"},
    "midnight": {"base":"#000000","mantle":"#0a0a0d","crust":"#000000","surface0":"#17171c","surface1":"#2a2a33","text":"#ececf1","subtext":"#9a9aa8","mauve":"#b69cff","pink":"#ff8ac8","red":"#ff6b81","peach":"#ffb27a","green":"#7ee0a0","blue":"#7db4ff","lavender":"#a5b4ff","scheme":"dark"},
    "sakura": {"base":"#fff5f7","mantle":"#ffeef2","crust":"#fbdfe7","surface0":"#f8dfe7","surface1":"#ecc4d1","text":"#4a3540","subtext":"#7d6470","mauve":"#b83d78","pink":"#dd5b93","red":"#c93a5a","peach":"#c8672a","green":"#4f8c5f","blue":"#3f6fb8","lavender":"#7d5fbd","scheme":"light"},
}

THEME_LABELS = {
    "mocha": "Mocha", "frappe": "Frappe", "macchiato": "Macchiato", "latte": "Latte", "nord": "Nord",
    "tokyo-night": "Tokyo Night", "gruvbox": "Gruvbox", "rose-pine": "Rose Pine", "noir-velvet": "Noir Velvet",
    "oxblood": "Oxblood", "nord-light": "Nord Light", "tokyo-night-light": "Tokyo Night Light",
    "gruvbox-light": "Gruvbox Light", "rose-pine-dawn": "Rosé Pine Dawn", "dracula": "Dracula",
    "solarized-dark": "Solarized Dark", "solarized-light": "Solarized Light", "midnight": "Midnight (AMOLED)",
    "sakura": "Sakura",
}

# (viewBox, nội dung) — sprite dùng chung cho toàn trang, không cần font icon.
ICONS = {
    "heart": ("0 0 24 24", '<path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/>'),
    "search": ("0 0 24 24", '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>'),
    "grid": ("0 0 24 24", '<rect width="7" height="7" x="3" y="3" rx="1"/><rect width="7" height="7" x="14" y="3" rx="1"/><rect width="7" height="7" x="14" y="14" rx="1"/><rect width="7" height="7" x="3" y="14" rx="1"/>'),
    "rows": ("0 0 24 24", '<rect width="18" height="7" x="3" y="3" rx="1"/><rect width="18" height="7" x="3" y="14" rx="1"/>'),
    "shuffle": ("0 0 24 24", '<path d="M2 18h1.4c1.3 0 2.5-.6 3.3-1.7l6.1-8.6c.7-1.1 2-1.7 3.3-1.7H22"/><path d="m18 2 4 4-4 4"/><path d="M2 6h1.9c1.5 0 2.9.9 3.6 2.2"/><path d="M22 18h-5.9c-1.3 0-2.6-.7-3.3-1.8l-.5-.8"/><path d="m18 14 4 4-4 4"/>'),
    "download": ("0 0 24 24", '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m7 10 5 5 5-5"/><path d="M12 15V3"/>'),
    "upload": ("0 0 24 24", '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m17 8-5-5-5 5"/><path d="M12 3v12"/>'),
    "ext": ("0 0 24 24", '<path d="M15 3h6v6"/><path d="M10 14 21 3"/><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>'),
    "full": ("0 0 24 24", '<path d="M8 3H5a2 2 0 0 0-2 2v3"/><path d="M21 8V5a2 2 0 0 0-2-2h-3"/><path d="M3 16v3a2 2 0 0 0 2 2h3"/><path d="M16 21h3a2 2 0 0 0 2-2v-3"/>'),
    "play": ("0 0 24 24", '<polygon points="7 4 20 12 7 20 7 4"/>'),
    "pause": ("0 0 24 24", '<rect x="14" y="4" width="4" height="16" rx="1"/><rect x="6" y="4" width="4" height="16" rx="1"/>'),
    "zin": ("0 0 24 24", '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/><path d="M11 8v6"/><path d="M8 11h6"/>'),
    "zout": ("0 0 24 24", '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/><path d="M8 11h6"/>'),
    "info": ("0 0 24 24", '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>'),
    "x": ("0 0 24 24", '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>'),
    "left": ("0 0 24 24", '<path d="m15 18-6-6 6-6"/>'),
    "right": ("0 0 24 24", '<path d="m9 18 6-6-6-6"/>'),
    "filter": ("0 0 24 24", '<path d="M3 6h18"/><path d="M7 12h10"/><path d="M10 18h4"/>'),
    "sliders": ("0 0 24 24", '<path d="M4 6h9m4 0h3M4 12h3m4 0h9M4 18h9m4 0h3"/><circle cx="15" cy="6" r="2"/><circle cx="9" cy="12" r="2"/><circle cx="15" cy="18" r="2"/>'),
    "up": ("0 0 24 24", '<path d="m5 12 7-7 7 7"/><path d="M12 19V5"/>'),
    "folder": ("0 0 24 24", '<path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/>'),
    "image": ("0 0 20 20", '<rect x="2.5" y="3" width="15" height="14" rx="3"/><circle cx="7" cy="8" r="1.4"/><path d="m4 15 4-4 2.4 2.2 2.1-2 3.5 3.8"/>'),
    "gif": ("0 0 20 20", '<rect x="1.5" y="3.5" width="17" height="13" rx="3"/><path d="M8 8.2a2.6 2.6 0 1 0 .1 3.6H8v-1.6h1.8"/><path d="M12 8v5m2-5h3m-3 0v5"/>'),
    "video": ("0 0 20 20", '<rect x="2" y="4" width="16" height="12" rx="3"/><path d="m8 7 5 3-5 3z"/>'),
    "stack": ("0 0 20 20", '<rect x="5" y="2.5" width="12" height="12" rx="2.5"/><path d="M3 6v10.5A1.5 1.5 0 0 0 4.5 18H15"/>'),
    "help": ("0 0 24 24", '<circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><path d="M12 17h.01"/>'),
    "palette": ("0 0 24 24", '<circle cx="13.5" cy="6.5" r=".8"/><circle cx="17.5" cy="10.5" r=".8"/><circle cx="8.5" cy="7.5" r=".8"/><circle cx="6.5" cy="12.5" r=".8"/><path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10c.93 0 1.65-.75 1.65-1.69 0-.44-.18-.84-.44-1.13-.29-.29-.44-.65-.44-1.13a1.64 1.64 0 0 1 1.67-1.67h2c3.05 0 5.55-2.5 5.55-5.55C21.97 6.01 17.46 2 12 2z"/>'),
    "copy": ("0 0 24 24", '<rect width="14" height="14" x="8" y="8" rx="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/>'),
    "check": ("0 0 24 24", '<path d="M20 6 9 17l-5-5"/>'),
    "file": ("0 0 24 24", '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M10 9H8"/><path d="M16 13H8"/><path d="M16 17H8"/>'),
    "link": ("0 0 24 24", '<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>'),
    "minus": ("0 0 24 24", '<path d="M5 12h14"/>'),
    "plus": ("0 0 24 24", '<path d="M5 12h14"/><path d="M12 5v14"/>'),
    "package": ("0 0 24 24", '<path d="m7.5 4.27 9 5.15"/><path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/><path d="m3.3 7 8.7 5 8.7-5"/><path d="M12 22V12"/>'),
    "bookmark": ("0 0 24 24", '<path d="m19 21-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16z"/>'),
    "pencil": ("0 0 24 24", '<path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/><path d="m15 5 4 4"/>'),
    "trash": ("0 0 24 24", '<path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/>'),
}

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif", ".bmp", ".svg", ".apng", ".jxl", ".heic", ".heif"}
VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov", ".m4v", ".ogv"}
MEDIA_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS
IGNORED_MEDIA_DIRS = {"@eaDir", "__MACOSX"}
KIND_IMAGE, KIND_GIF, KIND_VIDEO = 0, 1, 2
TUMBLR_MEDIA_SEQUENCE = re.compile(r"^(tumblr_.+?)o(\d+)(?:_r\d+)?_\d+$", re.IGNORECASE)
TUMBLR_ID = re.compile(r"^(tumblr_[A-Za-z0-9]+)(?:_|$)", re.IGNORECASE)
NUMERIC_MEDIA_SEQUENCE = re.compile(r"^(\d+)_\d+$")
NAMED_MEDIA_SEQUENCE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9_-]*)\s+(\d+)\s+(.+)$")
CACHE_FILENAME = ".build_archive_cache.json"


# --------------------------------------------------------------------------- #
# Tiện ích chung
# --------------------------------------------------------------------------- #
def natural_key(value: str):
    return [(1, int(part)) if part.isdigit() else (0, part.casefold())
            for part in re.split(r"(\d+)", value)]


def created_time(stat: os.stat_result) -> float:
    return float(getattr(stat, "st_birthtime", stat.st_ctime))


def media_kind(name: str) -> int:
    suffix = os.path.splitext(name)[1].casefold()
    if suffix in VIDEO_EXTENSIONS:
        return KIND_VIDEO
    if suffix == ".gif":
        return KIND_GIF
    return KIND_IMAGE


def js_json(value: object) -> str:
    """JSON an toàn để nhúng trong <script> (không thể thoát khỏi thẻ script)."""
    text = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return (text.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
                .replace("\u2028", "\\u2028").replace("\u2029", "\\u2029"))


def image_group_id(filename: str) -> str:
    """Group Tumblr image sequence files by their post id.

    Tumblr's ``o1``, ``o2`` suffix identifies a post's media item; optional
    ``_rN`` and size suffixes identify variants. Numeric archive names such
    as ``128635952498_0.jpg`` use ``_<index>`` for media in one post. Names
    such as ``1h5bjv8 01 Cute Asian.jpg`` share a group by id and title.
    Other filenames are grouped only by their complete stem.
    """
    name = posixpath.basename(filename)
    stem = os.path.splitext(name)[0]
    match = TUMBLR_MEDIA_SEQUENCE.match(stem)
    if match:
        return match.group(1).casefold()
    match = TUMBLR_ID.match(name)
    if match:
        return match.group(1).casefold()
    match = NAMED_MEDIA_SEQUENCE.match(stem)
    if match:
        series_id, _sequence, title = match.groups()
        normalized_title = " ".join(title.split()).casefold()
        return f"{series_id.casefold()} {normalized_title}"
    sequence = NUMERIC_MEDIA_SEQUENCE.match(stem)
    if sequence:
        return f"numeric-post-{sequence.group(1)}"
    return stem


# --------------------------------------------------------------------------- #
# Quét thư mục (một lượt duy nhất, dùng os.scandir nên stat gần như miễn phí)
# --------------------------------------------------------------------------- #
class IgnoreRules:
    """Quy tắc bỏ qua thư mục (không quét vào bên trong).

    Mẫu không có "/"  → so khớp TÊN thư mục ở mọi cấp (vd. "Thumbs", "_old*").
    Mẫu có "/"        → so khớp đường dẫn tương đối tính từ thư mục media (vd. "Anime/2023", "*/private").
    Mẫu là đường dẫn tuyệt đối hoặc bắt đầu bằng "~" → bỏ qua đúng thư mục đó và mọi thứ bên trong.
    Ký tự đại diện kiểu shell (* ? [abc]); không phân biệt hoa thường.
    """

    def __init__(self, patterns=()) -> None:
        self.names: list[str] = []
        self.paths: list[str] = []
        self.absolute: list[str] = []
        self.skipped = 0
        for raw in patterns:
            pattern = str(raw).strip().replace("\\", "/")
            while pattern.startswith("./"):
                pattern = pattern[2:]
            pattern = pattern.rstrip("/")
            if not pattern:
                continue
            expanded = os.path.expanduser(pattern)
            if os.path.isabs(expanded) or re.match(r"^[A-Za-z]:/", pattern):
                self.absolute.append(os.path.normcase(os.path.realpath(expanded)))
            elif "/" in pattern:
                self.paths.append(pattern.casefold())
            else:
                self.names.append(pattern.casefold())

    def __bool__(self) -> bool:
        return bool(self.names or self.paths or self.absolute)

    def matches(self, name: str, rel: str, full: str) -> bool:
        hit = False
        folded = name.casefold()
        if any(fnmatch.fnmatchcase(folded, p) for p in self.names):
            hit = True
        elif self.paths:
            rel_folded = rel.casefold()
            hit = any(fnmatch.fnmatchcase(rel_folded, p) for p in self.paths)
        if not hit and self.absolute:
            real = os.path.normcase(os.path.realpath(full))
            hit = any(real == a or real.startswith(a + os.sep) for a in self.absolute)
        if hit:
            self.skipped += 1
        return hit


class MediaFile(NamedTuple):
    rel: str        # đường dẫn tương đối theo thư mục media, dạng posix
    path: Path
    size: int
    created: float
    mtime_ns: int
    zip: tuple | None = None   # (đường dẫn file nén tương đối, đường dẫn bên trong, chỉ số entry) nếu media nằm trong .zip/.cbz


class ArchiveFile(NamedTuple):
    rel: str
    path: Path
    size: int
    created: float
    mtime_ns: int


ZIP_EXTENSIONS = {".zip", ".cbz"}
SUPPORTED_ZIP_METHODS = (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)   # unzipit chỉ giải nén được store + deflate
UNZIPIT_CDN_URL = "https://cdn.jsdelivr.net/npm/unzipit@1.4.3/dist/unzipit.module.js"
UNZIPIT_LOCAL_CANDIDATES = ("unzipit.module.js", "unzipit.module.min.js", "unzipit.min.js", "unzipit.js")


def scan_folder(root: Path, ignore: IgnoreRules | None = None, zip_support: bool = False) -> tuple[list[MediaFile], dict[str, Path], list[ArchiveFile]]:
    """Trả về (media sắp xếp tự nhiên, bảng ghi chú .md theo tên bỏ đuôi, danh sách file .zip/.cbz)."""
    media: list[MediaFile] = []
    archives: list[ArchiveFile] = []
    notes: dict[str, Path] = {}
    visited: set[str] = set()
    stack: list[tuple[str, str]] = [(str(root), "")]
    while stack:
        directory, prefix = stack.pop()
        try:
            real = os.path.realpath(directory)
            if real in visited:  # chống vòng lặp symlink
                continue
            visited.add(real)
            iterator = os.scandir(directory)
        except OSError:
            continue
        with iterator:
            for entry in iterator:
                name = entry.name
                if name.startswith(".") or name in IGNORED_MEDIA_DIRS:
                    continue
                rel = prefix + name
                try:
                    if entry.is_dir():
                        if ignore is not None and ignore.matches(name, rel, entry.path):
                            continue
                        stack.append((entry.path, rel + "/"))
                        continue
                    if not entry.is_file():
                        continue
                    suffix = os.path.splitext(name)[1].casefold()
                    if suffix in MEDIA_EXTENSIONS:
                        st = entry.stat()
                        media.append(MediaFile(rel, Path(entry.path), st.st_size, created_time(st), st.st_mtime_ns))
                    elif suffix == ".md":
                        notes[os.path.splitext(rel)[0].casefold()] = Path(entry.path)
                    elif zip_support and suffix in ZIP_EXTENSIONS:
                        if ignore is not None and ignore.matches(name, rel, entry.path):
                            continue
                        st = entry.stat()
                        archives.append(ArchiveFile(rel, Path(entry.path), st.st_size, created_time(st), st.st_mtime_ns))
                except OSError:
                    continue
    media.sort(key=lambda m: natural_key(m.rel))
    archives.sort(key=lambda a: natural_key(a.rel))
    return media, notes, archives


def folder_has_media(root: Path, ignore: IgnoreRules | None = None, zip_support: bool = False) -> bool:
    """Kiểm tra nhanh (dừng ngay khi gặp file đầu tiên) xem thư mục có media không."""
    for current, dirs, files in os.walk(root):
        rel_current = os.path.relpath(current, root).replace(os.sep, "/")
        kept = []
        for d in dirs:
            if d.startswith(".") or d in IGNORED_MEDIA_DIRS:
                continue
            rel = d if rel_current == "." else f"{rel_current}/{d}"
            if ignore is not None and ignore.matches(d, rel, os.path.join(current, d)):
                continue
            kept.append(d)
        dirs[:] = kept
        for name in files:
            suffix = os.path.splitext(name)[1].casefold()
            if not name.startswith(".") and (suffix in MEDIA_EXTENSIONS or (zip_support and suffix in ZIP_EXTENSIONS)):
                return True
    return False


def group_media(files: list[MediaFile], zip_mode: str = "folder") -> list[tuple[str, list[MediaFile]]]:
    """Gom các file cùng một bài. Khóa nhóm giữ nguyên như v2 để ID bài không đổi.
    Media trong .zip/.cbz: zip_mode="folder" coi file nén như thư mục ảo (gom theo tên như file thường);
    zip_mode="archive" gom MỌI media của một file nén thành một bài."""
    groups: dict[str, list[MediaFile]] = {}
    for media in files:
        if media.zip is not None and zip_mode == "archive":
            groups.setdefault(f"{media.zip[0]}::@archive", []).append(media)
            continue
        group_id = image_group_id(posixpath.basename(media.rel)).casefold()
        parent = posixpath.dirname(media.rel) or "."
        key = f"{parent}::{group_id}" if parent != "." else group_id
        groups.setdefault(key, []).append(media)
    return list(groups.items())


# --------------------------------------------------------------------------- #
# File nén .zip/.cbz như thư mục ảo: chỉ đọc danh sách (không giải nén ra đĩa)
# --------------------------------------------------------------------------- #
def _zip_entry_name(info: zipfile.ZipInfo) -> str:
    """Tên entry đã chuẩn hóa. Zip không bật cờ UTF-8 bị zipfile giải mã cp437 → thử khôi phục UTF-8 (trường hợp phổ biến)."""
    name = info.filename
    if not info.flag_bits & 0x800:
        try:
            name = name.encode("cp437").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass
    return name.replace("\\", "/")


def _zip_entry_time(info: zipfile.ZipInfo, fallback: float) -> float:
    try:
        return datetime(*info.date_time).timestamp()
    except (ValueError, OverflowError, OSError):
        return fallback


def list_archive_media(archive: ArchiveFile, ignore: IgnoreRules | None, warn) -> tuple[list[MediaFile], dict]:
    """Liệt kê ảnh/video bên trong một .zip/.cbz. Đường dẫn ảo: "<file nén>/<đường dẫn bên trong>"."""
    stats = {"encrypted": 0, "unsupported": 0, "bad": 0}
    try:
        with zipfile.ZipFile(archive.path) as handle:
            infos = handle.infolist()
    except (zipfile.BadZipFile, OSError, NotImplementedError, ValueError, RuntimeError, EOFError) as exc:
        warn(f"Bỏ qua file nén {archive.rel}: {exc}")
        stats["bad"] = 1
        return [], stats
    dir_cache: dict[str, bool] = {}

    def dir_allowed(dirs: tuple[str, ...]) -> bool:
        key = "/".join(dirs)
        cached = dir_cache.get(key)
        if cached is not None:
            return cached
        segment = dirs[-1]
        allowed = not segment.startswith(".") and segment not in IGNORED_MEDIA_DIRS
        if allowed and len(dirs) > 1:
            allowed = dir_allowed(dirs[:-1])
        if allowed and ignore is not None:
            allowed = not ignore.matches(segment, f"{archive.rel}/{key}", f"{archive.path}/{key}")
        dir_cache[key] = allowed
        return allowed

    media: list[MediaFile] = []
    for index, info in enumerate(infos):
        if info.is_dir():
            continue
        name = _zip_entry_name(info)
        while name.startswith("./"):
            name = name[2:]
        parts = [p for p in name.split("/") if p]
        if not parts or name.startswith("/") or ".." in parts:
            continue
        base = parts[-1]
        if base.startswith(".") or os.path.splitext(base)[1].casefold() not in MEDIA_EXTENSIONS:
            continue
        if len(parts) > 1 and not dir_allowed(tuple(parts[:-1])):
            continue
        if info.flag_bits & 0x1:
            stats["encrypted"] += 1
            continue
        if info.compress_type not in SUPPORTED_ZIP_METHODS:
            stats["unsupported"] += 1
            continue
        internal = "/".join(parts)
        media.append(MediaFile(f"{archive.rel}/{internal}", archive.path, info.file_size,
                               _zip_entry_time(info, archive.created), archive.mtime_ns, (archive.rel, internal, index)))
    if stats["encrypted"] or stats["unsupported"]:
        warn(f"{archive.rel}: bỏ qua {stats['encrypted']} file có mật khẩu và {stats['unsupported']} file nén bằng phương pháp không hỗ trợ (chỉ hỗ trợ store/deflate).")
    return media, stats


def prepare_unzipit_script(source: str) -> str | None:
    """Biến unzipit (ES module hoặc UMD) thành đoạn JS thường gán window.unzipit để nhúng inline.
    Nhúng inline là cách duy nhất chạy được khi mở bằng file:// (trình duyệt chặn <script type=module src=file://…>).
    Trả về None nếu file có cú pháp không chuyển được (khi đó dùng CDN)."""
    text = source
    if re.search(r"^\s*import\s|\bimport\.meta\b|\bimport\s*\(", text, re.M):
        return None
    if re.search(r"\bexport\s+(?:default|const|let|var|function|class|async)\b|\bexport\s*\*", text):
        return None
    lists = list(re.finditer(r"\bexport\s*\{([^}]*)\}\s*;?", text))
    if lists:
        pairs: list[tuple[str, str]] = []
        for match in lists:
            for part in match.group(1).split(","):
                part = part.strip()
                if not part:
                    continue
                parsed = re.fullmatch(r"(\w+)(?:\s+as\s+(\w+))?", part)
                if not parsed:
                    return None
                pairs.append((parsed.group(2) or parsed.group(1), parsed.group(1)))
        if not pairs:
            return None
        text = re.sub(r"\bexport\s*\{[^}]*\}\s*;?", "", text)
        assign = "window.unzipit={" + ",".join(a if a == b else f"{a}:{b}" for a, b in pairs) + "};"
        text = "(()=>{\n" + text + "\n" + assign + "\n})();"
    return text.replace("</script", "<\\/script")


# --------------------------------------------------------------------------- #
# Đọc kích thước ảnh từ header (không cần Pillow) + cache
# --------------------------------------------------------------------------- #
def _exif_orientation(tiff: bytes) -> int:
    if len(tiff) < 8:
        return 1
    endian = "<" if tiff[:2] == b"II" else ">" if tiff[:2] == b"MM" else None
    if endian is None:
        return 1
    try:
        offset = struct.unpack(endian + "I", tiff[4:8])[0]
        count = struct.unpack(endian + "H", tiff[offset:offset + 2])[0]
        for index in range(count):
            entry = tiff[offset + 2 + index * 12: offset + 14 + index * 12]
            if len(entry) < 12:
                break
            tag = struct.unpack(endian + "H", entry[:2])[0]
            if tag == 0x0112:
                return struct.unpack(endian + "H", entry[8:10])[0]
    except struct.error:
        pass
    return 1


def _jpeg_size(handle) -> tuple[int, int] | None:
    handle.seek(2)
    orientation = 1
    for _ in range(512):  # giới hạn số segment để tránh file hỏng
        byte = handle.read(1)
        if not byte:
            return None
        if byte != b"\xff":
            continue
        while byte == b"\xff":
            byte = handle.read(1)
        if not byte:
            return None
        marker = byte[0]
        if marker == 0x00 or marker == 0x01 or 0xD0 <= marker <= 0xD8:
            continue
        if marker in (0xD9, 0xDA):
            return None
        raw = handle.read(2)
        if len(raw) < 2:
            return None
        length = struct.unpack(">H", raw)[0]
        if length < 2:
            return None
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
            data = handle.read(5)
            if len(data) < 5:
                return None
            _precision, height, width = struct.unpack(">BHH", data)
            return (height, width) if orientation in (5, 6, 7, 8) else (width, height)
        if marker == 0xE1:
            data = handle.read(length - 2)
            if data[:6] == b"Exif\x00\x00":
                orientation = _exif_orientation(data[6:])
        else:
            handle.seek(length - 2, 1)
    return None


def _webp_size(handle) -> tuple[int, int] | None:
    handle.seek(12)
    fourcc = handle.read(4)
    handle.read(4)
    if fourcc == b"VP8X":
        data = handle.read(10)
        if len(data) == 10:
            return 1 + int.from_bytes(data[4:7], "little"), 1 + int.from_bytes(data[7:10], "little")
    elif fourcc == b"VP8L":
        data = handle.read(5)
        if len(data) == 5:
            bits = int.from_bytes(data[1:5], "little")
            return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
    elif fourcc == b"VP8 ":
        data = handle.read(10)
        if len(data) == 10:
            return struct.unpack("<H", data[6:8])[0] & 0x3FFF, struct.unpack("<H", data[8:10])[0] & 0x3FFF
    return None


def _isobmff_size(handle) -> tuple[int, int] | None:
    """AVIF/HEIC: lấy hộp `ispe` lớn nhất trong 128 KB đầu."""
    handle.seek(0)
    data = handle.read(131072)
    best: tuple[int, int] | None = None
    position = data.find(b"ispe")
    while position != -1:
        chunk = data[position + 8: position + 16]
        if len(chunk) == 8:
            width, height = struct.unpack(">II", chunk)
            if width and height and (best is None or width * height > best[0] * best[1]):
                best = (width, height)
        position = data.find(b"ispe", position + 4)
    return best


def _svg_size(handle) -> tuple[int, int] | None:
    handle.seek(0)
    head = handle.read(4096)
    match = re.search(rb'viewBox\s*=\s*["\']\s*[-\d.]+[\s,]+[-\d.]+[\s,]+([\d.]+)[\s,]+([\d.]+)', head)
    if not match:
        return None
    try:
        width, height = float(match.group(1)), float(match.group(2))
    except ValueError:
        return None
    if width <= 0 or height <= 0:
        return None
    return max(1, round(width / height * 1000)), 1000  # chỉ cần tỉ lệ


def _probe_handle(handle, suffix: str) -> tuple[int, int] | None:
    """Đọc kích thước từ một file-like (file thường hoặc entry trong zip)."""
    try:
        head = handle.read(32)
        if head.startswith(b"\x89PNG\r\n\x1a\n") and head[12:16] == b"IHDR":
            return struct.unpack(">II", head[16:24])
        if head[:6] in (b"GIF87a", b"GIF89a"):
            return struct.unpack("<HH", head[6:10])
        if head[:2] == b"\xff\xd8":
            return _jpeg_size(handle)
        if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
            return _webp_size(handle)
        if head[:2] == b"BM" and len(head) >= 26:
            width, height = struct.unpack("<ii", head[18:26])
            return abs(width), abs(height)
        if head[4:8] == b"ftyp":
            return _isobmff_size(handle)
        if suffix == ".svg":
            return _svg_size(handle)
    except (OSError, struct.error, ValueError, EOFError, RuntimeError, NotImplementedError, zlib.error, zipfile.BadZipFile):
        return None
    return None


def probe_size(path: Path) -> tuple[int, int] | None:
    """Kích thước hiển thị (đã tính xoay EXIF) hoặc None nếu không đọc được."""
    try:
        with open(path, "rb") as handle:
            return _probe_handle(handle, path.suffix.casefold())
    except OSError:
        return None


def media_key(media: MediaFile) -> str:
    """Khóa duy nhất cho cache/kết quả kích thước (entry trong zip không trùng với file nén)."""
    return str(media.path) if media.zip is None else f"{media.path}!/{media.zip[2]}:{media.zip[1]}"


def _probe_zip_group(path: Path, items: list[MediaFile]) -> list[tuple[MediaFile, tuple[int, int] | None]]:
    results: list[tuple[MediaFile, tuple[int, int] | None]] = []
    try:
        with zipfile.ZipFile(path) as handle:
            infos = handle.infolist()
            for media in items:
                dims = None
                try:
                    with handle.open(infos[media.zip[2]]) as member:
                        dims = _probe_handle(member, os.path.splitext(media.rel)[1].casefold())
                except (OSError, IndexError, RuntimeError, NotImplementedError, zipfile.BadZipFile, zlib.error, EOFError):
                    dims = None
                results.append((media, dims))
    except (zipfile.BadZipFile, OSError, NotImplementedError, ValueError, RuntimeError, EOFError):
        return [(media, None) for media in items]
    return results


class SizeCache:
    """Cache kích thước ảnh theo (đường dẫn, dung lượng, mtime) → lần build sau gần như tức thì."""
    VERSION = 2

    def __init__(self, path: Path | None) -> None:
        self.path = path
        self.entries: dict[str, list[int]] = {}
        self.used: dict[str, list[int]] = {}
        self.extra: dict[str, str] = {}
        self.extra_dirty = False
        if path is not None:
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(raw, dict) and raw.get("v") == self.VERSION and isinstance(raw.get("f"), dict):
                    self.entries = raw["f"]
                    if isinstance(raw.get("x"), dict):
                        self.extra = {k: v for k, v in raw["x"].items() if isinstance(v, str)}
            except (OSError, ValueError):
                pass

    def lookup(self, key: str, size: int, mtime_ns: int) -> tuple[int, int] | None:
        entry = self.entries.get(key)
        if entry and entry[0] == size and entry[1] == mtime_ns:
            self.used[key] = entry
            return entry[2], entry[3]
        return None

    def store(self, key: str, size: int, mtime_ns: int, width: int, height: int) -> None:
        self.used[key] = [size, mtime_ns, width, height]

    def save(self, scanned_prefixes: list[str]) -> None:
        if self.path is None:
            return
        # Giữ mục của thư mục khác; với thư mục vừa quét chỉ giữ file còn tồn tại.
        merged = {k: v for k, v in self.entries.items()
                  if not any(k.startswith(prefix) for prefix in scanned_prefixes)}
        merged.update(self.used)
        if merged == self.entries and not self.extra_dirty:
            return
        try:
            self.path.write_text(json.dumps({"v": self.VERSION, "f": merged, "x": self.extra}, separators=(",", ":")), encoding="utf-8")
            self.entries = merged
            self.extra_dirty = False
        except OSError:
            pass


def probe_media_sizes(files: list[MediaFile], cache: SizeCache, workers: int) -> dict[str, tuple[int, int]]:
    result: dict[str, tuple[int, int]] = {}
    todo: list[MediaFile] = []
    todo_zip: dict[str, list[MediaFile]] = {}
    for media in files:
        if media_kind(media.rel) == KIND_VIDEO:
            continue
        key = media_key(media)
        hit = cache.lookup(key, media.size, media.mtime_ns)
        if hit is not None:
            result[key] = hit
        elif media.zip is None:
            todo.append(media)
        else:
            todo_zip.setdefault(str(media.path), []).append(media)
    if todo or todo_zip:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for media, dims in zip(todo, pool.map(lambda m: probe_size(m.path), todo)):
                width, height = dims or (0, 0)
                cache.store(media_key(media), media.size, media.mtime_ns, width, height)
                result[media_key(media)] = (width, height)
            for group in pool.map(lambda item: _probe_zip_group(Path(item[0]), item[1]), todo_zip.items()):
                for media, dims in group:
                    width, height = dims or (0, 0)
                    cache.store(media_key(media), media.size, media.mtime_ns, width, height)
                    result[media_key(media)] = (width, height)
    return result


# --------------------------------------------------------------------------- #
# Icon ứng dụng (apple-touch-icon): dùng icon của bạn hoặc tự vẽ icon mặc định
# --------------------------------------------------------------------------- #
APP_ICON_SIZE = 180
APP_ICON_CANDIDATES = ("apple-touch-icon.png", "app-icon.png", "icon.png")
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
STATUS_BAR_STYLES = ("default", "black", "black-translucent")


def _hex_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def _mix(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[float, float, float]:
    return a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t


def _png_encode(width: int, height: int, rgb: bytes) -> bytes:
    stride = width * 3
    raw = b"".join(b"\x00" + rgb[y * stride:(y + 1) * stride] for y in range(height))

    def chunk(tag: bytes, data: bytes) -> bytes:
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    return (PNG_SIGNATURE + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def render_default_icon(top: str, bottom: str, ink: str, size: int = APP_ICON_SIZE) -> bytes:
    """Vẽ icon 'chồng ảnh' bằng Python thuần (không cần Pillow), khử răng cưa 2×2. Không trong suốt để iOS không tô nền đen."""
    c_top, c_bottom, c_ink = _hex_rgb(top), _hex_rgb(bottom), _hex_rgb(ink)
    white = (252, 252, 254)
    ss = 2
    rows = bytearray()
    for y in range(size):
        for x in range(size):
            acc_r = acc_g = acc_b = 0.0
            for sy in range(ss):
                py = (y + (sy + 0.5) / ss) / size
                for sx in range(ss):
                    px = (x + (sx + 0.5) / ss) / size
                    r, g, b = _mix(c_top, c_bottom, (px + py) / 2)
                    # thẻ ảnh phía sau (mờ)
                    dx = max(abs(px - 0.43) - 0.18, 0.0)
                    dy = max(abs(py - 0.43) - 0.20, 0.0)
                    if dx * dx + dy * dy <= 0.07 * 0.07:
                        r, g, b = r * 0.5 + 127.5, g * 0.5 + 127.5, b * 0.5 + 127.5
                    # thẻ ảnh phía trước
                    dx = max(abs(px - 0.54) - 0.18, 0.0)
                    dy = max(abs(py - 0.56) - 0.20, 0.0)
                    if dx * dx + dy * dy <= 0.07 * 0.07:
                        r, g, b = white
                        if (px - 0.635) ** 2 + (py - 0.45) ** 2 <= 0.045 ** 2:      # mặt trời
                            r, g, b = _mix(c_top, c_bottom, 0.5)
                        elif py <= 0.735 and py >= 0.60 + abs(px - 0.64) * 1.25:      # núi nhỏ (phía sau)
                            r, g, b = _mix(c_ink, c_top, 0.5)
                        if py <= 0.735 and py >= 0.52 + abs(px - 0.50) * 1.6:         # núi lớn (phía trước)
                            r, g, b = c_ink
                    acc_r += r
                    acc_g += g
                    acc_b += b
            n = ss * ss
            rows += bytes((round(acc_r / n), round(acc_g / n), round(acc_b / n)))
    return _png_encode(size, size, bytes(rows))


def _icon_with_pillow(data: bytes, background: str, size: int = APP_ICON_SIZE) -> bytes | None:
    """Nếu có Pillow: cắt vuông, thu về 180×180, dán lên nền đặc (iOS hiện nền trong suốt thành đen)."""
    try:
        from PIL import Image
        import io
    except ImportError:
        return None
    try:
        with Image.open(io.BytesIO(data)) as source:
            image = source.convert("RGBA")
        side = min(image.size)
        left, top = (image.width - side) // 2, (image.height - side) // 2
        image = image.crop((left, top, left + side, top + side)).resize((size, size), Image.LANCZOS)
        canvas = Image.new("RGB", (size, size), _hex_rgb(background))
        canvas.paste(image, mask=image.split()[3])
        out = io.BytesIO()
        canvas.save(out, "PNG", optimize=True)
        return out.getvalue()
    except (OSError, ValueError):
        return None


def prepare_app_icon(icon_path: Path | None, theme: dict, cache: SizeCache, warn) -> tuple[bytes, str]:
    """Trả về (bytes PNG, nguồn) với nguồn là 'custom' hoặc 'default'."""
    if icon_path is not None:
        if not icon_path.is_file():
            warn(f"Không tìm thấy app_icon: {icon_path} — dùng icon mặc định.")
        else:
            try:
                data = icon_path.read_bytes()
            except OSError as exc:
                warn(f"Không đọc được app_icon ({exc}) — dùng icon mặc định.")
            else:
                converted = _icon_with_pillow(data, theme["base"])
                if converted is not None:
                    return converted, "custom"
                if data.startswith(PNG_SIGNATURE):
                    if probe_size(icon_path) != (APP_ICON_SIZE, APP_ICON_SIZE):
                        warn(f"app_icon nên là PNG {APP_ICON_SIZE}×{APP_ICON_SIZE} không trong suốt "
                             f"(cài Pillow để tự chuyển đổi); vẫn dùng file này.")
                    return data, "custom"
                warn("app_icon cần là file PNG (hoặc cài Pillow để dùng JPG/WEBP/…) — dùng icon mặc định.")
    top, bottom = theme["mauve"], theme["blue"]
    ink = "#%02x%02x%02x" % tuple(round(v) for v in _mix(_hex_rgb(theme["crust"]), _hex_rgb(theme["mauve"]), 0.35))
    key = "icon1:" + hashlib.sha1(f"{top}{bottom}{ink}{APP_ICON_SIZE}".encode()).hexdigest()[:16]
    cached = cache.extra.get(key)
    if cached:
        try:
            return base64.b64decode(cached), "default"
        except ValueError:
            pass
    png = render_default_icon(top, bottom, ink)
    cache.extra = {k: v for k, v in cache.extra.items() if not k.startswith("icon1:")}
    cache.extra[key] = base64.b64encode(png).decode("ascii")
    cache.extra_dirty = True
    return png, "default"


# --------------------------------------------------------------------------- #
# Ghi chú Markdown (bộ con an toàn: HTML thô luôn bị escape)
# --------------------------------------------------------------------------- #
def markdown_sidecar(filename: str, used: set[Path], by_stem: dict[str, Path], archive_rel: str | None = None) -> Path | None:
    """Tìm ghi chú .md cùng tên với media (hoặc cùng tên nhóm bài). Thoát ngay nếu thư mục không có .md."""
    if not by_stem:
        return None
    parent, name = posixpath.split(filename)
    group_id = image_group_id(filename)
    group_stem = group_id[len("numeric-post-"):] if group_id.startswith("numeric-post-") else group_id
    keys = [posixpath.join(parent, stem).casefold() for stem in (os.path.splitext(name)[0], group_stem)]
    if archive_rel:   # ghi chú đặt cạnh file nén: "album.cbz" ↔ "album.md"
        keys.append(os.path.splitext(archive_rel)[0].casefold())
    for key in keys:
        match = by_stem.get(key)
        if match and match not in used:
            used.add(match)
            return match
    return None


def markdown_to_html(source: str) -> str:
    """Render a small safe Markdown subset; raw HTML is always escaped."""
    def inline(text: str) -> str:
        safe = html_escape(text, quote=True)
        safe = re.sub(r"`([^`]+)`", r"<code>\1</code>", safe)
        safe = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", safe)
        safe = re.sub(r"~~(.+?)~~", r"<del>\1</del>", safe)
        safe = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", safe)

        def link(match):
            label, target = match.group(1), match.group(2)
            decoded_target = target.replace("&amp;", "&")
            scheme = decoded_target.split(":", 1)[0].casefold() if ":" in decoded_target else ""
            if scheme not in ("", "http", "https", "mailto") or decoded_target.startswith("//"):
                return label
            return f'<a href="{html_escape(decoded_target, quote=True)}" target="_blank" rel="noopener noreferrer">{label}</a>'
        return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link, safe)

    output: list[str] = []
    paragraph: list[str] = []
    quote_lines: list[str] = []
    list_items: list[str] = []
    list_kind = ""

    def flush_paragraph():
        if paragraph:
            output.append("<p>" + "<br>".join(inline(line) for line in paragraph) + "</p>")
            paragraph.clear()

    def flush_quote():
        if quote_lines:
            output.append("<blockquote>" + "<br>".join(inline(line) for line in quote_lines) + "</blockquote>")
            quote_lines.clear()

    def flush_list():
        nonlocal list_kind
        if list_items:
            tag = "ol" if list_kind == "ol" else "ul"
            output.append(f"<{tag}>" + "".join(f"<li>{inline(item)}</li>" for item in list_items) + f"</{tag}>")
            list_items.clear()
        list_kind = ""

    def flush_all():
        flush_paragraph()
        flush_quote()
        flush_list()

    for raw_line in source.splitlines():
        line = raw_line.strip()
        heading = re.match(r"^(#{1,4})\s+(.+)$", line)
        bullet = re.match(r"^[-*+]\s+(.*)$", line)
        ordered = re.match(r"^\d+[.)]\s+(.*)$", line)
        if heading:
            flush_all()
            level = min(len(heading.group(1)) + 2, 6)
            output.append(f"<h{level}>{inline(heading.group(2))}</h{level}>")
        elif re.fullmatch(r"(?:-{3,}|\*{3,}|_{3,})", line):
            flush_all()
            output.append("<hr>")
        elif line.startswith(">"):
            flush_paragraph()
            flush_list()
            quote_lines.append(line.lstrip(">").strip())
        elif bullet or ordered:
            flush_paragraph()
            flush_quote()
            kind = "ul" if bullet else "ol"
            if list_kind and list_kind != kind:
                flush_list()
            list_kind = kind
            list_items.append((bullet or ordered).group(1))
        elif not line:
            flush_all()
        else:
            flush_list()
            flush_quote()
            paragraph.append(line)
    flush_all()
    return "".join(output)


# --------------------------------------------------------------------------- #
# Cấu hình (config.toml — đọc bằng tomllib có sẵn từ Python 3.11)
# --------------------------------------------------------------------------- #
CONFIG_FILENAME = "config.toml"
LEGACY_CONFIG_FILENAMES = ("config.yml", "config.yaml")
DEFAULT_CONFIG: dict[str, object] = {
    "title": "", "images_dir": "", "images_dirs": [], "theme": "auto", "theme_light": "rose-pine-dawn",
    "theme_dark": "mocha", "sort_by": "name", "sticky_header": True, "show_filename": False,
    "show_created_time": False, "show_file_size": False, "show_video_thumbnails": False,
    "show_dimensions": False, "folder_filter_depth": 1, "default_view": "feed", "columns": 0,
    "feed_width": 720, "probe_dimensions": True, "video_autoplay": False,
    "ignored_folders": [], "app_icon": "", "app_name": "", "app_status_bar": "black-translucent",
    "zip_support": True, "zip_post_mode": "folder", "unzipit_path": "", "unzipit_url": "", "zip_cache_mb": 48,
}
CONFIG_ALIASES = {
    "name": "title", "website_name": "title", "image_dir": "images_dir", "images": "images_dir",
    "image_folders": "images_dirs", "folders": "images_dirs", "sort": "sort_by", "order": "sort_by",
    "view": "default_view", "layout": "default_view", "cols": "columns", "width": "feed_width",
    "autoplay": "video_autoplay", "ignore_folders": "ignored_folders", "exclude_folders": "ignored_folders",
    "ignore": "ignored_folders", "exclude": "ignored_folders", "zip": "zip_support", "archives": "zip_support",
    "zip_mode": "zip_post_mode", "unzipit": "unzipit_path", "icon": "app_icon", "apple_touch_icon": "app_icon",
}


def load_config(script_dir: Path) -> tuple[dict[str, object], Path | None]:
    """Đọc config.toml (cạnh script hoặc trong thư mục hiện tại). Không có file → dùng mặc định."""
    directories = [script_dir, Path.cwd()]
    config_path = next((d / CONFIG_FILENAME for d in directories if (d / CONFIG_FILENAME).is_file()), None)
    config = {key: (list(value) if isinstance(value, list) else value) for key, value in DEFAULT_CONFIG.items()}
    if config_path is None:
        for directory in directories:
            for legacy in LEGACY_CONFIG_FILENAMES:
                if (directory / legacy).is_file():
                    raise ValueError(f"Tìm thấy {directory / legacy} nhưng phiên bản này chỉ đọc {CONFIG_FILENAME}. "
                                     f"Hãy chuyển cấu hình sang {CONFIG_FILENAME} (xem file mẫu và README).")
        return config, None
    try:
        with open(config_path, "rb") as handle:
            loaded = tomllib.load(handle)
    except tomllib.TOMLDecodeError as exc:
        raise ValueError(f"{config_path.name}: {exc}") from exc
    unknown: list[str] = []
    for raw_key, value in loaded.items():
        key = CONFIG_ALIASES.get(raw_key.casefold(), raw_key.casefold())
        if key in config:
            config[key] = value
        elif key != "show_media_info":
            unknown.append(raw_key)
    if "show_media_info" in loaded:  # khóa cũ của v2: bật cả tên file và ngày tạo
        for key in ("show_filename", "show_created_time"):
            if key not in loaded:
                config[key] = loaded["show_media_info"]
    if unknown:
        print(f"Cảnh báo: {config_path.name} có khóa không nhận ra, đã bỏ qua: {', '.join(unknown)}", file=sys.stderr)
    return config, config_path


# --------------------------------------------------------------------------- #
# Giao diện (CSS + HTML + JS nhúng). Placeholder dạng __TEN__ được thay lúc build.
# --------------------------------------------------------------------------- #
CSS = r''':root{color-scheme:__COLOR_SCHEME__;__THEME_VARS__;
--feed-w:__FEED_WIDTH__px;--r-card:18px;--r-media:12px;--card-gap:22px;--media-pad:10px;--media-gap:10px;--grid-gap:14px;--hdr-off:56px;
--ease:cubic-bezier(.22,.8,.24,1);
--font:ui-sans-serif,system-ui,-apple-system,"Segoe UI Variable Text","Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;
--serif:ui-serif,"Iowan Old Style","Palatino Linotype",Palatino,"Source Serif 4",Georgia,serif;
--mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
body.style-classic{--r-card:3px;--r-media:0px;--media-pad:0px;--media-gap:0px}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%;scroll-padding-top:var(--hdr-off);scrollbar-gutter:stable}
html.lb-open{overflow:hidden;background:#08080b}
body{margin:0;background:var(--base);color:var(--text);font:15px/1.5 var(--font);padding:0 12px calc(96px + env(safe-area-inset-bottom));-webkit-tap-highlight-color:transparent}
button,input,select,textarea{font:inherit;color:inherit}
button{cursor:pointer}
:focus-visible{outline:2px solid var(--mauve);outline-offset:2px}
[hidden]{display:none!important}
.sprite{position:absolute;width:0;height:0;overflow:hidden}
.ic{width:1.2em;height:1.2em;fill:none;stroke:currentColor;stroke-width:1.75;stroke-linecap:round;stroke-linejoin:round;flex:none;pointer-events:none}
kbd{font:600 10px var(--mono);padding:1px 6px;border:1px solid var(--surface1);border-radius:6px;background:color-mix(in srgb,var(--base) 70%,var(--surface0));color:var(--subtext)}
noscript{display:block;padding:40px 16px;text-align:center;color:var(--subtext)}

/* ---------- Header ---------- */
.site-header{position:sticky;top:0;z-index:9;margin:0 -12px;background:color-mix(in srgb,var(--mantle) 84%,transparent);-webkit-backdrop-filter:blur(16px) saturate(160%);backdrop-filter:blur(16px) saturate(160%);border-bottom:1px solid color-mix(in srgb,var(--surface1) 70%,transparent)}
.hdr-main{max-width:1500px;margin:0 auto;display:flex;align-items:center;gap:14px;padding:10px 16px;transition:padding .18s var(--ease)}
.brand{min-width:0;flex:1}
.brand-line{display:flex;align-items:baseline;gap:8px;min-width:0}
h1{margin:0;font:600 clamp(19px,2.4vw,24px)/1.2 var(--serif);letter-spacing:-.01em;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;transition:font-size .18s var(--ease)}
.ver{flex:none;padding:1px 7px;border:1px solid color-mix(in srgb,var(--surface1) 70%,transparent);border-radius:999px;color:var(--subtext);font:600 10px/1.5 var(--mono)}
.summary{color:var(--subtext);font-size:12px;max-height:20px;transition:opacity .15s,max-height .18s var(--ease)}
.site-header.compact .hdr-main{padding-block:6px}
.site-header.compact h1{font-size:16px}
.site-header.compact .summary{max-height:0;opacity:0;overflow:hidden}
.pos-chip{flex:none;display:inline-flex;align-items:baseline;padding:5px 12px;border:1px solid color-mix(in srgb,var(--mauve) 32%,var(--surface1));border-radius:999px;background:color-mix(in srgb,var(--mauve) 10%,var(--surface0));font:650 12px var(--font);font-variant-numeric:tabular-nums;color:var(--text)}
.pos-chip:hover{border-color:var(--mauve)}
.pos-sep{opacity:.45;margin:0 4px}
#posTotal{color:var(--subtext)}
.hdr-tools{display:flex;gap:6px;flex:none}
.hdr-tool{display:inline-flex;align-items:center;gap:7px;padding:7px 10px;border:1px solid var(--surface1);border-radius:10px;background:color-mix(in srgb,var(--surface0) 70%,transparent);font-size:12px;font-weight:600;transition:background .15s,border-color .15s}
.hdr-tool:hover{border-color:var(--mauve);background:color-mix(in srgb,var(--mauve) 14%,var(--surface0))}
.progress{position:absolute;left:0;right:0;bottom:-1px;height:2px;pointer-events:none;overflow:hidden}
.progress i{display:block;height:100%;background:var(--mauve);transform-origin:left;transform:scaleX(0);transition:transform .25s linear}
body.header-not-sticky .site-header{position:static;background:transparent;border-bottom:0;-webkit-backdrop-filter:none;backdrop-filter:none;margin:0}
body.header-not-sticky .progress{display:none}
@media(max-width:760px){.hdr-tools,.summary{display:none}.hdr-main{padding:8px 12px;gap:10px}h1{font-size:17px}.site-header.compact h1{font-size:15px}}

/* ---------- Feed & bài viết ---------- */
.feed{max-width:var(--feed-w);margin:18px auto 0;display:grid;gap:var(--card-gap)}
.post{position:relative;overflow:hidden;background:var(--mantle);border:1px solid color-mix(in srgb,var(--surface1) 62%,transparent);border-radius:var(--r-card);box-shadow:0 1px 2px #0000000f,0 12px 30px -14px #0000003a;scroll-margin-top:calc(var(--hdr-off) + 12px);transition:border-color .18s}
.feed:not(.grid) .post{content-visibility:auto;contain-intrinsic-height:auto var(--est,640px)}
.post:hover{border-color:color-mix(in srgb,var(--mauve) 34%,var(--surface1))}
.post.multi{border-color:color-mix(in srgb,var(--mauve) 45%,var(--surface1))}
.post.is-liked-post{border-color:color-mix(in srgb,var(--pink) 62%,var(--surface1));box-shadow:0 0 0 2px color-mix(in srgb,var(--pink) 18%,transparent),0 12px 30px -14px #0000003a}
.post-head{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:8px 12px 8px 6px}
.post.multi .post-head{background:color-mix(in srgb,var(--mauve) 7%,transparent)}
.post-no{padding:6px 9px;border:0;border-radius:9px;background:none;font:700 15px/1 var(--font);font-variant-numeric:tabular-nums;letter-spacing:-.01em;color:var(--text);transition:background .15s,color .15s}
.post-no:hover{background:var(--surface0);color:var(--mauve)}
.post-badge{display:inline-flex;align-items:center;gap:6px;min-height:26px;padding:4px 10px;border:1px solid color-mix(in srgb,var(--surface1) 70%,transparent);border-radius:999px;background:color-mix(in srgb,var(--surface0) 60%,transparent);font:600 11px/1.3 var(--font);color:var(--subtext)}
.post-badge .ic{width:15px;height:15px}
.post.multi .post-badge{border-color:color-mix(in srgb,var(--mauve) 50%,transparent);background:color-mix(in srgb,var(--mauve) 13%,transparent);color:var(--mauve)}
.post-media{display:grid;gap:var(--media-gap);padding:0 var(--media-pad) var(--media-pad)}
.media-item{position:relative;min-width:0}
.media-item :is(img,video){display:block;width:100%;height:auto;max-height:82vh;max-height:82dvh;background:var(--crust);object-fit:contain;border-radius:var(--r-media)}
.media-item img{cursor:zoom-in;opacity:0;transition:opacity .28s ease}
.media-item img.loaded{opacity:1}
.media-item img.nodim{min-height:120px}
.media-item img.broken{min-height:120px;cursor:default;color:var(--subtext);font-size:12px;text-align:center}
.media-no{position:absolute;z-index:2;top:8px;left:8px;padding:4px 9px;border:1px solid color-mix(in srgb,var(--surface1) 65%,transparent);border-radius:999px;background:color-mix(in srgb,var(--mantle) 78%,transparent);-webkit-backdrop-filter:blur(10px);backdrop-filter:blur(10px);font:700 11px var(--font);color:var(--text);pointer-events:none}
.video-wrap{position:relative}
.media-open{position:absolute;right:10px;top:10px;display:inline-flex;align-items:center;gap:6px;padding:6px 11px;border:1px solid color-mix(in srgb,var(--surface1) 70%,transparent);border-radius:999px;background:color-mix(in srgb,var(--mantle) 78%,transparent);-webkit-backdrop-filter:blur(10px);backdrop-filter:blur(10px);font-size:12px;font-weight:600}
.media-open .ic{width:14px;height:14px}
.media-meta{padding:6px 4px 0;color:var(--subtext);font-size:11px;text-align:right;overflow-wrap:anywhere}
.media-note{margin:8px 0 0;padding:11px 14px;max-height:16em;overflow:auto;border:1px solid color-mix(in srgb,var(--surface1) 58%,transparent);border-left:3px solid var(--mauve);border-radius:12px;background:color-mix(in srgb,var(--surface0) 38%,var(--mantle));color:var(--text);font-size:14px;overflow-wrap:anywhere}
.media-note :is(p,ul,ol,blockquote){margin:0 0 8px}
.media-note>:last-child{margin-bottom:0}
.media-note :is(h3,h4,h5,h6){margin:4px 0 6px;color:var(--mauve);line-height:1.3}
.media-note :is(ul,ol){padding-left:22px}
.media-note blockquote{padding-left:10px;border-left:2px solid var(--surface1);color:var(--subtext)}
.media-note hr{border:0;border-top:1px solid var(--surface1);margin:8px 0}
.media-note code{padding:2px 5px;border-radius:5px;background:var(--crust);color:var(--peach);font:.9em var(--mono)}
.media-note a{color:var(--blue);text-decoration:underline;text-underline-offset:2px}
.post-foot{display:flex;align-items:center;flex-wrap:wrap;gap:10px;padding:8px 12px 10px;color:var(--subtext);font-size:12px}
.post-source{display:inline-flex;align-items:center;gap:6px;max-width:100%;padding:5px 10px;border:1px solid color-mix(in srgb,var(--blue) 26%,var(--surface1));border-radius:999px;background:color-mix(in srgb,var(--blue) 8%,var(--surface0));font-weight:650;font-size:11px;overflow-wrap:anywhere}
.post-source .ic{width:14px;height:14px}
.post-actions{display:flex;align-items:center;gap:8px;margin-left:auto}
.btn-locate{display:none;align-items:center;padding:6px 10px;border:1px solid var(--surface1);border-radius:9px;background:var(--surface0);color:var(--mauve);font-size:11px;font-weight:700}
body.only-liked .btn-locate{display:inline-flex}
.like{display:grid;place-items:center;width:38px;height:38px;padding:0;border:1px solid transparent;border-radius:50%;background:color-mix(in srgb,var(--surface0) 55%,transparent);color:var(--subtext);font-size:20px;transition:color .16s,background .16s,border-color .16s,transform .16s}
.like:hover{color:var(--red);background:color-mix(in srgb,var(--red) 12%,var(--surface0));transform:scale(1.06)}
.like.is-liked{color:var(--red);border-color:color-mix(in srgb,var(--red) 42%,transparent);background:color-mix(in srgb,var(--red) 12%,var(--mantle))}
.like.is-liked .ic{fill:currentColor}
.like.pop .ic{animation:pop .34s var(--ease)}
@keyframes pop{0%{transform:scale(.55)}55%{transform:scale(1.35)}100%{transform:scale(1)}}
#loadSentinel{height:1px;pointer-events:none}
#empty{max-width:520px;margin:48px auto;text-align:center;color:var(--subtext)}
#empty .btn{margin-top:12px}

/* Phong cách cổ điển: phẳng, sát mép như Tumblr gốc */
body.style-classic .post{box-shadow:0 1px 4px #0002}
body.style-classic .post-head{padding:10px 14px;border-bottom:1px solid var(--surface0)}
body.style-classic .post-no{padding:0}
body.style-classic .post.multi .media-item+.media-item{border-top:1px solid var(--surface1)}
body.style-classic .media-note{margin:0;border:0;border-left:3px solid var(--mauve);border-radius:0}
body.style-classic .post-foot{padding:10px 15px;border-top:1px solid var(--surface0)}
body.style-classic .media-meta{padding:6px 14px 0}

/* ---------- Masonry ---------- */
.feed.grid{max-width:1500px;display:flex;align-items:flex-start;gap:var(--grid-gap)}
.col{flex:1 1 0;min-width:0;display:flex;flex-direction:column;gap:var(--grid-gap)}
.feed.grid .post{border-radius:calc(var(--r-card) - 4px);box-shadow:none}
body.style-classic .feed.grid .post{border-radius:3px}
.feed.grid .post-head{position:absolute;z-index:3;inset:8px 8px auto 8px;padding:0;border:0;background:none;pointer-events:none}
.feed.grid .post-no{pointer-events:auto;padding:5px 9px;border:1px solid color-mix(in srgb,var(--surface1) 65%,transparent);border-radius:999px;background:color-mix(in srgb,var(--mantle) 78%,transparent);-webkit-backdrop-filter:blur(10px);backdrop-filter:blur(10px);font-size:11px;opacity:0;transition:opacity .15s}
.feed.grid .post:hover .post-no,.feed.grid .post:focus-within .post-no{opacity:1}
.feed.grid .post-badge{background:color-mix(in srgb,var(--mantle) 78%,transparent);-webkit-backdrop-filter:blur(10px);backdrop-filter:blur(10px)}
.feed.grid .post-media{display:block;padding:0}
.feed.grid .media-item{display:none;border:0}
.feed.grid .media-item:first-child{display:block;aspect-ratio:var(--ar,1)}
.feed.grid .media-item:first-child :is(img,video){height:100%;max-height:none;border-radius:0;object-fit:cover}
.feed.grid :is(.media-no,.media-meta,.media-note,.post-source,.btn-locate){display:none}
.feed.grid .post-foot{position:absolute;z-index:3;right:8px;bottom:8px;padding:0;border:0;opacity:0;transition:opacity .15s}
.feed.grid .post:hover .post-foot,.feed.grid .post:focus-within .post-foot,.feed.grid .post.is-liked-post .post-foot{opacity:1}
.feed.grid .like{width:34px;height:34px;background:color-mix(in srgb,var(--mantle) 80%,transparent);-webkit-backdrop-filter:blur(10px);backdrop-filter:blur(10px)}
@media(hover:none){.feed.grid .post-foot,.feed.grid .post-no{opacity:1}}

/* ---------- Thanh điều khiển ---------- */
.controls{position:fixed;z-index:10;left:0;right:0;bottom:0;display:flex;justify-content:center;gap:7px;padding:8px 10px calc(8px + env(safe-area-inset-bottom));background:color-mix(in srgb,var(--mantle) 80%,transparent);border-top:1px solid color-mix(in srgb,var(--surface1) 60%,transparent);-webkit-backdrop-filter:blur(14px);backdrop-filter:blur(14px)}
.tb{position:relative;flex:1;min-width:0;display:flex;align-items:center;justify-content:center;gap:6px;height:42px;padding:0 8px;border:1px solid color-mix(in srgb,var(--surface1) 75%,transparent);border-radius:13px;background:color-mix(in srgb,var(--surface0) 84%,transparent);font-size:12px;font-weight:650;white-space:nowrap;transition:transform .15s var(--ease),background .15s,border-color .15s}
.tb:hover,.tb:focus-visible{border-color:color-mix(in srgb,var(--mauve) 60%,var(--surface1));background:color-mix(in srgb,var(--mauve) 13%,var(--surface0));transform:translateY(-1px)}
.tb .ic{font-size:18px}
.tb.active{background:var(--red);border-color:var(--red);color:var(--crust)}
.tb.accent{background:var(--mauve);border-color:var(--mauve);color:var(--crust)}
.tb.accent:hover{background:color-mix(in srgb,var(--mauve) 86%,#fff)}
.tb .badge{font-size:11px;font-weight:700}
.collapse{display:none}
.filter-wrap{position:relative;flex:1;min-width:0}
.filter-wrap>.tb{width:100%}
.menu{display:none;position:absolute;z-index:12;min-width:210px;max-height:78dvh;overflow:auto;padding:8px;border:1px solid color-mix(in srgb,var(--surface1) 76%,transparent);border-radius:16px;background:color-mix(in srgb,var(--mantle) 98%,transparent);box-shadow:0 18px 48px #0000004d;-webkit-backdrop-filter:blur(18px);backdrop-filter:blur(18px);overscroll-behavior:contain}
.menu.open{display:grid;gap:2px}
.settings{right:8px;bottom:calc(100% + 8px);width:min(310px,calc(100vw - 16px))}
.filter-pop{position:fixed;left:8px;right:8px;bottom:calc(64px + env(safe-area-inset-bottom));max-height:min(62dvh,540px)}
.filter-pop.open{display:block}
.menu-h{padding:4px 10px;color:var(--subtext);font-size:12px;font-weight:700}
.menu-sep{height:1px;margin:5px 2px;background:var(--surface0)}
.check{display:flex;align-items:center;gap:10px;padding:8px 10px;border-radius:9px;font-size:13px;cursor:pointer}
.check:hover{background:var(--surface0)}
.check input{width:17px;height:17px;margin:0;accent-color:var(--mauve)}
.check span{flex:1;min-width:0;overflow-wrap:anywhere}
.check em{font-style:normal;color:var(--subtext);font-size:11px;font-variant-numeric:tabular-nums}
.item{display:flex;align-items:center;gap:10px;width:100%;padding:9px 11px;border:0;border-radius:10px;background:none;text-align:left;font-size:13px}
.item:hover{background:color-mix(in srgb,var(--mauve) 12%,var(--surface0))}
.field{display:grid;gap:6px;padding:6px 10px 8px;color:var(--subtext);font-size:12px}
.field select{width:100%;padding:8px;border:1px solid var(--surface1);border-radius:9px;background:var(--surface0);color:var(--text)}
.field input[type=range]{width:100%;accent-color:var(--mauve)}
.field b{color:var(--text);font-weight:650;font-variant-numeric:tabular-nums}
.row-split{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:5px 6px 5px 10px;color:var(--subtext);font-size:12px;font-weight:650}
.pill,.stepper button{display:inline-flex;align-items:center;justify-content:center;gap:7px;padding:5px 10px;border:1px solid color-mix(in srgb,var(--surface1) 66%,transparent);border-radius:999px;background:color-mix(in srgb,var(--surface0) 58%,transparent);color:var(--text);font-size:11px;font-weight:650}
.pill:hover,.stepper button:hover{border-color:var(--mauve);background:color-mix(in srgb,var(--mauve) 12%,var(--surface0))}
.dot{width:7px;height:7px;border-radius:50%;background:var(--mauve);box-shadow:0 0 0 3px color-mix(in srgb,var(--mauve) 15%,transparent)}
.stepper{display:inline-flex;gap:4px}
.stepper button{min-width:30px}
.stepper .ic{width:14px;height:14px}
@media(min-width:800px){
body{padding-bottom:35px}
.controls{left:auto;right:20px;bottom:24px;width:54px;flex-direction:column;align-items:center;gap:7px;padding:7px;border:1px solid color-mix(in srgb,var(--surface1) 60%,transparent);border-radius:18px;box-shadow:0 10px 28px #0000004d}
.tb{flex:none;width:40px;height:40px;padding:0;border-radius:12px}
.tb .lbl{display:none}
.tb .badge{position:absolute;top:-5px;right:-5px;min-width:17px;height:17px;padding:0 4px;display:grid;place-items:center;border-radius:10px;background:var(--mauve);color:var(--crust);font-size:10px}
.filter-wrap{flex:none;width:40px}
.filter-wrap>.tb{width:40px}
.collapse{display:flex}
.filter-pop{position:absolute;left:auto;right:calc(100% + 10px);bottom:0;width:270px;max-height:min(72dvh,620px)}
.settings{right:calc(100% + 10px);bottom:0}
.controls.collapsed{width:44px;padding:4px;border-radius:50%}
.controls.collapsed>*:not(.collapse){display:none}
.controls.collapsed .collapse{width:34px;height:34px;border-radius:50%}}

/* ---------- Dialog dùng chung ---------- */
.overlay{position:fixed;inset:0;z-index:25;display:none;place-items:center;padding:16px;background:color-mix(in srgb,var(--crust) 80%,transparent);-webkit-backdrop-filter:blur(7px);backdrop-filter:blur(7px)}
.overlay.active{display:grid}
.sheet{width:min(740px,100%);max-height:min(88dvh,900px);overflow:auto;padding:22px;border:1px solid color-mix(in srgb,var(--surface1) 78%,transparent);border-radius:22px;background:color-mix(in srgb,var(--mantle) 97%,transparent);box-shadow:0 28px 90px #00000070;overscroll-behavior:contain}
.sheet-head{display:flex;align-items:flex-start;justify-content:space-between;gap:16px;padding-bottom:14px;margin-bottom:14px;border-bottom:1px solid color-mix(in srgb,var(--surface1) 55%,transparent)}
.sheet-head h2{margin:0;font:600 clamp(20px,3.6vw,26px)/1.2 var(--serif);letter-spacing:-.01em}
.sheet-head p{margin:4px 0 0;color:var(--subtext);font-size:13px}
.x-btn{flex:none;display:grid;place-items:center;width:34px;height:34px;border:1px solid var(--surface1);border-radius:11px;background:var(--surface0);color:var(--subtext)}
.x-btn:hover{color:var(--text);border-color:var(--mauve)}
.btn{display:inline-flex;align-items:center;gap:8px;padding:8px 13px;border:1px solid var(--surface1);border-radius:10px;background:var(--surface0);font-size:13px;font-weight:600}
.btn:hover{border-color:var(--mauve);background:color-mix(in srgb,var(--mauve) 12%,var(--surface0))}
.btn.primary{background:var(--mauve);border-color:var(--mauve);color:var(--crust)}
.btn .ic{width:16px;height:16px}
.btn-row{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}
.hint{margin:0 0 12px;color:var(--subtext);font-size:13px}
textarea{width:100%;padding:11px 13px;border:1px solid var(--surface1);border-radius:12px;background:var(--base);font:12px/1.5 var(--mono);resize:vertical}
.shortcut-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.shortcut-group{min-width:0;padding:14px;border:1px solid color-mix(in srgb,var(--surface1) 52%,transparent);border-radius:16px;background:color-mix(in srgb,var(--surface0) 32%,var(--mantle))}
.shortcut-group h3{margin:0 0 8px;color:var(--mauve);font-size:13px;font-weight:700}
.shortcut-group.wide{grid-column:1/-1;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));column-gap:14px}
.shortcut-group.wide h3{grid-column:1/-1}
.sc{min-height:42px;display:flex;align-items:center;gap:5px;padding:7px 0;border-top:1px solid color-mix(in srgb,var(--surface1) 35%,transparent)}
.sc>span{display:grid;flex:1;min-width:0}
.sc b{font-size:12px;font-weight:650}
.sc small{color:var(--subtext);font-size:10.5px;line-height:1.35}
.changelog{margin-top:14px;border:1px solid color-mix(in srgb,var(--surface1) 54%,transparent);border-radius:14px;background:color-mix(in srgb,var(--surface0) 25%,var(--mantle))}
.changelog summary{padding:11px 14px;font-size:12px;font-weight:700;cursor:pointer}
.changelog ul{margin:0;padding:0 18px 13px 34px;color:var(--subtext);font-size:12px}
.changelog li{padding:3px 0}
.formats{margin:14px 2px 0;color:var(--subtext);font-size:11px;line-height:1.6}
@media(max-width:600px){.overlay{padding:8px}.sheet{padding:17px;border-radius:19px;max-height:calc(100dvh - 16px)}.shortcut-grid{grid-template-columns:1fr}.shortcut-group.wide{grid-column:auto;display:block}}

/* Tìm kiếm */
.search-overlay{z-index:27}
.search-sheet{width:min(640px,100%);display:flex;flex-direction:column;gap:10px;padding:16px}
.search-sheet .sheet-head{margin:0;padding:0 0 4px;border:0}
.search-sheet .sheet-head h2{font-size:18px}
#searchQuery{width:100%;padding:11px 14px;border:1px solid var(--surface1);border-radius:13px;background:var(--base);font:inherit}
.search-count{min-height:17px;color:var(--subtext);font-size:11px}
.search-results{display:grid;gap:7px;overflow:auto;overscroll-behavior:contain}
.s-item{display:grid;grid-template-columns:68px minmax(0,1fr);align-items:center;gap:11px;width:100%;padding:7px;border:1px solid var(--surface0);border-radius:14px;background:color-mix(in srgb,var(--surface0) 52%,var(--mantle));text-align:left}
.s-item:hover,.s-item.sel{border-color:var(--mauve);background:color-mix(in srgb,var(--mauve) 12%,var(--surface0))}
.s-thumb{width:68px;height:58px;display:grid;place-items:center;border-radius:8px;background:var(--crust);object-fit:cover;color:var(--mauve);font-size:22px}
.s-text{display:grid;gap:3px;min-width:0}
.s-title{font-size:13px;font-weight:700}
.s-detail{overflow:hidden;color:var(--subtext);font-size:11px;text-overflow:ellipsis;white-space:nowrap}
.s-empty{padding:22px 10px;text-align:center;color:var(--subtext);font-size:13px}
.s-more{justify-self:center}
@media(max-width:700px){.search-overlay{inset:auto 0 auto;top:var(--vv-top,0px);height:var(--vv-height,100dvh);place-items:start center;overflow:hidden;padding:8px 10px calc(8px + env(safe-area-inset-bottom))}.search-sheet{max-height:calc(var(--vv-height,100dvh) - 16px);overflow:hidden}.search-results{min-height:0}}

#toast{position:fixed;z-index:40;top:15px;left:50%;max-width:calc(100vw - 24px);padding:9px 16px;border-radius:999px;background:var(--mauve);color:var(--crust);font-size:13px;font-weight:700;text-align:center;box-shadow:0 8px 24px #0006;opacity:0;pointer-events:none;transform:translate(-50%,-8px);transition:opacity .2s,transform .2s var(--ease)}
#toast.show{opacity:1;transform:translate(-50%,0)}

/* ---------- Lightbox (luôn nền tối cho dễ xem ảnh) ---------- */
#lightbox{--fg:#f3f3f6;position:fixed;inset:0;z-index:30;display:none;background:#08080b;color:var(--fg);user-select:none;-webkit-user-select:none;overscroll-behavior:contain;outline:0}
#lightbox.active{display:block}
.lb-stage{position:absolute;inset:0;display:grid;place-items:center;overflow:hidden;touch-action:none;cursor:zoom-in}
.lb-stage.zoomed{cursor:grab}
.lb-stage.panning{cursor:grabbing}
#lightbox.idle .lb-stage{cursor:none}
#lbImg{max-width:100vw;max-height:100vh;max-height:100dvh;object-fit:contain;transform:translate3d(var(--tx,0px),var(--ty,0px),0) scale(var(--sc,1));transition:opacity .15s;-webkit-user-drag:none}
#lbImg.loading{opacity:.25}
#lbVideo{max-width:100vw;max-height:100dvh;width:auto;height:auto;background:#000;outline:0}
.lb-spin{position:absolute;top:50%;left:50%;width:34px;height:34px;margin:-17px 0 0 -17px;border:3px solid #ffffff33;border-top-color:#fff;border-radius:50%;opacity:0;pointer-events:none;animation:spin .8s linear infinite paused}
#lightbox.loading .lb-spin{opacity:1;animation-play-state:running}
@keyframes spin{to{transform:rotate(360deg)}}
.lb-ui{transition:opacity .25s}
#lightbox.idle .lb-ui{opacity:0;pointer-events:none}
.lb-top{position:absolute;top:0;left:0;right:0;display:flex;align-items:center;justify-content:space-between;gap:10px;padding:calc(10px + env(safe-area-inset-top)) 12px 28px;background:linear-gradient(#000000b0,#0000);pointer-events:none}
.lb-top>*{pointer-events:auto}
.lb-count{font:700 13px var(--font);font-variant-numeric:tabular-nums;text-shadow:0 1px 3px #000}
.lb-tools{display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end}
.lb-btn{display:grid;place-items:center;width:40px;height:40px;padding:0;border:1px solid #ffffff26;border-radius:50%;background:#ffffff16;color:var(--fg);font-size:19px;-webkit-backdrop-filter:blur(8px);backdrop-filter:blur(8px);transition:background .15s,color .15s}
.lb-btn:hover{background:#ffffff2e}
.lb-btn.on{background:var(--mauve);border-color:var(--mauve);color:var(--crust)}
#lbLike.on{background:#ffffff16;border-color:color-mix(in srgb,var(--red) 60%,transparent);color:var(--red)}
#lbLike.on .ic{fill:currentColor}
.lb-nav{position:absolute;top:50%;width:46px;height:46px;margin-top:-23px}
.lb-prev{left:12px}
.lb-next{right:12px}
.lb-bottom{position:absolute;left:0;right:0;bottom:0;padding:30px 16px calc(14px + env(safe-area-inset-bottom));background:linear-gradient(#0000,#000000a8);text-align:center;font-size:13px;pointer-events:none;text-shadow:0 1px 3px #000}
#lbName{display:inline-block;max-width:min(90vw,900px);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.lb-info{position:absolute;z-index:3;right:12px;bottom:calc(58px + env(safe-area-inset-bottom));width:min(340px,calc(100vw - 24px));max-height:52dvh;overflow:auto;padding:14px;border:1px solid #ffffff24;border-radius:16px;background:#141418e8;color:#eee;font-size:13px;-webkit-backdrop-filter:blur(14px);backdrop-filter:blur(14px)}
.lb-row{display:flex;justify-content:space-between;gap:14px;padding:5px 0;border-bottom:1px solid #ffffff14}
.lb-row span{color:#a5a5b3;flex:none}
.lb-row b{font-weight:600;text-align:right;overflow-wrap:anywhere}
.lb-info .media-note{max-height:11em;color:#eee;background:#ffffff0d;border-color:#ffffff1f}
@media(min-width:800px){.lb-prev{left:30px}.lb-next{right:30px}}
@media(max-width:600px){.lb-tools{gap:4px}.lb-btn{width:36px;height:36px;font-size:17px}.lb-nav{width:40px;height:40px}}
@media(prefers-reduced-motion:reduce){*,*::before,*::after{transition-duration:.01ms!important;animation-duration:.01ms!important}}

/* ---------- Bổ sung ---------- */
body{background:radial-gradient(ellipse 70% 30rem at 50% -14rem,color-mix(in srgb,var(--mauve) 12%,transparent),transparent 72%),var(--base)}
.media-item img.broken{opacity:1}
.stepper button.on{background:var(--mauve);border-color:var(--mauve);color:var(--crust)}
.vid-ph{display:grid;place-items:center;width:100%;aspect-ratio:16/9;background:var(--crust);color:var(--mauve);font-size:34px;border-radius:var(--r-media)}
.feed.grid .vid-ph{height:100%;border-radius:0}
.play-badge{position:absolute;left:50%;top:50%;z-index:2;display:grid;place-items:center;width:46px;height:46px;margin:-23px 0 0 -23px;border-radius:50%;background:color-mix(in srgb,var(--mantle) 70%,transparent);-webkit-backdrop-filter:blur(8px);backdrop-filter:blur(8px);color:var(--text);font-size:20px;pointer-events:none}
.play-badge .ic{fill:currentColor}
.feed.grid .media-item{cursor:zoom-in}
.tb .lbl{font-size:11px}
@media(max-width:480px){.tb .lbl{display:none}.controls{gap:5px}}

/* ---------- Lọc theo tìm kiếm ---------- */
.chip-bar{max-width:1500px;margin:0 auto;padding:0 16px 8px;display:flex}
.s-chip{display:inline-flex;align-items:center;max-width:100%;border:1px solid color-mix(in srgb,var(--mauve) 50%,var(--surface1));border-radius:999px;background:color-mix(in srgb,var(--mauve) 13%,var(--surface0));font-size:12px;font-weight:650;overflow:hidden}
.chip-main,.chip-x{display:inline-flex;align-items:center;gap:7px;border:0;background:none;padding:5px 8px 5px 12px;min-width:0}
.chip-main:hover,.chip-x:hover{background:color-mix(in srgb,var(--mauve) 18%,transparent)}
.chip-main b{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:min(52vw,420px)}
.chip-main em{font-style:normal;color:var(--subtext);font-weight:600;white-space:nowrap}
.chip-x{padding:5px 10px 5px 8px;border-left:1px solid color-mix(in srgb,var(--mauve) 30%,transparent)}
.search-tools{display:flex;align-items:center;justify-content:space-between;gap:10px}
.search-tools .btn{flex:none;padding:6px 11px;font-size:12px}
.btn:disabled{opacity:.45;cursor:default;pointer-events:none}

/* ---------- Bộ lọc đã lưu ---------- */
.save-row{display:flex;gap:8px}
.save-row input,.rename-input{flex:1;min-width:0;padding:9px 12px;border:1px solid var(--surface1);border-radius:11px;background:var(--base);font:inherit}
.saved-list{display:grid;gap:8px}
.saved-item{display:flex;align-items:center;gap:4px;padding:5px;border:1px solid var(--surface0);border-radius:14px;background:color-mix(in srgb,var(--surface0) 40%,var(--mantle))}
.saved-item.on{border-color:var(--mauve);background:color-mix(in srgb,var(--mauve) 11%,var(--surface0))}
.saved-apply{flex:1;min-width:0;display:grid;gap:2px;padding:6px 9px;border:0;border-radius:10px;background:none;text-align:left}
.saved-apply:hover{background:color-mix(in srgb,var(--mauve) 12%,transparent)}
.saved-apply b{font-size:13px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.saved-apply small{display:flex;min-width:0;color:var(--subtext);font-size:11px;white-space:nowrap}
.saved-apply small .desc{min-width:0;overflow:hidden;text-overflow:ellipsis}
.saved-apply small .cnt{flex:none}
.icon-btn{flex:none;display:grid;place-items:center;width:34px;height:34px;padding:0;border:1px solid transparent;border-radius:10px;background:none;color:var(--subtext);font-size:16px}
.icon-btn:hover{color:var(--text);border-color:var(--surface1);background:var(--surface0)}
.icon-btn.danger:hover{color:var(--red);border-color:color-mix(in srgb,var(--red) 40%,transparent)}
.saved-empty{padding:18px 10px;text-align:center;color:var(--subtext);font-size:13px}
.item.on{background:color-mix(in srgb,var(--mauve) 16%,var(--surface0));font-weight:650}
.item .item-text{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}

/* ---------- Chế độ ứng dụng iOS (Thêm vào Màn hình chính) ---------- */
.site-header{padding-top:env(safe-area-inset-top,0px)}
#toast{top:calc(15px + env(safe-area-inset-top,0px))}
@media(display-mode:standalone){body{overscroll-behavior-y:none}}

/* ---------- File nén (.zip / .cbz) ---------- */
.feed:not(.grid) .post.zipped{content-visibility:visible}
.post-zip{border-color:color-mix(in srgb,var(--peach) 40%,var(--surface1));background:color-mix(in srgb,var(--peach) 9%,var(--surface0))}
.zip-need-btn{position:absolute;inset:0;z-index:3;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:8px;width:100%;padding:12px;border:1px dashed color-mix(in srgb,var(--mauve) 55%,var(--surface1));border-radius:var(--r-media);background:color-mix(in srgb,var(--crust) 72%,transparent);color:var(--text);font-size:13px;font-weight:650;text-align:center}
.zip-need-btn .ic{width:28px;height:28px;color:var(--mauve)}
.zip-need-btn:hover{background:color-mix(in srgb,var(--mauve) 16%,var(--crust))}
.feed.grid .zip-need-btn span{display:none}
.zip-play{position:absolute;left:50%;top:50%;z-index:2;display:grid;place-items:center;width:58px;height:58px;margin:-29px 0 0 -29px;padding:0;border:1px solid color-mix(in srgb,var(--surface1) 70%,transparent);border-radius:50%;background:color-mix(in srgb,var(--mantle) 76%,transparent);-webkit-backdrop-filter:blur(8px);backdrop-filter:blur(8px);color:var(--text);font-size:22px}
.zip-play .ic{fill:currentColor}
.zip-play:hover{background:color-mix(in srgb,var(--mauve) 30%,var(--mantle))}
.video-wrap:has(video[src]) .zip-play{display:none}
.zip-drop{margin:12px 0;padding:14px;border:1px dashed var(--surface1);border-radius:14px;color:var(--subtext);font-size:12px;text-align:center}
.lb-need{position:absolute;inset:0;z-index:2;display:grid;place-content:center;justify-items:center;gap:14px;padding:24px;text-align:center;color:var(--fg);font-size:14px}
.lb-need .ic{width:40px;height:40px;color:var(--mauve)}
.lb-need p{max-width:440px;margin:0}
'''

BODY = r'''</style>
<script>
/* Áp theme sớm (trước khi vẽ) để không bị nháy màu khi đã chọn theme khác. */
const THEMES=__THEMES__,FINGERPRINT=__FINGERPRINT__,DEFAULT_THEME=__DEFAULT_THEME__,AUTO_THEMES=__AUTO_THEMES__;
const THEME_KEY=`tumblr_archive_${FINGERPRINT}_theme_v2`;
let themeChoice=DEFAULT_THEME;
function readJSON(key,fallback){try{const v=localStorage.getItem(key);return v?JSON.parse(v):fallback}catch(e){return fallback}}
function resolvedTheme(c){return c==='auto'?AUTO_THEMES[matchMedia('(prefers-color-scheme: light)').matches?'light':'dark']:c}
function applyTheme(choice,persist){
  if(choice!=='auto'&&!THEMES[choice])choice=DEFAULT_THEME;
  themeChoice=choice;const t=THEMES[resolvedTheme(choice)],root=document.documentElement;
  for(const k in t){if(k==='scheme')root.style.colorScheme=t[k];else root.style.setProperty('--'+k,t[k])}
  const meta=document.querySelector('meta[name=theme-color]');if(meta)meta.content=t.mantle;
  const sel=document.getElementById('themeSelect');if(sel)sel.value=choice;
  if(persist){try{localStorage.setItem(THEME_KEY,JSON.stringify(choice))}catch(e){}}
}
applyTheme(readJSON(THEME_KEY,DEFAULT_THEME),false);
matchMedia('(prefers-color-scheme: light)').addEventListener?.('change',()=>{if(themeChoice==='auto')applyTheme('auto',false)});
</script>
</head>
<body class="__HEADER_STICKY_CLASS__">
__SPRITE__
<header class="site-header" id="siteHeader">
  <div class="hdr-main">
    <div class="brand">
      <div class="brand-line"><h1>__ARCHIVE_TITLE__</h1><span class="ver" title="Phiên bản archive">v__VERSION__</span></div>
      <div class="summary" id="summary"></div>
    </div>
    <button class="pos-chip" id="posChip" type="button" title="Vị trí hiện tại · bấm để tìm / nhảy tới bài (G)" aria-label="Mở tìm kiếm và nhảy tới bài"><span id="posNow">1</span><span class="pos-sep">/</span><span id="posTotal">__TOTAL_POSTS__</span></button>
    <nav class="hdr-tools" aria-label="Công cụ nhanh">
      <button class="hdr-tool" id="hSearch" type="button" title="Tìm bài (G)"><span data-ic="search"></span>Tìm <kbd>G</kbd></button>
      <button class="hdr-tool" id="hLayout" type="button" title="Đổi bố cục (V)"><span data-ic="grid" id="hLayoutIc"></span><span id="hLayoutLbl">Lưới</span> <kbd>V</kbd></button>
      <button class="hdr-tool" id="hRandom" type="button" title="Bài ngẫu nhiên (R)"><span data-ic="shuffle"></span>Ngẫu nhiên <kbd>R</kbd></button>
      <button class="hdr-tool" id="hTheme" type="button" title="Chọn theme (M)"><span data-ic="palette"></span>Theme <kbd>M</kbd></button>
    </nav>
  </div>
  <div class="chip-bar" id="chipBar" hidden>
    <span class="s-chip" role="status"><button class="chip-main" id="chipMain" type="button" title="Sửa nội dung lọc"><span data-ic="search"></span><b id="chipText"></b><em id="chipCount"></em></button><button class="chip-x" id="chipSave" type="button" title="Lưu bộ lọc này (B)" aria-label="Lưu bộ lọc này"><span data-ic="bookmark"></span></button><button class="chip-x" id="chipClear" type="button" title="Bỏ lọc tìm kiếm (Esc)" aria-label="Bỏ lọc tìm kiếm"><span data-ic="x"></span></button></span>
  </div>
  <div class="progress" aria-hidden="true"><i id="progressBar"></i></div>
</header>
<main class="feed" id="feed" aria-label="Danh sách bài"></main>
<div id="loadSentinel" aria-hidden="true"></div>
<div id="empty" hidden><p id="emptyMsg"></p><button class="btn" id="emptyReset" type="button">Xóa bộ lọc</button></div>
<noscript>Archive cần JavaScript để hiển thị.</noscript>

<nav class="controls" id="controls" aria-label="Điều khiển archive">
  <button class="tb collapse" id="collapseBtn" type="button" aria-label="Thu gọn thanh công cụ" title="Thu gọn thanh công cụ"><span data-ic="minus"></span></button>
  <div class="filter-wrap" id="filterWrap">
    <button class="tb" id="filterMenuToggle" type="button" aria-label="Mở bộ lọc" title="Bộ lọc" aria-expanded="false"><span data-ic="filter"></span><span class="lbl">Lọc</span></button>
    <div class="menu filter-pop" id="filterPop" role="group" aria-label="Bộ lọc">
      <div class="menu-h">Bộ lọc đã lưu</div>
      <div id="savedQuick"></div>
      <button class="item" id="savedManage" type="button"><span data-ic="bookmark"></span>Lưu / quản lý bộ lọc…</button>
      <div class="menu-sep"></div>
      <div class="menu-h">Loại nội dung</div>
      <label class="check"><input id="filterAll" type="checkbox" checked><span>Tất cả</span></label>
      <label class="check"><input class="type-check" data-kind="0" type="checkbox" checked><span>Ảnh</span><em id="cntImage"></em></label>
      <label class="check"><input class="type-check" data-kind="1" type="checkbox" checked><span>GIF</span><em id="cntGif"></em></label>
      <label class="check"><input class="type-check" data-kind="2" type="checkbox" checked><span>Video</span><em id="cntVideo"></em></label>
      <div id="folderSection" hidden>
        <div class="menu-sep"></div>
        <div class="menu-h">Thư mục</div>
        <label class="check"><input id="folderAll" type="checkbox" checked><span>Tất cả thư mục</span></label>
        <div id="folderList"></div>
      </div>
    </div>
  </div>
  <button class="tb" id="likedBtn" type="button" aria-label="Chỉ hiện bài đã thích" title="Bài đã thích (F)"><span data-ic="heart"></span><span class="lbl">Đã thích</span><span class="badge" id="likeCount">0</span></button>
  <button class="tb" id="jumpBtn" type="button" aria-label="Tìm bài hoặc media" title="Tìm bài (G)"><span data-ic="search"></span><span class="lbl">Tìm</span></button>
  <button class="tb" id="randomBtn" type="button" aria-label="Nhảy tới bài ngẫu nhiên" title="Bài ngẫu nhiên (R)"><span data-ic="shuffle"></span><span class="lbl">Ngẫu nhiên</span></button>
  <button class="tb accent" id="topBtn" type="button" aria-label="Lên đầu trang" title="Lên đầu (T)"><span data-ic="up"></span><span class="lbl">Top</span></button>
  <button class="tb" id="settingsBtn" type="button" aria-label="Cài đặt" title="Cài đặt" aria-expanded="false"><span data-ic="sliders"></span><span class="lbl">Thêm</span></button>
  <div class="menu settings" id="settingsMenu">
    <div class="row-split"><span>Phong cách</span><button class="pill" id="styleBtn" type="button"><span class="dot"></span><span id="styleLbl">Hiện đại</span></button></div>
    <div class="row-split"><span>Bố cục</span><div class="stepper" role="group" aria-label="Bố cục"><button id="viewFeed" type="button" title="Danh sách (V)" aria-label="Danh sách"><span data-ic="rows"></span></button><button id="viewGrid" type="button" title="Lưới (V)" aria-label="Lưới"><span data-ic="grid"></span></button></div></div>
    <label class="field" id="widthField">Độ rộng cột đọc <b id="widthVal"></b><input type="range" id="widthRange" min="480" max="1100" step="20"></label>
    <label class="field" id="colsField" hidden>Số cột lưới <b id="colsVal"></b><input type="range" id="colsRange" min="0" max="8" step="1"></label>
    <label class="field">Theme<select id="themeSelect"><option value="auto">Theo hệ thống</option>__THEME_OPTIONS__</select></label>
    <label class="check"><input id="reverseChk" type="checkbox"><span>Đảo thứ tự (cuối lên trước)</span></label>
    <label class="check"><input id="autoplayChk" type="checkbox"><span>Tự phát video (tắt tiếng) khi lướt tới</span></label>
    <label class="field">Thời gian mỗi ảnh khi trình chiếu<select id="slideSel"><option value="3">3 giây</option><option value="5">5 giây</option><option value="8">8 giây</option><option value="12">12 giây</option></select></label>
    <div class="menu-sep"></div>
    <button class="item" id="zipBtn" type="button" hidden><span data-ic="package"></span>File nén (zip / cbz)…</button>
    <button class="item" id="backupBtn" type="button"><span data-ic="download"></span>Sao lưu &amp; khôi phục</button>
    <button class="item" id="helpBtn" type="button"><span data-ic="help"></span>Phím tắt &amp; trợ giúp</button>
  </div>
</nav>
<div id="toast" role="status" aria-live="polite"></div>

<section id="lightbox" role="dialog" aria-modal="true" aria-label="Xem media phóng to" tabindex="-1">
  <div class="lb-need" id="lbNeed" hidden><span data-ic="package"></span><p id="lbNeedMsg"></p><button class="btn primary" id="lbNeedBtn" type="button">Chọn file nén…</button></div>
  <div class="lb-stage" id="lbStage">
    <img id="lbImg" alt="" draggable="false">
    <video id="lbVideo" controls playsinline preload="metadata" hidden></video>
    <div class="lb-spin"></div>
  </div>
  <div class="lb-top lb-ui">
    <span class="lb-count" id="lbCount"></span>
    <div class="lb-tools">
      <button class="lb-btn" id="lbSlide" type="button" title="Trình chiếu (S)" aria-label="Trình chiếu" aria-pressed="false"><span data-ic="play"></span></button>
      <button class="lb-btn" id="lbZoomOut" type="button" title="Thu nhỏ (−)" aria-label="Thu nhỏ"><span data-ic="zout"></span></button>
      <button class="lb-btn" id="lbZoomIn" type="button" title="Phóng to (+)" aria-label="Phóng to"><span data-ic="zin"></span></button>
      <button class="lb-btn" id="lbInfoBtn" type="button" title="Thông tin (I)" aria-label="Thông tin" aria-pressed="false"><span data-ic="info"></span></button>
      <a class="lb-btn" id="lbDl" title="Tải xuống (D)" aria-label="Tải xuống" download><span data-ic="download"></span></a>
      <a class="lb-btn" id="lbOpen" title="Mở tab mới (O)" aria-label="Mở trong tab mới" target="_blank" rel="noopener"><span data-ic="ext"></span></a>
      <button class="lb-btn" id="lbFull" type="button" title="Toàn màn hình (F)" aria-label="Toàn màn hình"><span data-ic="full"></span></button>
      <button class="lb-btn" id="lbLike" type="button" title="Thích (L)" aria-label="Thích bài viết" aria-pressed="false"><span data-ic="heart"></span></button>
      <button class="lb-btn" id="lbClose" type="button" title="Đóng (Esc)" aria-label="Đóng"><span data-ic="x"></span></button>
    </div>
  </div>
  <button class="lb-btn lb-nav lb-prev lb-ui" id="lbPrev" type="button" aria-label="Trước"><span data-ic="left"></span></button>
  <button class="lb-btn lb-nav lb-next lb-ui" id="lbNext" type="button" aria-label="Tiếp"><span data-ic="right"></span></button>
  <div class="lb-bottom lb-ui"><span id="lbName"></span></div>
  <div class="lb-info" id="lbInfo" hidden></div>
</section>

<section class="overlay search-overlay" id="searchDlg" role="dialog" aria-modal="true" aria-labelledby="searchTitle">
  <div class="sheet search-sheet">
    <div class="sheet-head"><h2 id="searchTitle">Tìm và nhảy tới bài</h2><button class="x-btn" id="searchClose" type="button" aria-label="Đóng tìm kiếm"><span data-ic="x"></span></button></div>
    <input id="searchQuery" type="search" maxlength="180" autocomplete="off" spellcheck="false" placeholder="Số bài, tên file, ghi chú…  (is:video · is:gif · is:multi · is:liked · is:note)">
    <div class="search-tools"><div class="search-count" id="searchCount" aria-live="polite"></div><button class="btn primary" id="searchApply" type="button" title="Chỉ hiện các bài khớp trong danh sách chính (Shift+Enter)"><span data-ic="filter"></span><span id="searchApplyLbl">Lọc danh sách</span></button></div>
    <div class="search-results" id="searchResults"></div>
  </div>
</section>

<section class="overlay" id="zipDlg" role="dialog" aria-modal="true" aria-labelledby="zipTitle">
  <div class="sheet" style="width:min(640px,100%)">
    <div class="sheet-head"><div><h2 id="zipTitle">File nén (zip / cbz)</h2><p>Ảnh/video bên trong được giải nén từng file một khi cần xem, không giải nén cả file nén.</p></div><button class="x-btn" id="zipClose" type="button" aria-label="Đóng"><span data-ic="x"></span></button></div>
    <p class="hint" id="zipMode"></p>
    <div class="btn-row" style="margin-top:0"><button class="btn primary" id="zipPickFilesBtn" type="button"><span data-ic="package"></span>Chọn file nén…</button><button class="btn" id="zipPickDirBtn" type="button"><span data-ic="folder"></span>Chọn thư mục chứa…</button></div>
    <div class="zip-drop" id="zipDrop">Hoặc kéo-thả các file .zip / .cbz vào trang</div>
    <div class="saved-list" id="zipList"></div>
    <input type="file" id="zipPickFiles" accept=".zip,.cbz,application/zip,application/vnd.comicbook+zip" multiple hidden>
    <input type="file" id="zipPickDir" webkitdirectory multiple hidden>
  </div>
</section>

<section class="overlay" id="savedDlg" role="dialog" aria-modal="true" aria-labelledby="savedTitle">
  <div class="sheet" style="width:min(600px,100%)">
    <div class="sheet-head"><div><h2 id="savedTitle">Bộ lọc đã lưu</h2><p>Lưu tổ hợp lọc đang bật để dùng lại chỉ với một cú bấm.</p></div><button class="x-btn" id="savedClose" type="button" aria-label="Đóng"><span data-ic="x"></span></button></div>
    <p class="hint" id="savedCurrent"></p>
    <div class="save-row"><input id="savedName" type="text" maxlength="60" autocomplete="off" spellcheck="false" placeholder="Tên bộ lọc"><button class="btn primary" id="savedSave" type="button"><span data-ic="bookmark"></span>Lưu</button></div>
    <div class="menu-sep" style="margin:16px 0 12px"></div>
    <div class="saved-list" id="savedList"></div>
  </div>
</section>

<section class="overlay" id="backupDlg" role="dialog" aria-modal="true" aria-labelledby="backupTitle">
  <div class="sheet" style="width:min(560px,100%)">
    <div class="sheet-head"><div><h2 id="backupTitle">Sao lưu &amp; khôi phục</h2><p>Bài đã thích, vị trí đang xem và bộ lọc đã lưu nằm trong trình duyệt. Sao lưu để chuyển sang máy khác.</p></div><button class="x-btn" id="backupClose" type="button" aria-label="Đóng"><span data-ic="x"></span></button></div>
    <p class="hint" id="backupStat"></p>
    <div class="btn-row" style="margin-top:0"><button class="btn primary" id="expFile" type="button"><span data-ic="download"></span>Tải file backup</button><button class="btn" id="expCopy" type="button"><span data-ic="copy"></span>Sao chép chuỗi</button></div>
    <div class="menu-sep" style="margin:16px 0"></div>
    <p class="hint">Khôi phục: chọn file backup hoặc dán chuỗi (Base64 của v2 vẫn dùng được). Bài yêu thích sẽ được gộp với bài hiện có.</p>
    <textarea id="impText" rows="4" placeholder="Dán chuỗi backup hoặc JSON…" spellcheck="false"></textarea>
    <div class="btn-row"><button class="btn" id="impFileBtn" type="button"><span data-ic="upload"></span>Chọn file…</button><button class="btn primary" id="impGo" type="button">Khôi phục</button><input type="file" id="impFile" accept=".json,.txt,application/json,text/plain" hidden></div>
  </div>
</section>

<section class="overlay" id="help" role="dialog" aria-modal="true" aria-labelledby="helpTitle">
  <div class="sheet">
    <div class="sheet-head"><div><h2 id="helpTitle">Phím tắt &amp; trợ giúp</h2><p>Điều khiển archive nhanh bằng bàn phím hoặc thanh công cụ.</p></div><div style="display:flex;gap:8px;align-items:center"><span class="ver">v__VERSION__</span><button class="x-btn" id="helpClose" type="button" aria-label="Đóng trợ giúp"><span data-ic="x"></span></button></div></div>
    <div class="shortcut-grid">
      <section class="shortcut-group"><h3>Duyệt bài</h3>
        <div class="sc"><span><b>Bài tiếp</b><small>Đi xuống một bài</small></span><kbd>J</kbd><kbd>↓</kbd></div>
        <div class="sc"><span><b>Bài trước</b><small>Quay lên một bài</small></span><kbd>K</kbd><kbd>↑</kbd></div>
        <div class="sc"><span><b>Tiến / lùi</b><small>Chuyển bài nhanh</small></span><kbd>Space</kbd><kbd>⇧ Space</kbd></div>
        <div class="sc"><span><b>Bài ngẫu nhiên</b><small>Nhảy tới một bài bất kỳ</small></span><kbd>R</kbd></div>
        <div class="sc"><span><b>Lên đầu</b><small>Về đầu archive</small></span><kbd>T</kbd></div>
      </section>
      <section class="shortcut-group"><h3>Công cụ</h3>
        <div class="sc"><span><b>Tìm / nhảy tới bài</b><small>Số bài, tên file, ghi chú, is:video…</small></span><kbd>G</kbd></div>
        <div class="sc"><span><b>Lọc danh sách theo tìm kiếm</b><small>Chỉ xem các bài khớp · Esc để bỏ lọc</small></span><kbd>⇧ Enter</kbd></div>
        <div class="sc"><span><b>Thích / lọc bài đã thích</b><small>Lưu bài yêu thích</small></span><kbd>L</kbd><kbd>F</kbd></div>
        <div class="sc"><span><b>Tìm trong file nén</b><small>Gõ is:zip để chỉ xem bài nằm trong .zip / .cbz</small></span></div>
        <div class="sc"><span><b>Bộ lọc đã lưu</b><small>Lưu, áp dụng, đổi tên, xóa</small></span><kbd>B</kbd></div>
        <div class="sc"><span><b>Đổi bố cục</b><small>Danh sách ⇄ lưới masonry</small></span><kbd>V</kbd></div>
        <div class="sc"><span><b>Đổi theme</b><small>Chọn giao diện màu</small></span><kbd>M</kbd></div>
        <div class="sc"><span><b>Sao lưu / khôi phục</b><small>File hoặc chuỗi Base64</small></span><kbd>E</kbd><kbd>I</kbd></div>
      </section>
      <section class="shortcut-group wide"><h3>Xem ảnh phóng to</h3>
        <div class="sc"><span><b>Media tiếp / trước</b><small>Vuốt ngang trên điện thoại</small></span><kbd>→</kbd><kbd>←</kbd></div>
        <div class="sc"><span><b>Phóng to / thu nhỏ</b><small>Cuộn chuột, chụm 2 ngón, chạm đúp</small></span><kbd>+</kbd><kbd>−</kbd><kbd>0</kbd></div>
        <div class="sc"><span><b>Trình chiếu</b><small>Tự chuyển ảnh</small></span><kbd>S</kbd></div>
        <div class="sc"><span><b>Thông tin file</b><small>Kích thước, dung lượng, ghi chú</small></span><kbd>I</kbd></div>
        <div class="sc"><span><b>Tải / mở tab mới</b></span><kbd>D</kbd><kbd>O</kbd></div>
        <div class="sc"><span><b>Toàn màn hình · Đóng</b><small>Vuốt xuống cũng đóng</small></span><kbd>F</kbd><kbd>Esc</kbd></div>
      </section>
    </div>
    <details class="changelog"><summary>Phiên bản v__VERSION__ · Có gì mới</summary><ul>
      <li>Lưới masonry cân cột thật, chọn số cột; ảnh có kích thước sẵn nên trang không bị nhảy khi tải.</li>
      <li>Xem ảnh: phóng to/kéo, chụm 2 ngón, trình chiếu, toàn màn hình, tải xuống, bảng thông tin, tải trước ảnh kế bên.</li>
      <li>Tìm kiếm có toán tử (is:video, is:gif, is:multi, is:liked, is:note), duyệt bằng phím mũi tên.</li>
      <li>Mới ở 3.3: xem trực tiếp ảnh/video trong file <b>.zip / .cbz</b> như thư mục ảo (giải nén từng file khi cần bằng unzipit, tự giải phóng bộ nhớ).</li>
      <li>Mới ở 3.2: <b>bộ lọc đã lưu</b> (thêm, xóa, đổi tên, có trong file sao lưu), icon Màn hình chính iOS, loại trừ thư mục khi quét.</li>
      <li>Mới ở 3.1: nút <b>Lọc danh sách</b> (Shift+Enter) chỉ hiện các bài khớp tìm kiếm, kèm thanh trạng thái để sửa hoặc bỏ lọc.</li>
      <li>Bài ngẫu nhiên, đảo thứ tự, thanh tiến độ, liên kết trực tiếp tới bài (#p123), nút Back đóng ảnh trên điện thoại.</li>
      <li>Sao lưu bằng file, tự phát video khi lướt tới, thêm theme Dracula / Solarized / Midnight / Sakura.</li>
    </ul></details>
    <p class="formats"><b>Định dạng media.</b> Ảnh: JPG/JPEG, PNG/APNG, WEBP, AVIF, BMP, SVG, JXL, HEIC/HEIF. GIF có bộ lọc riêng. Video: MP4, WEBM, MOV, M4V, OGV; khả năng phát tùy codec của trình duyệt.</p>
  </div>
</section>

__UNZIPIT_INLINE__
<script>
'use strict';
const POSTS=__POSTS__,BASE=__BASE__,ARCHIVES=__ARCHIVES__,ARCHIVE_TITLE=__ARCHIVE_TITLE_JSON__,FLAGS=__FLAGS__,DEFAULTS=__DEFAULTS__;
const $=id=>document.getElementById(id);
const VIDEO_RE=/\.(mp4|webm|mov|m4v|ogv)$/i,GIF_RE=/\.gif$/i;
const kindOf=n=>VIDEO_RE.test(n)?2:GIF_RE.test(n)?1:0;
const ic=(n,c)=>`<svg class="ic${c?' '+c:''}" aria-hidden="true"><use href="#i-${n}"/></svg>`;
const baseName=p=>p.slice(p.lastIndexOf('/')+1);
const urlOf=rel=>BASE+rel.split('/').map(encodeURIComponent).join('/');
const clamp=(v,a,b)=>Math.min(b,Math.max(a,v));
const K=k=>`tumblr_archive_${FINGERPRINT}_${k}`;
const STORE={likes:K('liked_posts_v2'),position:K('position_v2'),grid:K('grid_v1'),style:K('style_v1'),prefs:K('prefs_v3'),saved:K('saved_filters_v1')};
const feed=$('feed'),sentinel=$('loadSentinel'),header=$('siteHeader'),toastEl=$('toast');
document.querySelectorAll('[data-ic]').forEach(el=>el.insertAdjacentHTML('afterbegin',ic(el.dataset.ic)));

/* ---------- Dữ liệu dẫn xuất (một lượt, không chạm DOM) ---------- */
const ID_INDEX=new Map(),KIND_COUNT=[0,0,0],FOLDER_COUNT=new Map();
for(let i=0;i<POSTS.length;i++){const p=POSTS[i];ID_INDEX.set(p.id,i);p.k=p.m.map(m=>kindOf(m[0]));p.mask=0;for(const k of p.k){p.mask|=1<<k;KIND_COUNT[k]++}if(p.f)FOLDER_COUNT.set(p.f,(FOLDER_COUNT.get(p.f)||0)+1)}
const FOLDER_PATHS=[...FOLDER_COUNT.keys()];
const MEDIA_TOTAL=KIND_COUNT[0]+KIND_COUNT[1]+KIND_COUNT[2];

/* ---------- Lưu trữ & tuỳ chọn ---------- */
function save(key,val){try{localStorage.setItem(key,JSON.stringify(val));return true}catch(e){toast('Không lưu được dữ liệu trình duyệt');return false}}
const prefs=Object.assign({view:DEFAULTS.view,cols:DEFAULTS.cols,width:DEFAULTS.width,reverse:false,autoplay:DEFAULTS.autoplay,slide:5,style:'modern'},(()=>{
  const saved=readJSON(STORE.prefs,null);if(saved&&typeof saved==='object')return saved;
  const legacy={};if(readJSON(STORE.grid,false)===true)legacy.view='grid';const st=readJSON(STORE.style,null);if(st==='classic'||st==='modern')legacy.style=st;return legacy})());
if(prefs.view!=='grid')prefs.view='feed';
const savePrefs=()=>save(STORE.prefs,prefs);
const liked=new Set(readJSON(STORE.likes,[]).filter(x=>typeof x==='string'&&ID_INDEX.has(x)));
let typeFilter=new Set([0,1,2]),folderFilter=new Set(FOLDER_PATHS),onlyLiked=false,likedReturn=null,searchFilter=null;
let view=[],viewPos=new Int32Array(POSTS.length),cursor=0,focusIdx=0,restoreLock=true,colN=1,cols=[],colH=[];
const cards=new Map();
let toastTimer;
function toast(msg){toastEl.textContent=msg;toastEl.classList.add('show');clearTimeout(toastTimer);toastTimer=setTimeout(()=>toastEl.classList.remove('show'),2300)}
async function copyText(text){try{await navigator.clipboard.writeText(text);return true}catch(e){try{const ta=document.createElement('textarea');ta.value=text;ta.style.cssText='position:fixed;opacity:0';document.body.append(ta);ta.select();const ok=document.execCommand('copy');ta.remove();return ok}catch(e2){return false}}}
function fmtSize(b){if(!Number.isFinite(b)||b<0)return 'Không rõ';if(b<1024)return b+' B';const u=['KB','MB','GB','TB'];let v=b/1024,i=0;while(v>=1024&&i<u.length-1){v/=1024;i++}return new Intl.NumberFormat('vi-VN',{maximumFractionDigits:1}).format(v)+' '+u[i]}
function fmtDate(s){if(!s)return 'Ngày không rõ';const d=new Date(s*1000),p=n=>String(n).padStart(2,'0');return `${p(d.getDate())}/${p(d.getMonth()+1)}/${d.getFullYear()} ${p(d.getHours())}:${p(d.getMinutes())}`}
function kindLabel(kinds){return kinds}

/* ---------- Header ---------- */
let hdrTick=false;
function measureHeader(){document.documentElement.style.setProperty('--hdr-off',(document.body.classList.contains('header-not-sticky')?12:header.offsetHeight)+'px')}
measureHeader();if('ResizeObserver'in window)new ResizeObserver(measureHeader).observe(header);
$('summary').textContent=`${POSTS.length} bài · ${MEDIA_TOTAL} media`;
document.title=`${ARCHIVE_TITLE} (${POSTS.length} bài)`;
function updatePos(){const pos=viewPos[focusIdx];$('posNow').textContent=focusIdx+1;$('progressBar').style.transform=`scaleX(${view.length>1&&pos>=0?(pos+1)/view.length:0})`}

/* ---------- Thẻ bài ---------- */
const badgeHTML=(count,kinds)=>{const u=[...new Set(kinds)];const kind=count===1?u[0]:u.length===1?u[0]:'stack';const names=['image','gif','video'];const icon=count===1||u.length===1?names[u[0]]:'stack';const label=count===1?['Ảnh','GIF','Video'][u[0]]:u.length===1?`${count} ${['ảnh','GIF','video'][u[0]]}`:`${count} media`;return ic(icon)+`<span>${label}</span>`};
const videoIO='IntersectionObserver'in window?new IntersectionObserver(es=>{for(const e of es){const v=e.target;if(e.isIntersecting&&e.intersectionRatio>=.6){if(v.paused){v.muted=true;v.dataset.auto='1';v.play().catch(()=>{})}}else if(v.dataset.auto&&!v.paused){v.pause()}}},{threshold:[0,.6]}):null;
function makeCard(idx,grid){
  const p=POSTS[idx],multi=p.m.length>1,shown=[];
  for(let j=0;j<p.m.length;j++)if(typeFilter.has(p.k[j]))shown.push(j);
  if(!shown.length)return null;
  const card=document.createElement('article');card.className='post'+(multi?' multi':'')+(p.z!=null?' zipped':'');card.dataset.idx=idx;card.id='p'+(idx+1);
  const on=liked.has(p.id);if(on)card.classList.add('is-liked-post');
  const head=document.createElement('div');head.className='post-head';
  const no=document.createElement('button');no.type='button';no.className='post-no';no.textContent='#'+(idx+1);no.title='Sao chép liên kết tới bài này';
  const badge=document.createElement('span');badge.className='post-badge';
  badge.innerHTML=grid&&shown.length>1?ic('stack')+`<span>+${shown.length-1}</span>`:badgeHTML(shown.length,shown.map(j=>p.k[j]));
  head.append(no);
  if(!(grid&&shown.length===1&&p.k[shown[0]]===0))head.append(badge);
  const media=document.createElement('div');media.className='post-media';
  let est=90,ar=1;
  const build=grid?[shown[0]]:shown;
  build.forEach((j,n)=>{
    const m=p.m[j],[rel,w,h,size,ct]=m,kind=p.k[j],url=urlOf(rel),item=document.createElement('div');
    item.className='media-item';item.dataset.j=j;
    if(n===0){ar=w&&h?clamp(w/h,.62,1.9):(kind===2?16/9:1);if(grid)item.style.setProperty('--ar',ar.toFixed(4))}
    if(multi&&!grid){const nn=document.createElement('span');nn.className='media-no';nn.textContent=`${j+1}/${p.m.length}`;item.append(nn)}
    if(kind===2){
      if(grid){
        if(FLAGS.thumbs&&!m[5]){const v=document.createElement('video');v.muted=true;v.playsInline=true;v.preload='metadata';v.src=url+'#t=0.1';item.append(v)}else{const ph=document.createElement('div');ph.className='vid-ph';ph.innerHTML=ic('video');item.append(ph)}
        const pb=document.createElement('span');pb.className='play-badge';pb.innerHTML=ic('play');item.append(pb);
      }else{
        const wrap=document.createElement('div');wrap.className='video-wrap';
        const v=document.createElement('video');v.controls=true;v.playsInline=true;v.preload=FLAGS.thumbs&&!m[5]?'metadata':'none';if(!m[5])v.src=FLAGS.thumbs?url+'#t=0.1':url;
        v.setAttribute('aria-label',`Video của bài ${idx+1}`);if(prefs.autoplay){v.loop=true;v.muted=true}
        v.addEventListener('error',()=>toast('Không phát được video: '+baseName(rel)),{once:true});
        if(m[5]){v.dataset.zp=idx;v.dataset.zj=j;v.dataset.zauto='0';v.dataset.name=baseName(rel);zipWatch(v)}else if(prefs.autoplay&&videoIO)videoIO.observe(v);
        const open=document.createElement('button');open.type='button';open.className='media-open';open.dataset.act='open';open.innerHTML=ic('full')+'Phóng to';open.setAttribute('aria-label','Mở video trong trình xem');
        wrap.append(v,open);
        if(m[5]){const zp=document.createElement('button');zp.type='button';zp.className='zip-play';zp.dataset.act='zplay';zp.setAttribute('aria-label','Giải nén và phát video');zp.innerHTML=ic('play');wrap.append(zp)}
        item.append(wrap);est+=Math.round(FEED_W()*9/16);
      }
    }else{
      const img=document.createElement('img');img.decoding='async';img.alt=`Ảnh ${idx+1}${multi?`, media ${j+1}`:''}`;
      if(w&&h){img.width=w;img.height=h;est+=Math.min(FEED_W()*h/w,innerHeight*.82)}else{img.className='nodim';est+=420}
      if(m[5]){img.alt='';img.dataset.alt=`Ảnh ${idx+1}${multi?`, media ${j+1}`:''}`;img.dataset.zp=idx;img.dataset.zj=j;img.dataset.name=baseName(rel);zipWatch(img);item.append(img)}
      else{
        const first=idx===view[0]&&n===0;
        if(first){img.fetchPriority='high'}else img.loading='lazy';
        img.src=url;item.append(img);
      }
    }
    if(!grid){
      const parts=[];if(FLAGS.created)parts.push(fmtDate(ct));if(FLAGS.filename)parts.push(baseName(rel));if(FLAGS.dims&&w&&h)parts.push(`${w}×${h}`);if(FLAGS.size)parts.push('Dung lượng: '+fmtSize(size));
      if(parts.length){const meta=document.createElement('div');meta.className='media-meta';meta.replaceChildren(...parts.map(t=>{const d=document.createElement('div');d.textContent=t;return d}));item.append(meta)}
      const note=p.n&&p.n[j];if(note){const nd=document.createElement('div');nd.className='media-note';nd.innerHTML=note;item.append(nd)}
    }
    media.append(item);
  });
  const foot=document.createElement('footer');foot.className='post-foot';
  if(p.s){const src=document.createElement('span');src.className='post-source';src.title='Thư mục: '+p.s;src.innerHTML=ic('folder');const t=document.createElement('span');t.textContent=p.s;src.append(t);foot.append(src)}
  if(p.z!=null){const z=document.createElement('span');z.className='post-source post-zip';z.title='File nén: '+ARCHIVES[p.z][0];z.innerHTML=ic('package');const zt=document.createElement('span');zt.textContent=baseName(ARCHIVES[p.z][0]);z.append(zt);foot.append(z)}
  const actions=document.createElement('div');actions.className='post-actions';
  actions.innerHTML=`<button type="button" class="btn-locate" data-act="locate" aria-label="Mở bài này tại vị trí trong archive đầy đủ">Về vị trí gốc</button><button type="button" class="like" data-act="like" aria-label="Thích bài viết" aria-pressed="${on}">${ic('heart')}</button>`;
  actions.querySelector('.like').classList.toggle('is-liked',on);
  foot.append(actions);
  card.append(head,media,foot);
  if(!grid)card.style.setProperty('--est',Math.round(est)+'px');
  card._ar=ar;
  return card;
}
/* Chiều rộng cột đọc chỉ đo MỘT lần mỗi lần rebuild — đọc layout trong vòng lặp dựng thẻ sẽ buộc trình duyệt reflow từng ảnh. */
let feedWidthCache=720;
const FEED_W=()=>feedWidthCache;
function measureFeedWidth(){feedWidthCache=Math.min(feed.clientWidth||innerWidth,prefs.width||720)}

/* ---------- Render theo lô + masonry ---------- */
const isGrid=()=>prefs.view==='grid';
function calcCols(){if(prefs.cols>0)return clamp(prefs.cols,1,10);const w=feed.clientWidth||innerWidth;return clamp(Math.floor((w+14)/(w<600?170:250)),2,8)}
/* Bộ lọc thuần túy: dùng cho danh sách chính, đếm số bài của bộ lọc đã lưu. f = {q (đã parse|null), types:Set, folders:Set, liked:bool} */
function filterPosts(f){
  const out=[],allFolders=f.folders.size===FOLDER_PATHS.length;let mask=0;f.types.forEach(k=>mask|=1<<k);
  if(f.q)buildIndex();
  for(let i=0;i<POSTS.length;i++){const p=POSTS[i];if(!(p.mask&mask))continue;if(!allFolders&&p.f&&!f.folders.has(p.f))continue;if(f.liked&&!liked.has(p.id))continue;if(f.q&&!matchPost(i,f.q))continue;out.push(i)}
  return out;
}
function computeView(){
  const out=filterPosts({q:searchFilter&&searchFilter.q,types:typeFilter,folders:folderFilter,liked:onlyLiked});
  if(prefs.reverse)out.reverse();
  view=out;viewPos.fill(-1);for(let i=0;i<out.length;i++)viewPos[out[i]]=i;
}
function rebuild(){
  videoIO?.disconnect();releaseAllZipEls();
  feed.replaceChildren();cards.clear();cursor=0;measureFeedWidth();
  const grid=isGrid();feed.classList.toggle('grid',grid);
  if(grid){colN=calcCols();cols=[];colH=new Array(colN).fill(0);for(let i=0;i<colN;i++){const c=document.createElement('div');c.className='col';feed.append(c);cols.push(c)}}
  const empty=view.length===0;$('empty').hidden=!empty;sentinel.hidden=empty;
  if(empty)$('emptyMsg').textContent=searchFilter?'Không có bài nào khớp tìm kiếm và bộ lọc hiện tại.':onlyLiked&&!liked.size?'Bạn chưa thích bài nào. Bấm biểu tượng trái tim ở mỗi bài để lưu lại.':POSTS.length?'Không có bài nào khớp bộ lọc hiện tại.':'Không tìm thấy ảnh hoặc video trong thư mục media đã chọn hoặc các thư mục con.';
  $('emptyReset').hidden=!(searchFilter||onlyLiked||typeFilter.size<3||folderFilter.size<FOLDER_PATHS.length);
  updateSearchChip();renderSavedQuick();
  renderMore(grid?colN*6:12);
  fillNearViewport();updateLikeCount();updatePos();
}
function renderMore(n){
  const grid=isGrid(),end=Math.min(view.length,cursor+n),added=[];
  for(;cursor<end;cursor++){
    const idx=view[cursor],card=makeCard(idx,grid);
    if(!card)continue;
    cards.set(idx,card);added.push(card);
    if(grid){let c=0;for(let i=1;i<colN;i++)if(colH[i]<colH[c])c=i;cols[c].append(card);colH[c]+=1/card._ar+.05}else feed.append(card);
  }
  for(const card of added)card.querySelectorAll('img').forEach(im=>{if(im.complete&&im.naturalWidth)im.classList.add('loaded')});
  sentinel.hidden=cursor>=view.length;
}
function ensureRendered(pos){while(cursor<=pos&&cursor<view.length)renderMore(64)}
function fillNearViewport(){
  if(cursor>=view.length)return;
  if(sentinel.getBoundingClientRect().top<innerHeight+1800){renderMore(isGrid()?colN*3:8);requestAnimationFrame(fillNearViewport)}
}
if('IntersectionObserver'in window)new IntersectionObserver(es=>{if(es.some(e=>e.isIntersecting))fillNearViewport()},{rootMargin:'1800px 0px'}).observe(sentinel);
feed.addEventListener('load',e=>{if(e.target.tagName==='IMG')e.target.classList.add('loaded')},true);
feed.addEventListener('error',e=>{const t=e.target;if(t.tagName==='IMG'){t.classList.add('broken','loaded');t.alt='Không tải được: '+(t.dataset.name||decodeURIComponent(t.src.slice(t.src.lastIndexOf('/')+1)))}},true);
document.addEventListener('play',e=>{if(e.target.tagName==='VIDEO'&&e.target!==$('lbVideo'))document.querySelectorAll('video').forEach(v=>{if(v!==e.target&&!v.paused)v.pause()})},true);

/* ---------- Tương tác trong feed (ủy quyền sự kiện) ---------- */
feed.addEventListener('click',e=>{
  const card=e.target.closest('.post');if(!card)return;const idx=+card.dataset.idx,p=POSTS[idx];
  const actEl=e.target.closest('[data-act]'),act=actEl&&actEl.dataset.act;
  if(act==='like'){toggleLike(p.id);const b=actEl;b.classList.remove('pop');void b.offsetWidth;b.classList.add('pop');return}
  if(act==='locate'){leaveLiked(idx);toast('Đã mở bài tại vị trí trong archive');return}
  if(act==='open'){openLightbox(idx,+actEl.closest('.media-item').dataset.j);return}
  if(act==='zplay'){const v=actEl.parentElement.querySelector('video');if(v)zipPlay(v);return}
  if(act==='zipneed'){openZipDlg(+actEl.dataset.ai);return}
  if(e.target.closest('.post-no')){const link=location.href.split('#')[0]+'#p'+(idx+1);copyText(link).then(ok=>toast(ok?`Đã sao chép liên kết bài ${idx+1}`:'Không sao chép được liên kết'));return}
  const item=e.target.closest('.media-item');
  if(item&&(e.target.tagName==='IMG'||(isGrid()&&!e.target.closest('.like'))))openLightbox(idx,+item.dataset.j);
});
function toggleLike(id){
  const on=!liked.has(id);on?liked.add(id):liked.delete(id);save(STORE.likes,[...liked]);
  const idx=ID_INDEX.get(id),card=cards.get(idx);
  if(card){card.classList.toggle('is-liked-post',on);const b=card.querySelector('.like');b.classList.toggle('is-liked',on);b.setAttribute('aria-pressed',String(on))}
  updateLikeCount();if(lb.open)syncLbLike();
}
function updateLikeCount(){$('likeCount').textContent=liked.size;$('likedBtn').classList.toggle('active',onlyLiked);document.body.classList.toggle('only-liked',onlyLiked)}

/* ---------- Điều hướng bài ---------- */
function gotoPost(idx,opt){
  opt=opt||{};const block=opt.block||'start';
  if(viewPos[idx]<0){resetFilters(true);if(viewPos[idx]<0)return null}
  ensureRendered(viewPos[idx]);
  const el=cards.get(idx);if(!el)return null;
  el.scrollIntoView({block,behavior:opt.smooth?'smooth':'instant'});
  focusIdx=idx;updatePos();
  if(!opt.smooth){requestAnimationFrame(()=>{if(el.isConnected)el.scrollIntoView({block,behavior:'instant'})});setTimeout(()=>{if(el.isConnected){el.scrollIntoView({block,behavior:'instant'});noteScroll()}},120)}
  return el;
}
function navigatePost(dir){
  if(!view.length)return;let pos=viewPos[focusIdx];if(pos<0)pos=0;
  const next=clamp(pos+dir,0,view.length-1);ensureRendered(next);
  const idx=view[next],el=cards.get(idx);if(!el)return;
  focusIdx=idx;updatePos();el.scrollIntoView({block:isGrid()?'center':'start',behavior:'smooth'});
}
function randomPost(){
  if(!view.length){toast('Không có bài nào để chọn');return}
  const idx=view[Math.floor(Math.random()*view.length)];
  gotoPost(idx,{block:isGrid()?'center':'start'});toast(`Bài ngẫu nhiên #${idx+1}`);
}
function resetFilters(silent){
  typeFilter=new Set([0,1,2]);folderFilter=new Set(FOLDER_PATHS);onlyLiked=false;likedReturn=null;searchFilter=null;
  syncFilterUI();computeView();rebuild();if(!silent)window.scrollTo(0,0);
}
function applyFilters(){
  const keep=focusIdx;computeView();rebuild();
  if(viewPos[keep]>=0)gotoPost(keep,{block:isGrid()?'center':'start'});else window.scrollTo(0,0);
}
function toggleLiked(){
  if(!onlyLiked){likedReturn=focusIdx;onlyLiked=true;computeView();rebuild();window.scrollTo(0,0);if(!liked.size)toast('Chưa có bài nào được thích')}
  else{onlyLiked=false;const back=likedReturn;likedReturn=null;computeView();rebuild();if(back!=null&&viewPos[back]>=0)gotoPost(back);else window.scrollTo(0,0)}
  updateLikeCount();
}
function leaveLiked(idx){if(onlyLiked){onlyLiked=false;likedReturn=null;computeView();rebuild()}gotoPost(idx)}

/* ---------- Theo dõi cuộn: bài hiện tại, tiến độ, lưu vị trí ---------- */
let lastDetect=0,settleTimer,savedHash='';
function detectFocus(){
  for(const f of [.5,.35,.65,.2,.8]){
    const el=document.elementFromPoint(innerWidth*f,Math.min(innerHeight*.4,400)),card=el&&el.closest&&el.closest('.post');
    if(card){const idx=+card.dataset.idx;if(idx!==focusIdx){focusIdx=idx;updatePos()}return card}
  }
  return null;
}
function savePosition(){
  if(onlyLiked||restoreLock||!view.length)return;const card=cards.get(focusIdx);if(!card)return;
  save(STORE.position,{id:POSTS[focusIdx].id,index:focusIdx,top:Math.round(card.getBoundingClientRect().top),savedAt:Date.now()});
  const h='#p'+(focusIdx+1);if(h!==savedHash){savedHash=h;try{history.replaceState(history.state,'',h)}catch(e){}}
}
function noteScroll(){clearTimeout(settleTimer);settleTimer=setTimeout(()=>{detectFocus();savePosition()},220)}
addEventListener('scroll',()=>{
  if(!hdrTick){hdrTick=true;requestAnimationFrame(()=>{hdrTick=false;if(!document.body.classList.contains('header-not-sticky'))header.classList.toggle('compact',scrollY>40);const now=performance.now();if(now-lastDetect>120){lastDetect=now;detectFocus()}})}
  noteScroll();
},{passive:true});
addEventListener('pagehide',()=>{restoreLock=false;savePosition()});
let resizeTimer;addEventListener('resize',()=>{clearTimeout(resizeTimer);resizeTimer=setTimeout(()=>{if(isGrid()&&calcCols()!==colN){const keep=focusIdx;rebuild();if(viewPos[keep]>=0)gotoPost(keep,{block:'center'})}},220)});

/* ---------- Theme, phong cách, bố cục ---------- */
function applyStyle(v,persist){prefs.style=v==='classic'?'classic':'modern';document.body.classList.toggle('style-classic',prefs.style==='classic');$('styleLbl').textContent=prefs.style==='modern'?'Hiện đại':'Cổ điển';if(persist)savePrefs();measureHeader()}
function syncViewUI(){
  const g=isGrid();$('viewFeed').classList.toggle('on',!g);$('viewGrid').classList.toggle('on',g);
  $('widthField').hidden=g;$('colsField').hidden=!g;
  $('hLayoutLbl').textContent=g?'Danh sách':'Lưới';$('hLayoutIc').innerHTML=ic(g?'rows':'grid');
  $('widthRange').value=prefs.width;$('widthVal').textContent=prefs.width+' px';
  $('colsRange').value=prefs.cols;$('colsVal').textContent=prefs.cols>0?prefs.cols:'Tự động';
  document.documentElement.style.setProperty('--feed-w',prefs.width+'px');
}
function setView(v){
  if(prefs.view===v)return;const keep=focusIdx;prefs.view=v;savePrefs();syncViewUI();rebuild();
  if(viewPos[keep]>=0)gotoPost(keep,{block:'center'});
}
$('viewFeed').onclick=()=>setView('feed');$('viewGrid').onclick=()=>setView('grid');
$('hLayout').onclick=()=>setView(isGrid()?'feed':'grid');
$('widthRange').addEventListener('input',e=>{prefs.width=+e.target.value;syncViewUI()});$('widthRange').addEventListener('change',savePrefs);
$('colsRange').addEventListener('input',e=>{prefs.cols=+e.target.value;$('colsVal').textContent=prefs.cols>0?prefs.cols:'Tự động'});
$('colsRange').addEventListener('change',()=>{savePrefs();if(isGrid()){const keep=focusIdx;rebuild();if(viewPos[keep]>=0)gotoPost(keep,{block:'center'})}});
$('reverseChk').checked=prefs.reverse;$('reverseChk').addEventListener('change',e=>{prefs.reverse=e.target.checked;savePrefs();applyFilters();toast(prefs.reverse?'Đã đảo thứ tự':'Thứ tự mặc định')});
$('autoplayChk').checked=prefs.autoplay;$('autoplayChk').addEventListener('change',e=>{prefs.autoplay=e.target.checked;savePrefs();const keep=focusIdx;rebuild();if(viewPos[keep]>=0)gotoPost(keep)});
$('slideSel').value=String(prefs.slide);$('slideSel').addEventListener('change',e=>{prefs.slide=+e.target.value;savePrefs();slideTick()});
$('styleBtn').onclick=()=>applyStyle(prefs.style==='modern'?'classic':'modern',true);
$('themeSelect').addEventListener('change',e=>applyTheme(e.target.value,true));
$('themeSelect').value=themeChoice;

/* ---------- Thanh điều khiển & menu ---------- */
const controls=$('controls'),settingsMenu=$('settingsMenu'),settingsBtn=$('settingsBtn'),filterPop=$('filterPop'),filterToggle=$('filterMenuToggle');
function closeSettings(){settingsMenu.classList.remove('open');settingsBtn.setAttribute('aria-expanded','false')}
function closeFilter(){filterPop.classList.remove('open');filterToggle.setAttribute('aria-expanded','false')}
settingsBtn.onclick=e=>{e.stopPropagation();closeFilter();const o=settingsMenu.classList.toggle('open');settingsBtn.setAttribute('aria-expanded',String(o))};
filterToggle.onclick=e=>{e.stopPropagation();closeSettings();const o=filterPop.classList.toggle('open');filterToggle.setAttribute('aria-expanded',String(o))};
$('collapseBtn').onclick=()=>{const c=controls.classList.toggle('collapsed'),b=$('collapseBtn');b.innerHTML=ic(c?'plus':'minus');b.title=c?'Mở rộng thanh công cụ':'Thu gọn thanh công cụ';b.setAttribute('aria-label',b.title);closeSettings();closeFilter()};
document.addEventListener('click',e=>{if(!controls.contains(e.target)){closeSettings();closeFilter()}});
$('likedBtn').onclick=toggleLiked;$('jumpBtn').onclick=()=>openSearch();$('hSearch').onclick=()=>openSearch();$('posChip').onclick=()=>openSearch();
$('topBtn').onclick=()=>scrollTo({top:0,behavior:'smooth'});$('randomBtn').onclick=randomPost;$('hRandom').onclick=randomPost;
function openThemeSettings(){closeFilter();settingsMenu.classList.add('open');settingsBtn.setAttribute('aria-expanded','true');$('themeSelect').focus()}
$('hTheme').onclick=e=>{e.stopPropagation();openThemeSettings()};
$('emptyReset').onclick=()=>resetFilters();

/* Bộ lọc */
function buildFilterUI(){
  $('cntImage').textContent=KIND_COUNT[0];$('cntGif').textContent=KIND_COUNT[1];$('cntVideo').textContent=KIND_COUNT[2];
  if(FOLDER_PATHS.length<2)return;$('folderSection').hidden=false;
  const list=$('folderList');
  for(const f of FOLDER_PATHS){const l=document.createElement('label');l.className='check';const i=document.createElement('input');i.type='checkbox';i.className='folder-check';i.dataset.f=f;i.checked=true;const s=document.createElement('span');s.textContent=f;const c=document.createElement('em');c.textContent=FOLDER_COUNT.get(f);l.append(i,s,c);list.append(l);
    i.addEventListener('change',()=>{i.checked?folderFilter.add(f):folderFilter.delete(f);syncFilterUI();applyFilters()})}
  $('folderAll').addEventListener('change',e=>{folderFilter=new Set(e.target.checked?FOLDER_PATHS:[]);syncFilterUI();applyFilters()});
}
function syncFilterUI(){
  $('filterAll').checked=typeFilter.size===3;document.querySelectorAll('.type-check').forEach(i=>i.checked=typeFilter.has(+i.dataset.kind));
  const fa=$('folderAll');fa.checked=FOLDER_PATHS.length>0&&folderFilter.size===FOLDER_PATHS.length;fa.indeterminate=folderFilter.size>0&&folderFilter.size<FOLDER_PATHS.length;
  document.querySelectorAll('.folder-check').forEach(i=>i.checked=folderFilter.has(i.dataset.f));
  filterToggle.classList.toggle('accent',typeFilter.size<3||folderFilter.size<FOLDER_PATHS.length);
}
$('filterAll').addEventListener('change',e=>{typeFilter=new Set(e.target.checked?[0,1,2]:[]);syncFilterUI();applyFilters()});
document.querySelectorAll('.type-check').forEach(i=>i.addEventListener('change',()=>{const k=+i.dataset.kind;i.checked?typeFilter.add(k):typeFilter.delete(k);syncFilterUI();applyFilters()}));
buildFilterUI();

/* ---------- Tìm kiếm ---------- */
const searchDlg=$('searchDlg'),searchQuery=$('searchQuery'),searchResults=$('searchResults'),searchCount=$('searchCount');
let searchIndex=null,searchLimit=60,searchSel=0,searchHits=[];
const ENT={'&amp;':'&','&lt;':'<','&gt;':'>','&quot;':'"','&#x27;':"'",'&#39;':"'"};
function buildIndex(){
  if(searchIndex)return;
  searchIndex=POSTS.map((p,i)=>{
    const names=p.m.map(m=>baseName(m[0])+(m[5]?' '+m[5][1]+' '+baseName(ARCHIVES[m[5][0]][0]):'')).join(' ');
    const notes=p.n?Object.values(p.n).map(h=>h.replace(/<[^>]+>/g,' ').replace(/&(?:amp|lt|gt|quot|#x27|#39);/g,m=>ENT[m])).join(' '):'';
    return `${i+1} ${p.id} ${names} ${p.f||''} ${notes}`.toLocaleLowerCase();
  });
}
function syncVV(){const v=window.visualViewport;if(!v)return;const r=document.documentElement.style;r.setProperty('--vv-height',v.height+'px');r.setProperty('--vv-top',v.offsetTop+'px')}
syncVV();window.visualViewport?.addEventListener('resize',syncVV,{passive:true});window.visualViewport?.addEventListener('scroll',syncVV,{passive:true});
function parseQuery(raw){
  const q={text:[],kinds:0,multi:false,liked:false,note:false,zip:false,num:null};
  for(const tok of raw.toLocaleLowerCase().split(/\s+/).filter(Boolean)){
    if(tok==='is:video')q.kinds|=4;else if(tok==='is:gif')q.kinds|=2;else if(tok==='is:image'||tok==='is:photo')q.kinds|=1;
    else if(tok==='is:zip'||tok==='is:cbz')q.zip=true;else if(tok==='is:multi')q.multi=true;else if(tok==='is:liked')q.liked=true;else if(tok==='is:note')q.note=true;
    else q.text.push(tok.replace(/^#/,''));
  }
  if(q.text.length===1&&/^\d+$/.test(q.text[0])&&!q.kinds&&!q.multi&&!q.liked&&!q.note&&!q.zip)q.num=Number(q.text[0]);
  return q;
}
/* Một vị từ dùng chung cho hộp tìm kiếm VÀ bộ lọc danh sách. */
function matchPost(i,q){
  const p=POSTS[i];
  if(q.num!==null)return i===q.num-1;
  if(q.kinds&&!(p.mask&q.kinds))return false;
  if(q.multi&&p.m.length<2)return false;
  if(q.liked&&!liked.has(p.id))return false;
  if(q.note&&!p.n)return false;
  if(q.zip&&p.z==null)return false;
  for(const t of q.text)if(!searchIndex[i].includes(t))return false;
  return true;
}
function runSearch(){
  buildIndex();const raw=searchQuery.value.trim(),q=parseQuery(raw),hits=[],has=raw.length>0;
  if(q.num!==null){if(q.num>=1&&q.num<=POSTS.length)hits.push(q.num-1)}
  else for(let i=0;i<POSTS.length;i++){if(!matchPost(i,q))continue;hits.push(i);if(!has&&hits.length>=searchLimit)break}
  searchHits=hits;renderSearch(raw);
}
function renderSearch(raw){
  const total=searchHits.length,shown=searchHits.slice(0,searchLimit);
  const ab=$('searchApply');ab.disabled=!raw&&!searchFilter;$('searchApplyLbl').textContent=!raw&&searchFilter?'Bỏ lọc':raw?`Lọc danh sách (${total})`:'Lọc danh sách';
  searchCount.textContent=raw?`${total} bài phù hợp${total>shown.length?` · đang hiện ${shown.length}`:''}`:`${POSTS.length} bài · nhập số thứ tự, tên file hoặc từ khóa`;
  searchResults.replaceChildren();searchSel=Math.min(searchSel,Math.max(0,shown.length-1));
  if(!shown.length){const d=document.createElement('div');d.className='s-empty';d.textContent='Không tìm thấy bài phù hợp.';searchResults.append(d);return}
  const frag=document.createDocumentFragment();
  shown.forEach((idx,n)=>{
    const p=POSTS[idx],b=document.createElement('button');b.type='button';b.className='s-item'+(n===searchSel?' sel':'');b.dataset.idx=idx;
    const vi=p.k.findIndex(k=>k!==2);
    if(vi>=0&&p.m[vi][5]){const t=document.createElement('span');t.className='s-thumb';t.innerHTML=ic('package');b.append(t)}
    else if(vi>=0){const t=document.createElement('img');t.className='s-thumb';t.loading='lazy';t.decoding='async';t.alt='';t.src=urlOf(p.m[vi][0]);t.addEventListener('error',()=>{const f=document.createElement('span');f.className='s-thumb';f.innerHTML=ic('image');t.replaceWith(f)},{once:true});b.append(t)}
    else{const t=document.createElement('span');t.className='s-thumb';t.innerHTML=ic('video');b.append(t)}
    const tx=document.createElement('span');tx.className='s-text';
    const ti=document.createElement('span');ti.className='s-title';ti.textContent=`Bài ${idx+1} · ${p.m.length} media${liked.has(p.id)?' · ♥':''}`;
    const de=document.createElement('span');de.className='s-detail';
    const noteTxt=p.n?Object.values(p.n)[0].replace(/<[^>]+>/g,' ').replace(/\s+/g,' ').trim():'';
    de.textContent=p.m.slice(0,2).map(m=>baseName(m[0])).join(' · ')||noteTxt||p.id;
    tx.append(ti,de);b.append(tx);frag.append(b);
  });
  if(total>shown.length){const m=document.createElement('button');m.type='button';m.className='btn s-more';m.textContent=`Hiện thêm (${total-shown.length})`;m.onclick=()=>{searchLimit+=60;renderSearch(raw)};frag.append(m)}
  searchResults.append(frag);
}
function applySearchFilter(){
  const raw=searchQuery.value.trim();
  if(!raw){if(searchFilter){closeSearch(true);clearSearchFilter()}return}
  buildIndex();const q=parseQuery(raw);let any=false;
  for(let i=0;i<POSTS.length;i++)if(matchPost(i,q)){any=true;break}
  if(!any){toast('Không có bài nào khớp để lọc');return}
  searchFilter={raw,q};closeSearch(true);computeView();
  if(view.length)focusIdx=view[0];
  rebuild();window.scrollTo(0,0);
  toast(`Đang lọc "${raw}" · ${view.length} bài`);
}
function clearSearchFilter(){
  if(!searchFilter)return;const keep=focusIdx;searchFilter=null;computeView();rebuild();
  if(viewPos[keep]>=0)gotoPost(keep,{block:isGrid()?'center':'start'});else window.scrollTo(0,0);
  toast('Đã bỏ lọc tìm kiếm');
}
function updateSearchChip(){
  const bar=$('chipBar');bar.hidden=!searchFilter;
  if(searchFilter){$('chipText').textContent=searchFilter.raw;$('chipCount').textContent=view.length+' bài'}
}
$('searchApply').onclick=applySearchFilter;$('chipClear').onclick=clearSearchFilter;$('chipMain').onclick=()=>openSearch();
function pickSearch(idx){closeSearch(true);gotoPost(idx);toast(`Đã mở bài ${idx+1}`)}
searchResults.addEventListener('click',e=>{const b=e.target.closest('.s-item');if(b)pickSearch(+b.dataset.idx)});
function moveSel(d){const items=searchResults.querySelectorAll('.s-item');if(!items.length)return;items[searchSel]?.classList.remove('sel');searchSel=clamp(searchSel+d,0,items.length-1);items[searchSel].classList.add('sel');items[searchSel].scrollIntoView({block:'nearest'})}
let searchTimer;searchQuery.addEventListener('input',()=>{clearTimeout(searchTimer);searchLimit=60;searchSel=0;searchTimer=setTimeout(runSearch,90)});
searchQuery.addEventListener('keydown',e=>{if(e.key==='Enter'&&e.shiftKey){e.preventDefault();clearTimeout(searchTimer);applySearchFilter()}else if(e.key==='Enter'){e.preventDefault();clearTimeout(searchTimer);runSearch();const idx=searchHits[searchSel];if(idx!=null)pickSearch(idx)}else if(e.key==='ArrowDown'){e.preventDefault();moveSel(1)}else if(e.key==='ArrowUp'){e.preventDefault();moveSel(-1)}});
function openSearch(v){closeSettings();closeFilter();searchDlg.classList.add('active');searchQuery.value=v!=null?v:(searchFilter?searchFilter.raw:'');searchLimit=60;searchSel=0;runSearch();requestAnimationFrame(()=>{syncVV();searchQuery.focus();searchQuery.select()})}
function closeSearch(noFocus){searchDlg.classList.remove('active');if(!noFocus)$('jumpBtn').focus()}
$('searchClose').onclick=()=>closeSearch();searchDlg.addEventListener('click',e=>{if(e.target===searchDlg)closeSearch()});

/* ---------- File nén (.zip / .cbz) đọc bằng unzipit ----------
   Mỗi file nén là một "thư mục ảo". Trình duyệt chỉ giải nén ĐÚNG entry đang cần thành Blob (URL.createObjectURL).
   - Cache file nén đã mở (zipCache): mở một lần, dùng lại cho mọi ảnh trong đó (tối đa ZIP_MAX_OPEN file, LRU).
   - Cache Blob URL có đếm tham chiếu (zblobs): cùng một ảnh dùng chung một Blob; hết người dùng thì revoke.
   - Ảnh trong feed/lưới chỉ được giải nén khi cuộn tới gần, và nhả lại (revoke) khi cuộn đi xa.
   - Lightbox nhả Blob ngay khi đổi ảnh/đóng (chỉ giữ tối đa 2 ảnh kế bên để chuyển ảnh mượt). */
const ARCH_ON=ARCHIVES.length>0;
const ZIP_MAX_OPEN=6;
let ZIP_IDLE_CAP=((FLAGS.zip&&FLAGS.zip.cacheMB!=null)?FLAGS.zip.cacheMB:48)*1048576;   // zip_cache_mb: ngưỡng Blob "rảnh" được giữ lại để cuộn lại không phải giải nén lần nữa
const MIME={jpg:'image/jpeg',jpeg:'image/jpeg',png:'image/png',apng:'image/apng',gif:'image/gif',webp:'image/webp',avif:'image/avif',bmp:'image/bmp',svg:'image/svg+xml',jxl:'image/jxl',heic:'image/heic',heif:'image/heif',mp4:'video/mp4',m4v:'video/x-m4v',mov:'video/quicktime',webm:'video/webm',ogv:'video/ogg'};
const mimeOf=n=>MIME[n.slice(n.lastIndexOf('.')+1).toLowerCase()]||'application/octet-stream';
const zipErr=(code,msg,ai)=>Object.assign(new Error(msg),{code,archive:ai});
const zipFiles=new Map(),zipHttp=new Map(),zipCache=new Map(),zblobs=new Map(),zpend=new Map(),zipEls=new Set(),zipNeedToast=new Set();
let zidleBytes=0,unzipitP=null,lastZipToast='',lastZipToastT=0;
function zipToast(e){const msg='Không mở được file nén: '+((e&&e.message)||e),now=Date.now();if(msg===lastZipToast&&now-lastZipToastT<4000)return;lastZipToast=msg;lastZipToastT=now;toast(msg)}

/* Nạp thư viện: ưu tiên bản nhúng sẵn trong HTML (build đã nhúng unzipit local → chạy cả khi offline / file://),
   không có thì import() động từ CDN. Chỉ tải khi thật sự cần xem ảnh trong file nén. */
function loadUnzipit(){
  if(window.unzipit)return Promise.resolve(window.unzipit);
  if(!unzipitP){
    const url=FLAGS.zip&&FLAGS.zip.url;
    unzipitP=import(url).then(mod=>{window.unzipit=mod;return mod}).catch(()=>{unzipitP=null;throw zipErr('NO_LIB','không tải được thư viện unzipit từ '+url+' (hãy kiểm tra mạng, hoặc đặt unzipit.module.js cạnh config.toml rồi build lại để nhúng sẵn)')});
  }
  return unzipitP;
}
/* Nguồn dữ liệu của một file nén: File người dùng đã chọn → HTTP (Range) → tải cả file → yêu cầu chọn file. */
async function zipSource(ai,u){
  const f=zipFiles.get(ai);if(f)return f;
  if(location.protocol==='file:')throw zipErr('NEED_FILE','cần chọn file',ai);   // trình duyệt cấm fetch() tới file://
  const [path,size]=ARCHIVES[ai],url=urlOf(path);let r;
  try{r=await fetch(url,{headers:{Range:'bytes=0-0'}})}catch(e){throw zipErr('NEED_FILE','không đọc được qua mạng',ai)}
  if(r.status===206){if(r.body)r.body.cancel().catch(()=>{});zipHttp.set(ai,true);return u.HTTPRangeReader?new u.HTTPRangeReader(url):url}
  if(r.ok){
    if(r.body)r.body.cancel().catch(()=>{});
    toast(`Máy chủ không hỗ trợ Range — đang tải cả file ${fmtSize(size)}…`);
    const full=await fetch(url);if(!full.ok)throw zipErr('HTTP','HTTP '+full.status+' khi tải '+url,ai);
    const blob=await full.blob();zipHttp.set(ai,true);return blob;
  }
  throw zipErr('HTTP','HTTP '+r.status+' khi mở '+url,ai);
}
function getZip(ai){
  let p=zipCache.get(ai);
  if(p){zipCache.delete(ai);zipCache.set(ai,p);return p}
  p=(async()=>{
    const u=await loadUnzipit(),src=await zipSource(ai,u);let info;
    try{info=await (u.unzipRaw?u.unzipRaw(src):u.unzip(src))}catch(e){throw zipErr('BAD_ZIP','file nén hỏng hoặc không đọc được ('+((e&&e.message)||e)+')',ai)}
    return {entries:Array.isArray(info.entries)?info.entries:Object.values(info.entries)};
  })();
  zipCache.set(ai,p);p.catch(()=>{if(zipCache.get(ai)===p)zipCache.delete(ai)});
  while(zipCache.size>ZIP_MAX_OPEN)zipCache.delete(zipCache.keys().next().value);   // LRU: bỏ file nén lâu không dùng nhất
  return p;
}
async function extractZip(m){
  const [ai,internal,zi]=m[5],z=await getZip(ai);
  let ent=z.entries[zi];   // tra theo chỉ số (không phụ thuộc cách giải mã tên); lệch thì tra theo tên
  if(!ent||(ent.name!==internal&&ent.size!==m[3]))ent=z.entries.find(e=>e.name===internal)||null;
  if(!ent)throw zipErr('NOT_FOUND','không thấy “'+internal+'” trong '+baseName(ARCHIVES[ai][0]),ai);
  try{return ent.blob?await ent.blob(mimeOf(internal)):new Blob([await ent.arrayBuffer()],{type:mimeOf(internal)})}
  catch(e){throw zipErr('EXTRACT','không giải nén được “'+baseName(internal)+'” ('+((e&&e.message)||e)+')',ai)}
}
/* Lấy Blob URL cho một media trong file nén. Trả về tay cầm: {url, release({retain}), hold(ms)}. */
async function acquireZip(m){
  const key=m[5][0]+':'+m[5][2];let e=zblobs.get(key);
  if(!e){
    let pr=zpend.get(key);
    if(!pr){
      pr=extractZip(m).then(blob=>{const ent={key,url:URL.createObjectURL(blob),size:blob.size,refs:0,idle:false,idleAt:0,holdUntil:0};zblobs.set(key,ent);zpend.delete(key);return ent},err=>{zpend.delete(key);throw err});
      zpend.set(key,pr);
    }
    e=await pr;
  }
  if(e.idle){e.idle=false;zidleBytes-=e.size}
  e.refs++;let done=false;
  return {url:e.url,size:e.size,key,
    release(opt){if(done)return;done=true;zRelease(e,opt)},
    hold(ms){e.holdUntil=Math.max(e.holdUntil,Date.now()+ms)}};
}
function zRelease(e,opt){
  if(--e.refs>0)return;
  if(opt&&opt.retain){e.idle=true;e.idleAt=Date.now();zidleBytes+=e.size;zTrim()}   // feed: giữ tạm để cuộn lại không phải giải nén lần nữa
  else zDestroy(e);                                                                  // lightbox: thu hồi ngay
}
function zDestroy(e){
  const wait=e.holdUntil-Date.now();
  if(wait>0){setTimeout(()=>{if(e.refs===0&&zblobs.get(e.key)===e)zDestroy(e)},wait+50);return}
  zRevoke(e);
}
function zRevoke(e){URL.revokeObjectURL(e.url);zblobs.delete(e.key);if(e.idle){zidleBytes-=e.size;e.idle=false}}
function zTrim(){
  if(zidleBytes<=ZIP_IDLE_CAP)return;
  const idle=[...zblobs.values()].filter(x=>x.idle).sort((a,b)=>a.idleAt-b.idleAt);
  for(const e of idle){if(zidleBytes<=ZIP_IDLE_CAP)break;if(e.holdUntil>Date.now())continue;zRevoke(e)}
}

/* Ảnh/video trong feed & lưới: chỉ giải nén khi nằm gần khung nhìn, nhả khi cuộn đi xa. */
const zipIO='IntersectionObserver'in window?new IntersectionObserver(es=>{
  for(const en of es){const el=en.target;
    if(en.isIntersecting){el._want=true;if(!el._hold&&el.dataset.zauto!=='0')loadZipEl(el)}
    else{el._want=false;unloadZipEl(el)}}
},{rootMargin:'1400px 0px'}):null;
function zipWatch(el){zipEls.add(el);if(zipIO)zipIO.observe(el);else{el._want=true;if(el.dataset.zauto!=='0')loadZipEl(el)}}
async function loadZipEl(el){
  if(el._hold||el._loading)return false;
  const m=POSTS[+el.dataset.zp].m[+el.dataset.zj];el._loading=true;
  try{
    const h=await acquireZip(m);el._loading=false;
    if(!el.isConnected||!el._want){h.release({retain:true});return false}
    el._hold=h;el._need=false;const nb=el.closest('.media-item');if(nb){const b=nb.querySelector('.zip-need-btn');if(b)b.remove()}
    if(el.tagName==='VIDEO'){el.src=h.url;el.load()}else{el.alt=el.dataset.alt||'';el.src=h.url}
    return true;
  }catch(e){
    el._loading=false;
    if(e.code==='NEED_FILE')zipNeedFile(el,e.archive);else{el.classList.add('broken','loaded');zipToast(e)}
    return false;
  }
}
function unloadZipEl(el){
  const h=el._hold;if(!h)return;el._hold=null;
  if(el.tagName==='VIDEO'){el.pause();el.removeAttribute('src');el.load()}else el.removeAttribute('src');
  el.classList.remove('loaded');h.release({retain:true});
}
function releaseAllZipEls(){
  if(zipIO)zipIO.disconnect();
  for(const el of zipEls){el._want=false;const h=el._hold;if(h){el._hold=null;h.release({retain:true})}}
  zipEls.clear();
}
async function zipPlay(v){v._want=true;if(await loadZipEl(v)){try{await v.play()}catch(e){}}}
function zipNeedFile(el,ai){
  el._need=true;const item=el.closest('.media-item');
  if(item&&!item.querySelector('.zip-need-btn')){
    const b=document.createElement('button');b.type='button';b.className='zip-need-btn';b.dataset.act='zipneed';b.dataset.ai=ai;
    b.innerHTML=ic('package');const t=document.createElement('span');t.textContent=`Chọn file “${baseName(ARCHIVES[ai][0])}” để xem`;b.append(t);item.append(b);
  }
  if(!zipNeedToast.has(ai)){zipNeedToast.add(ai);toast(`Cần chọn file “${baseName(ARCHIVES[ai][0])}” (bấm vào ô xám để chọn)`)}
}

/* Hộp thoại chọn file nén: bắt buộc khi mở bằng file://, dùng được cả khi kéo-thả. */
const zipDlg=$('zipDlg');
function zipStatus(ai){return zipFiles.has(ai)?'Đã chọn file':zipHttp.get(ai)?'Đọc qua máy chủ (HTTP)':'Chưa có file'}
function renderZipDlg(){
  $('zipMode').textContent=location.protocol==='file:'
    ?'Bạn đang mở trang bằng file:// — trình duyệt không cho trang tự đọc file trên máy, nên hãy chọn (hoặc kéo-thả) các file nén bên dưới. Lựa chọn chỉ có hiệu lực trong phiên này. Mẹo: mở trang qua máy chủ web (ví dụ python -m http.server) để tự đọc, không cần chọn.'
    :'Đang mở qua HTTP: trang tự đọc các file nén từ máy chủ (nếu máy chủ hỗ trợ Range thì chỉ tải phần cần thiết). Chỉ cần chọn file thủ công khi đọc tự động không được.';
  const list=$('zipList');list.replaceChildren();
  ARCHIVES.forEach(([path,size,count],ai)=>{
    const ok=zipFiles.has(ai)||zipHttp.get(ai),row=document.createElement('div');row.className='saved-item'+(ok?' on':'');
    const box=document.createElement('div');box.className='saved-apply';const b=document.createElement('b');b.textContent=baseName(path);
    const sm=document.createElement('small');const d=document.createElement('span');d.className='desc';d.textContent=path;const c=document.createElement('span');c.className='cnt';c.textContent=` · ${fmtSize(size)} · ${count} media · ${zipStatus(ai)}`;sm.append(d,c);
    box.append(b,sm);row.append(box);list.append(row);
  });
}
function openZipDlg(){closeSettings();closeFilter();renderZipDlg();zipDlg.classList.add('active')}
function closeZipDlg(){zipDlg.classList.remove('active')}
function registerZipFiles(files){
  const list=[...files].filter(f=>/\.(zip|cbz)$/i.test(f.name));let n=0;
  ARCHIVES.forEach(([path,size],ai)=>{
    const bn=baseName(path).toLowerCase(),named=list.filter(f=>f.name.toLowerCase()===bn);if(!named.length)return;
    let pick=named.filter(f=>f.size===size);
    if(pick.length>1)pick=pick.filter(f=>(f.webkitRelativePath||'').toLowerCase().endsWith(path.toLowerCase().split('/').slice(-2).join('/'))).concat(pick);
    const file=(pick.length?pick:named)[0];
    if(file.size!==size)toast(`“${file.name}” có dung lượng khác lúc build — vẫn thử đọc`);
    zipFiles.set(ai,file);zipCache.delete(ai);zipNeedToast.delete(ai);n++;
  });
  return n;
}
function zipRetry(){
  zipEls.forEach(el=>{if(el._need){el._need=false;const nb=el.closest('.media-item'),b=nb&&nb.querySelector('.zip-need-btn');if(b)b.remove();if(el._want)loadZipEl(el)}});
  if(lb.open&&lb.needAi!=null)updateLightbox();
}
function onZipFiles(files){
  const n=registerZipFiles(files);
  if(zipDlg.classList.contains('active'))renderZipDlg();
  if(n){toast(`Đã nhận ${n} file nén`);zipRetry()}else toast('Không có file nào khớp với các file nén của archive này');
}
if(ARCH_ON){
  $('zipBtn').hidden=false;$('zipBtn').onclick=openZipDlg;$('zipClose').onclick=closeZipDlg;
  zipDlg.addEventListener('click',e=>{if(e.target===zipDlg)closeZipDlg()});
  $('zipPickFilesBtn').onclick=()=>$('zipPickFiles').click();
  if(!('webkitdirectory'in $('zipPickDir')))$('zipPickDirBtn').hidden=true;else $('zipPickDirBtn').onclick=()=>$('zipPickDir').click();
  $('zipPickFiles').addEventListener('change',e=>{const f=[...e.target.files];e.target.value='';if(f.length)onZipFiles(f)});
  $('zipPickDir').addEventListener('change',e=>{const f=[...e.target.files];e.target.value='';if(f.length)onZipFiles(f)});
  addEventListener('dragover',e=>{if(e.dataTransfer&&[...e.dataTransfer.types].includes('Files'))e.preventDefault()});
  addEventListener('drop',e=>{if(e.dataTransfer&&e.dataTransfer.files.length){e.preventDefault();onZipFiles(e.dataTransfer.files)}});
}else{$('zipBtn').remove()}

/* ---------- Xem ảnh phóng to ---------- */
const lightbox=$('lightbox'),lbStage=$('lbStage'),lbImg=$('lbImg'),lbVideo=$('lbVideo'),lbInfo=$('lbInfo');
const lb={open:false,list:[],i:0,scale:1,tx:0,ty:0,slide:false,slideT:0,idleT:0,pushed:false,skipPop:false,token:0,info:false,hold:null,holdKind:-1,needAi:null,pre:new Map()},lbNeed=$('lbNeed');
const code2=c=>[Math.floor(c/4096),c%4096];
function openLightbox(idx,j){
  const list=[];for(const pi of view){const p=POSTS[pi];for(let m=0;m<p.m.length;m++)if(typeFilter.has(p.k[m]))list.push(pi*4096+m)}
  const i=list.indexOf(idx*4096+j);if(i<0)return;
  document.querySelectorAll('video').forEach(v=>{if(v!==lbVideo)v.pause()});
  lb.list=list;lb.i=i;lb.open=true;closeSettings();closeFilter();
  lightbox.classList.add('active');document.documentElement.classList.add('lb-open');
  if(!lb.pushed){try{history.pushState({tumblrLb:1},'');lb.pushed=true}catch(e){}}
  updateLightbox();lightbox.focus({preventScroll:true});wake();
}
function closeLightbox(fromPop){
  if(!lb.open)return;lb.open=false;lbVideo.pause();lightbox.classList.remove('active','idle','loading');
  lb.token++;lbNeed.hidden=true;lb.needAi=null;   // huỷ mọi tác vụ giải nén đang chờ và nhả toàn bộ Blob của lightbox
  if(lb.hold){lb.hold.release();lb.hold=null;lb.holdKind=-1}
  lbVideo.removeAttribute('src');lbVideo.load();delete lbVideo.dataset.src;lbImg.removeAttribute('src');
  for(const slot of lb.pre.values())if(slot.h)slot.h.release();lb.pre.clear();document.documentElement.classList.remove('lb-open');
  lb.slide=false;syncSlideBtn();clearTimeout(lb.slideT);clearTimeout(lb.idleT);lbInfo.hidden=true;lb.info=false;$('lbInfoBtn').classList.remove('on');
  if(document.fullscreenElement||document.webkitFullscreenElement)(document.exitFullscreen||document.webkitExitFullscreen).call(document);
  if(lb.pushed&&!fromPop){lb.pushed=false;lb.skipPop=true;history.back()}else lb.pushed=false;
  const [idx]=code2(lb.list[lb.i]||0);const el=cards.get(idx);
  if(el){el.scrollIntoView({block:'center',behavior:'instant'});focusIdx=idx;updatePos()}
}
addEventListener('popstate',()=>{if(lb.skipPop){lb.skipPop=false;return}if(lb.open)closeLightbox(true)});
function resetZoom(){lb.scale=1;lb.tx=0;lb.ty=0;applyT()}
function applyT(){lbImg.style.setProperty('--sc',lb.scale);lbImg.style.setProperty('--tx',lb.tx+'px');lbImg.style.setProperty('--ty',lb.ty+'px');lbStage.classList.toggle('zoomed',lb.scale>1)}
function clampPan(){const mx=Math.max(0,(lbImg.offsetWidth*lb.scale-lbStage.clientWidth)/2),my=Math.max(0,(lbImg.offsetHeight*lb.scale-lbStage.clientHeight)/2);lb.tx=clamp(lb.tx,-mx,mx);lb.ty=clamp(lb.ty,-my,my)}
function zoomAt(s,cx,cy){
  if(lbImg.hidden)return;s=clamp(s,1,8);const px=cx-lbStage.clientWidth/2,py=cy-lbStage.clientHeight/2,r=s/lb.scale;
  lb.tx=px-(px-lb.tx)*r;lb.ty=py-(py-lb.ty)*r;lb.scale=s;if(s===1){lb.tx=0;lb.ty=0}clampPan();applyT();
}
const zoomCenter=f=>zoomAt(lb.scale*f,lbStage.clientWidth/2,lbStage.clientHeight/2);
const toggleZoom=(x,y)=>zoomAt(lb.scale>1.05?1:2.5,x,y);
function updateLightbox(){
  const [idx,j]=code2(lb.list[lb.i]),p=POSTS[idx],m=p.m[j],[rel,w,h,size,ct]=m,kind=p.k[j],name=baseName(rel),zipped=!!m[5];
  resetZoom();lbVideo.pause();clearTimeout(lb.slideT);
  const tok=++lb.token,prev=lb.hold,prevKind=lb.holdKind;lb.hold=null;lb.holdKind=-1;lb.needAi=null;lbNeed.hidden=true;
  const freePrev=()=>{if(prev)prev.release()};   // release() chỉ có tác dụng một lần
  if(prev&&prevKind===2){lbVideo.removeAttribute('src');lbVideo.load();delete lbVideo.dataset.src;freePrev()}   // video: nhả Blob ngay
  const dl=$('lbDl'),op=$('lbOpen');
  if(zipped){
    lightbox.classList.add('loading');dl.removeAttribute('href');op.removeAttribute('href');dl.setAttribute('download',name);
    if(kind===2){lbImg.hidden=true;lbVideo.hidden=false}else{lbVideo.hidden=true;lbImg.hidden=false;lbImg.classList.add('loading')}
    openZipInLightbox(m,kind,tok,name,freePrev);
  }else{
    const url=urlOf(rel);
    if(kind===2){
      lbImg.hidden=true;lbVideo.hidden=false;lightbox.classList.remove('loading');
      if(lbVideo.dataset.src!==url){lbVideo.dataset.src=url;lbVideo.src=url;lbVideo.load()}
    }else{
      lbVideo.hidden=true;lbImg.hidden=false;lbImg.classList.add('loading');lightbox.classList.add('loading');
      lbImg.onload=()=>{if(tok===lb.token){lbImg.classList.remove('loading');lightbox.classList.remove('loading')}};
      lbImg.onerror=()=>{if(tok===lb.token){lbImg.classList.remove('loading');lightbox.classList.remove('loading');toast('Không tải được ảnh')}};
      lbImg.alt=name;lbImg.src=url;
    }
    freePrev();dl.href=url;dl.setAttribute('download',name);op.href=url;
  }
  $('lbCount').textContent=`Bài ${idx+1}/${POSTS.length} · ${lb.i+1}/${lb.list.length}`;
  $('lbName').textContent=name;
  $('lbZoomIn').hidden=$('lbZoomOut').hidden=kind===2;
  syncLbLike();if(lb.info)renderInfo();
  for(const d of [1,-1]){const n=lb.list[(lb.i+d+lb.list.length)%lb.list.length],[ni,nj]=code2(n);if(!POSTS[ni].m[nj][5]&&POSTS[ni].k[nj]!==2){const im=new Image();im.decoding='async';im.src=urlOf(POSTS[ni].m[nj][0])}}
  syncLbPreload();
  slideTick();
}
async function openZipInLightbox(m,kind,tok,name,freePrev){
  let hold;
  try{hold=await acquireZip(m)}
  catch(e){
    freePrev();if(tok!==lb.token||!lb.open)return;
    lightbox.classList.remove('loading');lbImg.classList.remove('loading');lbImg.hidden=lbVideo.hidden=true;
    if(e.code==='NEED_FILE'){lb.needAi=e.archive;$('lbNeedMsg').textContent=`Cần chọn file “${baseName(ARCHIVES[e.archive][0])}” để xem ảnh/video bên trong (trình duyệt không tự đọc được file trên máy khi mở bằng file://).`;lbNeed.hidden=false}
    else zipToast(e);
    return;
  }
  if(tok!==lb.token||!lb.open){hold.release();freePrev();return}
  lb.hold=hold;lb.holdKind=kind;
  $('lbDl').href=hold.url;$('lbOpen').href=hold.url;
  if(kind===2){lbVideo.dataset.src=hold.url;lbVideo.src=hold.url;lbVideo.load();lightbox.classList.remove('loading')}
  else{
    lbImg.onload=()=>{if(tok===lb.token){lbImg.classList.remove('loading');lightbox.classList.remove('loading')}};
    lbImg.onerror=()=>{if(tok===lb.token){lbImg.classList.remove('loading');lightbox.classList.remove('loading');toast('Không hiển thị được ảnh trong file nén')}};
    lbImg.alt=name;lbImg.src=hold.url;
  }
  freePrev();   // Blob của ảnh trước chỉ được thu hồi SAU khi ảnh mới đã gán
}
/* Tải trước ảnh kế bên (chỉ ảnh nhỏ hơn 40 MB trong file nén); tối đa 2 Blob phụ, tự nhả khi không còn kế bên. */
function syncLbPreload(){
  const cur=lb.list[lb.i],[ci,cj]=code2(cur),cm=POSTS[ci].m[cj],curKey=cm[5]?cm[5][0]+':'+cm[5][2]:'',want=new Map();
  for(const d of [1,-1]){const n=lb.list[(lb.i+d+lb.list.length)%lb.list.length],[ni,nj]=code2(n),nm=POSTS[ni].m[nj];
    if(nm[5]&&POSTS[ni].k[nj]!==2&&nm[3]<=40*1048576){const k=nm[5][0]+':'+nm[5][2];if(k!==curKey)want.set(k,nm)}}
  for(const [k,slot] of [...lb.pre]){if(!want.has(k)){if(slot.h)slot.h.release();lb.pre.delete(k)}}
  for(const [k,nm] of want){
    if(lb.pre.has(k))continue;const slot={h:null};lb.pre.set(k,slot);
    acquireZip(nm).then(h=>{if(!lb.open||lb.pre.get(k)!==slot){h.release();return}slot.h=h}).catch(()=>{if(lb.pre.get(k)===slot)lb.pre.delete(k)});
  }
}
$('lbDl').addEventListener('click',()=>{if(lb.hold)lb.hold.hold(120000)});   // giữ Blob thêm 2 phút để tải xuống/mở tab kịp hoàn tất
$('lbOpen').addEventListener('click',()=>{if(lb.hold)lb.hold.hold(120000)});
$('lbNeedBtn').onclick=()=>openZipDlg(lb.needAi);
function syncLbLike(){const [idx]=code2(lb.list[lb.i]),on=liked.has(POSTS[idx].id),b=$('lbLike');b.classList.toggle('on',on);b.setAttribute('aria-pressed',String(on))}
function moveLb(d){if(!lb.list.length)return;lb.i=(lb.i+d+lb.list.length)%lb.list.length;updateLightbox()}
function renderInfo(){
  const [idx,j]=code2(lb.list[lb.i]),p=POSTS[idx],[rel,w,h,size,ct]=p.m[j];
  const rows=[['Tên file',baseName(rel)],['Đường dẫn',rel],['Bài',`#${idx+1} · media ${j+1}/${p.m.length}`]];
  const zm=p.m[j][5];if(zm)rows.splice(2,0,['File nén gốc',ARCHIVES[zm[0]][0]],['Đường dẫn trong file nén',zm[1]],['Dung lượng file nén',fmtSize(ARCHIVES[zm[0]][1])]);
  if(w&&h)rows.push(['Kích thước ảnh',`${w} × ${h} px`]);rows.push(['Dung lượng',fmtSize(size)],['Ngày tạo',fmtDate(ct)]);if(p.f)rows.push(['Thư mục',p.f]);
  lbInfo.replaceChildren(...rows.map(([k,v])=>{const r=document.createElement('div');r.className='lb-row';const a=document.createElement('span');a.textContent=k;const b=document.createElement('b');b.textContent=v;r.append(a,b);return r}));
  const note=p.n&&p.n[j];if(note){const n=document.createElement('div');n.className='media-note';n.style.marginTop='10px';n.innerHTML=note;lbInfo.append(n)}
}
function toggleInfo(){lb.info=!lb.info;lbInfo.hidden=!lb.info;$('lbInfoBtn').classList.toggle('on',lb.info);$('lbInfoBtn').setAttribute('aria-pressed',String(lb.info));if(lb.info)renderInfo()}
function syncSlideBtn(){const b=$('lbSlide');b.classList.toggle('on',lb.slide);b.setAttribute('aria-pressed',String(lb.slide));b.innerHTML=ic(lb.slide?'pause':'play')}
function toggleSlide(){lb.slide=!lb.slide;syncSlideBtn();slideTick();toast(lb.slide?`Trình chiếu · ${prefs.slide} giây/ảnh`:'Đã dừng trình chiếu')}
function slideTick(){clearTimeout(lb.slideT);if(!lb.open||!lb.slide||!lb.list.length)return;const [idx,j]=code2(lb.list[lb.i]);if(POSTS[idx].k[j]===2){lbVideo.play().catch(()=>{});return}lb.slideT=setTimeout(()=>moveLb(1),prefs.slide*1000)}
lbVideo.addEventListener('ended',()=>{if(lb.slide)moveLb(1)});
function toggleFull(){const d=document;if(d.fullscreenElement||d.webkitFullscreenElement)(d.exitFullscreen||d.webkitExitFullscreen).call(d);else{const f=lightbox.requestFullscreen||lightbox.webkitRequestFullscreen;if(f)f.call(lightbox)}}
if(!document.fullscreenEnabled&&!document.webkitFullscreenEnabled)$('lbFull').hidden=true;
function wake(){lightbox.classList.remove('idle');clearTimeout(lb.idleT);lb.idleT=setTimeout(()=>{if(lb.open&&!lb.info)lightbox.classList.add('idle')},2800)}
lightbox.addEventListener('pointermove',wake);lightbox.addEventListener('pointerdown',()=>{if(lightbox.classList.contains('idle'))wake()});
$('lbNext').onclick=()=>moveLb(1);$('lbPrev').onclick=()=>moveLb(-1);$('lbClose').onclick=()=>closeLightbox();
$('lbLike').onclick=()=>{const [idx]=code2(lb.list[lb.i]);toggleLike(POSTS[idx].id)};
$('lbSlide').onclick=toggleSlide;$('lbZoomIn').onclick=()=>zoomCenter(1.5);$('lbZoomOut').onclick=()=>zoomCenter(1/1.5);$('lbInfoBtn').onclick=toggleInfo;$('lbFull').onclick=toggleFull;
lbStage.addEventListener('wheel',e=>{if(lbImg.hidden)return;e.preventDefault();zoomAt(lb.scale*Math.exp(-e.deltaY*(e.ctrlKey?.01:.0018)),e.clientX,e.clientY)},{passive:false});
const pts=new Map();let drag=null,pinch=null,lastTap=0,lastX=0,lastY=0,tapTimer=0;
lbStage.addEventListener('pointerdown',e=>{
  if(e.target.closest('video'))return;lbStage.setPointerCapture(e.pointerId);pts.set(e.pointerId,{x:e.clientX,y:e.clientY});
  if(pts.size===1)drag={x:e.clientX,y:e.clientY,tx:lb.tx,ty:lb.ty,moved:false,type:e.pointerType,target:e.target};
  else if(pts.size===2){const [a,b]=[...pts.values()];pinch={d:Math.hypot(a.x-b.x,a.y-b.y)||1,s:lb.scale};if(drag)drag.moved=true}
});
lbStage.addEventListener('pointermove',e=>{
  const pt=pts.get(e.pointerId);if(!pt)return;pt.x=e.clientX;pt.y=e.clientY;
  if(pts.size===2&&pinch){const [a,b]=[...pts.values()];zoomAt(pinch.s*Math.hypot(a.x-b.x,a.y-b.y)/pinch.d,(a.x+b.x)/2,(a.y+b.y)/2);return}
  if(drag&&pts.size===1){const dx=e.clientX-drag.x,dy=e.clientY-drag.y;if(!drag.moved&&Math.hypot(dx,dy)>6){drag.moved=true;lbStage.classList.add('panning')}if(drag.moved&&lb.scale>1){lb.tx=drag.tx+dx;lb.ty=drag.ty+dy;clampPan();applyT()}}
});
function endPointer(e,cancel){
  if(!pts.has(e.pointerId))return;pts.delete(e.pointerId);lbStage.classList.remove('panning');
  if(pinch){if(pts.size<2)pinch=null;if(!pts.size)drag=null;return}
  if(!drag||pts.size)return;const d=drag;drag=null;if(cancel)return;
  const dx=e.clientX-d.x,dy=e.clientY-d.y;
  if(d.moved){if(lb.scale===1&&d.type!=='mouse'){if(Math.abs(dx)>55&&Math.abs(dx)>Math.abs(dy)*1.25)moveLb(dx<0?1:-1);else if(dy>110&&dy>Math.abs(dx)*1.25)closeLightbox()}return}
  if(d.target===lbStage){closeLightbox();return}
  if(d.type==='mouse'){toggleZoom(e.clientX,e.clientY);return}
  const now=Date.now();
  if(now-lastTap<300&&Math.hypot(e.clientX-lastX,e.clientY-lastY)<32){lastTap=0;clearTimeout(tapTimer);toggleZoom(e.clientX,e.clientY)}
  else{lastTap=now;lastX=e.clientX;lastY=e.clientY;clearTimeout(tapTimer);tapTimer=setTimeout(()=>lightbox.classList.toggle('idle'),300)}
}
lbStage.addEventListener('pointerup',e=>endPointer(e,false));lbStage.addEventListener('pointercancel',e=>endPointer(e,true));

/* ---------- Sao lưu & khôi phục ---------- */
const backupDlg=$('backupDlg');
const enc64=t=>{const b=new TextEncoder().encode(t);let s='';for(let i=0;i<b.length;i+=0x8000)s+=String.fromCharCode(...b.subarray(i,i+0x8000));return btoa(s)};
const dec64=v=>new TextDecoder().decode(Uint8Array.from(atob(v.replace(/\s+/g,'')),c=>c.charCodeAt(0)));
function backupData(){return {format:'tumblr-archive-backup',version:3,archiveFingerprint:FINGERPRINT,likedPosts:[...liked],savedFilters:savedFilters.map(({id,...rest})=>rest),position:readJSON(STORE.position,null),exportedAt:new Date().toISOString()}}
function openBackup(focusImport){closeSettings();$('backupStat').textContent=`Hiện có ${liked.size} bài đã thích, ${savedFilters.length} bộ lọc đã lưu${readJSON(STORE.position,null)?' và một vị trí đọc đã lưu':''}.`;backupDlg.classList.add('active');if(focusImport)requestAnimationFrame(()=>$('impText').focus())}
function closeBackup(){backupDlg.classList.remove('active')}
$('expFile').onclick=()=>{const blob=new Blob([JSON.stringify(backupData(),null,1)],{type:'application/json'}),a=document.createElement('a'),d=new Date(),p=n=>String(n).padStart(2,'0');a.href=URL.createObjectURL(blob);a.download=`archive-backup-${d.getFullYear()}${p(d.getMonth()+1)}${p(d.getDate())}.json`;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(a.href),4000);toast('Đã tạo file backup')};
$('expCopy').onclick=async()=>{const ok=await copyText(enc64(JSON.stringify(backupData())));toast(ok?'Đã sao chép chuỗi backup':'Không sao chép được — hãy dùng nút Tải file')};
function importBackup(text){
  try{
    text=text.trim();if(!text)throw Error('empty');if(text.length>16e6)throw Error('big');
    const data=JSON.parse(text[0]==='{'?text:dec64(text));
    if(!data||data.format!=='tumblr-archive-backup'||!Array.isArray(data.likedPosts)||data.likedPosts.some(x=>typeof x!=='string'))throw Error('bad');
    let added=0;for(const id of data.likedPosts)if(ID_INDEX.has(id)&&!liked.has(id)){liked.add(id);added++}
    save(STORE.likes,[...liked]);
    let addedF=0;
    if(Array.isArray(data.savedFilters)){
      for(const f of cleanSaved(data.savedFilters)){
        if(savedFilters.length>=MAX_SAVED)break;
        if(savedFilters.some(x=>sameName(x.name,f.name)))continue;
        f.id=newFilterId();savedFilters.push(f);addedF++;
      }
      if(addedF)persistSaved();
    }
    let pos=data.position;if(!pos&&data.lastPostId)pos={id:data.lastPostId,index:Number(data.lastPostIdx)-1};
    const idx=pos?(ID_INDEX.has(pos.id)?ID_INDEX.get(pos.id):Number(pos.index)):-1;
    computeView();rebuild();closeBackup();
    if(Number.isInteger(idx)&&idx>=0&&idx<POSTS.length&&viewPos[idx]>=0)gotoPost(idx,{block:'center'});
    toast(`Đã khôi phục: thêm ${added} bài đã thích (tổng ${liked.size})${addedF?`, ${addedF} bộ lọc`:''}`);
  }catch(err){toast(err.message==='big'?'Dữ liệu backup quá lớn':'Backup không hợp lệ')}
}
$('impGo').onclick=()=>importBackup($('impText').value);
$('impFileBtn').onclick=()=>$('impFile').click();
$('impFile').addEventListener('change',async e=>{const f=e.target.files[0];e.target.value='';if(!f)return;if(f.size>16e6){toast('File quá lớn');return}importBackup(await f.text())});
$('backupBtn').onclick=()=>openBackup();$('backupClose').onclick=closeBackup;backupDlg.addEventListener('click',e=>{if(e.target===backupDlg)closeBackup()});

/* ---------- Trợ giúp ---------- */
const help=$('help');function toggleHelp(){closeSettings();help.classList.toggle('active')}
$('helpBtn').onclick=toggleHelp;$('helpClose').onclick=toggleHelp;help.addEventListener('click',e=>{if(e.target===help)toggleHelp()});

/* ---------- Bàn phím ---------- */
document.addEventListener('keydown',e=>{
  if(e.ctrlKey||e.metaKey||e.altKey)return;const k=e.key;
  if(searchDlg.classList.contains('active')){if(k==='Escape'){closeSearch();e.preventDefault()}return}
  if(backupDlg.classList.contains('active')){if(k==='Escape'){closeBackup();e.preventDefault()}return}
  if(savedDlg.classList.contains('active')){if(k==='Escape'){closeSaved();e.preventDefault()}return}
  if(zipDlg.classList.contains('active')){if(k==='Escape'){closeZipDlg();e.preventDefault()}return}
  const tag=document.activeElement&&document.activeElement.tagName;
  if(['INPUT','TEXTAREA','SELECT'].includes(tag)||document.activeElement.isContentEditable){if(k==='Escape'){document.activeElement.blur();closeFilter();closeSettings()}return}
  if(lb.open){
    const onVideo=tag==='VIDEO';
    if(k==='Escape'){if(lb.info){toggleInfo()}else closeLightbox();e.preventDefault()}
    else if(k==='ArrowRight'&&!onVideo||k==='j'||k==='J'){e.preventDefault();moveLb(1)}
    else if(k==='ArrowLeft'&&!onVideo||k==='k'||k==='K'){e.preventDefault();moveLb(-1)}
    else if(e.code==='Space'&&!onVideo){e.preventDefault();moveLb(e.shiftKey?-1:1)}
    else if(k==='+'||k==='='){e.preventDefault();zoomCenter(1.5)}
    else if(k==='-'||k==='_'){e.preventDefault();zoomCenter(1/1.5)}
    else if(k==='0'){e.preventDefault();resetZoom()}
    else if(k==='l'||k==='L')$('lbLike').click();
    else if(k==='s'||k==='S')toggleSlide();
    else if(k==='i'||k==='I')toggleInfo();
    else if(k==='f'||k==='F')toggleFull();
    else if(k==='d'||k==='D')$('lbDl').click();
    else if(k==='o'||k==='O')$('lbOpen').click();
    wake();return;
  }
  if(help.classList.contains('active')){if(k==='Escape'||k==='?'||k==='h'||k==='H')toggleHelp();return}
  if(k==='Escape'){if(filterPop.classList.contains('open')){closeFilter();return}if(settingsMenu.classList.contains('open')){closeSettings();return}if(searchFilter){clearSearchFilter();return}}
  if(e.code==='Space'){e.preventDefault();navigatePost(e.shiftKey?-1:1)}
  else if(k==='j'||k==='J'||k==='ArrowDown'){e.preventDefault();navigatePost(1)}
  else if(k==='k'||k==='K'||k==='ArrowUp'){e.preventDefault();navigatePost(-1)}
  else if(k==='l'||k==='L'){if(view.length)toggleLike(POSTS[focusIdx].id)}
  else if(k==='f'||k==='F')toggleLiked();
  else if(k==='g'||k==='G'){e.preventDefault();openSearch()}
  else if(k==='r'||k==='R')randomPost();
  else if(k==='v'||k==='V')setView(isGrid()?'feed':'grid');
  else if(k==='m'||k==='M'){e.preventDefault();openThemeSettings()}
  else if(k==='b'||k==='B'){e.preventDefault();openSaved()}
  else if(k==='e'||k==='E'){e.preventDefault();openBackup()}
  else if(k==='i'||k==='I'){e.preventDefault();openBackup(true)}
  else if(k==='t'||k==='T')scrollTo({top:0,behavior:'smooth'});
  else if(k==='?'||k==='h'||k==='H')toggleHelp();
});

/* ---------- Bộ lọc đã lưu ---------- */
const savedDlg=$('savedDlg'),MAX_SAVED=40;
const newFilterId=()=>'f'+Date.now().toString(36)+Math.random().toString(36).slice(2,6);
function cleanSaved(arr){
  if(!Array.isArray(arr))return [];const out=[],seen=new Set();
  for(const x of arr){
    if(!x||typeof x.name!=='string')continue;const name=x.name.trim().slice(0,60),key=name.toLocaleLowerCase();
    if(!name||seen.has(key))continue;seen.add(key);
    out.push({id:typeof x.id==='string'&&x.id?x.id:newFilterId(),name,q:typeof x.q==='string'?x.q.slice(0,180):'',
      types:Array.isArray(x.types)?x.types.filter(k=>k===0||k===1||k===2):null,
      folders:Array.isArray(x.folders)?x.folders.filter(f=>typeof f==='string'):null,liked:!!x.liked,at:Number(x.at)||0});
    if(out.length>=MAX_SAVED)break;
  }
  return out;
}
let savedFilters=cleanSaved(readJSON(STORE.saved,[])),renamingId=null;
const persistSaved=()=>save(STORE.saved,savedFilters);
const sameName=(a,b)=>a.trim().toLocaleLowerCase()===b.trim().toLocaleLowerCase();
function currentSpec(){
  const active=!!searchFilter||onlyLiked||typeFilter.size<3||folderFilter.size<FOLDER_PATHS.length;
  if(!active)return null;
  return {q:searchFilter?searchFilter.raw:'',types:typeFilter.size<3?[...typeFilter].sort():null,folders:folderFilter.size<FOLDER_PATHS.length?[...folderFilter].sort():null,liked:onlyLiked};
}
const specKey=f=>JSON.stringify([f.q||'',f.types?[...f.types].sort():null,f.folders?[...f.folders].sort():null,!!f.liked]);
function describeSpec(f){
  const parts=[];
  if(f.q)parts.push('“'+f.q+'”');
  if(f.types)parts.push(f.types.length?f.types.map(k=>['Ảnh','GIF','Video'][k]).join(' + '):'Không loại nào');
  if(f.folders)parts.push(f.folders.length&&f.folders.length<=2?f.folders.join(', '):f.folders.length+'/'+FOLDER_PATHS.length+' thư mục');
  if(f.liked)parts.push('Đã thích');
  return parts.join(' · ')||'Không có điều kiện';
}
function specPosts(f){
  return filterPosts({q:f.q?parseQuery(f.q):null,types:new Set(f.types||[0,1,2]),
    folders:f.folders?new Set(f.folders.filter(x=>FOLDER_COUNT.has(x))):new Set(FOLDER_PATHS),liked:!!f.liked});
}
function applySpec(f){
  const wasLiked=onlyLiked;
  searchFilter=f.q?{raw:f.q,q:parseQuery(f.q)}:null;
  typeFilter=new Set(f.types||[0,1,2]);
  const known=f.folders?f.folders.filter(x=>FOLDER_COUNT.has(x)):null;
  folderFilter=known&&known.length?new Set(known):new Set(FOLDER_PATHS);
  onlyLiked=!!f.liked;if(onlyLiked&&!wasLiked)likedReturn=focusIdx;if(!onlyLiked)likedReturn=null;
  syncFilterUI();computeView();if(view.length)focusIdx=view[0];rebuild();window.scrollTo(0,0);
  return !!(f.folders&&f.folders.length&&known.length<f.folders.length);
}
function applySaved(s){
  const missing=applySpec(s);closeSaved();closeFilter();
  toast(`Đã áp dụng “${s.name}” · ${view.length} bài${missing?' (một số thư mục đã không còn)':''}`);
}
function suggestName(f){const d=describeSpec(f);return d.length>48?d.slice(0,47)+'…':d}
function renderSavedQuick(){
  const box=$('savedQuick');if(!box)return;box.replaceChildren();
  const cur=currentSpec(),curKey=cur?specKey(cur):null;
  for(const s of savedFilters.slice(0,8)){
    const b=document.createElement('button');b.type='button';b.className='item'+(specKey(s)===curKey?' on':'');b.dataset.id=s.id;b.title=describeSpec(s);
    b.innerHTML=ic('bookmark');const t=document.createElement('span');t.className='item-text';t.textContent=s.name;b.append(t);box.append(b);
  }
}
$('savedQuick').addEventListener('click',e=>{const b=e.target.closest('.item');const s=b&&savedFilters.find(x=>x.id===b.dataset.id);if(s)applySaved(s)});
function renderSaved(){
  const cur=currentSpec(),curKey=cur?specKey(cur):null,name=$('savedName');
  $('savedCurrent').textContent=cur?'Bộ lọc hiện tại: '+describeSpec(cur):'Chưa bật bộ lọc nào. Hãy dùng Lọc, Đã thích hoặc “Lọc danh sách” trong hộp tìm kiếm, rồi quay lại đây để lưu.';
  name.disabled=!cur;$('savedSave').disabled=!cur;name.placeholder=cur?suggestName(cur):'Tên bộ lọc';
  const list=$('savedList');list.replaceChildren();
  if(!savedFilters.length){const d=document.createElement('div');d.className='saved-empty';d.textContent='Chưa có bộ lọc nào được lưu.';list.append(d);return}
  let focusInput=null;
  for(const s of savedFilters){
    const row=document.createElement('div');row.className='saved-item'+(specKey(s)===curKey?' on':'');row.dataset.id=s.id;
    if(renamingId===s.id){
      const inp=document.createElement('input');inp.type='text';inp.maxLength=60;inp.value=s.name;inp.className='rename-input';inp.setAttribute('aria-label','Tên mới của bộ lọc');
      inp.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();commitRename(s,inp.value)}else if(e.key==='Escape'){e.preventDefault();e.stopPropagation();renamingId=null;renderSaved()}});
      row.append(inp,iconBtn('check','rename-ok','Lưu tên'),iconBtn('x','rename-cancel','Hủy'));focusInput=inp;
    }else{
      const a=document.createElement('button');a.type='button';a.className='saved-apply';a.dataset.act='apply';
      const b=document.createElement('b');b.textContent=s.name;const sm=document.createElement('small');
      const dd=document.createElement('span');dd.className='desc';dd.textContent=describeSpec(s);const cc=document.createElement('span');cc.className='cnt';cc.textContent=` · ${specPosts(s).length} bài`;
      sm.append(dd,cc);a.append(b,sm);
      row.append(a,iconBtn('pencil','rename','Đổi tên'),iconBtn('trash','del','Xóa','danger'));
    }
    list.append(row);
  }
  if(focusInput)requestAnimationFrame(()=>{focusInput.focus();focusInput.select()});
}
function iconBtn(icon,act,label,extra){const b=document.createElement('button');b.type='button';b.className='icon-btn'+(extra?' '+extra:'');b.dataset.act=act;b.title=label;b.setAttribute('aria-label',label);b.innerHTML=ic(icon);return b}
function commitRename(s,val){
  const name=val.trim().slice(0,60);
  if(!name){toast('Tên bộ lọc không được để trống');return}
  if(savedFilters.some(x=>x!==s&&sameName(x.name,name))){toast('Đã có bộ lọc trùng tên');return}
  s.name=name;persistSaved();renamingId=null;renderSaved();renderSavedQuick();toast(`Đã đổi tên thành “${name}”`);
}
function saveCurrent(){
  const cur=currentSpec();if(!cur){toast('Chưa có bộ lọc nào đang bật để lưu');return}
  const name=($('savedName').value.trim()||suggestName(cur)).slice(0,60),existing=savedFilters.find(x=>sameName(x.name,name));
  if(existing){Object.assign(existing,cur,{at:Date.now()});toast(`Đã cập nhật bộ lọc “${existing.name}”`)}
  else{if(savedFilters.length>=MAX_SAVED){toast(`Tối đa ${MAX_SAVED} bộ lọc — hãy xóa bớt trước khi lưu thêm`);return}savedFilters.push({id:newFilterId(),name,...cur,at:Date.now()});toast(`Đã lưu bộ lọc “${name}”`)}
  persistSaved();$('savedName').value='';renderSaved();renderSavedQuick();
}
$('savedList').addEventListener('click',e=>{
  const btn=e.target.closest('[data-act]'),row=e.target.closest('.saved-item');if(!btn||!row)return;
  const s=savedFilters.find(x=>x.id===row.dataset.id);if(!s)return;const act=btn.dataset.act;
  if(act==='apply')applySaved(s);
  else if(act==='rename'){renamingId=s.id;renderSaved()}
  else if(act==='rename-ok')commitRename(s,row.querySelector('input').value);
  else if(act==='rename-cancel'){renamingId=null;renderSaved()}
  else if(act==='del'&&confirm(`Xóa bộ lọc “${s.name}”?`)){savedFilters=savedFilters.filter(x=>x!==s);persistSaved();renderSaved();renderSavedQuick();toast(`Đã xóa bộ lọc “${s.name}”`)}
});
function openSaved(){closeSettings();closeFilter();renamingId=null;renderSaved();savedDlg.classList.add('active');requestAnimationFrame(()=>{const n=$('savedName');if(!n.disabled)n.focus()})}
function closeSaved(){savedDlg.classList.remove('active');renamingId=null}
$('savedName').addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();saveCurrent()}});
$('savedSave').onclick=saveCurrent;$('savedClose').onclick=closeSaved;$('savedManage').onclick=openSaved;$('chipSave').onclick=openSaved;
savedDlg.addEventListener('click',e=>{if(e.target===savedDlg)closeSaved()});

/* Dán liên kết #p123 vào tab đang mở (chỉ đổi hash, không tải lại trang) */
addEventListener('hashchange',()=>{
  const m=/^#p(\d+)$/.exec(location.hash);if(!m||location.hash===savedHash)return;
  const n=Number(m[1])-1;if(n>=0&&n<POSTS.length){if(lb.open)closeLightbox();gotoPost(n);savedHash=location.hash}
});

/* ---------- Khởi động ---------- */
try{history.scrollRestoration='manual'}catch(e){}
applyStyle(prefs.style,false);syncViewUI();syncFilterUI();
computeView();rebuild();
(function restore(){
  let idx=-1;const m=/^#p(\d+)$/.exec(location.hash);
  if(m){const n=Number(m[1])-1;if(n>=0&&n<POSTS.length)idx=n}
  if(idx<0){const pos=readJSON(STORE.position,null);if(pos){idx=ID_INDEX.has(pos.id)?ID_INDEX.get(pos.id):(Number.isInteger(Number(pos.index))?clamp(Number(pos.index),0,POSTS.length-1):-1)}}
  if(idx>0&&viewPos[idx]>=0){gotoPost(idx);toast(`Đã khôi phục vị trí bài ${idx+1}`)}
  else if(view.length)focusIdx=view[0];
  updatePos();
  setTimeout(()=>{restoreLock=false},600);
})();
</script>
</body>
</html>
'''


# --------------------------------------------------------------------------- #
# Sinh HTML
# --------------------------------------------------------------------------- #
class Options(NamedTuple):
    title: str
    theme: str
    theme_light: str
    theme_dark: str
    sort_by: str
    sticky_header: bool
    show_filename: bool
    show_created_time: bool
    show_file_size: bool
    show_video_thumbnails: bool
    show_dimensions: bool
    folder_filter_depth: int
    default_view: str
    columns: int
    feed_width: int
    probe_dimensions: bool
    video_autoplay: bool
    ignored_folders: tuple
    app_icon: str
    app_name: str
    app_status_bar: str
    zip_support: bool
    zip_post_mode: str
    unzipit_path: str
    unzipit_url: str
    zip_cache_mb: int


def render_sprite() -> str:
    symbols = "".join(f'<symbol id="i-{name}" viewBox="{box}">{body}</symbol>' for name, (box, body) in ICONS.items())
    return f'<svg class="sprite" aria-hidden="true" focusable="false">{symbols}</svg>'


def relative_media_root(folder: Path, output_dir: Path) -> str:
    return Path(os.path.relpath(folder.resolve(), output_dir)).as_posix()


def collect_entries(images_dirs: list[Path], output: Path, opts: Options, cache: SizeCache, log) -> tuple[list[dict], dict]:
    output_dir = output.parent.resolve()
    t0 = time.perf_counter()
    ignore = IgnoreRules(opts.ignored_folders)
    raw_scans = [(folder, *scan_folder(folder, ignore, opts.zip_support)) for folder in images_dirs]
    warn = lambda msg: print("Cảnh báo: " + msg, file=sys.stderr)
    scans = []
    archive_table: list[list] = []          # [đường dẫn file nén (tương đối với HTML), dung lượng, số media bên trong]
    archive_index: dict[tuple[Path, str], int] = {}
    zip_problems = 0
    for folder, media, notes_by_stem, archives in raw_scans:
        combined = list(media)
        root_rel_for_zip = relative_media_root(folder, output_dir)
        for archive in archives:
            items, zstats = list_archive_media(archive, ignore, warn)
            zip_problems += zstats["bad"] + zstats["encrypted"] + zstats["unsupported"]
            if items:
                archive_index[(folder, archive.rel)] = len(archive_table)
                archive_table.append([posixpath.normpath(posixpath.join(root_rel_for_zip, archive.rel)), archive.size, len(items)])
                combined.extend(items)
        if archives:
            combined.sort(key=lambda m: natural_key(m.rel))
        scans.append((folder, combined, notes_by_stem))
    t_scan = time.perf_counter() - t0

    sizes: dict[str, tuple[int, int]] = {}
    t0 = time.perf_counter()
    if opts.probe_dimensions:
        all_media = [m for _folder, media, _notes in scans for m in media]
        workers = min(16, (os.cpu_count() or 4) * 2)
        sizes = probe_media_sizes(all_media, cache, workers)
        cache.save([str(folder) for folder in images_dirs])
    t_probe = time.perf_counter() - t0

    name_counts: dict[str, int] = {}
    for folder in images_dirs:
        name_counts[folder.name.casefold()] = name_counts.get(folder.name.casefold(), 0) + 1
    labels: dict[Path, str] = {}
    for index, folder in enumerate(images_dirs):
        label = folder.name
        if name_counts[label.casefold()] > 1:
            parent_name = folder.parent.name
            label = f"{parent_name}/{label}" if parent_name else f"{label} ({index + 1})"
        labels[folder] = label

    multi_root = len(images_dirs) > 1
    entries: list[dict] = []
    for folder, media, notes_by_stem in scans:
        root_rel = relative_media_root(folder, output_dir)
        folder_key = natural_key(root_rel)
        used_notes: set[Path] = set()
        for group_key, files in group_media(media, opts.zip_post_mode):
            post_id = f"{root_rel}::{group_key}" if multi_root else group_key
            items, notes = [], {}
            for position, mf in enumerate(files):
                out_rel = posixpath.normpath(posixpath.join(root_rel, mf.rel))
                width, height = sizes.get(media_key(mf), (0, 0))
                item = [out_rel, width, height, mf.size, int(mf.created)]
                if mf.zip is not None:
                    # Metadata file nén: [chỉ số trong ARCHIVES (đường dẫn file nén gốc), đường dẫn bên trong, chỉ số entry]
                    item.append([archive_index[(folder, mf.zip[0])], mf.zip[1], mf.zip[2]])
                items.append(item)
                note_path = markdown_sidecar(mf.rel, used_notes, notes_by_stem, mf.zip[0] if mf.zip else None)
                if note_path is not None:
                    try:
                        text = note_path.read_text(encoding="utf-8", errors="replace")[:2_000_000]
                    except OSError:
                        text = ""
                    if text.strip():
                        notes[str(position)] = markdown_to_html(text)
            parent_parts = posixpath.dirname(files[0].rel)
            bucket = labels[folder]
            if opts.folder_filter_depth > 0 and parent_parts:
                bucket += "/" + "/".join(parent_parts.split("/")[:opts.folder_filter_depth])
            post = {"id": post_id, "m": items, "f": bucket}
            if files[0].zip is not None:
                post["z"] = archive_index[(folder, files[0].zip[0])]
            if notes:
                post["n"] = notes
            if multi_root:
                post["s"] = labels[folder]
            entries.append({
                "post": post,
                "names": [posixpath.normpath(posixpath.join(root_rel, mf.rel)) for mf in files],
                "nk_name": min(natural_key(mf.rel) for mf in files),
                "nk_folder": folder_key,
                "created": min(mf.created for mf in files),
            })

    if opts.sort_by == "name":
        entries.sort(key=lambda e: (e["nk_name"], e["nk_folder"], e["post"]["id"].casefold()))
    elif opts.sort_by == "created":
        entries.sort(key=lambda e: (e["created"], e["nk_name"], e["nk_folder"]))
    else:
        entries.sort(key=lambda e: (e["created"], e["nk_name"], e["nk_folder"]), reverse=True)
    stats = {"scan": t_scan, "probe": t_probe, "skipped_dirs": ignore.skipped, "media": sum(len(e["names"]) for e in entries),
             "unknown_dims": sum(1 for e in entries for m in e["post"]["m"] if not m[1] and media_kind(m[0]) != KIND_VIDEO),
             "archives": archive_table, "zip_entries": sum(row[2] for row in archive_table), "zip_problems": zip_problems}
    return entries, stats


HTML_HEAD = """<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="color-scheme" content="__COLOR_SCHEME__"><meta name="theme-color" content="__THEME_COLOR__"><meta name="generator" content="build_archive.py v__VERSION__">
__APP_META__
<title>__ARCHIVE_TITLE__</title>__FAVICON_LINK__
<style>
"""


def find_local_unzipit(opts: Options, dirs: list[Path], warn) -> str | None:
    """Tìm unzipit cục bộ để nhúng inline (chạy được cả khi mở bằng file:// và khi offline)."""
    if opts.unzipit_path:
        given = Path(opts.unzipit_path).expanduser()
        candidates = [given] if given.is_absolute() else [d / given for d in dirs]
        if not any(c.is_file() for c in candidates):
            warn(f"Không tìm thấy unzipit_path: {opts.unzipit_path} — sẽ tải unzipit từ CDN khi cần.")
            return None
    else:
        candidates = [d / name for d in dirs for name in UNZIPIT_LOCAL_CANDIDATES]
    for candidate in candidates:
        if not candidate.is_file():
            continue
        try:
            source = candidate.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            warn(f"Không đọc được {candidate.name}: {exc}")
            continue
        script = prepare_unzipit_script(source)
        if script is None:
            warn(f"Không nhúng được {candidate.name} (cú pháp không chuyển được sang script thường) — sẽ tải unzipit từ CDN khi cần.")
            return None
        return script
    return None


def generate_html(images_dirs: list[Path], output: Path, opts: Options, script_dir: Path, log=print, icon_base: Path | None = None) -> tuple[int, dict]:
    if not images_dirs:
        raise FileNotFoundError("Chưa cấu hình thư mục media nào.")
    for folder in images_dirs:
        if not folder.is_dir():
            raise FileNotFoundError(f"Không tìm thấy thư mục media: {folder}")
    output.parent.mkdir(parents=True, exist_ok=True)
    cache = SizeCache(script_dir / CACHE_FILENAME if opts.probe_dimensions else None)
    entries, stats = collect_entries(images_dirs, output, opts, cache, log)
    posts = [entry["post"] for entry in entries]

    # Vân tay archive: GIỮ NGUYÊN công thức của v2 để bài đã thích / vị trí đọc cũ vẫn khớp.
    identity = "\0".join(str(folder.resolve()) for folder in images_dirs) + "\0" + "\0".join(name for entry in entries for name in entry["names"])
    fingerprint = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20]

    theme = THEMES[opts.theme_dark if opts.theme == "auto" else opts.theme]
    theme_vars = ";".join(f"--{key}:{value}" for key, value in theme.items() if key != "scheme")
    auto_themes = {"light": opts.theme_light, "dark": opts.theme_dark}
    # --- Icon ứng dụng cho "Thêm vào Màn hình chính" (iOS) ---
    icon_dir = icon_base or script_dir
    if opts.app_icon:
        icon_path = Path(opts.app_icon).expanduser()
        icon_path = icon_path if icon_path.is_absolute() else icon_dir / icon_path
    else:
        icon_path = next((c for d in dict.fromkeys([icon_dir, script_dir]) for name in APP_ICON_CANDIDATES
                          if (c := d / name).is_file()), None)
    icon_png, icon_kind = prepare_app_icon(icon_path, theme, cache, lambda msg: print("Cảnh báo: " + msg, file=sys.stderr))
    cache.save([str(folder) for folder in images_dirs])
    icon_uri = "data:image/png;base64," + base64.b64encode(icon_png).decode("ascii")
    icon_w, icon_h = struct.unpack(">II", icon_png[16:24])
    app_name = html_escape((opts.app_name or opts.title).strip()[:40], quote=True)
    app_meta = (f'<meta name="apple-mobile-web-app-capable" content="yes"><meta name="mobile-web-app-capable" content="yes">'
                f'<meta name="apple-mobile-web-app-title" content="{app_name}">'
                f'<meta name="apple-mobile-web-app-status-bar-style" content="{opts.app_status_bar}">'
                f'<meta name="format-detection" content="telephone=no">'
                f'<link rel="apple-touch-icon" sizes="{icon_w}x{icon_h}" href="{icon_uri}">')
    stats["icon"] = icon_kind
    # --- Thư viện unzipit cho file .zip/.cbz (chỉ nhúng khi archive thật sự có file nén) ---
    zip_flags = None
    unzipit_inline = ""
    if stats["archives"]:
        local = find_local_unzipit(opts, list(dict.fromkeys([icon_dir, script_dir])), lambda msg: print("Cảnh báo: " + msg, file=sys.stderr))
        zip_flags = {"url": opts.unzipit_url or UNZIPIT_CDN_URL, "local": local is not None, "cacheMB": opts.zip_cache_mb}
        stats["unzipit_local"] = local is not None
        if local is not None:
            unzipit_inline = "<script>" + local + "</script>"
    favicon_link = ""
    favicon = next((c for folder in [script_dir, *images_dirs]
                    for c in (folder / "fav.icon", folder / "favicon.ico", folder / "favicon.png", folder / "favicon.svg")
                    if c.is_file()), None)
    if favicon:
        mime = {".ico": "image/x-icon", ".icon": "image/x-icon", ".png": "image/png", ".svg": "image/svg+xml"}.get(favicon.suffix.casefold(), "application/octet-stream")
        favicon_link = f'<link rel="icon" href="data:{mime};base64,{base64.b64encode(favicon.read_bytes()).decode("ascii")}">'
    else:
        favicon_link = f'<link rel="icon" type="image/png" href="{icon_uri}">'
    theme_options = "".join(f'<option value="{key}">{html_escape(THEME_LABELS.get(key, key))}</option>' for key in THEMES)
    flags = {"filename": opts.show_filename, "created": opts.show_created_time, "size": opts.show_file_size,
             "thumbs": opts.show_video_thumbnails, "dims": opts.show_dimensions, "zip": zip_flags}
    defaults = {"view": opts.default_view, "cols": opts.columns, "width": opts.feed_width, "autoplay": opts.video_autoplay}

    values = {
        "POSTS": js_json(posts), "BASE": '""', "FINGERPRINT": json.dumps(fingerprint),
        "ARCHIVE_TITLE": html_escape(opts.title), "ARCHIVE_TITLE_JSON": js_json(opts.title),
        "THEME_VARS": theme_vars, "THEMES": js_json(THEMES), "DEFAULT_THEME": json.dumps(opts.theme),
        "AUTO_THEMES": js_json(auto_themes), "FLAGS": js_json(flags), "DEFAULTS": js_json(defaults),
        "COLOR_SCHEME": theme["scheme"], "THEME_COLOR": theme["mantle"], "FAVICON_LINK": favicon_link,
        "HEADER_STICKY_CLASS": "" if opts.sticky_header else "header-not-sticky", "TOTAL_POSTS": str(len(posts)),
        "VERSION": VERSION, "APP_META": app_meta, "ARCHIVES": js_json(stats["archives"]), "UNZIPIT_INLINE": unzipit_inline, "FEED_WIDTH": str(opts.feed_width), "SPRITE": render_sprite(), "THEME_OPTIONS": theme_options,
    }
    # Thay một lượt: dữ liệu người dùng (tên file, ghi chú) không bao giờ bị quét lại tìm placeholder.
    html = re.sub(r"__([A-Z_]+)__", lambda m: values.get(m.group(1), m.group(0)), HTML_HEAD + CSS + BODY)
    tmp = output.with_name(output.name + ".tmp")
    tmp.write_text(html, encoding="utf-8")
    os.replace(tmp, output)
    stats["bytes"] = len(html.encode("utf-8"))
    return len(posts), stats


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def zip_enabled(args, config: dict) -> bool:
    value = config.get("zip_support", True)
    enabled = value if isinstance(value, bool) else str(value).strip().casefold() in ("true", "yes", "1", "on", "enabled")
    return enabled and not getattr(args, "no_zip", False)


def ignore_patterns(args, config: dict) -> tuple:
    """Gộp ignored_folders trong config.toml với --ignore trên dòng lệnh."""
    configured = config.get("ignored_folders") or []
    if isinstance(configured, str):
        configured = [configured]
    if not isinstance(configured, list) or not all(isinstance(v, str) for v in configured):
        raise ValueError('ignored_folders phải là danh sách chuỗi, ví dụ ["Thumbs", "_old*", "Anime/2023"]')
    extra = list(getattr(args, "ignore", None) or [])
    return tuple(dict.fromkeys(v.strip() for v in [*configured, *extra] if v.strip()))


def resolve_folders(args, config: dict, config_path: Path | None, script_dir: Path) -> list[Path]:
    if args.images is not None:
        return [args.images if args.images.is_absolute() else Path.cwd() / args.images]
    dirs = config.get("images_dirs") or []
    if isinstance(dirs, str):
        dirs = [dirs]
    single = config.get("images_dir") or ""
    if not isinstance(dirs, list) or not all(isinstance(v, str) for v in dirs) or not isinstance(single, str):
        raise ValueError('images_dir phải là chuỗi và images_dirs phải là danh sách chuỗi, ví dụ ["Images", "Videos"]')
    configured = dirs or ([single] if single else [])
    if configured:
        base_dir = config_path.parent if config_path else script_dir
        if len(configured) == 1 and str(configured[0]).strip().casefold() == "all":
            rules = IgnoreRules(ignore_patterns(args, config))
            candidates = sorted((item for item in base_dir.iterdir()
                                 if item.is_dir() and not item.name.startswith(".") and item.name not in IGNORED_MEDIA_DIRS
                                 and not rules.matches(item.name, item.name, str(item))),
                                key=lambda item: natural_key(item.name))
            return [c for c in candidates if folder_has_media(c, IgnoreRules(ignore_patterns(args, config)), zip_enabled(args, config))]
        return [Path(str(v)) if Path(str(v)).is_absolute() else base_dir / str(v) for v in configured]
    candidates = [script_dir / "Images", script_dir / "images", Path.cwd() / "Images", Path.cwd() / "images"]
    return [next((c for c in candidates if c.is_dir()), candidates[0])]


def build_options(args, config: dict) -> Options:
    def normalize_theme(value: object) -> str:
        name = str(value).strip().casefold().replace("catppuccin-", "").replace("_", "-")
        return {"tokyonight": "tokyo-night", "rosepine": "rose-pine", "solarized": "solarized-dark",
                "amoled": "midnight", "black": "midnight"}.get(name, name)

    def truthy(key: str, default: bool = False) -> bool:
        value = config.get(key, default)
        if isinstance(value, bool):
            return value
        return str(value).strip().casefold() in ("true", "yes", "1", "on", "enabled")

    def integer(key: str, low: int, high: int) -> int:
        value = config.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
            raise ValueError(f"{key} phải là số nguyên từ {low} đến {high} (viết số trần, không đặt trong dấu ngoặc kép)")
        return value

    theme = normalize_theme(args.theme or config.get("theme") or "mocha")
    theme_light = normalize_theme(config.get("theme_light") or "latte")
    theme_dark = normalize_theme(config.get("theme_dark") or "mocha")
    if theme not in set(THEMES) | {"auto"}:
        raise ValueError(f"Theme không hợp lệ: {theme}. Chọn một trong: auto, {', '.join(THEMES)}")
    if theme_light not in THEMES or theme_dark not in THEMES:
        raise ValueError("theme_light và theme_dark phải là theme có sẵn, không dùng auto")
    sort_by = str(args.sort_by or config.get("sort_by") or "name").strip().casefold()
    sort_by = {"date": "created", "created_at": "created", "newest": "created_desc", "latest": "created_desc"}.get(sort_by, sort_by)
    if sort_by not in ("name", "created", "created_desc"):
        raise ValueError("sort_by phải là name, created hoặc created_desc")
    zip_mode = str(config.get("zip_post_mode") or "folder").strip().casefold()
    zip_mode = {"file": "folder", "directory": "folder", "zip": "archive", "album": "archive"}.get(zip_mode, zip_mode)
    if zip_mode not in ("folder", "archive"):
        raise ValueError('zip_post_mode phải là "folder" (coi file nén như thư mục ảo) hoặc "archive" (mỗi file nén là một bài)')
    unzipit_url = str(config.get("unzipit_url") or "").strip()
    if unzipit_url and not re.match(r"^(https?://|/|\./)", unzipit_url):
        raise ValueError("unzipit_url phải là địa chỉ http(s):// hoặc đường dẫn bắt đầu bằng / hay ./")
    status_bar = str(config.get("app_status_bar") or "black-translucent").strip().casefold()
    if status_bar not in STATUS_BAR_STYLES:
        raise ValueError(f"app_status_bar phải là một trong: {', '.join(STATUS_BAR_STYLES)}")
    view = str(config.get("default_view", "feed")).strip().casefold()
    view = {"list": "feed", "timeline": "feed", "masonry": "grid", "gallery": "grid"}.get(view, view)
    if view not in ("feed", "grid"):
        raise ValueError("default_view phải là feed hoặc grid")
    return Options(
        title=str(args.title or config.get("title") or ""), theme=theme, theme_light=theme_light, theme_dark=theme_dark,
        sort_by=sort_by, sticky_header=truthy("sticky_header", True),
        show_filename=truthy("show_filename"), show_created_time=truthy("show_created_time"), show_file_size=truthy("show_file_size"),
        show_video_thumbnails=truthy("show_video_thumbnails"), show_dimensions=truthy("show_dimensions"),
        folder_filter_depth=integer("folder_filter_depth", 0, 10), default_view=view, columns=integer("columns", 0, 10),
        feed_width=integer("feed_width", 480, 1100), probe_dimensions=truthy("probe_dimensions", True) and not args.no_probe,
        video_autoplay=truthy("video_autoplay"),
        ignored_folders=ignore_patterns(args, config),
        app_icon=str(args.icon.resolve()) if getattr(args, "icon", None) else str(config.get("app_icon") or ""),
        app_name=str(config.get("app_name") or ""), app_status_bar=status_bar,
        zip_support=zip_enabled(args, config), zip_post_mode=zip_mode,
        unzipit_path=str(args.unzipit) if getattr(args, "unzipit", None) else str(config.get("unzipit_path") or ""),
        unzipit_url=unzipit_url, zip_cache_mb=integer("zip_cache_mb", 0, 4096),
    )


def folder_signature(folders: list[Path], patterns: tuple = (), zip_support: bool = False) -> tuple:
    parts = []
    for folder in folders:
        media, notes, archives = scan_folder(folder, IgnoreRules(patterns), zip_support)
        parts.append((str(folder), tuple((m.rel, m.size, m.mtime_ns) for m in media), tuple(sorted((k, v.stat().st_mtime_ns) for k, v in notes.items() if v.exists())),
                      tuple((a.rel, a.size, a.mtime_ns) for a in archives)))
    return tuple(parts)


def run_build(args, script_dir: Path) -> tuple[int, Path, Options, list[Path]]:
    config, config_path = load_config(script_dir)
    opts = build_options(args, config)
    if not opts.title:
        opts = opts._replace(title=f"{script_dir.name} Archive")
    folders = resolve_folders(args, config, config_path, script_dir)
    output = args.output if args.output is not None else script_dir / "index.html"
    started = time.perf_counter()
    count, stats = generate_html(folders, output, opts, script_dir, icon_base=config_path.parent if config_path else None)
    elapsed = time.perf_counter() - started
    if not args.quiet:
        print(f"Đã tạo {output} · {count} bài · {stats['media']} media · {stats['bytes'] / 1024:.0f} KB · "
              f"theme {opts.theme} · sort {opts.sort_by} · {elapsed:.2f}s (quét {stats['scan']:.2f}s, đọc kích thước {stats['probe']:.2f}s)")
        if stats["archives"]:
            print(f"Đã lập chỉ mục {len(stats['archives'])} file nén (.zip/.cbz) với {stats['zip_entries']} media bên trong, "
                  f"đọc bằng unzipit ({'nhúng local' if stats.get('unzipit_local') else 'tải từ CDN khi cần'}).")
        if stats["skipped_dirs"]:
            print(f"Đã bỏ qua {stats['skipped_dirs']} thư mục theo ignored_folders / --ignore.")
        if stats["unknown_dims"]:
            print(f"Lưu ý: {stats['unknown_dims']} ảnh không đọc được kích thước (định dạng lạ hoặc file hỏng); trang vẫn hoạt động nhưng các ảnh này có thể làm nhảy layout nhẹ.")
    return count, output, opts, folders


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Tạo archive HTML offline (kiểu Tumblr) từ config.toml và thư mục media.")
    parser.add_argument("--images", type=Path, default=None, help="Ghi đè danh sách thư mục trong config.toml bằng một thư mục")
    parser.add_argument("--output", type=Path, default=None, help="File HTML đầu ra (mặc định: index.html cạnh script)")
    parser.add_argument("--title", default=None, help="Ghi đè tên archive trong config.toml")
    parser.add_argument("--theme", default=None, help="Ghi đè theme trong config.toml (auto hoặc: " + ", ".join(THEMES) + ")")
    parser.add_argument("--sort-by", default=None, choices=("name", "created", "created_desc"), help="Sắp xếp theo tên, ngày tạo tăng dần hoặc mới nhất trước")
    parser.add_argument("--ignore", action="append", default=[], metavar="MẪU", help="Bỏ qua thư mục khớp mẫu (lặp lại được; gộp với ignored_folders). Ví dụ: --ignore Thumbs --ignore \"Anime/2023\"")
    parser.add_argument("--icon", type=Path, default=None, help="File PNG dùng làm icon Màn hình chính iOS (ghi đè app_icon)")
    parser.add_argument("--no-zip", action="store_true", help="Không quét bên trong file .zip/.cbz (mặc định: coi chúng như thư mục ảo)")
    parser.add_argument("--unzipit", type=Path, default=None, metavar="FILE", help="File unzipit cục bộ để nhúng inline (unzipit.module.js hoặc unzipit.min.js)")
    parser.add_argument("--no-probe", action="store_true", help="Bỏ qua bước đọc kích thước ảnh (build nhanh hơn, nhưng trang có thể nhảy layout khi ảnh tải)")
    parser.add_argument("--clear-cache", action="store_true", help="Xóa cache kích thước ảnh rồi build lại")
    parser.add_argument("--open", action="store_true", help="Mở archive trong trình duyệt sau khi build")
    parser.add_argument("--watch", action="store_true", help="Theo dõi thư mục media và tự build lại khi có thay đổi (Ctrl+C để dừng)")
    parser.add_argument("--quiet", action="store_true", help="Chỉ in lỗi")
    args = parser.parse_args()
    if args.clear_cache:
        try:
            (script_dir / CACHE_FILENAME).unlink()
        except FileNotFoundError:
            pass
        except OSError as exc:
            print(f"Không xóa được cache: {exc}", file=sys.stderr)
    try:
        _count, output, _opts, folders = run_build(args, script_dir)
    except (OSError, ValueError) as exc:
        print(f"Lỗi: {exc}", file=sys.stderr)
        return 1
    if args.open:
        webbrowser.open(output.resolve().as_uri())
    if args.watch:
        print("Đang theo dõi thay đổi… (Ctrl+C để dừng)")
        signature = folder_signature(folders, _opts.ignored_folders, _opts.zip_support)
        try:
            while True:
                time.sleep(2.0)
                current = folder_signature(folders, _opts.ignored_folders, _opts.zip_support)
                if current != signature:
                    signature = current
                    try:
                        run_build(args, script_dir)
                    except (OSError, ValueError) as exc:
                        print(f"Lỗi: {exc}", file=sys.stderr)
        except KeyboardInterrupt:
            print("\nĐã dừng.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
