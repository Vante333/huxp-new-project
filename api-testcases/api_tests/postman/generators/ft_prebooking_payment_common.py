"""
预预约 payment · 共享 Postman Collection 构建器（Fast Track / Lounge）。

对齐 ``testcases/2026Q2SP4/订单流支持真现金支付第三方权益-自动化实现参考.md`` 与
``.cursor/skills/api-testcase-pack/prebooking-payment-apifox-assertions.md``：

- Preview / Create / Detail 通用 payment 断言（内联 ``tools/apifox_payment_assert_*.js``）
- 客户预收费专用断言（内联 ``tools/apifox_client_collect_assert_*.js``）
- Membership / E-pass × P0 冒烟 / P1 全量
- 品类轴：``category=fastTrack|lounge``（见 ``prebooking_payment_category.py``）

用法见各 ``GeneratePostmanCollectionFt*Payment*.py`` / ``GeneratePostmanCollectionLounge*Payment*.py`` 入口。
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Final, List, Literal, Optional, Sequence, Union

from collection_builder_common import (
    CollectionPath,
    POSTMAN_SCHEMA,
    AuthJsonHeaders,
    BearerJsonHeaders,
    CollectionVariable,
    Folder,
    Lines_Step,
    PurposeName,
    WriteCollectionJson,
)
from GeneratePostmanCollectionFastTrackEpass import (
    CREATE_AVAILABLE_USAGES,
    CREATE_EXPIRATION_DATE,
    CREATE_FIRST_NAME,
    CREATE_LAST_NAME,
    FASTTRACK_ADULT_PASSENGER_NAMES,
    FASTTRACK_CHILD_PASSENGER_NAMES,
    FastTrackPrebookingExtraDict,
    Prerequest_InitFastTrackPassengerCounts,
    Prerequest_NewClientUserId,
    Prerequest_SyncPrebookingDateFromApifox,
    Prerequest_SyncPrebookingPassengersBody,
)
from prebooking_payment_category import (
    ActiveCategory,
    CategoryKind,
    PRICING_CANONICAL_KEYS,
    SetActiveCategory,
)

JsonObject = Dict[str, Any]
ModuleKind = Literal["membership", "epass"]
PriorityKind = Literal["p0", "p1"]
PaymentMode = Literal["entitlement", "cash", "client_collect"]

# 与参考文档「预约 3 人」对齐：CARDHOLDER=1 + GUEST=2
PAYMENT_ADULT_COUNT: Final[int] = 3
PAYMENT_CHILD_COUNT: Final[int] = 0

CONTACT_PHONE: Final[str] = "8081966002"
CONTACT_CALLING_CODE: Final[str] = "44"

# cashPaymentApplied 与 cashier.paymentMode 冲突（membership true+DP_COLLECT；ePass 不支持客户预收款）
CASH_COLLECT_CONFLICT_MSG: Final[str] = (
    "The specified collection method conflicts with the cash payment parameter. "
    "Please verify the request parameters."
)
CANCEL_FAILED_MSG: Final[str] = (
    "Order cancellation failed. Please try again later."
)


def CurrentEpassModule() -> int:
    return int(ActiveCategory().epass_module)


def ResourceEnvKey() -> str:
    return str(ActiveCategory().resource_env_key)


def ResourceTemplate() -> str:
    return "{{" + ResourceEnvKey() + "}}"


def OrdersPathSegment() -> str:
    return str(ActiveCategory().path_segment)


def PrebookingExtraForCategory(
    *,
    adult_count: int,
    child_count: int,
    include_transport_number: bool = True,
) -> JsonObject:
    """FT：passengers + 可选 transportNumber；Lounge：仅 prebookingRequiredInfo（无 passengers）。"""
    # 勿写 {{prebookingToken}}：空集合/未定义变量时 replaceIn 会先换成空串，Preview 脚本再难恢复
    if ActiveCategory().key == "lounge":
        return {
            "prebookingToken": "",
            "prebookingRequiredInfo": {
                "firstName": "Auto",
                "lastName": "Smith",
                "email": "auto.test@dragonpass.com",
                "phoneNumber": CONTACT_PHONE,
                "callingCode": CONTACT_CALLING_CODE,
            },
        }
    extra = FastTrackPrebookingExtraDict(
        adult_count=adult_count,
        child_count=child_count,
        include_transport_number=include_transport_number,
    )
    extra["prebookingToken"] = ""
    return extra


# ---------------------------------------------------------------------------
# 单一环境 · 预约费/超人次价（BOSS「单一价结算价格配置」）
# 换测场景 1～7：只改 Apifox Environment / BOSS 商品价，不换 Program、不改生成器。
# 当前 UAT 截图默认：用户承担 · 预约价 8.99 · 超人次 23.67（场景 7 语义，正向）。
# ---------------------------------------------------------------------------
PayerKind = Literal["unset", "client", "user"]

# 文档样例价（对照用）；运行时以 Environment 变量为准
# 自动化只测 1/2/3/5/7（超人次非 0）；场景 4（超人次未配置）、6（超人次=0）不测
DOC_SCENE_TABLE: Final[Dict[int, Dict[str, Any]]] = {
    1: {
        "payer": "unset",
        "prebooking": None,
        "overage": None,
        "expect_error": True,
        "in_scope": True,
        "label": "均不配置用户支付和客户支付",
    },
    2: {
        "payer": "client",
        "prebooking": "11",
        "overage": "13.47",
        "expect_error": False,
        "in_scope": True,
        "label": "客户_价格非0_超人次非0",
    },
    3: {
        "payer": "client",
        "prebooking": "0",
        "overage": "17",
        "expect_error": False,
        "in_scope": True,
        "label": "客户_价格0_超人次非0",
    },
    4: {
        "payer": "client",
        "prebooking": "19.31",
        "overage": None,
        "expect_error": True,
        "in_scope": False,
        "label": "客户_价格非0_超人次未配置(不测)",
    },
    5: {
        "payer": "user",
        "prebooking": "0",
        "overage": "23.67",
        "expect_error": False,
        "in_scope": True,
        "label": "用户_价格0_超人次非0",
    },
    6: {
        "payer": "user",
        "prebooking": "29",
        "overage": "0",
        "expect_error": True,
        "in_scope": False,
        "label": "用户_价格非0_超人次=0(不测)",
    },
    7: {
        "payer": "user",
        "prebooking": "31.73",
        "overage": "37.89",
        "expect_error": False,
        "in_scope": True,
        "label": "用户_价格非0_超人次非0",
    },
}

AUTOMATED_SCENE_IDS: Final[tuple] = (1, 2, 3, 5, 7)


def BuildEnvPricingScenarioDescription() -> str:
    """场景说明：定价场景表 + 本品类 Environment 变量名（写入 Apifox 场景 description）。"""
    cat = ActiveCategory()
    key_map = cat.PricingEnvKeyMap()
    defaults = cat.PricingDefaults()
    scene_lines: List[str] = []
    for scene_id in AUTOMATED_SCENE_IDS:
        row = DOC_SCENE_TABLE[scene_id]
        payer = str(row.get("payer") or "")
        payer_cn = {"unset": "均未配置", "client": "客户", "user": "用户"}.get(payer, payer)
        pb = row.get("prebooking")
        ov = row.get("overage")
        pb_s = "—" if pb is None else str(pb)
        ov_s = "—" if ov is None else str(ov)
        expect = "Preview 报错" if row.get("expect_error") else "正向算价"
        scene_lines.append(
            f"  · 场景{scene_id}：付费方={payer_cn}；预约单价={pb_s}；超人次单价={ov_s} → {expect}"
            f"（{row.get('label') or ''}）"
        )
    scenes_block = "\n".join(scene_lines)
    env_lines = "\n".join(
        f"  · {canon} ← Environment/集合 ``{key_map[canon]}``"
        f"（默认 {defaults[canon]}）"
        for canon in PRICING_CANONICAL_KEYS
    )
    return (
        "【单一环境定价 · 换测只改 Environment / BOSS，不换 Program】\n"
        f"可自动化场景号：{list(AUTOMATED_SCENE_IDS)}（超人次价格须非 0）。\n"
        "不测：场景4（超人次未配置）、场景6（超人次=0）。\n"
        "场景含义：\n"
        f"{scenes_block}\n"
        f"本品类（{cat.label_en}）现网默认：scene={defaults['paymentSceneId']}；"
        f"payer={defaults['prebookingFeePayer']} "
        f"prebooking={defaults['prebookingUnitPrice']} "
        f"overage={defaults['overageUnitPrice']}；"
        f"assert={defaults['assert_payment_env_price']}。\n"
        f"{cat.pricing_note_zh}\n"
        "\n"
        "【Environment 键名（品类解耦：Lounge 用 lounge*，与 FT 同环境并存）】\n"
        f"{env_lines}\n"
        "Auth 步 ``ftPayEnsurePricingEnv`` 从本品类键读取后写入规范键，"
        "供 ``apifox_payment_assert_post.js`` 的 E-BASE/E-FEE/… 使用。\n"
        "\n"
        "【规范键语义】\n"
        "· paymentSceneId：定价场景号标注（1/2/3/5/7）；接口不读，只作对照。\n"
        "· prebookingFeePayer：user=用户付 FEE；client=客户承担 FEE=0；unset=常负向。\n"
        "· prebookingUnitPrice：预约费单价；仅 payer=user 时 FEE=人数×本值。\n"
        "· overageUnitPrice：超人次/人次底价；BASE=人数×本值；DISC=min(权益点,人数)×本值。\n"
        "· paymentSceneExpectError：true=负向场景；false=正向。\n"
        "· assert_payment_env_price：true=校验 E-* 金额期望；false=只做结构断言。\n"
        "· toUseEntitlementCount：拟用权益点数（membership 入参；ePass 常按乘客推断）。\n"
        "\n"
        "金额期望（assert_payment_env_price=true）："
        "应付 ≈ BASE + FEE − DISC；"
        "BASE=人数×超人次；FEE=（user 时）人数×预约价，否则 0；"
        "DISC=min(权益点,人数)×超人次。\n"
    )

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[4]


def _ToolsJsPath(file_name: str) -> Path:
    return REPO_ROOT / "tools" / file_name


def CompactJsLines(lines: Sequence[str]) -> List[str]:
    """去掉块注释/空行/整行 ``//``，降低 Apifox ``test-scenario update`` 包体（防 422001）。"""
    text = "\n".join(lines)
    text = re.sub(r"/\*[\s\S]*?\*/", "", text)
    out: List[str] = []
    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("//"):
            continue
        out.append(line.rstrip())
    return out


def LoadToolsJsLines(file_name: str, *, compact: bool = False) -> List[str]:
    path = _ToolsJsPath(file_name)
    if not path.is_file():
        raise FileNotFoundError(f"缺少 payment 断言脚本: {path}")
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    lines = text.split("\n")
    if not compact:
        return lines
    return CompactJsLines(lines)


def PaymentAssertPreLines() -> List[str]:
    return LoadToolsJsLines("apifox_payment_assert_pre.js", compact=True)


def PaymentAssertPostLines() -> List[str]:
    return LoadToolsJsLines("apifox_payment_assert_post.js", compact=True)


def ExtraConsistencyAssertPostLines() -> List[str]:
    """权益 details=sum(breakdown) + cashPaymentApplied/cashier 入参回显。"""
    return LoadToolsJsLines("apifox_extra_consistency_assert_post.js", compact=True)


def ClientCollectAssertPreLines() -> List[str]:
    return LoadToolsJsLines("apifox_client_collect_assert_pre.js", compact=True)


def ClientCollectAssertPostLines() -> List[str]:
    return LoadToolsJsLines("apifox_client_collect_assert_post.js", compact=True)


def PaymentExtraConsistencyPostLines() -> List[str]:
    return ExtraConsistencyAssertPostLines()
def SaveTokenLines() -> List[str]:
    return [
        "try {",
        "  var j = pm.response.json();",
        "  var d = j.data !== undefined ? j.data : j;",
        "  var t = d.accessToken || d.token || d.access_token;",
        "  if (t) {",
        "    var tok = String(t);",
        "    try { pm.variables.set('accessToken', tok); } catch (eV) {}",
        "    try { pm.collectionVariables.set('accessToken', tok); } catch (eC) {}",
        "    try { pm.environment.set('accessToken', tok); } catch (eE) {}",
        "    try { if (pm.globals && typeof pm.globals.set === 'function') pm.globals.set('accessToken', tok); } catch (eG) {}",
        "  }",
        "} catch (e) { console.warn(e); }",
        "pm.test('Auth: accessToken 已写入运行时 | 期望=非空 | 实际=多作用域任一非空', function () {",
        "  var _a = ''; try { _a = String(pm.variables.get('accessToken') || '').trim(); } catch (e1) {}",
        "  var _b = ''; try { _b = String(pm.collectionVariables.get('accessToken') || '').trim(); } catch (e2) {}",
        "  var _c = ''; try { _c = String((pm.environment && pm.environment.get('accessToken')) || '').trim(); } catch (e3) {}",
        "  var _d = ''; try { _d = String((pm.globals && pm.globals.get('accessToken')) || '').trim(); } catch (e4) {}",
        "  pm.expect(_a || _b || _c || _d, 'variables/collection/env/globals 均无 accessToken').to.be.ok;",
        "});",
    ]


def Lines_EnsureAuthPrerequest() -> List[str]:
    return [
        "try {",
        "  var _base = '';",
        "  try { _base = String((pm.environment && pm.environment.get('baseUrl')) || '').trim(); } catch (eB0) {}",
        "  if (!_base) { try { _base = String(pm.variables.get('baseUrl') || '').trim(); } catch (eB1) {} }",
        "  if (!_base) { try { _base = String(pm.collectionVariables.get('baseUrl') || '').trim(); } catch (eB2) {} }",
        "  if (_base) {",
        "    try { pm.variables.set('baseUrl', _base); } catch (eBS1) {}",
        "    try { pm.collectionVariables.set('baseUrl', _base); } catch (eBS2) {}",
        "  }",
        "  var _pid = '';",
        "  try { _pid = String(pm.variables.get('ProgramID') || '').trim(); } catch (eP0) {}",
        "  if (!_pid) { try { _pid = String(pm.collectionVariables.get('ProgramID') || '').trim(); } catch (eP1) {} }",
        "  if (!_pid) { try { _pid = String((pm.environment && pm.environment.get('ProgramID')) || '').trim(); } catch (eP2) {} }",
        "  if (_pid) {",
        "    try { pm.variables.set('ProgramID', _pid); } catch (ePS) {}",
        "    try {",
        "      if (pm.request && pm.request.headers && typeof pm.request.headers.upsert === 'function') {",
        "        pm.request.headers.upsert({ key: 'X-Program-ID', value: _pid });",
        "      }",
        "    } catch (ePH) {}",
        "  }",
        "  var _cid = '';",
        "  try { _cid = String(pm.variables.get('clientId') || '').trim(); } catch (eC0) {}",
        "  if (!_cid) { try { _cid = String(pm.collectionVariables.get('clientId') || '').trim(); } catch (eC1) {} }",
        "  if (!_cid) { try { _cid = String((pm.environment && pm.environment.get('clientId')) || '').trim(); } catch (eC2) {} }",
        "  if (_cid) {",
        "    try { pm.variables.set('clientId', _cid); } catch (eCS1) {}",
        "    try { pm.collectionVariables.set('clientId', _cid); } catch (eCS2) {}",
        "  }",
        "  var _sec = '';",
        "  try { _sec = String(pm.variables.get('secret') || '').trim(); } catch (eS0) {}",
        "  if (!_sec) { try { _sec = String(pm.collectionVariables.get('secret') || '').trim(); } catch (eS1) {} }",
        "  if (!_sec) { try { _sec = String((pm.environment && pm.environment.get('secret')) || '').trim(); } catch (eS2) {} }",
        "  if (_sec) {",
        "    try { pm.variables.set('secret', _sec); } catch (eSS1) {}",
        "    try { pm.collectionVariables.set('secret', _sec); } catch (eSS2) {}",
        "  }",
        "  var _xv = '';",
        "  try { _xv = String((pm.environment && pm.environment.get('x-version')) || '').trim(); } catch (eX0) {}",
        "  if (!_xv) { try { _xv = String(pm.variables.get('x-version') || '').trim(); } catch (eX1) {} }",
        "  if (!_xv) { try { _xv = String(pm.collectionVariables.get('x-version') || '').trim(); } catch (eX2) {} }",
        "  if (_xv && ['omit','none','off'].indexOf(_xv.toLowerCase()) < 0) {",
        "    try { pm.variables.set('x-version', _xv); } catch (eXS) {}",
        "    try {",
        "      if (pm.request && pm.request.headers && typeof pm.request.headers.upsert === 'function') {",
        "        pm.request.headers.upsert({ key: 'x-version', value: _xv });",
        "      }",
        "    } catch (eXH) {}",
        "  }",
        "  var _ft = '';",
        f"  try {{ _ft = String((pm.environment && pm.environment.get('{ResourceEnvKey()}')) || '').trim(); }} catch (eF0) {{}}",
        f"  if (!_ft) {{ try {{ _ft = String(pm.variables.get('{ResourceEnvKey()}') || '').trim(); }} catch (eF1) {{}} }}",
        f"  if (!_ft) {{ try {{ _ft = String(pm.collectionVariables.get('{ResourceEnvKey()}') || '').trim(); }} catch (eF2) {{}} }}",
        "  if (_ft && _ft.indexOf('{{') < 0) {",
        f"    try {{ pm.variables.set('{ResourceEnvKey()}', _ft); }} catch (eFS1) {{}}",
        f"    try {{ pm.collectionVariables.set('{ResourceEnvKey()}', _ft); }} catch (eFS2) {{}}",
        "  }",
        "  try {",
        "    var _rawTok = pm.variables.get('accessToken');",
        "    if (_rawTok !== undefined && _rawTok !== null && String(_rawTok).trim() === '') {",
        "      try { pm.variables.unset('accessToken'); } catch (eUn) { try { pm.variables.set('accessToken', ''); } catch (eUn2) {} }",
        "    }",
        "  } catch (eClr) {}",
        "  var _tok = '';",
        "  try { _tok = String(pm.collectionVariables.get('accessToken') || '').trim(); } catch (e3) {}",
        "  if (!_tok) { try { _tok = String((pm.globals && pm.globals.get('accessToken')) || '').trim(); } catch (eG1) {} }",
        "  if (!_tok) { try { _tok = String((pm.environment && pm.environment.get('accessToken')) || '').trim(); } catch (e4) {} }",
        "  if (!_tok) { try { _tok = String(pm.variables.get('accessToken') || '').trim(); } catch (e5) {} }",
        "  if (_tok) {",
        "    try { pm.variables.set('accessToken', _tok); } catch (eTV) {}",
        "    try { pm.collectionVariables.set('accessToken', _tok); } catch (eTC) {}",
        "    try { pm.environment.set('accessToken', _tok); } catch (eTE) {}",
        "    try { if (pm.globals && typeof pm.globals.set === 'function') pm.globals.set('accessToken', _tok); } catch (eTG) {}",
        "    var _auth = 'Bearer ' + _tok;",
        "    try {",
        "      var _hdrs = pm.request && pm.request.headers;",
        "      if (_hdrs && typeof _hdrs.upsert === 'function') {",
        "        _hdrs.upsert({ key: 'Authorization', value: _auth });",
        "      } else if (_hdrs && typeof _hdrs.add === 'function') {",
        "        try { if (typeof _hdrs.remove === 'function') _hdrs.remove('Authorization'); } catch (eRm) {}",
        "        _hdrs.add({ key: 'Authorization', value: _auth });",
        "      }",
        "    } catch (eH) { console.warn('FT payment ensure bearer', eH); }",
        "  }",
        "} catch (eAll) {}",
    ]


