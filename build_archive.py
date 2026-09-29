#!/usr/bin/env python3
"""Build an offline, single-file Tumblr-style image archive from ./images."""
from __future__ import annotations

import argparse
import base64
from datetime import datetime
import hashlib
import json
import os
import re
import sys
from html import escape as html_escape
from pathlib import Path
from urllib.parse import quote

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
}

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif", ".bmp", ".svg", ".apng", ".jxl", ".heic", ".heif"}
VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov", ".m4v", ".ogv"}
MEDIA_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS
IGNORED_MEDIA_DIRS = {"@eaDir", "__MACOSX"}
TUMBLR_MEDIA_SEQUENCE = re.compile(r"^(tumblr_.+?)o(\d+)(?:_r\d+)?_\d+$", re.IGNORECASE)
TUMBLR_ID = re.compile(r"^(tumblr_[A-Za-z0-9]+)(?:_|$)", re.IGNORECASE)
NUMERIC_MEDIA_SEQUENCE = re.compile(r"^(\d+)_\d+$")
NAMED_MEDIA_SEQUENCE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9_-]*)\s+(\d+)\s+(.+)$")


def natural_key(value: str):
    return [(1, int(part)) if part.isdigit() else (0, part.casefold())
            for part in re.split(r"(\d+)", value)]


def file_created_time(path: Path) -> float:
    stat = path.stat()
    return float(getattr(stat, "st_birthtime", stat.st_ctime))


def image_group_id(filename: str) -> str:
    """Group Tumblr image sequence files by their post id.

    Tumblr's ``o1``, ``o2`` suffix identifies a post's media item; optional
    ``_rN`` and size suffixes identify variants. Numeric archive names such
    as ``128635952498_0.jpg`` use ``_<index>`` for media in one post. Names
    such as ``1h5bjv8 01 Cute Asian.jpg`` share a group by id and title.
    Other filenames are grouped only by their complete stem.
    """
    path = Path(filename)
    match = TUMBLR_MEDIA_SEQUENCE.match(path.stem)
    if match:
        return match.group(1).casefold()
    match = TUMBLR_ID.match(path.name)
    if match:
        return match.group(1).casefold()
    match = NAMED_MEDIA_SEQUENCE.match(path.stem)
    if match:
        series_id, _sequence, title = match.groups()
        normalized_title = " ".join(title.split()).casefold()
        return f"{series_id.casefold()} {normalized_title}"
    sequence = NUMERIC_MEDIA_SEQUENCE.match(path.stem)
    if sequence:
        return f"numeric-post-{sequence.group(1)}"
    return path.stem


def build_posts(images_dir: Path):
    files = [p for p in images_dir.rglob("*")
             if p.is_file()
             and all(not part.startswith(".") and part not in IGNORED_MEDIA_DIRS
                     for part in p.relative_to(images_dir).parts)
             and p.suffix.casefold() in MEDIA_EXTENSIONS]
    files.sort(key=lambda p: natural_key(p.relative_to(images_dir).as_posix()))
    groups: dict[str, list[Path]] = {}
    for path in files:
        relative = path.relative_to(images_dir)
        group_id = image_group_id(path.name).casefold()
        parent = relative.parent.as_posix()
        key = f"{parent}::{group_id}" if parent != "." else group_id
        groups.setdefault(key, []).append(path)
    return [{"id": key, "images": [p.relative_to(images_dir).as_posix() for p in paths]}
            for key, paths in groups.items()]


def markdown_sidecar(filename: str, used: set[Path], by_stem: dict[str, Path]) -> Path | None:
    """Find a Markdown note matching a media filename, or its grouped post."""
    media = Path(filename)
    candidates = [media.parent / media.stem]
    group_id = image_group_id(filename)
    if group_id.startswith("numeric-post-"):
        # Keep compatible with Python 3.8, which lacks str.removeprefix().
        group_stem = group_id[len("numeric-post-"):]
    else:
        group_stem = group_id
    candidates.append(media.parent / group_stem)
    for stem in candidates:
        match = by_stem.get(stem.as_posix().casefold())
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
    list_items: list[str] = []
    def flush_paragraph():
        if paragraph:
            output.append("<p>" + "<br>".join(inline(line) for line in paragraph) + "</p>")
            paragraph.clear()
    def flush_list():
        if list_items:
            output.append("<ul>" + "".join(f"<li>{inline(item)}</li>" for item in list_items) + "</ul>")
            list_items.clear()
    for raw_line in source.splitlines():
        line = raw_line.strip()
        heading = re.match(r"^(#{1,4})\s+(.+)$", line)
        if heading:
            flush_paragraph(); flush_list()
            level = min(len(heading.group(1)) + 2, 6)
            output.append(f"<h{level}>{inline(heading.group(2))}</h{level}>")
        elif line.startswith(("- ", "* ", "+ ")):
            flush_paragraph()
            list_items.append(line[2:])
        elif not line:
            flush_paragraph(); flush_list()
        else:
            flush_list()
            paragraph.append(line)
    flush_paragraph(); flush_list()
    return "".join(output)


DEFAULT_CONFIG = {"title": "", "images_dir": "", "images_dirs": [], "theme": "auto", "theme_light": "rose-pine-dawn", "theme_dark": "mocha", "sort_by": "name", "sticky_header": "true", "show_filename": "false", "show_created_time": "false", "show_file_size": "false", "show_video_thumbnails": "false", "folder_filter_depth": "1", "show_media_info": "false"}


def _strip_yaml_comment(value: str) -> str:
    quote_char = None
    escaped = False
    for i, char in enumerate(value):
        if escaped:
            escaped = False
        elif char == "\\" and quote_char == '"':
            escaped = True
        elif quote_char:
            if char == quote_char:
                quote_char = None
        elif char in ("'", '"'):
            quote_char = char
        elif char == "#" and (i == 0 or value[i - 1].isspace()):
            return value[:i].rstrip()
    return value.strip()


def _yaml_scalar(value: str) -> str:
    value = _strip_yaml_comment(value.strip())
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        if value[0] == '"':
            try:
                return str(json.loads(value))
            except json.JSONDecodeError:
                return value[1:-1]
        return value[1:-1].replace("''", "'")
    return value


def _parse_simple_yaml(path: Path) -> dict[str, object]:
    """Parse flat YAML settings and an images_dirs block list."""
    values: dict[str, object] = {}
    list_key: str | None = None
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped in ("---", "..."):
            continue
        if list_key and line[:1].isspace():
            item = re.match(r"^-\s*(.*?)\s*$", stripped)
            if item:
                values.setdefault(list_key, []).append(_yaml_scalar(item.group(1)))
                continue
        list_key = None
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*?)\s*$", stripped)
        if not match:
            raise ValueError(f"config.yml dòng {line_no}: dùng khóa dạng key: value hoặc danh sách images_dirs với dấu gạch ngang")
        key, value = match.groups()
        key = key.casefold()
        if key == "images_dirs" and not value:
            values[key] = []
            list_key = key
            continue
        if key == "images_dirs" and value.startswith("[") and value.endswith("]"):
            body = value[1:-1].strip()
            values[key] = [_yaml_scalar(part) for part in body.split(",") if part.strip()]
            continue
        value = _yaml_scalar(value)
        if value.startswith(("{", "|", ">")):
            raise ValueError(f"config.yml dòng {line_no}: chỉ hỗ trợ giá trị chữ đơn giản")
        values[key] = value
    return values

def load_config(script_dir: Path) -> tuple[dict[str, object], Path | None]:
    candidates = [script_dir / "config.yml", Path.cwd() / "config.yml"]
    config_path = next((path for path in candidates if path.is_file()), None)
    config = dict(DEFAULT_CONFIG)
    if config_path is None:
        return config, None
    loaded = _parse_simple_yaml(config_path)
    aliases = {"name": "title", "website_name": "title", "image_dir": "images_dir", "images": "images_dir", "image_folders": "images_dirs", "folders": "images_dirs", "sort": "sort_by", "order": "sort_by"}
    for key, value in loaded.items():
        key = aliases.get(key, key)
        if key in config:
            config[key] = value
    if "show_media_info" in loaded:
        for key in ("show_filename", "show_created_time"):
            if key not in loaded:
                config[key] = loaded["show_media_info"]
    return config, config_path


