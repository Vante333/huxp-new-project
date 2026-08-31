"""
首次会籍商品购买 · P1 全量 Postman Collection v2.1。

在 P0 两条冒烟 E2E 基础上扩展字段级用例（Preview / Create / Payments / Details 负向与变体）。

环境变量：复用 P0 的 ``MP_P0_*`` 鉴权；Environment **351893** 仅保留 ``baseUrl`` / ``x-version``。
业务键（券码、金额、program 等）一律走「全量数据」数据集选行（``pm.variables``），脚本不读 Environment 业务键。

用法（仓库根）::

    python api-testcases/api_tests/apifox-cli/generators/GeneratePostmanCollectionMembershipPurchaseP1.py
"""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Final, List, Mapping, Optional, Sequence, Tuple, Union

import GeneratePostmanCollectionMembershipPurchaseP0 as mp0

JsonObject = Dict[str, Any]


@dataclass(frozen=True)
class ScenarioEnvSpec:
    """单场景/Group 的 Environment 差分清单（导出 CSV 与换测选行）。"""

    scenario_key: str
    group_name: str
    polarity: str  # positive | negative | baseline
    env_keys: Sequence[str]
    notes: str = ""
    # None=按启发式标手工必改；显式 list（可空）=覆盖
    manual_keys: Optional[Sequence[str]] = None


@dataclass(frozen=True)
class StepPurpose:
    """单步测试目的（对齐 P0：PurposeName 中文 + request description）。"""

    name: str
    description: str


@dataclass(frozen=True)
class PendingE2EPurposes:
    """标准待支付 E2E 目的（含 usage details 隔离负向）。"""

    preview: StepPurpose
    create: StepPurpose
    details_before_pay: StepPurpose
    membership_usage_details_reject: StepPurpose
    payments: StepPurpose
    details_after_pay: StepPurpose
    cancel: StepPurpose
    details_after_cancel: StepPurpose


def PurposesProductB() -> PendingE2EPurposes:
    return PendingE2EPurposes(
        preview=StepPurpose(
            TC_TITLE["preview_b_no_coupon"],
            TcDesc("preview_b_no_coupon", "Preview 接口 · autoRenewal=false"),
        ),
        create=StepPurpose(
            TC_TITLE["create_b_no_coupon"],
            TcDesc("create_b_no_coupon", "Create 接口 · status=9 · 保存 orderIdProductB"),
        ),
        details_before_pay=StepPurpose(
            TC_TITLE["details_pending"],
            TcDesc("details_pending", "Create 后、Payments 前"),
        ),
        membership_usage_details_reject=StepPurpose(
            TC_TITLE["regression_ms_usage_details_reject"],
            TcDesc(
                "regression_ms_usage_details_reject",
                "用购买 orderId 打 usage details · 期望查不到会籍购买单",
            ),
        ),
        payments=StepPurpose(
            TC_TITLE["payments_h5"],
            TcDesc("payments_h5", "H5_CASHIER · REDIRECT"),
        ),
        details_after_pay=StepPurpose(
            TC_TITLE["details_pending"],
            TcDesc("details_pending", "Payments 后仍待支付"),
        ),
        cancel=StepPurpose(
            TC_TITLE["e2e_cancel_pending"],
            TcDesc("e2e_cancel_pending", "PATCH /v2/orders"),
        ),
        details_after_cancel=StepPurpose(
            TC_TITLE["e2e_details_after_cancel"],
            TcDesc("e2e_details_after_cancel"),
        ),
    )


def PurposesProductAIntro() -> PendingE2EPurposes:
    return PendingE2EPurposes(
        preview=StepPurpose(
            TC_TITLE["preview_a_intro"],
            TcDesc("preview_a_intro", "Preview 接口"),
        ),
        create=StepPurpose(
            TC_TITLE["create_a_intro"],
            TcDesc("create_a_intro", "Create 接口 · status=9（含应付 0 元）"),
        ),
        details_before_pay=StepPurpose(
            TC_TITLE["details_pending"],
            TcDesc("details_pending", "Create 后"),
        ),
        membership_usage_details_reject=StepPurpose(
            TC_TITLE["regression_ms_usage_details_reject"],
            TcDesc(
                "regression_ms_usage_details_reject",
                "用购买 orderId 打 usage details · 期望查不到会籍购买单",
            ),
        ),
        payments=StepPurpose(
            TC_TITLE["payments_h5"],
            TcDesc("payments_h5", "应付 0 元时期望业务失败"),
        ),
        details_after_pay=StepPurpose(
            TC_TITLE["details_pending"],
            TcDesc("details_pending", "Payments 后"),
        ),
        cancel=StepPurpose(
            TC_TITLE["e2e_cancel_pending"],
            TcDesc("e2e_cancel_pending"),
        ),
        details_after_cancel=StepPurpose(
            TC_TITLE["e2e_details_after_cancel"],
            TcDesc("e2e_details_after_cancel"),
        ),
    )


def PurposesProductANoIntro() -> PendingE2EPurposes:
    return PendingE2EPurposes(
        preview=StepPurpose(
            TC_TITLE["preview_a_no_intro"],
            TcDesc("preview_a_no_intro", "Preview 接口"),
        ),
        create=StepPurpose(
            TC_TITLE["create_a_no_intro"],
            TcDesc("create_a_no_intro", "Create 接口"),
        ),
        details_before_pay=StepPurpose(
            TC_TITLE["details_pending"],
            TcDesc("details_pending"),
        ),
        membership_usage_details_reject=StepPurpose(
            TC_TITLE["regression_ms_usage_details_reject"],
            TcDesc(
                "regression_ms_usage_details_reject",
                "用购买 orderId 打 usage details · 期望查不到会籍购买单",
            ),
        ),
        payments=StepPurpose(
            TC_TITLE["payments_h5"],
            TcDesc("payments_h5"),
        ),
        details_after_pay=StepPurpose(
            TC_TITLE["details_pending"],
            TcDesc("details_pending", "Payments 后"),
        ),
        cancel=StepPurpose(
            TC_TITLE["e2e_cancel_pending"],
            TcDesc("e2e_cancel_pending"),
        ),
        details_after_cancel=StepPurpose(
            TC_TITLE["e2e_details_after_cancel"],
            TcDesc("e2e_details_after_cancel"),
        ),
    )

OUT_NAME: Final[str] = "Membership-Purchase-P1.postman_collection.json"
COLLECTION_DISPLAY_NAME: Final[str] = "Membership Purchase · P1 全量（首次会籍购买）"

# usage 订单查询（非 purchase/details）；用于隔离：购买 orderId 不可被本接口查到。
PATH_MEMBERSHIP_USAGE_DETAILS: Final[str] = "/v2/orders/memberships/details"
# PAPI-3056：取消会籍订阅续费（Apifox api-3566653）
PATH_SUBSCRIPTION_CANCEL: Final[str] = "/v2/memberships/subscriptions/cancellation"
# OAS 示例 16 位 dpid；Create 未回 membershipId 时作归属负向入参（非本单会籍）
DUMMY_MEMBERSHIP_ID: Final[str] = "8888000066668888"
ERR_SUB_CANCEL_NO_ACTIVE: Final[str] = "500.020.034"
ERR_SUB_CANCEL_FAILED: Final[str] = "500.020.035"

# 字段级用例标题（来源：testcases/2026Q3_SP1/首次会籍商品购买API-字段级测试用例-001.md）
# PurposeName 的【目的】与此处字符串完全一致。
TC_TITLE: Final[Dict[str, str]] = {
    # Preview · 商品 B/A
    "preview_b_no_coupon": "不传券选择默认项目配置中的首个商品并按首月原价预览(EUR)",
    "preview_b_auto_renewal_true": "不传券选择商品B但autoRenewal为true回兜底错误",
    "preview_a_no_sub_original": "商品A不支持订阅且autoRenewal为false时按A原价预览（传couponCode）",
    "preview_a_no_sub_ar_true": "商品A不支持订阅但autoRenewal为true时返回兜底错误（传couponCode）",
    "preview_a_sub_off": "商品A支持订阅但autoRenewal为false时按A原价预览（传couponCode）",
    "preview_a_intro": "商品A支持订阅时autoRenewal为true使用阶段价（传couponCode，开启引导期阶段计费，activationMethod=1）",
    "preview_a_no_intro": "商品A支持订阅时autoRenewal为true使用阶段价（传couponCode，未开启引导期阶段计费，activationMethod=2）-原价计算",
    "preview_coupon_not_found": "优惠券不存在Preview按原价且详情为空（传couponCode）",
    "preview_coupon_wrong_type": "非周期优惠券Preview按原价且详情为空（传couponCode）",
    "preview_coupon_expired": "已过期周期优惠券Preview结构符合最终约定（传couponCode）",
    "preview_coupon_ineligible": "有效但不满足条件优惠券保留详情并按原价（传couponCode），例如优惠券未在使用有效期内",
    # Create · 商品 B/A
    "create_b_no_coupon": "不传券选择默认项目配置中的首个商品并按首月原价预览(EUR)",
    "create_b_auto_renewal_true": "不传券选择商品B但autoRenewal为true回兜底错误",
    "create_a_no_sub": "商品A不支持订阅且autoRenewal为false时Create报错（传couponCode）",
    "create_a_no_sub_ar_true": "商品A不支持订阅但autoRenewal为true时Create报错（传couponCode）",
    "create_a_sub_off": "商品A支持订阅但autoRenewal为false时Create报错（传couponCode）",
    "create_a_intro": "商品A支持订阅时autoRenewal为true使用阶段价（传couponCode，开启引导期阶段计费，activationMethod=1）",
    "create_a_no_intro": "商品A支持订阅时autoRenewal为true使用阶段价（传couponCode，未开启引导期阶段计费，activationMethod=2）-原价计算",
    "create_coupon_not_found": "优惠券不存在Create按原价且详情为空（传couponCode）",
    "create_coupon_wrong_type": "非周期优惠券Create按原价且详情为空（传couponCode）",
    "create_coupon_expired": "已过期周期优惠券Create结构符合最终约定（传couponCode）",
    "create_coupon_ineligible": "有效但不满足条件优惠券保留详情并按原价（传couponCode），例如优惠券未在使用有效期内",
    "create_dup_subscription": "已有生效订阅用户重复购买被拒绝",
    "create_email_required": "Create的email必填且clientUserId选填（支持同时入参）",
    # Preview · 字段校验
    "preview_required_body": "Preview必填Body字段缺失或null均拒绝",
    "preview_type_enum": "Preview字段类型与枚举错误均拒绝",
    "preview_email_required": "Preview的email必填且clientUserId选填（支持同时入参）",
    # Create · 字段校验
    "create_required_type": "Create必填字段和类型边界校验",
    # Payments / Details
    "payments_h5": "待支付订单获取H5收银台链接",
    "payments_retry": "再次调用Payments获取新支付链接",
    "payments_missing_field": "Payments必填字段缺失或类型错误均拒绝",
    "details_pending": "待支付订单Details字段形态",
    "details_order_id_required": "Details_orderId必填与类型校验",
    # 回归 · 订单类型隔离
    "regression_ms_usage_details_reject": "membership的订单查询不可以查询到会籍订单",
    # PAPI-3056 · 取消订阅
    "sub_cancel_after_create": "Create后调用取消订阅并校验会籍归属",
    "sub_cancel_required_type": "取消订阅必填字段和类型边界校验",
    "sub_cancel_mismatch": "membershipId与email不匹配Create注册时拒绝",
    # E2E 收尾（用例表无独立 tc，description 注明）
    "e2e_cancel_pending": "E2E收尾·取消待支付订单",
    "e2e_details_after_cancel": "E2E收尾·取消后Details查询",
}


def TcDesc(tc_key: str, extra: str = "") -> str:
    """步骤 description：追溯用例标题 + 可选补充。"""
    title = TC_TITLE[tc_key]
    base = f"追溯用例标题：{title}"
    if extra:
        return f"{base}。{extra}"
    return base


def TcGroupName(tc_key: str) -> str:
    """Apifox/Postman Folder 名 = 字段级用例标题（与步骤【目的】同源）。"""
    return TC_TITLE[tc_key]

# P0 业务变量 + P1 增量（占位；换测改 Apifox Environment）
# 券码/金额/program：以「全量数据」数据集行为准（见 DATASET_ONLY_KEYS）；生成器值写入 CSV 供导入。
P1_EXTRA_BUSINESS_ENV: Final[Dict[str, str]] = {
    "CouponIntroNoRenew": "3UVFFEA89K9V08Y7U37NI4Z13N27OY",
    "CouponIntroNoRenewName": "会籍购买商品_不支持订阅",
    "productASubOffCouponName": "会籍购买商品支持订阅_未开引导",
    "productANoSubProgramId": "2032786406298624",
    "productANoSubProgramName": "会籍购买-商品A无订阅",
    "productANoSubPrice": "10.43",
    "productANoSubPayableAmount": "10.43",
    "productANoSubCurrency": "USD",
    "productASubOffProgramId": "2032786406298624",
    "productASubOffProgramName": "会籍购买-商品A订阅关原价",
    "productASubOffPrice": "10.43",
    "productASubOffPayableAmount": "10.43",
    "productASubOffCurrency": "USD",
    "productANoIntroPayableAmount": "10",
    "productBCurrencyConfigured": "EUR",
    "productBCurrencyUnconfigured": "XXX",
    "productACurrencyConfigured": "USD",
    "productACurrencyUnconfigured": "XXX",
    "CouponExpired": "PLACEHOLDER_EXPIRED",
    "CouponIneligible": "PLACEHOLDER_INELIGIBLE",
    "CouponWrongType": "PLACEHOLDER_WRONG_TYPE",
    "CouponNotFoundCode": "MP_P1_NONEXISTENT_COUPON_XYZ",
    "ExistingActiveProfileEmail": "mp_p1_active_sub@example.com",
    "ExistingActiveProfileClientUserId": "mp_p1_active_sub_cuid",
}

# 仅网关/路由留 Environment；其余业务键一律数据集选行（pm.variables）。
ENV_INFRA_KEYS: Final[frozenset] = frozenset({"baseUrl", "x-version"})

MERGED_BUSINESS_ENV: Final[Dict[str, str]] = {
    **mp0.DEFAULT_BUSINESS_ENV,
    **P1_EXTRA_BUSINESS_ENV,
}

# 业务键（不含 infra）：种子/getEnv/{{}} 强制替换均只认数据集。
DATASET_ONLY_KEYS: Final[Tuple[str, ...]] = tuple(
    k for k in MERGED_BUSINESS_ENV.keys() if k not in ENV_INFRA_KEYS
)