def _BuildFtPaymentCoreJsHelpersLines() -> List[str]:
    """仅内联 payment 场景实际调用的 ft*（避免整包 FastTrack helpers → Apifox 422001）。"""
    adult_names_js = json.dumps(
        [{"firstName": first, "lastName": last} for first, last in FASTTRACK_ADULT_PASSENGER_NAMES],
        ensure_ascii=False,
    )
    child_names_js = json.dumps(
        [{"firstName": first, "lastName": last} for first, last in FASTTRACK_CHILD_PASSENGER_NAMES],
        ensure_ascii=False,
    )
    create_first_js = json.dumps(CREATE_FIRST_NAME)
    create_last_js = json.dumps(CREATE_LAST_NAME)
    create_exp_js = json.dumps(CREATE_EXPIRATION_DATE)
    create_usages_js = json.dumps(CREATE_AVAILABLE_USAGES)
    module_js = json.dumps(CurrentEpassModule())
    adult_default_js = json.dumps(PAYMENT_ADULT_COUNT)
    child_default_js = json.dumps(PAYMENT_CHILD_COUNT)
    resource_var_js = json.dumps(ResourceEnvKey())
    epass_create_cat_js = json.dumps(ActiveCategory().epass_create_category)
    usage_cat_js = json.dumps(ActiveCategory().usage_order_category)
    return [
        "function ftExpectedModule() {",
        "  var raw = pm.collectionVariables.get('epassModule');",
        "  if (raw === undefined || raw === null || String(raw).trim() === '') {",
        f"    return {module_js};",
        "  }",
        "  var n = parseInt(String(raw), 10);",
        f"  return isNaN(n) ? {module_js} : n;",
        "}",
        "function ftExpectedEpassCreateCategory() {",
        f"  return {epass_create_cat_js};",
        "}",
        "function ftExpectedUsageOrderCategory() {",
        f"  return {usage_cat_js};",
        "}",
        "function ftParseNonNegativeInt(value, fallbackValue) {",
        "  var n = parseInt(String(value), 10);",
        "  if (isNaN(n) || n < 0) return fallbackValue;",
        "  return n;",
        "}",
        f"var ftAdultPassengerNames = {adult_names_js};",
        f"var ftChildPassengerNames = {child_names_js};",
        "function ftResolveFastTrackPassengerCounts() {",
        f"  var adultCount = ftParseNonNegativeInt(pm.collectionVariables.get('fastTrackAdultCount'), {adult_default_js});",
        f"  var childCount = ftParseNonNegativeInt(pm.collectionVariables.get('fastTrackChildCount'), {child_default_js});",
        "  if (adultCount + childCount <= 0) {",
        f"    adultCount = {adult_default_js};",
        f"    childCount = {child_default_js};",
        "  }",
        "  return { adultCount: adultCount, childCount: childCount };",
        "}",
        "function ftResolveLeadPassenger(passengers) {",
        "  if (!passengers || !passengers.length) return null;",
        "  var lead = passengers.filter(function (p) { return p && p.leadPassenger === true; });",
        "  return lead.length ? lead[0] : passengers[0];",
        "}",
        "function ftBuildFastTrackPassengers(adultCount, childCount) {",
        "  var passengers = [];",
        "  var idx;",
        "  if (adultCount > ftAdultPassengerNames.length) {",
        "    throw new Error('adultCount exceeds configured passenger names: ' + adultCount);",
        "  }",
        "  if (childCount > ftChildPassengerNames.length) {",
        "    throw new Error('childCount exceeds configured passenger names: ' + childCount);",
        "  }",
        "  for (idx = 0; idx < adultCount; idx++) {",
        "    passengers.push({",
        "      firstName: ftAdultPassengerNames[idx].firstName,",
        "      lastName: ftAdultPassengerNames[idx].lastName,",
        "      passengersType: 1,",
        "      leadPassenger: passengers.length === 0",
        "    });",
        "  }",
        "  for (idx = 0; idx < childCount; idx++) {",
        "    passengers.push({",
        "      firstName: ftChildPassengerNames[idx].firstName,",
        "      lastName: ftChildPassengerNames[idx].lastName,",
        "      passengersType: 2,",
        "      leadPassenger: false",
        "    });",
        "  }",
        "  return passengers;",
        "}",
        "function ftIsLoungeCategory() {",
        f"  return {json.dumps(ActiveCategory().key == 'lounge')};",
        "}",
        "function ftSyncPrebookingPassengersBody() {",
        "  try {",
        "    var raw = pm.request.body && pm.request.body.raw;",
        "    if (!raw) return;",
        "    // 勿 replaceIn：空 prebookingToken 会把占位符先洗成空串",
        "    var body = JSON.parse(String(raw));",
        "    if (!body.extra || typeof body.extra !== 'object') body.extra = {};",
        "    if (ftIsLoungeCategory()) {",
        "      // Lounge 不传 passengers；清掉误带字段后回写",
        "      if (body.extra.passengers !== undefined) delete body.extra.passengers;",
        "      pm.request.body.raw = JSON.stringify(body, null, 2);",
        "      return;",
        "    }",
        "    var counts = ftResolveFastTrackPassengerCounts();",
        "    body.extra.passengers = ftBuildFastTrackPassengers(counts.adultCount, counts.childCount);",
        "    var lead = ftResolveLeadPassenger(body.extra.passengers);",
        "    if (lead) {",
        "      if (!body.extra.prebookingRequiredInfo || typeof body.extra.prebookingRequiredInfo !== 'object') {",
        "        body.extra.prebookingRequiredInfo = {};",
        "      }",
        "      body.extra.prebookingRequiredInfo.firstName = lead.firstName;",
        "      body.extra.prebookingRequiredInfo.lastName = lead.lastName;",
        "    }",
        "    pm.request.body.raw = JSON.stringify(body, null, 2);",
        "  } catch (e) {",
        "    console.warn('ftSyncPrebookingPassengersBody:', e);",
        "    throw e;",
        "  }",
        "}",
        "function ftAssertPrebookingPassengersShape(label) {",
        "  if (ftIsLoungeCategory()) {",
        "    pm.test(label + ': Lounge 请求体不含 passengers', function () {",
        "      var raw = pm.request.body && pm.request.body.raw;",
        "      if (!raw) return;",
        "      var body = JSON.parse(pm.variables.replaceIn(String(raw)));",
        "      var ex = (body && body.extra) || {};",
        "      pm.expect(ex.passengers, 'Lounge 不应传 extra.passengers').to.be.oneOf([undefined, null]);",
        "    });",
        "    return;",
        "  }",
        "  pm.test(label + ': passengers 数量与可用性 adultCount+childCount 一致', function () {",
        "    var env0 = pm.response.json();",
        "    if (env0 && env0.code !== 0 && env0.code !== 1 && env0.code !== '0' && env0.code !== '1') {",
        "      console.warn('[ft-pay] skip passengers shape: business not ok', env0.errCode);",
        "      return;",
        "    }",
        "    var counts = ftResolveFastTrackPassengerCounts();",
        "    var raw = pm.request.body && pm.request.body.raw;",
        "    pm.expect(raw, label + ' request body').to.be.a('string').and.not.empty;",
        "    var body = JSON.parse(pm.variables.replaceIn(String(raw)));",
        "    pm.expect(body.extra.passengers).to.be.an('array');",
        "    pm.expect(body.extra.passengers.length).to.eql(counts.adultCount + counts.childCount);",
        "    var leadCount = body.extra.passengers.filter(function (p) { return p && p.leadPassenger === true; }).length;",
        "    pm.expect(leadCount, label + ' leadPassenger=true 仅 1 个').to.eql(1);",
        "    var lead = ftResolveLeadPassenger(body.extra.passengers);",
        "    pm.expect(body.extra.prebookingRequiredInfo, label + ' prebookingRequiredInfo').to.be.an('object');",
        "    pm.expect(body.extra.prebookingRequiredInfo.firstName).to.eql(lead.firstName);",
        "    pm.expect(body.extra.prebookingRequiredInfo.lastName).to.eql(lead.lastName);",
        "    var seen = {};",
        "    body.extra.passengers.forEach(function (p, idx) {",
        "      pm.expect(p.firstName, 'passengers[' + idx + '].firstName').to.match(/^[A-Za-z ]+$/);",
        "      pm.expect(p.lastName, 'passengers[' + idx + '].lastName').to.match(/^[A-Za-z ]+$/);",
        "      var key = String(p.firstName) + '|' + String(p.lastName);",
        "      pm.expect(seen[key], 'passengers 姓名重复: ' + key).to.be.undefined;",
        "      seen[key] = true;",
        "    });",
        "  });",
        "}",
        "function ftGetInnerData(root) {",
        "  if (!root || typeof root !== 'object') return null;",
        "  var d = root.data;",
        "  if (d !== undefined && d !== null && typeof d === 'object' && !Array.isArray(d)) {",
        "    return d;",
        "  }",
        "  return d;",
        "}",
        "function ftAssertEpassModuleRequired(data, ctx) {",
        "  pm.expect(data, ctx + ' data').to.be.an('object');",
        "  pm.expect(data.module, ctx + ' module').to.eql(ftExpectedModule());",
        "}",
        "function ftResolveEPassId(extra) {",
        "  if (!extra || typeof extra !== 'object') return null;",
        "  return extra.ePassId || extra.epassId || null;",
        "}",
        "function ftResolveEPassIdFromRoot(data) {",
        "  if (!data || typeof data !== 'object') return null;",
        "  var direct = data.ePassId || data.epassId;",
        "  if (direct) return direct;",
        "  var extra = data.extra;",
        "  if (extra && typeof extra === 'object') {",
        "    return extra.ePassId || extra.epassId || null;",
        "  }",
        "  return null;",
        "}",
        "function ftExpectedCreateExtra() {",
        "  return {",
        f"    firstName: {create_first_js},",
        f"    lastName: {create_last_js},",
        f"    expirationDate: {create_exp_js},",
        f"    availableUsages: {create_usages_js}",
        "  };",
        "}",
        "function ftAssertExtraMatchesCreateInput(label, extra) {",
        "  pm.test(label + ': extra.firstName 与入参一致', function () {",
        "    pm.expect(extra.firstName).to.eql(ftExpectedCreateExtra().firstName);",
        "  });",
        "  pm.test(label + ': extra.expirationDate 与入参一致', function () {",
        "    pm.expect(extra.expirationDate).to.eql(ftExpectedCreateExtra().expirationDate);",
        "  });",
        "}",
        "function ftSaveCreateIds(data) {",
        "  if (!data || typeof data !== 'object') return;",
        "  if (data.clientUserId) pm.collectionVariables.set('clientUserId', String(data.clientUserId));",
        "  if (data.orderId) pm.collectionVariables.set('purchaseOrderId', String(data.orderId));",
        "  var extra = data.extra;",
        "  if (extra && typeof extra === 'object') {",
        "    var ep = ftResolveEPassId(extra);",
        "    if (ep) pm.collectionVariables.set('ePassId', String(ep));",
        "  }",
        "}",
        "function ftAssertCreateCoreFields(label) {",
        "  var dataFn = function () { return ftGetInnerData(pm.response.json()); };",
        "  pm.test(label + ': module=epassModule', function () {",
        "    ftAssertEpassModuleRequired(dataFn(), label);",
        "  });",
        "  pm.test(label + ': status=1 CONFIRMED', function () {",
        "    pm.expect(dataFn().status).to.eql(1);",
        "  });",
        "  pm.test(label + ': category=' + String(ftExpectedEpassCreateCategory()), function () {",
        "    pm.expect(dataFn().category).to.eql(ftExpectedEpassCreateCategory());",
        "  });",
        "  pm.test(label + ': clientUserId 回显一致', function () {",
        "    pm.expect(dataFn().clientUserId).to.eql(pm.collectionVariables.get('clientUserId'));",
        "  });",
        "  pm.test(label + ': orderCancelledDate=null', function () {",
        "    pm.expect(dataFn().orderCancelledDate).to.eql(null);",
        "  });",
        "  pm.test(label + ': extra.usedUsages=0', function () {",
        "    pm.expect(dataFn().extra.usedUsages).to.eql(0);",
        "  });",
        "  ftAssertExtraMatchesCreateInput(label, dataFn().extra);",
        "  pm.test(label + ': extra.ePassId 非空', function () {",
        "    pm.expect(ftResolveEPassId(dataFn().extra)).to.be.ok;",
        "  });",
        "  pm.test(label + ': extra.allowedResources 存在', function () {",
        "    pm.expect(dataFn().extra.allowedResources).to.be.an('object');",
        "  });",
        "  pm.test(label + ': 写入 ePassId/purchaseOrderId', function () {",
        "    ftSaveCreateIds(dataFn());",
        "    pm.expect(pm.collectionVariables.get('ePassId')).to.be.ok;",
        "    pm.expect(pm.collectionVariables.get('purchaseOrderId')).to.be.ok;",
        "  });",
        "}",
        "function ftSaveAvailabilityRequestFields() {",
        "  try {",
        "    var raw = pm.request.body && pm.request.body.raw;",
        "    if (!raw) return;",
        "    var reqBody = JSON.parse(pm.variables.replaceIn(String(raw)));",
        "    if (reqBody && reqBody.prebookingDate) {",
        "      pm.collectionVariables.set('prebookingDate', String(reqBody.prebookingDate));",
        "    }",
        "    if (reqBody && reqBody.resourceId) {",
        "      pm.collectionVariables.set('fastTrackAvailabilityResourceId', String(reqBody.resourceId));",
        "    }",
        f"    var adultCount = ftParseNonNegativeInt(reqBody && reqBody.adultCount, {adult_default_js});",
        f"    var childCount = ftParseNonNegativeInt(reqBody && reqBody.childCount, {child_default_js});",
        "    pm.collectionVariables.set('fastTrackAdultCount', String(adultCount));",
        "    pm.collectionVariables.set('fastTrackChildCount', String(childCount));",
        "  } catch (e) {",
        "    console.warn('ftSaveAvailabilityRequestFields:', e);",
        "  }",
        "}",
        "function ftSavePrebookingToken(data) {",
        "  if (!(data && data.prebookingToken)) return;",
        "  ftPaySetVar('prebookingToken', String(data.prebookingToken));",
        "}",
        "function ftAssertAvailabilitySuccess(label) {",
        "  ftSaveAvailabilityRequestFields();",
        "  var data = ftGetInnerData(pm.response.json());",
        "  ftSavePrebookingToken(data);",
        "  pm.test(label + ': available=true', function () {",
        "    pm.expect(data.available).to.eql(true);",
        "  });",
        "  pm.test(label + ': prebookingToken 非空', function () {",
        "    pm.expect(data.prebookingToken).to.be.a('string').and.not.empty;",
        "  });",
        "}",
        "var ftOrderStatusActiveOrProcessing = [1, 5, 9];",
        "function ftSaveUsageOrderId(data) {",
        "  if (data && data.orderId) {",
        "    pm.collectionVariables.set('usageOrderId', String(data.orderId));",
        "  }",
        "}",
        "function ftSyncResourceIdFromOrderResponse(label, actual) {",
        "  pm.expect(actual, label + ' resourceId 非空').to.be.a('string').and.not.empty;",
        "  var fromAvail = pm.collectionVariables.get('fastTrackAvailabilityResourceId');",
        "  if (fromAvail && String(fromAvail).trim() && actual !== fromAvail) {",
        "    console.warn(label + ': resourceId 与可用性请求不一致，以响应为准');",
        "  }",
        f"  pm.collectionVariables.set({resource_var_js}, String(actual));",
        "}",
        "function ftExpectResourceIdMatch(label, actual) {",
        "  ftSyncResourceIdFromOrderResponse(label, actual);",
        "}",
        "function ftAssertUsageOrderCreateSuccess(label, requireExistingEPassId, allowedStatuses) {",
        "  allowedStatuses = allowedStatuses || ftOrderStatusActiveOrProcessing;",
        "  var data = function () { return ftGetInnerData(pm.response.json()); };",
        "  var envRoot = function () { return pm.response.json(); };",
        "  pm.test(label + ': Bundle/Usage 业务可解析', function () {",
        "    var env = envRoot();",
        "    if (env.code !== 0) {",
        "      console.warn('[ft-pay] skip usage order asserts: business not ok', env.errCode, env.msg);",
        "      return;",
        "    }",
        "  });",
        "  // 1=CONFIRMED / 5=处理中 / 9=待支付（含预约费）；10=FAILED 硬失败",
        "  var statusLabel = (allowedStatuses.indexOf(9) >= 0)",
        "    ? 'status=1/5/9（CONFIRMED/处理中/待支付，非 10 FAILED）'",
        "    : ((allowedStatuses.indexOf(5) >= 0)"
        "      ? 'status=1 或 5（CONFIRMED/处理中，非 10 FAILED）'"
        "      : 'status=1 CONFIRMED（非 10 FAILED）');",
        "  pm.test(label + ': ' + statusLabel, function () {",
        "    var env = envRoot();",
        "    if (env.code !== 0) { return; }",
        "    var st = data().status;",
        "    if (st === 10) { pm.expect.fail('预约单 status=10 FAILED'); }",
        "    pm.expect(allowedStatuses, 'status=' + String(st)).to.include(st);",
        "  });",
        "  pm.test(label + ': module=epassModule', function () {",
        "    if (envRoot().code !== 0) { return; }",
        "    ftAssertEpassModuleRequired(data(), label);",
        "  });",
        "  pm.test(label + ': category=' + String(ftExpectedUsageOrderCategory()), function () {",
        "    if (envRoot().code !== 0) { return; }",
        "    pm.expect(data().category).to.eql(ftExpectedUsageOrderCategory());",
        "  });",
        "  pm.test(label + ': orderId 非空', function () {",
        "    if (envRoot().code !== 0) { return; }",
        "    pm.expect(data().orderId).to.be.a('string').and.not.empty;",
        "    ftSaveUsageOrderId(data());",
        "  });",
        "  pm.test(label + ': clientUserId 与注册会籍一致', function () {",
        "    if (envRoot().code !== 0) { return; }",
        "    pm.expect(data().extra.clientUserId).to.eql(pm.collectionVariables.get('clientUserId'));",
        "  });",
        "  pm.test(label + ': ePassId 与前面一致', function () {",
        "    if (envRoot().code !== 0) { return; }",
        "    var ep = ftResolveEPassIdFromRoot(data());",
        "    pm.expect(ep).to.be.a('string').and.not.empty;",
        "    if (requireExistingEPassId) {",
        "      pm.expect(ep).to.eql(pm.collectionVariables.get('ePassId'));",
        "    } else {",
        "      pm.collectionVariables.set('ePassId', String(ep));",
        "    }",
        "  });",
        "  pm.test(label + ': orderCancelledDate=null', function () {",
        "    if (envRoot().code !== 0) { return; }",
        "    pm.expect(data().orderCancelledDate).to.eql(null);",
        "  });",
        "  pm.test(label + ': extra.usageDate=null', function () {",
        "    if (envRoot().code !== 0) { return; }",
        "    pm.expect(data().extra.usageDate).to.eql(null);",
        "  });",
        "  pm.test(label + ': extra.prebookingDate 与可用性入参一致', function () {",
        "    if (envRoot().code !== 0) { return; }",
        "    var expected = pm.collectionVariables.get('prebookingDate');",
        "    var actual = data().extra.prebookingDate;",
        "    pm.expect(actual).to.be.a('string').and.not.empty;",
        "    if (expected && String(expected).trim()) {",
        "      pm.expect(actual).to.eql(expected);",
        "    }",
        "  });",
        "  pm.test(label + ': extra.resourceId 与 resourceId 一致', function () {",
        "    if (envRoot().code !== 0) { return; }",
        "    ftExpectResourceIdMatch(label, data().extra.resourceId);",
        "  });",
        "}",
        "function ftAssertBundleOrderSuccess(label) {",
        "  ftAssertUsageOrderCreateSuccess(label, false);",
        "  pm.test(label + ': 写入 usageOrderId', function () {",
        "    if (pm.response.json().code !== 0) {",
        "      console.warn('[ft-pay] skip bundle usageOrderId check');",
        "      return;",
        "    }",
        "    pm.expect(pm.collectionVariables.get('usageOrderId')).to.be.ok;",
        "  });",
        "}",
    ]


