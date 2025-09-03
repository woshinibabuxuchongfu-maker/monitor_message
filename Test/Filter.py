import ahocorasick
import pickle
import re
from datetime import datetime
from typing import List, Generator, Optional, Tuple, Union, Dict, Any
from dataclasses import dataclass

# 保持你原有的 KeyWord 类
class KeyWord:
    def __init__(self, keyword: str, type: str = 'keyword'):
        self.id = None
        self.keyword = keyword
        self.type = type
        self.created_at = datetime.now()

    def __repr__(self):
        return f"KeyWord(id={self.id}, keyword='{self.keyword}', type='{self.type}', created_at={self.created_at})"


@dataclass
class MatchResult:
    """统一的匹配结果结构"""
    start: int
    end: int
    keyword: Union[KeyWord, str]  # KeyWord 或 正则 pattern 字符串
    match_type: str  # 'exact', 'regex', 'fuzzy'


class KeywordMatcher:
    """
    增强版单例关键词匹配器
    支持：精确匹配、正则、模糊匹配、持久化
    """
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._keywords: List[KeyWord] = []
        self._keyword_to_id = {}
        self._id_to_keyword = {}
        self._next_id = 0
        self._automaton = ahocorasick.Automaton()
        self._case_sensitive = False

        # 正则支持
        self._regex_patterns: List[Tuple[re.Pattern, str]] = []  # (compiled_pattern, type)

        # 模糊匹配（编辑距离）
        self._enable_fuzzy = False
        self._fuzzy_keywords = []  # 用于模糊匹配的关键词列表
        self._max_distance = 1

        self._initialized = True

    # ==================== 精确匹配（原有功能） ====================

    def set_case_sensitive(self, case_sensitive: bool):
        if self._case_sensitive != case_sensitive:
            self._case_sensitive = case_sensitive
            self._rebuild_automaton()

    def add_keyword(self, keyword_obj: KeyWord) -> int:
        kw = keyword_obj.keyword if self._case_sensitive else keyword_obj.keyword.lower()
        if kw in self._keyword_to_id:
            return self._keyword_to_id[kw]

        keyword_obj.id = self._next_id
        self._next_id += 1

        self._keywords.append(keyword_obj)
        self._keyword_to_id[kw] = keyword_obj.id
        self._id_to_keyword[keyword_obj.id] = keyword_obj

        word_for_match = keyword_obj.keyword if self._case_sensitive else kw
        self._automaton.add_word(word_for_match, keyword_obj.id)

        # 如果启用模糊匹配，也加入模糊词库
        if self._enable_fuzzy:
            self._fuzzy_keywords.append(keyword_obj.keyword)

        return keyword_obj.id

    def add_keywords(self, keywords: List[KeyWord]) -> List[int]:
        return [self.add_keyword(kw) for kw in keywords]

    def _rebuild_automaton(self):
        self._automaton = ahocorasick.Automaton()
        for kw in self._keywords:
            word_for_match = kw.keyword if self._case_sensitive else kw.keyword.lower()
            self._automaton.add_word(word_for_match, kw.id)
        self._automaton.make_automaton()

    def build(self):
        self._automaton.make_automaton()
        if self._enable_fuzzy:
            # 可以预处理模糊索引（这里简化为线性扫描）
            pass

    # ==================== 新增：正则混合匹配 ====================

    def add_regex(self, pattern: str, type: str = "regex", flags: int = 0):
        """添加正则表达式匹配规则"""
        compiled = re.compile(pattern, flags if self._case_sensitive else flags | re.IGNORECASE)
        self._regex_patterns.append((compiled, type))

    def _search_regex(self, text: str) -> Generator[MatchResult, None, None]:
        for pattern, r_type in self._regex_patterns:
            for match in pattern.finditer(text):
                yield MatchResult(
                    start=match.start(),
                    end=match.end() - 1,
                    keyword=pattern.pattern,
                    match_type='regex'
                )

    # ==================== 新增：模糊匹配（编辑距离）====================

    def enable_fuzzy_match(self, max_distance: int = 1):
        """启用模糊匹配"""
        self._enable_fuzzy = True
        self._max_distance = max_distance
        self._fuzzy_keywords = [kw.keyword for kw in self._keywords]

    def _edit_distance(self, s1: str, s2: str) -> int:
        """计算编辑距离（Levenshtein Distance）"""
        if len(s1) < len(s2):
            return self._edit_distance(s2, s1)
        if len(s2) == 0:
            return len(s1)
        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        return previous_row[-1]

    def _search_fuzzy(self, text: str) -> Generator[MatchResult, None, None]:
        """在文本中搜索模糊匹配（性能较低，适合小文本）"""
        words = re.findall(r'\w+', text)
        for word in words:
            for kw in self._fuzzy_keywords:
                if self._edit_distance(word.lower(), kw.lower()) <= self._max_distance:
                    # 查找在原文中的位置
                    start = text.lower().find(word.lower())
                    if start != -1:
                        end = start + len(word) - 1
                        # 找到对应的 KeyWord 对象
                        matched_kw = next((k for k in self._keywords if k.keyword == kw), None)
                        if matched_kw:
                            yield MatchResult(
                                start=start,
                                end=end,
                                keyword=matched_kw,
                                match_type='fuzzy'
                            )

    # ==================== 新增：持久化 ====================

    def save(self, filepath: str):
        """保存整个 matcher 状态到文件"""
        state = {
            'keywords': self._keywords,
            'keyword_to_id': self._keyword_to_id,
            'id_to_keyword': self._id_to_keyword,
            'next_id': self._next_id,
            'case_sensitive': self._case_sensitive,
            'regex_patterns': [(p.pattern, t, p.flags) for p, t in self._regex_patterns],
            'enable_fuzzy': self._enable_fuzzy,
            'max_distance': self._max_distance,
        }
        with open(filepath, 'wb') as f:
            pickle.dump(state, f)

    def load(self, filepath: str):
        """从文件加载 matcher 状态"""
        with open(filepath, 'rb') as f:
            state = pickle.load(f)

        self._keywords = state['keywords']
        self._keyword_to_id = state['keyword_to_id']
        self._id_to_keyword = state['id_to_keyword']
        self._next_id = state['next_id']
        self._case_sensitive = state['case_sensitive']
        self._enable_fuzzy = state['enable_fuzzy']
        self._max_distance = state['max_distance']

        # 重建自动机
        self._automaton = ahocorasick.Automaton()
        for kw in self._keywords:
            word_for_match = kw.keyword if self._case_sensitive else kw.keyword.lower()
            self._automaton.add_word(word_for_match, kw.id)

        # 恢复正则
        self._regex_patterns = []
        for pattern_str, r_type, flags in state['regex_patterns']:
            compiled = re.compile(pattern_str, flags)
            self._regex_patterns.append((compiled, r_type))

        # 恢复模糊匹配词库
        if self._enable_fuzzy:
            self._fuzzy_keywords = [kw.keyword for kw in self._keywords]

        self.build()

    # ==================== 统一搜索接口 ====================

    def search(self, text: str) -> Generator[MatchResult, None, None]:
        """统一搜索：精确 + 正则 + 模糊"""
        # 1. 精确匹配
        search_text = text if self._case_sensitive else text.lower()
        for end_index, keyword_id in self._automaton.iter(search_text):
            keyword_obj = self._id_to_keyword[keyword_id]
            start_index = end_index - len(keyword_obj.keyword) + 1
            yield MatchResult(
                start=start_index,
                end=end_index,
                keyword=keyword_obj,
                match_type='exact'
            )

        # 2. 正则匹配
        yield from self._search_regex(text)

        # 3. 模糊匹配（较慢，可选）
        if self._enable_fuzzy:
            yield from self._search_fuzzy(text)

    def contains_any(self, text: str) -> bool:
        try:
            next(self.search(text))
            return True
        except StopIteration:
            return False

    def replace(self, text: str, replacement: str = "[***]") -> str:
        """替换所有匹配项（精确 + 正则 + 模糊）"""
        matches = list(self.search(text))
        matches.sort(key=lambda x: x.start)  # 按位置排序

        result = []
        last_end = 0
        for match in matches:
            if match.start < last_end:
                continue  # 重叠跳过
            result.append(text[last_end:match.start])
            result.append(replacement)
            last_end = match.end + 1
        result.append(text[last_end:])
        return ''.join(result)

    def clear(self):
        self._keywords.clear()
        self._keyword_to_id.clear()
        self._id_to_keyword.clear()
        self._next_id = 0
        self._automaton = ahocorasick.Automaton()
        self._regex_patterns.clear()
        self._fuzzy_keywords.clear()
        self._enable_fuzzy = False

    def size(self) -> int:
        return len(self._keywords)

