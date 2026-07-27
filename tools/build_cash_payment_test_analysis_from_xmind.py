"""从 XMind **原样**导出测试分析；仅在每个 tc 用例步骤列表末尾追加 ``- 数据`` 子节点。

原则：章节、用例标题、步骤与预期完全以脑图为准；「数据」用 ``- 数据`` 列表项（与 pc/步骤平级），不用 ``#### 数据``。

用法：
  python tools/build_cash_payment_test_analysis_from_xmind.py
  python tools/build_cash_payment_test_analysis_from_xmind.py --skip-xmind
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
XMIND = Path(
    r"d:\fenxi\API\2026_Q2\评审后\Q2_SP4\订单流支持真现金支付第三方权益测试分析.xmind"
)
TARGET = ROOT / "testcases" / "2026Q2SP4" / "订单流支持真现金支付第三方权益-测试分析-001.md"
PREVIEW_TARGET = (
    ROOT / "testcases" / "2026Q2SP4" / "订单流-预览订单接口-预收费权益现金-测试分析-001.md"
)
REQUIREMENT = "requirements/2026Q2SP4/Confluence-1906049058.md"


def _ExportXmind() -> None:
    if not XMIND.is_file():
        raise FileNotFoundError(f"未找到最新脑图：{XMIND}")
    cmd = [
        sys.executable,
        str(ROOT / "tools" / "xmind_to_testcases_md.py"),
        "--xmind",
        str(XMIND),
        "--out",
        str(TARGET),
        "--requirement",
        REQUIREMENT,
    ]
    subprocess.run(cmd, check=True, cwd=str(ROOT))


def _ApplyDataSections(path: Path) -> int:
    sys.path.insert(0, str(ROOT / "tools"))
    from append_case_data_sections import AppendCaseDataSections

    text = path.read_text(encoding="utf-8")
    updated = AppendCaseDataSections(text)
    path.write_text(updated, encoding="utf-8")
    import re

    return len(re.findall(r"^#{3,4} tc(?:-p\d+)?:", updated, re.M))


def Main() -> None:
    parser = argparse.ArgumentParser(description="从 XMind 原样导出并为全部用例追加数据节点")
    parser.add_argument(
        "--with-patch",
        action="store_true",
        help="额外运行 _patch_payment_expectations（会改写用例步骤，默认关闭）",
    )
    parser.add_argument(
        "--skip-xmind",
        action="store_true",
        help="跳过 XMind 导出，仅对现有 Markdown 追加/补齐数据节点",
    )
    args = parser.parse_args()

    if not args.skip_xmind:
        print("1/3 从最新 XMind 原样导出主文档…")
        _ExportXmind()
    else:
        print("1/3 跳过 XMind 导出…")

    if args.with_patch:
        print("  （可选）运行 payment 全文校正…")
        patch_mod = ROOT / "tools" / "_patch_payment_expectations.py"
        subprocess.run([sys.executable, str(patch_mod)], check=True, cwd=str(ROOT))

    print("2/3 主文档全部用例追加数据节点…")
    main_count = _ApplyDataSections(TARGET)
    print(f"  → {TARGET.name}：{main_count} 条用例")

    print("3/3 Preview 专项全部用例追加数据节点…")
    if PREVIEW_TARGET.is_file():
        preview_count = _ApplyDataSections(PREVIEW_TARGET)
        print(f"  → {PREVIEW_TARGET.name}：{preview_count} 条用例")
    else:
        print(f"  → 跳过（未找到 {PREVIEW_TARGET.name}）")

    print(f"完成。源脑图：{XMIND}")


if __name__ == "__main__":
    Main()