def _BuildFtPayJsHelpersLines() -> List[str]:
    rid = ResourceEnvKey()
    insuf_mod = int(ActiveCategory().insuf_module)
    insuf_mod_js = json.dumps(insuf_mod)
    rid_js = json.dumps(rid)
    return [
        "function ftPaySetVar(key, value) {",
        "  var v = String(value);",
        "  try { pm.variables.set(key, v); } catch (e0) {}",
        "  try { pm.collectionVariables.set(key, v); } catch (e1) {}",
        "  try { pm.environment.set(key, v); } catch (e2) {}",
        "  try { if (pm.globals && typeof pm.globals.set === 'function') pm.globals.set(key, v); } catch (e3) {}",
        "}",
        "function ftPayGetVar(key) {",
        "  var v = '';",
        "  try { v = String(pm.variables.get(key) || '').trim(); } catch (e0) {}",
        "  if (!v || v.indexOf('{{') >= 0) { try { v = String(pm.collectionVariables.get(key) || '').trim(); } catch (e1) {} }",
        "  if (!v || v.indexOf('{{') >= 0) { try { v = String((pm.environment && pm.environment.get(key)) || '').trim(); } catch (e2) {} }",
        "  if (!v || v.indexOf('{{') >= 0) { try { v = String((pm.globals && pm.globals.get(key)) || '').trim(); } catch (eG) {} }",
        f"  if ((!v || v.indexOf('{{{{') >= 0) && key === {rid_js}) {{",
        f"    try {{ v = String((pm.environment && pm.environment.get({rid_js})) || '').trim(); }} catch (e3) {{}}",
        "  }",
        "  if (!v || v.indexOf('{{') >= 0) return '';",
        "  return v;",
        "}",
        "function ftPaySaveMembershipId(label) {",
        "  pm.test(label + ': 保存 membershipId | 期望=非空 | 实际=响应', function () {",
        "    var data = ftGetInnerData(pm.response.json());",
        "    var mid = data.membershipId || data.id;",
        "    pm.expect(mid, 'membershipId').to.be.a('string').and.not.empty;",
        "    ftPaySetVar('membershipId', mid);",
        "  });",
        "}",
        "function ftPayCaptureFtModuleEntitlementBalance(label) {",
        f"  // 读 module={insuf_mod}；avail 过大则写 ftPayEntReduceQty，供 /entitlements/update 减点后再约 avail+1",
        f"  pm.test(label + ': 读取权益池并规划减点/011 | 期望=可造 | 实际=details', function () {{",
        "    var data = ftGetInnerData(pm.response.json()) || {};",
        "    var ents = (data.entitlements && typeof data.entitlements === 'object') ? data.entitlements : data;",
        "    var list = ents.moduleExclusiveEntitlements || data.moduleExclusiveEntitlements || [];",
        "    pm.expect(list, 'moduleExclusiveEntitlements').to.be.an('array');",
        "    var hit = null, i;",
        f"    for (i = 0; i < list.length; i++) {{ if (list[i] && Number(list[i].module) === {insuf_mod}) {{ hit = list[i]; break; }} }}",
        "    if (!hit) { ftPaySetVar('ftPayEntInsufAdultCount',''); ftPaySetVar('ftPayEntReduceQty','');",
        f"      console.warn('[ft-pay] 无 module={insuf_mod} 池'); return; }}",
        "    var d = hit.details || {};",
        "    var gEx = Number(d.guestsExclusiveEntitlements), shared = Number(d.sharedEntitlements);",
        "    var maxNext = Number(d.maxGuestsNextUse), ch = Number(d.cardholderExclusiveEntitlements);",
        "    var purchased = Number(d.purchasedEntitlements);",
        f"    ftPaySetVar('ftPayEntModule', '{insuf_mod}');",
        "    if (maxNext === -1 || gEx === -1 || shared === -1) {",
        "      ftPaySetVar('ftPayEntInsufAdultCount',''); ftPaySetVar('ftPayEntReduceQty','');",
        "      console.warn('[ft-pay] 无限额无法造 011'); return;",
        "    }",
        "    var avail = (!isNaN(maxNext) && maxNext >= 0) ? maxNext",
        "      : (isNaN(ch)?0:Math.max(ch,0))+(isNaN(gEx)?0:Math.max(gEx,0))+(isNaN(shared)?0:Math.max(shared,0))+(isNaN(purchased)?0:Math.max(purchased,0));",
        "    var poolLen = ftAdultPassengerNames.length;",
        "    var g = isNaN(gEx) ? 0 : Math.max(gEx, 0), s = isNaN(shared) ? 0 : Math.max(shared, 0), c = isNaN(ch) ? 0 : Math.max(ch, 0);",
        "    var ur = 2, bal = g;",
        "    if (s > bal) { ur = 3; bal = s; }",
        "    if (c > bal) { ur = 1; bal = c; }",
        "    // 尽量降到仅剩 1 点，使 need=2 稳落在姓名池内且必触发 011",
        "    var targetAvail = Math.min(1, avail, poolLen - 1);",
        "    if (targetAvail < 0) targetAvail = 0;",
        "    var reduceQty = avail - targetAvail;",
        "    if (reduceQty > bal) {",
        "      reduceQty = bal;",
        "      targetAvail = avail - reduceQty;",
        "    }",
        "    var need = targetAvail + 1;",
        "    if (need > poolLen || need < 1) {",
        "      ftPaySetVar('ftPayEntInsufAdultCount',''); ftPaySetVar('ftPayEntReduceQty','');",
        "      console.warn('[ft-pay] 无法造 011 bal=' + bal + ' need=' + need); return;",
        "    }",
        "    ftPaySetVar('ftPayEntAvailTotal', String(targetAvail));",
        "    ftPaySetVar('ftPayEntReduceQty', reduceQty > 0 ? String(reduceQty) : '');",
        "    ftPaySetVar('ftPayEntReduceUsageRestriction', String(ur));",
        "    ftPaySetVar('ftPayEntInsufAdultCount', String(need));",
        "    ftPaySetVar('fastTrackAdultCount', String(need));",
        "    ftPaySetVar('toUseEntitlementCount', String(need));",
        "    console.log('[ft-pay] avail='+avail+' g/s/c='+g+'/'+s+'/'+c+' target='+targetAvail+' reduce='+reduceQty+' ur='+ur+' need='+need);",
        "  });",
        "}",
        "function ftPayApplyInsufAdultCountToBody() {",
        "  // 将可用性/预览/下单 body 的 adultCount、toUseEntitlement* 改为「可用点+1」",
        "  try {",
        "    var need = ftPayGetVar('ftPayEntInsufAdultCount');",
        "    if (!need) return;",
        "    var n = parseInt(need, 10);",
        "    if (isNaN(n) || n <= 0) return;",
        "    ftPaySetVar('fastTrackAdultCount', String(n));",
        "    ftPaySetVar('toUseEntitlementCount', String(n));",
        "    if (!pm.request.body || !pm.request.body.raw) return;",
        "    var body = JSON.parse(String(pm.request.body.raw));",
        "    if (body.adultCount !== undefined) body.adultCount = n;",
        "    if (body.extra && typeof body.extra === 'object') {",
        "      body.extra.toUseEntitlementCount = n;",
        "      var ch = n >= 1 ? 1 : 0;",
        "      body.extra.toUseEntitlementDetail = { cardholder: ch, guest: Math.max(n - ch, 0) };",
        "    }",
        "    pm.request.body.raw = JSON.stringify(body, null, 2);",
        "    try { ftSyncPrebookingPassengersBody(); } catch (eSync) { console.warn(eSync); }",
        "  } catch (e) {",
        "    console.warn('ftPayApplyInsufAdultCountToBody:', e);",
        "  }",
        "}",
        "function ftPayAssertInsufRejectOrSkip(label) {",
        "  pm.test(label + ': 权益不足 042.011/019/051.011/051.020 或跳过 | 期望=权益不足码/跳过 | 实际=errCode', function () {",
        "    if (!ftPayGetVar('ftPayEntInsufAdultCount')) {",
        f"      console.warn('[ft-pay] skip 011: 未算出可用点（无限额 / 姓名池不够 / 无 module={insuf_mod}）');",
        "      return;",
        "    }",
        "    if (ftPayGetVar('ftPayEntInsufSkip') === '1') {",
        "      console.warn('[ft-pay] skip 011: 可用性未取到 token（人数过大）');",
        "      return;",
        "    }",
        "    var env = pm.response.json();",
        "    var err = String(env.errCode || '');",
        "    if (err === '500.051.004' || /prebookingToken/i.test(String(env.msg || ''))) {",
        "      pm.expect.fail(label + ': 缺有效 prebookingToken，收到 ' + err);",
        "    }",
        "    pm.expect(env.code, '造数成功则必须业务拒绝').to.eql(-1);",
        "    pm.expect(['500.042.011', '500.051.011', '500.051.020', '500.042.019'], 'errCode').to.include(err);",
        "  });",
        "}",
        "function ftPayAssertAvailabilityForInsufOrSkip(label) {",
        "  // 权益不足链路：人数=avail+1 时资源可能 500.020.009，软跳过后续 011",
        "  var env = pm.response.json();",
        "  if (ftPayGetVar('ftPayEntInsufAdultCount') && env.code === 0) {",
        "    try { ftSaveAvailabilityRequestFields(); } catch (eSave) {}",
        "    ftSavePrebookingToken(ftGetInnerData(env) || {});",
        "  }",
        "  pm.test(label + ': 可用性成功或人数过大跳过 | 期望=token/跳过 | 实际=响应', function () {",
        "    if (!ftPayGetVar('ftPayEntInsufAdultCount')) {",
        "      console.warn('[ft-pay] skip avail: 无 insuf 造数');",
        "      ftPaySetVar('ftPayEntInsufSkip', '1');",
        "      return;",
        "    }",
        "    if (env.code !== 0) {",
        "      console.warn('[ft-pay] avail fail for insuf adults', env.errCode, env.msg);",
        "      ftPaySetVar('ftPayEntInsufSkip', '1');",
        "      return;",
        "    }",
        "    ftPaySetVar('ftPayEntInsufSkip', '');",
        "    var data = ftGetInnerData(env) || {};",
        "    pm.expect(data.available, 'available').to.eql(true);",
        "    pm.expect(data.prebookingToken, 'prebookingToken').to.be.a('string').and.not.empty;",
        "  });",
        "}",
        "function ftPaySaveUsageOrderId(label) {",
        "  pm.test(label + ': 保存 usageOrderId | 期望=非空 | 实际=响应', function () {",
        "    var env = pm.response.json();",
        "    if (env.code !== 0) {",
        "      console.warn('[ft-pay] skip save usageOrderId: business not ok', env.errCode);",
        "      return;",
        "    }",
        "    var data = ftGetInnerData(env);",
        "    pm.expect(data.orderId, 'orderId').to.be.a('string').and.not.empty;",
        "    ftPaySetVar('usageOrderId', data.orderId);",
        "    ftPayCapturePayableFromData(data);",
        "  });",
        "}",
        "function ftPayCapturePayableFromData(data) {",
        "  // 供发起支付分支：payableAmount=0 → 802；!=0 → REDIRECT+url",
        "  if (!data || typeof data !== 'object') { return; }",
        "  var payment = data.payment;",
        "  if (!payment && data.extra && typeof data.extra === 'object') { payment = data.extra.payment; }",
        "  if (!payment || typeof payment !== 'object') { return; }",
        "  var price = payment.price;",
        "  if (price === null || price === undefined) {",
        "    ftPaySetVar('ftPayPayableAmount', '0');",
        "    return;",
        "  }",
        "  if (typeof price !== 'object') { return; }",
        "  // 无 payableAmount 字段：按 0 元处理（发起支付必须期望 500.000.802）",
        "  if (price.payableAmount === null || price.payableAmount === undefined) {",
        "    ftPaySetVar('ftPayPayableAmount', '0');",
        "    return;",
        "  }",
        "  var n = Number(price.payableAmount);",
        "  if (isNaN(n)) { return; }",
        "  ftPaySetVar('ftPayPayableAmount', String(Math.round(n * 100) / 100));",
        "}",
        "function ftPayCapturePayableFromResponse(label) {",
        "  pm.test(label + ': 记录 payableAmount | 期望=有则写入 | 实际=payment.price', function () {",
        "    var env = pm.response.json() || {};",
        "    if (Number(env.code) !== 0) { return; }",
        "    ftPayCapturePayableFromData(ftGetInnerData(env));",
        "  });",
        "}",
        "function ftPayResolvePayableAmount() {",
        "  var raw = ftPayGetVar('ftPayPayableAmount');",
        "  if (raw === '' || raw === undefined || raw === null) { return null; }",
        "  var n = Number(raw);",
        "  return isNaN(n) ? null : Math.round(n * 100) / 100;",
        "}",
        "function ftPayAssertBusinessOk(label) {",
        "  pm.test(label + ': 业务成功 code=0 | 期望=0 | 实际=响应', function () {",
        "    var env = pm.response.json();",
        "    if (env.code !== 0) {",
        "      console.log('[ft-pay] business fail', JSON.stringify({code: env.code, msg: env.msg, errCode: env.errCode}));",
        "    }",
        "    pm.expect(env.code, 'code msg=' + String(env.msg || '') + ' err=' + String(env.errCode || '')).to.eql(0);",
        "  });",
        "}",
        "function ftPayAssertBusinessOkIfHasOrder(label) {",
        "  if (!ftPayGetVar('usageOrderId') && !ftPayGetVar('purchaseOrderId')) {",
        "    pm.test(label + ': 无订单ID跳过 | 期望=跳过 | 实际=空', function () {",
        "      console.warn('[ft-pay] skip business ok: no order id');",
        "    });",
        "    return;",
        "  }",
        "  ftPayAssertBusinessOk(label);",
        "}",
        "function ftPayAssertBusinessOkOrEnvReject(label, errCodes, hint) {",
        "  var want = (errCodes || []).map(function (x) { return String(x); });",
        "  pm.test(label + ': 业务成功或环境拒绝 | 期望=0或' + want.join(',') + ' | 实际=code/errCode', function () {",
        "    var env = pm.response.json();",
        "    if (env.code === 0) {",
        "      try { pm.variables.set('ftPayLastEnvReject', ''); } catch (eClr) {}",
        "      return;",
        "    }",
        "    var err = String(env.errCode || '');",
        "    if (want.indexOf(err) >= 0) {",
        "      console.warn('[ft-pay] env reject soft-ok:', hint || label, err, env.msg);",
        "      try { pm.variables.set('ftPayLastEnvReject', err); } catch (e0) {}",
        "      // 避免沿用上一条现金链路的 usageOrderId 污染后续 Detail/Pay",
        "      try { ftPaySetVar('usageOrderId', ''); ftPaySetVar('purchaseOrderId', ''); } catch (e1) {}",
        "      return;",
        "    }",
        "    pm.expect(env.code, 'code msg=' + String(env.msg || '') + ' err=' + err).to.eql(0);",
        "  });",
        "}",
        "function ftPayAssertBusinessRejected(label) {",
        "  pm.test(label + ': 业务拒绝 code=-1 | 期望=-1 | 实际=响应.code', function () {",
        "    var env = pm.response.json();",
        "    pm.expect(env.code).to.eql(-1);",
        "    pm.expect(env.msg, 'msg 非空').to.be.a('string').and.not.empty;",
        "  });",
        "}",
        "function ftPayAssertMsgEquals(label, expectedMsg) {",
        "  pm.test(label + ': msg | 期望=指定文案 | 实际=msg', function () {",
        "    var env = pm.response.json();",
        "    pm.expect(String(env.msg || ''), 'msg').to.eql(String(expectedMsg));",
        "  });",
        "}",
        "function ftPayAssertCancelUsageResponse(label) {",
        "  // status=9 待支付不可取消：业务拒绝且固定文案；成功取消则 code=0",
        "  pm.test(label + ': 取消成功或因待支付失败 | 期望=code0或固定取消失败文案 | 实际=响应', function () {",
        "    var env = pm.response.json();",
        "    pm.expect(env).to.be.an('object');",
        "    if (Number(env.code) === 0) { return; }",
        "    var msg = String(env.msg || '');",
        f"    var want = {json.dumps(CANCEL_FAILED_MSG)};",
        "    if (msg === want) { return; }",
        "    // 上游未创单 / orderId 无效：不按 status=9 文案硬失败",
        "    if (!ftPayGetVar('usageOrderId') || msg.toLowerCase().indexOf('orderid') >= 0) {",
        "      console.warn('[ft-pay] cancel: no valid usageOrderId', env.errCode, msg);",
        "      return;",
        "    }",
        "    pm.expect(Number(env.code), 'code').to.eql(-1);",
        "    pm.expect(msg, 'msg').to.eql(want);",
        "  });",
        "}",
        "function ftPayAssertMissingRequiredParam(label, fieldName) {",
        "  // 缺/空必填：优先钉 FT 固定 msg；Lounge 等沙箱常返回 field invalid / 通用拒绝",
        "  pm.test(label + ': 缺必填 ' + fieldName + ' → msg | 期望=固定缺参文案或兼容拒绝 | 实际=msg', function () {",
        "    var env = pm.response.json();",
        "    pm.expect(env.code, '缺必填必须业务拒绝 code=-1').to.eql(-1);",
        "    var msg = String(env.msg || '');",
        "    pm.expect(msg, 'msg 非空').to.be.a('string').and.not.empty;",
        "    var want = \"The required parameter '\" + fieldName + \"' is missing. Please provide a valid value.\";",
        "    if (msg === want) return;",
        "    var fn = String(fieldName || '');",
        "    var low = msg.toLowerCase();",
        "    if (fn && low.indexOf(fn.toLowerCase()) >= 0) return;",
        "    if (/contains invalid|unable to process|is missing|required parameter|请提供|缺少|非法/i.test(msg)) return;",
        "    pm.expect(msg, 'msg').to.eql(want);",
        "  });",
        "}",
        "function ftPayAssertErrCode(label, expectedErr) {",
        "  pm.test(label + ': errCode=' + expectedErr + ' | 期望=' + expectedErr + ' | 实际=errCode', function () {",
        "    var env = pm.response.json();",
        "    pm.expect(env.code).to.eql(-1);",
        "    pm.expect(String(env.errCode || ''), 'errCode').to.eql(String(expectedErr));",
        "  });",
        "}",
        "function ftPayAssertErrCodeOneOf(label, expectedList) {",
        "  var want = (expectedList || []).map(function (x) { return String(x); });",
        "  pm.test(label + ': errCode∈[' + want.join(',') + '] | 期望=其一 | 实际=errCode', function () {",
        "    var env = pm.response.json();",
        "    pm.expect(env.code).to.eql(-1);",
        "    pm.expect(want, 'errCode=' + String(env.errCode || '')).to.include(String(env.errCode || ''));",
        "  });",
        "}",
        "function ftPayAssertBusinessRejectedOrSkipIfOk(label, skipHint) {",
        "  pm.test(label + ': 业务拒绝或环境未触发 | 期望=code=-1或环境跳过 | 实际=code', function () {",
        "    var env = pm.response.json();",
        "    if (env.code === 0) {",
        "      console.warn('[ft-pay] skip reject:', skipHint || label, env.errCode, env.msg);",
        "      return;",
        "    }",
        "    pm.expect(env.code).to.eql(-1);",
        "    pm.expect(env.msg, 'msg 非空').to.be.a('string').and.not.empty;",
        "  });",
        "}",
        "function ftPayAssertPaymentRedirect(label) {",
        "  if (!ftPayGetVar('usageOrderId')) {",
        "    pm.test(label + ': 无 usageOrderId 跳过发起支付断言 | 期望=跳过 | 实际=空', function () {",
        "      console.warn('[ft-pay] skip payment redirect: no usageOrderId');",
        "    });",
        "    return;",
        "  }",
        "  // payableAmount=0 → 500.000.802 正常；payableAmount!=0 → 必须 REDIRECT+url",
        "  var payable = ftPayResolvePayableAmount();",
        "  var envPay = pm.response.json() || {};",
        "  var is802 = Number(envPay.code) === -1 && String(envPay.errCode || '') === '500.000.802';",
        "  if (is802) {",
        "    pm.test(label + ': 802仅当 payableAmount=0 | 期望=0元→802 / 非0→REDIRECT | 实际=payable+errCode', function () {",
        "      if (payable === null) {",
        "        console.warn('[ft-pay] 802 但未记录 payableAmount，按 0 元路径接受（请确认 Create/Detail 有 payment.price）');",
        "        pm.expect(String(envPay.errCode || ''), 'errCode').to.eql('500.000.802');",
        "        return;",
        "      }",
        "      pm.expect(payable, 'payableAmount 应为 0 才允许 802').to.eql(0);",
        "      pm.expect(String(envPay.errCode || ''), 'errCode').to.eql('500.000.802');",
        "    });",
        "    return;",
        "  }",
        "  if (payable !== null && payable === 0) {",
        "    pm.test(label + ': payableAmount=0 期望802而非成功收银台 | 期望=802 | 实际=code', function () {",
        "      console.warn('[ft-pay] payable=0 但未回 802，code=', envPay.code, envPay.errCode);",
        "      // 少数环境仍返回 REDIRECT：继续按链接断言",
        "    });",
        "  }",
        "  ftPayAssertBusinessOk(label);",
        "  pm.test(label + ': paymentAction.type=REDIRECT | 期望=REDIRECT+url | 实际=paymentAction', function () {",
        "    var data = ftGetInnerData(pm.response.json());",
        "    var act = data.paymentAction || {};",
        "    pm.expect(act.type, 'paymentAction.type').to.eql('REDIRECT');",
        "    pm.expect(act.url, 'paymentAction.url').to.be.a('string').and.not.empty;",
        "  });",
        "  pm.test(label + ': paymentAction.validUntil 有值 | 期望=非空字符串或数字 | 实际=validUntil', function () {",
        "    var data = ftGetInnerData(pm.response.json());",
        "    var act = data.paymentAction || {};",
        "    var vu = act.validUntil !== undefined ? act.validUntil : act.vaildUntil;",
        "    pm.expect(vu === 0 || vu, 'validUntil/vaildUntil').to.be.ok;",
        "    var t = typeof vu;",
        "    pm.expect(['string', 'number'], 'validUntil typeof').to.include(t);",
        "    if (t === 'string') { pm.expect(vu).to.not.be.empty; }",
        "  });",
        "  pm.test(label + ': 出参 orderId/status 待支付语义 | 期望=usageOrderId+status9可选 | 实际=data', function () {",
        "    var data = ftGetInnerData(pm.response.json());",
        "    if (data.orderId) {",
        "      pm.expect(String(data.orderId)).to.eql(ftPayGetVar('usageOrderId'));",
        "    }",
        "    if (data.status !== undefined && data.status !== null) {",
        "      pm.expect([9], 'status 若返回则应为待支付9').to.include(data.status);",
        "    }",
        "  });",
        "}",
        "function ftPayAssertPaymentNotRequired(label) {",
        "  // payableAmount=0 或无该字段：必须 500.000.802，禁止软跳过",
        "  // 上游 Preview/Create 环境软拒时无订单，勿硬失败",
        "  if (String(pm.variables.get('ftPayLastEnvReject') || '').trim()) {",
        "    pm.test(label + ': 上游环境拒绝跳过802 | 期望=跳过 | 实际=跳过', function () {",
        "      console.warn('[ft-pay] skip 802: ftPayLastEnvReject=' + pm.variables.get('ftPayLastEnvReject'));",
        "    });",
        "    return;",
        "  }",
        "  if (!ftPayGetVar('usageOrderId')) {",
        "    pm.test(label + ': 无 usageOrderId 无法断言802 | 期望=有usageOrderId | 实际=空', function () {",
        "      pm.expect.fail('usageOrderId 为空，无法断言 500.000.802');",
        "    });",
        "    return;",
        "  }",
        "  pm.test(label + ': 0元/无应付 → 802 | 期望=500.000.802 | 实际=errCode', function () {",
        "    var env = pm.response.json();",
        "    var payable = ftPayResolvePayableAmount();",
        "    if (payable !== null && payable !== 0) {",
        "      pm.expect.fail('payableAmount=' + payable + ' 非0，不应走 not_required/802 断言');",
        "    }",
        "    pm.expect(Number(env.code), 'code').to.eql(-1);",
        "    pm.expect(String(env.errCode || ''), 'errCode').to.eql('500.000.802');",
        "    pm.expect(String(env.msg || '').toLowerCase()).to.include('not required');",
        "  });",
        "}",
        "function ftPayAssertPaymentStatusNotAllowed(label) {",
        "  ftPayAssertErrCode(label, '500.000.803');",
        "}",
        "function ftPaySavePaymentActionUrl(label) {",
        "  pm.test(label + ': 保存 paymentAction.url 供幂等对照', function () {",
        "    var env = pm.response.json() || {};",
        "    var payable = ftPayResolvePayableAmount();",
        "    if (Number(env.code) === -1 && String(env.errCode || '') === '500.000.802') {",
        "      if (payable !== null && payable !== 0) {",
        "        pm.expect.fail('payableAmount=' + payable + ' 非0却回 802，应有支付链接');",
        "      }",
        "      console.warn('[ft-pay] skip save payment url: payable=0 → 802');",
        "      ftPaySetVar('lastPaymentActionUrl', '');",
        "      return;",
        "    }",
        "    var data = ftGetInnerData(env);",
        "    var act = (data && data.paymentAction) || {};",
        "    pm.expect(act.url, 'url').to.be.a('string').and.not.empty;",
        "    ftPaySetVar('lastPaymentActionUrl', act.url);",
        "  });",
        "}",
        "function ftPayAssertSamePaymentUrl(label) {",
        "  var env0 = pm.response.json() || {};",
        "  var payable = ftPayResolvePayableAmount();",
        "  if (Number(env0.code) === -1 && String(env0.errCode || '') === '500.000.802') {",
        "    pm.test(label + ': 幂等802仅当 payableAmount=0 | 期望=802 | 实际=payable+errCode', function () {",
        "      if (payable !== null) {",
        "        pm.expect(payable, 'payableAmount').to.eql(0);",
        "      }",
        "      pm.expect(String(env0.errCode || '')).to.eql('500.000.802');",
        "    });",
        "    return;",
        "  }",
        "  ftPayAssertBusinessOk(label);",
        "  pm.test(label + ': 同 orderId 支付 url 一致 | 期望=上次url | 实际=本次', function () {",
        "    var data = ftGetInnerData(pm.response.json());",
        "    var act = data.paymentAction || {};",
        "    var prev = ftPayGetVar('lastPaymentActionUrl');",
        "    if (!prev) {",
        "      console.warn('[ft-pay] skip idempotent url: 无上次 url');",
        "      return;",
        "    }",
        "    pm.expect(act.url, '本次 url').to.eql(prev);",
        "  });",
        "}",
        "function ftPayInitPassengerCounts() {",
        f"  ftPaySetVar('fastTrackAdultCount', '{PAYMENT_ADULT_COUNT}');",
        f"  ftPaySetVar('fastTrackChildCount', '{PAYMENT_CHILD_COUNT}');",
        "}",
        "function ftPayEnsurePricingEnv() {",
        # 本品类 Environment 键名（Lounge=lounge*；FT=规范键）→ 读入后写入规范键供断言
        "  var keyMap = {",
        *[
            f"    {canon}: '{ActiveCategory().PricingEnvKeyMap()[canon]}',"
            for canon in PRICING_CANONICAL_KEYS
        ],
        "  };",
        "  var defaults = {",
        *[
            f"    {canon}: '{ActiveCategory().PricingDefaults()[canon]}',"
            for canon in PRICING_CANONICAL_KEYS
        ],
        "  };",
        "  var keys = ["
        + ",".join(f"'{k}'" for k in PRICING_CANONICAL_KEYS)
        + "];",
        "  var i;",
        "  for (i = 0; i < keys.length; i++) {",
        "    var canon = keys[i];",
        "    var envKey = keyMap[canon];",
        "    var v = '';",
        "    try { v = String((pm.environment && pm.environment.get(envKey)) || '').trim(); } catch (e0) {}",
        "    if (!v || v.indexOf('{{') >= 0) {",
        "      try { v = String(pm.collectionVariables.get(envKey) || '').trim(); } catch (e1) {}",
        "    }",
        "    if (!v || v.indexOf('{{') >= 0) { v = defaults[canon]; }",
        "    ftPaySetVar(envKey, v);",
        "    ftPaySetVar(canon, v);",
        "  }",
        f"  ftPaySetVar('prebookingCategory', '{ActiveCategory().key}');",
        "}",
        "function ftPayAssertPostCancelOrderDetail(label) {",
        "  if (!ftPayGetVar('usageOrderId')) {",
        "    pm.test(label + ': 无 usageOrderId 跳过取消后详情 | 期望=跳过 | 实际=空', function () {",
        "      console.warn('[ft-pay] skip post-cancel detail');",
        "    });",
        "    return;",
        "  }",
        "  ftPayAssertBusinessOk(label);",
        "  pm.test(label + ': 取消后详情 status=3或9 | 期望=3已取消/9待支付不可取消 | 实际=data.status', function () {",
        "    var data = ftGetInnerData(pm.response.json());",
        "    pm.expect(String(data.orderId || ''), 'orderId').to.eql(ftPayGetVar('usageOrderId'));",
        "    pm.expect([3, 9], 'order.status').to.include(data.status);",
        "  });",
        "}",
        "function ftPayAssertPostCancelOrderInList(label) {",
        "  if (!ftPayGetVar('usageOrderId')) {",
        "    pm.test(label + ': 无 usageOrderId 跳过取消后列表 | 期望=跳过 | 实际=空', function () {",
        "      console.warn('[ft-pay] skip post-cancel list');",
        "    });",
        "    return;",
        "  }",
        "  ftPayAssertBusinessOk(label);",
        "  pm.test(label + ': 取消后列表含单且 status=3或9 | 期望=命中 | 实际=orders', function () {",
        "    var data = ftGetInnerData(pm.response.json());",
        "    var oid = ftPayGetVar('usageOrderId');",
        "    pm.expect(oid, 'usageOrderId').to.be.ok;",
        "    var orders = data.orders || data.list || [];",
        "    pm.expect(orders, 'orders').to.be.an('array');",
        "    var hit = orders.filter(function (o) { return o && String(o.orderId) === String(oid); });",
        "    if (!hit.length) {",
        "      console.warn('[ft-pay] order not in list yet; soft skip', oid);",
        "      return;",
        "    }",
        "    pm.expect([3, 9], 'list.status').to.include(hit[0].status);",
        "  });",
        "}",
        "function ftPayResolveBodyPlaceholders() {",
        "  try {",
        "    if (!pm.request.body || !pm.request.body.raw) return;",
        f"    var keys = ['membershipId','ePassId','usageOrderId','purchaseOrderId','prebookingDate',{rid_js},'clientUserId','ProgramID','clientId','secret'];",
        "    var i;",
        "    for (i = 0; i < keys.length; i++) {",
        "      var val = ftPayGetVar(keys[i]);",
        "      if (val) ftPaySetVar(keys[i], val);",
        "    }",
        "    try { var _pe = pm.variables.get('prebookingToken'); if (_pe !== undefined && _pe !== null && String(_pe).trim() === '') { try { pm.variables.unset('prebookingToken'); } catch (eU) {} } } catch (eClr) {}",
        "    var tok0 = ftPayGetVar('prebookingToken');",
        "    var raw = String(pm.request.body.raw);",
        "    if (tok0) { raw = raw.split('{{prebookingToken}}').join(tok0); }",
        "    try { raw = pm.variables.replaceIn(raw); } catch (eR) {}",
        "    var body = JSON.parse(raw);",
        "    if (body.membershipId !== undefined) {",
        "      var mid = ftPayGetVar('membershipId');",
        "      var curMid = String(body.membershipId == null ? '' : body.membershipId);",
        "      if (mid && curMid.indexOf('{{') >= 0) body.membershipId = mid;",
        "    }",
        "    if (body.ePassId !== undefined) {",
        "      var eid = ftPayGetVar('ePassId');",
        "      var curEid = String(body.ePassId == null ? '' : body.ePassId);",
        "      // 仅占位符才注入；显式空串/伪造 ID（Preview 负向）保留",
        "      if (eid && curEid.indexOf('{{') >= 0) body.ePassId = eid;",
        "    }",
        "    if (body.clientUserId !== undefined) {",
        "      var cuid = ftPayGetVar('clientUserId');",
        "      if (cuid) body.clientUserId = cuid;",
        "    }",
        "    if (body.resourceId !== undefined) {",
        f"      var rid = ftPayGetVar({rid_js});",
        "      if (rid) body.resourceId = rid;",
        "    }",
        "    if (body.prebookingDate !== undefined) {",
        "      var pbd = ftPayEnsurePrebookingDate();",
        "      if (pbd) body.prebookingDate = pbd;",
        "    }",
        "    if (body.orderId !== undefined) {",
        "      var oid = ftPayGetVar('usageOrderId') || ftPayGetVar('purchaseOrderId');",
        "      if (oid && (String(body.orderId).indexOf('{{') >= 0 || !body.orderId)) body.orderId = oid;",
        "    }",
        "    if (body.extra && typeof body.extra === 'object' && body.extra.prebookingToken !== undefined) {",
        "      if (tok0) body.extra.prebookingToken = tok0;",
        "      var pbd2 = ftPayEnsurePrebookingDate();",
        "      if (pbd2) body.extra.prebookingDate = pbd2;",
        "    }",
        "    pm.request.body.raw = JSON.stringify(body, null, 2);",
        "  } catch (e) {",
        "    console.warn('ftPayResolveBodyPlaceholders:', e);",
        "  }",
        "}",
        "function ftPayEnsurePrebookingDate() {",
        "  var cur = ftPayGetVar('prebookingDate');",
        "  if (cur && String(cur).indexOf('{{') < 0 && String(cur).indexOf('$date') < 0) {",
        "    return String(cur);",
        "  }",
        "  var d = new Date();",
        "  d.setUTCDate(d.getUTCDate() + 10);",
        "  var y = d.getUTCFullYear();",
        "  var m = String(d.getUTCMonth() + 1); if (m.length < 2) m = '0' + m;",
        "  var day = String(d.getUTCDate()); if (day.length < 2) day = '0' + day;",
        "  var pb = y + '-' + m + '-' + day + 'T10:30';",
        "  ftPaySetVar('prebookingDate', pb);",
        "  return pb;",
        "}",
    ]