HTML = r'''<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="color-scheme" content="__COLOR_SCHEME__"><title>__ARCHIVE_TITLE__</title>__FAVICON_LINK__
<style>
:root{color-scheme:__COLOR_SCHEME__;__THEME_VARS__}
*{box-sizing:border-box}body{margin:0;background:var(--base);color:var(--text);font:16px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif;padding:20px 12px calc(96px + env(safe-area-inset-bottom))}
header{padding:8px 0 9px}.site-header{position:sticky;top:0;z-index:9;display:flex;align-items:center;justify-content:space-between;gap:16px;margin:-20px -12px 8px;padding:10px 16px;background:rgba(24,24,37,.82);background:color-mix(in srgb,var(--mantle) 82%,transparent);-webkit-backdrop-filter:blur(16px) saturate(180%);backdrop-filter:blur(16px) saturate(180%);border-bottom:1px solid color-mix(in srgb,var(--surface1) 75%,transparent);box-shadow:0 5px 18px #0003;transition:padding .18s ease,box-shadow .18s ease}.header-brand{display:flex;align-items:center;gap:12px;min-width:0}.header-title-wrap{min-width:0}.site-header h1{font-size:clamp(19px,2.7vw,25px);line-height:1.15;margin:0;background:linear-gradient(100deg,var(--mauve),var(--blue));background-clip:text;-webkit-background-clip:text;color:transparent;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;text-shadow:none;transition:font-size .18s ease}.header-count{flex:none;padding:4px 9px;border:1px solid color-mix(in srgb,var(--mauve) 32%,var(--surface1));border-radius:999px;background:color-mix(in srgb,var(--mauve) 12%,var(--surface0));color:var(--subtext);font-size:11px;font-weight:700;white-space:nowrap}.site-header #summary{color:var(--subtext);font-size:11px;margin-top:3px;max-height:30px;opacity:1;transition:opacity .15s ease,max-height .18s ease,margin .18s ease}.site-header.compact{padding-top:5px;padding-bottom:5px;box-shadow:0 3px 12px #0003}.site-header.compact h1{font-size:16px}.site-header.compact #summary{max-height:0;opacity:0;margin:0;overflow:hidden}.header-tools{display:flex;align-items:center;gap:6px;flex:none}.header-tool{display:inline-flex;align-items:center;gap:7px;padding:7px 10px;border:1px solid var(--surface1);border-radius:10px;background:color-mix(in srgb,var(--surface0) 72%,transparent);color:var(--text);font-family:inherit;font-size:12px;font-weight:600;cursor:pointer;transition:transform .16s ease,border-color .16s ease,background .16s ease}.header-tool:hover,.header-tool:focus-visible{transform:translateY(-1px);border-color:var(--mauve);background:color-mix(in srgb,var(--mauve) 14%,var(--surface0));outline:none}.header-tool kbd{font-size:10px}body.header-not-sticky .site-header{position:static;margin:0;padding:10px 0;border-bottom:0;box-shadow:none;background:transparent;-webkit-backdrop-filter:none;backdrop-filter:none}body.header-not-sticky .site-header.compact{padding:10px 0}@media(max-width:760px){.site-header{padding:7px 10px;gap:6px}.header-brand{width:100%;gap:8px}.header-title-wrap{flex:1}.site-header h1{font-size:16px}.site-header #summary,.header-tools{display:none}.header-count{padding:3px 7px;font-size:10px}.site-header.compact{padding-top:4px;padding-bottom:4px}.site-header.compact h1{font-size:14px}body.header-not-sticky .site-header{padding:7px 0}body.header-not-sticky .site-header.compact{padding:7px 0}}
.feed{max-width:600px;margin:auto;display:grid;gap:22px}.post{overflow:hidden;background:var(--mantle);border:1px solid color-mix(in srgb,var(--surface1) 50%,transparent);border-radius:3px;box-shadow:0 1px 4px #0002;scroll-margin:18px}.post.hidden{display:none}.post.multi-media{border-color:#8b72ad;box-shadow:0 8px 24px #0003,0 0 0 1px #cba6f733}.post-heading{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:10px 14px;border-bottom:1px solid var(--surface0);background:var(--mantle)}.post.multi-media .post-heading{border-left:4px solid var(--mauve);background:color-mix(in srgb,var(--mauve) 9%,var(--mantle))}.post-title{font-size:12px;font-weight:700;color:var(--text)}.post-count{flex:none;border:1px solid color-mix(in srgb,var(--surface1) 75%,transparent);border-radius:9px;padding:4px 9px;color:var(--text);font:600 10px/1.3 ui-monospace,SFMono-Regular,Menlo,monospace;background:color-mix(in srgb,var(--surface0) 58%,transparent);backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px)}.post.multi-media .post-count{border-color:color-mix(in srgb,var(--mauve) 55%,transparent);background:color-mix(in srgb,var(--mauve) 13%,transparent);color:var(--mauve)}.post-images{display:grid;gap:0;padding:0}.media-item{position:relative;min-width:0}.post.multi-media .media-item+.media-item{border-top:1px solid var(--surface1);margin-top:0;padding-top:8px}.media-number{position:absolute;z-index:2;top:8px;left:8px;padding:4px 8px;border:1px solid var(--surface1);border-radius:20px;background:color-mix(in srgb,var(--mantle) 94%,transparent);color:var(--mauve);font-size:11px;font-weight:700;pointer-events:none}.post-images img,.post-images video{display:block;width:100%;height:auto;max-height:80vh;min-height:90px;background:var(--crust);color:var(--subtext);object-fit:contain;border-radius:0}.post-images img{cursor:zoom-in}.video-wrap{position:relative}.video-wrap video{width:100%}.media-open{position:absolute;right:10px;top:10px;border:1px solid var(--surface1);background:color-mix(in srgb,var(--mantle) 92%,transparent);color:var(--text);border-radius:9px;padding:6px 10px;cursor:pointer}.post-footer{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:10px 15px;border-top:1px solid var(--surface0);color:var(--subtext);font-size:13px}.return-archive-btn{display:none;border:1px solid var(--surface1);border-radius:8px;background:var(--surface0);color:var(--mauve);padding:6px 9px;font-size:11px;font-weight:700;cursor:pointer}.return-archive-btn.visible{display:inline-flex}
button{font:inherit;color:inherit}.like{display:grid;place-items:center;width:38px;height:38px;border:1px solid transparent;border-radius:50%;background:color-mix(in srgb,var(--surface0) 55%,transparent);color:var(--subtext);cursor:pointer;font-size:21px;font-weight:700;padding:0;transition:color .16s,background .16s,border-color .16s,transform .16s}.like:hover{color:var(--mauve);background:color-mix(in srgb,var(--mauve) 13%,var(--surface0));transform:scale(1.06)}.like.is-liked{color:var(--red);border-color:color-mix(in srgb,var(--red) 42%,transparent);background:color-mix(in srgb,var(--red) 12%,var(--mantle))}.like.is-liked:hover{color:var(--red);background:color-mix(in srgb,var(--red) 19%,var(--mantle))}.like:focus-visible,button:focus-visible,input:focus-visible{outline:2px solid var(--mauve);outline-offset:2px}.controls{position:fixed;z-index:10;left:0;right:0;bottom:0;padding:8px 10px calc(8px + env(safe-area-inset-bottom));display:flex;justify-content:center;gap:7px;background:color-mix(in srgb,var(--mantle) 80%,transparent);border-top:1px solid var(--surface0);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px)}.toolbar-btn{position:relative;min-width:0;flex:1;display:flex;align-items:center;justify-content:center;gap:5px;border:1px solid var(--surface1);border-radius:11px;background:var(--surface0);padding:9px 8px;font-size:13px;font-weight:650;cursor:pointer;white-space:nowrap}.toolbar-btn:hover,.toolbar-btn:focus-visible,.settings-menu button:hover{filter:brightness(1.22);border-color:var(--mauve);box-shadow:0 0 0 2px color-mix(in srgb,var(--mauve) 28%,transparent);transform:translateY(-1px)}.toolbar-btn.active{background:var(--red);border-color:var(--red);color:var(--crust)}.toolbar-btn.accent{background:var(--mauve);border-color:var(--mauve);color:var(--crust)}.toolbar-icon{font-size:18px;line-height:1}.toolbar-label{font-size:11px}.like-count{font-size:11px;font-weight:700}.settings-menu{display:none;position:absolute;right:7px;bottom:calc(100% + 8px);min-width:190px;padding:7px;background:var(--mantle);border:1px solid var(--surface1);border-radius:13px;box-shadow:0 10px 25px #0007}.settings-menu.open{display:grid;gap:3px}.settings-menu button{border:0;border-radius:8px;background:transparent;color:var(--text);text-align:left;padding:9px 11px;font-size:13px;cursor:pointer}.menu-separator{height:1px;background:var(--surface0);margin:4px 2px}.filter-control{position:relative;min-width:0;flex:1}.filter-control>.toolbar-btn{width:100%}.filter-popover{display:none;position:fixed;z-index:20;left:8px;right:8px;bottom:calc(64px + env(safe-area-inset-bottom));max-height:min(62dvh,540px);overflow:auto;padding:9px;background:color-mix(in srgb,var(--mantle) 96%,transparent);border:1px solid var(--surface1);border-radius:15px;box-shadow:0 12px 35px #0007;backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);overscroll-behavior:contain}.filter-popover.open{display:block}.filter-check span{min-width:0;overflow-wrap:anywhere}.folder-filter-section:not([hidden]){display:block}.filter-heading{padding:4px 10px;color:var(--subtext);font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:.06em}.filter-check{display:flex;align-items:center;gap:10px;padding:8px 10px;border-radius:8px;color:var(--text);font-size:13px;cursor:pointer}.filter-check:hover{background:var(--surface0)}.filter-check input{width:17px;height:17px;margin:0;accent-color:var(--mauve)}.collapse-toggle{display:none}.btn{border:1px solid var(--surface1);border-radius:9px;background:var(--surface0);padding:8px 12px;cursor:pointer}
#toast{position:fixed;z-index:30;top:15px;left:50%;transform:translateX(-50%);background:var(--mauve);color:var(--crust);padding:9px 15px;border-radius:30px;font-weight:700;font-size:13px;box-shadow:0 8px 24px #0005;opacity:0;pointer-events:none;transition:opacity .2s}#toast.show{opacity:1}
#lightbox{position:fixed;inset:0;z-index:20;background:#11111bf5;display:none;align-items:center;justify-content:center;touch-action:pan-y;user-select:none}#lightbox.active{display:flex}#lbImg,#lbVideo{max-width:min(90vw,1500px);max-height:82dvh;object-fit:contain;border-radius:7px;transition:opacity .12s}#lbVideo{width:auto;height:auto;background:#000}#lbImg.loading{opacity:.25}.lb-btn{position:absolute;z-index:2;width:46px;height:46px;border-radius:50%;border:1px solid var(--surface1);background:var(--surface0);font-size:22px;cursor:pointer}.lb-close{top:15px;right:15px;color:var(--red)}.lb-prev{left:12px;top:50%;transform:translateY(-50%)}.lb-next{right:12px;top:50%;transform:translateY(-50%)}.lb-bar{position:absolute;bottom:calc(14px + env(safe-area-inset-bottom));display:flex;align-items:center;gap:12px;border:1px solid var(--surface1);border-radius:30px;background:var(--surface0);padding:5px 12px}.lb-counter{font-size:13px;font-weight:700;color:var(--mauve)}
#help{position:fixed;inset:0;z-index:25;background:#11111bdd;display:none;place-items:center;padding:16px}#help.active{display:grid}.help-card{max-width:460px;width:100%;max-height:85dvh;overflow:auto;background:var(--mantle);border:1px solid var(--surface1);border-radius:17px;padding:20px}.help-card h2{margin:0;color:var(--mauve)}.help-title{display:flex;justify-content:space-between;align-items:center;padding-bottom:12px;margin-bottom:12px;border-bottom:1px solid var(--surface0)}.version-badge{border:1px solid var(--surface1);border-radius:20px;padding:3px 8px;color:var(--peach);font-size:11px;font-weight:700}.help-card h3{margin:16px 0 6px;font-size:14px;color:var(--mauve)}.help-card p{margin:8px 0;color:var(--subtext)}.help-card ul{margin:4px 0 16px;padding-left:20px;color:var(--subtext);font-size:13px}.help-card li{margin:5px 0}kbd{background:var(--surface0);border:1px solid var(--surface1);padding:1px 6px;border-radius:5px;color:var(--blue)}#empty{max-width:680px;margin:30px auto;text-align:center;color:var(--subtext)}
@media(min-width:800px){.filter-control{flex:none;width:38px;height:38px}.filter-control>.toolbar-btn{width:38px;height:38px;padding:0}.filter-popover{position:absolute;left:auto;right:calc(100% + 9px);bottom:0;width:260px;max-height:min(72dvh,620px)}body{padding-bottom:35px}.controls{left:auto;right:20px;bottom:24px;width:52px;flex-direction:column;align-items:center;gap:7px;border:1px solid var(--surface0);border-radius:17px;padding:7px;background:color-mix(in srgb,var(--mantle) 80%,transparent);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);box-shadow:0 10px 28px #0006}.toolbar-btn{flex:none;width:38px;height:38px;padding:0;font-size:18px;border-radius:12px}.toolbar-label{display:none}.like-count{position:absolute;top:-5px;right:-5px;min-width:16px;height:16px;padding:0 4px;display:grid;place-items:center;border-radius:10px;background:var(--mauve);color:var(--crust);font-size:10px}.collapse-toggle{display:flex}.settings-menu{right:calc(100% + 9px);bottom:0}.controls.collapsed{width:42px;border-radius:50%;padding:4px}.controls.collapsed .toolbar-btn:not(.collapse-toggle){display:none}.controls.collapsed .filter-control{display:none}.controls.collapsed .collapse-toggle{width:32px;height:32px;border-radius:50%}.lb-prev{left:30px}.lb-next{right:30px}}
@media(max-width:420px){.controls{gap:4px;padding-left:5px;padding-right:5px}.toolbar-btn{padding:8px 5px;font-size:12px}.toolbar-label{font-size:10px}.lb-prev{left:7px}.lb-next{right:7px}.settings-menu{right:5px;min-width:min(88vw,230px)}}
.media-note{padding:12px 15px;margin-top:8px;border-left:3px solid var(--mauve);background:color-mix(in srgb,var(--surface0) 48%,var(--mantle));color:var(--text);font-size:14px;overflow-wrap:anywhere}.media-note p{margin:0 0 9px}.media-note p:last-child{margin-bottom:0}.media-note h3,.media-note h4,.media-note h5,.media-note h6{margin:5px 0 8px;color:var(--mauve);line-height:1.3}.media-note ul{margin:5px 0;padding-left:22px}.media-note code{padding:2px 5px;border-radius:5px;background:var(--crust);color:var(--peach);font:.9em ui-monospace,monospace}.media-note a{color:var(--blue);text-decoration:underline;text-underline-offset:2px}
.media-meta{padding:7px 12px 2px;color:var(--subtext);font-size:11px;text-align:right;overflow-wrap:anywhere}.theme-select-label{display:grid;gap:6px;padding:5px 10px 8px;color:var(--subtext);font-size:12px}.theme-select-label select{width:100%;border:1px solid var(--surface1);border-radius:8px;background:var(--surface0);color:var(--text);padding:8px;font:inherit}
.feed.grid-view{display:block;max-width:1200px;column-count:3;column-gap:16px}.feed.grid-view .post{display:inline-block;width:100%;break-inside:avoid;-webkit-column-break-inside:avoid;vertical-align:top;margin:0 0 16px;border-radius:13px}.feed.grid-view .post.hidden{display:none}.feed.grid-view .post-images{display:block;min-height:0;padding:8px}.feed.grid-view .media-item{display:none;min-height:0}.feed.grid-view .media-item.grid-primary{display:block}.feed.grid-view .post-images img,.feed.grid-view .post-images video{height:auto;min-height:0;max-height:320px;object-fit:cover;border-radius:8px}.feed.grid-view .video-wrap{min-height:0}.feed.grid-view .media-note{font-size:12px;max-height:105px;overflow:hidden}.grid-media-badge{display:none;position:absolute;z-index:3;right:8px;top:8px;padding:5px 8px;border:1px solid color-mix(in srgb,var(--surface1) 80%,transparent);border-radius:9px;background:color-mix(in srgb,var(--mantle) 82%,transparent);backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);color:var(--text);font-size:11px;font-weight:750;pointer-events:none}.feed.grid-view .media-item.grid-primary .grid-media-badge{display:block}@media(max-width:900px){.feed.grid-view{column-count:2}}@media(max-width:560px){.feed.grid-view{column-count:1}}.search-dialog{position:fixed;inset:0;z-index:27;display:none;place-items:center;padding:16px;background:#11111bd9}.search-dialog.active{display:grid}.search-card{width:min(620px,100%);max-height:88dvh;display:flex;flex-direction:column;gap:10px;padding:16px;background:var(--mantle);color:var(--text);border:1px solid var(--surface1);border-radius:17px;box-shadow:0 18px 55px #0008}.search-heading{display:flex;align-items:center;justify-content:space-between;gap:12px}.search-heading h2{margin:0;color:var(--mauve);font-size:17px}.search-close{width:34px;height:34px;border:1px solid var(--surface1);border-radius:10px;background:var(--surface0);font-size:22px;cursor:pointer}.search-card>input{width:100%;border:1px solid var(--surface1);border-radius:10px;background:var(--base);color:var(--text);padding:11px 13px;font:inherit}.search-count{min-height:17px;color:var(--subtext);font-size:11px}.search-results{overflow:auto;display:grid;gap:7px;overscroll-behavior:contain}.search-result{width:100%;display:grid;grid-template-columns:68px minmax(0,1fr);align-items:center;gap:11px;padding:7px;text-align:left;border:1px solid var(--surface0);border-radius:11px;background:color-mix(in srgb,var(--surface0) 52%,var(--mantle));color:var(--text);cursor:pointer}.search-result:hover,.search-result:focus-visible{border-color:var(--mauve);background:color-mix(in srgb,var(--mauve) 12%,var(--surface0))}.search-thumb,.search-video-thumb{width:68px;height:58px;display:grid;place-items:center;border-radius:7px;background:var(--crust);object-fit:cover;color:var(--mauve);font-size:23px}.search-result-text{min-width:0;display:grid;gap:3px}.search-result-title{font-size:13px;font-weight:750}.search-result-detail{overflow:hidden;color:var(--subtext);font-size:11px;text-overflow:ellipsis;white-space:nowrap}.search-empty{padding:22px 10px;text-align:center;color:var(--subtext);font-size:13px}@media(max-width:700px){.search-dialog{position:fixed;inset:auto 0 auto;top:var(--search-vv-top,0px);height:var(--search-vv-height,100dvh);place-items:start center;overflow:hidden;padding:8px 10px calc(8px + env(safe-area-inset-bottom));}.search-card{margin-top:0;max-height:calc(var(--search-vv-height,100dvh) - 16px);overflow:hidden}.search-results{min-height:0}}

/* Modern archive surfaces — theme-aware across Catppuccin and custom palettes */
body{background:radial-gradient(ellipse 70% 34rem at 50% -18rem,color-mix(in srgb,var(--mauve) 13%,transparent),transparent 72%),var(--base)}
.feed{max-width:720px;gap:24px}
.post{border:1px solid color-mix(in srgb,var(--surface1) 68%,transparent);border-radius:20px;background:color-mix(in srgb,var(--mantle) 96%,transparent);box-shadow:0 12px 36px #00000012;scroll-margin:calc(var(--header-sticky-offset,0px) + 14px);transition:border-color .18s ease,box-shadow .18s ease}
.post:hover{border-color:color-mix(in srgb,var(--mauve) 34%,var(--surface1));box-shadow:0 16px 42px #0000001c}
.post.multi-media{border-color:color-mix(in srgb,var(--mauve) 52%,var(--surface1));box-shadow:0 12px 36px #00000016,0 0 0 1px color-mix(in srgb,var(--mauve) 12%,transparent)}
.post-heading{padding:12px 16px;background:color-mix(in srgb,var(--surface0) 34%,var(--mantle));border-bottom:1px solid color-mix(in srgb,var(--surface1) 55%,transparent)}
.post.multi-media .post-heading{border-left:0;background:linear-gradient(100deg,color-mix(in srgb,var(--mauve) 12%,var(--mantle)),color-mix(in srgb,var(--surface0) 22%,var(--mantle)))}
.post-title{font-size:13px;letter-spacing:.01em}
.post-count{border-radius:999px;padding:5px 10px;font-size:10px;background:color-mix(in srgb,var(--surface0) 72%,transparent)}
.post-images{gap:10px;padding:10px}
.post.multi-media .media-item+.media-item{border-top:1px solid color-mix(in srgb,var(--surface1) 58%,transparent);padding-top:10px}
.post-images img,.post-images video{border-radius:13px;background:var(--base)}
.media-number{top:10px;left:10px;border-color:color-mix(in srgb,var(--surface1) 65%,transparent);border-radius:999px;padding:5px 9px;background:color-mix(in srgb,var(--mantle) 82%,transparent);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);color:var(--text)}
.media-open{border-radius:999px;padding:7px 12px;background:color-mix(in srgb,var(--mantle) 78%,transparent);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px)}
.post-footer{padding:9px 14px;border-top:1px solid color-mix(in srgb,var(--surface1) 42%,transparent);font-size:12px}
.post-footer .like{width:36px;height:36px}
.media-note{margin:2px 10px 10px;padding:13px 15px;border:1px solid color-mix(in srgb,var(--surface1) 58%,transparent);border-left:3px solid var(--mauve);border-radius:12px;background:color-mix(in srgb,var(--surface0) 38%,var(--mantle))}
.controls{gap:8px;background:color-mix(in srgb,var(--mantle) 76%,transparent);border-color:color-mix(in srgb,var(--surface1) 60%,transparent);box-shadow:0 8px 32px #00000012}
.toolbar-btn{border-color:color-mix(in srgb,var(--surface1) 72%,transparent);border-radius:14px;background:color-mix(in srgb,var(--surface0) 84%,transparent);transition:transform .16s ease,border-color .16s ease,background .16s ease,box-shadow .16s ease}
.toolbar-btn:hover,.toolbar-btn:focus-visible{filter:none;background:color-mix(in srgb,var(--mauve) 13%,var(--surface0));box-shadow:0 5px 16px color-mix(in srgb,var(--mauve) 16%,transparent);transform:translateY(-2px)}
.toolbar-btn.accent{background:linear-gradient(135deg,var(--mauve),color-mix(in srgb,var(--mauve) 65%,var(--blue)));border-color:transparent;color:var(--crust)}
.toolbar-icon{display:grid;place-items:center}.toolbar-icon svg{display:block}
.settings-menu{padding:8px;border-color:color-mix(in srgb,var(--surface1) 76%,transparent);border-radius:17px;background:color-mix(in srgb,var(--mantle) 92%,transparent);backdrop-filter:blur(18px);-webkit-backdrop-filter:blur(18px);box-shadow:0 18px 48px #00000028}
.settings-menu button{border-radius:10px}.settings-menu button:hover{filter:none;background:color-mix(in srgb,var(--mauve) 12%,var(--surface0));box-shadow:none;transform:none}
.search-card{border-color:color-mix(in srgb,var(--surface1) 70%,transparent);border-radius:22px;background:color-mix(in srgb,var(--mantle) 94%,transparent);backdrop-filter:blur(18px);-webkit-backdrop-filter:blur(18px);box-shadow:0 24px 70px #00000035}
.search-card>input{border-radius:13px}.search-result{border-radius:14px}.search-result:hover,.search-result:focus-visible{transform:translateY(-1px)}
.search-close{border-radius:11px;color:var(--subtext)}
@media(max-width:760px){body{padding-left:10px;padding-right:10px}.feed{max-width:640px;gap:17px}.post{border-radius:17px}.post-heading{padding:10px 13px}.post-images{gap:8px;padding:8px}.post-images img,.post-images video{border-radius:11px}.post-footer{padding:8px 12px}.controls{gap:6px;padding:7px 8px calc(7px + env(safe-area-inset-bottom))}.toolbar-btn{border-radius:13px}.search-dialog{padding:8px 10px calc(8px + env(safe-area-inset-bottom))}.search-card{border-radius:18px}}
@media(prefers-reduced-motion:reduce){.post,.toolbar-btn,.search-result{transition:none}}

body.style-classic{background:var(--base)}
body.style-classic .feed{max-width:600px;gap:22px}
body.style-classic .post{border:1px solid color-mix(in srgb,var(--surface1) 50%,transparent);border-radius:3px;background:var(--mantle);box-shadow:0 1px 4px #0002}
body.style-classic .post:hover{border-color:color-mix(in srgb,var(--surface1) 50%,transparent);box-shadow:0 1px 4px #0002}
body.style-classic .post.multi-media{border-color:#8b72ad;box-shadow:0 8px 24px #0003,0 0 0 1px #cba6f733}
body.style-classic .post-heading{padding:10px 14px;background:var(--mantle);border-bottom:1px solid var(--surface0)}
body.style-classic .post.multi-media .post-heading{border-left:4px solid var(--mauve);background:color-mix(in srgb,var(--mauve) 9%,var(--mantle))}
body.style-classic .post-title{font-size:12px}
body.style-classic .post-count{border-radius:9px;padding:4px 9px}
body.style-classic .post-images{gap:0;padding:0}
body.style-classic .post.multi-media .media-item+.media-item{border-top:1px solid var(--surface1);padding-top:8px}
body.style-classic .post-images img,body.style-classic .post-images video{border-radius:0}
body.style-classic .media-number{border-radius:20px;background:color-mix(in srgb,var(--mantle) 94%,transparent);color:var(--mauve)}
body.style-classic .post-footer{padding:10px 15px;border-top:1px solid var(--surface0);font-size:13px}
body.style-classic .media-note{margin:8px 0 0;padding:12px 15px;border:0;border-left:3px solid var(--mauve);border-radius:0;background:color-mix(in srgb,var(--surface0) 48%,var(--mantle))}
body.style-classic .controls{gap:7px;background:color-mix(in srgb,var(--mantle) 80%,transparent);border-color:var(--surface0);box-shadow:none}
body.style-classic .toolbar-btn{border-color:var(--surface1);border-radius:11px;background:var(--surface0)}
body.style-classic .toolbar-btn:hover,body.style-classic .toolbar-btn:focus-visible{filter:brightness(1.22);background:var(--surface0);box-shadow:0 0 0 2px color-mix(in srgb,var(--mauve) 28%,transparent);transform:translateY(-1px)}
body.style-classic .toolbar-btn.accent{background:var(--mauve);border-color:var(--mauve)}
body.style-classic .settings-menu{padding:7px;border-radius:13px;background:var(--mantle);backdrop-filter:none;-webkit-backdrop-filter:none;box-shadow:0 10px 25px #0007}
body.style-classic .search-card{border-radius:17px;background:var(--mantle);backdrop-filter:none;-webkit-backdrop-filter:none;box-shadow:0 18px 55px #0008}
body.style-classic .search-result{border-radius:11px}
@media(max-width:760px){body.style-classic{padding-left:12px;padding-right:12px}body.style-classic .feed{max-width:600px;gap:18px}body.style-classic .post{border-radius:3px}body.style-classic .post-images{gap:0;padding:0}body.style-classic .post-images img,body.style-classic .post-images video{border-radius:0}body.style-classic .controls{gap:5px;padding:8px 10px calc(8px + env(safe-area-inset-bottom))}}
.header-title-line{display:flex;align-items:center;gap:8px;min-width:0}.header-title-line h1{min-width:0}.header-version{flex:none;padding:2px 6px;border:1px solid color-mix(in srgb,var(--surface1) 70%,transparent);border-radius:999px;background:color-mix(in srgb,var(--surface0) 55%,transparent);color:var(--subtext);font:600 9px/1.3 ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:.02em}.post-count{display:inline-flex;align-items:center;gap:6px;min-height:26px}.post-count svg,.grid-media-badge svg{width:15px;height:15px;fill:none;stroke:currentColor;stroke-width:1.6;stroke-linecap:round;stroke-linejoin:round}.post-count span{white-space:nowrap}.grid-media-badge{display:none;align-items:center;gap:4px}.grid-media-badge svg{width:13px;height:13px}.post-footer{justify-content:flex-end}.return-archive-btn{margin-right:auto}.settings-menu{max-height:78dvh;overflow:auto;overscroll-behavior:contain}.style-switch-row{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:4px 6px 6px 10px;color:var(--subtext);font-size:11px;font-weight:700}.settings-menu .style-switch-row button{display:inline-flex;align-items:center;gap:7px;padding:5px 9px;border:1px solid color-mix(in srgb,var(--surface1) 66%,transparent);border-radius:999px;background:color-mix(in srgb,var(--surface0) 58%,transparent);color:var(--text);font-size:11px;font-weight:650}.settings-menu .style-switch-row button:hover{background:color-mix(in srgb,var(--mauve) 12%,var(--surface0));border-color:color-mix(in srgb,var(--mauve) 55%,var(--surface1));box-shadow:none;transform:none}.style-switch-dot{width:7px;height:7px;border-radius:50%;background:var(--mauve);box-shadow:0 0 0 3px color-mix(in srgb,var(--mauve) 15%,transparent)}@media(max-width:760px){.header-title-line{gap:6px}.header-version{font-size:8px;padding:2px 5px}.post-footer{padding:7px 10px}.settings-menu{max-height:72dvh}}
.post.is-liked-post{border-color:color-mix(in srgb,var(--pink) 65%,var(--surface1));box-shadow:0 0 0 2px color-mix(in srgb,var(--pink) 22%,transparent),0 14px 40px #00000020}.post.is-liked-post .post-heading{background:color-mix(in srgb,var(--pink) 9%,var(--mantle))}.post.is-liked-post.multi-media{border-color:color-mix(in srgb,var(--pink) 72%,var(--mauve));box-shadow:0 0 0 2px color-mix(in srgb,var(--pink) 24%,transparent),0 14px 40px #00000024}
#loadSentinel{height:1px;pointer-events:none}
.post-footer{display:flex;align-items:center;gap:10px;flex-wrap:wrap}.post-actions{display:flex;align-items:center;gap:8px;margin-left:auto}.post-source-folder{display:inline-flex;align-items:center;gap:6px;max-width:100%;padding:5px 9px;border:1px solid color-mix(in srgb,var(--blue) 26%,var(--surface1));border-radius:999px;background:color-mix(in srgb,var(--blue) 8%,var(--surface0));color:var(--subtext);font-size:11px;font-weight:650;overflow-wrap:anywhere}.post-source-folder svg{width:14px;height:14px;flex:none;fill:none;stroke:currentColor;stroke-width:1.7;stroke-linecap:round;stroke-linejoin:round}
#help{position:fixed;inset:0;z-index:25;display:none;place-items:center;padding:16px;background:color-mix(in srgb,var(--crust) 82%,transparent);backdrop-filter:blur(7px);-webkit-backdrop-filter:blur(7px)}#help.active{display:grid}.help-card{width:min(740px,100%);max-height:min(88dvh,900px);overflow:auto;padding:24px;border:1px solid color-mix(in srgb,var(--surface1) 78%,transparent);border-radius:24px;background:color-mix(in srgb,var(--mantle) 96%,transparent);color:var(--text);box-shadow:0 28px 90px #0007;overscroll-behavior:contain}.help-top{display:flex;justify-content:space-between;align-items:flex-start;gap:18px;padding-bottom:18px;margin-bottom:18px;border-bottom:1px solid color-mix(in srgb,var(--surface1) 55%,transparent)}.help-heading-copy{min-width:0}.help-kicker{display:block;margin-bottom:5px;color:var(--mauve);font-size:10px;font-weight:800;letter-spacing:.16em}.help-card h2{margin:0;color:var(--text);font-size:clamp(21px,4vw,28px);letter-spacing:-.035em}.help-heading-copy p{margin:5px 0 0;color:var(--subtext);font-size:13px}.help-head-actions{display:flex;align-items:center;gap:9px}.version-badge{border:1px solid color-mix(in srgb,var(--mauve) 42%,var(--surface1));border-radius:999px;padding:5px 10px;background:color-mix(in srgb,var(--mauve) 11%,var(--surface0));color:var(--mauve);font:700 11px ui-monospace,SFMono-Regular,Menlo,monospace}.help-dismiss{width:34px;height:34px;border:1px solid var(--surface1);border-radius:11px;background:var(--surface0);color:var(--subtext);font-size:22px;line-height:1;cursor:pointer}.shortcut-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.shortcut-group{min-width:0;padding:14px;border:1px solid color-mix(in srgb,var(--surface1) 52%,transparent);border-radius:16px;background:color-mix(in srgb,var(--surface0) 32%,var(--mantle))}.shortcut-group h3,.help-format h3{margin:0 0 9px;color:var(--mauve);font-size:13px;font-weight:750}.shortcut-group-wide{grid-column:1/-1;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));column-gap:12px}.shortcut-group-wide h3{grid-column:1/-1}.shortcut-row{min-height:43px;display:flex;align-items:center;gap:5px;padding:7px 0;border-top:1px solid color-mix(in srgb,var(--surface1) 35%,transparent)}.shortcut-row>span{display:grid;gap:1px;flex:1;min-width:0}.shortcut-row b{font-size:12px;font-weight:650}.shortcut-row small{color:var(--subtext);font-size:10px;line-height:1.35}.shortcut-row kbd{min-width:25px;padding:3px 6px;border:1px solid var(--surface1);border-radius:7px;background:color-mix(in srgb,var(--base) 78%,var(--surface0));color:var(--text);font:650 10px ui-monospace,SFMono-Regular,Menlo,monospace;text-align:center;white-space:nowrap}.help-changelog{margin-top:14px;border:1px solid color-mix(in srgb,var(--surface1) 54%,transparent);border-radius:14px;background:color-mix(in srgb,var(--surface0) 25%,var(--mantle))}.help-changelog summary{padding:11px 14px;color:var(--text);font-size:12px;font-weight:700;cursor:pointer}.help-changelog ul{margin:0;padding:0 18px 13px 34px;color:var(--subtext);font-size:12px}.help-changelog li{padding:3px 0}.help-format{margin:14px 2px 0}.help-format p{margin:0;color:var(--subtext);font-size:11px;line-height:1.6}
@media(max-width:600px){#help{padding:8px}.help-card{padding:17px;border-radius:19px;max-height:calc(100dvh - 16px)}.help-top{gap:8px;padding-bottom:13px;margin-bottom:13px}.help-heading-copy p{font-size:11px}.shortcut-grid{grid-template-columns:1fr;gap:9px}.shortcut-group{padding:11px 13px}.shortcut-group-wide{grid-column:auto;display:block}.shortcut-row{min-height:39px}.help-head-actions{gap:6px}.version-badge{padding:4px 7px;font-size:10px}}
</style></head><body class="__HEADER_STICKY_CLASS__">
<header class="site-header" id="siteHeader"><div class="header-brand"><div class="header-title-wrap"><div class="header-title-line"><h1>__ARCHIVE_TITLE__</h1><span class="header-version" title="Phiên bản archive">v2.14</span></div><div id="summary"></div></div><span class="header-count" title="Tổng số bài">__TOTAL_POSTS__ bài</span></div><nav class="header-tools" aria-label="Công cụ nhanh"><button class="header-tool" id="headerSearch" type="button" title="Tìm bài (G)">⌕ <span>Tìm</span><kbd>G</kbd></button><button class="header-tool" id="headerLayout" type="button" title="Đổi bố cục (V)">▦ <span>Lưới</span><kbd>V</kbd></button><button class="header-tool" id="headerBackup" type="button" title="Xuất backup (E)">↥ <span>Backup</span><kbd>E</kbd></button><button class="header-tool" id="headerTheme" type="button" title="Chọn theme (M)">◐ <span>Theme</span><kbd>M</kbd></button></nav></header><main class="feed" id="feed"></main><div id="loadSentinel" aria-hidden="true"></div><div id="empty" hidden>Không tìm thấy ảnh hoặc video trong thư mục media đã chọn hoặc các thư mục con.</div>
<nav class="controls" id="controls" aria-label="Điều khiển archive">
<button class="toolbar-btn collapse-toggle" id="collapseBtn" type="button" aria-label="Thu gọn toolbar" title="Thu gọn toolbar">−</button>
<div class="filter-control" id="filterControl"><button class="toolbar-btn" id="filterMenuToggle" type="button" aria-label="Mở bộ lọc" title="Bộ lọc" aria-expanded="false"><span class="toolbar-icon" aria-hidden="true">☷</span><span class="toolbar-label">Lọc</span></button><div class="filter-popover" id="filterPopover"><div class="filter-heading">Lọc nội dung</div><label class="filter-check"><input id="filterAll" type="checkbox" checked><span>Tất cả</span></label><label class="filter-check"><input class="media-filter-check" data-kind="image" type="checkbox" checked><span>Ảnh</span></label><label class="filter-check"><input class="media-filter-check" data-kind="gif" type="checkbox" checked><span>GIF</span></label><label class="filter-check"><input class="media-filter-check" data-kind="video" type="checkbox" checked><span>Video</span></label><div class="folder-filter-section" id="folderFilterSection" hidden><div class="menu-separator"></div><div class="filter-heading">Lọc thư mục</div><label class="filter-check"><input id="folderFilterAll" type="checkbox" checked><span>Tất cả thư mục</span></label><div id="folderFilterList"></div></div></div></div><button class="toolbar-btn" id="filterBtn" type="button" aria-label="Lọc bài đã thích" title="Bài đã thích"><span class="toolbar-icon" aria-hidden="true">♥</span><span class="toolbar-label">Đã thích</span><span class="like-count" id="likeCount">0</span></button>
<button class="toolbar-btn" id="jumpBtn" type="button" aria-label="Tìm bài đăng hoặc media" title="Tìm bài và media"><span class="toolbar-icon" aria-hidden="true">⌕</span><span class="toolbar-label">Tìm</span></button>
<button class="toolbar-btn accent" id="topBtn" type="button" aria-label="Lên đầu trang" title="Top"><span class="toolbar-icon" aria-hidden="true">↑</span><span class="toolbar-label">Top</span></button>
<button class="toolbar-btn" id="settingsBtn" type="button" aria-label="Cài đặt" title="Cài đặt" aria-expanded="false"><span class="toolbar-icon" aria-hidden="true"><svg viewBox="0 0 24 24" width="19" height="19" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 6h9m4 0h3M4 12h3m4 0h9M4 18h9m4 0h3"/><circle cx="15" cy="6" r="2"/><circle cx="9" cy="12" r="2"/><circle cx="15" cy="18" r="2"/></svg></span><span class="toolbar-label">More</span></button>
<div class="settings-menu" id="settingsMenu"><div class="style-switch-row"><span>Phong cách</span><button id="styleToggleBtn" type="button" aria-label="Đổi phong cách"><span class="style-switch-dot" aria-hidden="true"></span><span id="styleToggleLabel">Hiện đại</span></button></div><div class="filter-heading">Giao diện</div><label class="theme-select-label" for="themeSelect">Theme<select id="themeSelect"><option value="auto">Theo hệ thống</option><option value="mocha">Mocha</option><option value="frappe">Frappe</option><option value="macchiato">Macchiato</option><option value="latte">Latte</option><option value="nord">Nord</option><option value="tokyo-night">Tokyo Night</option><option value="gruvbox">Gruvbox</option><option value="rose-pine">Rose Pine</option><option value="noir-velvet">Noir Velvet</option><option value="oxblood">Oxblood</option><option value="nord-light">Nord Light</option><option value="tokyo-night-light">Tokyo Night Light</option><option value="gruvbox-light">Gruvbox Light</option><option value="rose-pine-dawn">Rosé Pine Dawn</option></select></label><label class="filter-check"><input id="gridView" type="checkbox"><span>Lưới gọn</span></label><div class="menu-separator"></div><button id="exportBtn" type="button">Export backup ↥</button><button id="importBtn" type="button">Import backup ↧</button><button id="helpBtn" type="button">Phím tắt & trợ giúp ?</button></div></nav>
<div id="toast" role="status" aria-live="polite"></div>
<section id="lightbox" aria-modal="true" role="dialog" aria-label="Xem ảnh phóng to"><button class="lb-btn lb-close" id="lbClose" aria-label="Đóng">×</button><button class="lb-btn lb-prev" id="lbPrev" aria-label="Ảnh trước">‹</button><img id="lbImg" alt="Ảnh phóng to"><video id="lbVideo" controls playsinline preload="metadata" hidden></video><button class="lb-btn lb-next" id="lbNext" aria-label="Ảnh tiếp">›</button><div class="lb-bar"><span id="lbCounter" class="lb-counter"></span><button id="lbLike" class="like" aria-label="Thích bài viết" aria-pressed="false">♥</button></div></section>
<section id="help" aria-modal="true" role="dialog" aria-labelledby="helpTitle"><div class="help-card"><div class="help-top"><div class="help-heading-copy"><span class="help-kicker">ARCHIVE GUIDE</span><h2 id="helpTitle">Phím tắt & trợ giúp</h2><p>Điều khiển archive nhanh bằng bàn phím hoặc toolbar.</p></div><div class="help-head-actions"><span class="version-badge">v2.14</span><button class="help-dismiss" id="helpClose" type="button" aria-label="Đóng trợ giúp">×</button></div></div><div class="shortcut-grid"><section class="shortcut-group"><h3>Duyệt bài</h3><div class="shortcut-row"><span><b>Bài tiếp</b><small>Đi xuống một bài</small></span><kbd>J</kbd><kbd>↓</kbd></div><div class="shortcut-row"><span><b>Bài trước</b><small>Quay lên một bài</small></span><kbd>K</kbd><kbd>↑</kbd></div><div class="shortcut-row"><span><b>Tiến / lùi</b><small>Chuyển bài nhanh</small></span><kbd>Space</kbd><kbd>⇧ Space</kbd></div><div class="shortcut-row"><span><b>Lên đầu</b><small>Về đầu archive</small></span><kbd>T</kbd></div></section><section class="shortcut-group"><h3>Công cụ</h3><div class="shortcut-row"><span><b>Tìm / nhảy tới bài</b><small>Nhập số, tên file hoặc ghi chú</small></span><kbd>G</kbd></div><div class="shortcut-row"><span><b>Thích / lọc bài đã thích</b><small>Lưu bài yêu thích</small></span><kbd>L</kbd><kbd>F</kbd></div><div class="shortcut-row"><span><b>Đổi bố cục</b><small>Lưới gọn / danh sách</small></span><kbd>V</kbd></div><div class="shortcut-row"><span><b>Đổi theme</b><small>Chọn giao diện màu</small></span><kbd>M</kbd></div><div class="shortcut-row"><span><b>Sao lưu</b><small>Sao lưu / khôi phục</small></span><kbd>E</kbd><kbd>I</kbd></div></section><section class="shortcut-group shortcut-group-wide"><h3>Lightbox</h3><div class="shortcut-row"><span><b>Ảnh / media tiếp theo</b><small>Vuốt ngang trên điện thoại</small></span><kbd>J</kbd><kbd>→</kbd></div><div class="shortcut-row"><span><b>Ảnh / media trước</b></span><kbd>K</kbd><kbd>←</kbd></div><div class="shortcut-row"><span><b>Đóng</b></span><kbd>Esc</kbd></div></section></div><details class="help-changelog"><summary>Phiên bản v2.14 · Có gì mới</summary><ul><li>Nút Bộ lọc riêng cho loại media và thư mục.</li><li>Cấu hình độ sâu thư mục để lọc theo các nhánh con.</li><li>Tùy chọn hình thu nhỏ video, mặc định tắt.</li></ul></details><div class="help-format"><h3>Định dạng media</h3><p>Ảnh: JPG/JPEG, PNG/APNG, WEBP, AVIF, BMP, SVG, JXL, HEIC/HEIF. GIF có bộ lọc riêng. Video: MP4, WEBM, MOV, M4V, OGV; khả năng phát tùy codec trình duyệt.</p></div></div></section>
<section id="searchDialog" class="search-dialog" aria-modal="true" role="dialog" aria-labelledby="searchTitle"><div class="search-card"><div class="search-heading"><h2 id="searchTitle">Tìm và nhảy tới bài</h2><button type="button" id="searchClose" class="search-close" aria-label="Đóng tìm kiếm">×</button></div><input id="searchQuery" type="search" maxlength="180" autocomplete="off" placeholder="Số bài, tên file hoặc nội dung ghi chú…"><div id="searchCount" class="search-count" aria-live="polite"></div><div id="searchResults" class="search-results"></div></div></section>
<script>
'use strict';
const POSTS=__POSTS__, BASE=__BASE__, FINGERPRINT=__FINGERPRINT__, ARCHIVE_TITLE=__ARCHIVE_TITLE_JSON__, THEMES=__THEMES__, DEFAULT_THEME=__DEFAULT_THEME__, AUTO_THEMES=__AUTO_THEMES__, SHOW_FILENAME=__SHOW_FILENAME__, SHOW_CREATED_TIME=__SHOW_CREATED_TIME__, SHOW_FILE_SIZE=__SHOW_FILE_SIZE__, SHOW_VIDEO_THUMBNAILS=__SHOW_VIDEO_THUMBNAILS__, STORE={likes:`tumblr_archive_${FINGERPRINT}_liked_posts_v2`,position:`tumblr_archive_${FINGERPRINT}_position_v2`,theme:`tumblr_archive_${FINGERPRINT}_theme_v2`,grid:`tumblr_archive_${FINGERPRINT}_grid_v1`,style:`tumblr_archive_${FINGERPRINT}_style_v1`};
const FOLDER_PATHS=[...new Set(POSTS.map(post=>post.folderPath).filter(Boolean))], selectedFolderPaths=new Set(FOLDER_PATHS);
const feed=document.getElementById('feed'), toastEl=document.getElementById('toast'), siteHeader=document.getElementById('siteHeader');
function updateStickyOffset(){document.documentElement.style.setProperty('--header-sticky-offset',`${siteHeader.getBoundingClientRect().height}px`)}updateStickyOffset();if('ResizeObserver'in window)new ResizeObserver(updateStickyOffset).observe(siteHeader);window.addEventListener('resize',updateStickyOffset,{passive:true});let headerScrollTick=false;function updateCompactHeader(){headerScrollTick=false;if(!document.body.classList.contains('header-not-sticky'))siteHeader.classList.toggle('compact',window.scrollY>40)}window.addEventListener('scroll',()=>{if(!headerScrollTick){headerScrollTick=true;requestAnimationFrame(updateCompactHeader)}},{passive:true});updateCompactHeader();
const allImages=[];let liked=new Set(readJSON(STORE.likes,[]).filter(x=>typeof x==='string')), onlyLiked=false, mediaTypeFilters=new Set(['image','gif','video']), focusPost=0, likedReturnPosition=null, lbIndex=0, lightboxImages=[], toastTimer, restoreLock=false;
function readJSON(key,fallback){try{const v=localStorage.getItem(key);return v?JSON.parse(v):fallback}catch{return fallback}}
function save(key,value){try{localStorage.setItem(key,JSON.stringify(value));return true}catch{showToast('Không lưu được dữ liệu trình duyệt');return false}}
function formatFileSize(bytes){if(!Number.isFinite(bytes)||bytes<0)return 'Không rõ';if(bytes<1024)return `${bytes} B`;const units=['KB','MB','GB','TB'];let value=bytes/1024,index=0;while(value>=1024&&index<units.length-1){value/=1024;index++}return `${new Intl.NumberFormat('vi-VN',{maximumFractionDigits:1}).format(value)} ${units[index]}`}
function resolvedTheme(choice){return choice==='auto'?AUTO_THEMES[matchMedia('(prefers-color-scheme: light)').matches?'light':'dark']:choice}
function applyTheme(choice,persist=true){if(choice!=='auto'&&!THEMES[choice])choice=DEFAULT_THEME;themeChoice=choice;const theme=THEMES[resolvedTheme(choice)];for(const [key,value] of Object.entries(theme)){if(key==='scheme')document.documentElement.style.colorScheme=value;else document.documentElement.style.setProperty(`--${key}`,value)}const selector=document.getElementById('themeSelect');if(selector)selector.value=choice;if(persist)save(STORE.theme,choice)}
let themeChoice=readJSON(STORE.theme,DEFAULT_THEME);if(themeChoice!=='auto'&&!THEMES[themeChoice])themeChoice=DEFAULT_THEME;applyTheme(themeChoice,false);const systemThemeQuery=matchMedia('(prefers-color-scheme: light)');systemThemeQuery.addEventListener?.('change',()=>{if(themeChoice==='auto')applyTheme('auto',false)});
function showToast(message){toastEl.textContent=message;toastEl.classList.add('show');clearTimeout(toastTimer);toastTimer=setTimeout(()=>toastEl.classList.remove('show'),2300)}
function safeUrl(name){return BASE+name.split('/').map(encodeURIComponent).join('/')}let mediaSequence=0;POSTS.forEach((post,postIndex)=>post.images.forEach((name,mediaIndex)=>{const info=post.mediaInfo?.[mediaIndex]||{filename:name,created:''},isVideo=/\.(mp4|webm|mov|m4v|ogv)$/i.test(name),isGif=/\.gif$/i.test(name);allImages.push({url:safeUrl(name),postId:post.id,postIndex,imageIndex:mediaSequence++,isVideo,kind:isVideo?'video':isGif?'gif':'image',filename:info.filename,created:info.created,folderPath:post.folderPath})}));
function escapeId(s){return s}
function syncMediaFilterButtons(){document.querySelectorAll('.media-filter-check').forEach(input=>{input.checked=mediaTypeFilters.has(input.dataset.kind)});document.getElementById('filterAll').checked=mediaTypeFilters.size===3;const all=document.getElementById('folderFilterAll');if(all)all.checked=FOLDER_PATHS.length>0&&selectedFolderPaths.size===FOLDER_PATHS.length;document.querySelectorAll('.folder-path-filter').forEach(input=>{input.checked=selectedFolderPaths.has(input.dataset.folderPath)})}
function mountFolderPathFilters(){const section=document.getElementById('folderFilterSection');if(FOLDER_PATHS.length<2)return;section.hidden=false;const list=document.getElementById('folderFilterList');for(const folder of FOLDER_PATHS){const label=document.createElement('label');label.className='filter-check';const input=document.createElement('input');input.type='checkbox';input.className='folder-path-filter';input.dataset.folderPath=folder;input.checked=true;const text=document.createElement('span');text.textContent=folder;label.append(input,text);list.append(label);input.addEventListener('change',()=>{if(input.checked)selectedFolderPaths.add(folder);else selectedFolderPaths.delete(folder);syncLikes()})}document.getElementById('folderFilterAll').addEventListener('change',event=>{selectedFolderPaths.clear();if(event.target.checked)FOLDER_PATHS.forEach(folder=>selectedFolderPaths.add(folder));syncLikes()})}
const MEDIA_ICON_SVG={image:'<svg viewBox="0 0 20 20" aria-hidden="true"><rect x="2.5" y="3" width="15" height="14" rx="3"/><circle cx="7" cy="8" r="1.4"/><path d="m4 15 4-4 2.4 2.2 2.1-2 3.5 3.8"/></svg>',gif:'<svg viewBox="0 0 20 20" aria-hidden="true"><rect x="1.5" y="3.5" width="17" height="13" rx="3"/><path d="M8 8.2a2.6 2.6 0 1 0 .1 3.6H8v-1.6h1.8"/><path d="M12 8v5m2-5h3m-3 0v5"/></svg>',video:'<svg viewBox="0 0 20 20" aria-hidden="true"><rect x="2" y="4" width="16" height="12" rx="3"/><path d="m8 7 5 3-5 3z"/></svg>',stack:'<svg viewBox="0 0 20 20" aria-hidden="true"><rect x="5" y="2.5" width="12" height="12" rx="2.5"/><path d="M3 6v10.5A1.5 1.5 0 0 0 4.5 18H15"/></svg>'};function mediaBadgeHTML(count,kinds,total=count){const unique=[...new Set(kinds)],kind=count===1?(unique[0]||'image'):unique.length===1?unique[0]:'stack',icon=MEDIA_ICON_SVG[kind]||MEDIA_ICON_SVG.stack;const label=count===1?(kind==='video'?'Video':kind==='gif'?'GIF':'Ảnh'):count===total?`${count} media`:`${count}/${total}`;return `${icon}<span>${label}</span>`}function stackBadgeHTML(amount){return `${MEDIA_ICON_SVG.stack}<span>+${amount}</span>`}
function syncLikes(){syncMediaFilterButtons();document.getElementById('likeCount').textContent=liked.size;document.querySelectorAll('.post').forEach(el=>{const b=el.querySelector('.post-like');if(b){const on=liked.has(el.dataset.postid);b.textContent='♥';b.classList.toggle('is-liked',on);b.setAttribute('aria-pressed',String(on));el.classList.toggle('is-liked-post',on)}const locate=el.querySelector('.return-archive-btn');if(locate)locate.classList.toggle('visible',onlyLiked);const post=POSTS[Number(el.dataset.index)],folderMatches=!post?.folderPath||selectedFolderPaths.has(post.folderPath),items=[...el.querySelectorAll('.media-item')];let shown=0;items.forEach(item=>{const match=mediaTypeFilters.has(item.dataset.kind);item.hidden=!match;if(match)shown++});const badge=el.querySelector('.post-count');if(badge){const filterNames=[...mediaTypeFilters].map(k=>k==='image'?'ảnh':k==='gif'?'GIF':'video').join(', ');badge.innerHTML=mediaBadgeHTML(shown,items.filter(item=>!item.hidden).map(item=>item.dataset.kind),items.length)}el.classList.toggle('hidden',(onlyLiked&&!liked.has(el.dataset.postid))||!folderMatches||shown===0)});document.getElementById('filterBtn').classList.toggle('active',onlyLiked);syncGridMedia()}
function syncGridMedia(){document.querySelectorAll('.post').forEach(card=>{const items=[...card.querySelectorAll('.media-item')],primary=items.find(item=>!item.hidden);items.forEach(item=>item.classList.toggle('grid-primary',item===primary));const badge=primary?.querySelector('.grid-media-badge');if(badge)badge.innerHTML=stackBadgeHTML(Math.max(0,items.length-1))})}
mountFolderPathFilters();
function toggleLike(id){if(liked.has(id))liked.delete(id);else liked.add(id);save(STORE.likes,[...liked]);syncLikes();if(lightbox.classList.contains('active')&&lightboxImages[lbIndex]){const b=document.getElementById('lbLike'),on=liked.has(lightboxImages[lbIndex].postId);b.textContent='♥';b.classList.toggle('is-liked',on);b.setAttribute('aria-pressed',String(on))}}
const imageLoadObserver='IntersectionObserver'in window?new IntersectionObserver(entries=>{for(const entry of entries){if(!entry.isIntersecting)continue;const image=entry.target;imageLoadObserver.unobserve(image);if(image.dataset.src){image.src=image.dataset.src;delete image.dataset.src}}},{rootMargin:'1500px 0px 1800px'}):null;let renderCursor=0,globalMediaNo=0,positionObserver=null,feedLoader=null;const RENDER_BATCH_SIZE=36;function makeArchive(deferSync=false){const end=Math.min(POSTS.length,renderCursor+RENDER_BATCH_SIZE);for(let index=renderCursor;index<end;index++){const post=POSTS[index];const isMulti=post.images.length>1;const card=document.createElement('article');card.className=isMulti?'post multi-media':'post';card.dataset.index=index;card.dataset.postid=post.id;card.id='post-'+index;const heading=document.createElement('div');heading.className='post-heading';const title=document.createElement('span');title.className='post-title';title.textContent=`#${index+1}`;const count=document.createElement('span');count.className='post-count';count.innerHTML=mediaBadgeHTML(post.images.length,post.images.map(name=>/\.(mp4|webm|mov|m4v|ogv)$/i.test(name)?'video':/\.gif$/i.test(name)?'gif':'image'),post.images.length);heading.append(title,count);const images=document.createElement('div');images.className='post-images';post.images.forEach((name,postMediaIndex)=>{const globalIndex=globalMediaNo++,url=safeUrl(name),isVideo=/\.(mp4|webm|mov|m4v|ogv)$/i.test(name),isGif=/\.gif$/i.test(name),kind=isVideo?'video':isGif?'gif':'image',item=document.createElement('div');item.className='media-item';item.dataset.kind=kind;if(isMulti){const number=document.createElement('span');number.className='media-number';number.textContent=`${postMediaIndex+1}/${post.images.length}`;item.append(number);const gridBadge=document.createElement('span');gridBadge.className='grid-media-badge';gridBadge.innerHTML=stackBadgeHTML(post.images.length-1);item.append(gridBadge)}if(isVideo){const wrap=document.createElement('div');wrap.className='video-wrap';const video=document.createElement('video');video.controls=true;video.playsInline=true;video.preload=SHOW_VIDEO_THUMBNAILS?'metadata':'none';video.src=SHOW_VIDEO_THUMBNAILS?`${url}#t=0.1`:url;video.setAttribute('aria-label',`Video ${index+1}`);video.addEventListener('error',()=>showToast(`Không phát được video: ${name}`),{once:true});const open=document.createElement('button');open.type='button';open.className='media-open';open.textContent='Phóng to ⛶';open.setAttribute('aria-label','Mở video trong lightbox');open.addEventListener('click',()=>openLightbox(globalIndex));wrap.append(video,open);item.append(wrap)}else{const img=document.createElement('img');img.loading='lazy';img.decoding='async';img.fetchPriority=globalIndex===0?'high':'low';img.alt=`Ảnh ${index+1}, media ${postMediaIndex+1}`;if(globalIndex===0){img.loading='eager';img.src=url}else if(imageLoadObserver){img.dataset.src=url;imageLoadObserver.observe(img)}else{img.src=url}img.addEventListener('error',()=>{img.alt=`Không tải được: ${name}`},{once:true});img.addEventListener('click',()=>openLightbox(globalIndex));item.append(img)}images.append(item);const meta=post.mediaInfo?.[postMediaIndex]||{filename:name,created:'Ngày không rõ'};if(SHOW_FILENAME||SHOW_CREATED_TIME||SHOW_FILE_SIZE){const mediaMeta=document.createElement('div');mediaMeta.className='media-meta';const details=[SHOW_CREATED_TIME?meta.created:'',SHOW_FILENAME?meta.filename:'',SHOW_FILE_SIZE?`Dung lượng: ${formatFileSize(meta.size)}`:''];mediaMeta.replaceChildren(...details.filter(Boolean).map(t=>{const d=document.createElement('div');d.textContent=t;return d}));item.append(mediaMeta)}const noteHtml=post.notes?.[postMediaIndex];if(noteHtml){const note=document.createElement('div');note.className='media-note';note.innerHTML=noteHtml;item.append(note)}});const footer=document.createElement('footer');footer.className='post-footer';if(post.sourceFolder){const source=document.createElement('span');source.className='post-source-folder';source.innerHTML='<svg viewBox="0 0 20 20" aria-hidden="true"><path d="M2.5 5.5A1.5 1.5 0 0 1 4 4h4l2 2h6A1.5 1.5 0 0 1 17.5 7.5v7A1.5 1.5 0 0 1 16 16H4a1.5 1.5 0 0 1-1.5-1.5z"/><path d="M2.5 8h15"/></svg>';const sourceName=document.createElement('span');sourceName.textContent=post.sourceFolder;source.append(sourceName);source.title=`Thư mục: ${post.sourceFolder}`;footer.append(source)}const actions=document.createElement('div');actions.className='post-actions';const locate=document.createElement('button');locate.type='button';locate.className='return-archive-btn';locate.textContent='Về vị trí gốc ↗';locate.setAttribute('aria-label','Mở bài này tại vị trí trong archive đầy đủ');locate.addEventListener('click',()=>goToArchivePost(post.id,index));const like=document.createElement('button');like.type='button';like.className='like post-like';like.setAttribute('aria-label','Thích bài viết');like.addEventListener('click',()=>toggleLike(post.id));actions.append(locate,like);footer.append(actions);card.append(heading,images,footer);feed.append(card);if(positionObserver)positionObserver.observe(card)}renderCursor=end;document.title=`${ARCHIVE_TITLE} (${POSTS.length} bài)`;document.getElementById('summary').textContent=`${POSTS.length} bài · ${allImages.length} media`;document.getElementById('empty').hidden=POSTS.length>0;if(renderCursor>=POSTS.length){feedLoader?.disconnect();document.getElementById('loadSentinel').hidden=true}if(!deferSync)syncLikes()}function ensureRenderedThrough(index){let changed=false;while(renderCursor<=index&&renderCursor<POSTS.length){makeArchive(true);changed=true}if(changed)syncLikes()}function ensureAllRendered(done){function step(){if(renderCursor>=POSTS.length){syncLikes();done?.();return}makeArchive(true);syncLikes();requestAnimationFrame(step)}step()}function ensureRenderedAsync(index,done){if(renderCursor>index||renderCursor>=POSTS.length){syncLikes();done();return}makeArchive(true);requestAnimationFrame(()=>ensureRenderedAsync(index,done))}
makeArchive();
let gridView=readJSON(STORE.grid,false);const gridToggle=document.getElementById('gridView');feed.classList.toggle('grid-view',gridView);gridToggle.checked=gridView;gridToggle.addEventListener('change',()=>{gridView=gridToggle.checked;feed.classList.toggle('grid-view',gridView);save(STORE.grid,gridView)});function setGridView(value){gridView=Boolean(value);gridToggle.checked=gridView;feed.classList.toggle('grid-view',gridView);save(STORE.grid,gridView)}document.getElementById('headerSearch').onclick=()=>document.getElementById('jumpBtn').click();document.getElementById('headerLayout').onclick=()=>setGridView(!gridView);document.getElementById('headerBackup').onclick=()=>document.getElementById('exportBtn').click();
const searchDialog=document.getElementById('searchDialog'),searchQuery=document.getElementById('searchQuery'),searchResults=document.getElementById('searchResults'),searchCount=document.getElementById('searchCount');function syncSearchViewport(){const viewport=window.visualViewport;if(!viewport)return;document.documentElement.style.setProperty('--search-vv-height',`${viewport.height}px`);document.documentElement.style.setProperty('--search-vv-top',`${viewport.offsetTop}px`)}syncSearchViewport();window.visualViewport?.addEventListener('resize',syncSearchViewport,{passive:true});window.visualViewport?.addEventListener('scroll',syncSearchViewport,{passive:true});
function noteText(post){return (post.notes||[]).map(html=>{const box=document.createElement('template');box.innerHTML=html;return box.content.textContent||''}).join(' ')}
function renderSearchResults(){const raw=searchQuery.value.trim().toLocaleLowerCase();const query=raw.replace(/^#/, '');let hits;if(/^\d+$/.test(query)){const postNumber=Number(query);hits=Number.isSafeInteger(postNumber)&&postNumber>=1&&postNumber<=POSTS.length?[{post:POSTS[postNumber-1],index:postNumber-1}]:[]}else{hits=POSTS.map((post,index)=>({post,index})).filter(({post,index})=>{if(!query)return index<40;const filenames=(post.mediaInfo||[]).map(info=>info.filename||'').join(' ');const haystack=[String(index+1),post.id,filenames,noteText(post)].join(' ').toLocaleLowerCase();return haystack.includes(query)})}const total=hits.length;hits=hits.slice(0,60);searchResults.replaceChildren();searchCount.textContent=raw?`${total} bài phù hợp${total>hits.length?` · đang hiện ${hits.length} bài`:''}`:`${POSTS.length} bài · nhập số thứ tự, tên file hoặc từ khóa để lọc`;if(!hits.length){const empty=document.createElement('div');empty.className='search-empty';empty.textContent='Không tìm thấy bài phù hợp.';searchResults.append(empty);return}const fragment=document.createDocumentFragment();for(const {post,index} of hits){const button=document.createElement('button');button.type='button';button.className='search-result';const info=(post.mediaInfo||[])[0]||{filename:post.images[0]||''};const isVideo=/\.(mp4|webm|mov|m4v|ogv)$/i.test(info.filename);if(isVideo){const thumb=document.createElement('span');thumb.className='search-video-thumb';thumb.textContent='▶';thumb.setAttribute('aria-hidden','true');button.append(thumb)}else{const thumb=document.createElement('img');thumb.className='search-thumb';thumb.loading='lazy';thumb.alt='';thumb.src=safeUrl(post.images[0]);thumb.addEventListener('error',()=>{const fallback=document.createElement('span');fallback.className='search-video-thumb';fallback.textContent='▧';thumb.replaceWith(fallback)},{once:true});button.append(thumb)}const text=document.createElement('span');text.className='search-result-text';const title=document.createElement('span');title.className='search-result-title';title.textContent=`Bài ${index+1} · ${post.images.length} media`;const detail=document.createElement('span');detail.className='search-result-detail';const filenames=(post.mediaInfo||[]).slice(0,2).map(x=>x.filename).filter(Boolean).join(' · ');const note=noteText(post).trim().replace(/\s+/g,' ');detail.textContent=filenames||(note.slice(0,100))||post.id;text.append(title,detail);button.append(text);button.addEventListener('click',()=>{closeSearchDialog();if(onlyLiked){onlyLiked=false;likedReturnPosition=null;syncLikes()}returnToPost(post.id,index);showToast(`Đã mở bài ${index+1}`)});fragment.append(button)}searchResults.append(fragment)}
function openSearchDialog(value=''){closeSettings();searchDialog.classList.add('active');searchQuery.value=value;renderSearchResults();requestAnimationFrame(()=>{syncSearchViewport();searchQuery.focus();searchQuery.select();setTimeout(syncSearchViewport,80)})}
function closeSearchDialog(){searchDialog.classList.remove('active');document.getElementById('jumpBtn').focus()}
searchQuery.addEventListener('input',renderSearchResults);searchQuery.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();const first=searchResults.querySelector('.search-result');if(first)first.click()}});document.getElementById('searchClose').onclick=closeSearchDialog;searchDialog.addEventListener('click',e=>{if(e.target===searchDialog)closeSearchDialog()});
const lightbox=document.getElementById('lightbox'), lbImg=document.getElementById('lbImg'), lbVideo=document.getElementById('lbVideo');
function openLightbox(index){const selected=allImages[index],folderMatches=item=>!item.folderPath||selectedFolderPaths.has(item.folderPath);if(!selected||!mediaTypeFilters.has(selected.kind)||!folderMatches(selected))return;lightboxImages=allImages.filter(item=>mediaTypeFilters.has(item.kind)&&folderMatches(item));lbIndex=lightboxImages.indexOf(selected);if(lbIndex<0)return;lightbox.classList.add('active');document.body.style.overflow='hidden';updateLightbox();document.getElementById('lbClose').focus()}
function closeLightbox(){lightbox.classList.remove('active');lbVideo.pause();document.body.style.overflow='';const item=lightboxImages[lbIndex];if(item){const card=document.querySelector(`.post[data-postid="${CSS.escape(item.postId)}"]`);card?.scrollIntoView({block:'center',behavior:'instant'})}}
function updateLightbox(){const item=lightboxImages[lbIndex];if(!item)return;lbVideo.pause();if(item.isVideo){lbImg.hidden=true;lbVideo.hidden=false;if(lbVideo.src!==new URL(item.url,document.baseURI).href){lbVideo.src=item.url;lbVideo.load()}}else{lbVideo.hidden=true;lbImg.hidden=false;lbImg.onload=()=>lbImg.classList.remove('loading');lbImg.onerror=()=>{lbImg.classList.remove('loading');showToast('Không tải được ảnh')};lbImg.classList.add('loading');lbImg.src=item.url}document.getElementById('lbCounter').textContent=`Bài ${item.postIndex+1}/${POSTS.length} · ${lbIndex+1}/${lightboxImages.length}`;(()=>{const b=document.getElementById('lbLike'),on=liked.has(item.postId);b.textContent='♥';b.classList.toggle('is-liked',on);b.setAttribute('aria-pressed',String(on))})()}
function moveImage(n){if(!lightboxImages.length)return;lbIndex=(lbIndex+n+lightboxImages.length)%lightboxImages.length;updateLightbox()}
document.getElementById('lbNext').onclick=()=>moveImage(1);document.getElementById('lbPrev').onclick=()=>moveImage(-1);document.getElementById('lbClose').onclick=closeLightbox;lightbox.addEventListener('click',e=>{if(e.target===lightbox)closeLightbox()});document.getElementById('lbLike').onclick=()=>{const i=lightboxImages[lbIndex];if(i)toggleLike(i.postId)};
let touchX=0,touchY=0;lightbox.addEventListener('touchstart',e=>{touchX=e.changedTouches[0].clientX;touchY=e.changedTouches[0].clientY},{passive:true});lightbox.addEventListener('touchend',e=>{const dx=e.changedTouches[0].clientX-touchX,dy=e.changedTouches[0].clientY-touchY;if(Math.abs(dx)>55&&Math.abs(dx)>Math.abs(dy)*1.25)moveImage(dx<0?1:-1)},{passive:true});
const help=document.getElementById('help');function toggleHelp(){closeSettings();help.classList.toggle('active')}document.getElementById('helpBtn').onclick=toggleHelp;document.getElementById('helpClose').onclick=toggleHelp;help.addEventListener('click',e=>{if(e.target===help)toggleHelp()});
function visibleCards(){return [...document.querySelectorAll('.post:not(.hidden)')]}
function navigatePost(dir){let cards=visibleCards();if(!cards.length)return;let i=cards.findIndex(x=>Number(x.dataset.index)===focusPost);if(i<0)i=0;if(dir>0&&i===cards.length-1&&renderCursor<POSTS.length){makeArchive();cards=visibleCards()}const target=cards[Math.max(0,Math.min(cards.length-1,i+dir))];focusPost=Number(target.dataset.index);target.scrollIntoView({block:'center',behavior:'smooth'});savePosition(target)}
function savePosition(card){if(!card||onlyLiked||restoreLock)return;save(STORE.position,{id:card.dataset.postid,index:Number(card.dataset.index),top:Math.round(card.getBoundingClientRect().top),savedAt:Date.now()})}
let saveTimer;positionObserver=new IntersectionObserver(entries=>{const best=entries.filter(e=>e.isIntersecting).sort((a,b)=>b.intersectionRatio-a.intersectionRatio)[0];if(!best)return;const card=best.target;focusPost=Number(card.dataset.index);clearTimeout(saveTimer);saveTimer=setTimeout(()=>savePosition(card),180)},{threshold:[0,.25,.5,.75,1]});document.querySelectorAll('.post').forEach(p=>positionObserver.observe(p));function fillFeedNearViewport(){if(renderCursor>=POSTS.length)return;const sentinel=document.getElementById('loadSentinel');if(sentinel.getBoundingClientRect().top<window.innerHeight+1500){makeArchive();requestAnimationFrame(fillFeedNearViewport)}}feedLoader=new IntersectionObserver(entries=>{if(entries.some(entry=>entry.isIntersecting))fillFeedNearViewport()},{rootMargin:'1500px 0px'});feedLoader.observe(document.getElementById('loadSentinel'));
function returnToPost(id,index,behavior='instant'){const wanted=Number.isInteger(index)?index:POSTS.findIndex(p=>p.id===id);if(wanted>=0)ensureRenderedThrough(wanted);const indexedMatch=Number.isInteger(index)&&index>=0&&index<POSTS.length&&POSTS[index]?.id===id;const found=indexedMatch?index:POSTS.findIndex(p=>p.id===id);const targetIndex=found>=0?found:index;let card=document.querySelector(`.post[data-index="${targetIndex}"]`);if(card?.classList.contains('hidden')){mediaTypeFilters=new Set(['image','gif','video']);selectedFolderPaths.clear();FOLDER_PATHS.forEach(folder=>selectedFolderPaths.add(folder));syncLikes()}card=document.querySelector(`.post[data-index="${targetIndex}"]`);if(card){focusPost=targetIndex;card.scrollIntoView({block:'start',behavior});requestAnimationFrame(()=>{if(card.isConnected)card.scrollIntoView({block:'start',behavior:'instant'})});setTimeout(()=>{if(card.isConnected){card.scrollIntoView({block:'start',behavior:'instant'});savePosition(card)}},120)}return card}
function goToArchivePost(id,index){if(onlyLiked){onlyLiked=false;likedReturnPosition=null;syncLikes()}returnToPost(id,index);showToast('Đã mở bài tại vị trí trong archive')}
function toggleFilter(){if(!onlyLiked){const card=document.querySelector(`.post[data-index="${focusPost}"]`);likedReturnPosition=card?{id:card.dataset.postid,index:focusPost}:null;onlyLiked=true;ensureAllRendered(()=>{const first=visibleCards()[0];if(first)first.scrollIntoView({block:'start',behavior:'smooth'})})}else{onlyLiked=false;syncLikes();const saved=likedReturnPosition;likedReturnPosition=null;if(saved)returnToPost(saved.id,saved.index);else window.scrollTo({top:0,behavior:'smooth'})}}
document.getElementById('filterBtn').onclick=toggleFilter;document.getElementById('jumpBtn').onclick=()=>openSearchDialog();document.getElementById('topBtn').onclick=()=>window.scrollTo({top:0,behavior:'smooth'});document.getElementById('filterAll').addEventListener('change',e=>{mediaTypeFilters=e.target.checked?new Set(['image','gif','video']):new Set();syncLikes()});document.querySelectorAll('.media-filter-check').forEach(input=>input.addEventListener('change',()=>{if(input.checked)mediaTypeFilters.add(input.dataset.kind);else mediaTypeFilters.delete(input.dataset.kind);syncLikes()}));
const controls=document.getElementById('controls'),settingsMenu=document.getElementById('settingsMenu'),settingsBtn=document.getElementById('settingsBtn'),filterControl=document.getElementById('filterControl'),filterPopover=document.getElementById('filterPopover'),filterMenuToggle=document.getElementById('filterMenuToggle');function closeFilterPopover(){filterPopover.classList.remove('open');filterMenuToggle.setAttribute('aria-expanded','false')}filterMenuToggle.onclick=event=>{event.stopPropagation();const open=filterPopover.classList.toggle('open');filterMenuToggle.setAttribute('aria-expanded',String(open));closeSettings()};let visualStyle=readJSON(STORE.style,'modern');function applyVisualStyle(value){visualStyle=value==='classic'?'classic':'modern';document.body.classList.toggle('style-classic',visualStyle==='classic');document.body.classList.toggle('style-modern',visualStyle==='modern');const styleButton=document.getElementById('styleToggleBtn');document.getElementById('styleToggleLabel').textContent=visualStyle==='modern'?'Hiện đại':'Cổ điển';styleButton.setAttribute('aria-label',`Phong cách hiện tại: ${visualStyle==='modern'?'Hiện đại':'Cổ điển'}`);save(STORE.style,visualStyle)}applyVisualStyle(visualStyle);document.getElementById('styleToggleBtn').onclick=()=>applyVisualStyle(visualStyle==='modern'?'classic':'modern');function openThemeSettings(){if(!settingsMenu.classList.contains('open')){settingsMenu.classList.add('open');settingsBtn.setAttribute('aria-expanded','true')}document.getElementById('themeSelect').focus()}document.getElementById('headerTheme').onclick=e=>{e.stopPropagation();openThemeSettings()};document.getElementById('themeSelect').addEventListener('change',e=>applyTheme(e.target.value));function closeSettings(){settingsMenu.classList.remove('open');settingsBtn.setAttribute('aria-expanded','false')}settingsBtn.onclick=()=>{closeFilterPopover();const open=settingsMenu.classList.toggle('open');settingsBtn.setAttribute('aria-expanded',String(open))};document.getElementById('collapseBtn').onclick=()=>{const collapsed=controls.classList.toggle('collapsed');const button=document.getElementById('collapseBtn');button.textContent=collapsed?'＋':'−';button.title=collapsed?'Mở rộng toolbar':'Thu gọn toolbar';button.setAttribute('aria-label',button.title);closeSettings();closeFilterPopover()};document.addEventListener('click',e=>{if(!controls.contains(e.target))closeSettings();if(!filterControl.contains(e.target))closeFilterPopover()});
function jump(){openSearchDialog()}
function encodeBase64(text){const bytes=new TextEncoder().encode(text);let binary='';for(let i=0;i<bytes.length;i+=0x8000)binary+=String.fromCharCode(...bytes.subarray(i,i+0x8000));return btoa(binary)}
function decodeBase64(value){const binary=atob(value.replace(/\s+/g,''));const bytes=Uint8Array.from(binary,ch=>ch.charCodeAt(0));return new TextDecoder().decode(bytes)}
function importBackup(){const encoded=prompt('Dán chuỗi backup Base64 vào đây:');if(!encoded)return;try{if(encoded.length>8_000_000)throw Error('too-large');const data=JSON.parse(decodeBase64(encoded));if(!data||data.format!=='tumblr-archive-backup'||!Array.isArray(data.likedPosts)||data.likedPosts.some(x=>typeof x!=='string'))throw Error('invalid');liked=new Set(data.likedPosts.filter(id=>POSTS.some(p=>p.id===id)));save(STORE.likes,[...liked]);syncLikes();let pos=data.position;if(!pos&&data.lastPostId)pos={id:data.lastPostId,index:Number(data.lastPostIdx)-1};if(pos){const byId=POSTS.findIndex(p=>p.id===pos.id);const index=byId>=0?byId:Number(pos.index);if(Number.isInteger(index)&&index>=0&&index<POSTS.length){ensureRenderedThrough(index);const target=document.querySelector(`.post[data-index="${index}"]`);if(target){onlyLiked=false;syncLikes();target.scrollIntoView({block:'center',behavior:'instant'});focusPost=index;savePosition(target)}}}showToast('Đã nhập backup')}catch(err){showToast(err.message==='too-large'?'Chuỗi backup quá dài':'Chuỗi backup không hợp lệ')}}
async function exportBackup(){const data={format:'tumblr-archive-backup',version:3,archiveFingerprint:FINGERPRINT,likedPosts:[...liked],position:readJSON(STORE.position,null),exportedAt:new Date().toISOString()};const encoded=encodeBase64(JSON.stringify(data));try{if(!navigator.clipboard?.writeText)throw Error('clipboard unavailable');await navigator.clipboard.writeText(encoded);showToast('Đã copy chuỗi backup vào clipboard')}catch{prompt('Clipboard bị chặn. Hãy copy chuỗi backup này:',encoded)}}
document.getElementById('exportBtn').onclick=()=>{closeSettings();exportBackup()};document.getElementById('importBtn').onclick=()=>{closeSettings();importBackup()};
function restorePosition(){const pos=readJSON(STORE.position,null);if(!pos)return;let idx=POSTS.findIndex(p=>p.id===pos.id);if(idx<0&&Number.isInteger(Number(pos.index)))idx=Math.max(0,Math.min(POSTS.length-1,Number(pos.index)));if(idx<0)return;restoreLock=true;ensureRenderedAsync(idx,()=>{const card=document.querySelector(`.post[data-index="${idx}"]`);card?.scrollIntoView({block:'start',behavior:'instant'});focusPost=idx;setTimeout(()=>{restoreLock=false;showToast(`Đã khôi phục vị trí bài ${idx+1}`)},250)})}
window.addEventListener('load',()=>setTimeout(restorePosition,80));
document.addEventListener('keydown',e=>{if(e.ctrlKey||e.metaKey||e.altKey)return;if(searchDialog.classList.contains('active')&&e.key==='Escape'){closeSearchDialog();return}const tag=document.activeElement?.tagName;if(['INPUT','TEXTAREA','SELECT','VIDEO','AUDIO'].includes(tag)||document.activeElement?.isContentEditable)return;if(lightbox.classList.contains('active')){if(e.code==='Space'){e.preventDefault();moveImage(e.shiftKey?-1:1)}else if(['ArrowRight','j','J'].includes(e.key)){e.preventDefault();moveImage(1)}else if(['ArrowLeft','k','K'].includes(e.key)){e.preventDefault();moveImage(-1)}else if(e.key==='Escape')closeLightbox();else if(e.key==='l'||e.key==='L')document.getElementById('lbLike').click();return}if(help.classList.contains('active')){if(e.key==='Escape'||e.key==='?'||e.key==='h'||e.key==='H')toggleHelp();return}if(e.key==='Escape'&&filterPopover.classList.contains('open')){closeFilterPopover();return}if(e.key==='Escape'&&settingsMenu.classList.contains('open')){closeSettings();return}if(e.code==='Space'){e.preventDefault();navigatePost(e.shiftKey?-1:1)}else if(['j','J','ArrowDown'].includes(e.key)){e.preventDefault();navigatePost(1)}else if(['k','K','ArrowUp'].includes(e.key)){e.preventDefault();navigatePost(-1)}else if(e.key==='l'||e.key==='L'){const p=POSTS[focusPost];if(p)toggleLike(p.id)}else if(e.key==='f'||e.key==='F')toggleFilter();else if(e.key==='g'||e.key==='G')jump();else if(e.key==='v'||e.key==='V')setGridView(!gridView);else if(e.key==='m'||e.key==='M')openThemeSettings();else if(e.key==='e'||e.key==='E')exportBackup();else if(e.key==='i'||e.key==='I')importBackup();else if(e.key==='t'||e.key==='T')window.scrollTo({top:0,behavior:'smooth'});else if(e.key==='?'||e.key==='h'||e.key==='H')toggleHelp()});
</script></body></html>'''