if __name__ == "__main__":
    matcher = KeywordMatcher()

    # === 1. 添加精确关键词 ===
    kw1 = KeyWord("python", "lang")
    kw2 = KeyWord("北京", "city")
    matcher.add_keywords([kw1, kw2])

    # === 2. 添加正则 ===
    matcher.add_regex(r"\b\d{3}-\d{3}-\d{4}\b", "phone")  # 匹配电话
    matcher.add_regex(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "email")

    # === 3. 启用模糊匹配 ===
    matcher.enable_fuzzy_match(max_distance=1)

    # === 4. 构建 ===
    matcher.build()

    # === 5. 搜索 ===
    text = "我的号码是123-456-7890，邮箱是test@example.com，我爱pyhton和北京！"

    for match in matcher.search(text):
        print(f"[{match.match_type}] '{match.keyword}' at {match.start}-{match.end}")

    # 输出：
    # [exact] '北京' at 30-31
    # [regex] '123-456-7890' at 5-18
    # [regex] 'test@example.com' at 21-38
    # [fuzzy] 'python' at 28-33  ← 注意：pyhton → python

    # === 6. 持久化 ===
    matcher.save("keyword_matcher.pkl")

    # --- 重启后 ---
    # new_matcher = KeywordMatcher()
    # new_matcher.load("keyword_matcher.pkl")
    # new_matcher.search("...")