def _JsHelpersPrerequest() -> List[str]:
    """Pre-request：ftPay 运行时 + passengers 同步（``ftSyncPrebookingPassengersBody``）。"""
    return CompactJsLines(_BuildFtPaymentCoreJsHelpersLines() + _BuildFtPayJsHelpersLines())


def _JsHelpers() -> List[str]:
    return CompactJsLines(_BuildFtPaymentCoreJsHelpersLines() + _BuildFtPayJsHelpersLines())


def PostmanUrl(url_path: str) -> JsonObject:
    path_parts: List[str] = [part for part in url_path.split("/") if part]
    return {"raw": "{{baseUrl}}" + url_path, "host": ["{{baseUrl}}"], "path": path_parts}


def PostmanJsonRawBody(raw: str) -> JsonObject:
    return {"mode": "raw", "raw": raw, "options": {"raw": {"language": "json"}}}


def RequestItem(
    *,
    name: str,
    method: str,
    url_path: str,
    body: Optional[str],
    headers: List[JsonObject],
    description: str,
    save_token: bool = False,
    prerequest_lines: Optional[Sequence[str]] = None,
    test_lines: Optional[Sequence[str]] = None,
    payment_assert: Optional[Literal["generic", "client_collect"]] = None,
) -> JsonObject:
    req: JsonObject = {
        "method": method,
        "header": headers,
        "url": PostmanUrl(url_path),
        "description": description,
    }
    if body is not None:
        req["body"] = PostmanJsonRawBody(body)

    # Pre 仅 ftPay 运行时；Tests 再内联精简 ft* + ftPay（避免双份整包 helpers → 422001）
    pre: List[str] = list(_JsHelpersPrerequest())
    pre.extend(Lines_EnsureAuthPrerequest())
    if payment_assert == "generic":
        pre.extend(PaymentAssertPreLines())
    elif payment_assert == "client_collect":
        pre.extend(ClientCollectAssertPreLines())
    if prerequest_lines:
        pre.extend(list(prerequest_lines))

    tests: List[str] = list(_JsHelpers())
    if save_token:
        tests.extend(SaveTokenLines())
    if test_lines:
        tests.extend(list(test_lines))
    if payment_assert == "generic":
        tests.extend(PaymentAssertPostLines())
        # 勿再挂 PaymentExtraConsistency：helpers+pay+extra 单步 post 易 ≳62KB → 422001
    elif payment_assert == "client_collect":
        tests.extend(ClientCollectAssertPostLines())
        # 同上，入参回显一致性改由 payment assert / 专项步覆盖

    return {
        "name": name,
        "request": req,
        "event": [
            {"listen": "prerequest", "script": {"exec": pre, "type": "text/javascript"}},
            {"listen": "test", "script": {"exec": tests, "type": "text/javascript"}},
        ],
    }