def generate_html(images_dirs: list[Path], output: Path, archive_title: str, theme_name: str, theme_light: str, theme_dark: str, sort_by: str, sticky_header: bool, show_filename: bool, show_created_time: bool, show_file_size: bool, show_video_thumbnails: bool, folder_filter_depth: int, script_dir: Path) -> int:
    if not images_dirs:
        raise FileNotFoundError("Chưa cấu hình thư mục media nào.")
    for folder in images_dirs:
        if not folder.is_dir():
            raise FileNotFoundError(f"Không tìm thấy thư mục media: {folder}")
    entries = []
    folder_name_counts: dict[str, int] = {}
    for folder in images_dirs:
        folder_name_counts[folder.name.casefold()] = folder_name_counts.get(folder.name.casefold(), 0) + 1
    source_labels = {}
    for index, folder in enumerate(images_dirs):
        label = folder.name
        if folder_name_counts[label.casefold()] > 1:
            parent_name = folder.parent.name
            label = f"{parent_name}/{label}" if parent_name else f"{label} ({index + 1})"
        source_labels[folder] = label
    for folder in images_dirs:
        relative_folder = Path(os.path.relpath(folder.resolve(), output.parent.resolve())).as_posix()
        markdown_files = {p.relative_to(folder).with_suffix("").as_posix().casefold(): p for p in folder.rglob("*")
                          if p.is_file() and p.suffix.casefold() == ".md"
                          and all(not part.startswith(".") and part not in IGNORED_MEDIA_DIRS
                                  for part in p.relative_to(folder).parts)}
        used_markdown: set[Path] = set()
        for post in build_posts(folder):
            source_files = [folder / name for name in post["images"]]
            post_id = f"{relative_folder}::{post['id']}" if len(images_dirs) > 1 else post["id"]
            media_paths = [Path(os.path.relpath(path.resolve(), output.parent.resolve())).as_posix() for path in source_files]
            media_info = [{"filename": path.name,
                           "created": datetime.fromtimestamp(file_created_time(path)).strftime("%d/%m/%Y %H:%M"),
                           "size": path.stat().st_size}
                          for path in source_files]
            notes = []
            relative_media_parent = Path(post["images"][0]).parent
            folder_components = () if relative_media_parent.as_posix() == "." else relative_media_parent.parts
            folder_bucket = source_labels[folder]
            if folder_filter_depth > 0 and folder_components:
                folder_bucket += "/" + "/".join(folder_components[:folder_filter_depth])
            for media_name in post["images"]:
                note_path = markdown_sidecar(media_name, used_markdown, markdown_files)
                note_text = note_path.read_text(encoding="utf-8", errors="replace") if note_path else ""
                notes.append(markdown_to_html(note_text[:2_000_000]) if note_text else "")
            entries.append({
                "post": {"id": post_id, "images": media_paths, "notes": notes, "mediaInfo": media_info, "folderPath": folder_bucket, **({"sourceFolder": source_labels[folder]} if len(images_dirs) > 1 else {})},
                "sort_name": min(post["images"], key=natural_key),
                "sort_folder": relative_folder,
                "created": min(file_created_time(path) for path in source_files),
            })
    if sort_by == "name":
        entries.sort(key=lambda e: (natural_key(e["sort_name"]), natural_key(e["sort_folder"]), e["post"]["id"].casefold()))
    elif sort_by == "created":
        entries.sort(key=lambda e: (e["created"], natural_key(e["sort_name"]), natural_key(e["sort_folder"])))
    elif sort_by == "created_desc":
        entries.sort(key=lambda e: (e["created"], natural_key(e["sort_name"]), natural_key(e["sort_folder"])), reverse=True)
    posts = [entry["post"] for entry in entries]
    payload = json.dumps(posts, ensure_ascii=False, separators=(",", ":"))
    payload = payload.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    theme = THEMES[theme_dark if theme_name == "auto" else theme_name]
    auto_themes = {"light": theme_light, "dark": theme_dark}
    theme_vars = ";".join(f"--{key}:{value}" for key, value in theme.items() if key != "scheme")
    identity = "\0".join(str(folder.resolve()) for folder in images_dirs) + "\0" + "\0".join(name for post in posts for name in post["images"])
    fingerprint = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20]
    favicon = next((candidate for folder in [script_dir, *images_dirs]
                    for candidate in (folder / "fav.icon", folder / "favicon.ico", folder / "favicon.png", folder / "favicon.svg")
                    if candidate.is_file()), None)
    favicon_link = ""
    if favicon:
        mime = {".ico":"image/x-icon", ".icon":"image/x-icon", ".png":"image/png", ".svg":"image/svg+xml"}.get(favicon.suffix.casefold(), "application/octet-stream")
        encoded = base64.b64encode(favicon.read_bytes()).decode("ascii")
        favicon_link = f'<link rel="icon" href="data:{mime};base64,{encoded}">'
    html = (HTML.replace("__POSTS__", payload)
            .replace("__TOTAL_POSTS__", str(len(posts)))
            .replace("__BASE__", json.dumps(""))
            .replace("__FINGERPRINT__", json.dumps(fingerprint))
            .replace("__ARCHIVE_TITLE__", html_escape(archive_title))
            .replace("__ARCHIVE_TITLE_JSON__", json.dumps(archive_title, ensure_ascii=False))
            .replace("__THEME_VARS__", theme_vars)
            .replace("__THEMES__", json.dumps(THEMES, ensure_ascii=False, separators=(",", ":")))
            .replace("__DEFAULT_THEME__", json.dumps(theme_name))
            .replace("__AUTO_THEMES__", json.dumps(auto_themes, separators=(",", ":")))
            .replace("__SHOW_FILENAME__", "true" if show_filename else "false")
            .replace("__SHOW_CREATED_TIME__", "true" if show_created_time else "false")
            .replace("__SHOW_FILE_SIZE__", "true" if show_file_size else "false")
            .replace("__SHOW_VIDEO_THUMBNAILS__", "true" if show_video_thumbnails else "false")
            .replace("__COLOR_SCHEME__", theme["scheme"])
            .replace("__FAVICON_LINK__", favicon_link)
            .replace("__HEADER_STICKY_CLASS__", "" if sticky_header else "header-not-sticky"))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")
    return len(posts)