def JsStringLiteral(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def Lines_SeedRuntimeEnvP1() -> List[str]:
    """P1：业务键只取数据集（``pm.variables``）+ 生成器占位；不读不写 Environment。

    - ``baseUrl``：可读 Environment（共用 351893 网关配置）；``x-version`` 只认 Environment，空=生产不传头
    - 鉴权三列：优先勾选的鉴权数据集行；空才回落 ``.env`` 的 ``MP_P0_*``（禁止 .env 覆盖选行）
    - body 内 ``{{业务键}}`` 强制按 variables 替换，避免 Apifox 用旧 Environment 解析
    """
    creds = mp0.AuthCredentials()
    biz_keys_json = json.dumps(list(DATASET_ONLY_KEYS), ensure_ascii=False)
    lines: List[str] = [
        "try {",
        "  function _mpIsPlaceholder(v) {",
        "    var s = String(v || '').trim();",
        "    if (!s) return true;",
        "    return s.indexOf('PLACEHOLDER') === 0 || s.indexOf('FILL_') === 0;",
        "  }",
        "  function _mpFromDataset(name, fallback) {",
        "    // 选行优先级：iterationData（Apifox 全量数据勾选行）→ variables → environment 非占位 → 生成器占位",
        "    var idV = '';",
        "    try { if (pm.iterationData) idV = String(pm.iterationData.get(name) || '').trim(); } catch (eI) {}",
        "    var v = '';",
        "    try { v = String(pm.variables.get(name) || '').trim(); } catch (e0) {}",
        "    var envV = '';",
        "    try { envV = String((pm.environment && pm.environment.get(name)) || '').trim(); } catch (e1) {}",
        "    if (idV && !_mpIsPlaceholder(idV)) return idV;",
        "    if (v && !_mpIsPlaceholder(v)) return v;",
        "    if (envV && !_mpIsPlaceholder(envV)) return envV;",
        "    if (idV) return idV;",
        "    if (v) return v;",
        "    if (envV) return envV;",
        "    return String(fallback || '').trim();",
        "  }",
        "  // 业务键：解析后只写入 variables，并用其强制替换 body {{键}}",
    ]
    for key, value in MERGED_BUSINESS_ENV.items():
        lit = JsStringLiteral(value)
        k_lit = JsStringLiteral(key)
        if key == "x-version":
            continue
        if key in ENV_INFRA_KEYS:
            lines.append("  (function () {")
            lines.append(f"    var _k = {k_lit};")
            lines.append("    var _v = '';")
            lines.append("    try { _v = String((pm.environment && pm.environment.get(_k)) || '').trim(); } catch (eE) {}")
            lines.append("    if (!_v) { try { _v = String(pm.variables.get(_k) || '').trim(); } catch (eV0) {} }")
            lines.append(f"    if (!_v) _v = {lit};")
            lines.append("    try { pm.variables.set(_k, _v); } catch (eV1) {}")
            lines.append("  })();")
        else:
            lines.append("  (function () {")
            lines.append(f"    var _k = {k_lit};")
            lines.append(f"    var _v = _mpFromDataset(_k, {lit});")
            lines.append("    try { pm.variables.set(_k, _v); } catch (eV) {}")
            lines.append("  })();")
    # 鉴权：选行/Auth 已写入的值优先；禁止 .env 回落盖掉勾选行。
    # Apifox 勾选「自动化-鉴权」常注入 Environment；步骤间 pm.variables 可能被清空，
    # 故必须读 collection/env，并把选中值写回 env/globals（与 accessToken 同策略）。
    for key in ("ProgramID", "clientId", "secret"):
        fb = JsStringLiteral(creds.get(key) or "")
        k_lit = JsStringLiteral(key)
        lines.append("  (function () {")
        lines.append(f"    var _k = {k_lit};")
        lines.append("    var _id = ''; try { if (pm.iterationData) _id = String(pm.iterationData.get(_k) || '').trim(); } catch (eI) {}")
        lines.append("    var _v = ''; try { _v = String(pm.variables.get(_k) || '').trim(); } catch (eV0) {}")
        lines.append("    var _c = ''; try { _c = String(pm.collectionVariables.get(_k) || '').trim(); } catch (eC0) {}")
        lines.append("    var _e = ''; try { _e = String((pm.environment && pm.environment.get(_k)) || '').trim(); } catch (eE0) {}")
        lines.append("    var _g = ''; try { _g = String((pm.globals && pm.globals.get(_k)) || '').trim(); } catch (eG0) {}")
        lines.append(f"    var _fb = {fb};")
        # 勾选鉴权行常进 Environment；只跑后续 Group 时 variables 可能仍是旧 .env 值。
        # iterationData → environment → variables → collection → globals → .env 生成回落
        lines.append("    var _pick = _id || _e || _v || _c || _g || _fb;")
        lines.append("    if (_pick) {")
        lines.append("      try { pm.variables.set(_k, _pick); } catch (e1) {}")
        lines.append("      try { pm.collectionVariables.set(_k, _pick); } catch (e2) {}")
        lines.append("      try { if (pm.environment) pm.environment.set(_k, _pick); } catch (e3) {}")
        lines.append("      try { if (pm.globals && typeof pm.globals.set === 'function') pm.globals.set(_k, _pick); } catch (e4) {}")
        lines.append("    }")
        lines.append("  })();")
    lines.extend(mp0.Lines_ApplyXVersionFromEnvironment())
    lines.extend(
        [
            "  // body {{业务键}} / 鉴权占位强制替换（防止 Environment 旧值抢 {{}}）",
            f"  var _bizKeys = {biz_keys_json};",
            "  if (pm.request && pm.request.body && pm.request.body.raw) {",
            "    var _raw = String(pm.request.body.raw);",
            "    for (var _i = 0; _i < (_bizKeys || []).length; _i++) {",
            "      var _bk = String(_bizKeys[_i] || '');",
            "      if (!_bk) continue;",
            "      var _bv = ''; try { _bv = String(pm.variables.get(_bk) || '').trim(); } catch (eB) {}",
            "      if (_bv) { _raw = _raw.split('{{' + _bk + '}}').join(_bv); }",
            "    }",
            "    var _cid = ''; try { _cid = String(pm.variables.get('clientId') || '').trim(); } catch (eC0) {}",
            "    var _sec = ''; try { _sec = String(pm.variables.get('secret') || '').trim(); } catch (eS0) {}",
            "    if (_cid) _raw = _raw.replace(/{{clientId}}/g, _cid);",
            "    if (_sec) _raw = _raw.replace(/{{secret}}/g, _sec);",
            "    // 仅 Auth body（本就含 clientId/secret）按选行覆盖；禁止注入业务 Preview/Create 等 body",
            "    try {",
            "      var _bj = JSON.parse(_raw);",
            "      var _hasCid = Object.prototype.hasOwnProperty.call(_bj, 'clientId');",
            "      var _hasSec = Object.prototype.hasOwnProperty.call(_bj, 'secret');",
            "      if (_hasCid || _hasSec) {",
            "        if (_hasCid && _cid) _bj.clientId = _cid;",
            "        if (_hasSec && _sec) _bj.secret = _sec;",
            "        _raw = JSON.stringify(_bj, null, 2);",
            "      }",
            "    } catch (eJ) {}",
            "    pm.request.body.raw = _raw;",
            "  }",
            "  var _pid = '';",
            "  try { if (pm.iterationData) _pid = String(pm.iterationData.get('ProgramID') || '').trim(); } catch (ePid) {}",
            "  if (!_pid) { try { _pid = String((pm.environment && pm.environment.get('ProgramID')) || '').trim(); } catch (eP2) {} }",
            "  if (!_pid) { try { _pid = String(pm.variables.get('ProgramID') || '').trim(); } catch (eP0) {} }",
            "  if (!_pid) { try { _pid = String(pm.collectionVariables.get('ProgramID') || '').trim(); } catch (eP1) {} }",
            "  if (!_pid) { try { _pid = String((pm.globals && pm.globals.get('ProgramID')) || '').trim(); } catch (eP3) {} }",
            "  if (_pid && pm.request && pm.request.headers && typeof pm.request.headers.upsert === 'function') {",
            "    try { pm.request.headers.upsert({ key: 'X-Program-ID', value: _pid }); } catch (ePH) {}",
            "  }",
            "} catch (eSeed) { console.warn('seed runtime env', eSeed); }",
        ]
    )
    return lines


def RequestItemP1(**kwargs: Any) -> JsonObject:
    """P1 请求：使用 MERGED 种子环境。"""
    item = mp0.RequestItem(**kwargs)
    for ev in item.get("event") or []:
        if ev.get("listen") == "prerequest":
            script = ev.get("script") or {}
            exec_lines = list(script.get("exec") or [])
            # 替换 P0 种子为 P1 合并种子
            new_pre = Lines_SeedRuntimeEnvP1() + list(mp0.Lines_EnsureAuthPrerequest())
            extra = kwargs.get("prerequest_extra")
            if extra:
                new_pre.extend(list(extra))
            ev["script"] = {"exec": new_pre, "type": "text/javascript"}
    return item


def BuildScenarioDescription() -> str:
    b = MERGED_BUSINESS_ENV
    return (
        "由 GeneratePostmanCollectionMembershipPurchaseP1 生成 · Membership Purchase · P1 全量\n"
        "鉴权：运行时勾选「自动化-鉴权」数据集行 → ProgramID/clientId/secret；未勾选回落 .env MP_P0_*。\n"
        "环境：仅 baseUrl / x-version 用 Apifox Environment（351893；与其它套件共用，勿整表清空）。\n"
        "业务变量：全部走「全量数据」数据集选行（pm.variables）；脚本不再读 Environment 业务键。\n"
        "\n"
        "【链路摘要】\n"
        "· 正向 E2E：Preview→Create→subscriptions/cancellation→purchase/details→memberships/details(隔离负向)→Payments→…→Cancel；"
        "B/A 三主 Group + 同级【币种·已配置/未配置】变体 Group（各一条完整 E2E）\n"
        "· 取消订阅：POST /v2/memberships/subscriptions/cancellation（membershipId+email）；"
        "正向挂在 Create 后；Create 若未回 dpid 则用 OAS 示例 16 位做归属校验。"
        "鉴权须会籍模板 Program（非 Retail 商品 Program），见 PAPI-3056\n"
        "· activationMethod（可选，默认 1）：引导期 Group 写死 1=dpid+激活码；未开引导期 Group 写死 2=兑换码；"
        "Preview/Create/币种变体同传；本批仍为待支付链路，不验支付成功后 activation 凭据\n"
        "· 回归隔离：购买 orderId 调 POST /v2/orders/memberships/details 期望 code=-1 且 msg/errCode 非空（不钉精确码）\n"
        "· Preview 字段校验：必填缺失/null（含 email）、类型错误；email 必填且 clientUserId 选填（同组含 Create/purchase）\n"
        "· Create 字段校验：必填缺失/null（含 email）、类型错误 appId/autoRenewal(1)/email\n"
        "· 取消订阅字段校验：必填缺失/null（membershipId/email）、类型/格式；"
        "membershipId 与 email 与 Create 注册不一致 → 500.020.035\n"
        "· Details 字段校验：orderId 缺/null/number/空串\n"
        "· 负向：无订阅/订阅关 autoRenewal=false（Preview valid=false 原价、Create 031）；券与 autoRenewal、Payments 缺 orderId\n"
        "· 排除（本批）：callback、支付成功 activation、已支付取消退款、下游 5xx、分级告警\n"
        "\n"
        "【变量关系 · 数据集选行】\n"
        f"· productBPrice → original/payable（默认 {b['productBPrice']} {b['productBCurrency']}）\n"
        f"· productAPrice / productAPayableAmount → deduction=original−payable（默认 {b['productAPrice']}/{b['productAPayableAmount']}）\n"
        "· CouponIntroValid / CouponIntroValidName → 引导期券\n"
        "· CouponIntroNoRenew / productANoSub* / productASubOff* → 无订阅/订阅关\n"
        "· productANoIntroPayableAmount → 引导期未开时 payable（=原价则 deduction=0）\n"
        "· CouponExpired / CouponIneligible / CouponWrongType → 负向券\n"
        "· CouponNotFoundCode → 不存在券（默认假码，可不改）\n"
        "· ExistingActiveProfileEmail/clientUserId → 重复订阅负向\n"
        "· productBCurrencyConfigured / productBCurrencyUnconfigured → 商品 B 币种入参（已配置=断言入参；未配置=回落 productBCurrency）\n"
        "· productACurrencyConfigured / productACurrencyUnconfigured → 商品 A 币种入参（同上，回落 productACurrency）\n"
        "\n"
        "【换测】\n"
        "只改「全量数据」对应 name 行（见 scenario-group-map.md）；勾选该行再跑对应 Group。\n"
        "Environment 351893 里的业务键（券码/金额等）请手动删掉或留空，避免与数据集混淆。\n"
        "Console 首步会打印「要改的数据集列」与当前值。\n"
        "CSV：api-testcases/api_tests/apifox-cli/datasets/membership_purchase_p1/\n"
        "\n"
        "【业务失败 errCode 映射（已确认）】\n"
        "· Preview 500.020.030：B/A autoRenewal=true 兜底（Unable to preview the order…）\n"
        "· Create 500.020.031：B/A autoRenewal=true；不存在券；无订阅/订阅关且 autoRenewal=false"
        "（Sorry, we’re unable to process your order…）\n"
        "· Create 500.000.702：过期/非周期/有效但不满足条件\n"
        "· 应付 0 元 Create：status 期望 = 9\n"
        "· 取消订阅 500.020.034：无有效订阅计划（No active subscription plan…）\n"
        "· 取消订阅 500.020.035：取消失败兜底（含 membershipId/email 不匹配）\n"
    )


def BodyPreviewCreate(
    *,
    coupon_env: Optional[str] = None,
    auto_renewal: bool,
    email_var: str = "uniqueProfileEmail",
    client_user_id_var: str = "uniqueProfileClientUserId",
    include_email: bool = True,
    include_client_user_id: bool = True,
    currency_env: Optional[str] = None,
    activation_method: Optional[int] = None,
) -> str:
    """构造 Preview/Create 共用 body。

    ``activation_method``：可选；1=dpid+激活码，2=兑换码（不传则省略，服务端默认 1）。
    """
    profile: JsonObject = {}
    if include_email:
        profile["email"] = "{{" + email_var + "}}"
    if include_client_user_id:
        if client_user_id_var == "uniqueProfileClientUserId":
            profile["clientUserId"] = "{{$string.uuid}}"
        else:
            profile["clientUserId"] = "{{" + client_user_id_var + "}}"
    payload: JsonObject = {"appId": 1, "autoRenewal": auto_renewal, "profile": profile}
    if coupon_env:
        payload["couponCode"] = "{{" + coupon_env + "}}"
    if currency_env:
        payload["currency"] = "{{" + currency_env + "}}"
    if activation_method is not None:
        payload["activationMethod"] = int(activation_method)
    return json.dumps(payload, ensure_ascii=False, indent=2)


def Lines_FieldRejected(label: str, *, required_field: Optional[str] = None) -> List[str]:
    """字段契约负向：HTTP 可为 200/400；业务 code=-1；必填缺失时校验 msg 模板。

    负向校验网关常回 HTTP 400，故不断言固定 200（与 P2839 负向一致）。
    """
    reject_title = json.dumps(f"{label}: 字段校验拒绝 | 期望=code=-1")
    lines = [
        "var j = parseJson() || {};",
        f"pm.test({reject_title} + ' | 实际=' + fmtJsonBrief({{ code: j.code, errCode: j.errCode, msg: j.msg, http: pm.response.code }}), function () {{",
        "  pm.expect([200, 400]).to.include(pm.response.code);",
        "  pm.expect(j.code).to.eql(-1);",
        "  pm.expect(String(j.msg || '')).to.be.a('string').and.not.empty;",
        "  pm.expect(String(j.errCode || '')).to.be.a('string').and.not.empty;",
        "});",
    ]
    if required_field:
        expected_msg = (
            f"The required parameter '{required_field}' is missing. Please provide a valid value."
        )
        msg_title = json.dumps(f"{label}: msg 必填缺失模板 | 期望={expected_msg}")
        lines.extend(
            [
                f"pm.test({msg_title} + ' | 实际=' + String(j.msg || ''), function () {{",
                f"  pm.expect(String(j.msg || '')).to.eql({json.dumps(expected_msg)});",
                "});",
            ]
        )
    return lines


def Lines_PreviewFieldRejected(label: str, *, required_field: Optional[str] = None) -> List[str]:
    """兼容别名：同 ``Lines_FieldRejected``。"""
    return Lines_FieldRejected(label, required_field=required_field)


def Lines_FieldRejectedWithErrCode(label: str, err_code: str) -> List[str]:
    """字段/业务负向，并钉死 ``errCode``（已确认码才调用）。"""
    lines = Lines_FieldRejected(label)
    err_title = json.dumps(f"{label}: errCode | 期望={err_code}")
    lines.extend(
        [
            f"pm.test({err_title} + ' | 实际=' + String(j.errCode || ''), function () {{",
            f"  pm.expect(String(j.errCode || '')).to.eql({json.dumps(err_code)});",
            "});",
        ]
    )
    return lines


def Lines_SavePurchaseMembershipId(label: str) -> List[str]:
    """从 Create 响应尽量取出 membershipId，供随后取消订阅使用。"""
    return [
        "var _mid = '';",
        "try {",
        "  if (typeof data === 'object' && data) {",
        "    _mid = String(data.membershipId || '').trim();",
        "    if (!_mid) { var _ex = data.extra || {}; _mid = String(_ex.membershipId || '').trim(); }",
        "    if (!_mid && data.activation) { _mid = String(data.activation.membershipId || '').trim(); }",
        "    if (!_mid) {",
        "      var _act = (data.extra && data.extra.activation) ? data.extra.activation : {};",
        "      _mid = String(_act.membershipId || '').trim();",
        "    }",
        "    if (!_mid) { var _prof = (data.extra || {}).profile || {}; _mid = String(_prof.membershipId || '').trim(); }",
        "  }",
        "} catch (eMid) {}",
        "if (_mid) { setRuntime('purchaseMembershipId', _mid); }",
        "else {",
        f"  assertInfo({json.dumps(label + ': Create未回membershipId')}, '取消订阅用OAS示例16位dpid做归属校验', {{}});",
        "}",
    ]


def Lines_InjectSubscriptionCancelPrerequest() -> List[str]:
    """把 Create 注册的 email / membershipId 写入取消订阅 body；无 dpid 则用 OAS 示例 16 位。"""
    dummy = DUMMY_MEMBERSHIP_ID
    return [
        "try {",
        "  var _mid = ''; var _email = '';",
        "  try { _mid = String(pm.variables.get('purchaseMembershipId') || '').trim(); } catch (e0) {}",
        "  if (!_mid) { try { _mid = String(pm.collectionVariables.get('purchaseMembershipId') || '').trim(); } catch (e1) {} }",
        f"  if (!_mid) {{ _mid = '{dummy}'; }}",
        "  try { _email = String(pm.variables.get('uniqueProfileEmail') || '').trim(); } catch (e2) {}",
        "  if (!_email) { try { _email = String(pm.collectionVariables.get('uniqueProfileEmail') || '').trim(); } catch (e3) {} }",
        "  if (pm.request && pm.request.body && pm.request.body.raw) {",
        "    var raw = String(pm.request.body.raw);",
        "    raw = raw.replace(/\\{\\{purchaseMembershipId\\}\\}/g, _mid);",
        "    if (_email) raw = raw.replace(/\\{\\{uniqueProfileEmail\\}\\}/g, _email);",
        "    pm.request.body.raw = raw;",
        "  }",
        "} catch (eAll) {}",
    ]


def BodySubscriptionCancel(*, membership_id: str, email: str) -> str:
    """取消订阅 JSON body。"""
    return json.dumps(
        {"membershipId": membership_id, "email": email},
        ensure_ascii=False,
        indent=2,
    )


def Lines_SubscriptionCancelAfterCreate(label: str) -> List[str]:
    """Create 后取消订阅：成功则验 subscription 形态；失败则 code=-1 且 errCode/msg 非空。

    待支付 Create 常无生效订阅（034/035），不把 code=0 当作硬前提。
    """
    ok_title = json.dumps(f"{label}: HTTP 可为 200/400")
    fork_title = json.dumps(f"{label}: 取消订阅信封 | 期望=code=0或业务拒绝")
    status_title = json.dumps(f"{label}: subscription.status=2 已取消")
    next_title = json.dumps(f"{label}: nextBillingDate=null")
    cancel_date_title = json.dumps(f"{label}: cancelledDate 非空")
    fail_title = json.dumps(f"{label}: 无有效订阅或归属失败 | 期望=code=-1")
    return [
        "var j = parseJson() || {};",
        f"pm.test({ok_title} + ' | 实际=' + String(pm.response.code), function () {{",
        "  pm.expect([200, 400]).to.include(pm.response.code);",
        "});",
        f"pm.test({fork_title} + ' | 实际=' + fmtJsonBrief({{ code: j.code, errCode: j.errCode, msg: j.msg }}), function () {{",
        "  pm.expect(j).to.be.an('object');",
        "  pm.expect(j.code === 0 || j.code === -1).to.eql(true);",
        "});",
        "if (j.code === 0) {",
        "  var data = j.data || {};",
        "  var sub = data.subscription || {};",
        f"  var expectMid = getEnv('purchaseMembershipId') || '{DUMMY_MEMBERSHIP_ID}';",
        "  if (String(expectMid || '') && expectMid !== '" + DUMMY_MEMBERSHIP_ID + "') {",
        f"    assertCheck('{label}: data.membershipId', expectMid, String(data.membershipId || ''));",
        "  }",
        f"  pm.test({status_title} + ' | 实际=' + fmtJsonBrief(sub.status), function () {{",
        "    pm.expect(String(sub.status)).to.eql('2');",
        "  });",
        f"  pm.test({next_title} + ' | 实际=' + fmtJsonBrief(sub.nextBillingDate), function () {{",
        "    pm.expect(sub.nextBillingDate === null).to.eql(true);",
        "  });",
        f"  pm.test({cancel_date_title} + ' | 实际=' + fmtJsonBrief(sub.cancelledDate), function () {{",
        "    pm.expect(String(sub.cancelledDate || '')).to.be.a('string').and.not.empty;",
        "  });",
        "} else {",
        f"  pm.test({fail_title} + ' | 实际=' + fmtJsonBrief({{ code: j.code, errCode: j.errCode, msg: j.msg }}), function () {{",
        "    pm.expect(j.code).to.eql(-1);",
        "    pm.expect(String(j.msg || '')).to.be.a('string').and.not.empty;",
        "    pm.expect(String(j.errCode || '')).to.be.a('string').and.not.empty;",
        "  });",
        "}",
    ]


def SubscriptionCancelAfterCreateItem(step: str, extra: str = "") -> JsonObject:
    """正向 Create 后的取消订阅步骤。"""
    return RequestItemP1(
        name=mp0.PurposeName(
            TC_TITLE["sub_cancel_after_create"],
            step,
            "POST",
            PATH_SUBSCRIPTION_CANCEL,
        ),
        method="POST",
        url_path=PATH_SUBSCRIPTION_CANCEL,
        body=BodySubscriptionCancel(
            membership_id="{{purchaseMembershipId}}",
            email="{{uniqueProfileEmail}}",
        ),
        headers=mp0.BearerJsonHeaders(),
        description=TcDesc(
            "sub_cancel_after_create",
            extra or "membershipId+email 对齐 Create 注册；无 dpid 则用 OAS 示例 16 位",
        ),
        test_lines=Lines_SubscriptionCancelAfterCreate(step),
        prerequest_extra=Lines_InjectSubscriptionCancelPrerequest(),
    )


def _Lines_OptionalProfileEcho(
    label: str,
    *,
    expect_email: bool,
    expect_client_user_id: bool,
) -> List[str]:
    """profile 回显：已传原样；未传不得伪造非空。"""
    lines = [
        "var prof = extra.profile || {};",
        f"assertCheck('{label}: extra.appId', 1, extra.appId);",
        f"assertCheck('{label}: extra.autoRenewal', false, extra.autoRenewal);",
    ]
    if expect_email:
        lines.append(
            f"assertCheck('{label}: extra.profile.email', getEnv('uniqueProfileEmail'), String(prof.email || ''));"
        )
    else:
        lines.extend(
            [
                f"pm.test('{label}: 未传 email 不得伪造非空 | 期望=空/null | 实际=' + fmtJsonBrief(prof.email), function () {{",
                "  var em = prof.email;",
                "  pm.expect(em === null || em === undefined || em === '').to.eql(true);",
                "});",
            ]
        )
    if expect_client_user_id:
        lines.extend(
            [
                f"pm.test('{label}: extra.profile.clientUserId 为 UUID | 期望=UUID | 实际=' + fmtJsonBrief(prof.clientUserId), function () {{",
                "  var cu = String(prof.clientUserId || '');",
                "  var sent = '';",
                "  try {",
                "    var _raw = (pm.request && pm.request.body && pm.request.body.raw) ? String(pm.request.body.raw) : '';",
                "    var _parsed = JSON.parse(_raw);",
                "    if (_parsed && _parsed.profile && _parsed.profile.clientUserId != null) sent = String(_parsed.profile.clientUserId);",
                "  } catch (eParse) {}",
                "  if (sent && sent.indexOf('{{') < 0) { pm.expect(cu).to.eql(sent); }",
                "  else { pm.expect(cu).to.match(/^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$/); }",
                "});",
            ]
        )
    else:
        lines.extend(
            [
                f"pm.test('{label}: 未传 clientUserId 不得伪造非空 | 期望=空/null | 实际=' + fmtJsonBrief(prof.clientUserId), function () {{",
                "  var cu = prof.clientUserId;",
                "  pm.expect(cu === null || cu === undefined || cu === '').to.eql(true);",
                "});",
            ]
        )
    return lines


def Lines_PreviewProductBOptionalProfile(
    label: str,
    *,
    expect_email: bool,
    expect_client_user_id: bool,
) -> List[str]:
    """Preview 选填 profile：算价对齐商品 B；未传字段不得伪造非空；已传原样回显。"""
    lines = [
        f"var j = assertBizOk('{label}');",
        "var data = j.data || {};",
        "var extra = data.extra || {};",
    ]
    lines.extend(
        _Lines_OptionalProfileEcho(
            label,
            expect_email=expect_email,
            expect_client_user_id=expect_client_user_id,
        )
    )
    lines.extend(
        [
            "var pay = data.payment || {};",
            f"pm.test('{label}: paymentStatus/timeline 为 null | 期望=null | 实际=' + fmtJsonBrief({{ ps: pay.paymentStatus, tl: pay.timeline }}), function () {{",
            "  pm.expect(pay.paymentStatus === null || pay.paymentStatus === undefined).to.eql(true);",
            "  pm.expect(pay.timeline === null || pay.timeline === undefined).to.eql(true);",
            "});",
            f"assertPriceBlock('{label}', pay, {{",
            "  expectCurrency: getEnv('productBCurrency') || 'EUR',",
            "  expectOriginal: getEnv('productBPrice') || '15',",
            "  expectPayable: getEnv('productBPrice') || '15',",
            "  expectDeduction: '0',",
            "  expectPaxType: 'CARDHOLDER',",
            "  expectQuantity: 1,",
            "  expectUnitPrice: getEnv('productBPrice') || '15'",
            "});",
        ]
    )
    return lines


def Lines_CreateProductBOptionalProfile(
    label: str,
    order_var: str,
    *,
    expect_email: bool,
    expect_client_user_id: bool,
) -> List[str]:
    """Create 选填 profile：商品 B 成单；未传字段不得伪造非空；已传原样回显。"""
    lines = [
        f"var j = assertBizOk('{label}');",
        "var data = j.data || {};",
        f"assertCheck('{label}: status=9 待支付', 9, data.status);",
        f"assertCreateOrderMeta('{label}', data);",
        f"setRuntime('{order_var}', data.orderId);",
        "var extra = data.extra || {};",
        f"assertCheck('{label}: extra.programId', getEnv('productBProgramId'), String(extra.programId || ''));",
        f"assertCheck('{label}: extra.programName', getEnv('productBProgramName'), String(extra.programName || ''));",
    ]
    lines.extend(
        _Lines_OptionalProfileEcho(
            label,
            expect_email=expect_email,
            expect_client_user_id=expect_client_user_id,
        )
    )
    lines.extend(
        [
            "var pay = data.payment || {};",
            f"assertCheck('{label}: paymentStatus', 'PENDING_PAYMENT', String(pay.paymentStatus || ''));",
            f"assertPriceBlock('{label}', pay, {{",
            "  expectCurrency: getEnv('productBCurrency') || 'EUR',",
            "  expectOriginal: getEnv('productBPrice') || '15',",
            "  expectPayable: getEnv('productBPrice') || '15',",
            "  expectDeduction: '0',",
            "  expectPaxType: 'CARDHOLDER',",
            "  expectQuantity: 1,",
            "  expectUnitPrice: getEnv('productBPrice') || '15'",
            "});",
        ]
    )
    return lines


def Lines_AssertBizFail(label: str, err_code: str, msg_contains: Optional[str] = None) -> List[str]:
    lines = [
        "var j = parseJson() || {};",
        f"assertHttp('{label}: HTTP', 200);",
        f"pm.test('{label}: 业务失败 | 期望=code=-1 errCode={err_code} | 实际=' + fmtJsonBrief({{ code: j.code, errCode: j.errCode, msg: j.msg }}), function () {{",
        "  pm.expect(j.code).to.eql(-1);",
        f"  pm.expect(String(j.errCode || '')).to.eql('{err_code}');",
    ]
    if msg_contains:
        lines.append(f"  pm.expect(String(j.msg || '')).to.include('{msg_contains}');")
    lines.append("});")
    return lines


def Lines_MembershipUsageDetailsRejectPurchaseOrder(label: str, order_var: str) -> List[str]:
    """购买 orderId 调 usage details：仅断言 code=-1 且 msg/errCode 非空（不钉精确 errCode）。"""
    return [
        "var j = parseJson() || {};",
        (
            f"pm.test('{label}: usage details 不可查会籍购买单 | 期望=code=-1 且 msg/errCode 非空"
            f" | 实际=' + fmtJsonBrief({{ code: j.code, errCode: j.errCode, msg: j.msg, "
            f"http: pm.response.code, orderId: getEnv('{order_var}') }}), function () {{"
        ),
        "  pm.expect([200, 400]).to.include(pm.response.code);",
        "  pm.expect(j.code).to.eql(-1);",
        "  pm.expect(String(j.msg || ''), 'msg 非空').to.be.a('string').and.not.empty;",
        "  pm.expect(String(j.errCode || ''), 'errCode 非空').to.be.a('string').and.not.empty;",
        "});",
    ]


def Lines_PreviewFail030(label: str) -> List[str]:
    """Preview 兜底失败：500.020.030 + Unable to preview…"""
    return Lines_AssertBizFail(
        label,
        "500.020.030",
        "Unable to preview the order at the moment",
    )


def Lines_CreateFail031(label: str) -> List[str]:
    """Create/Purchase 兜底失败：500.020.031 + Sorry, we’re unable to process…"""
    # msg 用 ASCII 子串，避免 we’re 弯引号在 JS 单引号里踩坑
    return Lines_AssertBizFail(
        label,
        "500.020.031",
        "unable to process your order",
    )


def Lines_CreateFail033(label: str) -> List[str]:
    """历史：500.020.033 Auto-renewal is not supported（AR=true 现已改 031）。"""
    return Lines_AssertBizFail(label, "500.020.033", "Auto-renewal is not supported")


def Lines_CreateFail032(label: str) -> List[str]:
    return Lines_AssertBizFail(
        label,
        "500.020.032",
        "An active membership subscription already exists",
    )


def Lines_PreviewInvalidCoupon(
    label: str,
    *,
    coupon_env: str,
    expect_route_b: bool = True,
) -> List[str]:
    """Preview 无效/不适用券：valid=false，按 B 或 A 原价回退。"""
    price_env = "productBPrice" if expect_route_b else "productANoSubPrice"
    currency_env = "productBCurrency" if expect_route_b else "productANoSubCurrency"
    return [
        "var j = assertBizOk('" + label + "');",
        "var data = j.data || {};",
        "var coupon = data.coupon || {};",
        f"assertCheck('{label}: coupon.valid', false, coupon.valid);",
        f"pm.test('{label}: coupon.details 为 null | 期望=null | 实际=' + fmtJsonBrief(coupon.details), function () {{",
        "  pm.expect(coupon.details === null || coupon.details === undefined).to.eql(true);",
        "});",
        f"var price = getEnv('{price_env}') || getEnv('productBPrice') || '15';",
        f"assertPriceBlock('{label}', data.payment || {{}}, {{",
        f"  expectCurrency: getEnv('{currency_env}') || 'EUR',",
        "  expectOriginal: price,",
        "  expectPayable: price,",
        "  expectDeduction: '0',",
        "  expectPaxType: 'CARDHOLDER',",
        "  expectQuantity: 1,",
        "  expectUnitPrice: price",
        "});",
        f"assertCheck('{label}: extra.couponCode', getEnv('{coupon_env}'), String((data.extra || {{}}).couponCode || ''));",
    ]


def Lines_PreviewIneligibleCoupon(label: str) -> List[str]:
    """有效但不满足条件：valid=false，details=null，按 A 原价。"""
    return [
        f"var j = assertBizOk('{label}');",
        "var data = j.data || {};",
        "var coupon = data.coupon || {};",
        f"assertCheck('{label}: coupon.valid', false, coupon.valid);",
        f"pm.test('{label}: coupon.details 为 null | 期望=null | 实际=' + fmtJsonBrief(coupon.details), function () {{",
        "  pm.expect(coupon.details === null || coupon.details === undefined).to.eql(true);",
        "});",
        "var orig = getEnv('productANoSubPrice') || getEnv('productAPrice') || '10.43';",
        f"assertPriceBlock('{label}', data.payment || {{}}, {{",
        "  expectCurrency: getEnv('productANoSubCurrency') || getEnv('productACurrency') || 'USD',",
        "  expectOriginal: orig,",
        "  expectPayable: orig,",
        "  expectDeduction: '0',",
        "  expectPaxType: 'CARDHOLDER',",
        "  expectQuantity: 1,",
        "  expectUnitPrice: orig",
        "});",
    ]


def Lines_PreviewProductAOriginal(
    label: str,
    *,
    coupon_env: str,
    auto_renewal: bool,
    program_id_env: str,
    program_name_env: str,
    price_env: str,
    currency_env: str,
    expect_coupon_valid: bool = True,
    description_env: Optional[str] = None,
) -> List[str]:
    """Preview 按 A 原价。

    expect_coupon_valid=False（无订阅/订阅关）：coupon.valid=false，
    details 为对象（couponType=4、currency/discount=null），payment.currency=null。

    注意：assertCheck 须传 coupon.valid 原值；勿传 coupon.valid === false
    （valid 为 false 时表达式变 true，断言反倒失败）。
    """
    lines = [
        f"var j = assertBizOk('{label}');",
        "var data = j.data || {};",
        "var coupon = data.coupon || {};",
        f"assertCheck('{label}: coupon.valid', {str(expect_coupon_valid).lower()}, coupon.valid);",
    ]
    if expect_coupon_valid:
        lines.extend(
            [
                f"pm.test('{label}: details.currency 为 null | 期望=null | 实际=' + fmtJsonBrief((coupon.details || {{}}).currency), function () {{",
                "  pm.expect((coupon.details || {}).currency === null, 'details.currency 应为 null').to.eql(true);",
                "});",
                f"pm.test('{label}: details.discount 为 null | 期望=null | 实际=' + fmtJsonBrief((coupon.details || {{}}).discount), function () {{",
                "  pm.expect((coupon.details || {}).discount === null || (coupon.details || {}).discount === undefined).to.eql(true);",
                "});",
            ]
        )
    else:
        lines.extend(
            [
                f"pm.test('{label}: details 为对象 | 期望=object | 实际=' + fmtJsonBrief(coupon.details), function () {{",
                "  pm.expect(!!(coupon.details && typeof coupon.details === 'object' && !Array.isArray(coupon.details)), 'details 应为对象').to.eql(true);",
                "});",
                "var details = coupon.details || {};",
                f"assertCheck('{label}: details.couponType', 4, details.couponType);",
                f"pm.test('{label}: details.currency 为 null | 期望=null | 实际=' + fmtJsonBrief(details.currency), function () {{",
                "  pm.expect(details.currency === null, 'details.currency 应为 null').to.eql(true);",
                "});",
                f"pm.test('{label}: details.discount 为 null | 期望=null | 实际=' + fmtJsonBrief(details.discount), function () {{",
                "  pm.expect(details.discount === null || details.discount === undefined).to.eql(true);",
                "});",
            ]
        )
        if description_env:
            lines.extend(
                [
                    f"var _expectDesc = getEnv('{description_env}');",
                    "if (_expectDesc && _expectDesc.indexOf('FILL_') !== 0 && _expectDesc.indexOf('PLACEHOLDER') !== 0) {",
                    f"  assertCheck('{label}: details.description', _expectDesc, String(details.description || ''));",
                    "}",
                ]
            )
    lines.extend(
        [
            "var orig = getEnv('" + price_env + "');",
            f"pm.test('{label}: 金额期望来自数据集/变量 {price_env} 非空 | 期望=非空 | 实际=' + fmtJsonBrief(orig), function () {{",
            "  pm.expect(!!orig, '请勾选全量数据行并填 " + price_env + "').to.eql(true);",
            "});",
            "var pay = data.payment || {};",
        ]
    )
    if not expect_coupon_valid:
        lines.extend(
            [
                f"pm.test('{label}: payment.currency 为 null | 期望=null | 实际=' + fmtJsonBrief(pay.currency), function () {{",
                "  pm.expect(pay.currency === null, 'payment.currency 应为 null').to.eql(true);",
                "});",
                f"assertPriceBlock('{label}', pay, {{",
                "  expectOriginal: orig,",
                "  expectPayable: orig,",
                "  expectDeduction: '0',",
                "  expectPaxType: 'CARDHOLDER',",
                "  expectQuantity: 1,",
                "  expectUnitPrice: orig",
                "});",
            ]
        )
    else:
        lines.extend(
            [
                f"assertPriceBlock('{label}', pay, {{",
                f"  expectCurrency: getEnv('{currency_env}') || 'USD',",
                "  expectOriginal: orig,",
                "  expectPayable: orig,",
                "  expectDeduction: '0',",
                "  expectPaxType: 'CARDHOLDER',",
                "  expectQuantity: 1,",
                "  expectUnitPrice: orig",
                "});",
            ]
        )
    lines.extend(
        [
            "assertExtraEchoRequest('" + label + "', data.extra || {}, {",
            "  expectAppId: 1,",
            f"  expectAutoRenewal: {str(auto_renewal).lower()},",
            f"  expectCouponCode: getEnv('{coupon_env}'),",
            "  expectEmail: getEnv('uniqueProfileEmail'),",
            "  expectClientUserId: '{{$string.uuid}}'",
            "});",
        ]
    )
    return lines



def Lines_CreateProductAVariant(
    label: str,
    order_var: str,
    *,
    coupon_env: Optional[str],
    auto_renewal: bool,
    program_id_env: str,
    program_name_env: str,
    price_env: str,
    payable_env: str,
    currency_env: str,
) -> List[str]:
    coupon_lines = ""
    if coupon_env:
        coupon_lines = f"  expectCouponCode: getEnv('{coupon_env}'),\n"
    return [
        f"var j = assertBizOk('{label}');",
        "var data = j.data || {};",
        f"assertCheck('{label}: status=9 待支付', 9, data.status);",
        "assertCreateOrderMeta('" + label + "', data);",
        f"setRuntime('{order_var}', data.orderId);",
        "var extra = data.extra || {};",
        f"assertCheck('{label}: extra.programId', getEnv('{program_id_env}'), String(extra.programId || ''));",
        f"assertCheck('{label}: extra.programName', getEnv('{program_name_env}'), String(extra.programName || ''));",
        "assertExtraEchoRequest('" + label + "', extra, {",
        "  expectAppId: 1,",
        f"  expectAutoRenewal: {str(auto_renewal).lower()},",
        coupon_lines
        + "  expectEmail: getEnv('uniqueProfileEmail'),",
        "  expectClientUserId: '{{$string.uuid}}'",
        "});",
        f"var orig = getEnv('{price_env}') || '10';",
        f"var payable = getEnv('{payable_env}');",
        "if (payable === '') payable = orig;",
        "var deduction = money2(Number(orig) - Number(payable));",
        "var pay = data.payment || {};",
        f"assertCheck('{label}: paymentStatus', 'PENDING_PAYMENT', String(pay.paymentStatus || ''));",
        f"assertPriceBlock('{label}', pay, {{",
        f"  expectCurrency: getEnv('{currency_env}') || 'USD',",
        "  expectOriginal: orig,",
        "  expectPayable: payable,",
        "  expectDeduction: deduction,",
        "  expectPaxType: 'CARDHOLDER',",
        "  expectQuantity: 1,",
        "  expectUnitPrice: orig",
        "});",
    ]



def Lines_PreviewProductBWithCurrency(label: str, *, currency_env: str) -> List[str]:
    """商品 B Preview：金额沿用 productB*；payment.currency ← ``currency_env``。"""
    return [
        f"var j = assertBizOk('{label}');",
        "var data = j.data || {};",
        "var extra = data.extra || {};",
        f"assertExtraEchoRequest('{label}', extra, {{",
        "  expectAppId: 1,",
        "  expectAutoRenewal: false,",
        "  expectEmail: getEnv('uniqueProfileEmail'),",
        "  expectClientUserId: '{{$string.uuid}}'",
        "});",
        "var pay = data.payment || {};",
        f"pm.test('{label}: paymentStatus/timeline 为 null | 期望=null | 实际=' + fmtJsonBrief({{ ps: pay.paymentStatus, tl: pay.timeline }}), function () {{",
        "  pm.expect(pay.paymentStatus === null || pay.paymentStatus === undefined).to.eql(true);",
        "  pm.expect(pay.timeline === null || pay.timeline === undefined).to.eql(true);",
        "});",
        f"assertPriceBlock('{label}', pay, {{",
        f"  expectCurrency: getEnv('{currency_env}') || 'EUR',",
        "  expectOriginal: getEnv('productBPrice') || '15',",
        "  expectPayable: getEnv('productBPrice') || '15',",
        "  expectDeduction: '0',",
        "  expectPaxType: 'CARDHOLDER',",
        "  expectQuantity: 1,",
        "  expectUnitPrice: getEnv('productBPrice') || '15'",
        "});",
    ]


def Lines_CreateProductBWithCurrency(label: str, order_var: str, *, currency_env: str) -> List[str]:
    """商品 B Create：金额沿用 productB*；payment.currency ← ``currency_env``。"""
    return [
        f"var j = assertBizOk('{label}');",
        "var data = j.data || {};",
        f"assertCheck('{label}: status=9 待支付', 9, data.status);",
        f"assertCreateOrderMeta('{label}', data);",
        f"setRuntime('{order_var}', data.orderId);",
        "var extra = data.extra || {};",
        f"assertCheck('{label}: extra.programId', getEnv('productBProgramId'), String(extra.programId || ''));",
        f"assertCheck('{label}: extra.programName', getEnv('productBProgramName'), String(extra.programName || ''));",
        f"assertExtraEchoRequest('{label}', extra, {{",
        "  expectAppId: 1,",
        "  expectAutoRenewal: false,",
        "  expectEmail: getEnv('uniqueProfileEmail'),",
        "  expectClientUserId: '{{$string.uuid}}'",
        "});",
        "var pay = data.payment || {};",
        f"assertCheck('{label}: paymentStatus', 'PENDING_PAYMENT', String(pay.paymentStatus || ''));",
        f"assertPriceBlock('{label}', pay, {{",
        f"  expectCurrency: getEnv('{currency_env}') || 'EUR',",
        "  expectOriginal: getEnv('productBPrice') || '15',",
        "  expectPayable: getEnv('productBPrice') || '15',",
        "  expectDeduction: '0',",
        "  expectPaxType: 'CARDHOLDER',",
        "  expectQuantity: 1,",
        "  expectUnitPrice: getEnv('productBPrice') || '15'",
        "});",
    ]


def Lines_PreviewProductAWithCurrency(
    label: str,
    *,
    currency_env: str,
    payable_env: str = "productAPayableAmount",
) -> List[str]:
    """商品 A 引导期 Preview：金额沿用 productA*；payment.currency ← ``currency_env``。"""
    return [
        f"var j = assertBizOk('{label}');",
        "var data = j.data || {};",
        "var coupon = data.coupon || {};",
        f"assertCheck('{label}: coupon.valid', true, coupon.valid === true);",
        "var details = coupon.details || {};",
        f"assertCheck('{label}: details.couponType=4 INTRODUCTORY_PRICING', 4, details.couponType);",
        f"assertCheck('{label}: details.description', getEnv('CouponIntroValidName'), String(details.description || ''));",
        f"pm.test('{label}: details.currency 为 null | 期望=null | 实际=' + fmtJsonBrief(details.currency), function () {{",
        "  pm.expect(details.currency === null, 'currency 应为 null').to.eql(true);",
        "});",
        f"pm.test('{label}: details.discount 为 null | 期望=null | 实际=' + fmtJsonBrief(details.discount), function () {{",
        "  pm.expect(details.discount === null, 'discount 应为 null').to.eql(true);",
        "});",
        "var extra = data.extra || {};",
        f"assertExtraEchoRequest('{label}', extra, {{",
        "  expectAppId: 1,",
        "  expectAutoRenewal: true,",
        "  expectCouponCode: getEnv('CouponIntroValid'),",
        "  expectEmail: getEnv('uniqueProfileEmail'),",
        "  expectClientUserId: '{{$string.uuid}}'",
        "});",
        "var pay = data.payment || {};",
        f"pm.test('{label}: paymentStatus/timeline 为 null | 期望=null | 实际=' + fmtJsonBrief({{ ps: pay.paymentStatus, tl: pay.timeline }}), function () {{",
        "  pm.expect(pay.paymentStatus === null || pay.paymentStatus === undefined).to.eql(true);",
        "  pm.expect(pay.timeline === null || pay.timeline === undefined).to.eql(true);",
        "});",
        "var orig = getEnv('productAPrice') || '10';",
        f"var payable = getEnv('{payable_env}');",
        "if (payable === '') payable = '0';",
        "var deduction = money2(Number(orig) - Number(payable));",
        f"assertPriceBlock('{label}', pay, {{",
        f"  expectCurrency: getEnv('{currency_env}') || 'USD',",
        "  expectOriginal: orig,",
        "  expectPayable: payable,",
        "  expectDeduction: deduction,",
        "  expectPaxType: 'CARDHOLDER',",
        "  expectQuantity: 1,",
        "  expectUnitPrice: orig",
        "});",
    ]


def PurposesCurrencyVariant(*, configured: bool) -> PendingE2EPurposes:
    """币种变体 E2E【目的】。"""
    tag = "已配置币种" if configured else "未配置币种回落默认"
    return PendingE2EPurposes(
        preview=StepPurpose(f"正向：{tag}Preview可算价", f"body.currency 参数化 · {tag}"),
        create=StepPurpose(f"正向：{tag}Create可成单", f"body.currency 与 Preview 一致 · {tag}"),
        details_before_pay=StepPurpose(TC_TITLE["details_pending"], f"{tag} · Create 后"),
        membership_usage_details_reject=StepPurpose(
            TC_TITLE["regression_ms_usage_details_reject"],
            f"{tag} · 购买 orderId 不可被 usage details 查到",
        ),
        payments=StepPurpose(TC_TITLE["payments_h5"], f"{tag} · H5"),
        details_after_pay=StepPurpose(TC_TITLE["details_pending"], f"{tag} · Payments 后"),
        cancel=StepPurpose(TC_TITLE["e2e_cancel_pending"], f"{tag} · 收尾"),
        details_after_cancel=StepPurpose(TC_TITLE["e2e_details_after_cancel"], f"{tag}"),
    )


def BuildCurrencyVariantSiblingFolders(
    *,
    parent_group_name: str,
    product: str,
    coupon_env: Optional[str],
    auto_renewal: bool,
    payments_allow_zero: bool,
    program_id_env: str,
    program_name_env: str,
    default_currency_env: str,
    configured_currency_env: str,
    unconfigured_currency_env: str,
    price_env: str,
    payable_env: str,
    deduction_env: str,
    profile_prefix: str,
    prefix_base: str,
    activation_method: Optional[int] = None,
) -> List[JsonObject]:
    """币种变体与主正向 Group **同级**（不嵌套）：已配置 / 未配置各一条完整 E2E。

    Group 名：``【币种·已配置|未配置】{parent_group_name}``，避免三主场景提升后重名。
    """
    variants: List[JsonObject] = []
    for configured, body_cur, expect_cur, tag, prefix_suffix in (
        (
            True,
            configured_currency_env,
            configured_currency_env,
            "已配置",
            "CCFG",
        ),
        (
            False,
            unconfigured_currency_env,
            default_currency_env,
            "未配置",
            "CUNC",
        ),
    ):
        folder_label = f"【币种·{tag}】{parent_group_name}"
        prefix = f"{prefix_base}-{prefix_suffix}"
        order_var = f"orderId{prefix_base}{prefix_suffix}"
        body = BodyPreviewCreate(
            coupon_env=coupon_env,
            auto_renewal=auto_renewal,
            currency_env=body_cur,
            activation_method=activation_method,
        )
        purposes = PurposesCurrencyVariant(configured=configured)
        if product == "B":
            preview_tests = Lines_PreviewProductBWithCurrency(f"{prefix}-PRE", currency_env=expect_cur)
            create_tests = Lines_CreateProductBWithCurrency(
                f"{prefix}-CRT", order_var, currency_env=expect_cur
            )
        elif product == "A_INTRO":
            preview_tests = Lines_PreviewProductAWithCurrency(
                f"{prefix}-PRE",
                currency_env=expect_cur,
                payable_env=payable_env,
            )
            create_tests = Lines_CreateProductAVariant(
                f"{prefix}-CRT",
                order_var,
                coupon_env=coupon_env,
                auto_renewal=auto_renewal,
                program_id_env=program_id_env,
                program_name_env=program_name_env,
                price_env=price_env,
                payable_env=payable_env,
                currency_env=expect_cur,
            )
        else:
            preview_tests = [
                f"var j = assertBizOk('{prefix}-PRE');",
                "var data = j.data || {};",
                "var orig = getEnv('productAPrice') || '10';",
                f"var payable = getEnv('{payable_env}') || orig;",
                "var deduction = money2(Number(orig) - Number(payable));",
                f"assertPriceBlock('{prefix}-PRE', data.payment || {{}}, {{",
                f"  expectCurrency: getEnv('{expect_cur}') || 'USD',",
                "  expectOriginal: orig,",
                "  expectPayable: payable,",
                "  expectDeduction: deduction,",
                "  expectPaxType: 'CARDHOLDER',",
                "  expectQuantity: 1,",
                "  expectUnitPrice: orig",
                "});",
            ]
            create_tests = Lines_CreateProductAVariant(
                f"{prefix}-CRT",
                order_var,
                coupon_env=coupon_env,
                auto_renewal=auto_renewal,
                program_id_env=program_id_env,
                program_name_env=program_name_env,
                price_env=price_env,
                payable_env=payable_env,
                currency_env=expect_cur,
            )
        if configured:
            note = (
                "请求 currency ← {{"
                + body_cur
                + "}}；断言 payment.currency ← {{"
                + expect_cur
                + "}}"
            )
        else:
            note = (
                "请求 currency ← {{"
                + body_cur
                + "}}（未配置）；断言回落 {{"
                + expect_cur
                + "}}"
            )
        variants.append(
            BuildStandardPendingE2E(
                folder_name=folder_label,
                prefix=prefix,
                order_var=order_var,
                preview_body=body,
                create_body=body,
                preview_tests=preview_tests,
                create_tests=create_tests,
                program_id_env=program_id_env,
                program_name_env=program_name_env,
                currency_env=expect_cur,
                price_env=price_env,
                payable_env=payable_env,
                deduction_env=deduction_env,
                auto_renewal=auto_renewal,
                payments_allow_zero=payments_allow_zero,
                profile_prefix=f"{profile_prefix}_{prefix_suffix.lower()}",
                purposes=purposes,
                description=note,
                coupon_env=coupon_env,
                announce_extra_keys=[body_cur, expect_cur],
                announce_fixed_notes=[note],
            )
        )
    return variants


def BuildStandardPendingE2E(
    *,
    folder_name: str,
    prefix: str,
    order_var: str,
    preview_body: str,
    create_body: str,
    preview_tests: Sequence[str],
    create_tests: Sequence[str],
    program_id_env: str,
    program_name_env: str,
    currency_env: str,
    price_env: str,
    payable_env: str,
    deduction_env: str,
    auto_renewal: bool,
    purposes: PendingE2EPurposes,
    payments_allow_zero: bool = False,
    profile_prefix: str = "mp_p1",
    description: str = "",
    coupon_env: Optional[str] = None,
    announce_extra_keys: Optional[Sequence[str]] = None,
    announce_fixed_notes: Optional[Sequence[str]] = None,
    announce_only_keys: Optional[Sequence[str]] = None,
) -> JsonObject:
    """标准正向 E2E：Preview→Create→取消订阅→purchase/details→memberships/details(隔离)→Payments→…→Cancel。"""
    p = purposes
    if announce_only_keys is not None:
        env_keys = [k for k in announce_only_keys if (k or "").strip()]
        notes: List[str] = list(announce_fixed_notes or [])
    else:
        env_keys = []
        if coupon_env:
            env_keys.append(coupon_env)
            if coupon_env == "CouponIntroValid":
                env_keys.append("CouponIntroValidName")
            elif coupon_env == "CouponIntroNoRenew":
                env_keys.append("CouponIntroNoRenewName")
        env_keys.extend(
            [
                program_id_env,
                program_name_env,
                price_env,
                payable_env,
                currency_env,
                "returnUrl",
            ]
        )
        if announce_extra_keys:
            env_keys.extend(list(announce_extra_keys))
        notes = [
            f"autoRenewal={str(auto_renewal).lower()}（脚本写死）",
            f"deduction 断言键={deduction_env}（多数场景用 price−payable 公式）",
        ]
        if coupon_env:
            notes.insert(0, f"请求 couponCode ← {{{{{coupon_env}}}}}")
        else:
            notes.insert(0, "不传 couponCode")
        if announce_fixed_notes:
            notes.extend(list(announce_fixed_notes))
    announce_pre, announce_test = mp0.Lines_AnnounceGroupEnv(
        folder_name,
        env_keys,
        fixed_notes=notes,
    )
    guide_desc = mp0.FormatGroupEnvGuideText(folder_name, env_keys, fixed_notes=notes)
    folder_desc = (description + "\n\n" + guide_desc).strip() if description else guide_desc
    create_tests_all = list(create_tests) + Lines_SavePurchaseMembershipId(f"{prefix}-CRT")
    items: List[JsonObject] = [
        RequestItemP1(
            name=mp0.PurposeName(p.preview.name, f"{prefix}-PRE", "POST", mp0.PATH_PREVIEW),
            method="POST",
            url_path=mp0.PATH_PREVIEW,
            body=preview_body,
            headers=mp0.BearerJsonHeaders(),
            description=(p.preview.description or "") + " · 跑本步看 Console/断言「填写指南」。",
            test_lines=list(announce_test) + list(preview_tests),
            prerequest_extra=list(announce_pre) + list(mp0.Lines_UniqueProfilePrerequest(profile_prefix)),
        ),
        RequestItemP1(
            name=mp0.PurposeName(p.create.name, f"{prefix}-CRT", "POST", mp0.PATH_CREATE),
            method="POST",
            url_path=mp0.PATH_CREATE,
            body=create_body,
            headers=mp0.BearerJsonHeaders(),
            description=p.create.description,
            test_lines=create_tests_all,
            prerequest_extra=mp0.Lines_InjectProfilePrerequest(),
        ),
        SubscriptionCancelAfterCreateItem(
            f"{prefix}-SUBCAN",
            extra="Create 后 · membershipId/email 对齐本次注册",
        ),
        RequestItemP1(
            name=mp0.PurposeName(p.details_before_pay.name, f"{prefix}-DET1", "POST", mp0.PATH_DETAILS),
            method="POST",
            url_path=mp0.PATH_DETAILS,
            body=json.dumps({"orderId": "{{" + order_var + "}}"}, ensure_ascii=False, indent=2),
            headers=mp0.BearerJsonHeaders(),
            description=p.details_before_pay.description,
            test_lines=mp0.Lines_DetailsPending(
                f"{prefix}-DET1",
                order_var,
                program_id_env=program_id_env,
                program_name_env=program_name_env,
                currency_env=currency_env,
                price_env=price_env,
                payable_env=payable_env,
                deduction_env=deduction_env,
                auto_renewal=auto_renewal,
            ),
            prerequest_extra=mp0.Lines_InjectOrderIdPrerequest(order_var),
        ),
        RequestItemP1(
            name=mp0.PurposeName(
                p.membership_usage_details_reject.name,
                f"{prefix}-MS-DET",
                "POST",
                PATH_MEMBERSHIP_USAGE_DETAILS,
            ),
            method="POST",
            url_path=PATH_MEMBERSHIP_USAGE_DETAILS,
            body=json.dumps({"orderId": "{{" + order_var + "}}"}, ensure_ascii=False, indent=2),
            headers=mp0.BearerJsonHeaders(),
            description=p.membership_usage_details_reject.description,
            test_lines=Lines_MembershipUsageDetailsRejectPurchaseOrder(
                f"{prefix}-MS-DET",
                order_var,
            ),
            prerequest_extra=mp0.Lines_InjectOrderIdPrerequest(order_var),
        ),
        RequestItemP1(
            name=mp0.PurposeName(p.payments.name, f"{prefix}-PAY", "POST", mp0.PATH_PAYMENTS),
            method="POST",
            url_path=mp0.PATH_PAYMENTS,
            body=json.dumps(
                {
                    "orderId": "{{" + order_var + "}}",
                    "returnUrl": "{{returnUrl}}",
                    "paymentMethod": "H5_CASHIER",
                },
                ensure_ascii=False,
                indent=2,
            ),
            headers=mp0.BearerJsonHeaders(),
            description=p.payments.description,
            test_lines=mp0.Lines_PaymentsH5(
                f"{prefix}-PAY",
                order_var,
                allow_zero_payable=payments_allow_zero,
            ),
            prerequest_extra=mp0.Lines_InjectOrderIdPrerequest(order_var),
        ),
        RequestItemP1(
            name=mp0.PurposeName(p.details_after_pay.name, f"{prefix}-DET2", "POST", mp0.PATH_DETAILS),
            method="POST",
            url_path=mp0.PATH_DETAILS,
            body=json.dumps({"orderId": "{{" + order_var + "}}"}, ensure_ascii=False, indent=2),
            headers=mp0.BearerJsonHeaders(),
            description=p.details_after_pay.description,
            test_lines=mp0.Lines_DetailsPending(
                f"{prefix}-DET2",
                order_var,
                program_id_env=program_id_env,
                program_name_env=program_name_env,
                currency_env=currency_env,
                price_env=price_env,
                payable_env=payable_env,
                deduction_env=deduction_env,
                auto_renewal=auto_renewal,
            ),
            prerequest_extra=mp0.Lines_InjectOrderIdPrerequest(order_var),
        ),
    ]
    cancel_items = [
        RequestItemP1(
            name=mp0.PurposeName(p.cancel.name, f"{prefix}-CAN", "PATCH", mp0.PATH_CANCEL),
            method="PATCH",
            url_path=mp0.PATH_CANCEL,
            body=json.dumps({"status": 3, "orderId": "{{" + order_var + "}}"}, ensure_ascii=False, indent=2),
            headers=mp0.BearerJsonHeaders(),
            description=p.cancel.description,
            test_lines=mp0.Lines_CancelOrder(f"{prefix}-CAN", order_var),
            prerequest_extra=mp0.Lines_InjectOrderIdPrerequest(order_var),
        ),
        RequestItemP1(
            name=mp0.PurposeName(p.details_after_cancel.name, f"{prefix}-DET3", "POST", mp0.PATH_DETAILS),
            method="POST",
            url_path=mp0.PATH_DETAILS,
            body=json.dumps({"orderId": "{{" + order_var + "}}"}, ensure_ascii=False, indent=2),
            headers=mp0.BearerJsonHeaders(),
            description=p.details_after_cancel.description,
            test_lines=mp0.Lines_DetailsAfterCancel(f"{prefix}-DET3", order_var, f"{prefix}-CAN"),
            prerequest_extra=mp0.Lines_InjectOrderIdPrerequest(order_var),
        ),
    ]
    return mp0.Folder(folder_name, items + cancel_items, description=folder_desc)


def BuildProductAIntroFolderP1() -> Tuple[JsonObject, List[JsonObject]]:
    """P0 商品 A 引导期，Create 强制 status=9；币种变体与主 Group 同级返回。

    activationMethod=1（dpid+激活码）；待支付链路不验支付成功凭据。
    """
    order_var = "orderIdProductA"
    body = BodyPreviewCreate(
        coupon_env="CouponIntroValid",
        auto_renewal=True,
        activation_method=1,
    )
    base = BuildStandardPendingE2E(
        folder_name=TcGroupName("preview_a_intro"),
        prefix="A",
        order_var=order_var,
        preview_body=body,
        create_body=body,
        preview_tests=mp0.Lines_PreviewProductA(),
        create_tests=Lines_CreateProductAVariant(
            "A-CRT",
            order_var,
            coupon_env="CouponIntroValid",
            auto_renewal=True,
            program_id_env="productAProgramId",
            program_name_env="productAProgramName",
            price_env="productAPrice",
            payable_env="productAPayableAmount",
            currency_env="productACurrency",
        ),
        program_id_env="productAProgramId",
        program_name_env="productAProgramName",
        currency_env="productACurrency",
        price_env="productAPrice",
        payable_env="productAPayableAmount",
        deduction_env="productADeduction",
        auto_renewal=True,
        payments_allow_zero=True,
        profile_prefix="mp_a",
        purposes=PurposesProductAIntro(),
        description=(
            "传 CouponIntroValid · autoRenewal=true · activationMethod=1（dpid+激活码）· 引导期 · "
            "E2E 含 Cancel；Create 后挂取消订阅；DET1 后 memberships/details 隔离负向；0 元 Payments 业务失败；Create status=9。"
            "\n· 币种变体见同级【币种·已配置/未配置】Group。"
        ),
        coupon_env="CouponIntroValid",
        announce_fixed_notes=[
            "activationMethod=1（脚本写死，dpid+激活码）",
            "应付 0 时 Create status=9，Payments 可业务失败",
        ],
    )
    currency_siblings = BuildCurrencyVariantSiblingFolders(
        parent_group_name=str(base["name"]),
        product="A_INTRO",
        coupon_env="CouponIntroValid",
        auto_renewal=True,
        payments_allow_zero=True,
        program_id_env="productAProgramId",
        program_name_env="productAProgramName",
        default_currency_env="productACurrency",
        configured_currency_env="productACurrencyConfigured",
        unconfigured_currency_env="productACurrencyUnconfigured",
        price_env="productAPrice",
        payable_env="productAPayableAmount",
        deduction_env="productADeduction",
        profile_prefix="mp_a",
        prefix_base="A",
        activation_method=1,
    )
    return base, currency_siblings


def BuildPositiveE2EFolder() -> JsonObject:
    order_b = "orderIdProductB"
    body_b = BodyPreviewCreate(coupon_env=None, auto_renewal=False)
    folder_b = BuildStandardPendingE2E(
        folder_name=TcGroupName("preview_b_no_coupon"),
        prefix="B",
        order_var=order_b,
        preview_body=body_b,
        create_body=body_b,
        preview_tests=mp0.Lines_PreviewProductB(),
        create_tests=mp0.Lines_CreateProductB(order_b),
        program_id_env="productBProgramId",
        program_name_env="productBProgramName",
        currency_env="productBCurrency",
        price_env="productBPrice",
        payable_env="productBPrice",
        deduction_env="productBDeduction",
        auto_renewal=False,
        profile_prefix="mp_b",
        purposes=PurposesProductB(),
        description=(
            "不传券 · autoRenewal=false · 商品 B · E2E 含 Cancel（对齐 P0 冒烟）；"
            "DET1 后 memberships/details 隔离负向；Create 后挂取消订阅。"
            "\n· 币种变体见同级【币种·已配置/未配置】Group。"
        ),
        coupon_env=None,
    )
    currency_b = BuildCurrencyVariantSiblingFolders(
        parent_group_name=str(folder_b["name"]),
        product="B",
        coupon_env=None,
        auto_renewal=False,
        payments_allow_zero=False,
        program_id_env="productBProgramId",
        program_name_env="productBProgramName",
        default_currency_env="productBCurrency",
        configured_currency_env="productBCurrencyConfigured",
        unconfigured_currency_env="productBCurrencyUnconfigured",
        price_env="productBPrice",
        payable_env="productBPrice",
        deduction_env="productBDeduction",
        profile_prefix="mp_b",
        prefix_base="B",
    )

    body_no_intro = BodyPreviewCreate(
        coupon_env="CouponIntroValid",
        auto_renewal=True,
        activation_method=2,
    )
    folder_no_intro = BuildStandardPendingE2E(
        folder_name=TcGroupName("preview_a_no_intro"),
        prefix="ANI",
        order_var="orderIdANoIntro",
        preview_body=body_no_intro,
        create_body=body_no_intro,
        preview_tests=[
            "var j = assertBizOk('ANI-PRE');",
            "var data = j.data || {};",
            "var orig = getEnv('productAPrice') || '10';",
            "var payable = getEnv('productANoIntroPayableAmount') || orig;",
            "var deduction = money2(Number(orig) - Number(payable));",
            "assertPriceBlock('ANI-PRE', data.payment || {}, {",
            "  expectCurrency: getEnv('productACurrency') || 'USD',",
            "  expectOriginal: orig,",
            "  expectPayable: payable,",
            "  expectDeduction: deduction,",
            "  expectPaxType: 'CARDHOLDER',",
            "  expectQuantity: 1,",
            "  expectUnitPrice: orig",
            "});",
        ],
        create_tests=Lines_CreateProductAVariant(
            "ANI-CRT",
            "orderIdANoIntro",
            coupon_env="CouponIntroValid",
            auto_renewal=True,
            program_id_env="productAProgramId",
            program_name_env="productAProgramName",
            price_env="productAPrice",
            payable_env="productANoIntroPayableAmount",
            currency_env="productACurrency",
        ),
        program_id_env="productAProgramId",
        program_name_env="productAProgramName",
        currency_env="productACurrency",
        price_env="productAPrice",
        payable_env="productANoIntroPayableAmount",
        deduction_env="productADeduction",
        auto_renewal=True,
        payments_allow_zero=False,
        profile_prefix="mp_ani",
        purposes=PurposesProductANoIntro(),
        description=(
            "CouponIntroValid + autoRenewal=true + activationMethod=2（兑换码）但未开引导期 · "
            "payable=productANoIntroPayableAmount；DET1 后 memberships/details 隔离负向。"
            "\n· 币种变体见同级【币种·已配置/未配置】Group。"
        ),
        coupon_env="CouponIntroValid",
        announce_only_keys=["productANoIntroPayableAmount"],
        announce_fixed_notes=[
            "activationMethod=2（脚本写死，兑换码）",
            "通常 = productAPrice（原价）",
        ],
    )
    currency_no_intro = BuildCurrencyVariantSiblingFolders(
        parent_group_name=str(folder_no_intro["name"]),
        product="A_NO_INTRO",
        coupon_env="CouponIntroValid",
        auto_renewal=True,
        payments_allow_zero=False,
        program_id_env="productAProgramId",
        program_name_env="productAProgramName",
        default_currency_env="productACurrency",
        configured_currency_env="productACurrencyConfigured",
        unconfigured_currency_env="productACurrencyUnconfigured",
        price_env="productAPrice",
        payable_env="productANoIntroPayableAmount",
        deduction_env="productADeduction",
        profile_prefix="mp_ani",
        prefix_base="ANI",
        activation_method=2,
    )

    order_retry = "orderIdPayRetry"
    body_retry = BodyPreviewCreate(coupon_env=None, auto_renewal=False)
    pr_keys = ["productBProgramId", "productBPrice", "productBCurrency", "returnUrl"]
    pr_notes = ["无券造单后 Payments×2", "returnUrl 影响收银台回跳"]
    pr_announce_pre, pr_announce_test = mp0.Lines_AnnounceGroupEnv(
        TcGroupName("payments_retry"),
        pr_keys,
        fixed_notes=pr_notes,
    )
    folder_pay_retry = mp0.Folder(
        TcGroupName("payments_retry"),
        [
            RequestItemP1(
                name=mp0.PurposeName(
                    TC_TITLE["create_b_no_coupon"],
                    "PR-CRT",
                    "POST",
                    mp0.PATH_CREATE,
                ),
                method="POST",
                url_path=mp0.PATH_CREATE,
                body=body_retry,
                headers=mp0.BearerJsonHeaders(),
                description=TcDesc("create_b_no_coupon", "造数 orderIdPayRetry 供双次取链 · 跑本步看填写指南"),
                test_lines=list(pr_announce_test)
                + list(mp0.Lines_CreateProductB(order_retry))
                + Lines_SavePurchaseMembershipId("PR-CRT"),
                prerequest_extra=list(pr_announce_pre) + list(mp0.Lines_UniqueProfilePrerequest("mp_pr")),
            ),
            SubscriptionCancelAfterCreateItem("PR-SUBCAN", extra="Payments 再取链造数 Create 后取消订阅"),
            RequestItemP1(
                name=mp0.PurposeName(
                    TC_TITLE["payments_h5"],
                    "PR-PAY1",
                    "POST",
                    mp0.PATH_PAYMENTS,
                ),
                method="POST",
                url_path=mp0.PATH_PAYMENTS,
                body=json.dumps(
                    {
                        "orderId": "{{" + order_retry + "}}",
                        "returnUrl": "{{returnUrl}}",
                        "paymentMethod": "H5_CASHIER",
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                headers=mp0.BearerJsonHeaders(),
                description=TcDesc("payments_h5", "首次取链 · 保存 url/validUntil"),
                test_lines=mp0.Lines_PaymentsH5("PR-PAY1", order_retry, allow_zero_payable=False)
                + [
                    "var j1 = parseJson() || {};",
                    "var d1 = (j1.data !== undefined && j1.data !== null) ? j1.data : j1;",
                    "var a1 = d1.paymentAction || {};",
                    "setRuntime('payRetryUrl1', a1.url || '');",
                    "setRuntime('payRetryValidUntil1', String(a1.validUntil || ''));",
                ],
                prerequest_extra=mp0.Lines_InjectOrderIdPrerequest(order_retry),
            ),
            RequestItemP1(
                name=mp0.PurposeName(
                    TC_TITLE["payments_retry"],
                    "PR-PAY2",
                    "POST",
                    mp0.PATH_PAYMENTS,
                ),
                method="POST",
                url_path=mp0.PATH_PAYMENTS,
                body=json.dumps(
                    {
                        "orderId": "{{" + order_retry + "}}",
                        "returnUrl": "{{returnUrl}}",
                        "paymentMethod": "H5_CASHIER",
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                headers=mp0.BearerJsonHeaders(),
                description=TcDesc("payments_retry", "url/validUntil 应与首次不完全相同"),
                test_lines=[
                    "var j2 = parseJson() || {};",
                    "assertHttp('PR-PAY2: HTTP', 200);",
                    "pm.test('PR-PAY2: 业务成功 | 期望=code=0', function () { pm.expect(isBusinessSuccess(j2)).to.eql(true); });",
                    "var d2 = (j2.data !== undefined && j2.data !== null) ? j2.data : j2;",
                    "var a2 = d2.paymentAction || {};",
                    "var u1 = getEnv('payRetryUrl1');",
                    "var v1 = getEnv('payRetryValidUntil1');",
                    "pm.test('PR-PAY2: 新 url 与首次不完全相同 | 期望=不同 | 实际=' + fmtJsonBrief({ u1: u1, u2: a2.url }), function () {",
                    "  pm.expect(String(a2.url || '') !== String(u1 || '') || String(a2.validUntil || '') !== String(v1 || '')).to.eql(true);",
                    "});",
                ],
                prerequest_extra=mp0.Lines_InjectOrderIdPrerequest(order_retry),
            ),
        ],
        description=TcDesc("payments_retry")
        + "\n\n"
        + mp0.FormatGroupEnvGuideText(TcGroupName("payments_retry"), pr_keys, fixed_notes=pr_notes),
    )

    folder_a_intro, currency_a_intro = BuildProductAIntroFolderP1()
    return mp0.Folder(
        "会籍商品购买·正向E2E",
        [
            folder_b,
            *currency_b,
            folder_a_intro,
            *currency_a_intro,
            folder_no_intro,
            *currency_no_intro,
            folder_pay_retry,
        ],
        description=(
            "子 Group 名=字段级用例标题；步骤【目的】同源。"
            "币种变体【币种·已配置/未配置】与对应主场景同级（不嵌套）。"
            "email 必填见 Preview字段校验同组（含 Create）。"
        ),
    )


def BuildNegativeBusinessScenariosFolder() -> JsonObject:
    """负向：一场景一 Group，Preview 与 Create 同组（步骤序 Preview→Create）。"""

    def neg_preview_step(
        tc_key: str,
        step: str,
        body: str,
        tests: Sequence[str],
        profile_prefix: str,
        extra: str = "",
        announce_keys: Optional[Sequence[str]] = None,
        announce_notes: Optional[Sequence[str]] = None,
    ) -> JsonObject:
        label = TcGroupName(tc_key)
        keys = list(announce_keys or [])
        notes = list(announce_notes or [])
        announce_pre: List[str] = []
        announce_test: List[str] = []
        if keys or notes:
            announce_pre, announce_test = mp0.Lines_AnnounceGroupEnv(
                label,
                keys,
                fixed_notes=notes,
            )
        return RequestItemP1(
            name=mp0.PurposeName(TC_TITLE[tc_key], step, "POST", mp0.PATH_PREVIEW),
            method="POST",
            url_path=mp0.PATH_PREVIEW,
            body=body,
            headers=mp0.BearerJsonHeaders(),
            description=TcDesc(tc_key, (extra + " · 跑本步看填写指南").strip(" ·") if extra else "跑本步看填写指南"),
            test_lines=list(announce_test) + list(tests),
            prerequest_extra=list(announce_pre) + list(mp0.Lines_UniqueProfilePrerequest(profile_prefix)),
        )

    def neg_create_step(
        tc_key: str,
        step: str,
        body: str,
        tests: Sequence[str],
        profile_prefix: str,
        extra: str = "",
        profile_extra: Optional[Sequence[str]] = None,
        announce_keys: Optional[Sequence[str]] = None,
        announce_notes: Optional[Sequence[str]] = None,
    ) -> JsonObject:
        label = TcGroupName(tc_key)
        announce_pre: List[str] = []
        announce_test: List[str] = []
        if announce_keys or announce_notes:
            announce_pre, announce_test = mp0.Lines_AnnounceGroupEnv(
                label,
                list(announce_keys or []),
                fixed_notes=list(announce_notes or []),
            )
        pre: List[str] = list(announce_pre) + list(mp0.Lines_UniqueProfilePrerequest(profile_prefix))
        if profile_extra:
            pre.extend(list(profile_extra))
        else:
            pre.extend(mp0.Lines_InjectProfilePrerequest())
        hint = (extra + " · 跑本步看填写指南").strip(" ·") if (announce_keys or announce_notes) else extra
        return RequestItemP1(
            name=mp0.PurposeName(TC_TITLE[tc_key], step, "POST", mp0.PATH_CREATE),
            method="POST",
            url_path=mp0.PATH_CREATE,
            body=body,
            headers=mp0.BearerJsonHeaders(),
            description=TcDesc(tc_key, hint) if hint else TcDesc(tc_key),
            test_lines=list(announce_test) + list(tests),
            prerequest_extra=pre,
        )

    def scenario_group(group_title_key: str, steps: Sequence[JsonObject], note: str = "") -> JsonObject:
        desc = TcDesc(group_title_key, note) if note else TcDesc(group_title_key)
        return mp0.Folder(TcGroupName(group_title_key), list(steps), description=desc)

    dup_profile_extra = [
        "try {",
        "  var em = getEnv('ExistingActiveProfileEmail');",
        "  var cu = getEnv('ExistingActiveProfileClientUserId');",
        "  if (em) { pm.variables.set('existingActiveProfileEmail', em); pm.collectionVariables.set('existingActiveProfileEmail', em); }",
        "  if (cu) { pm.variables.set('existingActiveProfileClientUserId', cu); pm.collectionVariables.set('existingActiveProfileClientUserId', cu); }",
        "} catch (eProf) {}",
    ]

    items: List[JsonObject] = [
        scenario_group(
            "preview_b_auto_renewal_true",
            [
                neg_preview_step(
                    "preview_b_auto_renewal_true",
                    "NG-PB-AR",
                    BodyPreviewCreate(coupon_env=None, auto_renewal=True),
                    Lines_PreviewFail030("NG-PB-AR"),
                    "ng_b_ar",
                    "Preview · 期望 500.020.030",
                    announce_keys=["productBProgramId", "productBPrice", "productBCurrency"],
                    announce_notes=["不传券", "autoRenewal=true → Preview 030 / Create 031"],
                ),
                neg_create_step(
                    "create_b_auto_renewal_true",
                    "NG-CB-AR",
                    BodyPreviewCreate(coupon_env=None, auto_renewal=True),
                    Lines_CreateFail031("NG-CB-AR"),
                    "ng_b_ar",
                    "Create · 期望 500.020.031",
                ),
            ],
            "同场景 Preview→Create：Preview 030 / Create 031",
        ),
        scenario_group(
            "preview_a_no_sub_ar_true",
            [
                neg_preview_step(
                    "preview_a_no_sub_ar_true",
                    "NG-PA-AR",
                    BodyPreviewCreate(coupon_env="CouponIntroNoRenew", auto_renewal=True),
                    Lines_PreviewFail030("NG-PA-AR"),
                    "ng_a_ar",
                    "Preview · 期望 500.020.030",
                    announce_keys=["CouponIntroNoRenew", "productANoSubProgramId", "productANoSubPrice"],
                    announce_notes=["无订阅商品 + autoRenewal=true → Preview 030 / Create 031"],
                ),
                neg_create_step(
                    "create_a_no_sub_ar_true",
                    "NG-CA-AR",
                    BodyPreviewCreate(coupon_env="CouponIntroNoRenew", auto_renewal=True),
                    Lines_CreateFail031("NG-CA-AR"),
                    "ng_a_ar",
                    "Create · 期望 500.020.031",
                ),
            ],
            "Group 名取 Preview 用例标题；Create 用例标题见步骤【目的】；Preview 030 / Create 031",
        ),
        scenario_group(
            "preview_a_no_sub_original",
            [
                neg_preview_step(
                    "preview_a_no_sub_original",
                    "NG-ANS-PRE",
                    BodyPreviewCreate(coupon_env="CouponIntroNoRenew", auto_renewal=False),
                    Lines_PreviewProductAOriginal(
                        "NG-ANS-PRE",
                        coupon_env="CouponIntroNoRenew",
                        auto_renewal=False,
                        program_id_env="productANoSubProgramId",
                        program_name_env="productANoSubProgramName",
                        price_env="productANoSubPrice",
                        currency_env="productANoSubCurrency",
                        expect_coupon_valid=False,
                        description_env="CouponIntroNoRenewName",
                    ),
                    "ng_ans",
                    "Preview · 原价成功（coupon.valid=false，details 对象）",
                    announce_keys=[
                        "CouponIntroNoRenew",
                        "CouponIntroNoRenewName",
                        "productANoSubProgramId",
                        "productANoSubPrice",
                    ],
                    announce_notes=[
                        "须勾选数据集行 neg_a_no_sub_ar_false 或 _FULL_SUITE",
                        "券码/原价/券名读数据集：CouponIntroNoRenew、productANoSubPrice、CouponIntroNoRenewName",
                        "coupon.valid=false；details={couponType:4, description, currency:null, discount:null}",
                        "Create 期望 500.020.031（Sorry）",
                    ],
                ),
                neg_create_step(
                    "create_a_no_sub",
                    "NG-ANS-CRT",
                    BodyPreviewCreate(coupon_env="CouponIntroNoRenew", auto_renewal=False),
                    Lines_AssertBizFail(
                        "NG-ANS-CRT",
                        "500.020.031",
                        "Sorry",
                    ),
                    "ng_ans",
                    "Create · 期望 500.020.031",
                ),
            ],
            "Preview 原价 OK（valid=false）→ Create 拒绝（500.020.031）",
        ),
        scenario_group(
            "preview_a_sub_off",
            [
                neg_preview_step(
                    "preview_a_sub_off",
                    "NG-ASO-PRE",
                    BodyPreviewCreate(coupon_env="CouponIntroNoRenew", auto_renewal=False),
                    Lines_PreviewProductAOriginal(
                        "NG-ASO-PRE",
                        coupon_env="CouponIntroNoRenew",
                        auto_renewal=False,
                        program_id_env="productASubOffProgramId",
                        program_name_env="productASubOffProgramName",
                        price_env="productASubOffPrice",
                        currency_env="productASubOffCurrency",
                        expect_coupon_valid=False,
                        description_env="productASubOffCouponName",
                    ),
                    "ng_aso",
                    "Preview · 原价成功（coupon.valid=false，details 对象）",
                    announce_keys=[
                        "CouponIntroNoRenew",
                        "productASubOffCouponName",
                        "productASubOffProgramId",
                        "productASubOffPrice",
                    ],
                    announce_notes=[
                        "须勾选数据集行 neg_a_sub_off_ar_false 或 _FULL_SUITE",
                        "券码/原价/券名读数据集：CouponIntroNoRenew、productASubOffPrice、productASubOffCouponName",
                        "coupon.valid=false；details={couponType:4, description, currency:null, discount:null}",
                        "Create 期望 500.020.031（Sorry）",
                    ],
                ),
                neg_create_step(
                    "create_a_sub_off",
                    "NG-ASO-CRT",
                    BodyPreviewCreate(coupon_env="CouponIntroNoRenew", auto_renewal=False),
                    Lines_AssertBizFail(
                        "NG-ASO-CRT",
                        "500.020.031",
                        "Sorry",
                    ),
                    "ng_aso",
                    "Create · 期望 500.020.031",
                ),
            ],
            "Preview 原价 OK（valid=false）→ Create 拒绝（500.020.031）",
        ),
        scenario_group(
            "preview_coupon_not_found",
            [
                neg_preview_step(
                    "preview_coupon_not_found",
                    "NG-PV-NF",
                    BodyPreviewCreate(coupon_env="CouponNotFoundCode", auto_renewal=False),
                    Lines_PreviewInvalidCoupon("NG-PV-NF", coupon_env="CouponNotFoundCode", expect_route_b=True),
                    "ng_cpn_nf",
                    "",
                    announce_keys=["CouponNotFoundCode", "productBPrice", "productBCurrency"],
                    announce_notes=["假券码默认可不改", "Preview 按原价回退；Create 期望 500.020.031"],
                ),
                neg_create_step(
                    "create_coupon_not_found",
                    "NG-CC-NF",
                    BodyPreviewCreate(coupon_env="CouponNotFoundCode", auto_renewal=False),
                    Lines_AssertBizFail("NG-CC-NF", "500.020.031", "Sorry"),
                    "ng_cpn_nf",
                    "Create · 期望 500.020.031",
                ),
            ],
            "同场景 Preview→Create",
        ),
        scenario_group(
            "preview_coupon_expired",
            [
                neg_preview_step(
                    "preview_coupon_expired",
                    "NG-PV-EX",
                    BodyPreviewCreate(coupon_env="CouponExpired", auto_renewal=False),
                    Lines_PreviewInvalidCoupon("NG-PV-EX", coupon_env="CouponExpired", expect_route_b=True),
                    "ng_cpn_ex",
                    "",
                    announce_keys=["CouponExpired", "productBPrice", "productBCurrency"],
                    announce_notes=["填沙箱已过期券码", "Create 期望 500.000.702"],
                ),
                neg_create_step(
                    "create_coupon_expired",
                    "NG-CC-EX",
                    BodyPreviewCreate(coupon_env="CouponExpired", auto_renewal=False),
                    Lines_AssertBizFail("NG-CC-EX", "500.000.702", "not applicable"),
                    "ng_cpn_ex",
                    "Create · 期望 500.000.702",
                ),
            ],
            "同场景 Preview→Create",
        ),
        scenario_group(
            "preview_coupon_wrong_type",
            [
                neg_preview_step(
                    "preview_coupon_wrong_type",
                    "NG-PV-WT",
                    BodyPreviewCreate(coupon_env="CouponWrongType", auto_renewal=False),
                    Lines_PreviewInvalidCoupon("NG-PV-WT", coupon_env="CouponWrongType", expect_route_b=True),
                    "ng_cpn_wt",
                    "",
                    announce_keys=["CouponWrongType", "productBPrice", "productBCurrency"],
                    announce_notes=["填非周期优惠券", "Create 期望 500.000.702"],
                ),
                neg_create_step(
                    "create_coupon_wrong_type",
                    "NG-CC-WT",
                    BodyPreviewCreate(coupon_env="CouponWrongType", auto_renewal=False),
                    Lines_AssertBizFail("NG-CC-WT", "500.000.702", "not applicable"),
                    "ng_cpn_wt",
                    "Create · 期望 500.000.702",
                ),
            ],
            "同场景 Preview→Create",
        ),
        scenario_group(
            "preview_coupon_ineligible",
            [
                neg_preview_step(
                    "preview_coupon_ineligible",
                    "NG-PV-IN",
                    BodyPreviewCreate(coupon_env="CouponIneligible", auto_renewal=False),
                    Lines_PreviewIneligibleCoupon("NG-PV-IN"),
                    "ng_cpn_in",
                    "",
                    announce_keys=[
                        "CouponIneligible",
                        "productANoSubPrice",
                        "productANoSubCurrency",
                        "productAPrice",
                    ],
                    announce_notes=[
                        "autoRenewal=false（脚本写死）",
                        "填有效但不满足条件的券",
                        "Create 期望 500.000.702",
                    ],
                ),
                neg_create_step(
                    "create_coupon_ineligible",
                    "NG-CC-IN",
                    BodyPreviewCreate(coupon_env="CouponIneligible", auto_renewal=False),
                    Lines_AssertBizFail("NG-CC-IN", "500.000.702", "not applicable"),
                    "ng_cpn_in",
                    "Create · 期望 500.000.702",
                ),
            ],
            "同场景 Preview→Create",
        ),
        scenario_group(
            "create_dup_subscription",
            [
                neg_create_step(
                    "create_dup_subscription",
                    "NG-CC-DUP",
                    BodyPreviewCreate(
                        coupon_env=None,
                        auto_renewal=False,
                        email_var="existingActiveProfileEmail",
                        client_user_id_var="existingActiveProfileClientUserId",
                    ),
                    Lines_CreateFail032("NG-CC-DUP"),
                    "ng_dup",
                    "期望 500.020.032",
                    profile_extra=dup_profile_extra,
                    announce_keys=["ExistingActiveProfileEmail", "ExistingActiveProfileClientUserId"],
                    announce_notes=["填沙箱已有生效订阅用户", "期望 Create 500.020.032"],
                ),
            ],
            "仅 Create（用例表无 Preview 步骤）",
        ),
    ]
    return mp0.Folder(
        "会籍商品购买·负向场景",
        items,
        description="一场景一 Group；含 Preview+Create 的按 Preview→Create 顺序同组。email 必填负向见 Preview字段校验同组。",
    )


def BuildPreviewFieldValidationFolder() -> JsonObject:
    """Preview 字段校验：必填缺失/null、类型错误、email 必填且 clientUserId 选填。

    步骤【目的】按子场景细化（缺键/null/类型/仅 email 等），Group 名仍用用例标题。
    """
    profile_ok: JsonObject = {
        "email": "{{uniqueProfileEmail}}",
        "clientUserId": "{{$string.uuid}}",
    }

    def preview_step(
        tc_key: str,
        step: str,
        purpose: str,
        body_obj: JsonObject,
        tests: Sequence[str],
        profile_prefix: str,
        *,
        announce: bool = False,
        extra: str = "",
    ) -> JsonObject:
        announce_pre: List[str] = []
        announce_test: List[str] = []
        if announce:
            announce_pre, announce_test = mp0.Lines_AnnounceGroupEnv(
                TcGroupName(tc_key),
                ["productBProgramId", "productBProgramName", "productBPrice", "productBCurrency"],
                fixed_notes=["autoRenewal=false", "金额断言对齐商品 B", "Preview 与 Create 同规则"],
            )
        desc = TcDesc(tc_key, f"{extra} · 追溯用例：{TC_TITLE[tc_key]}" if extra else f"追溯用例：{TC_TITLE[tc_key]}")
        return RequestItemP1(
            name=mp0.PurposeName(purpose, step, "POST", mp0.PATH_PREVIEW),
            method="POST",
            url_path=mp0.PATH_PREVIEW,
            body=json.dumps(body_obj, ensure_ascii=False, indent=2),
            headers=mp0.BearerJsonHeaders(),
            description=desc,
            test_lines=list(announce_test) + list(tests),
            prerequest_extra=list(announce_pre) + list(mp0.Lines_UniqueProfilePrerequest(profile_prefix)),
        )

    required_steps = [
        preview_step(
            "preview_required_body",
            "NG-PV-REQ-APP",
            "负向：Preview缺appId拒绝",
            {"autoRenewal": False, "profile": profile_ok},
            Lines_PreviewFieldRejected("NG-PV-REQ-APP", required_field="appId"),
            "mp_pv_req_app",
            extra="缺 appId",
        ),
        preview_step(
            "preview_required_body",
            "NG-PV-REQ-APPN",
            "负向：Preview的appId为null拒绝",
            {"appId": None, "autoRenewal": False, "profile": profile_ok},
            Lines_PreviewFieldRejected("NG-PV-REQ-APPN", required_field="appId"),
            "mp_pv_req_appn",
            extra="appId=null",
        ),
        preview_step(
            "preview_required_body",
            "NG-PV-REQ-AR",
            "负向：Preview缺autoRenewal拒绝",
            {"appId": 1, "profile": profile_ok},
            Lines_PreviewFieldRejected("NG-PV-REQ-AR", required_field="autoRenewal"),
            "mp_pv_req_ar",
            extra="缺 autoRenewal",
        ),
        preview_step(
            "preview_required_body",
            "NG-PV-REQ-ARN",
            "负向：Preview的autoRenewal为null拒绝",
            {"appId": 1, "autoRenewal": None, "profile": profile_ok},
            Lines_PreviewFieldRejected("NG-PV-REQ-ARN", required_field="autoRenewal"),
            "mp_pv_req_arn",
            extra="autoRenewal=null",
        ),
        preview_step(
            "preview_required_body",
            "NG-PV-REQ-EM",
            "负向：Preview缺profile.email拒绝",
            {"appId": 1, "autoRenewal": False, "profile": {"clientUserId": "{{$string.uuid}}"}},
            Lines_PreviewFieldRejected("NG-PV-REQ-EM", required_field="profile.email"),
            "mp_pv_req_em",
            extra="缺 profile.email",
        ),
        preview_step(
            "preview_required_body",
            "NG-PV-REQ-EMN",
            "负向：Preview的profile.email为null拒绝",
            {
                "appId": 1,
                "autoRenewal": False,
                "profile": {"email": None, "clientUserId": "{{$string.uuid}}"},
            },
            Lines_PreviewFieldRejected("NG-PV-REQ-EMN", required_field="profile.email"),
            "mp_pv_req_emn",
            extra="profile.email=null",
        ),
    ]

    type_base: JsonObject = {"appId": 1, "autoRenewal": False, "profile": dict(profile_ok)}
    type_steps = [
        preview_step(
            "preview_type_enum",
            "NG-PV-TY-APP",
            "负向：Preview的appId类型错误拒绝",
            {**type_base, "appId": "dsds"},
            Lines_PreviewFieldRejected("NG-PV-TY-APP"),
            "mp_pv_ty_app",
            extra="appId 为字符串",
        ),
        # autoRenewal=number：沙箱常强转/接受，不纳入本 Group（已删 NG-PV-TY-AR）
        preview_step(
            "preview_type_enum",
            "NG-PV-TY-PROF",
            "负向：Preview的profile类型错误拒绝",
            {"appId": 1, "autoRenewal": False, "profile": []},
            Lines_PreviewFieldRejected("NG-PV-TY-PROF"),
            "mp_pv_ty_prof",
            extra="profile 为数组",
        ),
        preview_step(
            "preview_type_enum",
            "NG-PV-TY-EM",
            "负向：Preview的profile.email类型错误拒绝",
            {
                "appId": 1,
                "autoRenewal": False,
                "profile": {"email": 123, "clientUserId": "{{$string.uuid}}"},
            },
            Lines_PreviewFieldRejected("NG-PV-TY-EM"),
            "mp_pv_ty_em",
            extra="email 为 number",
        ),
        # couponCode=number：沙箱常强转字符串并算价成功，不纳入本 Group
    ]

    def create_email_step(
        step: str,
        purpose: str,
        body_obj: JsonObject,
        tests: Sequence[str],
        profile_prefix: str,
        *,
        announce: bool = False,
        extra: str = "",
        prerequest_extra: Optional[Sequence[str]] = None,
    ) -> JsonObject:
        announce_pre: List[str] = []
        announce_test: List[str] = []
        if announce:
            announce_pre, announce_test = mp0.Lines_AnnounceGroupEnv(
                TcGroupName("preview_email_required"),
                ["productBProgramId", "productBProgramName", "productBPrice", "productBCurrency"],
                fixed_notes=["autoRenewal=false", "金额断言对齐商品 B", "Preview 与 Create 同规则"],
            )
        desc = TcDesc(
            "create_email_required",
            f"{extra} · 追溯用例：{TC_TITLE['create_email_required']}"
            if extra
            else f"追溯用例：{TC_TITLE['create_email_required']}",
        )
        return RequestItemP1(
            name=mp0.PurposeName(purpose, step, "POST", mp0.PATH_CREATE),
            method="POST",
            url_path=mp0.PATH_CREATE,
            body=json.dumps(body_obj, ensure_ascii=False, indent=2),
            headers=mp0.BearerJsonHeaders(),
            description=desc,
            test_lines=list(announce_test) + list(tests),
            prerequest_extra=list(announce_pre)
            + list(mp0.Lines_UniqueProfilePrerequest(profile_prefix))
            + list(prerequest_extra or []),
        )

    def cancel_email_step(step: str, order_var: str, extra: str) -> JsonObject:
        return RequestItemP1(
            name=mp0.PurposeName(TC_TITLE["e2e_cancel_pending"], step, "PATCH", mp0.PATH_CANCEL),
            method="PATCH",
            url_path=mp0.PATH_CANCEL,
            body=json.dumps({"status": 3, "orderId": "{{" + order_var + "}}"}, ensure_ascii=False, indent=2),
            headers=mp0.BearerJsonHeaders(),
            description=TcDesc("e2e_cancel_pending", extra),
            test_lines=mp0.Lines_CancelOrder(step, order_var),
            prerequest_extra=mp0.Lines_InjectOrderIdPrerequest(order_var),
        )

    # Preview → Create 成对；正向 Create 后 Cancel 收尾（同组同规则）
    email_steps = [
        preview_step(
            "preview_email_required",
            "OK-PV-EM",
            "正向：Preview仅传email可算价",
            {"appId": 1, "autoRenewal": False, "profile": {"email": "{{uniqueProfileEmail}}"}},
            Lines_PreviewProductBOptionalProfile("OK-PV-EM", expect_email=True, expect_client_user_id=False),
            "mp_pv_em",
            announce=True,
            extra="仅 email 成功",
        ),
        create_email_step(
            "OK-CC-EM",
            "正向：Create仅传email可成单",
            {"appId": 1, "autoRenewal": False, "profile": {"email": "{{uniqueProfileEmail}}"}},
            list(
                Lines_CreateProductBOptionalProfile(
                    "OK-CC-EM",
                    "orderIdEmailOnly",
                    expect_email=True,
                    expect_client_user_id=False,
                )
            )
            + Lines_SavePurchaseMembershipId("OK-CC-EM"),
            "mp_cc_em",
            announce=True,
            extra="仅 email 成功",
        ),
        SubscriptionCancelAfterCreateItem("OK-CC-EM-SUBCAN", extra="仅 email Create 后取消订阅"),
        cancel_email_step("OK-CC-EM-CAN", "orderIdEmailOnly", "仅 email Create 收尾"),
        preview_step(
            "preview_email_required",
            "OK-PV-BOTH",
            "正向：Preview同时传email与clientUserId可算价",
            {"appId": 1, "autoRenewal": False, "profile": dict(profile_ok)},
            Lines_PreviewProductBOptionalProfile("OK-PV-BOTH", expect_email=True, expect_client_user_id=True),
            "mp_pv_both",
            extra="email+clientUserId 成功",
        ),
        create_email_step(
            "OK-CC-BOTH",
            "正向：Create同时传email与clientUserId可成单",
            {"appId": 1, "autoRenewal": False, "profile": dict(profile_ok)},
            list(
                Lines_CreateProductBOptionalProfile(
                    "OK-CC-BOTH",
                    "orderIdEmailBoth",
                    expect_email=True,
                    expect_client_user_id=True,
                )
            )
            + Lines_SavePurchaseMembershipId("OK-CC-BOTH"),
            "mp_cc_both",
            extra="email+clientUserId 成功",
        ),
        SubscriptionCancelAfterCreateItem("OK-CC-BOTH-SUBCAN", extra="email+clientUserId Create 后取消订阅"),
        cancel_email_step("OK-CC-BOTH-CAN", "orderIdEmailBoth", "email+clientUserId Create 收尾"),
        preview_step(
            "preview_email_required",
            "NG-PV-EM-CUID",
            "负向：Preview仅传clientUserId缺email拒绝",
            {"appId": 1, "autoRenewal": False, "profile": {"clientUserId": "{{$string.uuid}}"}},
            Lines_FieldRejected("NG-PV-EM-CUID", required_field="profile.email"),
            "mp_pv_em_cuid",
            extra="仅 clientUserId 拒绝",
        ),
        create_email_step(
            "NG-CC-EM-CUID",
            "负向：Create仅传clientUserId缺email拒绝",
            {"appId": 1, "autoRenewal": False, "profile": {"clientUserId": "{{$string.uuid}}"}},
            Lines_FieldRejected("NG-CC-EM-CUID", required_field="profile.email"),
            "mp_cc_em_cuid",
            extra="仅 clientUserId 拒绝",
        ),
        preview_step(
            "preview_email_required",
            "NG-PV-EM-NONE",
            "负向：Preview的email与clientUserId都不传拒绝",
            {"appId": 1, "autoRenewal": False, "profile": {}},
            Lines_FieldRejected("NG-PV-EM-NONE", required_field="profile.email"),
            "mp_pv_em_none",
            extra="两者都不传拒绝",
        ),
        create_email_step(
            "NG-CC-EM-NONE",
            "负向：Create的email与clientUserId都不传拒绝",
            {"appId": 1, "autoRenewal": False, "profile": {}},
            Lines_FieldRejected("NG-CC-EM-NONE", required_field="profile.email"),
            "mp_cc_em_none",
            extra="两者都不传拒绝",
        ),
        preview_step(
            "preview_email_required",
            "NG-PV-EM-NULL",
            "负向：Preview的profile.email为null拒绝",
            {"appId": 1, "autoRenewal": False, "profile": {"email": None}},
            Lines_FieldRejected("NG-PV-EM-NULL", required_field="profile.email"),
            "mp_pv_em_null",
            extra="email=null 拒绝",
        ),
        create_email_step(
            "NG-CC-EM-NULL",
            "负向：Create的profile.email为null拒绝",
            {"appId": 1, "autoRenewal": False, "profile": {"email": None}},
            Lines_FieldRejected("NG-CC-EM-NULL", required_field="profile.email"),
            "mp_cc_em_null",
            extra="email=null 拒绝",
        ),
    ]

    return mp0.Folder(
        "会籍商品购买·Preview字段校验",
        [
            mp0.Folder(
                TcGroupName("preview_required_body"),
                required_steps,
                description=TcDesc("preview_required_body", "含 email；clientUserId 选填不纳入必填缺失组"),
            ),
            mp0.Folder(
                TcGroupName("preview_type_enum"),
                type_steps,
                description=TcDesc("preview_type_enum"),
            ),
            mp0.Folder(
                TcGroupName("preview_email_required"),
                email_steps,
                description=TcDesc(
                    "preview_email_required",
                    "Preview+Create 同规则：仅 email / 同时传成功；cuid-only / 都不传 / email=null 拒绝；正向 Create 后取消订阅再 Cancel",
                ),
            ),
        ],
        description="一场景一 Group；必填/类型负向 + email 必填且 clientUserId 选填（含 Create/purchase）。",
    )


def BuildCreateFieldValidationFolder() -> JsonObject:
    """Create 字段校验：必填缺失/null、类型错误；email 必填变体见 Preview email 同组。"""
    profile_ok: JsonObject = {
        "email": "{{uniqueProfileEmail}}",
        "clientUserId": "{{$string.uuid}}",
    }

    def create_step(
        tc_key: str,
        step: str,
        purpose: str,
        body_obj: JsonObject,
        tests: Sequence[str],
        profile_prefix: str,
        *,
        extra: str = "",
    ) -> JsonObject:
        desc = TcDesc(tc_key, f"{extra} · 追溯用例：{TC_TITLE[tc_key]}" if extra else f"追溯用例：{TC_TITLE[tc_key]}")
        return RequestItemP1(
            name=mp0.PurposeName(purpose, step, "POST", mp0.PATH_CREATE),
            method="POST",
            url_path=mp0.PATH_CREATE,
            body=json.dumps(body_obj, ensure_ascii=False, indent=2),
            headers=mp0.BearerJsonHeaders(),
            description=desc,
            test_lines=list(tests),
            prerequest_extra=list(mp0.Lines_UniqueProfilePrerequest(profile_prefix)),
        )

    required_steps = [
        create_step(
            "create_required_type",
            "NG-CC-REQ-APP",
            "负向：Create缺appId拒绝",
            {"autoRenewal": False, "profile": profile_ok},
            Lines_FieldRejected("NG-CC-REQ-APP"),
            "mp_cc_req_app",
            extra="缺 appId",
        ),
        create_step(
            "create_required_type",
            "NG-CC-REQ-APPN",
            "负向：Create的appId为null拒绝",
            {"appId": None, "autoRenewal": False, "profile": profile_ok},
            Lines_FieldRejected("NG-CC-REQ-APPN"),
            "mp_cc_req_appn",
            extra="appId=null",
        ),
        create_step(
            "create_required_type",
            "NG-CC-REQ-AR",
            "负向：Create缺autoRenewal拒绝",
            {"appId": 1, "profile": profile_ok},
            Lines_FieldRejected("NG-CC-REQ-AR"),
            "mp_cc_req_ar",
            extra="缺 autoRenewal",
        ),
        create_step(
            "create_required_type",
            "NG-CC-REQ-ARN",
            "负向：Create的autoRenewal为null拒绝",
            {"appId": 1, "autoRenewal": None, "profile": profile_ok},
            Lines_FieldRejected("NG-CC-REQ-ARN"),
            "mp_cc_req_arn",
            extra="autoRenewal=null",
        ),
        create_step(
            "create_required_type",
            "NG-CC-REQ-EM",
            "负向：Create缺profile.email拒绝",
            {"appId": 1, "autoRenewal": False, "profile": {"clientUserId": "{{$string.uuid}}"}},
            Lines_FieldRejected("NG-CC-REQ-EM"),
            "mp_cc_req_em",
            extra="缺 profile.email",
        ),
        create_step(
            "create_required_type",
            "NG-CC-REQ-EMN",
            "负向：Create的profile.email为null拒绝",
            {"appId": 1, "autoRenewal": False, "profile": {"email": None, "clientUserId": "{{$string.uuid}}"}},
            Lines_FieldRejected("NG-CC-REQ-EMN"),
            "mp_cc_req_emn",
            extra="profile.email=null",
        ),
        create_step(
            "create_required_type",
            "NG-CC-TY-APP",
            "负向：Create的appId类型错误拒绝",
            {"appId": "dsds", "autoRenewal": False, "profile": profile_ok},
            Lines_FieldRejected("NG-CC-TY-APP"),
            "mp_cc_ty_app",
            extra="appId 为字符串",
        ),
        # autoRenewal=number：沙箱常强转/接受，不纳入本 Group（已删 NG-CC-TY-AR）
        create_step(
            "create_required_type",
            "NG-CC-TY-EM",
            "负向：Create的profile.email类型错误拒绝",
            {
                "appId": 1,
                "autoRenewal": False,
                "profile": {"email": 123, "clientUserId": "{{$string.uuid}}"},
            },
            Lines_FieldRejected("NG-CC-TY-EM"),
            "mp_cc_ty_em",
            extra="email 为 number",
        ),
    ]

    return mp0.Folder(
        "会籍商品购买·Create字段校验",
        [
            mp0.Folder(
                TcGroupName("create_required_type"),
                required_steps,
                description=TcDesc(
                    "create_required_type",
                    "缺/null appId·autoRenewal·email；类型错误 appId/autoRenewal(number 1)/email；clientUserId 不纳入必填缺失",
                ),
            ),
        ],
        description="Create 必填/类型负向；email 必填变体见 Preview email 同组（含 Create）。",
    )


def BuildSubscriptionCancelFieldValidationFolder() -> JsonObject:
    """取消订阅字段校验：必填/类型/格式 + membershipId 与 Create 注册 email 不一致。"""
    valid_email = "developer@dragonpass.com"
    valid_mid = DUMMY_MEMBERSHIP_ID
    mismatch_email = "mismatch.other@example.com"

    def cancel_step(
        tc_key: str,
        step: str,
        purpose: str,
        body_obj: JsonObject,
        tests: Sequence[str],
        *,
        extra: str = "",
        prerequest_extra: Optional[Sequence[str]] = None,
        profile_prefix: str = "",
    ) -> JsonObject:
        desc = TcDesc(tc_key, f"{extra} · 追溯：{TC_TITLE[tc_key]}" if extra else f"追溯：{TC_TITLE[tc_key]}")
        pre: List[str] = []
        if profile_prefix:
            pre.extend(mp0.Lines_UniqueProfilePrerequest(profile_prefix))
        if prerequest_extra:
            pre.extend(list(prerequest_extra))
        return RequestItemP1(
            name=mp0.PurposeName(purpose, step, "POST", PATH_SUBSCRIPTION_CANCEL),
            method="POST",
            url_path=PATH_SUBSCRIPTION_CANCEL,
            body=json.dumps(body_obj, ensure_ascii=False, indent=2),
            headers=mp0.BearerJsonHeaders(),
            description=desc,
            test_lines=list(tests),
            prerequest_extra=pre,
        )

    required_steps = [
        cancel_step(
            "sub_cancel_required_type",
            "NG-SC-REQ-MID",
            "负向：取消订阅缺membershipId拒绝",
            {"email": valid_email},
            Lines_FieldRejected("NG-SC-REQ-MID", required_field="membershipId"),
            extra="缺 membershipId",
        ),
        cancel_step(
            "sub_cancel_required_type",
            "NG-SC-REQ-MIDN",
            "负向：取消订阅的membershipId为null拒绝",
            {"membershipId": None, "email": valid_email},
            Lines_FieldRejected("NG-SC-REQ-MIDN", required_field="membershipId"),
            extra="membershipId=null",
        ),
        cancel_step(
            "sub_cancel_required_type",
            "NG-SC-REQ-EM",
            "负向：取消订阅缺email拒绝",
            {"membershipId": valid_mid},
            Lines_FieldRejected("NG-SC-REQ-EM", required_field="email"),
            extra="缺 email",
        ),
        cancel_step(
            "sub_cancel_required_type",
            "NG-SC-REQ-EMN",
            "负向：取消订阅的email为null拒绝",
            {"membershipId": valid_mid, "email": None},
            Lines_FieldRejected("NG-SC-REQ-EMN", required_field="email"),
            extra="email=null",
        ),
        cancel_step(
            "sub_cancel_required_type",
            "NG-SC-TY-MID",
            "负向：取消订阅的membershipId类型错误拒绝",
            {"membershipId": 123, "email": valid_email},
            Lines_FieldRejected("NG-SC-TY-MID"),
            extra="membershipId 为 number",
        ),
        cancel_step(
            "sub_cancel_required_type",
            "NG-SC-TY-EM",
            "负向：取消订阅的email类型错误拒绝",
            {"membershipId": valid_mid, "email": 123},
            Lines_FieldRejected("NG-SC-TY-EM"),
            extra="email 为 number",
        ),
        cancel_step(
            "sub_cancel_required_type",
            "NG-SC-PAT-MID",
            "负向：取消订阅的membershipId非16位数字拒绝",
            {"membershipId": "abc", "email": valid_email},
            Lines_FieldRejected("NG-SC-PAT-MID"),
            extra="membershipId 不匹配 ^[0-9]{16}$",
        ),
        cancel_step(
            "sub_cancel_required_type",
            "NG-SC-PAT-EM",
            "负向：取消订阅的email格式错误拒绝",
            {"membershipId": valid_mid, "email": "not-an-email"},
            Lines_FieldRejected("NG-SC-PAT-EM"),
            extra="email 非邮箱格式",
        ),
    ]

    setup_body = BodyPreviewCreate(coupon_env=None, auto_renewal=False)
    setup_create = RequestItemP1(
        name=mp0.PurposeName(
            TC_TITLE["create_b_no_coupon"],
            "SC-MM-SETUP-CRT",
            "POST",
            mp0.PATH_CREATE,
        ),
        method="POST",
        url_path=mp0.PATH_CREATE,
        body=setup_body,
        headers=mp0.BearerJsonHeaders(),
        description=TcDesc(
            "sub_cancel_mismatch",
            "造数：Create 注册 uniqueProfileEmail / 可能的 membershipId",
        ),
        test_lines=list(mp0.Lines_CreateProductB("orderIdSubCancelMismatch"))
        + Lines_SavePurchaseMembershipId("SC-MM-SETUP-CRT"),
        prerequest_extra=mp0.Lines_UniqueProfilePrerequest("mp_sc_mm"),
    )
    mismatch_mid = cancel_step(
        "sub_cancel_mismatch",
        "NG-SC-MM-MID",
        "负向：membershipId不是Create注册的会籍拒绝",
        {"membershipId": valid_mid, "email": "{{uniqueProfileEmail}}"},
        Lines_FieldRejectedWithErrCode("NG-SC-MM-MID", ERR_SUB_CANCEL_FAILED),
        extra="Create 的 email + 非本单 16 位 membershipId",
        prerequest_extra=Lines_InjectSubscriptionCancelPrerequest(),
    )
    mismatch_email = cancel_step(
        "sub_cancel_mismatch",
        "NG-SC-MM-EM",
        "负向：email与Create注册不一致拒绝",
        {"membershipId": "{{purchaseMembershipId}}", "email": mismatch_email},
        Lines_FieldRejectedWithErrCode("NG-SC-MM-EM", ERR_SUB_CANCEL_FAILED),
        extra="Create 的 membershipId（无则 OAS 示例 dpid）+ 另一合法 email",
        prerequest_extra=Lines_InjectSubscriptionCancelPrerequest(),
    )

    return mp0.Folder(
        "会籍商品购买·取消订阅字段校验",
        [
            mp0.Folder(
                TcGroupName("sub_cancel_required_type"),
                required_steps,
                description=TcDesc(
                    "sub_cancel_required_type",
                    "缺/null membershipId·email；类型 number；membershipId 非16位；email 非法格式",
                ),
            ),
            mp0.Folder(
                TcGroupName("sub_cancel_mismatch"),
                [setup_create, mismatch_mid, mismatch_email],
                description=TcDesc(
                    "sub_cancel_mismatch",
                    "Create 注册后：异 membershipId / 异 email 均期望 500.020.035",
                ),
            ),
        ],
        description=(
            "PAPI-3056 POST /v2/memberships/subscriptions/cancellation。"
            "必填 membershipId（16位数字）+ email；归属不一致走 500.020.035。"
        ),
    )


def BuildNegativePaymentsDetailsFolder() -> JsonObject:
    """Payments / Details 字段负向（需先有 orderId）。"""
    setup_body = BodyPreviewCreate(coupon_env=None, auto_renewal=False)
    setup_create = RequestItemP1(
        name=mp0.PurposeName(
            TC_TITLE["create_b_no_coupon"],
            "NG-SETUP-CRT",
            "POST",
            mp0.PATH_CREATE,
        ),
        method="POST",
        url_path=mp0.PATH_CREATE,
        body=setup_body,
        headers=mp0.BearerJsonHeaders(),
        description=TcDesc("create_b_no_coupon", "前置造数 orderIdNegSetup"),
        test_lines=mp0.Lines_CreateProductB("orderIdNegSetup"),
        prerequest_extra=mp0.Lines_UniqueProfilePrerequest("mp_ngsetup"),
    )
    pay_step = RequestItemP1(
        name=mp0.PurposeName(
            "负向：Payments缺orderId拒绝",
            "NG-PAY-MO",
            "POST",
            mp0.PATH_PAYMENTS,
        ),
        method="POST",
        url_path=mp0.PATH_PAYMENTS,
        body=json.dumps({"returnUrl": "{{returnUrl}}", "paymentMethod": "H5_CASHIER"}, ensure_ascii=False, indent=2),
        headers=mp0.BearerJsonHeaders(),
        description=TcDesc("payments_missing_field", "缺 orderId · 追溯用例：" + TC_TITLE["payments_missing_field"]),
        test_lines=Lines_FieldRejected("NG-PAY-MO"),
    )

    def details_step(
        step: str,
        purpose: str,
        body_obj: JsonObject,
        extra: str,
        *,
        required_field: Optional[str] = None,
    ) -> JsonObject:
        return RequestItemP1(
            name=mp0.PurposeName(purpose, step, "POST", mp0.PATH_DETAILS),
            method="POST",
            url_path=mp0.PATH_DETAILS,
            body=json.dumps(body_obj, ensure_ascii=False, indent=2),
            headers=mp0.BearerJsonHeaders(),
            description=TcDesc(
                "details_order_id_required",
                f"{extra} · 追溯用例：{TC_TITLE['details_order_id_required']}",
            ),
            test_lines=Lines_FieldRejected(step, required_field=required_field),
        )

    det_steps = [
        details_step("NG-DET-MO", "负向：Details缺orderId拒绝", {}, "body 空对象无 orderId"),
        details_step("NG-DET-NULL", "负向：Details的orderId为null拒绝", {"orderId": None}, "orderId=null"),
        details_step("NG-DET-NUM", "负向：Details的orderId类型错误拒绝", {"orderId": 123}, "orderId 为 number"),
        details_step("NG-DET-EMPTY", "负向：Details的orderId为空串拒绝", {"orderId": ""}, "orderId 空字符串"),
    ]
    pay_group = mp0.Folder(
        TcGroupName("payments_missing_field"),
        [setup_create, pay_step],
        description=TcDesc("payments_missing_field", "造数 Create + 缺 orderId 负向"),
    )
    det_group = mp0.Folder(
        TcGroupName("details_order_id_required"),
        det_steps,
        description=TcDesc("details_order_id_required", "参数化 {} / null / number / 空串"),
    )
    return mp0.Folder(
        "会籍商品购买·Payments与Details字段校验",
        [pay_group, det_group],
        description="一场景一 Group；Details orderId 四变体；Payments 含造数+缺 orderId。",
    )


def BuildAuthFolder() -> JsonObject:
    return mp0.Folder(
        "00 Auth",
        [
            RequestItemP1(
                name=mp0.PurposeName("鉴权获取访问令牌", "Auth", "POST", mp0.PATH_AUTH),
                method="POST",
                url_path=mp0.PATH_AUTH,
                # 必须用占位符：Apifox 勾选鉴权数据集行时注入 ProgramID/clientId/secret；
                # 禁止把 .env 写死进 body（否则永远是第一套 Program）。
                body=json.dumps(
                    {"clientId": "{{clientId}}", "secret": "{{secret}}"},
                    ensure_ascii=False,
                    indent=2,
                ),
                headers=[
                    {"key": "X-Program-ID", "value": "{{ProgramID}}"},
                    {"key": "x-version", "value": "{{x-version}}"},
                    {"key": "X-Request-ID", "value": "{{$guid}}"},
                    {"key": "Content-Type", "value": "application/json"},
                    {"key": "Accept", "value": "*/*"},
                ],
                description=(
                    "写入 accessToken。"
                    "优先用运行时勾选的鉴权数据集行（ProgramID/clientId/secret）；"
                    "未勾选时回落 .env 的 MP_P0_*。"
                ),
                save_token=True,
                test_lines=mp0.Lines_Auth(),
            ),
        ],
        description="先执行以写入 accessToken；鉴权随勾选数据集行切换。",
    )


def BuildCollection() -> JsonObject:
    return {
        "info": {
            "name": COLLECTION_DISPLAY_NAME,
            "description": BuildScenarioDescription(),
            "schema": mp0.POSTMAN_SCHEMA,
        },
        "variable": [
            mp0.CollectionVariable("baseUrl", ""),
            mp0.CollectionVariable("x-version", ""),
            mp0.CollectionVariable("returnUrl", "https://www.ly.com"),
            mp0.CollectionVariable("productBDeduction", "0"),
            mp0.CollectionVariable("productADeduction", "0"),
        ],
        "item": [
            BuildAuthFolder(),
            BuildPositiveE2EFolder(),
            BuildNegativeBusinessScenariosFolder(),
            BuildPreviewFieldValidationFolder(),
            BuildCreateFieldValidationFolder(),
            BuildSubscriptionCancelFieldValidationFolder(),
            BuildNegativePaymentsDetailsFolder(),
        ],
    }


def _EnvKeyRole(key: str) -> str:
    guide = mp0.ENV_KEY_FILL_GUIDE.get(key) or ""
    if guide.startswith("【入参"):
        return "入参"
    if guide.startswith("【断言"):
        return "断言"
    if guide.startswith("【环境"):
        return "环境"
    if guide.startswith("【参考"):
        return "参考"
    return "其它"


def _DefaultManualKeys(keys: Sequence[str]) -> List[str]:
    """启发式：券码/商品断言/已有订阅用户视为手工必改；假券码与扣减名义键可不动。"""
    skip = {
        "CouponNotFoundCode",
        "productBDeduction",
        "productADeduction",
        "returnUrl",
        "baseUrl",
        "x-version",
    }
    out: List[str] = []
    for k in keys:
        if k in skip:
            continue
        if k.startswith("Coupon") or k.startswith("product") or k.startswith("Existing"):
            out.append(k)
    return out


def BuildScenarioEnvCatalog() -> List[ScenarioEnvSpec]:
    """P1 各 Group 差分 Environment 键（与 Build*Folder 对齐；改 Group 时请同步本表）。"""
    specs: List[ScenarioEnvSpec] = [
        ScenarioEnvSpec(
            scenario_key="_SHARED_BASELINE",
            group_name="公共基线（全场景共用，填一次）",
            polarity="baseline",
            env_keys=["baseUrl", "x-version", "returnUrl"],
            notes="鉴权三列 ProgramID/clientId/secret 走 .env MP_P0_* 或数据集，不进本 CSV。",
            manual_keys=["baseUrl", "x-version"],
        ),
        # —— 正向 ——
        ScenarioEnvSpec(
            scenario_key="pos_b_no_coupon",
            group_name=TcGroupName("preview_b_no_coupon"),
            polarity="positive",
            env_keys=[
                "productBProgramId",
                "productBProgramName",
                "productBPrice",
                "productBCurrency",
                "productBCurrencyConfigured",
                "productBCurrencyUnconfigured",
                "productBDeduction",
                "returnUrl",
            ],
            notes="不传券 · autoRenewal=false · 商品 B 原价 E2E；币种变体见同级【币种·*】Group",
        ),
        ScenarioEnvSpec(
            scenario_key="pos_a_intro",
            group_name=TcGroupName("preview_a_intro"),
            polarity="positive",
            env_keys=[
                "CouponIntroValid",
                "CouponIntroValidName",
                "productAProgramId",
                "productAProgramName",
                "productAPrice",
                "productAPayableAmount",
                "productACurrency",
                "productACurrencyConfigured",
                "productACurrencyUnconfigured",
                "returnUrl",
            ],
            notes="引导期 · activationMethod=1 · payable 常 0 · Create status=9；币种变体见同级【币种·*】Group",
        ),
        ScenarioEnvSpec(
            scenario_key="pos_a_no_intro",
            group_name=TcGroupName("preview_a_no_intro"),
            polarity="positive",
            env_keys=[
                "CouponIntroValid",
                "productAProgramId",
                "productAProgramName",
                "productAPrice",
                "productANoIntroPayableAmount",
                "productACurrency",
                "productACurrencyConfigured",
                "productACurrencyUnconfigured",
                "returnUrl",
            ],
            notes="未开引导期 · activationMethod=2 · productANoIntroPayableAmount 通常=productAPrice；币种变体见同级【币种·*】Group",
            manual_keys=None,  # 启发式：含应付键 + 券/商品
        ),
        ScenarioEnvSpec(
            scenario_key="pos_payments_retry",
            group_name=TcGroupName("payments_retry"),
            polarity="positive",
            env_keys=[
                "productBProgramId",
                "productBProgramName",
                "productBPrice",
                "productBCurrency",
                "returnUrl",
            ],
            notes="再次取链 · Create 商品 B + Payments×2",
        ),
        # —— 负向：无订阅 / 订阅关 Create 031 ——
        ScenarioEnvSpec(
            scenario_key="neg_a_no_sub_ar_false",
            group_name=TcGroupName("preview_a_no_sub_original"),
            polarity="negative",
            env_keys=[
                "CouponIntroNoRenew",
                "CouponIntroNoRenewName",
                "productANoSubProgramId",
                "productANoSubProgramName",
                "productANoSubPrice",
            ],
            notes="Preview valid=false + details对象 → Create 500.020.031",
        ),
        ScenarioEnvSpec(
            scenario_key="neg_a_sub_off_ar_false",
            group_name=TcGroupName("preview_a_sub_off"),
            polarity="negative",
            env_keys=[
                "CouponIntroNoRenew",
                "productASubOffCouponName",
                "productASubOffProgramId",
                "productASubOffProgramName",
                "productASubOffPrice",
            ],
            notes="Preview valid=false + details对象 → Create 500.020.031",
        ),
        ScenarioEnvSpec(
            scenario_key="neg_b_ar_true",
            group_name=TcGroupName("preview_b_auto_renewal_true"),
            polarity="negative",
            env_keys=["productBProgramId", "productBPrice", "productBCurrency"],
            notes="Preview 030 / Create 031；不传券",
        ),
        ScenarioEnvSpec(
            scenario_key="neg_a_no_sub_ar_true",
            group_name=TcGroupName("preview_a_no_sub_ar_true"),
            polarity="negative",
            env_keys=["CouponIntroNoRenew", "productANoSubProgramId", "productANoSubPrice"],
            notes="Preview 030 / Create 031",
        ),
        ScenarioEnvSpec(
            scenario_key="neg_coupon_not_found",
            group_name=TcGroupName("preview_coupon_not_found"),
            polarity="negative",
            env_keys=["CouponNotFoundCode", "productBPrice", "productBCurrency"],
            notes="Create 031；假券码默认可不改",
            manual_keys=[],
        ),
        ScenarioEnvSpec(
            scenario_key="neg_coupon_expired",
            group_name=TcGroupName("preview_coupon_expired"),
            polarity="negative",
            env_keys=["CouponExpired", "productBPrice", "productBCurrency"],
            notes="Create 031",
        ),
        ScenarioEnvSpec(
            scenario_key="neg_coupon_wrong_type",
            group_name=TcGroupName("preview_coupon_wrong_type"),
            polarity="negative",
            env_keys=["CouponWrongType", "productBPrice", "productBCurrency"],
            notes="Create 702",
        ),
        ScenarioEnvSpec(
            scenario_key="neg_coupon_ineligible",
            group_name=TcGroupName("preview_coupon_ineligible"),
            polarity="negative",
            env_keys=[
                "CouponIneligible",
                "productANoSubPrice",
                "productANoSubCurrency",
                "productAPrice",
            ],
            notes="Create 702",
        ),
        ScenarioEnvSpec(
            scenario_key="neg_dup_subscription",
            group_name=TcGroupName("create_dup_subscription"),
            polarity="negative",
            env_keys=["ExistingActiveProfileEmail", "ExistingActiveProfileClientUserId"],
            notes="仅 Create · 032",
        ),
        ScenarioEnvSpec(
            scenario_key="neg_preview_required_body",
            group_name=TcGroupName("preview_required_body"),
            polarity="negative",
            env_keys=[],
            notes="缺/null appId·autoRenewal·profile.email；clientUserId 不测必填缺失",
            manual_keys=[],
        ),
        ScenarioEnvSpec(
            scenario_key="neg_preview_type_enum",
            group_name=TcGroupName("preview_type_enum"),
            polarity="negative",
            env_keys=[],
            notes="类型错误组脚本写死；无额外 Environment 差分键",
            manual_keys=[],
        ),
        ScenarioEnvSpec(
            scenario_key="pos_preview_email_required",
            group_name=TcGroupName("preview_email_required"),
            polarity="positive",
            env_keys=[
                "productBProgramId",
                "productBProgramName",
                "productBPrice",
                "productBCurrency",
            ],
            notes="Preview+Create 同规则：仅 email / 同时传成功；cuid-only·都不传·null 负向；正向 Create 后 Cancel",
        ),
        ScenarioEnvSpec(
            scenario_key="neg_create_required_type",
            group_name=TcGroupName("create_required_type"),
            polarity="negative",
            env_keys=[],
            notes="缺/null appId·autoRenewal·email；类型错误 appId/autoRenewal(number 1)/email",
            manual_keys=[],
        ),
        ScenarioEnvSpec(
            scenario_key="neg_sub_cancel_required_type",
            group_name=TcGroupName("sub_cancel_required_type"),
            polarity="negative",
            env_keys=[],
            notes="缺/null membershipId·email；类型 number；membershipId 非16位；email 非法格式",
            manual_keys=[],
        ),
        ScenarioEnvSpec(
            scenario_key="neg_sub_cancel_mismatch",
            group_name=TcGroupName("sub_cancel_mismatch"),
            polarity="negative",
            env_keys=[
                "productBProgramId",
                "productBProgramName",
                "productBPrice",
                "productBCurrency",
            ],
            notes="Create 商品B注册后：异 membershipId / 异 email 期望 500.020.035",
        ),
        ScenarioEnvSpec(
            scenario_key="neg_details_order_id",
            group_name=TcGroupName("details_order_id_required"),
            polarity="negative",
            env_keys=[],
            notes="orderId：{} / null / number / 空串",
            manual_keys=[],
        ),
        ScenarioEnvSpec(
            scenario_key="neg_payments_details",
            group_name="Payments/Details 缺 orderId",
            polarity="negative",
            env_keys=[
                "productBProgramId",
                "productBProgramName",
                "productBPrice",
                "productBCurrency",
                "returnUrl",
            ],
            notes="先 Create 商品 B 造数，再缺 orderId 负向",
        ),
    ]
    filled: List[ScenarioEnvSpec] = []
    for spec in specs:
        if spec.manual_keys is None:
            manual: Sequence[str] = _DefaultManualKeys(spec.env_keys)
        else:
            manual = list(spec.manual_keys)
        filled.append(
            ScenarioEnvSpec(
                scenario_key=spec.scenario_key,
                group_name=spec.group_name,
                polarity=spec.polarity,
                env_keys=spec.env_keys,
                notes=spec.notes,
                manual_keys=manual,
            )
        )
    return filled


def ScenarioEnvDatasetDir() -> Path:
    return Path(__file__).resolve().parents[1] / "datasets" / "membership_purchase_p1"


def WriteScenarioEnvCsvs(specs: Optional[Sequence[ScenarioEnvSpec]] = None) -> List[Path]:
    """写出 long + wide CSV：换测选行 / 填齐后可共 Environment 跑全量。"""
    catalog = list(specs or BuildScenarioEnvCatalog())
    out_dir = ScenarioEnvDatasetDir()
    out_dir.mkdir(parents=True, exist_ok=True)

    all_keys: List[str] = []
    seen: Dict[str, bool] = {}
    for spec in catalog:
        for k in spec.env_keys:
            if k not in seen:
                seen[k] = True
                all_keys.append(k)

    written: List[Path] = []

    long_path = out_dir / "scenario-env-keys.csv"
    try:
        with long_path.open("w", encoding="utf-8-sig", newline="") as fp:
            writer = csv.DictWriter(
                fp,
                fieldnames=[
                    "scenario_key",
                    "group_name",
                    "polarity",
                    "env_key",
                    "placeholder",
                    "role",
                    "manual_fill",
                    "short_meaning",
                    "notes",
                ],
            )
            writer.writeheader()
            for spec in catalog:
                manual_set = set(spec.manual_keys or ())
                if not spec.env_keys:
                    writer.writerow(
                        {
                            "scenario_key": spec.scenario_key,
                            "group_name": spec.group_name,
                            "polarity": spec.polarity,
                            "env_key": "",
                            "placeholder": "",
                            "role": "",
                            "manual_fill": "N",
                            "short_meaning": "",
                            "notes": spec.notes,
                        }
                    )
                    continue
                for k in spec.env_keys:
                    writer.writerow(
                        {
                            "scenario_key": spec.scenario_key,
                            "group_name": spec.group_name,
                            "polarity": spec.polarity,
                            "env_key": k,
                            "placeholder": MERGED_BUSINESS_ENV.get(k, ""),
                            "role": _EnvKeyRole(k),
                            "manual_fill": "Y" if k in manual_set else "N",
                            "short_meaning": mp0.ENV_KEY_FILL_SHORT.get(k, ""),
                            "notes": spec.notes,
                        }
                    )
        written.append(long_path)
    except OSError as exc:
        print(f"WARN: skip {long_path} ({exc})")

    wide_path = out_dir / "scenario-env-matrix.csv"
    wide_fields = [
        "scenario_key",
        "group_name",
        "polarity",
        "manual_keys",
        "notes",
        "how_to_use",
    ] + all_keys
    try:
        with wide_path.open("w", encoding="utf-8-sig", newline="") as fp:
            writer = csv.DictWriter(fp, fieldnames=wide_fields, extrasaction="ignore")
            writer.writeheader()
            for spec in catalog:
                row: Dict[str, str] = {
                    "scenario_key": spec.scenario_key,
                    "group_name": spec.group_name,
                    "polarity": spec.polarity,
                    "manual_keys": "|".join(spec.manual_keys or ()),
                    "notes": spec.notes,
                    "how_to_use": (
                        "只跑本场景：把本行非空键写入 Environment 351893；"
                        "跑全量：填齐各行并集（键名已分场景，可一次填完）。"
                    ),
                }
                for k in all_keys:
                    row[k] = MERGED_BUSINESS_ENV.get(k, "") if k in spec.env_keys else ""
                writer.writerow(row)
        written.append(wide_path)
    except OSError as exc:
        print(f"WARN: skip {wide_path} ({exc})")

    return written


# Apifox「全量数据」业务列：不含鉴权三列、不含 accessToken（鉴权仍走 .env / 鉴权数据集）
# baseUrl / x-version 留在 Environment（与 Skill 约定一致），不进业务数据集
APIFOX_DATASET_SKIP_KEYS: Final[Sequence[str]] = (
    "baseUrl",
    "x-version",
    "ProgramID",
    "clientId",
    "secret",
    "accessToken",
)


def ApifoxBusinessDatasetKeys() -> List[str]:
    return [k for k in MERGED_BUSINESS_ENV.keys() if k not in set(APIFOX_DATASET_SKIP_KEYS)]


def WriteApifoxBusinessDatasetCsvs(
    specs: Optional[Sequence[ScenarioEnvSpec]] = None,
) -> List[Path]:
    """写出可导入 Apifox「全量数据」的业务数据集（选行驱动）。

    - ``name``：中文 Group 名（Apifox UI 选行用，与场景目录一致）
    - ``scenario_key``：稳定英文键（对照/脚本用）
    - 业务列：与 ``{{键}}`` / getEnv 同名；占位非 ASCII 用 ``FILL_*``
    - 另出 ascii 版（name 仍为英文）供编码异常时备用
    """
    catalog = [s for s in (specs or BuildScenarioEnvCatalog()) if s.scenario_key != "_SHARED_BASELINE"]
    biz_keys = ApifoxBusinessDatasetKeys()
    out_dir = ScenarioEnvDatasetDir()
    out_dir.mkdir(parents=True, exist_ok=True)

    fieldnames = ["name", "scenario_key", "title", "polarity", "notes"] + biz_keys
    full_zh = "全量并集（填齐后勾选本行跑整场景）"

    def _ascii_placeholder(key: str, value: str) -> str:
        if not value:
            return ""
        try:
            value.encode("ascii")
            return value
        except UnicodeEncodeError:
            return f"FILL_{key}"

    def build_zh_rows() -> List[Dict[str, str]]:
        rows: List[Dict[str, str]] = []
        full: Dict[str, str] = {
            "name": full_zh,
            "scenario_key": "_FULL_SUITE",
            "title": full_zh,
            "polarity": "full",
            "notes": "填齐本行全部业务列后勾选；鉴权仍用 MP_P0_* / 鉴权数据集",
        }
        for k in biz_keys:
            full[k] = _ascii_placeholder(k, MERGED_BUSINESS_ENV.get(k, ""))
        rows.append(full)
        for spec in catalog:
            zh = spec.group_name
            row: Dict[str, str] = {
                "name": zh,
                "scenario_key": spec.scenario_key,
                "title": zh,
                "polarity": spec.polarity,
                "notes": zh,
            }
            for k in biz_keys:
                raw = MERGED_BUSINESS_ENV.get(k, "") if k in spec.env_keys else ""
                row[k] = _ascii_placeholder(k, raw) if raw else ""
            rows.append(row)
        return rows

    def build_ascii_rows() -> List[Dict[str, str]]:
        """备用：name=scenario_key，纯 ASCII，编码异常时导入。"""
        rows: List[Dict[str, str]] = []
        full: Dict[str, str] = {
            "name": "_FULL_SUITE",
            "scenario_key": "_FULL_SUITE",
            "title": "full_suite",
            "polarity": "full",
            "notes": "fill_all_biz_cols; auth=MP_P0_or_auth_dataset",
        }
        for k in biz_keys:
            full[k] = _ascii_placeholder(k, MERGED_BUSINESS_ENV.get(k, ""))
        rows.append(full)
        for spec in catalog:
            row: Dict[str, str] = {
                "name": spec.scenario_key,
                "scenario_key": spec.scenario_key,
                "title": spec.scenario_key,
                "polarity": spec.polarity,
                "notes": spec.scenario_key,
            }
            for k in biz_keys:
                raw = MERGED_BUSINESS_ENV.get(k, "") if k in spec.env_keys else ""
                row[k] = _ascii_placeholder(k, raw) if raw else ""
            rows.append(row)
        return rows

    zh_rows = build_zh_rows()
    ascii_rows = build_ascii_rows()
    utf8_path = out_dir / "apifox-dataset-business.csv"
    ascii_path = out_dir / "apifox-dataset-business-ascii.csv"

    with utf8_path.open("w", encoding="utf-8-sig", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(zh_rows)

    ascii_fields = fieldnames
    with ascii_path.open("w", encoding="ascii", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=ascii_fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(ascii_rows)

    return [utf8_path, ascii_path]


def Main() -> None:
    out = mp0.CollectionPath(OUT_NAME)
    payload = BuildCollection()
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out}")
    for path in WriteScenarioEnvCsvs():
        print(f"Wrote {path}")
    for path in WriteApifoxBusinessDatasetCsvs():
        print(f"Wrote {path}")
    map_path = WriteScenarioGroupMapMd()
    print(f"Wrote {map_path}")


def WriteScenarioGroupMapMd(specs: Optional[Sequence[ScenarioEnvSpec]] = None) -> Path:
    """中文 Group 名（数据集 name）↔ scenario_key 对照。"""
    catalog = list(specs or BuildScenarioEnvCatalog())
    out = ScenarioEnvDatasetDir() / "scenario-group-map.md"
    lines = [
        "# 数据集 name（中文）↔ scenario_key",
        "",
        "Apifox 全量数据 **name** 列已用中文 Group 名；`scenario_key` 为稳定英文键。",
        "",
        "| name（中文 Group） | scenario_key | 类型 |",
        "|---|---|---|",
        "| 全量并集（填齐后勾选本行跑整场景） | `_FULL_SUITE` | full |",
    ]
    for spec in catalog:
        if spec.scenario_key == "_SHARED_BASELINE":
            continue
        lines.append(
            f"| {spec.group_name} | `{spec.scenario_key}` | {spec.polarity} |"
        )
    lines.append("")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


if __name__ == "__main__":
    Main()