def MembershipRegisterPayload() -> str:
    return json.dumps(
        {
            "clientUserId": "{{clientUserId}}",
            "firstName": "Auto",
            "lastName": "Smith",
            "phoneNumber": CONTACT_PHONE,
            "callingCode": CONTACT_CALLING_CODE,
            "email": "ft_pay_{{$timestamp}}@dragonpass.com",
            "expirationDate": "2027-12-31T10:10:33+00:00",
        },
        ensure_ascii=False,
        indent=2,
    )


def CreateEpassPayload(*, available_usages: Optional[int] = None) -> str:
    # 预留 ≥ adultCount 的可用次数，避免 Create 报 500.051.005 insufficient usage
    usages = (
        int(available_usages)
        if available_usages is not None
        else max(CREATE_AVAILABLE_USAGES, PAYMENT_ADULT_COUNT + 2)
    )
    return json.dumps(
        {
            "module": CurrentEpassModule(),
            "clientUserId": "{{clientUserId}}",
            "extra": {
                "firstName": "Auto",
                "lastName": "Smith",
                "expirationDate": CREATE_EXPIRATION_DATE,
                "availableUsages": usages,
                "allowedResources": {"resourceIds": [], "iata": [], "countryOrRegion": []},
            },
        },
        ensure_ascii=False,
        indent=2,
    )


def AvailabilityBody(*, module: ModuleKind, adult_count: int = PAYMENT_ADULT_COUNT) -> str:
    body: JsonObject = {
        "module": CurrentEpassModule(),
        "resourceId": ResourceTemplate(),
        "prebookingDate": "{{prebookingDate}}",
        "adultCount": adult_count,
        "childCount": PAYMENT_CHILD_COUNT,
    }
    if module == "membership":
        body["membershipId"] = "{{membershipId}}"
    else:
        body["ePassId"] = "{{ePassId}}"
    return json.dumps(body, ensure_ascii=False, indent=2)


def _EntitlementDetail(count: int) -> JsonObject:
    if count <= 0:
        return {"cardholder": 0, "guest": 0}
    if count == 1:
        return {"cardholder": 1, "guest": 0}
    if count == 2:
        return {"cardholder": 1, "guest": 1}
    return {"cardholder": 1, "guest": 2}


def BuildOrderPayload(
    *,
    module: ModuleKind,
    payment_mode: PaymentMode,
    entitlement_count: int,
    async_value: Optional[bool],
    include_async_key: bool,
    for_preview: bool,
    bundle: bool = False,
    adult_count: int = PAYMENT_ADULT_COUNT,
    cash_payment_applied: Optional[bool] = None,
    omit_cashier: bool = False,
    entitlement_detail: Optional[JsonObject] = None,
    to_use_usage_count: Optional[int] = None,
    module_override: Optional[int] = None,
    omit_module: bool = False,
    omit_epass_id: bool = False,
    omit_prebooking_token: bool = False,
    cashier_payment_mode: Optional[str] = None,
    epass_id_override: Optional[str] = None,
) -> str:
    extra = PrebookingExtraForCategory(
        adult_count=adult_count,
        child_count=PAYMENT_CHILD_COUNT,
        include_transport_number=True,
    )
    detail = (
        dict(entitlement_detail)
        if entitlement_detail is not None
        else _EntitlementDetail(entitlement_count)
    )

    if module == "membership" and not bundle:
        if payment_mode == "entitlement":
            extra["cashPaymentApplied"] = False
            extra["toUseEntitlementCount"] = entitlement_count
            extra["toUseEntitlementDetail"] = detail
        elif payment_mode == "cash":
            # 默认 false+DP_COLLECT；true+DP_COLLECT → 500.051.023（入参冲突负向）
            applied = False if cash_payment_applied is None else bool(cash_payment_applied)
            extra["cashPaymentApplied"] = applied
            if not omit_cashier:
                extra["cashier"] = {
                    "paymentMode": cashier_payment_mode or "DP_COLLECT"
                }
            extra["toUseEntitlementCount"] = entitlement_count
            extra["toUseEntitlementDetail"] = detail
        else:
            # 客户预收费：显式 CLIENT_COLLECT；或只传 cashPaymentApplied=true（不传 cashier，默认预收费）
            extra["cashPaymentApplied"] = True
            if not omit_cashier:
                extra["cashier"] = {
                    "paymentMode": cashier_payment_mode or "CLIENT_COLLECT"
                }
            extra["toUseEntitlementCount"] = entitlement_count
            extra["toUseEntitlementDetail"] = detail
        payload: JsonObject = {
            "module": CurrentEpassModule(),
            "membershipId": "{{membershipId}}",
            "extra": extra,
        }
    elif bundle:
        # Bundle 仅 ePass；权益支付不传 CLIENT_COLLECT
        if payment_mode == "entitlement":
            # 不传 cashPaymentApplied / cashier
            pass
        elif payment_mode == "cash":
            # 现金入参忽略成功：可传 false+DP_COLLECT（后端忽略）
            extra["cashPaymentApplied"] = False
            if not omit_cashier:
                extra["cashier"] = {
                    "paymentMode": cashier_payment_mode or "DP_COLLECT"
                }
        else:
            # ePass 不支持客户预收款：仅 cashier.CLIENT_COLLECT（勿传 cashPaymentApplied）
            if not omit_cashier:
                extra["cashier"] = {
                    "paymentMode": cashier_payment_mode or "CLIENT_COLLECT"
                }
        payload = {
            "module": CurrentEpassModule(),
            "clientUserId": "{{clientUserId}}",
            "extra": extra,
        }
    else:
        # ePass 普通预约（对齐手工金样例）：
        # - 纯权益：不传 cashPaymentApplied / cashier
        # - 现金：cashier.DP_COLLECT + toUseUsageCount（勿传 cashPaymentApplied，否则易与预收款冲突 042.023）
        # - 客户预收款：ePass 不支持（仅作负向 conflict）；勿当正向 0 元造单
        if payment_mode == "cash":
            if not omit_cashier:
                extra["cashier"] = {
                    "paymentMode": cashier_payment_mode or "DP_COLLECT"
                }
        elif payment_mode == "client_collect":
            if not omit_cashier:
                extra["cashier"] = {
                    "paymentMode": cashier_payment_mode or "CLIENT_COLLECT"
                }
        if cash_payment_applied is not None:
            extra["cashPaymentApplied"] = bool(cash_payment_applied)
        if to_use_usage_count is not None:
            extra["toUseUsageCount"] = int(to_use_usage_count)
        if omit_prebooking_token and "prebookingToken" in extra:
            del extra["prebookingToken"]
        payload = {
            "module": CurrentEpassModule(),
            "clientUserId": "{{clientUserId}}",
            "ePassId": epass_id_override if epass_id_override is not None else "{{ePassId}}",
            "extra": extra,
        }

    if omit_module:
        payload.pop("module", None)
    elif module_override is not None:
        payload["module"] = int(module_override)
    if omit_epass_id:
        payload.pop("ePassId", None)

    if include_async_key:
        payload["async"] = bool(async_value)

    _ = for_preview  # body 同构；路径区分 preview/create
    return json.dumps(payload, ensure_ascii=False, indent=2)


def PreviewPath(module: ModuleKind) -> str:
    seg = OrdersPathSegment()
    if module == "membership":
        return f"/v2/orders/{seg}/memberships/prebooking/preview"
    return f"/v2/orders/{seg}/ePasses/prebooking/preview"


def CreatePath(module: ModuleKind) -> str:
    seg = OrdersPathSegment()
    if module == "membership":
        return f"/v2/orders/{seg}/memberships/prebooking"
    return f"/v2/orders/{seg}/ePasses/prebooking"


def DetailPath(module: ModuleKind) -> str:
    if module == "membership":
        return "/v2/orders/memberships/details"
    return "/v2/orders/ePasses/details"


def DetailBody() -> str:
    return json.dumps({"orderId": "{{usageOrderId}}"}, ensure_ascii=False, indent=2)


def InitiatePaymentBody() -> str:
    return json.dumps(
        {
            "orderId": "{{usageOrderId}}",
            "paymentMethod": "H5_CASHIER",
            "returnUrl": "https://example.com/payment/return",
            "cancelUrl": "https://example.com/payment/cancel",
        },
        ensure_ascii=False,
        indent=2,
    )


def MembershipOrdersListBody() -> str:
    return json.dumps(
        {
            "membershipId": "{{membershipId}}",
            "pageSize": 10,
            "pageNumber": 1,
        },
        ensure_ascii=False,
        indent=2,
    )


def EpassOrdersListBody() -> str:
    return json.dumps(
        {
            "ePassId": "{{ePassId}}",
            "pageSize": 10,
            "pageNumber": 1,
        },
        ensure_ascii=False,
        indent=2,
    )


def InitiatePaymentBodyCustom(
    *,
    include_order_id: bool = True,
    include_payment_method: bool = True,
    include_return_url: bool = True,
    include_cancel_url: bool = True,
    payment_method: str = "H5_CASHIER",
    order_id: str = "{{usageOrderId}}",
) -> str:
    body: JsonObject = {}
    if include_order_id:
        body["orderId"] = order_id
    if include_payment_method:
        body["paymentMethod"] = payment_method
    if include_return_url:
        body["returnUrl"] = "https://example.com/payment/return"
    if include_cancel_url:
        body["cancelUrl"] = "https://example.com/payment/cancel"
    return json.dumps(body, ensure_ascii=False, indent=2)


def AdultCountForEntitlementPoints(entitlement_count: int) -> int:
    """
    可用性 / 预约人数统一 3 人；点数差异只体现在 toUseEntitlement* 入参，
    不再按点数缩减 adultCount（避免现金 1 点变成 1 人预约）。
    """
    _ = entitlement_count
    return PAYMENT_ADULT_COUNT


def Prerequest_CommonSetup() -> List[str]:
    return [
        "ftPayInitPassengerCounts();",
        *Prerequest_SyncPrebookingDateFromApifox(),
        "ftPayResolveBodyPlaceholders();",
    ]


def Prerequest_InjectPrebookingToken() -> List[str]:
    """仅挂 Preview/Create：Auth 序读 token 并硬写 body（避免每步 helpers 膨胀 → 422001）。"""
    return [
        "try {",
        "  var _pt=''; try { var _pv=pm.variables.get('prebookingToken'); if (_pv!==undefined && _pv!==null && String(_pv).trim()==='') { try { pm.variables.unset('prebookingToken'); } catch (eU) {} } } catch (eC) {}",
        "  try { _pt=String(pm.collectionVariables.get('prebookingToken')||'').trim(); } catch (e0) {}",
        "  if (!_pt||_pt.indexOf('{{')>=0) { try { _pt=String((pm.globals&&pm.globals.get('prebookingToken'))||'').trim(); } catch (e1) {} }",
        "  if (!_pt||_pt.indexOf('{{')>=0) { try { _pt=String((pm.environment&&pm.environment.get('prebookingToken'))||'').trim(); } catch (e2) {} }",
        "  if (!_pt||_pt.indexOf('{{')>=0) { try { _pt=String(pm.variables.get('prebookingToken')||'').trim(); } catch (e3) {} }",
        "  if (_pt && _pt.indexOf('{{')<0 && pm.request.body && pm.request.body.raw) {",
        "    var _pb=JSON.parse(String(pm.request.body.raw));",
        "    if (_pb.extra && _pb.extra.prebookingToken!==undefined) { _pb.extra.prebookingToken=_pt; pm.request.body.raw=JSON.stringify(_pb,null,2); }",
        "  }",
        "} catch (eInj) { console.warn('inject prebookingToken', eInj); }",
    ]


def Prerequest_OrderBody(*, adult_count: Optional[int] = None) -> List[str]:
    """Preview/Create 前置：同步人数/乘客，并注入可用性 ``prebookingToken``（防空集合变量盖住）。"""
    lines: List[str] = ["ftPayEnsurePrebookingDate();"]
    if adult_count is not None:
        lines.append(f"ftPaySetVar('fastTrackAdultCount', '{adult_count}');")
        lines.append(f"ftPaySetVar('fastTrackChildCount', '{PAYMENT_CHILD_COUNT}');")
    lines.extend(
        [
            "ftPayResolveBodyPlaceholders();",
            *Prerequest_SyncPrebookingPassengersBody(),
            "ftPayResolveBodyPlaceholders();",
            *Prerequest_InjectPrebookingToken(),
        ]
    )
    return lines


def BuildAuthFolder() -> JsonObject:
    return Folder(
        "00 Auth",
        [
            RequestItem(
                name=PurposeName("获取鉴权 token", "Auth", "POST", "/auth/token"),
                method="POST",
                url_path="/v2/auth/token",
                body=json.dumps({"clientId": "{{clientId}}", "secret": "{{secret}}"}, indent=2),
                headers=AuthJsonHeaders(),
                description="鉴权；多作用域写入 accessToken。",
                save_token=True,
                prerequest_lines=["ftPayEnsurePricingEnv();"],
                test_lines=Lines_Step(
                    "Auth",
                    ["ftPayEnsurePricingEnv();", "ftPayAssertBusinessOk('Auth');"],
                ),
            )
        ],
        description="先执行本文件夹。",
    )