def main() -> int:
    script_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Tạo archive HTML offline từ config.yml và thư mục media.")
    parser.add_argument("--images", type=Path, default=None, help="Ghi đè danh sách thư mục trong config.yml bằng một thư mục")
    parser.add_argument("--output", type=Path, default=None, help="File HTML đầu ra (mặc định: index.html cạnh script)")
    parser.add_argument("--title", default=None, help="Ghi đè tên archive trong config.yml")
    parser.add_argument("--theme", default=None, help="Ghi đè theme trong config.yml (bao gồm auto, Nord, Tokyo Night, Gruvbox, Rose Pine)")
    parser.add_argument("--sort-by", default=None, choices=("name", "created", "created_desc"), help="Sắp xếp theo tên, ngày tạo tăng dần hoặc mới nhất trước")
    args = parser.parse_args()
    try:
        config, config_path = load_config(script_dir)
        archive_title = args.title or config.get("title") or f"{script_dir.name} Archive"
        def normalize_theme(value: object) -> str:
            name = str(value).strip().casefold().replace("catppuccin-", "").replace("_", "-")
            return {"tokyonight": "tokyo-night", "rosepine": "rose-pine"}.get(name, name)
        theme_name = normalize_theme(args.theme or config.get("theme") or "mocha")
        theme_light = normalize_theme(config.get("theme_light") or "latte")
        theme_dark = normalize_theme(config.get("theme_dark") or "mocha")
        valid_themes = set(THEMES) | {"auto"}
        if theme_name not in valid_themes:
            raise ValueError(f"Theme không hợp lệ: {theme_name}. Chọn một trong: auto, {', '.join(THEMES)}")
        if theme_light not in THEMES or theme_dark not in THEMES:
            raise ValueError("theme_light và theme_dark phải là theme có sẵn, không dùng auto")
        sort_by = str(args.sort_by or config.get("sort_by") or "name").strip().casefold()
        sort_by = {"date": "created", "created_at": "created", "newest": "created_desc", "latest": "created_desc"}.get(sort_by, sort_by)
        if sort_by not in ("name", "created", "created_desc"):
            raise ValueError("sort_by phải là name, created hoặc created_desc")
        output = args.output if args.output is not None else script_dir / "index.html"
        if args.images is not None:
            folders = [args.images if args.images.is_absolute() else Path.cwd() / args.images]
        else:
            configured = config.get("images_dirs") or ([config["images_dir"]] if config.get("images_dir") else [])
            if configured:
                base_dir = config_path.parent if config_path else script_dir
                if len(configured) == 1 and str(configured[0]).strip().casefold() == "all":
                    folders = []
                    candidates = sorted((item for item in base_dir.iterdir()
                                         if item.is_dir() and not item.name.startswith(".")
                                         and item.name not in IGNORED_MEDIA_DIRS),
                                        key=lambda item: natural_key(item.name))
                    for candidate in candidates:
                        if any(path.is_file() and path.suffix.casefold() in MEDIA_EXTENSIONS
                               for path in candidate.rglob("*")
                               if all(not part.startswith(".") and part not in IGNORED_MEDIA_DIRS
                                      for part in path.relative_to(candidate).parts)):
                            folders.append(candidate)
                else:
                    folders = [Path(str(value)) if Path(str(value)).is_absolute() else base_dir / str(value) for value in configured]
            else:
                candidates = [script_dir / "Images", script_dir / "images", Path.cwd() / "Images", Path.cwd() / "images"]
                folders = [next((candidate for candidate in candidates if candidate.is_dir()), candidates[0])]
        sticky_value = str(config.get("sticky_header", "true")).strip().casefold()
        sticky_header = sticky_value not in ("false", "no", "0", "off", "disabled")
        def config_bool(key: str) -> bool:
            return str(config.get(key, "false")).strip().casefold() in ("true", "yes", "1", "on", "enabled")
        show_filename = config_bool("show_filename")
        show_created_time = config_bool("show_created_time")
        show_file_size = config_bool("show_file_size")
        show_video_thumbnails = config_bool("show_video_thumbnails")
        try:
            folder_filter_depth = int(config.get("folder_filter_depth", 1))
        except (TypeError, ValueError):
            raise ValueError("folder_filter_depth phải là số nguyên từ 0 đến 10")
        if not 0 <= folder_filter_depth <= 10:
            raise ValueError("folder_filter_depth phải là số nguyên từ 0 đến 10")
        count = generate_html(folders, output, str(archive_title), theme_name, theme_light, theme_dark, sort_by, sticky_header, show_filename, show_created_time, show_file_size, show_video_thumbnails, folder_filter_depth, script_dir)
    except (OSError, ValueError) as exc:
        print(f"Lỗi: {exc}", file=sys.stderr)
        return 1
    print(f"Đã tạo {output} với {count} bài viết · theme {theme_name} · sort {sort_by}.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
