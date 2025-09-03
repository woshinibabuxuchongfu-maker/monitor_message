import ahocorasick
import pickle
import re
from datetime import datetime
from typing import List, Generator, Optional, Tuple, Union, Dict, Any
from dataclasses import dataclass
# 导入RapidFuzz库
from rapidfuzz import fuzz, process

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
        try:
            # 默认添加re.UNICODE标志以更好地支持中文
            compiled_flags = flags | re.UNICODE
            if not self._case_sensitive:
                compiled_flags |= re.IGNORECASE
            compiled = re.compile(pattern, compiled_flags)
            self._regex_patterns.append((compiled, type))
        except re.error as e:
            print(f"编译正则表达式失败 '{pattern}': {e}")

    def _search_regex(self, text: str) -> Generator[MatchResult, None, None]:
        for pattern, r_type in self._regex_patterns:
            try:
                for match in pattern.finditer(text):
                    yield MatchResult(
                        start=match.start(),
                        end=match.end() - 1,
                        keyword=pattern.pattern,
                        match_type='regex'
                    )
            except Exception as e:
                print(f"正则 {pattern.pattern} 匹配出错: {e}")

    # ==================== 新增：模糊匹配（编辑距离）====================
    def _search_fuzzy(self, text: str) -> Generator[MatchResult, None, None]:
        """使用RapidFuzz在文本中搜索模糊匹配"""


        

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
        try:
            for end_index, keyword_id in self._automaton.iter(search_text):
                keyword_obj = self._id_to_keyword[keyword_id]
                # 计算实际文本中的起始位置
                # 注意：这里在不区分大小写时需要特殊处理，因为search_text是小写的
                if not self._case_sensitive:
                    # 找到原始文本中对应的位置
                    keyword_lower = keyword_obj.keyword.lower()
                    # 从end_index - len(keyword_lower) + 1位置开始向前找
                    start_pos = end_index - len(keyword_lower) + 1
                    # 确保在原始文本中正确匹配
                    while start_pos >= 0:
                        if text[start_pos:end_index+1].lower() == keyword_lower:
                            start_index = start_pos
                            break
                        start_pos -= 1
                else:
                    start_index = end_index - len(keyword_obj.keyword) + 1

                yield MatchResult(
                    start=start_index,
                    end=end_index,
                    keyword=keyword_obj,
                    match_type='exact'
                )
        except Exception as e:
            print(f"精确匹配出错: {e}")

        # 2. 正则匹配
        try:
            yield from self._search_regex(text)
        except Exception as e:
            print(f"正则匹配出错: {e}")

        # 3. 模糊匹配（较慢，可选）
        if self._enable_fuzzy:
            try:
                yield from self._search_fuzzy(text)
            except Exception as e:
                print(f"模糊匹配出错: {e}")

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
    print(f"添加的关键词: {matcher._keywords}")

    # === 2. 添加正则 ===
    # 优化正则表达式，移除可能导致问题的\b边界（在中文环境中可能不可靠）
    matcher.add_regex(r"\d{3}-\d{3}-\d{4}", "phone")  # 匹配电话
    # 修复邮箱正则，移除|字符（它在字符类中被当作普通字符）
    matcher.add_regex(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "email")
    print(f"添加的正则表达式: {[(p.pattern, t) for p, t in matcher._regex_patterns]}")

    # === 3. 启用模糊匹配 ===
    matcher.enable_fuzzy_match(max_distance=1)
    print(f"模糊匹配启用状态: {matcher._enable_fuzzy}, 模糊关键词: {matcher._fuzzy_keywords}")

    # === 4. 构建 ===
    matcher.build()

    # === 5. 搜索 ===
    text = "我的号码是123-456-7890，邮箱是test@example.com，我爱pyhton和北京！"
    print(f"测试文本: {text}")

    print("\n搜索结果:")
    matches = list(matcher.search(text))
    if not matches:
        print("未找到任何匹配")
    else:
        for match in matches:
            # 获取实际匹配的文本片段用于调试
            matched_text = text[match.start:match.end+1]
            print(f"[{match.match_type}] '{match.keyword}' at {match.start}-{match.end} → '{matched_text}'")

    # === 6. 测试替换功能 ===
    replaced_text = matcher.replace(text)
    print(f"\n替换后的文本: {replaced_text}")

    # === 7. 持久化 ===
    matcher.save("keyword_matcher.pkl")
    print("\n已保存到 keyword_matcher.pkl")

    # --- 重启后 ---
    # new_matcher = KeywordMatcher()
    # new_matcher.load("keyword_matcher.pkl")
    # new_matcher.search("...")