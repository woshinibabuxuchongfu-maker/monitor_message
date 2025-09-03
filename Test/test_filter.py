import re
import sys
from Filter import KeywordMatcher, KeyWord

# 测试函数
print("===== 开始测试 Filter.py 功能 =====")
print(f"Python版本: {sys.version}")
print(f"当前路径: {__file__}")

# 创建匹配器实例
matcher = KeywordMatcher()
matcher.clear()  # 确保清除所有可能的残留数据

# === 1. 测试添加关键词 ===
print("\n=== 1. 测试添加关键词 ===")
kw1 = KeyWord("python", "lang")
kw2 = KeyWord("北京", "city")
ids = matcher.add_keywords([kw1, kw2])
print(f"添加的关键词ID: {ids}")
print(f"当前关键词数量: {matcher.size()}")
print(f"关键词列表: {matcher._keywords}")

# === 2. 测试添加正则表达式 ===
print("\n=== 2. 测试添加正则表达式 ===")
matcher.add_regex(r"\\b\\d{3}-\\d{3}-\\d{4}\\b", "phone")
matcher.add_regex(r"\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}\\b", "email")
print(f"正则表达式数量: {len(matcher._regex_patterns)}")
for i, (pattern, r_type) in enumerate(matcher._regex_patterns):
    print(f"正则{i+1} ({r_type}): {pattern.pattern}")

# === 3. 测试模糊匹配设置 ===
print("\n=== 3. 测试模糊匹配设置 ===")
matcher.enable_fuzzy_match(max_distance=1)
print(f"模糊匹配启用状态: {matcher._enable_fuzzy}")
print(f"最大编辑距离: {matcher._max_distance}")
print(f"模糊关键词列表: {matcher._fuzzy_keywords}")

# === 4. 构建自动机 ===
print("\n=== 4. 构建自动机 ===")
matcher.build()
print("自动机构建完成")

# === 5. 测试精确匹配 ===
print("\n=== 5. 测试精确匹配 ===")
test_text = "我的号码是123-456-7890，邮箱是test@example.com，我爱pyhton和北京！"
print(f"测试文本: {test_text}")
print("\n搜索结果:")

# 分别测试各个匹配类型
matches = list(matcher.search(test_text))
print(f"总匹配数: {len(matches)}")

for match in matches:
    print(f"[{match.match_type}] '{match.keyword}' at {match.start}-{match.end}")
    # 验证匹配位置是否正确
    matched_text = test_text[match.start:match.end+1]
    print(f"  匹配的文本片段: '{matched_text}'")

# === 6. 测试替换功能 ===
print("\n=== 6. 测试替换功能 ===")
replaced_text = matcher.replace(test_text)
print(f"替换后的文本: {replaced_text}")

# === 7. 单独测试正则匹配功能 ===
print("\n=== 7. 单独测试正则匹配功能 ===")
print("测试电话号码正则:")
phone_match = re.search(r"\\b\\d{3}-\\d{3}-\\d{4}\\b", test_text)
if phone_match:
    print(f"找到电话号码: '{phone_match.group()}' at {phone_match.start()}-{phone_match.end()-1}")
else:
    print("未找到电话号码")

print("\n测试邮箱正则:")
email_match = re.search(r"\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}\\b", test_text)
if email_match:
    print(f"找到邮箱: '{email_match.group()}' at {email_match.start()}-{email_match.end()-1}")
else:
    print("未找到邮箱")

# === 8. 单独测试模糊匹配功能 ===
print("\n=== 8. 单独测试模糊匹配功能 ===")
# 直接调用模糊匹配方法
if matcher._enable_fuzzy:
    fuzzy_matches = list(matcher._search_fuzzy(test_text))
    print(f"模糊匹配结果数: {len(fuzzy_matches)}")
    for match in fuzzy_matches:
        print(f"[fuzzy] '{match.keyword}' at {match.start}-{match.end}")
else:
    print("模糊匹配未启用")

print("\n===== 测试完成 =====")