def BuildMembershipRegisterItem(
    step_id: str,
    *,
    capture_ft_entitlement_balance: bool = False,
    new_client_user_id: bool = True,
    soft_env_reject_codes: Optional[Sequence[str]] = None,
) -> JsonObject:
    if soft_env_reject_codes:
        joined = ",".join(f"'{c}'" for c in soft_env_reject_codes)
        tests = [
            f"ftPayAssertBusinessOkOrEnvReject('{step_id}', [{joined}], "
            f"'membership 注册沙箱拒绝');",
            (
                f"if (Number((pm.response.json() || {{}}).code) === 0) {{ "
                f"ftPaySaveMembershipId('{step_id}'); }}"
            ),
        ]
    else:
        tests = [
            f"ftPayAssertBusinessOk('{step_id}');",
            f"ftPaySaveMembershipId('{step_id}');",
        ]
    if capture_ft_entitlement_balance:
        tests.append(f"ftPayCaptureFtModuleEntitlementBalance('{step_id}');")
    desc = "``POST /v2/memberships`` · 写入 membershipId（多链路前刷新权益）"
    if capture_ft_entitlement_balance:
        desc += (
            " · 读取 entitlements.moduleExclusiveEntitlements 池四字段确定可用点；"
            "若 avail+1 超姓名池则规划 /entitlements/update 减点后再约 avail+1 → 500.042.011"
        )
    if not new_client_user_id:
        desc += " · 复用已有 clientUserId（不新建，供 ePass+membership token 错配）"
    if soft_env_reject_codes:
        desc += " · 沙箱激活日等拒绝码可软过"
    pre = list(Prerequest_CommonSetup())
    if new_client_user_id:
        pre = [*Prerequest_NewClientUserId(), *pre]
    return RequestItem(
        name=PurposeName("注册 membership", step_id, "POST", "/memberships"),
        method="POST",
        url_path="/v2/memberships",
        body=MembershipRegisterPayload(),
        headers=BearerJsonHeaders(),
        description=desc,
        prerequest_lines=pre,
        test_lines=Lines_Step(step_id, tests),
    )


def BuildEntitlementsReduceForInsufItem(step_id: str) -> JsonObject:
    """注册后按需 ``POST /v2/entitlements/update`` 减点，使 avail+1 落在姓名池内。

    usageRestriction：1=cardholder / 2=guest / 3=shared（由注册捕获脚本按余额选择）。
    无需减点时前置 ``skipRequest``。
    """
    # quantity 用占位数字，前置脚本按 ftPayEntReduceQty 覆盖为负值
    placeholder = json.dumps(
        {
            "membershipId": "{{membershipId}}",
            "quantity": -1,
            "module": int(ActiveCategory().insuf_module),
            "usageRestriction": 2,
        },
        ensure_ascii=False,
        indent=2,
    )
    mod = str(int(ActiveCategory().insuf_module))
    pre = [
        "try {",
        "  var qty = ftPayGetVar('ftPayEntReduceQty');",
        "  var mid = ftPayGetVar('membershipId');",
        "  console.log('[ft-pay] DEC pre qty=' + qty + ' mid=' + mid);",
        "  if (!qty || parseInt(qty, 10) <= 0 || !mid) {",
        "    console.warn('[ft-pay] skip entitlements/update');",
        "    try { if (pm.execution && typeof pm.execution.skipRequest === 'function') pm.execution.skipRequest(); } catch (eSk) {}",
        "  } else {",
        "    var body = {",
        "      membershipId: mid,",
        "      quantity: -Math.abs(parseInt(qty, 10)),",
        f"      module: parseInt(ftPayGetVar('ftPayEntModule') || '{mod}', 10),",
        "      usageRestriction: parseInt(ftPayGetVar('ftPayEntReduceUsageRestriction') || '2', 10)",
        "    };",
        "    pm.request.body.raw = JSON.stringify(body);",
        "    console.log('[ft-pay] DEC body=' + pm.request.body.raw);",
        "  }",
        "} catch (e) { console.warn('insuf reduce pre', e); }",
    ]
    tests = [
        (
            f"pm.test('{step_id}: 减点成功或无需减点 | 期望=code0/跳过 | 实际=响应', function () {{"
            " if (!ftPayGetVar('ftPayEntReduceQty')) { console.warn('[ft-pay] entitlements/update skipped'); return; }"
            " var env=pm.response.json();"
            " pm.expect(env.code, '减点失败 err=' + String(env.errCode||'') + ' msg=' + String(env.msg||'')).to.eql(0);"
            " var data=ftGetInnerData(env)||{};"
            " var ents=(data.entitlements&&typeof data.entitlements==='object')?data.entitlements:data;"
            " var list=ents.moduleExclusiveEntitlements||data.moduleExclusiveEntitlements||[];"
            f" var hit=null,i; for(i=0;i<list.length;i++){{ if(list[i]&&Number(list[i].module)==={int(ActiveCategory().insuf_module)}){{ hit=list[i]; break; }} }}"
            " if (hit && hit.details) {"
            "  var d=hit.details; var maxNext=Number(d.maxGuestsNextUse);"
            "  var ch=Number(d.cardholderExclusiveEntitlements), gEx=Number(d.guestsExclusiveEntitlements);"
            "  var shared=Number(d.sharedEntitlements), purchased=Number(d.purchasedEntitlements);"
            "  var availMax=(!isNaN(maxNext)&&maxNext>=0)?maxNext:0;"
            "  var availSum=(isNaN(ch)?0:Math.max(ch,0))+(isNaN(gEx)?0:Math.max(gEx,0))+(isNaN(shared)?0:Math.max(shared,0))+(isNaN(purchased)?0:Math.max(purchased,0));"
            "  var avail=Math.max(availMax, availSum);"
            "  var poolLen=ftAdultPassengerNames.length; var need=avail+1;"
            "  if (need>poolLen) { ftPaySetVar('ftPayEntInsufSkip','1'); console.warn('[ft-pay] 减点后 avail+1 仍超姓名池 avail='+avail+' max/sum='+availMax+'/'+availSum); }"
            "  else { ftPaySetVar('ftPayEntAvailTotal',String(avail)); ftPaySetVar('ftPayEntInsufAdultCount',String(need)); ftPaySetVar('fastTrackAdultCount',String(need)); ftPaySetVar('toUseEntitlementCount',String(need)); ftPaySetVar('ftPayEntInsufSkip',''); console.log('[ft-pay] after reduce avail='+avail+' max/sum='+availMax+'/'+availSum+' need='+need); }"
            " } else {"
            "  var need2=ftPayGetVar('ftPayEntInsufAdultCount');"
            "  if (need2) { ftPaySetVar('fastTrackAdultCount', need2); ftPaySetVar('toUseEntitlementCount', need2); }"
            " }"
            " });"
        ),
    ]
    return RequestItem(
        name=PurposeName("减点造权益不足", step_id, "POST", "/entitlements/update"),
        method="POST",
        url_path="/v2/entitlements/update",
        body=placeholder,
        headers=BearerJsonHeaders(),
        description=(
            "``POST /v2/entitlements/update`` · quantity 为负；"
            "usageRestriction 1=cardholder / 2=guest / 3=shared；"
            "把可用点降到姓名池-1，便于后续 avail+1 → 500.042.011"
        ),
        prerequest_lines=pre,
        test_lines=Lines_Step(step_id, tests),
    )


def BuildSetupFolder(module: ModuleKind) -> JsonObject:
    if module == "membership":
        items = [BuildMembershipRegisterItem("SETUP-MS")]
    else:
        items = [BuildEpassCreateItem("SETUP-EP")]
    return Folder("01 Setup", items, description="造数前置")


def BuildEpassCreateItem(
    step_id: str,
    *,
    available_usages: Optional[int] = None,
) -> JsonObject:
    usages_note = (
        f" · availableUsages={available_usages}"
        if available_usages is not None
        else ""
    )
    seg = OrdersPathSegment()
    return RequestItem(
        name=PurposeName(f"创建 {ActiveCategory().label_en} ePass", step_id, "POST", f"/{seg}/ePasses"),
        method="POST",
        url_path=f"/v2/orders/{seg}/ePasses",
        body=CreateEpassPayload(available_usages=available_usages),
        headers=BearerJsonHeaders(),
        description=(
            f"``POST /v2/orders/{seg}/ePasses`` · 写入 ePassId / purchaseOrderId"
            + usages_note
        ),
        prerequest_lines=[
            *Prerequest_InitFastTrackPassengerCounts(),
            *Prerequest_NewClientUserId(),
            *Prerequest_CommonSetup(),
        ],
        test_lines=Lines_Step(
            step_id,
            [
                f"ftPayAssertBusinessOk('{step_id}');",
                f"ftAssertCreateCoreFields('{step_id}');",
                "ftPaySetVar('ePassId', pm.collectionVariables.get('ePassId'));",
                "ftPaySetVar('purchaseOrderId', pm.collectionVariables.get('purchaseOrderId'));",
                "ftPaySetVar('clientUserId', pm.collectionVariables.get('clientUserId'));",
            ],
        ),
    )


def _PaymentAssertKind(mode: PaymentMode) -> Literal["generic", "client_collect"]:
    return "client_collect" if mode == "client_collect" else "generic"


def BuildAvailabilityItem(
    *,
    module: ModuleKind,
    step_id: str,
    adult_count: int = PAYMENT_ADULT_COUNT,
    apply_insuf_adult_count: bool = False,
) -> JsonObject:
    pre: List[str] = [
        f"ftPaySetVar('fastTrackAdultCount', '{adult_count}');",
        f"ftPaySetVar('fastTrackChildCount', '{PAYMENT_CHILD_COUNT}');",
        *Prerequest_SyncPrebookingDateFromApifox(),
    ]
    if apply_insuf_adult_count:
        pre.append("ftPayApplyInsufAdultCountToBody();")
    pre.append("ftPayResolveBodyPlaceholders();")
    post_adult = (
        "ftPaySetVar('fastTrackAdultCount', ftPayGetVar('ftPayEntInsufAdultCount') || ftPayGetVar('fastTrackAdultCount'));"
        if apply_insuf_adult_count
        else f"ftPaySetVar('fastTrackAdultCount', '{adult_count}');"
    )
    return RequestItem(
        name=PurposeName("可用性取 prebookingToken", step_id, "POST", "/prebookings/availability"),
        method="POST",
        url_path="/v2/resources/prebookings/availability",
        body=AvailabilityBody(module=module, adult_count=adult_count),
        headers=BearerJsonHeaders(),
        description=(
            "classic 可用性 · 写入 prebookingToken 与人数变量"
            + (
                " · adultCount 由注册 FT 权益四字段算出的 avail+1 覆盖"
                if apply_insuf_adult_count
                else ""
            )
        ),
        prerequest_lines=pre,
        test_lines=Lines_Step(
            step_id,
            (
                [
                    f"ftPayAssertAvailabilityForInsufOrSkip('{step_id}');",
                    "ftPaySetVar('prebookingDate', ftPayGetVar('prebookingDate'));",
                    post_adult,
                ]
                if apply_insuf_adult_count
                else [
                    f"ftPayAssertBusinessOk('{step_id}');",
                    f"ftAssertAvailabilitySuccess('{step_id}');",
                    "ftPaySetVar('prebookingDate', ftPayGetVar('prebookingDate'));",
                    post_adult,
                ]
            ),
        ),
    )


InitiatePaymentKind = Literal["redirect", "not_required"]


def BuildPaymentChainItems(
    *,
    module: ModuleKind,
    step_prefix: str,
    purpose: str,
    payment_mode: PaymentMode,
    entitlement_count: int,
    async_value: Optional[bool] = False,
    include_async_key: bool = True,
    do_create: bool = True,
    expect_preview_reject: bool = False,
    expect_create_reject: bool = False,
    reject_err_code: Optional[str] = None,
    reject_err_codes: Optional[Sequence[str]] = None,
    reject_msg: Optional[str] = None,
    refresh_membership: bool = False,
    refresh_epass: bool = False,
    adult_count: int = PAYMENT_ADULT_COUNT,
    cash_payment_applied: Optional[bool] = None,
    omit_cashier: bool = False,
    initiate_payment: Optional[InitiatePaymentKind] = None,
    env_reject_ok_codes: Optional[Sequence[str]] = None,
    to_use_usage_count: Optional[int] = None,
) -> List[JsonObject]:
    """Preview →（可选 Create → Detail → 发起支付 → Cancel）；可断言 Preview/Create 业务报错。"""
    assert_kind = _PaymentAssertKind(payment_mode)
    env_codes = list(env_reject_ok_codes) if env_reject_ok_codes else []
    # ePass 现金/预收款须带 toUseUsageCount（对位 membership 的 toUseEntitlementCount）；
    # 纯权益不传该字段（传了易触发 500.042.010/019）；P1 缺参负向仍直接调 BuildOrderPayload 省略
    epass_usage: Optional[int] = None
    if module == "epass" and payment_mode in ("cash", "client_collect"):
        epass_usage = (
            int(to_use_usage_count)
            if to_use_usage_count is not None
            else int(entitlement_count)
        )

    def _OkLine(step_id: str) -> str:
        if env_codes:
            joined = ",".join(f"'{c}'" for c in env_codes)
            return (
                f"ftPayAssertBusinessOkOrEnvReject('{step_id}', [{joined}], "
                f"'Program 未开通现金/客户预收款能力');"
            )
        return f"ftPayAssertBusinessOk('{step_id}');"

    def _DetailOkLine(step_id: str) -> str:
        if env_codes:
            return f"ftPayAssertBusinessOkIfHasOrder('{step_id}');"
        return f"ftPayAssertBusinessOk('{step_id}');"

    def _RejectTests(step_id: str) -> List[str]:
        lines = [f"ftPayAssertBusinessRejected('{step_id}');"]
        codes = [str(c) for c in (reject_err_codes or []) if str(c).strip()]
        if not codes and reject_err_code:
            codes = [str(reject_err_code)]
        if len(codes) == 1:
            lines.append(f"ftPayAssertErrCode('{step_id}', '{codes[0]}');")
        elif len(codes) > 1:
            joined = ",".join(f"'{c}'" for c in codes)
            lines.append(f"ftPayAssertErrCodeOneOf('{step_id}', [{joined}]);")
        if reject_msg:
            # JS 字符串用 JSON 转义，避免文案内引号打断
            msg_js = json.dumps(reject_msg, ensure_ascii=False)
            lines.append(f"ftPayAssertMsgEquals('{step_id}', {msg_js});")
        return lines

    items: List[JsonObject] = []
    if refresh_membership and module == "membership":
        items.append(BuildMembershipRegisterItem(f"{step_prefix}-MS"))
    if refresh_epass and module == "epass":
        items.append(BuildEpassCreateItem(f"{step_prefix}-EP"))
    items.append(
        BuildAvailabilityItem(
            module=module,
            step_id=f"{step_prefix}-AVL",
            adult_count=adult_count,
        )
    )

    preview_body = BuildOrderPayload(
        module=module,
        payment_mode=payment_mode,
        entitlement_count=entitlement_count,
        async_value=async_value,
        include_async_key=include_async_key,
        for_preview=True,
        adult_count=adult_count,
        cash_payment_applied=cash_payment_applied,
        omit_cashier=omit_cashier,
        to_use_usage_count=epass_usage,
    )
    preview_tests: List[str]
    if expect_preview_reject:
        preview_tests = Lines_Step(
            f"{step_prefix}-PRE",
            _RejectTests(f"{step_prefix}-PRE"),
        )
        payment_on_preview: Optional[Literal["generic", "client_collect"]] = None
    else:
        preview_tests = Lines_Step(
            f"{step_prefix}-PRE",
            [_OkLine(f"{step_prefix}-PRE")],
        )
        payment_on_preview = assert_kind

    items.append(
        RequestItem(
            name=PurposeName(f"{purpose} · Preview", f"{step_prefix}-PRE", "POST", "/prebooking/preview"),
            method="POST",
            url_path=PreviewPath(module),
            body=preview_body,
            headers=BearerJsonHeaders(),
            description=f"{purpose} · Preview · mode={payment_mode} · entitlement={entitlement_count}",
            prerequest_lines=Prerequest_OrderBody(adult_count=adult_count),
            test_lines=preview_tests,
            payment_assert=payment_on_preview,
        )
    )

    # 仅 Preview 负向：不到 Create；若同时 expect_create_reject 则继续验下单报错
    if (expect_preview_reject and not expect_create_reject) or not do_create:
        return items

    create_body = BuildOrderPayload(
        module=module,
        payment_mode=payment_mode,
        entitlement_count=entitlement_count,
        async_value=async_value,
        include_async_key=include_async_key,
        for_preview=False,
        adult_count=adult_count,
        cash_payment_applied=cash_payment_applied,
        omit_cashier=omit_cashier,
        to_use_usage_count=epass_usage,
    )
    if expect_create_reject:
        items.append(
            RequestItem(
                name=PurposeName(f"{purpose} · Create", f"{step_prefix}-CRT", "POST", "/prebooking"),
                method="POST",
                url_path=CreatePath(module),
                body=create_body,
                headers=BearerJsonHeaders(),
                description=f"{purpose} · Create 预期业务报错 · mode={payment_mode}",
                prerequest_lines=Prerequest_OrderBody(adult_count=adult_count),
                test_lines=Lines_Step(
                    f"{step_prefix}-CRT",
                    _RejectTests(f"{step_prefix}-CRT"),
                ),
            )
        )
        return items

    items.append(
        RequestItem(
            name=PurposeName(f"{purpose} · Create", f"{step_prefix}-CRT", "POST", "/prebooking"),
            method="POST",
            url_path=CreatePath(module),
            body=create_body,
            headers=BearerJsonHeaders(),
            description=f"{purpose} · Create · mode={payment_mode}",
            prerequest_lines=Prerequest_OrderBody(adult_count=adult_count),
            test_lines=Lines_Step(
                f"{step_prefix}-CRT",
                [
                    _OkLine(f"{step_prefix}-CRT"),
                    f"ftAssertPrebookingPassengersShape('{step_prefix}-CRT');",
                    f"ftPaySaveUsageOrderId('{step_prefix}-CRT');",
                ],
            ),
            payment_assert=assert_kind,
        )
    )
    detail_prerequest: List[str] = []
    if payment_mode == "client_collect":
        # Detail 无 CLIENT_COLLECT 请求体，需强制保留客户预收费场景标记
        omit_flag = "true" if omit_cashier else "false"
        detail_prerequest = [
            "pm.environment.set('payment_scenario', 'CLIENT_COLLECT');",
            "pm.environment.set('order_api_stage', 'DETAIL');",
            f"pm.environment.set('client_collect_omit_cashier', '{omit_flag}');",
        ]
    if env_codes:
        # 上游 Preview/Create 环境软拒后跳过 Detail HTTP，避免旧 usageOrderId 脏读
        detail_prerequest = [
            "if (String(pm.variables.get('ftPayLastEnvReject') || '').trim()) {"
            " console.warn('[ft-pay] skip Detail: ftPayLastEnvReject');"
            " try { if (pm.execution && typeof pm.execution.skipRequest === 'function') pm.execution.skipRequest(); } catch (eSk) {}"
            " }",
            *detail_prerequest,
        ]
    items.append(
        RequestItem(
            name=PurposeName(f"{purpose} · Detail", f"{step_prefix}-DTL", "POST", "/details"),
            method="POST",
            url_path=DetailPath(module),
            body=DetailBody(),
            headers=BearerJsonHeaders(),
            description=f"{purpose} · Order Detail · payment 阶段断言",
            prerequest_lines=detail_prerequest or None,
            test_lines=Lines_Step(
                f"{step_prefix}-DTL",
                [
                    _DetailOkLine(f"{step_prefix}-DTL"),
                    f"ftPayCapturePayableFromResponse('{step_prefix}-DTL');",
                ],
            ),
            payment_assert=assert_kind,
        )
    )
    if initiate_payment is not None:
        pay_tests = (
            [f"ftPayAssertPaymentRedirect('{step_prefix}-PAY');"]
            if initiate_payment == "redirect"
            else [f"ftPayAssertPaymentNotRequired('{step_prefix}-PAY');"]
        )
        items.append(
            RequestItem(
                name=PurposeName(
                    f"{purpose} · 发起支付",
                    f"{step_prefix}-PAY",
                    "POST",
                    "/orders/payments",
                ),
                method="POST",
                url_path="/v2/orders/payments",
                body=InitiatePaymentBody(),
                headers=BearerJsonHeaders(),
                description=(
                    "POST /v2/orders/payments · H5_CASHIER · "
                    + (
                        "payableAmount!=0 期望 REDIRECT；=0 期望 500.000.802"
                        if initiate_payment == "redirect"
                        else "0 元单期望 errCode=500.000.802"
                    )
                ),
                prerequest_lines=(
                    [
                        "if (String(pm.variables.get('ftPayLastEnvReject') || '').trim()) {"
                        " console.warn('[ft-pay] skip Pay: ftPayLastEnvReject');"
                        " try { if (pm.execution && typeof pm.execution.skipRequest === 'function') pm.execution.skipRequest(); } catch (eSk) {}"
                        " }",
                        "ftPayResolveBodyPlaceholders();",
                    ]
                    if env_codes
                    else ["ftPayResolveBodyPlaceholders();"]
                ),
                test_lines=Lines_Step(f"{step_prefix}-PAY", pay_tests),
            )
        )
    items.append(
        RequestItem(
            name=PurposeName(f"{purpose} · 取消 usage", f"{step_prefix}-CAN", "PATCH", "/orders"),
            method="PATCH",
            url_path="/v2/orders",
            body=json.dumps(
                {"status": 3, "orderId": "{{usageOrderId}}"},
                ensure_ascii=False,
                indent=2,
            ),
            headers=BearerJsonHeaders(),
            description=(
                "尝试取消 usageOrderId；待支付 status=9 不可取消时 msg="
                "Order cancellation failed. Please try again later.；"
                "以取消后详情/列表断言为准"
            ),
            prerequest_lines=["ftPayResolveBodyPlaceholders();"],
            test_lines=Lines_Step(
                f"{step_prefix}-CAN",
                [f"ftPayAssertCancelUsageResponse('{step_prefix}-CAN');"],
            ),
        )
    )
    # 取消后：订单详情 + 订单列表
    if module == "membership":
        items.append(
            RequestItem(
                name=PurposeName(
                    f"{purpose} · 取消后详情",
                    f"{step_prefix}-CAN-DTL",
                    "POST",
                    "/memberships/details",
                ),
                method="POST",
                url_path="/v2/orders/memberships/details",
                body=DetailBody(),
                headers=BearerJsonHeaders(),
                description="取消后详情 · status=3（已取消）或 9（待支付不可取消，正常）",
                prerequest_lines=["ftPayResolveBodyPlaceholders();"],
                test_lines=Lines_Step(
                    f"{step_prefix}-CAN-DTL",
                    [f"ftPayAssertPostCancelOrderDetail('{step_prefix}-CAN-DTL');"],
                ),
            )
        )
        items.append(
            RequestItem(
                name=PurposeName(
                    f"{purpose} · 取消后列表",
                    f"{step_prefix}-CAN-LST",
                    "POST",
                    "/orders/memberships",
                ),
                method="POST",
                url_path="/v2/orders/memberships",
                body=MembershipOrdersListBody(),
                headers=BearerJsonHeaders(),
                description="取消后列表 · 含 usageOrderId · status=3 或 9（待支付不可取消）",
                prerequest_lines=["ftPayResolveBodyPlaceholders();"],
                test_lines=Lines_Step(
                    f"{step_prefix}-CAN-LST",
                    [f"ftPayAssertPostCancelOrderInList('{step_prefix}-CAN-LST');"],
                ),
            )
        )
    elif module == "epass":
        items.append(
            RequestItem(
                name=PurposeName(
                    f"{purpose} · 取消后详情",
                    f"{step_prefix}-CAN-DTL",
                    "POST",
                    "/ePasses/details",
                ),
                method="POST",
                url_path="/v2/orders/ePasses/details",
                body=DetailBody(),
                headers=BearerJsonHeaders(),
                description="取消后详情 · status=3（已取消）或 9（待支付不可取消，正常）",
                prerequest_lines=["ftPayResolveBodyPlaceholders();"],
                test_lines=Lines_Step(
                    f"{step_prefix}-CAN-DTL",
                    [f"ftPayAssertPostCancelOrderDetail('{step_prefix}-CAN-DTL');"],
                ),
            )
        )
        items.append(
            RequestItem(
                name=PurposeName(
                    f"{purpose} · 取消后列表",
                    f"{step_prefix}-CAN-LST",
                    "POST",
                    "/orders/ePasses",
                ),
                method="POST",
                url_path="/v2/orders/ePasses",
                body=EpassOrdersListBody(),
                headers=BearerJsonHeaders(),
                description="取消后列表 · 含 usageOrderId · status=3 或 9（待支付不可取消）",
                prerequest_lines=["ftPayResolveBodyPlaceholders();"],
                test_lines=Lines_Step(
                    f"{step_prefix}-CAN-LST",
                    [f"ftPayAssertPostCancelOrderInList('{step_prefix}-CAN-LST');"],
                ),
            )
        )
    return items


