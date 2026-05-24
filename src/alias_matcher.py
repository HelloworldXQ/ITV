# src/alias_matcher.py
# 别名匹配模块，支持正则表达式，匹配策略：优先精确匹配，再子串

import re
from pathlib import Path
from typing import Dict, Optional, Union, Tuple

from src.config import ALIAS_FILE, ENABLE_ALIAS

class AliasMatcher:
    def __init__(self, alias_file: Path = ALIAS_FILE):
        self.alias_file = alias_file
        self.exact_mappings: Dict[str, str] = {}      # 精确别名（全等）-> 标准名
        self.substr_mappings: Dict[str, str] = {}     # 子串别名 -> 标准名
        self.regex_mappings: Dict[re.Pattern, str] = {} # 正则别名 -> 标准名
        self._load()

    def _load(self):
        if not self.alias_file.exists():
            print(f"⚠️ 别名文件不存在: {self.alias_file}")
            return
        with open(self.alias_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split(',')
                if len(parts) < 2:
                    print(f"⚠️ 别名文件第 {line_num} 行格式错误，跳过: {line}")
                    continue
                standard = parts[0].strip()
                aliases = parts[1:]
                for alias in aliases:
                    alias = alias.strip()
                    if not alias:
                        continue
                    if alias.startswith('re:'):
                        pattern_str = alias[3:].strip()
                        try:
                            pattern = re.compile(pattern_str, re.IGNORECASE)
                            self.regex_mappings[pattern] = standard
                        except re.error as e:
                            print(f"⚠️ 别名文件第 {line_num} 行正则错误: {e}")
                    else:
                        # 检查是否可能为精确别名（不包含通配符）
                        if '*' in alias or '?' in alias:
                            # 简单通配符转正则，但这里先作为子串处理
                            self.substr_mappings[alias.lower()] = standard
                        else:
                            # 精确匹配：要求整个字符串相等（忽略大小写）
                            self.exact_mappings[alias.lower()] = standard
        print(f"✅ 已加载别名规则：精确 {len(self.exact_mappings)}，子串 {len(self.substr_mappings)}，正则 {len(self.regex_mappings)}")

    def match(self, channel_name: str) -> Optional[str]:
        """返回标准化名称，若无匹配则返回 None"""
        if not channel_name:
            return None
        name_lower = channel_name.lower()
        # 1. 精确匹配（最高优先级）
        if name_lower in self.exact_mappings:
            return self.exact_mappings[name_lower]
        # 2. 正则匹配
        for pattern, standard in self.regex_mappings.items():
            if pattern.search(channel_name):
                return standard
        # 3. 子串匹配（最低优先级）
        for alias, standard in self.substr_mappings.items():
            if alias in name_lower:
                return standard
        return None

    def normalize(self, channel_name: str) -> str:
        """标准化频道名，若无匹配则返回原名称"""
        mapped = self.match(channel_name)
        return mapped if mapped is not None else channel_name

_matcher = None

def get_alias_matcher() -> AliasMatcher:
    global _matcher
    if _matcher is None and ENABLE_ALIAS:
        _matcher = AliasMatcher()
    return _matcher
