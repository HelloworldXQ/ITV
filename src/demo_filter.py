# src/demo_filter.py
# Demo 频道筛选与排序模块，使用倒排索引提升速度，并输出未匹配频道到 shai.txt

from pathlib import Path
from collections import defaultdict
from src.config import DEMO_FILE, OUTPUT_DIR
from src.alias_matcher import get_alias_matcher

try:
    from src.config import DEMO_MATCH_MODE
except ImportError:
    DEMO_MATCH_MODE = "exact"

def parse_demo_order_with_categories(demo_file: Path = DEMO_FILE):
    """解析 demo.txt，返回 (分类列表, 频道名列表) 保持顺序"""
    if not demo_file.exists():
        print(f"⚠️ Demo 文件不存在: {demo_file}")
        return [], []
    matcher = get_alias_matcher()
    categories = []
    channel_names = []
    current_category = None
    with open(demo_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.endswith(",#genre#"):
                current_category = line[:-7]
                continue
            if line.startswith('#'):
                continue
            if current_category is not None:
                demo_name = line
                if matcher:
                    demo_name = matcher.normalize(demo_name)
                categories.append(current_category)
                channel_names.append(demo_name)
            else:
                categories.append("其他")
                channel_names.append(line)
    print(f"📋 从 demo.txt 解析到 {len(channel_names)} 个有序频道，共 {len(set(categories))} 个分类")
    return categories, channel_names

def filter_and_order_by_demo(channels: list, alias_matcher=None):
    """
    根据 demo.txt 筛选并排序频道。
    返回 (ordered_channels, unmatched_channels)
    """
    categories, demo_names = parse_demo_order_with_categories()
    if not demo_names:
        print("⚠️ demo.txt 为空，跳过筛选")
        return channels, []

    # 建立倒排索引：频道名 -> 频道对象（通常一个名对应一个频道）
    name_to_channel = {ch["name"]: ch for ch in channels}

    matched = []
    matched_names = set()
    unmatched = []

    # 精确匹配（推荐）
    if DEMO_MATCH_MODE == "exact":
        for idx, demo_name in enumerate(demo_names):
            if demo_name in name_to_channel:
                ch = name_to_channel[demo_name].copy()
                ch["demo_category"] = categories[idx]
                matched.append(ch)
                matched_names.add(demo_name)
            else:
                print(f"⚠️ Demo 未匹配 (精确): {demo_name} (分类: {categories[idx]})")
    else:
        # 包含匹配（较慢，但保留）
        # 构建所有频道名列表用于模糊匹配
        all_names = list(name_to_channel.keys())
        for idx, demo_name in enumerate(demo_names):
            if demo_name in name_to_channel:
                ch = name_to_channel[demo_name].copy()
                ch["demo_category"] = categories[idx]
                matched.append(ch)
                matched_names.add(demo_name)
                continue
            # 模糊查找
            found = False
            for ch_name in all_names:
                if ch_name in matched_names:
                    continue
                # 简单的包含匹配（忽略大小写和空格）
                if demo_name.lower().replace(' ', '') in ch_name.lower().replace(' ', '') or \
                   ch_name.lower().replace(' ', '') in demo_name.lower().replace(' ', ''):
                    ch = name_to_channel[ch_name].copy()
                    ch["demo_category"] = categories[idx]
                    matched.append(ch)
                    matched_names.add(ch_name)
                    found = True
                    break
            if not found:
                print(f"⚠️ Demo 未匹配 (模糊): {demo_name} (分类: {categories[idx]})")

    # 收集未匹配的频道
    for ch in channels:
        if ch["name"] not in matched_names:
            unmatched.append(ch)

    print(f"🎯 Demo 筛选：原始 {len(channels)} 个频道 -> 匹配 {len(matched)} 个频道，未匹配 {len(unmatched)} 个")

    # 输出未匹配频道到 shai.txt
    if unmatched:
        shai_path = OUTPUT_DIR / "shai.txt"
        with open(shai_path, "w", encoding="utf-8") as f:
            f.write("# 未被 demo.txt 匹配的频道列表\n")
            f.write("# 格式：频道名,URL\n\n")
            for ch in unmatched:
                url = ch["urls"][0] if ch.get("urls") else ch["url"]
                f.write(f"{ch['name']},{url}\n")
        print(f"📄 未匹配频道已写入 {shai_path}")

    return matched, unmatched