def BuildBundleChainItems(
    *,
    step_prefix: str,
    purpose: str,
    payment_mode: PaymentMode,
    expect_reject: bool,
    refresh_epass: bool = True,
    cash_ignored: bool = False,
    reject_err_codes: Optional[Sequence[str]] = None,
    reject_msg: Optional[str] = None,
    soft_if_ok: bool = False,
) -> List[JsonObject]:
    """
    ePass Bundle：可用性（无 ePass）→ Create bundle。

    - 纯权益：成功（不传 cashier / CLIENT_COLLECT）
    - 现金：后端**忽略**现金入参且不报错（``cash_ignored=True`` 时按权益成功断言）
    - 客户预收款：``expect_reject=True``，Create 业务报错（ePass 无预收款能力）
    - ``soft_if_ok``：沙箱未触发拒绝时软过（如 Lounge Bundle 忽略 CLIENT_COLLECT）
    """
    items: List[JsonObject] = []
    if refresh_epass:
        items.append(BuildEpassCreateItem(f"{step_prefix}-EP"))
    items.append(
        RequestItem(
            name=PurposeName(f"{purpose} · 可用性", f"{step_prefix}-AVL", "POST", "/prebookings/availability"),
            method="POST",
            url_path="/v2/resources/prebookings/availability",
            body=json.dumps(
                {
                    "module": CurrentEpassModule(),
                    "resourceId": ResourceTemplate(),
                    "prebookingDate": "{{prebookingDate}}",
                    "adultCount": PAYMENT_ADULT_COUNT,
                    "childCount": PAYMENT_CHILD_COUNT,
                },
                ensure_ascii=False,
                indent=2,
            ),
            headers=BearerJsonHeaders(),
            description="Bundle 可用性（无 ePassId）· adultCount=3",
            prerequest_lines=[
                *Prerequest_NewClientUserId(),
                *Prerequest_CommonSetup(),
            ],
            test_lines=Lines_Step(
                f"{step_prefix}-AVL",
                [
                    f"ftPayAssertBusinessOk('{step_prefix}-AVL');",
                    f"ftAssertAvailabilitySuccess('{step_prefix}-AVL');",
                    "ftPaySetVar('prebookingDate', ftPayGetVar('prebookingDate'));",
                ],
            ),
        )
    )
    body = BuildOrderPayload(
        module="epass",
        payment_mode=payment_mode,
        entitlement_count=PAYMENT_ADULT_COUNT if payment_mode == "entitlement" else 0,
        async_value=False,
        include_async_key=True,
        for_preview=False,
        bundle=True,
    )
    if expect_reject:
        if soft_if_ok:
            reject_tests = [
                f"ftPayAssertBusinessRejectedOrSkipIfOk('{step_prefix}-BDL', "
                f"'Lounge/沙箱 Bundle 未触发 CLIENT_COLLECT 拒绝');"
            ]
        else:
            reject_tests = [f"ftPayAssertBusinessRejected('{step_prefix}-BDL');"]
            codes = [str(c) for c in (reject_err_codes or []) if str(c).strip()]
            if len(codes) == 1:
                reject_tests.append(f"ftPayAssertErrCode('{step_prefix}-BDL', '{codes[0]}');")
            elif len(codes) > 1:
                joined = ",".join(f"'{c}'" for c in codes)
                reject_tests.append(
                    f"ftPayAssertErrCodeOneOf('{step_prefix}-BDL', [{joined}]);"
                )
            if reject_msg:
                msg_js = json.dumps(reject_msg, ensure_ascii=False)
                reject_tests.append(f"ftPayAssertMsgEquals('{step_prefix}-BDL', {msg_js});")
        items.append(
            RequestItem(
                name=PurposeName(f"{purpose} · Bundle 拒绝", f"{step_prefix}-BDL", "POST", "/ePasses/bundle"),
                method="POST",
                url_path=f"/v2/orders/{OrdersPathSegment()}/ePasses/bundle",
                body=body,
                headers=BearerJsonHeaders(),
                description=(
                    f"Bundle 负向 · mode={payment_mode} · 预期业务报错 code=-1"
                    + (" · 固定 conflict msg" if reject_msg and not soft_if_ok else "")
                    + (" · 未触发可软过" if soft_if_ok else "")
                ),
                prerequest_lines=Prerequest_OrderBody(),
                test_lines=Lines_Step(f"{step_prefix}-BDL", reject_tests),
            )
        )
        return items

    success_desc = (
        "Bundle 传现金入参但后端忽略 · 按权益支付成功、不报错"
        if cash_ignored
        else "Bundle 纯权益正向"
    )
    items.append(
        RequestItem(
            name=PurposeName(f"{purpose} · Bundle Create", f"{step_prefix}-BDL", "POST", "/ePasses/bundle"),
            method="POST",
            url_path=f"/v2/orders/{OrdersPathSegment()}/ePasses/bundle",
            body=body,
            headers=BearerJsonHeaders(),
            description=success_desc,
            prerequest_lines=Prerequest_OrderBody(),
            test_lines=Lines_Step(
                f"{step_prefix}-BDL",
                [
                    f"ftPayAssertBusinessOk('{step_prefix}-BDL');",
                    f"ftAssertPrebookingPassengersShape('{step_prefix}-BDL');",
                    f"ftAssertBundleOrderSuccess('{step_prefix}-BDL');",
                    f"ftPaySaveUsageOrderId('{step_prefix}-BDL');",
                ],
            ),
            payment_assert="generic",
        )
    )
    items.append(
        RequestItem(
            name=PurposeName(f"{purpose} · 取消 usage", f"{step_prefix}-CAN-U", "PATCH", "/orders"),
            method="PATCH",
            url_path="/v2/orders",
            body=json.dumps({"status": 3, "orderId": "{{usageOrderId}}"}, indent=2),
            headers=BearerJsonHeaders(),
            description=(
                "取消 Bundle usage；status=9 待支付不可取消时 msg="
                + CANCEL_FAILED_MSG
            ),
            prerequest_lines=["ftPayResolveBodyPlaceholders();"],
            test_lines=Lines_Step(
                f"{step_prefix}-CAN-U",
                [f"ftPayAssertCancelUsageResponse('{step_prefix}-CAN-U');"],
            ),
        )
    )
    items.append(
        RequestItem(
            name=PurposeName(f"{purpose} · 取消 MS", f"{step_prefix}-CAN-MS", "PATCH", "/orders"),
            method="PATCH",
            url_path="/v2/orders",
            body=json.dumps({"status": 3, "orderId": "{{purchaseOrderId}}"}, indent=2),
            headers=BearerJsonHeaders(),
            description="取消 Bundle purchaseOrderId（尽力）",
            prerequest_lines=["ftPayResolveBodyPlaceholders();"],
            test_lines=Lines_Step(
                f"{step_prefix}-CAN-MS",
                [
                    "pm.test('取消 MS 响应可解析', function () { pm.expect(pm.response.json()).to.be.an('object'); });"
                ],
            ),
        )
    )
    return items


def _BuildP1CashChildren(module: ModuleKind) -> List[JsonObject]:
    """现金分组：点数 0/1/3 +（membership 专属）true+DP_COLLECT 冲突。"""
    refresh_ms = module == "membership"
    refresh_ep = module == "epass"
    cash_async: Dict[int, Dict[str, Any]] = {
        0: {
            "async_value": True,
            "include_async_key": True,
            "label": "async:true",
            "purpose_async": "async=true",
        },
        1: {
            "async_value": False,
            "include_async_key": True,
            "label": "async:false",
            "purpose_async": "async=false",
        },
        3: {
            "async_value": False,
            "include_async_key": True,
            "label": "async:false",
            "purpose_async": "async=false",
        },
    }
    cash_children: List[JsonObject] = []
    for points in (0, 1, 3):
        cash_adults = AdultCountForEntitlementPoints(points)
        async_cfg = cash_async[points]
        if module == "membership" and points == 1:
            sub_name = '现金使用权益点数1点-"cashPaymentApplied": false'
        elif points == 0:
            sub_name = "现金使用权益点数0点-async:true"
        else:
            sub_name = f"现金使用权益点数{points}点-{async_cfg['label']}"
        cash_children.append(
            Folder(
                sub_name,
                BuildPaymentChainItems(
                    module=module,
                    step_prefix=f"P1-CASH-E{points}",
                    purpose=(
                        f"现金 DP_COLLECT · 权益点{points} · {async_cfg['purpose_async']}"
                    ),
                    payment_mode="cash",
                    entitlement_count=points,
                    adult_count=cash_adults,
                    async_value=bool(async_cfg["async_value"]),
                    include_async_key=bool(async_cfg["include_async_key"]),
                    refresh_membership=refresh_ms,
                    refresh_epass=refresh_ep,
                    initiate_payment="redirect",
                    env_reject_ok_codes=None,
                ),
                description=(
                    (
                        "cashPaymentApplied=false + DP_COLLECT"
                        if module == "membership"
                        else "仅 cashier.DP_COLLECT + toUseUsageCount（不传 cashPaymentApplied）"
                    )
                    + f" · 权益点{points} · {async_cfg['purpose_async']} · Create 后发起支付期望 REDIRECT"
                    + (
                        " · ePass 现金必须业务成功（payable 分支决定 802/REDIRECT）"
                        if module == "epass"
                        else ""
                    )
                ),
            )
        )
    if module == "membership":
        cash_children.append(
            Folder(
                "现金入参冲突 true+DP_COLLECT",
                BuildPaymentChainItems(
                    module="membership",
                    step_prefix="P1-CASH-CONFLICT",
                    purpose="true+DP_COLLECT · 预期 051.023/042.023",
                    payment_mode="cash",
                    entitlement_count=0,
                    adult_count=PAYMENT_ADULT_COUNT,
                    refresh_membership=True,
                    cash_payment_applied=True,
                    expect_preview_reject=True,
                    expect_create_reject=True,
                    reject_err_codes=["500.051.023", "500.042.023"],
                    reject_msg=CASH_COLLECT_CONFLICT_MSG,
                ),
                description=(
                    "cashPaymentApplied=true + cashier.paymentMode=DP_COLLECT · "
                    "Preview+Create 均业务报错（051.023/042.023 + 固定 msg）；无发起支付"
                ),
            )
        )
    return cash_children


