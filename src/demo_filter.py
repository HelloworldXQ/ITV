# src/demo_filter.py
# Demo 频道筛选与排序模块，支持精确匹配和宽松匹配

from pathlib import Path
import re
from src.config import DEMO_FILE, OUTPUT_DIR
from src.alias_matcher import get_alias_matcher

try:
    from src.config import DEMO_MATCH_MODE
except ImportError:
    DEMO_MATCH_MODE = "exact"

def normalize_for_demo(name: str) -> str:
    """对 demo 频道名进行规范化，用于宽松匹配"""
    # 转小写
    name = name.lower()
    # 去除空格
    name = re.sub(r'\s+', '', name)
    # 去除连字符和点号
    name = re.sub(r'[-._]', '', name)
    # 去除常见后缀
    name = re.sub(r'(高清|频道|hd|标清|付费|备\d+)$', '', name)
    return name

def parse_demo_order_with_categories(demo_file: Path = DEMO_FILE):
    """解析 demo.txt，返回 (分类列表, 原始频道名列表, 标准化后的频道名列表)"""
    if not demo_file.exists():
        print(f"⚠️ Demo 文件不存在: {demo_file}")
        return [], [], []
    matcher = get_alias_matcher()
    categories = []
    raw_names = []
    norm_names = []
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
                raw_names.append(demo_name)
                if matcher:
                    demo_name = matcher.normalize(demo_name)
                norm_names.append(demo_name)
                categories.append(current_category)
            else:
                raw_names.append(line)
                norm_names.append(line)
                categories.append("其他")
    print(f"📋 从 demo.txt 解析到 {len(norm_names)} 个有序频道，共 {len(set(categories))} 个分类")
    # 打印前10个标准化后的demo名用于调试
    print(f"   Demo 名称样例（标准化后）: {norm_names[:10]}")
    return categories, raw_names, norm_names

def filter_and_order_by_demo(channels: list, alias_matcher=None):
    """
    根据 demo.txt 筛选并排序频道。
    返回 (ordered_channels, unmatched_channels)
    """
    categories, raw_demo_names, demo_names = parse_demo_order_with_categories()
    if not demo_names:
        print("⚠️ demo.txt 为空，跳过筛选")
        return channels, []

    # 建立倒排索引：频道名 -> 频道对象
    name_to_channel = {ch["name"]: ch for ch in channels}
    # 打印前20个采集到的频道名（标准化后）用于调试
    sample_channels = list(name_to_channel.keys())[:20]
    print(f"   采集频道名样例（标准化后）: {sample_channels}")

    matched = []
    matched_names = set()
    unmatched = []

    if DEMO_MATCH_MODE == "exact":
        for idx, demo_name in enumerate(demo_names):
            if demo_name in name_to_channel:
                ch = name_to_channel[demo_name].copy()
                ch["demo_category"] = categories[idx]
                matched.append(ch)
                matched_names.add(demo_name)
            else:
                # 尝试宽松匹配：去除标点、空格后比较
                demo_simple = normalize_for_demo(demo_name)
                found = False
                for ch_name, ch in name_to_channel.items():
                    if ch_name in matched_names:
                        continue
                    ch_simple = normalize_for_demo(ch_name)
                    if ch_simple == demo_simple:
                        ch_copy = ch.copy()
                        ch_copy["demo_category"] = categories[idx]
                        matched.append(ch_copy)
                        matched_names.add(ch_name)
                        print(f"🔧 宽松匹配成功: '{demo_name}' -> '{ch_name}'")
                        found = True
                        break
                if not found:
                    print(f"⚠️ Demo 未匹配 (精确): {demo_name} (分类: {categories[idx]})")
    else:
        # 包含匹配（较慢，但提供备用）
        all_names = list(name_to_channel.keys())
        for idx, demo_name in enumerate(demo_names):
            if demo_name in name_to_channel:
                ch = name_to_channel[demo_name].copy()
                ch["demo_category"] = categories[idx]
                matched.append(ch)
                matched_names.add(demo_name)
                continue
            demo_lower = demo_name.lower()
            found = False
            for ch_name in all_names:
                if ch_name in matched_names:
                    continue
                if demo_lower in ch_name.lower() or ch_name.lower() in demo_lower:
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
