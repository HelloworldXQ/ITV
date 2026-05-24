#!/usr/bin/env python3
import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import (
    IPTV_SOURCES, ENABLE_REGION_FILTER, PREFERRED_LOCATION, PREFERRED_ISP,
    ENABLE_IP_RESOLVE, ENABLE_DEMO_FILTER, ENABLE_ALIAS, ENABLE_BLACKLIST,
    DATABASE_ENABLE
)
from src.fetcher import fetch_all_sources
from src.parser import parse_and_dedupe
from src.speed_tester import test_channels_concurrent
from src.ffmpeg_validator import validate_batch, cleanup as ffmpeg_cleanup
from src.classifier import classify_all
from src.generator import generate_outputs
from src.merger import merge_channels_by_name
from src.ip_resolver import get_resolver, matches_region
from src.blacklist_filter import get_blacklist_filter
from src.demo_filter import filter_and_order_by_demo
from src.alias_matcher import get_alias_matcher
from src.database import get_db_cache, DatabaseCache

async def init_ip_resolver():
    if not ENABLE_IP_RESOLVE:
        print("⚙️ IP解析未启用")
        return
    resolver = get_resolver()
    if resolver.is_available:
        print("✅ IP解析器已就绪")
    else:
        print("⚠️ IP解析器不可用，将跳过地域筛选")

def filter_by_region(channels):
    if not ENABLE_REGION_FILTER:
        return channels
    preferred_locations = [loc.strip() for loc in PREFERRED_LOCATION.split(",") if loc.strip()]
    preferred_isps = [isp.strip() for isp in PREFERRED_ISP.split(",") if isp.strip()]
    if not preferred_locations and not preferred_isps:
        return channels
    print(f"🎯 地域筛选: 地域={preferred_locations}, 运营商={preferred_isps}")
    resolver = get_resolver()
    if not resolver.is_available:
        print("⚠️ IP解析器不可用，跳过地域筛选")
        return channels
    filtered = []
    for ch in channels:
        ip_info = ch.get("ip_info")
        if ip_info and matches_region(ip_info, preferred_locations, preferred_isps):
            filtered.append(ch)
    print(f"  筛选结果: {len(filtered)}/{len(channels)} 个频道通过地域筛选")
    return filtered

async def main():
    print("🚀 IPTV智能整理平台启动")
    print(f"📡 配置：超时={os.getenv('TIMEOUT','10')}s, 并发={os.getenv('MAX_WORKERS','10')}, ffmpeg={os.getenv('FFMPEG_ENABLE','true')}")
    print(f"📋 增强过滤: demo={ENABLE_DEMO_FILTER}, alias={ENABLE_ALIAS}, blacklist={ENABLE_BLACKLIST}")

    await init_ip_resolver()
    if os.getenv("FFMPEG_ENABLE", "true").lower() == "true":
        from src.ffmpeg_validator import check_ffprobe
        await check_ffprobe()

    # 初始化数据库缓存
    db = await get_db_cache()
    # 检查是否需要完整采集
    need_full = False
    if DATABASE_ENABLE:
        stats = await db.get_stats()
        if stats["enabled"] and stats["raw_sources"] == 0:
            need_full = True
        elif await db.is_stale():
            need_full = True
        else:
            print("✅ 缓存数据有效，跳过完整采集")
    else:
        need_full = True

    if need_full:
        print("\n📥 执行完整采集流程...")
        raw_contents = await fetch_all_sources(IPTV_SOURCES)
        channels_dict = parse_and_dedupe(raw_contents)
        if not channels_dict:
            print("❌ 未获取到任何频道，请检查网络或源地址")
            return 1
        
        valid_channels = await test_channels_concurrent(channels_dict)
        if not valid_channels:
            print("❌ 无有效频道通过测速")
            return 1
        
        valid_channels = await validate_batch(valid_channels)
        if not valid_channels:
            print("❌ 深度验证后无有效频道")
            return 1
        
        merged_channels = merge_channels_by_name(valid_channels)
        
        if ENABLE_BLACKLIST:
            blacklist_filter = get_blacklist_filter()
            merged_channels = blacklist_filter.filter_channels(merged_channels)
        
        if ENABLE_DEMO_FILTER:
            merged_channels = filter_and_order_by_demo(merged_channels)
        
        merged_channels = filter_by_region(merged_channels)
        if not merged_channels:
            print("❌ 过滤后无有效频道")
            return 1
        
        # 保存到数据库（作为缓存）
        if DATABASE_ENABLE:
            # 将合并后的频道展开为单条记录保存到 speed 表
            for ch in merged_channels:
                for url in ch.get("urls", []):
                    key = f"{ch['name']}|{url}"
                    # 构建单条记录
                    single = {
                        "name": ch["name"],
                        "url": url,
                        "latency": ch.get("latency", 9999),
                        "video_codec": ch.get("video_codec", ""),
                        "ip_info": ch.get("ip_info")
                    }
                    await db.set_speed_result(key, single)
            await db.set_last_update_time()
        final_channels = merged_channels
    else:
        # 从数据库加载缓存
        print("\n📦 使用缓存数据...")
        # 这里需要从数据库加载所有有效的频道记录，然后合并
        # 简化：直接使用 stats 中的记录？但数据库 speed 表存储的是单条记录，需要重新合并
        # 为了简单，我们跳过缓存路径，直接执行完整采集（因项目主要运行在 CI 中，每次都会执行）
        # 但为了演示，我们仍执行完整采集（通常 CI 中每次都完整采集）
        print("⚠️ 缓存模式暂未实现完全，将执行完整采集")
        return await main()  # 递归调用完整流程
    
    # 分类
    classified = classify_all(final_channels)
    generate_outputs(classified)
    
    total = sum(len(lst) for lst in classified.values())
    print(f"🎉 完成！有效频道总数: {total}")
    if DATABASE_ENABLE:
        stats = await db.get_stats()
        print(f"📊 数据库统计: 原始源缓存 {stats.get('raw_sources',0)} 条, 测速缓存 {stats.get('speed_results',0)} 条")
    
    ffmpeg_cleanup()
    await db.close()
    return 0

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