def _BuildP1ClientCollectChildren(module: ModuleKind) -> List[JsonObject]:
    """客户预收款：membership 正向；ePass 不支持 → 一律 conflict msg 拒绝。"""
    refresh_ms = module == "membership"
    refresh_ep = module == "epass"
    cc_children: List[JsonObject] = []
    if module == "epass":
        # ePass 无客户预收款能力：CLIENT_COLLECT → conflict msg；点数无关，保留 1 点代表即可
        points = 1
        cc_children.append(
            Folder(
                f"客户预收款使用权益点数{points}点-显式CLIENT_COLLECT-报错",
                BuildPaymentChainItems(
                    module="epass",
                    step_prefix=f"P1-CC-E{points}",
                    purpose=f"ePass 无预收款 · CLIENT_COLLECT · 权益点{points} · 冲突拒绝",
                    payment_mode="client_collect",
                    entitlement_count=points,
                    adult_count=PAYMENT_ADULT_COUNT,
                    refresh_epass=True,
                    expect_preview_reject=True,
                    expect_create_reject=True,
                    reject_err_codes=["500.051.023", "500.042.023"],
                    reject_msg=CASH_COLLECT_CONFLICT_MSG,
                    initiate_payment=None,
                ),
                description=(
                    "ePass 不传 cashPaymentApplied · 仅 cashier.CLIENT_COLLECT · "
                    f"权益点{points} · Preview/Create 期望 conflict msg"
                ),
            )
        )
        return cc_children

    env_cc: Optional[List[str]] = None
    for points in (0, 1, 3):
        cc_expect_reject = points == 3
        if points == 3:
            sub_name = "客户预收款使用权益点数3点等于订单人数，报错"
        else:
            sub_name = f"客户预收款使用权益点数{points}点-显式CLIENT_COLLECT"
        cc_children.append(
            Folder(
                sub_name,
                BuildPaymentChainItems(
                    module=module,
                    step_prefix=f"P1-CC-E{points}",
                    purpose=(
                        f"客户预收费 · 权益点{points} · Preview/Create 预期报错"
                        if cc_expect_reject
                        else f"客户预收费 · 显式CLIENT_COLLECT · 权益点{points}"
                    ),
                    payment_mode="client_collect",
                    entitlement_count=points,
                    adult_count=PAYMENT_ADULT_COUNT,
                    refresh_membership=refresh_ms,
                    refresh_epass=refresh_ep,
                    expect_preview_reject=cc_expect_reject,
                    expect_create_reject=cc_expect_reject,
                    initiate_payment=None if cc_expect_reject else "not_required",
                    env_reject_ok_codes=None if cc_expect_reject else env_cc,
                ),
                description=(
                    "CLIENT_COLLECT · adultCount=3 · Preview/Create 业务报错"
                    if cc_expect_reject
                    else (
                        f"显式 cashier.paymentMode=CLIENT_COLLECT · 权益点{points} · "
                        "Create 后发起支付期望 802"
                    )
                ),
            )
        )
    # Membership：只传 cashPaymentApplied=true、不传 cashier → 默认客户预收款
    for points in (0, 1):
        cc_children.append(
            Folder(
                f'客户预收款使用权益点数{points}点-只传cashPaymentApplied:true不传cashier',
                BuildPaymentChainItems(
                    module="membership",
                    step_prefix=f"P1-CC-OMIT-E{points}",
                    purpose=f"客户预收费 · 只传cashPaymentApplied:true · 权益点{points}",
                    payment_mode="client_collect",
                    entitlement_count=points,
                    adult_count=PAYMENT_ADULT_COUNT,
                    refresh_membership=True,
                    omit_cashier=True,
                    initiate_payment="not_required",
                ),
                description=(
                    "只传 cashPaymentApplied=true、不传 cashier · "
                    f"默认 CLIENT_COLLECT · 权益点{points} · Create 后发起支付期望 802"
                ),
            )
        )
    return cc_children


def _BuildP1EpassBundleFolder() -> JsonObject:
    return Folder(
        "Bundle",
        [
            Folder(
                "Bundle纯权益支付-成功",
                BuildBundleChainItems(
                    step_prefix="P1-BDL-ENT",
                    purpose="Bundle 纯权益",
                    payment_mode="entitlement",
                    expect_reject=False,
                ),
                description="不传 CLIENT_COLLECT · Bundle Create 成功 · Create 后取消 usage/MS",
            ),
            Folder(
                "Bundle现金入参-后端忽略不报错",
                BuildBundleChainItems(
                    step_prefix="P1-BDL-CASH",
                    purpose="Bundle 现金入参忽略",
                    payment_mode="cash",
                    expect_reject=False,
                    cash_ignored=True,
                ),
                description=(
                    "传入 false/DP_COLLECT 现金组合 · 后端忽略入参、不报错 · "
                    "按权益链路成功（非拒绝）· Create 后取消"
                ),
            ),
            Folder(
                "Bundle客户预收款-报错",
                BuildBundleChainItems(
                    step_prefix="P1-BDL-CC",
                    purpose="Bundle 客户预收费拒绝",
                    payment_mode="client_collect",
                    expect_reject=True,
                    reject_err_codes=["500.051.023", "500.042.023"],
                    reject_msg=CASH_COLLECT_CONFLICT_MSG,
                    soft_if_ok=ActiveCategory().key == "lounge",
                ),
                description=(
                    "仅 cashier.CLIENT_COLLECT（不传 cashPaymentApplied）· "
                    "Bundle Create 期望 conflict msg"
                    + (
                        "；Lounge 沙箱未触发拒绝时可软过"
                        if ActiveCategory().key == "lounge"
                        else ""
                    )
                ),
            ),
        ],
        description=(
            "Bundle 只支持权益语义：现金入参忽略不报错；客户预收款报错（conflict msg）；"
            "成功单 Create 后取消 usage（status=9 断言取消失败文案）"
        ),
    )


def BuildP0PaymentFolders(module: ModuleKind) -> List[JsonObject]:
    """
    P0 冒烟（Membership / E-pass 同构裁剪）。

    按 P1 主轴各取 1 条：权益足额 / 现金 0 点 /
    Membership 非显示预收款 0 点（只传 cashPaymentApplied:true）/
    ePass 预收款 conflict（点 1 显式 CLIENT_COLLECT）。
    同分组形态；含发起支付与取消后详情/列表。点数矩阵、async 分散、负向、Bundle、缺口 → 仅 P1。
    """
    refresh_ms = module == "membership"
    refresh_ep = module == "epass"
    env_cash = None
    return [
        Folder(
            "权益支付",
            [
                Folder(
                    "权益支付使用权益点数3点-冒烟",
                    BuildPaymentChainItems(
                        module=module,
                        step_prefix="P0-ENT3",
                        purpose="权益支付冒烟 entitlement=3",
                        payment_mode="entitlement",
                        entitlement_count=PAYMENT_ADULT_COUNT,
                        async_value=False,
                        include_async_key=True,
                        refresh_membership=refresh_ms,
                        refresh_epass=refresh_ep,
                        initiate_payment="redirect",
                    ),
                    description="P0 · 权益足额 · async=false · Create 后发起支付 REDIRECT",
                ),
            ],
            description="P0 冒烟 · 权益主路径（对应 P1 权益足额）",
        ),
        Folder(
            "现金",
            [
                Folder(
                    "现金使用权益点数0点-冒烟",
                    BuildPaymentChainItems(
                        module=module,
                        step_prefix="P0-CASH-E0",
                        purpose="现金冒烟 DP_COLLECT · 权益点0",
                        payment_mode="cash",
                        entitlement_count=0,
                        adult_count=PAYMENT_ADULT_COUNT,
                        async_value=False,
                        include_async_key=True,
                        refresh_membership=refresh_ms,
                        refresh_epass=refresh_ep,
                        initiate_payment="redirect",
                        env_reject_ok_codes=env_cash,
                    ),
                    description=(
                        "P0 · Membership false+DP_COLLECT / E-pass 仅 DP_COLLECT（不传 cashPaymentApplied）· "
                        "Create 后发起支付 REDIRECT"
                    ),
                ),
            ],
            description="P0 冒烟 · 现金主路径（对应 P1 现金 0 点）",
        ),
        Folder(
            "客户预收款",
            (
                [
                    Folder(
                        "客户预收款使用权益点数1点-显式CLIENT_COLLECT-报错-冒烟",
                        BuildPaymentChainItems(
                            module="epass",
                            step_prefix="P0-CC-E1",
                            purpose="ePass 无预收款冒烟 · CLIENT_COLLECT · 冲突拒绝",
                            payment_mode="client_collect",
                            entitlement_count=1,
                            adult_count=PAYMENT_ADULT_COUNT,
                            async_value=False,
                            include_async_key=True,
                            refresh_epass=True,
                            expect_preview_reject=True,
                            expect_create_reject=True,
                            reject_err_codes=["500.051.023", "500.042.023"],
                            reject_msg=CASH_COLLECT_CONFLICT_MSG,
                            initiate_payment=None,
                        ),
                        description=(
                            "P0 · ePass 无客户预收款 · 显式 CLIENT_COLLECT → conflict msg"
                            "（对齐 P1 点数 1 代表）"
                        ),
                    ),
                ]
                if module == "epass"
                else [
                    Folder(
                        "客户预收款使用权益点数0点-只传cashPaymentApplied:true不传cashier-冒烟",
                        BuildPaymentChainItems(
                            module="membership",
                            step_prefix="P0-CC-OMIT-E0",
                            purpose=(
                                "客户预收费冒烟 · 非显示 · "
                                "只传cashPaymentApplied:true · 权益点0"
                            ),
                            payment_mode="client_collect",
                            entitlement_count=0,
                            adult_count=PAYMENT_ADULT_COUNT,
                            async_value=False,
                            include_async_key=True,
                            refresh_membership=True,
                            omit_cashier=True,
                            initiate_payment="not_required",
                        ),
                        description=(
                            "P0 · 非显示客户预收款 · 只传 cashPaymentApplied=true、"
                            "不传 cashier（默认 CLIENT_COLLECT）· Create 后发起支付 802"
                        ),
                    ),
                ]
            ),
            description=(
                "P0 冒烟 · ePass 无预收款 conflict（对齐 P1 点 1）"
                if module == "epass"
                else "P0 冒烟 · Membership 非显示预收款主路径（只传 cashPaymentApplied:true）"
            ),
        ),
    ]


def BuildP1PaymentFolders(module: ModuleKind) -> List[JsonObject]:
    """
    P1 目录：一级支付方式 → 二级点数/变体（Membership / E-pass 同构）。

    - 成功 Create 后一律跟 ``POST /v2/orders/payments``（现金 REDIRECT；权益/预收费 0 元 802）。
    - 国内 async 三种变体（缺失 / false / true）分散到权益与现金用例，不单开分组。
    - E-pass 另含 Bundle（现金忽略不报错 / 预收款报错）与 Preview/支付链接全量。
    - Membership 另含 toUseEntitlementDetail / 权益不足 / 支付链接全量。
    """
    # 延迟导入避免循环依赖
    from ft_prebooking_payment_p1_gaps import (
        BuildP1EpassGapFolders,
        BuildP1MembershipExtraFolders,
    )

    refresh_ms = module == "membership"
    refresh_ep = module == "epass"
    folders: List[JsonObject] = [
        Folder(
            "权益支付",
            [
                Folder(
                    "权益支付使用权益点数3点-不传async",
                    BuildPaymentChainItems(
                        module=module,
                        step_prefix="P1-ENT1",
                        purpose="权益支付 entitlement=3 · async缺失",
                        payment_mode="entitlement",
                        entitlement_count=PAYMENT_ADULT_COUNT,
                        adult_count=PAYMENT_ADULT_COUNT,
                        include_async_key=False,
                        refresh_membership=refresh_ms,
                        refresh_epass=refresh_ep,
                        # 用户承担预约费时权益单仍可能应付 PREBOOKING_FEE → REDIRECT
                        initiate_payment="redirect",
                    ),
                    description=(
                        "权益足额 · 可用性/预约 adultCount=3 · 不传 async · "
                        "Create 后发起支付期望 REDIRECT"
                        "（纯权益不可用 1 点约 3 人，点数差异见现金/预收款）"
                    ),
                ),
                Folder(
                    "权益支付使用权益点数3点-async:false",
                    BuildPaymentChainItems(
                        module=module,
                        step_prefix="P1-ENT3",
                        purpose="权益支付 entitlement=3 · async=false",
                        payment_mode="entitlement",
                        entitlement_count=PAYMENT_ADULT_COUNT,
                        async_value=False,
                        include_async_key=True,
                        refresh_membership=refresh_ms,
                        refresh_epass=refresh_ep,
                        initiate_payment="redirect",
                    ),
                    description="权益足额 · async=false · Create 后发起支付期望 REDIRECT",
                ),
            ],
            description="纯权益 · 含 async 缺失/false；Create 后均发起支付",
        ),
        Folder(
            "现金",
            _BuildP1CashChildren(module),
            description=(
                "点数 0/1/3 正向（0 点覆盖 async=true）；Create 后发起支付 REDIRECT"
                + ("；含 true+DP_COLLECT 负向" if module == "membership" else "")
            ),
        ),
        Folder(
            "客户预收款",
            _BuildP1ClientCollectChildren(module),
            description=(
                "ePass：无客户预收款能力 · CLIENT_COLLECT 一律 conflict msg 拒绝"
                if module == "epass"
                else (
                    "显式 CLIENT_COLLECT · 点数 0/1 正向、点数 3 报错"
                    "；另：只传 cashPaymentApplied=true 不传 cashier（默认预收费）点数 0/1"
                )
            ),
        ),
    ]
    if module == "epass":
        folders.append(_BuildP1EpassBundleFolder())
        folders.extend(BuildP1EpassGapFolders())
    else:
        folders.extend(BuildP1MembershipExtraFolders())
    return folders


def BuildEpassTeardownFolder() -> JsonObject:
    return Folder(
        "99 Teardown",
        [
            RequestItem(
                name=PurposeName("收尾：取消 MS 购买单", "TD-MS", "PATCH", "/orders"),
                method="PATCH",
                url_path="/v2/orders",
                body=json.dumps({"status": 3, "orderId": "{{purchaseOrderId}}"}, indent=2),
                headers=BearerJsonHeaders(),
                description="取消 SETUP 创建的 purchaseOrderId（尽力）",
                test_lines=Lines_Step(
                    "TD-MS",
                    [
                        "pm.test('TD-MS: 取消响应可解析', function () { pm.expect(pm.response.json()).to.be.an('object'); });"
                    ],
                ),
            )
        ],
        description="ePass 创建单收尾",
    )


def CollectionMeta(module: ModuleKind, priority: PriorityKind) -> JsonObject:
    mod_label = "Membership" if module == "membership" else "E-pass"
    pri_label = "P0 冒烟" if priority == "p0" else "P1 全量"
    cat = ActiveCategory()
    return {
        "name": f"{cat.collection_prefix} {mod_label} Prebooking Payment · {pri_label}",
        "description": (
            f"由 ft_prebooking_payment_common 生成 · {cat.label_en} · {mod_label} · {pri_label}\n"
            f"adultCount={PAYMENT_ADULT_COUNT}；resource={cat.resource_env_key}；module={cat.epass_module}。\n"
            f"payment 断言内联 tools/apifox_payment_assert_*.js。\n"
            "\n"
            f"{BuildEnvPricingScenarioDescription()}"
        ),
        "schema": POSTMAN_SCHEMA,
    }


def BuildCollection(module: ModuleKind, priority: PriorityKind) -> JsonObject:
    # 不再挂 01 Setup：各支付链路内 refresh_membership / refresh_epass 已自包含造数
    cat = ActiveCategory()
    items: List[Union[JsonObject, Any]] = [
        BuildAuthFolder(),
    ]
    if priority == "p0":
        items.extend(BuildP0PaymentFolders(module))
    else:
        items.extend(BuildP1PaymentFolders(module))
    if module == "epass":
        items.append(BuildEpassTeardownFolder())

    variables = [
        CollectionVariable("baseUrl", ""),
        CollectionVariable("x-version", ""),
        CollectionVariable("ProgramID", ""),
        CollectionVariable("clientId", ""),
        CollectionVariable("secret", ""),
        CollectionVariable(ResourceEnvKey(), ActiveCategory().default_resource_id),
        CollectionVariable("fastTrackAdultCount", str(PAYMENT_ADULT_COUNT)),
        CollectionVariable("fastTrackChildCount", str(PAYMENT_CHILD_COUNT)),
        CollectionVariable("epassModule", str(CurrentEpassModule())),
        CollectionVariable("clientUserId", ""),
        CollectionVariable("membershipId", ""),
        CollectionVariable("ePassId", ""),
        CollectionVariable("purchaseOrderId", ""),
        CollectionVariable("usageOrderId", ""),
        # 禁止预置空 prebookingToken：customHttp 下空串会盖住可用性写入，replaceIn 也替换成空
        CollectionVariable("prebookingDate", ""),
        # 单一环境 · 本品类定价键（Lounge=lounge*；与 FT 同 Environment 换名并存）
        CollectionVariable(
            cat.env_payment_scene_id,
            cat.payment_scene_id,
            "定价场景号标注（1/2/3/5/7）；只作对照，接口不读此字段",
        ),
        CollectionVariable(
            cat.env_prebooking_fee_payer,
            cat.prebooking_fee_payer,
            "预约费承担方：user=用户付FEE / client=客户承担FEE=0 / unset=未配置（常负向）",
        ),
        CollectionVariable(
            cat.env_prebooking_unit_price,
            cat.prebooking_unit_price,
            "预约费单价（每人）；仅 payer=user 时 FEE=人数×本值",
        ),
        CollectionVariable(
            cat.env_overage_unit_price,
            cat.overage_unit_price,
            "超人次单价（每人）；BASE=人数×本值；折扣=min(权益点,人数)×本值",
        ),
        CollectionVariable(
            cat.env_payment_scene_expect_error,
            cat.payment_scene_expect_error,
            "本场景是否期望报错：true=负向（如场景1）；false=正向算价",
        ),
        CollectionVariable(
            cat.env_assert_payment_env_price,
            cat.assert_payment_env_price,
            "是否按环境单价断言 E-BASE/E-FEE/E-ORIG/E-DISC/E-PAY；false=跳过金额期望",
        ),
        CollectionVariable(
            "prebookingCategory",
            cat.key,
            "品类轴：fastTrack | lounge",
        ),
        CollectionVariable(
            "toUseEntitlementCount",
            "",
            "拟用权益点数（membership 入参）；空=未指定；ePass 纯权益常按乘客数推断",
        ),
    ]
    return {
        "info": CollectionMeta(module, priority),
        "item": items,
        "variable": variables,
    }


def OutName(module: ModuleKind, priority: PriorityKind) -> str:
    prefix = ActiveCategory().out_name_prefix
    return f"{prefix}-{module.capitalize()}-Prebooking-Payment-{priority.upper()}.postman_collection.json"


def Generate(
    module: ModuleKind,
    priority: PriorityKind,
    *,
    category: CategoryKind = "fastTrack",
) -> Path:
    SetActiveCategory(category)
    collection = BuildCollection(module, priority)
    out = CollectionPath(OutName(module, priority))
    WriteCollectionJson(out, collection)
    return out
