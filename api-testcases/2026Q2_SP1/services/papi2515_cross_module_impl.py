"""
PAPI-2515 crossModuleEntitlements — 业务实现模块（原 ``papi2515_helpers`` 主体）。

对外兼容：``papi2515_helpers`` 仅为重导出壳。

**OpenAPI（Default module MCP Q1SP4+5，2026-03）契约**：

- ``POST /v2/entitlements/search``：查询会籍权益摘要
- ``POST /v2/entitlements/update``：**与下一条为不同接口**。按请求体中的 ``module``/``tier``/``usageRestriction`` 等更新（典型为 **moduleExclusive** 单品类），**路径中无** ``entitlementPoolId``。
- ``POST /v2/entitlements/{entitlementPoolId}/update``：**与上一条为不同接口**。路径参数指定 **权益池 ID**，在 ``crossModuleEntitlements`` 分组下按池轮询更新；请求体为 ``purchasedQuantity`` 或 ``quantity``+``usageRestriction``（见 ``BuildP2515PoolUpdatePlan``）。

必填环境变量与 2548 一致：``DP_CLIENT_ID``、``DP_CLIENT_SECRET``；注册需 ``DP_PROGRAM_ID`` 或
``DP_P2515_PROGRAM_ID``（后者优先）。可选覆盖见根目录 ``.env.example`` 中 ``DP_P2515_*`` 说明。

**副作用**：用例会改写沙箱中测试会籍的权益数值，请勿对生产或共享手工数据执行。

**多接口统一契约**：当 ``POST /v2/memberships`` 或 ``POST /v2/entitlements/update`` 的 ``data`` 中含 ``entitlements`` 时，
可用 ``RunP2515CrossModuleAndModuleExclusiveFromInner`` 与 search 侧一致地校验 cross（summary / pools 四指标聚合：缺键按 0、任池 ``-1`` 则该指标为 ``-1``；各池 ``details`` 不含携伴聚合键）与 moduleExclusive（``details`` 若含携伴聚合键则须为 ``null`` 或可解析整数，与 cross 池裁剪规则不同）。

**主链路（写侧附件 E2E，单一编排入口）**：``RunP2515MainE2EScenario(token, steps)``，**HTTP 先后顺序**如下（与
``test_e2e_register_search_module_update_pool_updates`` 一致）。Allure 的 ``S01/S02/…`` 由 ``steps.Next`` 按**每次请求**递增：
按池更新有 N 条则多 N 次 ``Next``，故末尾两次 ``search`` 的序列码会随 N 平移，勿死记为某一固定 ``Sxx``。

1. ``POST /v2/memberships``（``BuildP2515RegisterPayload``）→ 响应内 entitlements 契约（``RunP2515CrossModuleAndModuleExclusiveFromInner``）
2. ``POST /v2/entitlements/search`` 基线 → cross 契约与 summary/pools 四指标聚合
3. ``POST /v2/entitlements/update`` 单品类（``BuildP2515ModuleExclusiveUpdateBody``，**非** 路径带 poolId）
4. ``POST /v2/entitlements/search``（module 更新后）→ cross 归一化与基线一致、moduleExclusive 指标增量
5. 零至多条 ``POST /v2/entitlements/{entitlementPoolId}/update``（``BuildP2515PoolUpdatePlan``；无计划则 ``soft.Record`` 提示并跳过 POST）
6. ``POST /v2/entitlements/search``（全部单池更新后）→ 契约 + summary 与预期指标（软断言标签 ``PAPI-2515-S06``）
7. ``POST /v2/entitlements/search``（最终一致性）→ 同上（软断言标签 ``PAPI-2515-S07``）；末尾 ``P2515E2ESoftAssert.RaiseIfAnyFailure``

**只读探测（非上述编排）**：已存在会籍时 ``POST /v2/entitlements/search`` + ``AssertCrossModuleContract``（见探测用例与 ``DP_P2515_PROBE_MEMBERSHIP_ID``）。
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Final, List, Mapping, MutableMapping, Optional, Sequence, Tuple, Union, cast

import allure
import pytest
from requests import Response
from framework.data import (
    LoadMembershipRegisterCsvRow,
    LoadP2515DatasetCsvRow,
    ResolveMembershipProgramIdOverride,
)

from services.papi2548_memberships_extensions_impl import (
    AfterResponseHook,
    AllureHttpScenarioSteps,
    AssertHttpAndBusinessOk,
    AssertMembershipSearchRecord,
    IsBusinessSuccess,
    IsHttpOk,
    JsonDict,
    ParseResponseEnvelope,
    PostMembershipsSearch,
    RegisterMembershipSuccessDetail,
    RequestWithAllure,
    UnwrapMembershipRecord,
    _RunAllureAssertionStep,
)

# 沙箱常见：program 配置不允许按权益池更新（单池 update 被拒绝）
P2515_POOL_UPDATE_PROGRAM_DENIED_ERR: Final[str] = "500.030.024"


@dataclass
class P2515E2ESoftAssert:
    """
    E2E **软断言**容器：执行可调用对象时捕获 ``AssertionError`` 记入列表，不中断用例，便于**继续发后续 HTTP**。

    在链路末尾调用 ``RaiseIfAnyFailure``，若有失败则 ``pytest.fail`` 一次性输出全部信息，Allure 中仍可见已执行的步骤。
    """

    errors: List[str] = field(default_factory=list)

    def Run(self, label: str, fn: Callable[[], None]) -> None:
        """在 Allure 子步骤 ``label`` 下执行 ``fn``；失败仅记录，不向外抛。"""
        with allure.step(label):
            try:
                fn()
            except AssertionError as exc:
                self.errors.append(f"{label}\n{exc}")

    def Record(self, message: str) -> None:
        """记录非 ``AssertionError`` 类提示（如无可执行计划、program 拒绝按池更新）。"""
        self.errors.append(message)

    def RaiseIfAnyFailure(self, *, header: str = "E2E 链路已跑完，下列项未通过（聚合）：") -> None:
        """若存在记录则 ``pytest.fail``；无记录则正常返回（用例通过）。"""
        if not self.errors:
            return
        pytest.fail(header + "\n\n" + "\n\n---\n\n".join(self.errors))


def RequireP2515ProgramIdForRegisterOrSkip() -> None:
    """缺 ``DP_PROGRAM_ID`` / ``DP_P2515_PROGRAM_ID`` 时 ``pytest.skip``（注册造数前置）。"""
    if os.environ.get("DP_P2515_PROGRAM_ID", "").strip() or os.environ.get("DP_PROGRAM_ID", "").strip():
        return
    csv_program = ResolveMembershipProgramIdOverride()
    if csv_program:
        return
    csv_extra = LoadP2515DatasetCsvRow().register_extra_json or {}
    if str(csv_extra.get("programId", "")).strip():
        return
    pytest.skip("注册造数需要 DP_PROGRAM_ID 或 DP_P2515_PROGRAM_ID（见套件 README）")


def _CaptureP2515E2EAssertion(soft: P2515E2ESoftAssert, label: str, fn: Callable[[], None]) -> None:
    """在同一步 HTTP Allure 步骤内执行断言；失败记入软断言列表（不额外包一层 ``allure.step``）。"""
    try:
        fn()
    except AssertionError as exc:
        soft.errors.append(f"{label}\n{exc}")


def _HttpStepKw(steps: AllureHttpScenarioSteps, brief: str) -> Dict[str, str]:
    """生成 ``RequestWithAllure`` 用的 ``step_code`` / ``step_title``。"""
    code, title = steps.Next(brief)
    return {"step_code": code, "step_title": title}


# 携伴聚合字段名：cross 各组 ``pools[].details`` **不得**出现；moduleExclusive ``details`` 可出现（常为 null）
_POOL_GUEST_AGGREGATE_KEYS: Final[Tuple[str, ...]] = ("allowedGuestsPerUsage", "maxGuestsNextUse")

# summary 与 pools 求和用到的四类指标
_METRIC_KEYS: Final[Tuple[str, ...]] = (
    "cardholderExclusiveEntitlements",
    "guestsExclusiveEntitlements",
    "sharedEntitlements",
    "purchasedEntitlements",
)

_USAGE_RESTRICTION_TO_FIELD: Final[Dict[int, str]] = {
    1: "cardholderExclusiveEntitlements",
    2: "guestsExclusiveEntitlements",
    3: "sharedEntitlements",
}


@dataclass(frozen=True)
class P2515PlannedPoolUpdate:
    """单池更新计划：所属 applicableModules 键 + 路径参数 + 请求体。"""

    applicable_modules_key: Tuple[int, ...]
    entitlement_pool_id: str
    body: JsonDict


def PostEntitlementsSearch(
    token: str,
    membership_id: str,
    *,
    after_response: Optional[AfterResponseHook] = None,
    step_code: Optional[str] = None,
    step_title: Optional[str] = None,
) -> Tuple[Response, Optional[JsonDict], Any]:
    """``POST /v2/entitlements/search``，body 含 ``membershipId``。"""
    body: JsonDict = {"membershipId": membership_id}
    resp = RequestWithAllure(
        "POST",
        "/v2/entitlements/search",
        token=token,
        json_body=body,
        after_response=after_response,
        step_code=step_code,
        step_title=step_title,
    )
    status, env, inner = ParseResponseEnvelope(resp)
    return resp, env, inner


def PostEntitlementsUpdate(
    token: str,
    payload: JsonDict,
    *,
    after_response: Optional[AfterResponseHook] = None,
    step_code: Optional[str] = None,
    step_title: Optional[str] = None,
) -> Tuple[Response, Optional[JsonDict], Any]:
    """
    ``POST /v2/entitlements/update``（**非** ``/v2/entitlements/{entitlementPoolId}/update``）。

    用于按 ``module``+``tier`` 等定位的权益更新；路径不含 ``entitlementPoolId``。
    """
    resp = RequestWithAllure(
        "POST",
        "/v2/entitlements/update",
        token=token,
        json_body=payload,
        after_response=after_response,
        step_code=step_code,
        step_title=step_title,
    )
    status, env, inner = ParseResponseEnvelope(resp)
    return resp, env, inner


def PostEntitlementsUpdateByPoolId(
    token: str,
    entitlement_pool_id: str,
    payload: JsonDict,
    *,
    after_response: Optional[AfterResponseHook] = None,
    step_code: Optional[str] = None,
    step_title: Optional[str] = None,
) -> Tuple[Response, Optional[JsonDict], Any]:
    """
    ``POST /v2/entitlements/{entitlementPoolId}/update``（**非** ``POST /v2/entitlements/update``）。

    路径参数为 ``crossModuleEntitlements[].pools[].entitlementPoolId``；body 规则见 ``BuildP2515PoolUpdatePlan``。
    """
    path = f"/v2/entitlements/{entitlement_pool_id}/update"
    resp = RequestWithAllure(
        "POST",
        path,
        token=token,
        json_body=payload,
        after_response=after_response,
        step_code=step_code,
        step_title=step_title,
    )
    status, env, inner = ParseResponseEnvelope(resp)
    return resp, env, inner


def ExtractEntitlements(inner: Any) -> JsonDict:
    """
    从业务 ``data`` 对象中取出 ``entitlements``（与路径无关的通用形状）。

    适用于：``POST /v2/entitlements/search``、``POST /v2/entitlements/update``、
    ``POST /v2/memberships`` 等响应里 ``data.entitlements`` 嵌套形态（基址一般为 ``…/api``，路径常写作 ``/v2/...``）。
    """
    if not isinstance(inner, dict):
        return {}
    ent = inner.get("entitlements")
    if isinstance(ent, dict):
        return cast(JsonDict, ent)
    return {}


def GetCrossModuleEntitlements(entitlements: Mapping[str, Any]) -> List[JsonDict]:
    """返回 ``crossModuleEntitlements`` 列表（元素均为 dict）。"""
    raw = entitlements.get("crossModuleEntitlements")
    if raw is None:
        return []
    if not isinstance(raw, list):
        return []
    return [cast(JsonDict, x) for x in raw if isinstance(x, dict)]


def GetModuleExclusiveEntitlements(entitlements: Mapping[str, Any]) -> List[JsonDict]:
    raw = entitlements.get("moduleExclusiveEntitlements")
    if raw is None:
        return []
    if not isinstance(raw, list):
        return []
    return [cast(JsonDict, x) for x in raw if isinstance(x, dict)]


def AssertModuleExclusiveDetailsContract(
    module_exclusive: Sequence[Mapping[str, Any]],
    *,
    context: str = "PAPI-2515",
) -> None:
    """
    单品类 ``moduleExclusiveEntitlements``：每条 ``details`` 若含 ``allowedGuestsPerUsage`` /
    ``maxGuestsNextUse``，则值须为 ``null`` 或可解析为整数（网关常见占位 ``null``）。

    与 **cross** 的 ``pools[].details`` 不同：后者 **不得**出现上述二键（携伴聚合仅在组级 ``summary``）。

    注：单品类无 ``summary``+``pools`` 分栏，不适用「``summary`` 与跨池 ``details`` 四指标聚合一致」校验；该校验仅针对 ``crossModuleEntitlements``。
    """
    prefix = f"[{context}] " if context else ""
    title = f"{prefix}moduleExclusive details 契约（携伴键仅 null 或整数）".strip()

    def _Do() -> str:
        lines: List[str] = []
        for idx, row in enumerate(module_exclusive):
            if not isinstance(row, dict):
                continue
            det = row.get("details")
            if not isinstance(det, dict):
                lines.append(f"moduleExclusive[{idx}] 无 details 对象，跳过键检查")
                continue
            for fk in _POOL_GUEST_AGGREGATE_KEYS:
                if fk not in det:
                    continue
                v = det[fk]
                if v is None:
                    continue
                iv = IntDetail(det, fk)
                assert iv is not None, (
                    f"{prefix}moduleExclusive[{idx}].details[{fk!r}] 若非 null 须为可解析整数，实际值={v!r}"
                )
            lines.append(f"moduleExclusive[{idx}] module={row.get('module')!r} OK")
        if not lines:
            return "moduleExclusiveEntitlements 为空或无有效行，跳过"
        return "\n".join(lines)

    _RunAllureAssertionStep(title, _Do)


def RunP2515CrossModuleAndModuleExclusiveFromInner(
    inner: Any,
    *,
    context: str,
    assert_summary_equals_pool_sums: Optional[bool] = None,
) -> None:
    """
    从接口响应 ``data`` 解析 ``entitlements``，对 **crossModule** 与 **moduleExclusive** 套用 PAPI-2515 校验：

    - ``crossModuleEntitlements`` 非空：``AssertCrossModuleContract``（各池 ``details`` 不含携伴聚合键；``summary`` 与 ``pools`` 四指标聚合：缺键按 0、任池 ``-1`` 则该指标为 ``-1``，及 Allure 分解附件）
    - ``moduleExclusiveEntitlements`` 非空：``AssertModuleExclusiveDetailsContract``（携伴键允许存在，须 null 或可解析 int）

    若二者皆空则静默跳过（不生成断言步骤）。
    """
    ent = ExtractEntitlements(inner)
    cross = GetCrossModuleEntitlements(ent)
    me = GetModuleExclusiveEntitlements(ent)
    if not cross and not me:
        return
    if cross:
        AssertCrossModuleContract(
            cross,
            context=context,
            assert_summary_equals_pool_sums=assert_summary_equals_pool_sums,
        )
    if me:
        AssertModuleExclusiveDetailsContract(me, context=context)


def ApplicableModulesKey(applicable_modules: Any) -> Tuple[int, ...]:
    """将 ``applicableModules`` 规范为升序整数元组，作分组键。"""
    if not isinstance(applicable_modules, list) or not applicable_modules:
        return tuple()
    out: List[int] = []
    for x in applicable_modules:
        try:
            out.append(int(x))
        except (TypeError, ValueError):
            out.append(0)
    return tuple(sorted(out))


def IntDetail(details: Mapping[str, Any], key: str) -> Optional[int]:
    """读取 details 中的整型指标；无法解析则 ``None``。"""
    if key not in details:
        return None
    v = details[key]
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def DetailsOnlyPurchasedEntitlements(details: Mapping[str, Any]) -> bool:
    """
    判定是否为「仅买点池」形态：含 ``purchasedEntitlements``，且不含持卡人/携伴/共享三类键。
    """
    keys = set(details.keys())
    if "purchasedEntitlements" not in keys:
        return False
    other = {"cardholderExclusiveEntitlements", "guestsExclusiveEntitlements", "sharedEntitlements"}
    return not (keys & other)


def DetailMetricOrZero(details: Mapping[str, Any], key: str) -> int:
    """
    单池 ``details`` 上某一指标的贡献值：键不存在或无法解析为整数时视为 **0**（与 summary 对齐规则一致）。

    用于跨池聚合（见 ``AggregatePoolDetailsMetric`` / ``SumPoolDetailsMetrics``）：「不含该字段」按 0；
    若某池显式为 ``-1``，该指标整组聚合结果为 ``-1``（非与其它池数值相加）。
    """
    iv = IntDetail(details, key)
    return 0 if iv is None else iv


def AggregatePoolDetailsMetric(pools: Sequence[Any], key: str) -> int:
    """
    单指标跨 ``pools`` 聚合：任一池 ``details[key] == -1``（可解析整数）时结果为 ``-1``；
    否则为各池贡献之和（键缺失或不可解析按 **0**，与 ``DetailMetricOrZero`` 一致）。
    """
    total = 0
    for p in pools:
        if not isinstance(p, dict):
            d: Mapping[str, Any] = {}
        else:
            raw = p.get("details")
            d = cast(Mapping[str, Any], raw) if isinstance(raw, dict) else {}
        iv = IntDetail(d, key)
        if iv is None:
            continue
        if iv == -1:
            return -1
        total += iv
    return total


def SumPoolDetailsMetrics(pools: Sequence[Mapping[str, Any]]) -> Dict[str, int]:
    """
    组内 ``pools`` 各池 ``details`` 四类指标的跨池聚合（见 ``AggregatePoolDetailsMetric``）。

    缺键或不可解析 int 按 0；任池对某指标为 ``-1`` 时该指标聚合为 ``-1``。
    """
    return {k: AggregatePoolDetailsMetric(pools, k) for k in _METRIC_KEYS}


def BuildCrossModuleSummaryPoolBreakdown(group: Mapping[str, Any]) -> JsonDict:
    """
    构造「四指标 × summary 与各池 details 分项及跨池聚合」结构化数据，供 Allure 附件与排查。

    规则（与 ``SumPoolDetailsMetrics`` / ``SummaryMetrics`` 一致）：

    - 各指标：缺键按 0；任池 ``details`` 该指标为 ``-1`` 时聚合为 ``-1``；否则为各池数值之和；
    - 四类字段：``cardholderExclusiveEntitlements``、``guestsExclusiveEntitlements``、
      ``sharedEntitlements``、``purchasedEntitlements``。
    """
    am = group.get("applicableModules")
    summary_raw = group.get("summary")
    pools_raw = group.get("pools")
    summary_d: Mapping[str, Any] = (
        cast(Mapping[str, Any], summary_raw) if isinstance(summary_raw, dict) else {}
    )
    pools_iter: Sequence[Any] = pools_raw if isinstance(pools_raw, list) else []
    sm = SummaryMetrics(summary_d)
    by_metric: Dict[str, Any] = {}
    comparison_table: List[JsonDict] = []
    for k in _METRIC_KEYS:
        pool_rows: List[JsonDict] = []
        for p in pools_iter:
            if not isinstance(p, dict):
                pid = None
                d: Mapping[str, Any] = {}
            else:
                pid = p.get("entitlementPoolId")
                raw_det = p.get("details")
                d = cast(Mapping[str, Any], raw_det) if isinstance(raw_det, dict) else {}
            v = DetailMetricOrZero(d, k)
            pool_rows.append({"entitlementPoolId": pid, "details_value": v})
        total = AggregatePoolDetailsMetric(pools_iter, k)
        s_val = int(sm.get(k, 0))
        by_metric[k] = {
            "summary": s_val,
            "details_sum": total,
            "pools_breakdown": pool_rows,
            "match": s_val == total,
        }
        comparison_table.append(
            {
                "field": k,
                "summary": s_val,
                "details_sum": total,
                "match": s_val == total,
            }
        )
    out: JsonDict = {
        "applicableModules": list(am) if isinstance(am, list) else am,
        "comparison_table": comparison_table,
        "by_metric": by_metric,
    }
    return out


def _SanitizeAllureAttachmentNameFragment(text: str, max_len: int = 40) -> str:
    one_line = " ".join(str(text).split())
    out_chars: List[str] = []
    for ch in one_line[:max_len]:
        if ch in '/\\:*?"<>|':
            out_chars.append("_")
        else:
            out_chars.append(ch)
    s = "".join(out_chars).strip()
    return s if s else "p2515"


def AttachAllureP2515SummaryVsPoolDetailsBreakdown(
    group: Mapping[str, Any],
    *,
    context: str,
    group_index: Optional[int] = None,
) -> None:
    """在 Allure 中附加 ``summary`` 与 ``pools[].details`` 四指标对照（JSON 文本）。"""
    breakdown = BuildCrossModuleSummaryPoolBreakdown(group)
    frag = _SanitizeAllureAttachmentNameFragment(context, max_len=36)
    idx_part = f"_g{group_index}" if group_index is not None else ""
    name = f"p2515_summary_vs_details_{frag}{idx_part}.json.txt"
    allure.attach(
        json.dumps(breakdown, ensure_ascii=False, indent=2) + "\n",
        name=name,
        attachment_type=allure.attachment_type.TEXT,
    )


def SummaryMetrics(summary: Mapping[str, Any]) -> Dict[str, int]:
    """从 ``summary`` 读取四类指标，缺键视为 0。"""
    out: Dict[str, int] = {}
    for k in _METRIC_KEYS:
        iv = IntDetail(summary, k)
        out[k] = iv if iv is not None else 0
    return out


def RelaxSummaryPoolSumFromEnv() -> bool:
    """
    为真时 **关闭** ``summary`` 与 pools 明细跨池聚合严格相等断言（用于响应裁剪与合并语义暂不一致的沙箱）。

    环境变量：``DP_P2515_RELAX_SUMMARY_POOL_SUM`` 为 ``1`` / ``true`` / ``yes`` / ``on``。
    """

    v = os.environ.get("DP_P2515_RELAX_SUMMARY_POOL_SUM", "").strip().lower()
    return v in ("1", "true", "yes", "on")


def ResolveStrictSummaryEqualsPoolSums(assert_summary_equals_pool_sums: Optional[bool]) -> bool:
    """
    - 显式 ``True``/``False``：以参数为准。
    - ``None``：默认 **严格**（断言聚合相等）；仅当 ``RelaxSummaryPoolSumFromEnv()`` 为真时放宽。
    """
    if assert_summary_equals_pool_sums is not None:
        return bool(assert_summary_equals_pool_sums)
    return not RelaxSummaryPoolSumFromEnv()


def AssertCrossModuleContract(
    cross_groups: Sequence[Mapping[str, Any]],
    *,
    context: str = "PAPI-2515",
    assert_summary_equals_pool_sums: Optional[bool] = None,
) -> None:
    """
    结构契约：每组含 ``applicableModules``、``summary``、``pools``；``pools`` 项含 ``entitlementPoolId``、
    ``details``；各池 ``details`` **不得**含 ``allowedGuestsPerUsage`` / ``maxGuestsNextUse``（携伴聚合仅出现在 ``summary``）。

    **summary 与 pools 聚合**：默认 **严格** 断言每组 ``summary`` 四类指标等于各池 ``details`` 的跨池聚合结果：
    缺键按 **0**；任池某指标为 **-1** 时该指标整组为 **-1**（见 ``AggregatePoolDetailsMetric`` / ``SumPoolDetailsMetrics``）。
    开启严格时会在 Allure 附加 ``p2515_summary_vs_details_*``，逐字段展示 ``summary``、各池 ``details_value`` 与 ``details_sum``。
    若仍无法与网关对齐，可设 ``DP_P2515_RELAX_SUMMARY_POOL_SUM=1`` 或 ``assert_summary_equals_pool_sums=False``。
    """
    prefix = f"[{context}] " if context else ""
    strict = ResolveStrictSummaryEqualsPoolSums(assert_summary_equals_pool_sums)
    title = (
        f"{prefix}crossModule 结构契约" + (" 与 summary/pools 聚合" if strict else "")
    ).strip()

    def _Do() -> str:
        lines: List[str] = []
        for idx, g in enumerate(cross_groups):
            assert isinstance(g, dict), f"{prefix}crossModule[{idx}] 非对象: {g!r}"
            assert "applicableModules" in g, f"{prefix}crossModule[{idx}] 缺 applicableModules"
            assert "summary" in g, f"{prefix}crossModule[{idx}] 缺 summary"
            assert "pools" in g, f"{prefix}crossModule[{idx}] 缺 pools"
            summary = g.get("summary")
            assert isinstance(summary, dict), f"{prefix}crossModule[{idx}].summary 非对象"
            pools = g.get("pools")
            assert isinstance(pools, list), f"{prefix}crossModule[{idx}].pools 非数组"
            for j, p in enumerate(pools):
                assert isinstance(p, dict), f"{prefix}crossModule[{idx}].pools[{j}] 非对象"
                assert p.get("entitlementPoolId"), f"{prefix}池缺 entitlementPoolId: {p!r}"
                det = p.get("details")
                assert isinstance(det, dict), f"{prefix}池 details 非对象: {p!r}"
                for fk in _POOL_GUEST_AGGREGATE_KEYS:
                    assert fk not in det, (
                        f"{prefix}crossModule[{idx}].pools[{j}].details 不应含键 {fk!r}，实际存在且值={det.get(fk)!r}"
                    )
            if strict:
                AttachAllureP2515SummaryVsPoolDetailsBreakdown(
                    cast(Mapping[str, Any], g),
                    context=f"{context}-cross-{idx}",
                    group_index=idx,
                )
                sm = SummaryMetrics(cast(Mapping[str, Any], summary))
                pm = SumPoolDetailsMetrics(cast(List[Mapping[str, Any]], pools))
                assert sm == pm, (
                    f"{prefix}crossModule[{idx}] summary 与 pools 聚合不一致（缺键按 0；任池 -1 则该指标为 -1）\n"
                    f"summary={sm!r}\npools_sum={pm!r}\n"
                    f"详见 Allure 附件 p2515_summary_vs_details_*_g{idx}"
                )
            lines.append(f"组[{idx}] applicableModules={ApplicableModulesKey(g.get('applicableModules'))!r} OK")
        if not lines:
            return "crossModuleEntitlements 为空，跳过组内断言"
        return "\n".join(lines)

    _RunAllureAssertionStep(title, _Do)


def AssertSummaryEqualsPoolSums(
    group: Mapping[str, Any],
    *,
    context: str = "",
) -> None:
    """
    对单条 crossModule 组断言 ``summary`` 与 ``pools`` 四类指标聚合一致（缺键按 0；任池 -1 则该指标为 -1）。

    断言前写入 Allure 附件 ``p2515_summary_vs_details_*``：四字段各自的 ``summary``、各池 ``details_value``、``details_sum``。
    """
    prefix = f"[{context}] " if context else ""
    title = f"{prefix}summary 与 pools 求和一致".strip()

    def _Do() -> str:
        summary = group.get("summary")
        pools = group.get("pools")
        assert isinstance(summary, dict) and isinstance(pools, list), f"{prefix}summary/pools 形态异常: {group!r}"
        AttachAllureP2515SummaryVsPoolDetailsBreakdown(
            group,
            context=context.strip() or "summary_pool",
            group_index=None,
        )
        sm = SummaryMetrics(cast(Mapping[str, Any], summary))
        pm = SumPoolDetailsMetrics(cast(List[Mapping[str, Any]], pools))
        assert sm == pm, (
            f"{prefix}summary 与 pools 聚合不一致（缺键按 0；任池 -1 则该指标为 -1）\n"
            f"summary={sm!r} pools_sum={pm!r}\n详见 Allure 附件 p2515_summary_vs_details_*"
        )
        return f"summary==pools_sum: {sm!r}"

    _RunAllureAssertionStep(title, _Do)


def NormalizeCrossModuleEntitlementsForCompare(cross_groups: Sequence[Mapping[str, Any]]) -> List[JsonDict]:
    """
    归一化 crossModule 列表便于深度相等比较：组按 applicableModules 排序，池按 entitlementPoolId 排序；
    applicableModules 按升序整数列表写出。
    """
    normalized: List[JsonDict] = []
    for g in cross_groups:
        if not isinstance(g, dict):
            continue
        am_key = ApplicableModulesKey(g.get("applicableModules"))
        pools = g.get("pools")
        pool_list: List[JsonDict] = []
        if isinstance(pools, list):
            dict_pools = [cast(JsonDict, p) for p in pools if isinstance(p, dict)]
            dict_pools.sort(key=lambda x: str(x.get("entitlementPoolId", "")))
            for p in dict_pools:
                det = p.get("details")
                pool_list.append(
                    {
                        "entitlementPoolId": p.get("entitlementPoolId"),
                        "details": dict(det) if isinstance(det, dict) else {},
                    }
                )
        summ = g.get("summary")
        summ_d: JsonDict = dict(summ) if isinstance(summ, dict) else {}
        normalized.append(
            {
                "applicableModules": list(am_key),
                "summary": summ_d,
                "pools": pool_list,
            }
        )
    normalized.sort(key=lambda x: tuple(x.get("applicableModules", [])))
    return normalized


def AssertNormalizedCrossModuleEqual(
    before: Sequence[Mapping[str, Any]],
    after: Sequence[Mapping[str, Any]],
    *,
    context: str = "PAPI-2515",
) -> None:
    """断言两次 search 的 crossModule（归一化后）完全一致。"""
    prefix = f"[{context}] " if context else ""
    title = f"{prefix}crossModuleEntitlements（归一化）一致".strip()

    def _Do() -> str:
        nb = NormalizeCrossModuleEntitlementsForCompare(before)
        na = NormalizeCrossModuleEntitlementsForCompare(after)
        assert nb == na, f"{prefix}不一致\nbefore={json.dumps(nb, ensure_ascii=False, indent=2)}\nafter={json.dumps(na, ensure_ascii=False, indent=2)}"
        return f"组数={len(nb)}，归一化后全量相等"

    _RunAllureAssertionStep(title, _Do)


def MembershipsSearchSuccessEntitlements(
    token: str,
    membership_id: str,
    *,
    step_code: Optional[str] = None,
    step_title: Optional[str] = None,
    after_entitlements: Optional[Callable[[JsonDict], None]] = None,
) -> JsonDict:
    """
    ``POST /v2/memberships/search`` 成功，返回与 ``ExtractEntitlements`` 一致形态的 **entitlements** 对象。

    会籍记录上若无 ``entitlements`` 嵌套，则回退尝试从 ``data`` 根解析（兼容个别网关形态）。

    ``after_entitlements``：在同一步骤内、解析出 ``entitlements`` 后调用，用于契约断言嵌套在 HTTP 步骤下。
    """
    box: Dict[str, Any] = {}

    def _After(resp: Response) -> None:
        _st, env, inner = ParseResponseEnvelope(resp)
        AssertHttpAndBusinessOk(resp, env, context="POST /v2/memberships/search")
        rec = UnwrapMembershipRecord(inner)
        AssertMembershipSearchRecord(rec, membership_id)
        ent = ExtractEntitlements(rec)
        if not isinstance(ent, dict) or not ent:
            ent = ExtractEntitlements(inner)
        ent_d = ent if isinstance(ent, dict) else {}
        box["ent"] = ent_d
        if after_entitlements is not None:
            after_entitlements(cast(JsonDict, ent_d))

    PostMembershipsSearch(
        token,
        membership_id,
        after_response=_After,
        step_code=step_code,
        step_title=step_title,
    )
    if "ent" not in box:
        raise RuntimeError("memberships/search 回调未写入 entitlements")
    return cast(JsonDict, box["ent"])


def AssertCrossModuleSearchVsMembershipsAlign(
    entitlements_from_search: Mapping[str, Any],
    entitlements_from_memberships_search: Mapping[str, Any],
    *,
    context: str = "PAPI-2515-tc-P2-MBR-001",
) -> None:
    """
    **tc-P2-MBR-001**：同一用户下 ``POST /v2/entitlements/search`` 与 ``POST /v2/memberships/search`` 得到的
    ``crossModuleEntitlements`` 在归一化后须一致（组数、各组 applicableModules、summary 与 pools 明细形态）。
    """
    prefix = f"[{context}] " if context else ""
    title = f"{prefix}entitlements/search 与 memberships/search 的 crossModule 对齐".strip()

    def _Do() -> str:
        a = GetCrossModuleEntitlements(entitlements_from_search)
        b = GetCrossModuleEntitlements(entitlements_from_memberships_search)
        na = NormalizeCrossModuleEntitlementsForCompare(a)
        nb = NormalizeCrossModuleEntitlementsForCompare(b)
        assert na == nb, (
            f"{prefix}crossModule 不一致\nsearch={json.dumps(na, ensure_ascii=False, indent=2)}\n"
            f"memberships_search={json.dumps(nb, ensure_ascii=False, indent=2)}"
        )
        return f"cross 组数={len(na)}，归一化后全量相等"

    _RunAllureAssertionStep(title, _Do)


def _SummaryGuestKeysFromEnv() -> Tuple[str, str]:
    """环境变量覆盖携伴聚合字段名，默认与需求文档一致。"""
    a = os.environ.get("DP_P2515_SUMMARY_GUEST_KEY_ALLOWED", "").strip()
    b = os.environ.get("DP_P2515_SUMMARY_GUEST_KEY_MAX", "").strip()
    csv_row = LoadP2515DatasetCsvRow()
    return (
        a or csv_row.summary_guest_key_allowed or "allowedGuestsPerUsage",
        b or csv_row.summary_guest_key_max or "maxGuestsNextUse",
    )


def AssertCrossModuleSummaryGuestAggregateKeys(
    cross_groups: Sequence[Mapping[str, Any]],
    *,
    context: str = "PAPI-2515-tc-P1-GEN-002",
) -> None:
    """
    **tc-P1-GEN-002**：每组 ``summary`` 须含携伴相关聚合字段（键名可用 ``DP_P2515_SUMMARY_GUEST_KEY_*`` 覆盖），
    且值为可解析整数（含 ``0``）；布尔误填视为失败。
    """
    prefix = f"[{context}] " if context else ""
    k_allowed, k_max = _SummaryGuestKeysFromEnv()
    title = f"{prefix}summary 含携伴聚合字段 {k_allowed!r}/{k_max!r}".strip()

    def _Do() -> str:
        lines: List[str] = []
        for idx, g in enumerate(cross_groups):
            if not isinstance(g, dict):
                continue
            summ = g.get("summary")
            assert isinstance(summ, dict), f"{prefix}cross[{idx}].summary 非对象"
            for kn in (k_allowed, k_max):
                assert kn in summ, f"{prefix}cross[{idx}].summary 缺 {kn!r}"
                iv = IntDetail(cast(Mapping[str, Any], summ), kn)
                assert iv is not None, f"{prefix}cross[{idx}].summary[{kn!r}] 非整数可解析值: {summ.get(kn)!r}"
            lines.append(f"组[{idx}] OK")
        if not lines:
            return "crossModule 为空，跳过"
        return "\n".join(lines)

    _RunAllureAssertionStep(title, _Do)


def AssertCrossModuleSingleRowPerApplicableModules(
    cross_groups: Sequence[Mapping[str, Any]],
    *,
    context: str = "PAPI-2515-tc-P1-GEN-005",
) -> None:
    """
    **tc-P1-GEN-005**：相同 ``applicableModules`` 集合在 ``crossModuleEntitlements`` 中只对应 **一条** 元素。
    """
    prefix = f"[{context}] " if context else ""
    title = f"{prefix}applicableModules 分组唯一（无重复 cross 行）".strip()

    def _Do() -> str:
        keys: List[Tuple[int, ...]] = []
        for idx, g in enumerate(cross_groups):
            if not isinstance(g, dict):
                continue
            gk = ApplicableModulesKey(g.get("applicableModules"))
            assert gk, f"{prefix}cross[{idx}] applicableModules 无效，无法建分组键"
            keys.append(gk)
        assert len(keys) == len(set(keys)), f"{prefix}存在重复 applicableModules 分组: {keys!r}"
        return f"共 {len(keys)} 组，键均唯一"

    _RunAllureAssertionStep(title, _Do)


def AssertCrossModuleAtLeastTwoDistinctGroupsOrSkip(
    cross_groups: Sequence[Mapping[str, Any]],
) -> List[Tuple[int, ...]]:
    """
    **tc-P2-GEN-004 前置**：至少两组不同 ``applicableModules``；否则 ``pytest.skip``。

    返回升序排列的不重复分组键列表。
    """
    raw: List[Tuple[int, ...]] = []
    for g in cross_groups:
        if isinstance(g, dict):
            gk = ApplicableModulesKey(g.get("applicableModules"))
            if gk:
                raw.append(gk)
    uniq = sorted(set(raw))
    if len(uniq) < 2:
        pytest.skip(
            "tc-P2-GEN-004 / tc-P3-GEN-001：当前会籍 crossModule 不足两组不同 applicableModules，"
            "请换含多组跨模块数据的 program 或 DP_P2515_REGISTER_EXTRA_JSON"
        )
    return uniq


def AssertFictiveZeroPurchasedPoolInSearch(
    cross_groups: Sequence[Mapping[str, Any]],
    *,
    context: str = "PAPI-2515-tc-P2-GEN-005",
) -> None:
    """
    **tc-P2-GEN-005**：存在「买点池」形态且 ``details.purchasedEntitlements == 0`` 的池（虚构买点余额语义）。

    若模板无此类池则 ``pytest.skip``。
    """
    prefix = f"[{context}] " if context else ""
    title = f"{prefix}存在 purchasedEntitlements=0 的买点池".strip()

    def _Do() -> str:
        for gi, g in enumerate(cross_groups):
            if not isinstance(g, dict):
                continue
            pools = g.get("pools")
            if not isinstance(pools, list):
                continue
            for j, p in enumerate(pools):
                if not isinstance(p, dict):
                    continue
                det = p.get("details")
                if not isinstance(det, dict):
                    continue
                dm = cast(Mapping[str, Any], det)
                if not DetailsOnlyPurchasedEntitlements(dm):
                    continue
                v = IntDetail(dm, "purchasedEntitlements")
                if v == 0:
                    return f"组[{gi}] pool[{j}] 买点池 purchasedEntitlements=0 OK"
        pytest.skip(f"{prefix}未找到「仅 purchasedEntitlements 且值为 0」的池，换模板或造数后重试")

    _RunAllureAssertionStep(title, _Do)


def CrossModuleMetricsSnapshotFromEnvelopeInner(inner: Any) -> Dict[Tuple[int, ...], Dict[str, int]]:
    """从任意业务 ``data`` 内解析 ``entitlements`` 并取各组 ``summary`` 四类指标。"""
    ent = ExtractEntitlements(inner)
    return CrossModuleGroupMetricsByKey(GetCrossModuleEntitlements(ent))


def AssertCrossModuleMetricsEqualBetweenDataInners(
    inner_a: Any,
    inner_b: Any,
    *,
    context: str = "PAPI-2515-update-vs-search",
) -> None:
    """
    **tc-P2-GEN-001（Update）辅助**：两次响应 ``data`` 上 cross 各组 summary 四类指标须一致（如 update 响应与紧跟的 search）。
    """
    prefix = f"[{context}] " if context else ""
    title = f"{prefix}crossModule 各组 summary 指标一致".strip()

    def _Do() -> str:
        ma = CrossModuleMetricsSnapshotFromEnvelopeInner(inner_a)
        mb = CrossModuleMetricsSnapshotFromEnvelopeInner(inner_b)
        assert ma == mb, f"{prefix}metrics 不一致\nA={ma!r}\nB={mb!r}"
        return f"组键数={len(ma)} 全量一致"

    _RunAllureAssertionStep(title, _Do)


def AssertCrossModuleOtherGroupsNormalizedUnchanged(
    before: Sequence[Mapping[str, Any]],
    after: Sequence[Mapping[str, Any]],
    *,
    touched_group_key: Tuple[int, ...],
    context: str = "PAPI-2515-tc-P3-GEN-001",
) -> None:
    """
    **tc-P3-GEN-001**：按池更新仅影响所属组；**其它** ``applicableModules`` 组归一化快照须与更新前一致。
    """
    prefix = f"[{context}] " if context else ""
    title = f"{prefix}非目标组 crossModule 不变（touched={list(touched_group_key)!r}）".strip()

    def _ByKey(groups: Sequence[Mapping[str, Any]]) -> Dict[Tuple[int, ...], JsonDict]:
        m: Dict[Tuple[int, ...], JsonDict] = {}
        for g in groups:
            if not isinstance(g, dict):
                continue
            gk = ApplicableModulesKey(g.get("applicableModules"))
            if not gk:
                continue
            one = NormalizeCrossModuleEntitlementsForCompare([cast(Mapping[str, Any], g)])
            m[gk] = one[0] if one else {}
        return m

    def _Do() -> str:
        bmap = _ByKey(before)
        amap = _ByKey(after)
        assert set(bmap.keys()) == set(amap.keys()), (
            f"{prefix}更新前后分组键集合不一致 before={sorted(bmap.keys())!r} after={sorted(amap.keys())!r}"
        )
        lines: List[str] = []
        for gk, snap_b in bmap.items():
            if gk == touched_group_key:
                continue
            assert gk in amap, f"{prefix}after 缺组 {gk!r}"
            assert snap_b == amap[gk], (
                f"{prefix}组 {gk!r} 不应被按池更新波及\nbefore={json.dumps(snap_b, ensure_ascii=False)}\n"
                f"after={json.dumps(amap[gk], ensure_ascii=False)}"
            )
            lines.append(f"组{list(gk)!r} 未变")
        if not lines:
            return "仅单组 cross，无「其它组」可校验（请用多组数据）"
        return "\n".join(lines)

    _RunAllureAssertionStep(title, _Do)


def UsageRestrictionToMetricField(usage_restriction: int) -> str:
    """单品类 ``usageRestriction`` 与 details 字段映射（1 持卡人 / 2 携伴 / 3 共享）。"""
    ur = int(usage_restriction)
    if ur not in _USAGE_RESTRICTION_TO_FIELD:
        raise ValueError(f"不支持的 usageRestriction: {usage_restriction!r}")
    return _USAGE_RESTRICTION_TO_FIELD[ur]


def FindModuleExclusiveItem(
    module_exclusive: Sequence[Mapping[str, Any]],
    *,
    module: Any,
    tier: Optional[int] = None,
) -> Optional[JsonDict]:
    """在 ``moduleExclusiveEntitlements`` 中按 ``module`` 与可选 ``tier`` 查找条目。"""
    candidates: List[JsonDict] = []
    for it in module_exclusive:
        if not isinstance(it, dict):
            continue
        if str(it.get("module")) != str(module):
            continue
        candidates.append(cast(JsonDict, it))
    if not candidates:
        return None
    if tier is None:
        return candidates[0]
    for it in candidates:
        t = it.get("tier")
        if t is None or int(t) == int(tier):
            return it
    return candidates[0]


def AssertModuleExclusiveMetricDelta(
    before_ent: Mapping[str, Any],
    after_ent: Mapping[str, Any],
    *,
    module: Any,
    tier: Optional[int],
    usage_restriction: int,
    expect_delta: int,
    context: str = "PAPI-2515",
) -> None:
    """断言单品类指定 ``module``/``tier``/``usageRestriction`` 对应指标变化量。"""
    prefix = f"[{context}] " if context else ""
    field = UsageRestrictionToMetricField(usage_restriction)
    title = f"{prefix}moduleExclusive {field} 增量 {expect_delta:+d}".strip()

    def _Do() -> str:
        b_list = GetModuleExclusiveEntitlements(before_ent)
        a_list = GetModuleExclusiveEntitlements(after_ent)
        b_item = FindModuleExclusiveItem(b_list, module=module, tier=tier)
        a_item = FindModuleExclusiveItem(a_list, module=module, tier=tier)
        assert b_item is not None, f"{prefix}更新前未找到 module={module!r} tier={tier!r}"
        assert a_item is not None, f"{prefix}更新后未找到 module={module!r} tier={tier!r}"
        b_det = b_item.get("details")
        a_det = a_item.get("details")
        assert isinstance(b_det, dict) and isinstance(a_det, dict), f"{prefix}details 非对象"
        bv = IntDetail(cast(Mapping[str, Any], b_det), field)
        av = IntDetail(cast(Mapping[str, Any], a_det), field)
        assert bv is not None, f"{prefix}更新前缺 {field!r}"
        assert av is not None, f"{prefix}更新后缺 {field!r}"
        assert av == bv + expect_delta, (
            f"{prefix}{field}: 期望 {bv + expect_delta}（{bv}+{expect_delta}）实际 {av}"
        )
        return f"{field}: {bv} -> {av}（增量 {expect_delta:+d}）"

    _RunAllureAssertionStep(title, _Do)


def _PoolQuantityDefault() -> int:
    csv_row = LoadP2515DatasetCsvRow()
    raw = os.environ.get("DP_P2515_ATTACH2_POOL_QUANTITY", "").strip()
    if raw:
        return int(raw)
    if csv_row.pool_quantity is not None:
        return csv_row.pool_quantity
    return 2


def _PoolPurchasedQuantityDefault() -> int:
    csv_row = LoadP2515DatasetCsvRow()
    raw = os.environ.get("DP_P2515_ATTACH2_POOL_PURCHASED_QTY", "").strip()
    if raw:
        return int(raw)
    if csv_row.pool_purchased_quantity is not None:
        return csv_row.pool_purchased_quantity
    return 1


def BuildP2515PoolUpdatePlan(
    membership_id: str,
    cross_groups: Sequence[Mapping[str, Any]],
    *,
    pool_quantity: Optional[int] = None,
    purchased_quantity: Optional[int] = None,
) -> List[P2515PlannedPoolUpdate]:
    """
    对 ``crossModuleEntitlements`` 按组（``applicableModules``）遍历 ``pools[]``，为每个 ``entitlementPoolId``
    生成 ``POST /v2/entitlements/{entitlementPoolId}/update`` 请求体（**与** ``POST /v2/entitlements/update`` **不同接口**）。

    **（1）仅买点池**：``details`` 中**只存在** ``purchasedEntitlements``（无持卡人/携伴/共享三键）且值不为 ``-1`` 时，入参::

        {"membershipId": "...", "purchasedQuantity": <默认见环境变量>}

    **（2）其余池**：对 ``details`` 中出现的下列字段分别判断（值为 ``-1`` 则**跳过**该次更新），否则入参::

        {"membershipId": "...", "quantity": <默认见环境变量>, "usageRestriction": <1|2|3>}

    - ``cardholderExclusiveEntitlements`` → ``usageRestriction=1``
    - ``guestsExclusiveEntitlements`` → ``usageRestriction=2``
    - ``sharedEntitlements`` → ``usageRestriction=3``

    上述三字段以外键名不参与本分支的 ``usageRestriction`` 映射；``purchasedEntitlements`` 仅在**（1）**单独池形态下走 ``purchasedQuantity``。
    """
    pq = pool_quantity if pool_quantity is not None else _PoolQuantityDefault()
    puch = purchased_quantity if purchased_quantity is not None else _PoolPurchasedQuantityDefault()
    out: List[P2515PlannedPoolUpdate] = []
    for g in cross_groups:
        if not isinstance(g, dict):
            continue
        gk = ApplicableModulesKey(g.get("applicableModules"))
        pools = g.get("pools")
        if not isinstance(pools, list):
            continue
        for p in pools:
            if not isinstance(p, dict):
                continue
            pid = p.get("entitlementPoolId")
            if not pid:
                continue
            details = p.get("details")
            if not isinstance(details, dict):
                continue
            det = cast(Mapping[str, Any], details)
            if DetailsOnlyPurchasedEntitlements(det):
                v = IntDetail(det, "purchasedEntitlements")
                if v is None or v == -1:
                    continue
                body: JsonDict = {"membershipId": membership_id, "purchasedQuantity": puch}
                out.append(P2515PlannedPoolUpdate(gk, str(pid), body))
                continue
            pairs = (
                ("cardholderExclusiveEntitlements", 1),
                ("guestsExclusiveEntitlements", 2),
                ("sharedEntitlements", 3),
            )
            for field, ur in pairs:
                v = IntDetail(det, field)
                if v is None or v == -1:
                    continue
                out.append(
                    P2515PlannedPoolUpdate(
                        gk,
                        str(pid),
                        {"membershipId": membership_id, "quantity": pq, "usageRestriction": ur},
                    )
                )
    return out


def ApplyPlannedUpdateToExpectedGroupMetrics(
    base: Mapping[Tuple[int, ...], Mapping[str, int]],
    plan: Sequence[P2515PlannedPoolUpdate],
) -> Dict[Tuple[int, ...], Dict[str, int]]:
    """
    在「组级 summary 指标」上累加计划中的增量，用于与最终 search 比对。

    ``base`` 的键为 ``ApplicableModulesKey`` 得到的 ``Tuple[int, ...]``。
    """
    result: Dict[Tuple[int, ...], Dict[str, int]] = {k: dict(v) for k, v in base.items()}
    for item in plan:
        gk = item.applicable_modules_key
        if gk not in result:
            result[gk] = {m: 0 for m in _METRIC_KEYS}
        body = item.body
        if "purchasedQuantity" in body:
            result[gk]["purchasedEntitlements"] += int(body["purchasedQuantity"])
        if "quantity" in body and "usageRestriction" in body:
            ur = int(body["usageRestriction"])
            field = UsageRestrictionToMetricField(ur)
            result[gk][field] += int(body["quantity"])
    return result


def CrossModuleGroupMetricsByKey(cross_groups: Sequence[Mapping[str, Any]]) -> Dict[Tuple[int, ...], Dict[str, int]]:
    """每组 crossModule 当前 ``summary`` 四类指标，键为 ``ApplicableModulesKey``。"""
    out: Dict[Tuple[int, ...], Dict[str, int]] = {}
    for g in cross_groups:
        if not isinstance(g, dict):
            continue
        gk = ApplicableModulesKey(g.get("applicableModules"))
        summ = g.get("summary")
        if isinstance(summ, dict):
            out[gk] = SummaryMetrics(cast(Mapping[str, Any], summ))
        else:
            out[gk] = {m: 0 for m in _METRIC_KEYS}
    return out


def AssertCrossModuleSummaryMatchesExpected(
    cross_groups: Sequence[Mapping[str, Any]],
    expected_by_key: Mapping[Tuple[int, ...], Mapping[str, int]],
    *,
    context: str = "PAPI-2515",
    assert_summary_equals_pool_sums: Optional[bool] = None,
) -> None:
    """
    断言每组 ``summary`` 指标与期望值（如按单池更新计划推算）一致。

    默认 **同时** 断言 ``summary`` 与 pools 明细跨池聚合相等（与 ``AssertCrossModuleContract`` 同一套开关：
    ``ResolveStrictSummaryEqualsPoolSums`` / ``DP_P2515_RELAX_SUMMARY_POOL_SUM``）。
    """
    prefix = f"[{context}] " if context else ""
    strict = ResolveStrictSummaryEqualsPoolSums(assert_summary_equals_pool_sums)
    title = f"{prefix}crossModule summary 与预期一致".strip()

    def _Do() -> str:
        lines: List[str] = []
        for g in cross_groups:
            if not isinstance(g, dict):
                continue
            gk = ApplicableModulesKey(g.get("applicableModules"))
            if strict:
                AssertSummaryEqualsPoolSums(g, context=context)
            summ = g.get("summary")
            assert isinstance(summ, dict), f"{prefix}缺 summary"
            actual = SummaryMetrics(cast(Mapping[str, Any], summ))
            exp = expected_by_key.get(gk)
            assert exp is not None, f"{prefix}无预期数据 key={gk!r} actual_keys={list(expected_by_key.keys())!r}"
            exp_d = {k: int(exp[k]) for k in _METRIC_KEYS}
            assert actual == exp_d, f"{prefix}key={gk!r} 期望 {exp_d!r} 实际 {actual!r}"
            lines.append(f"{gk!r}: {actual!r}")
        return "\n".join(lines) if lines else "无 cross 组"

    _RunAllureAssertionStep(title, _Do)


def BuildP2515ModuleExclusiveUpdateBody(membership_id: str) -> JsonDict:
    """
    构造 ``POST /v2/entitlements/update`` 单品类更新体。

    若设置 ``DP_P2515_ATTACH2_MODULE_UPDATE_JSON``（JSON 对象字符串），与其合并并强制写入 ``membershipId``。
    否则使用 ``DP_P2515_ATTACH2_UPDATE_*`` 与默认：module=1、tier=2、usageRestriction=1、quantity=2。
    """
    csv_row = LoadP2515DatasetCsvRow()
    raw = os.environ.get("DP_P2515_ATTACH2_MODULE_UPDATE_JSON", "").strip()
    if raw:
        try:
            extra = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"DP_P2515_ATTACH2_MODULE_UPDATE_JSON 非合法 JSON: {exc}") from exc
        if not isinstance(extra, dict):
            raise RuntimeError("DP_P2515_ATTACH2_MODULE_UPDATE_JSON 须为 JSON 对象")
        body = cast(JsonDict, dict(extra))
        body["membershipId"] = membership_id
        return body
    base = dict(csv_row.module_update_json or {})
    mod_raw = os.environ.get("DP_P2515_ATTACH2_UPDATE_MODULE", "").strip()
    if not mod_raw:
        mod_raw = csv_row.update_module or str(base.get("module", "1"))
    try:
        module_val: Union[int, str] = int(mod_raw)
    except ValueError:
        module_val = mod_raw
    tier = int(
        os.environ.get("DP_P2515_ATTACH2_UPDATE_TIER", "").strip()
        or (str(csv_row.update_tier) if csv_row.update_tier is not None else str(base.get("tier", "2")))
    )
    ur = int(
        os.environ.get("DP_P2515_ATTACH2_UPDATE_USAGE_RESTRICTION", "").strip()
        or (
            str(csv_row.update_usage_restriction)
            if csv_row.update_usage_restriction is not None
            else str(base.get("usageRestriction", "1"))
        )
    )
    qty = int(
        os.environ.get("DP_P2515_ATTACH2_UPDATE_QUANTITY", "").strip()
        or (str(csv_row.update_quantity) if csv_row.update_quantity is not None else str(base.get("quantity", "2")))
    )
    return {
        "membershipId": membership_id,
        "quantity": qty,
        "module": module_val,
        "tier": tier,
        "usageRestriction": ur,
    }


def BuildP2515RegisterPayload(
    *,
    program_id: Optional[str] = None,
    extra: Optional[JsonDict] = None,
) -> JsonDict:
    """
    构造 ``POST /v2/memberships`` 注册体：在 ``BuildMinimalMembershipPayload`` 上合并 ``programId``。

    ``program_id`` 显式参数优先，否则 ``DP_P2515_PROGRAM_ID``，再否则 ``DP_PROGRAM_ID``。
    ``DP_P2515_REGISTER_EXTRA_JSON``：额外 JSON 对象合并进 payload（覆盖同名键）。
    """
    from services.papi2548_memberships_extensions_impl import BuildMinimalMembershipPayload

    payload = BuildMinimalMembershipPayload(extra=None)
    csv_row = LoadP2515DatasetCsvRow()
    membership_row = LoadMembershipRegisterCsvRow()
    pid = (program_id or "").strip() or os.environ.get("DP_P2515_PROGRAM_ID", "").strip()
    if not pid:
        pid = os.environ.get("DP_PROGRAM_ID", "").strip()
    if not pid:
        pid = membership_row.program_id_override.strip()
    csv_extra = dict(csv_row.register_extra_json or {})
    if not pid:
        pid = str(csv_extra.get("programId", "")).strip()
    if pid:
        payload["programId"] = pid
    if csv_extra:
        payload.update(csv_extra)
    reg_extra = os.environ.get("DP_P2515_REGISTER_EXTRA_JSON", "").strip()
    if reg_extra:
        try:
            merged = json.loads(reg_extra)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"DP_P2515_REGISTER_EXTRA_JSON 非合法 JSON: {exc}") from exc
        if not isinstance(merged, dict):
            raise RuntimeError("DP_P2515_REGISTER_EXTRA_JSON 须为 JSON 对象")
        payload.update(cast(JsonDict, merged))
    if extra:
        payload.update(extra)
    return payload


def MaybeAttach2515SearchDetails(
    entitlements: Mapping[str, Any],
    *,
    label: str,
) -> None:
    """调试：将 cross/moduleExclusive 摘要写入 Allure（完整结构较大时仅摘要）。"""
    if os.environ.get("DP_P2515_PRINT_SUMMARY_POOLS", "").strip().lower() not in ("1", "true", "yes"):
        return
    cross = GetCrossModuleEntitlements(entitlements)
    me = GetModuleExclusiveEntitlements(entitlements)
    snap = {
        "label": label,
        "crossModule_groups": len(cross),
        "moduleExclusive_rows": len(me),
        "crossModule_keys": [list(ApplicableModulesKey(g.get("applicableModules"))) for g in cross],
    }
    allure.attach(
        json.dumps(snap, ensure_ascii=False, indent=2) + "\n",
        name=f"p2515_entitlements_snapshot_{label}",
        attachment_type=allure.attachment_type.TEXT,
    )


def EntitlementsSearchSuccess(
    token: str,
    membership_id: str,
    *,
    step_code: Optional[str] = None,
    step_title: Optional[str] = None,
    after_entitlements: Optional[Callable[[JsonDict], None]] = None,
) -> JsonDict:
    """
    发起 search 并断言 HTTP+业务成功，返回 ``entitlements`` 对象。

    ``after_entitlements``：在成功解析 ``entitlements`` 后、仍位于同一 HTTP Allure 步骤内调用，
    便于将 PAPI-2515 等断言挂到 ``POST /v2/entitlements/search`` 步骤下。
    """
    box: Dict[str, Any] = {}

    def _After(resp: Response) -> None:
        _st, env, inner = ParseResponseEnvelope(resp)
        AssertHttpAndBusinessOk(resp, env, context="POST /v2/entitlements/search")
        ent = ExtractEntitlements(inner)
        box["ent"] = ent
        if after_entitlements is not None:
            after_entitlements(cast(JsonDict, ent))

    PostEntitlementsSearch(
        token,
        membership_id,
        after_response=_After,
        step_code=step_code,
        step_title=step_title,
    )
    if "ent" not in box:
        raise RuntimeError("search 回调未写入 entitlements")
    return cast(JsonDict, box["ent"])


def EntitlementsUpdateSuccess(
    token: str,
    payload: JsonDict,
    *,
    step_code: Optional[str] = None,
    step_title: Optional[str] = None,
    assert_p2515_entitlements_contract: bool = True,
    p2515_contract_context: str = "PAPI-2515-POST-/v2/entitlements/update",
    assert_summary_equals_pool_sums: Optional[bool] = None,
) -> None:
    """
    ``POST /v2/entitlements/update`` 成功断言（**非** ``/v2/entitlements/{poolId}/update``）。

    若 ``assert_p2515_entitlements_contract`` 为真且响应 ``data`` 中含 ``entitlements``，则对 cross / moduleExclusive
    执行与 search 相同的 P2515 契约（cross 含 summary 与 pools 四指标聚合；moduleExclusive 仅校验 details 键）。
    """

    def _After(resp: Response) -> None:
        _st, env, inner = ParseResponseEnvelope(resp)
        AssertHttpAndBusinessOk(resp, env, context="POST /v2/entitlements/update")
        if assert_p2515_entitlements_contract:
            RunP2515CrossModuleAndModuleExclusiveFromInner(
                inner,
                context=p2515_contract_context,
                assert_summary_equals_pool_sums=assert_summary_equals_pool_sums,
            )

    PostEntitlementsUpdate(
        token,
        payload,
        after_response=_After,
        step_code=step_code,
        step_title=step_title,
    )


def EntitlementsPoolUpdateSuccess(
    token: str,
    pool_id: str,
    payload: JsonDict,
    *,
    step_code: Optional[str] = None,
    step_title: Optional[str] = None,
) -> None:
    """``POST /v2/entitlements/{{poolId}}/update`` 成功断言。"""

    def _After(resp: Response) -> None:
        _st, env, _inner = ParseResponseEnvelope(resp)
        AssertHttpAndBusinessOk(resp, env, context=f"POST /v2/entitlements/{pool_id}/update")

    PostEntitlementsUpdateByPoolId(
        token,
        pool_id,
        payload,
        after_response=_After,
        step_code=step_code,
        step_title=step_title,
    )


def IsEntitlementPoolUpdateDeniedByProgram(env: Optional[JsonDict]) -> bool:
    """业务体 ``errCode == 500.030.024`` 时表示当前 program 不允许按池编辑该类权益。"""
    if not isinstance(env, dict):
        return False
    return str(env.get("errCode", "")).strip() == P2515_POOL_UPDATE_PROGRAM_DENIED_ERR


def PostEntitlementsPoolUpdateOrRecord(
    token: str,
    pool_id: str,
    payload: JsonDict,
    *,
    errors_out: List[str],
    step_code: Optional[str] = None,
    step_title: Optional[str] = None,
) -> None:
    """
    发起按池更新；若返回 ``500.030.024`` 或 HTTP/业务失败，将说明写入 ``errors_out`` 而**不**抛异常，
    供 E2E 软断言链路继续执行后续步骤。
    """

    def _After(resp: Response) -> None:
        _st, env, _inner = ParseResponseEnvelope(resp)
        if IsHttpOk(resp) and isinstance(env, dict) and IsEntitlementPoolUpdateDeniedByProgram(env):
            errors_out.append(
                f"POST /v2/entitlements/{pool_id}/update：program 禁止按池编辑（errCode={P2515_POOL_UPDATE_PROGRAM_DENIED_ERR}）"
            )
            return
        try:
            AssertHttpAndBusinessOk(resp, env, context=f"POST /v2/entitlements/{pool_id}/update")
        except AssertionError as exc:
            errors_out.append(f"POST /v2/entitlements/{pool_id}/update：\n{exc}")

    PostEntitlementsUpdateByPoolId(
        token,
        pool_id,
        payload,
        after_response=_After,
        step_code=step_code,
        step_title=step_title,
    )


def EntitlementsPoolUpdateSuccessOrSkipIfProgramDenied(
    token: str,
    pool_id: str,
    payload: JsonDict,
    *,
    step_code: Optional[str] = None,
    step_title: Optional[str] = None,
) -> None:
    """
    同 ``EntitlementsPoolUpdateSuccess``；若返回 ``500.030.024``（program 禁止按池编辑）则 ``pytest.skip``，
    避免在仅开放读侧或未开 SWAP 写权限的沙箱上误报失败。
    """

    def _After(resp: Response) -> None:
        _st, env, _inner = ParseResponseEnvelope(resp)
        if IsHttpOk(resp) and not IsBusinessSuccess(env) and IsEntitlementPoolUpdateDeniedByProgram(env):
            pytest.skip(
                f"当前 program 禁止按池更新权益（errCode={P2515_POOL_UPDATE_PROGRAM_DENIED_ERR}），"
                f"poolId={pool_id!r}。请换允许按池写入的模板或联系环境管理员。"
            )
        AssertHttpAndBusinessOk(resp, env, context=f"POST /v2/entitlements/{pool_id}/update")

    PostEntitlementsUpdateByPoolId(
        token,
        pool_id,
        payload,
        after_response=_After,
        step_code=step_code,
        step_title=step_title,
    )


def RequireNonEmptyCrossModule(
    entitlements: Mapping[str, Any],
    *,
    hint: str = "请配置含跨模块权益的 program 模板，或设置 DP_P2515_REGISTER_EXTRA_JSON",
) -> List[JsonDict]:
    """若无 crossModule 数据则 ``pytest.skip``。"""
    cross = GetCrossModuleEntitlements(entitlements)
    if not cross:
        pytest.skip(f"PAPI-2515：crossModuleEntitlements 为空，无法继续。{hint}")
    return cross


def RunP2515MainE2EScenario(token: str, steps: AllureHttpScenarioSteps) -> None:
    """
    PAPI-2515 **主链路**编排：注册 → 基线 search → 单品类 ``/v2/entitlements/update`` → search →
    按池 ``/v2/entitlements/{poolId}/update``（可选）→ 两次收尾 search。

    使用 ``P2515E2ESoftAssert`` 跑完全部 HTTP，最后 ``RaiseIfAnyFailure``；前置 programId 缺失则 skip。
    步骤顺序与模块 docstring **主链路**表一致；pytest 用例宜直接调用本函数以保持单一真相源。
    """
    RequireP2515ProgramIdForRegisterOrSkip()
    soft = P2515E2ESoftAssert()

    reg_payload = BuildP2515RegisterPayload()
    membership_id, _exts, _body = RegisterMembershipSuccessDetail(
        token,
        reg_payload,
        after_register_success=lambda body: _CaptureP2515E2EAssertion(
            soft,
            "PAPI-2515-S01：注册响应 data.entitlements（cross / moduleExclusive 契约）",
            lambda: RunP2515CrossModuleAndModuleExclusiveFromInner(
                body,
                context="PAPI-2515-S01-/v2/memberships",
            ),
        ),
        **_HttpStepKw(steps, "注册会籍（P2515 模板）"),
    )

    def _AfterBaselineSearch(ent: Dict[str, Any]) -> None:
        MaybeAttach2515SearchDetails(ent, label="baseline")
        _CaptureP2515E2EAssertion(
            soft,
            "PAPI-2515-S02：cross 结构契约与 summary/pools 聚合",
            lambda: AssertCrossModuleContract(
                GetCrossModuleEntitlements(ent),
                context="PAPI-2515-S02",
            ),
        )

    ent1 = EntitlementsSearchSuccess(
        token,
        membership_id,
        after_entitlements=_AfterBaselineSearch,
        **_HttpStepKw(steps, "entitlements/search（基线）"),
    )
    cross_snapshot = GetCrossModuleEntitlements(ent1)
    RequireNonEmptyCrossModule(ent1)

    mod_body = BuildP2515ModuleExclusiveUpdateBody(membership_id)
    tier_v = mod_body.get("tier")
    tier_int = int(tier_v) if tier_v is not None else None

    def _AfterS03(resp: Response) -> None:
        _st, env, inner = ParseResponseEnvelope(resp)
        try:
            AssertHttpAndBusinessOk(resp, env, context="POST /v2/entitlements/update")
            RunP2515CrossModuleAndModuleExclusiveFromInner(
                inner,
                context="PAPI-2515-S03-/v2/entitlements/update",
            )
        except AssertionError as exc:
            soft.errors.append(
                "PAPI-2515-S03：/v2/entitlements/update HTTP 成功且响应 entitlements 契约\n" + str(exc)
            )

    PostEntitlementsUpdate(
        token,
        mod_body,
        after_response=_AfterS03,
        **_HttpStepKw(steps, "entitlements/update（单品类 module+tier）"),
    )

    def _AfterSearchModuleUpdated(ent: Dict[str, Any]) -> None:
        MaybeAttach2515SearchDetails(ent, label="after_module_update")
        cross2_local = GetCrossModuleEntitlements(ent)
        _CaptureP2515E2EAssertion(
            soft,
            "PAPI-2515-S04：cross 归一化快照一致",
            lambda: AssertNormalizedCrossModuleEqual(
                cross_snapshot,
                cross2_local,
                context="PAPI-2515-S04-cross",
            ),
        )
        _CaptureP2515E2EAssertion(
            soft,
            "PAPI-2515-S04：cross 契约",
            lambda: AssertCrossModuleContract(cross2_local, context="PAPI-2515-S04"),
        )
        _CaptureP2515E2EAssertion(
            soft,
            "PAPI-2515-S04：moduleExclusive 指标增量",
            lambda: AssertModuleExclusiveMetricDelta(
                ent1,
                ent,
                module=mod_body.get("module"),
                tier=tier_int,
                usage_restriction=int(mod_body["usageRestriction"]),
                expect_delta=int(mod_body["quantity"]),
                context="PAPI-2515-S04-moduleExclusive",
            ),
        )

    ent2 = EntitlementsSearchSuccess(
        token,
        membership_id,
        after_entitlements=_AfterSearchModuleUpdated,
        **_HttpStepKw(steps, "entitlements/search（module 更新后）"),
    )
    cross2 = GetCrossModuleEntitlements(ent2)

    plan = BuildP2515PoolUpdatePlan(membership_id, cross2)
    if not plan:
        soft.Record("提示：无可执行 cross 单池更新计划，跳过按池 POST；预期指标按 search 后 cross 现状")
        expected_metrics = CrossModuleGroupMetricsByKey(cross2)
    else:
        metrics_base = CrossModuleGroupMetricsByKey(cross2)
        expected_metrics = ApplyPlannedUpdateToExpectedGroupMetrics(metrics_base, plan)
        for idx, item in enumerate(plan, start=1):
            PostEntitlementsPoolUpdateOrRecord(
                token,
                item.entitlement_pool_id,
                item.body,
                errors_out=soft.errors,
                **_HttpStepKw(
                    steps,
                    f"entitlements/{{poolId}}/update（{idx}/{len(plan)} pool={item.entitlement_pool_id}）",
                ),
            )

    metrics_final: Dict[Tuple[int, ...], Dict[str, int]] = expected_metrics

    def _AfterSearchAllPoolsDone(ent: Dict[str, Any]) -> None:
        cross = GetCrossModuleEntitlements(ent)
        _CaptureP2515E2EAssertion(
            soft,
            "PAPI-2515-S06：cross 契约",
            lambda: AssertCrossModuleContract(cross, context="PAPI-2515-S06"),
        )
        _CaptureP2515E2EAssertion(
            soft,
            "PAPI-2515-S06：summary 与预期一致",
            lambda: AssertCrossModuleSummaryMatchesExpected(
                cross,
                metrics_final,
                context="PAPI-2515-S06",
            ),
        )

    def _AfterSearchFinalConsistency(ent: Dict[str, Any]) -> None:
        cross = GetCrossModuleEntitlements(ent)
        _CaptureP2515E2EAssertion(
            soft,
            "PAPI-2515-S07：cross 契约",
            lambda: AssertCrossModuleContract(cross, context="PAPI-2515-S07"),
        )
        _CaptureP2515E2EAssertion(
            soft,
            "PAPI-2515-S07：summary 与预期一致",
            lambda: AssertCrossModuleSummaryMatchesExpected(
                cross,
                metrics_final,
                context="PAPI-2515-S07",
            ),
        )

    EntitlementsSearchSuccess(
        token,
        membership_id,
        after_entitlements=_AfterSearchAllPoolsDone,
        **_HttpStepKw(steps, "entitlements/search（全部单池更新后）"),
    )

    EntitlementsSearchSuccess(
        token,
        membership_id,
        after_entitlements=_AfterSearchFinalConsistency,
        **_HttpStepKw(steps, "entitlements/search（最终一致性）"),
    )

    soft.RaiseIfAnyFailure()
