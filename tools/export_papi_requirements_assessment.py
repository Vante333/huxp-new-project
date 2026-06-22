"""导出 PAPI 需求评估表为 Excel（附件1格式）。"""
from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

OUT = Path(__file__).resolve().parent / "PAPI-requirements-assessment.xlsx"
JIRA_BROWSE_BASE = "https://dragonpass.atlassian.net/browse/"

HEADERS = ["需求说明", "ticket", "风险等级", "流量等级", "需求等级", "备注"]


def TicketUrl(ticket: str) -> str:
    """将 ``PAPI-1234`` 转为 Jira browse 链接。"""
    key = ticket.strip()
    if key.startswith("http"):
        return key
    return f"{JIRA_BROWSE_BASE}{key}"

# (分组名, 行数据列表) — 每行: 需求说明, ticket, 风险, 流量, 等级, 备注
SECTIONS: list[tuple[str, list[tuple[str, ...]]]] = [
    (
        "1. Aero Blue",
        [
            ("【Aero Blue】Lounge+FT订单流支持AB5月版本", "PAPI-2576", "M", "H", "B", ""),
            ("【Aero Blue】修改注册新增字段到saas真实字段、支持clientUserId重复注册", "PAPI-2568", "M", "H", "B", ""),
            ("【Aero Blue】下单接口内部字段新增aeroblue支持（临时）", "PAPI-2572", "M", "H", "B", ""),
            ("【Aero Blue】批量获取项目可用资源/站点数据", "PAPI-2553", "M", "M", "B", ""),
            ("【Aero Blue】新增prebooking.created event", "PAPI-2590", "M", "M", "B", ""),
            ("【Aero Blue】SAAS H5订单要写入ProgramId", "PAPI-2598", "M", "H", "B", ""),
            ("【Aero Blue】/v2/programs/resources/batch 新增program是否可预约属性", "PAPI-2620", "M", "M", "B", ""),
            ("【Aero Blue】Preview接口修改usedEntitlementDetails为非必传", "PAPI-2657", "M", "H", "B", ""),
            ("【Aero Blue】收据获取接口", "PAPI-2664", "M", "M", "B", ""),
            ("【Aero Blue】payment status change callback", "PAPI-2671", "H", "H", "A", "涉及支付回调"),
            ("【Aero Blue】membership注册/查询接口新增内部字段", "PAPI-2548", "M", "H", "B", ""),
            ("【Aero Blue】多语言逻辑调整，支持es-419", "PAPI-2584", "L", "M", "C", "多语言配置类"),
        ],
    ),
    (
        "2. Local Offer",
        [
            ("Local Offer 资源查询部分", "PAPI-2608", "M", "M", "B", ""),
            ("Local Offer 订单部分", "PAPI-2750", "M", "H", "A", "核心订单流"),
            ("优化eSIM和Local offer只允许下1人次订单的提示语", "PAPI-2739", "L", "L", "C", "无需测试"),
        ],
    ),
    (
        "3. 通用优化 / Minor Enhancement",
        [
            ("/ePasses/details判断到MS订单给提示语【V1+V2】", "PAPI-2424", "L", "M", "C", "提示语优化"),
            ("预览/创单/订单详情新增usedEntitlementBreakdown array", "PAPI-2467", "M", "H", "B", "订单核心字段"),
            ("优化价格为空的告警逻辑", "PAPI-2497", "L", "L", "C", "告警逻辑"),
            ("优化zh-CN和zh-HK下港澳台机场数据冗余问题", "PAPI-2501", "L", "M", "C", "数据优化"),
            ("优化swap品类权益在注册/查询/update接口的返回结构", "PAPI-2515", "M", "H", "B", "会籍/权益核心"),
            ("优化crossModuleEntitlement空数据返回[]", "PAPI-2519", "L", "M", "C", "返回结构优化"),
            ("资源检索内存机制优化", "PAPI-2616", "M", "M", "B", "性能优化"),
            ("修复epass-bundle同一clientUserId注册失败问题", "PAPI-2640", "M", "H", "B", "注册修复"),
            ("membership preview/prebooking创单接口逻辑调整", "PAPI-2667", "M", "H", "A", "创单核心逻辑"),
            ("订单列表支持按状态过滤", "PAPI-2700", "M", "M", "B", ""),
            ("优化下单前token可用性检查逻辑", "PAPI-2780", "M", "H", "B", "下单前置校验"),
            ("优化bundle订单判断逻辑", "PAPI-2505", "M", "H", "B", ""),
            ("资源/站点列表支持通过id过滤", "PAPI-2636", "M", "M", "B", ""),
            ("project level资源/站点更新推送", "PAPI-2644", "M", "M", "B", "推送机制"),
        ],
    ),
    (
        "4. 多语言 / 区域",
        [
            ("语种支持新增韩语ko-KR", "PAPI-2541", "L", "L", "C", "已完成"),
            ("Support new language code｜新增多语种支持", "PAPI-2735", "L", "M", "B", "P0"),
            ("新增商业区域与iso国家地区code映射接口", "PAPI-2784", "L", "L", "C", "无需测试，产品验收即可；P0"),
        ],
    ),
    (
        "5. 运维 / SAAS / 其他",
        [
            ("SAAS权限组支持双key切换", "PAPI-2653", "M", "L", "B", "配置/权限"),
            ("token verification endpoint｜token鉴权接口", "PAPI-2730", "M", "M", "B", ""),
            ("【Revolut】FT订单详情/会籍列表补回字段", "PAPI-2707", "L", "M", "C", "无需测试，开发自测即可"),
            ("Sandbox simulate支持setmeal/coupon模拟核销", "PAPI-2697", "L", "L", "C", "Sandbox环境"),
            ("休息室/FT预订单PII信息收集改读BOSS", "PAPI-2722", "M", "M", "B", "数据源切换"),
        ],
    ),
]

