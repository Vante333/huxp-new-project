"""
统计 Redis 缓存 JSON 数据中 tier=1 的记录条数
双击运行即可，需要同目录下有 data.json 文件
"""
import json
import os
import sys


def main():
    # 脚本所在目录
    base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    data_path = os.path.join(base_dir, "data.json")

    if not os.path.exists(data_path):
        print(f"当前目录未找到 data.json 文件：{data_path}")
        input("按回车键退出...")
        return

    try:
        with open(data_path, "r", encoding="utf-8") as f:
            obj = json.load(f)
    except Exception as e:
        print("读取或解析 data.json 失败：", e)
        input("按回车键退出...")
        return

    # 统计各个 tier 的数量
    tier_counts = {}
    all_items = []
    
    # 遍历外层所有 key（可能是 "1", "2", "3" 等）
    for key, items in obj.items():
        if isinstance(items, list):
            all_items.extend(items)
    
    for item in all_items:
        tier = str(item.get("tier", "unknown"))
        tier_counts[tier] = tier_counts.get(tier, 0) + 1

    print("=" * 40)
    print("统计结果")
    print("=" * 40)
    print(f"总记录数：{len(all_items)}")
    print("-" * 40)
    print("各 tier 分组数量：")
    for tier in sorted(tier_counts.keys()):
        print(f"  tier={tier}: {tier_counts[tier]} 条")
    print("=" * 40)
    
    input("\n统计完成，按回车键退出...")


if __name__ == "__main__":
    main()
