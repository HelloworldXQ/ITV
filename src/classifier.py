# src/classifier.py
# 智能分类模块（只输出用户要求的四个大类）

from src.config import CATEGORY_KEYWORDS, CCTV_ORDER

# 用户期望的最终分类（只保留这四个）
ALLOWED_CATEGORIES = {"央视", "卫视", "地方", "港澳台"}

def classify_channel(channel: dict) -> str:
    """根据标准化频道名返回分类（映射到四个大类）"""
    name = channel.get("name", "")
    group = channel.get("group_title", "")
    
    # 优先使用 group-title 匹配
    if group:
        group_lower = group.lower()
        if any(kw in group_lower for kw in ["cctv", "央视", "中央"]):
            return "央视"
        if "卫视" in group_lower:
            return "卫视"
        if any(kw in group_lower for kw in ["港", "澳", "台", "香港", "澳门", "台湾", "翡翠", "明珠", "凤凰", "tvb"]):
            return "港澳台"
        # 地方台关键词
        if any(kw in group_lower for kw in ["综合", "频道", "新闻", "生活", "经济", "公共"]):
            return "地方"
    
    # 匹配频道名
    name_lower = name.lower()
    if any(kw in name_lower for kw in ["cctv", "央视", "中央"]):
        return "央视"
    if "卫视" in name_lower:
        return "卫视"
    if any(kw in name_lower for kw in ["港", "澳", "台", "香港", "澳门", "台湾", "翡翠", "明珠", "凤凰", "tvb"]):
        return "港澳台"
    # 地方台（包含省份、城市名或常见后缀）
    provinces = ["北京","天津","上海","重庆","河北","山西","辽宁","吉林","黑龙江","江苏","浙江","安徽","福建","江西","山东","河南","湖北","湖南","广东","海南","四川","贵州","云南","陕西","甘肃","青海","台湾","内蒙古","广西","西藏","宁夏","新疆","香港","澳门"]
    for prov in provinces:
        if prov in name:
            return "地方"
    if any(kw in name_lower for kw in ["电视台", "综合频道", "公共频道", "生活频道", "新闻综合"]):
        return "地方"
    
    return "其他"  # 其他分类最终会被过滤掉

def classify_and_filter(channels: list) -> dict:
    """分类并只保留四个大类，央视频道按顺序排序"""
    classified = {cat: [] for cat in ALLOWED_CATEGORIES}
    other_count = 0
    for ch in channels:
        cat = classify_channel(ch)
        if cat in ALLOWED_CATEGORIES:
            classified[cat].append(ch)
        else:
            other_count += 1
    
    # 央视频道内部排序
    if "央视" in classified:
        def ctv_key(ch):
            name = ch["name"]
            for idx, std in enumerate(CCTV_ORDER):
                if std.lower() == name.lower() or name.lower().startswith(std.lower()):
                    return idx
            return len(CCTV_ORDER)
        classified["央视"].sort(key=ctv_key)
    
    # 其他分类按名称排序
    for cat in ["卫视", "地方", "港澳台"]:
        if classified.get(cat):
            classified[cat].sort(key=lambda x: x["name"])
    
    print(f"📊 分类统计（仅保留央视/卫视/地方/港澳台）：")
    for cat, lst in classified.items():
        if lst:
            print(f"  {cat}: {len(lst)} 个频道")
    print(f"  （其他分类被过滤: {other_count} 个频道）")
    return classified