HEADER_FILL = PatternFill("solid", fgColor="FFF2CC")
SECTION_FILL = PatternFill("solid", fgColor="E7E6E6")
LEGEND_FILL = PatternFill("solid", fgColor="F2F2F2")


def main() -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "PAPI需求评估"

    # 表头
    for col, h in enumerate(HEADERS, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.fill = HEADER_FILL
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal="center", vertical="center")

    row = 2
    total = 0
    for section_name, rows in SECTIONS:
        ws.cell(row=row, column=1, value=section_name).font = Font(bold=True)
        for c in range(1, len(HEADERS) + 1):
            ws.cell(row=row, column=c).fill = SECTION_FILL
        row += 1
        for data in rows:
            for col, val in enumerate(data, 1):
                cell = ws.cell(row=row, column=col, value=val)
                if col == 2 and val:
                    url = TicketUrl(str(val))
                    cell.value = url
                    cell.hyperlink = url
                    cell.font = Font(color="0563C1", underline="single")
            row += 1
            total += 1
        row += 1  # 分组空行

    # 图例（G 列）
    legends = [
        ("需求等级说明", ""),
        ("A级别", "100%投入"),
        ("B级别", "关注修改点，回归核心功能"),
        ("C级别", "开发自测"),
        ("", ""),
        ("风险/流量 H", "高"),
        ("风险/流量 M", "中"),
        ("风险/流量 L", "低"),
    ]
    for i, (k, v) in enumerate(legends, 1):
        ws.cell(row=i, column=8, value=k).font = Font(bold=(i == 1))
        ws.cell(row=i, column=9, value=v)
        if i == 1:
            ws.cell(row=i, column=8).fill = LEGEND_FILL

    # 列宽
    widths = [55, 52, 10, 10, 10, 28]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.column_dimensions["H"].width = 14
    ws.column_dimensions["I"].width = 28

    ws.freeze_panes = "A2"
    wb.save(OUT)
    print(f"Wrote {OUT} ({total} rows)")


if __name__ == "__main__":
    main()
