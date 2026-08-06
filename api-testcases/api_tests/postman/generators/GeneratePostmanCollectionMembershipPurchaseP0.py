"""
首次会籍商品购买 · P0 冒烟 Postman Collection v2.1。

两条 E2E（步骤序按用户确认）::

    Preview → Create → Details → Payments → Details → Cancel → Details

1. 商品 B：不传券、``autoRenewal=false``、EUR 原价
2. 商品 A：传 ``CouponIntroValid``、``autoRenewal=true``、引导期（应付可为 0）

环境变量（Apifox Environment，勿写死 secret 进仓库）::

    ProgramID / clientId / secret / baseUrl / x-version
    productBProgramId / productBProgramName / productBPrice / productBCurrency
    productAProgramId / productAProgramName / productAPrice / productAPayableAmount / productACurrency
    CouponIntroValid / returnUrl

用法（仓库根）::

    python api-testcases/api_tests/postman/generators/GeneratePostmanCollectionMembershipPurchaseP0.py
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Final, List, Mapping, Optional, Sequence, Tuple, Union

from collection_builder_common import CollectionPath, Lines_EnsureRequestIdHeader

JsonObject = Dict[str, Any]

POSTMAN_SCHEMA: Final[str] = "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
OUT_NAME: Final[str] = "Membership-Purchase-P0.postman_collection.json"
COLLECTION_DISPLAY_NAME: Final[str] = "Membership Purchase · P0 冒烟（首次会籍购买）"

PATH_AUTH: Final[str] = "/v2/auth/token"
PATH_PREVIEW: Final[str] = "/v2/orders/memberships/purchase/preview"
PATH_CREATE: Final[str] = "/v2/orders/memberships/purchase"
PATH_DETAILS: Final[str] = "/v2/orders/memberships/purchase/details"
PATH_PAYMENTS: Final[str] = "/v2/orders/payments"
PATH_CANCEL: Final[str] = "/v2/orders"

# 业务期望默认值（可提交）；鉴权三列仅从 .env 的 MP_P0_* 注入，勿写死 secret。
DEFAULT_BUSINESS_ENV: Final[Dict[str, str]] = {
    "productBProgramId": "2032786406298624",
    "productBProgramName": "会籍购买测试-无优惠订阅15/15eur",
    "productBPrice": "15",
    "productBCurrency": "EUR",
    "productBDeduction": "0",
    "productAProgramId": "2032786406298624",
    "productAProgramName": "会籍购买测试-有优惠10/0usd",
    "productAPrice": "10",
    "productAPayableAmount": "0",
    "productADeduction": "0",
    "productACurrency": "USD",
    "CouponIntroValid": "PC9850UZX4MWDU9RHW04",
    "CouponIntroValidName": "会籍购买测试-有优惠10/0EUR",
    "returnUrl": "https://www.ly.com",
    "x-version": "canary",
    "baseUrl": "https://developer-sandbox.dragonpass.com/api",
}

# Environment 键 → 填写说明（完整版：Group description / Console）
ENV_KEY_FILL_GUIDE: Final[Dict[str, str]] = {
    "CouponIntroValid": (
        "【入参】body.couponCode。"
        "填沙箱「周期订阅 + 引导期」有效券码。"
        "商品A引导期 / 未开引导期两组都传此键；是否出引导期价由商品侧是否开启引导期阶段计费决定。"
    ),
    "CouponIntroValidName": (
        "【断言】coupon.details.description 期望。"
        "填与 CouponIntroValid 对应的券展示名/描述；接口无 couponName 字段。"
    ),
    "CouponIntroNoRenew": (
        "【入参】body.couponCode。"
        "填「商品A无订阅」或「支持订阅但本单 autoRenewal=false」场景用的券码（通常非引导期价）。"
    ),
    "CouponIntroNoRenewName": (
        "【断言】券 description 期望（若脚本断言）。"
        "与 CouponIntroNoRenew 对应的展示名。"
    ),
    "CouponExpired": "【入参·负向】已过期券码 → Preview 按原价回退 / Create 期望 500.000.702。",
    "CouponIneligible": (
        "【入参·负向】有效但不满足使用条件的券（如未到使用期）→ "
        "Preview valid=false、details=null、按原价 / Create 期望 500.000.702。"
    ),
    "CouponWrongType": "【入参·负向】非周期优惠券码 → Preview 按原价且详情空 / Create 期望 500.000.702。",
    "CouponCrossProgram": "【入参·负向】其它 Program 的券码 → 按无效券 / Create 期望 500.020.031。",
    "CouponNotFoundCode": "【入参·负向】不存在的券码（默认可不改）→ Preview 按原价 / Create 期望 500.020.031。",
    "productBProgramId": "【断言】选中商品 B 的 programId（Retail Program / 商品 ID）。与沙箱商品一致。",
    "productBProgramName": "【断言】商品 B 的 programName 回显。与沙箱展示名一致。",
    "productBPrice": "【断言】商品 B 原价=应付（无券）。→ originalAmount / payableAmount / unitPrice。",
    "productBCurrency": "【断言】商品 B 币种 → payment.currency（如 EUR）。",
    "productBDeduction": "【断言】商品 B 扣减额；无券通常填 0。payable 期望≈ price−deduction。",
    "productAProgramId": "【断言】商品 A（支持订阅+引导期链路）的 programId。",
    "productAProgramName": "【断言】商品 A 的 programName 回显。",
    "productAPrice": "【断言】商品 A 原价 → originalAmount / unitPrice。",
    "productAPayableAmount": (
        "【断言】商品 A 应付（已开启引导期阶段计费）。"
        "引导期常填 0；此时 Create status 期望 9，Payments 可业务失败。"
    ),
    "productADeduction": (
        "【参考】扣减名义键；脚本实际用 money2(productAPrice−productAPayableAmount)，"
        "一般不必改此键。"
    ),
    "productACurrency": "【断言】商品 A 币种 → payment.currency（如 USD）。",
    "productANoSubProgramId": "【断言】「商品A不支持订阅」专用 programId（可与引导期商品不同）。",
    "productANoSubProgramName": "【断言】无订阅商品 A 的 programName。",
    "productANoSubPrice": "【断言】无订阅商品 A 原价（本场景按原价，常=应付）。",
    "productANoSubPayableAmount": "【断言】无订阅商品 A 应付；通常= productANoSubPrice。",
    "productANoSubCurrency": "【断言】无订阅商品 A 币种。",
    "productASubOffProgramId": "【断言】「支持订阅但 autoRenewal=false」专用 programId。",
    "productASubOffProgramName": "【断言】订阅关原价场景的 programName。",
    "productASubOffPrice": "【断言】订阅关场景原价。",
    "productASubOffPayableAmount": "【断言】订阅关场景应付；通常=原价。",
    "productASubOffCurrency": "【断言】订阅关场景币种。",
    "productANoIntroPayableAmount": (
        "【断言】商品 A 应付（传引导期券但商品未开引导期阶段计费 → 按原价）。"
        "通常填成与 productAPrice 相同，此时 deduction 期望 0。"
    ),
    "returnUrl": "【入参】Payments body.returnUrl；H5 收银台回跳地址。",
    "ExistingActiveProfileEmail": "【入参·负向】沙箱已有生效订阅用户的 email（重复购买拒绝）。",
    "ExistingActiveProfileClientUserId": "【入参·负向】同上用户的 clientUserId。",
    "baseUrl": "【环境】网关根地址；换测改 Environment，勿用空集合变量覆盖。",
    "x-version": "【环境】路由头（如 canary）。",
}

# 断言面板短文案（避免 assertInfo 标题过长；完整说明见 ENV_KEY_FILL_GUIDE）
ENV_KEY_FILL_SHORT: Final[Dict[str, str]] = {
    "CouponIntroValid": "入参 couponCode（周期订阅券）",
    "CouponIntroValidName": "断言券 description",
    "CouponIntroNoRenew": "入参 couponCode（无引导期/订阅关）",
    "CouponIntroNoRenewName": "断言券 description",
    "CouponExpired": "入参·过期券",
    "CouponIneligible": "入参·不满足条件券",
    "CouponWrongType": "入参·非周期券",
    "CouponCrossProgram": "入参·跨 Program 券",
    "CouponNotFoundCode": "入参·不存在券（可不改）",
    "productBProgramId": "断言商品B programId",
    "productBProgramName": "断言商品B programName",
    "productBPrice": "断言商品B原价=应付",
    "productBCurrency": "断言商品B币种",
    "productBDeduction": "断言商品B扣减（无券常0）",
    "productAProgramId": "断言商品A programId",
    "productAProgramName": "断言商品A programName",
    "productAPrice": "断言商品A原价",
    "productAPayableAmount": "断言商品A应付（引导期，常0）",
    "productADeduction": "参考·一般不改",
    "productACurrency": "断言商品A币种",
    "productANoSubProgramId": "断言无订阅A programId",
    "productANoSubProgramName": "断言无订阅A programName",
    "productANoSubPrice": "断言无订阅A原价",
    "productANoSubPayableAmount": "断言无订阅A应付(=原价)",
    "productANoSubCurrency": "断言无订阅A币种",
    "productASubOffProgramId": "断言订阅关A programId",
    "productASubOffProgramName": "断言订阅关A programName",
    "productASubOffPrice": "断言订阅关A原价",
    "productASubOffPayableAmount": "断言订阅关A应付(=原价)",
    "productASubOffCurrency": "断言订阅关A币种",
    "productANoIntroPayableAmount": "断言应付(未开引导期，通常=原价)",
    "returnUrl": "入参 Payments 回跳URL",
    "ExistingActiveProfileEmail": "入参·已有订阅用户email",
    "ExistingActiveProfileClientUserId": "入参·已有订阅用户cuid",
    "baseUrl": "环境·网关",
    "x-version": "环境·路由头",
}


def FormatGroupEnvGuideText(
    group_label: str,
    env_keys: Sequence[str],
    *,
    fixed_notes: Sequence[str] = (),
) -> str:
    """生成某 Group 的 Environment 填写指南（中文）。"""
    lines: List[str] = [
        f"======== [{group_label}] Environment 填写指南 ========",
        "说明：下列键请在 Apifox Environment（351893）填写；空则脚本用生成器默认占位。",
        "分类：【入参】进请求体；【断言】对响应期望；【环境】网关/路由；【参考】可不改。",
    ]
    for note in fixed_notes:
        lines.append(f"· 固定/脚本写死：{note}")
    seen: Dict[str, bool] = {}
    for key in env_keys:
        k = (key or "").strip()
        if not k or k in seen:
            continue
        seen[k] = True
        guide = ENV_KEY_FILL_GUIDE.get(k) or "（未登记说明）换测时与断言标题对照填写。"
        lines.append(f"· {k} = {{{{{k}}}}}  ← 当前值见下行 Console「当前值」")
        lines.append(f"  {guide}")
    lines.append("======== 指南结束（本断言恒通过，仅作填写提示）========")
    return "\n".join(lines)


def BuildScenarioDescription() -> str:
    """写入 Apifox 场景 description：生成源 + 变量关系 + 金额公式（对齐 FT payment 说明风格）。"""
    b = DEFAULT_BUSINESS_ENV
    return (
        "由 GeneratePostmanCollectionMembershipPurchaseP0 生成 · Membership Purchase · P0 冒烟\n"
        "鉴权：.env 的 MP_P0_PROGRAM_ID / MP_P0_CLIENT_ID / MP_P0_SECRET → 运行时 ProgramID/clientId/secret\n"
        "环境：baseUrl / x-version 用 Apifox Environment（Environment 351893；勿用空集合变量覆盖）。\n"
        "\n"
        "【链路】\n"
        "1 商品B-无券-原价EUR：Preview→Create→Details→Payments→Details→Cancel→Details（autoRenewal=false）\n"
        "2 商品A-传券-引导期USD：同上（CouponIntroValid + autoRenewal=true）；"
        "payable=0 时 Payments 期望业务失败；其后仍 Cancel→Details\n"
        "\n"
        "【商品 B 变量关系（场景1）】\n"
        f"· productBProgramId / productBProgramName → Preview/Create 选品"
        f"（默认 {b['productBProgramId']} / {b['productBProgramName']}）\n"
        f"· productBPrice → originalAmount / charges.details.unitPrice&amount 期望（默认 {b['productBPrice']}）\n"
        f"· productBCurrency → payment.currency（默认 {b['productBCurrency']}）\n"
        f"· productBDeduction → deductionAmount 期望（无券默认 {b['productBDeduction']}）\n"
        "· payableAmount 期望 = productBPrice − productBDeduction\n"
        "\n"
        "【商品 A 变量关系（场景2）】\n"
        f"· productAProgramId / productAProgramName → Preview/Create 选品"
        f"（默认 {b['productAProgramId']} / {b['productAProgramName']}）\n"
        f"· productAPrice → originalAmount / unitPrice 期望（默认 {b['productAPrice']}）\n"
        f"· productAPayableAmount → payableAmount 期望（引导期默认 {b['productAPayableAmount']}）\n"
        f"· productACurrency → payment.currency（默认 {b['productACurrency']}）\n"
        f"· CouponIntroValid → couponCodes（默认 {b['CouponIntroValid']}）\n"
        "· CouponIntroValidName → coupon.details.description 期望（接口无 couponName 字段，不断言）\n"
        "· deductionAmount 期望 = money2(productAPrice − productAPayableAmount)"
        "（保留两位小数；例 10−0=10；不以 productADeduction 写死为准）\n"
        "· Create.orderCreatedDate：仅断言非空（不校验 UTC 后缀格式）\n"
        "\n"
        "【金额块断言（Preview/Create/Details）】\n"
        "payment.currency / originalAmount / payableAmount / deductionAmount；\n"
        "charges[0].details[0]：paxType=CARDHOLDER、quantity=1、unitPrice、amount=unitPrice×quantity。\n"
        "\n"
        "【运行时变量（勿预置空集合变量）】\n"
        "· uniqueProfileEmail / uniqueProfileClientUserId → Create 时生成\n"
        "· orderIdB / orderIdA → Create 写出，供 Details / Payments / Cancel 使用\n"
        f"· returnUrl → Payments 回跳（默认 {b['returnUrl']}）\n"
    )


def LoadDotEnv() -> None:
    """加载仓库根 .env（不覆盖已有进程环境变量）。"""
    root = Path(__file__).resolve().parents[4]
    env_path = root / ".env"
    if not env_path.is_file():
        return
    try:
        text = env_path.read_text(encoding="utf-8")
    except OSError:
        return
    for line in text.splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def AuthCredentials() -> Dict[str, str]:
    LoadDotEnv()
    return {
        "ProgramID": (os.environ.get("MP_P0_PROGRAM_ID") or "").strip(),
        "clientId": (os.environ.get("MP_P0_CLIENT_ID") or "").strip(),
        "secret": (os.environ.get("MP_P0_SECRET") or "").strip(),
    }


def JsStringLiteral(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def Lines_AnnounceGroupEnv(
    group_label: str,
    env_keys: Sequence[str],
    *,
    fixed_notes: Sequence[str] = (),
) -> Tuple[List[str], List[str]]:
    """
    返回 ``(prerequest_lines, test_lines)``：
    - 只打 Console 短行：``键 = 当前值  // 短含义``（不占断言、不打长文）
    - Pre-request 与 Tests 各打一遍
    """
    keys_raw = [k for k in env_keys if (k or "").strip()]
    keys: List[str] = []
    seen_k: Dict[str, bool] = {}
    for k in keys_raw:
        if k in seen_k:
            continue
        seen_k[k] = True
        keys.append(k)

    label_lit = JsStringLiteral(group_label)
    keys_js = json.dumps(keys, ensure_ascii=False)
    meaning_map: Dict[str, str] = {}
    for k in keys:
        meaning_map[k] = ENV_KEY_FILL_SHORT.get(k) or "对照填写"
    meaning_js = json.dumps(meaning_map, ensure_ascii=False)
    # 固定说明也缩短
    short_notes = [(n if len(n) <= 40 else n[:37] + "…") for n in fixed_notes]
    notes_js = json.dumps(short_notes, ensure_ascii=False)

    log_block: List[str] = [
        "try {",
        f"  var _label = {label_lit};",
        f"  var _keys = {keys_js};",
        f"  var _meanings = {meaning_js};",
        f"  var _notes = {notes_js};",
        "  console.log('[' + _label + '] 要改的数据集列（勿改 Environment 业务键）:');",
        "  for (var _n = 0; _n < (_notes || []).length; _n++) {",
        "    console.log('  · ' + _notes[_n]);",
        "  }",
        "  for (var _i = 0; _i < (_keys || []).length; _i++) {",
        "    var _k = String(_keys[_i] || '');",
        "    if (!_k) continue;",
        "    var _v = '';",
        "    try { _v = String(pm.variables.get(_k) || ''); } catch (eV) {}",
        "    if (!_v) { try { _v = String(pm.collectionVariables.get(_k) || ''); } catch (eC) {} }",
        "    if (!_v) { try { if (typeof getEnv === 'function') _v = String(getEnv(_k) || ''); } catch (eG) {} }",
        "    if (!_v) _v = '(空)';",
        "    var _m = '';",
        "    try { _m = String((_meanings && _meanings[_k]) || ''); } catch (eM) {}",
        "    console.log('  ' + _k + ' = ' + _v + (_m ? ('  // ' + _m) : ''));",
        "  }",
        "} catch (eAnnounce) { console.warn('announce group env', eAnnounce); }",
    ]
    return list(log_block), list(log_block)


def Lines_SeedRuntimeEnv() -> List[str]:
    """
    业务键优先 ``pm.variables``（数据集选行）；空则用 Environment；再空用生成器占位。
    只把结果写入 variables（不回写 Environment 业务键，避免污染共用 351893）。
    ``baseUrl`` / ``x-version`` 仍可读 Environment。
    鉴权三列来自本机 .env 的 MP_P0_*（勿提交）。
    """
    creds = AuthCredentials()
    infra = frozenset({"baseUrl", "x-version"})
    lines: List[str] = ["try {"]
    for key, value in DEFAULT_BUSINESS_ENV.items():
        lit = JsStringLiteral(value)
        k_lit = JsStringLiteral(key)
        lines.append("  (function () {")
        lines.append(f"    var _k = {k_lit};")
        lines.append("    var _v = '';")
        lines.append("    try { _v = String(pm.variables.get(_k) || '').trim(); } catch (e0) {}")
        if key in infra:
            lines.append(
                "    if (!_v) { try { _v = String((pm.environment && pm.environment.get(_k)) || '').trim(); } catch (e1) {} }"
            )
        else:
            # 业务键：仅当 variables 为空时才读 Environment（兼容旧 P0 手填）；有数据集行则以行为准
            lines.append(
                "    if (!_v) { try { _v = String((pm.environment && pm.environment.get(_k)) || '').trim(); } catch (e1) {} }"
            )
        lines.append(f"    if (!_v) _v = {lit};")
        lines.append("    try { pm.variables.set(_k, _v); } catch (eV) {}")
        lines.append("  })();")
    for key in ("ProgramID", "clientId", "secret"):
        val = creds.get(key) or ""
        if not val:
            continue
        lit = JsStringLiteral(val)
        lines.append(f"  try {{ pm.variables.set({JsStringLiteral(key)}, {lit}); }} catch (e1) {{}}")
        lines.append(f"  try {{ pm.collectionVariables.set({JsStringLiteral(key)}, {lit}); }} catch (e2) {{}}")
        lines.append(f"  try {{ pm.environment.set({JsStringLiteral(key)}, {lit}); }} catch (e3) {{}}")
    lines.extend(
        [
            "  // Auth body 占位符强制替换，避免 {{clientId}}/{{secret}} 未解析",
            "  if (pm.request && pm.request.body && pm.request.body.raw) {",
            "    var _raw = String(pm.request.body.raw);",
            "    var _cid = ''; try { _cid = String(pm.variables.get('clientId') || '').trim(); } catch (eC0) {}",
            "    var _sec = ''; try { _sec = String(pm.variables.get('secret') || '').trim(); } catch (eS0) {}",
            "    if (_cid) _raw = _raw.replace(/{{clientId}}/g, _cid);",
            "    if (_sec) _raw = _raw.replace(/{{secret}}/g, _sec);",
            "    // 业务键 {{}} 强制用 variables（数据集优先，防 Environment 旧值）",
            "    var _biz = ["
            + ", ".join(JsStringLiteral(k) for k in DEFAULT_BUSINESS_ENV if k not in ("baseUrl", "x-version"))
            + "];",
            "    for (var _i = 0; _i < _biz.length; _i++) {",
            "      var _bk = _biz[_i];",
            "      var _bv = ''; try { _bv = String(pm.variables.get(_bk) || '').trim(); } catch (eB) {}",
            "      if (_bv) { _raw = _raw.split('{{' + _bk + '}}').join(_bv); }",
            "    }",
            "    pm.request.body.raw = _raw;",
            "  }",
            "  var _pid = ''; try { _pid = String(pm.variables.get('ProgramID') || '').trim(); } catch (eP0) {}",
            "  if (_pid && pm.request && pm.request.headers && typeof pm.request.headers.upsert === 'function') {",
            "    try { pm.request.headers.upsert({ key: 'X-Program-ID', value: _pid }); } catch (ePH) {}",
            "  }",
            "} catch (eSeed) { console.warn('seed runtime env', eSeed); }",
        ]
    )
    return lines


def BuildHelpersJsLines() -> List[str]:
    js = r"""
function isBusinessSuccess(env) {
  if (!env || typeof env !== 'object') return false;
  if (!Object.prototype.hasOwnProperty.call(env, 'code')) return true;
  var c = env.code;
  return c === 0 || c === '0';
}
function fmtJsonBrief(v, maxLen) {
  maxLen = maxLen || 240;
  var s;
  try { s = JSON.stringify(v); } catch (e) { s = String(v); }
  // JSON.stringify(undefined) === undefined，直接 .length 会抛错
  if (s === undefined || s === null) s = String(v);
  if (s.length > maxLen) return s.slice(0, maxLen) + '...(len=' + s.length + ')';
  return s;
}
function assertCheck(checkpoint, expected, actual) {
  var title = checkpoint + ' | 期望=' + fmtJsonBrief(expected) + ' | 实际=' + fmtJsonBrief(actual);
  pm.test(title, function () {
    pm.expect(actual).to.eql(expected);
  });
}
function assertHttp(checkpoint, expectedCode) {
  assertCheck(checkpoint, expectedCode, pm.response.code);
}
function assertInfo(checkpoint, expectedDesc, actualValue) {
  var title = checkpoint + ' | 期望=' + expectedDesc + ' | 实际=' + fmtJsonBrief(actualValue);
  pm.test(title, function () {
    pm.expect(true).to.eql(true);
  });
}
function parseJson() {
  try { return pm.response.json(); } catch (e) { return null; }
}
function getEnv(name) {
  // 优先 variables（Apifox 全量数据/数据集行常注入此处），再 collection。
  // Environment 仅 infra/鉴权/令牌：业务键（券码、金额等）勿再读 Environment，避免旧值盖掉数据集。
  var v = '';
  try { v = String(pm.variables.get(name) || '').trim(); } catch (e0) {}
  if (!v) { try { v = String(pm.collectionVariables.get(name) || '').trim(); } catch (e2) {} }
  if (!v) {
    var _infra = (
      name === 'baseUrl' || name === 'x-version' || name === 'accessToken' ||
      name === 'ProgramID' || name === 'clientId' || name === 'secret'
    );
    if (_infra) {
      try { v = String((pm.environment && pm.environment.get(name)) || '').trim(); } catch (e1) {}
    }
  }
  return v;
}
function setRuntime(name, value) {
  // 订单态等只写 variables/collection，禁止写 Environment（共用 351893；业务键只读数据集）。
  var s = value === null || value === undefined ? '' : String(value);
  try { pm.variables.set(name, s); } catch (eV) {}
  try { pm.collectionVariables.set(name, s); } catch (eC) {}
}
function money2(v) {
  // 金额统一保留两位小数，避免 JS 浮点（如 10-2.63→7.369999…）与接口四舍五入不一致
  if (v === null || v === undefined || v === '') return NaN;
  var n = Number(v);
  if (!isFinite(n)) return NaN;
  return Math.round(n * 100) / 100;
}
function numEq(a, b) {
  if (a === null || a === undefined || b === null || b === undefined || b === '') return false;
  var x = money2(a);
  var y = money2(b);
  if (!isFinite(x) || !isFinite(y)) return false;
  return x === y;
}
function assertNum(checkpoint, expected, actual) {
  var title = checkpoint + ' | 期望=' + fmtJsonBrief(money2(expected)) + ' | 实际=' + fmtJsonBrief(actual);
  pm.test(title, function () {
    pm.expect(numEq(actual, expected), '数值不相等').to.eql(true);
  });
}
function assertBizOk(checkpoint) {
  assertHttp(checkpoint + ': HTTP', 200);
  var j = parseJson() || {};
  var ok = isBusinessSuccess(j);
  var title = checkpoint + ': 业务成功 | 期望=code=0 | 实际=' + fmtJsonBrief({ code: j.code, errCode: j.errCode, msg: j.msg });
  pm.test(title, function () {
    pm.expect(ok, '正向步骤业务失败不可跳过').to.eql(true);
  });
  return j;
}
function emptyOrNullArr(v) {
  return v === null || v === undefined || (Array.isArray(v) && v.length === 0);
}
function assertChargeDetails(label, charge, cfg) {
  assertCheck(label + ': charges[0].type', 'MONTHLY_MEMBERSHIP_FEE', String((charge && charge.type) || ''));
  var details = charge && charge.details;
  assertCheck(label + ': charges[0].details 为数组', true, Array.isArray(details));
  if (!Array.isArray(details) || !details.length) return;
  var row = details[0] || {};
  var expectPax = cfg.expectPaxType || 'CARDHOLDER';
  var expectQty = cfg.expectQuantity !== undefined && cfg.expectQuantity !== '' ? cfg.expectQuantity : 1;
  var expectUnit = cfg.expectUnitPrice;
  assertCheck(label + ': charges[0].details[0].paxType', String(expectPax), String(row.paxType || ''));
  assertNum(label + ': charges[0].details[0].quantity', expectQty, row.quantity);
  if (expectUnit !== undefined && expectUnit !== '') {
    assertNum(label + ': charges[0].details[0].unitPrice', expectUnit, row.unitPrice);
    assertNum(label + ': charges[0].details[0].amount', Number(expectQty) * Number(expectUnit), row.amount);
  }
}
function assertPriceBlock(label, pay, cfg) {
  assertCheck(label + ': payment 为对象', 'object', (!pay || typeof pay !== 'object' || Array.isArray(pay)) ? typeof pay : 'object');
  if (!pay) return;
  if (cfg.expectCurrency) {
    assertCheck(label + ': currency', String(cfg.expectCurrency), String(pay.currency || ''));
  }
  var price = pay.price || {};
  if (cfg.expectOriginal !== undefined && cfg.expectOriginal !== '') {
    assertNum(label + ': originalAmount', cfg.expectOriginal, price.originalAmount);
  }
  if (cfg.expectPayable !== undefined && cfg.expectPayable !== '') {
    assertNum(label + ': payableAmount', cfg.expectPayable, price.payableAmount);
  }
  if (cfg.expectDeduction !== undefined && cfg.expectDeduction !== '') {
    assertNum(label + ': deductionAmount', cfg.expectDeduction, price.deductionAmount);
  }
  var charges = pay.charges;
  assertCheck(label + ': charges 为数组', true, Array.isArray(charges));
  if (Array.isArray(charges) && charges.length) {
    assertChargeDetails(label, charges[0], cfg);
  }
  pm.test(label + ': deductions 为空或[] | 期望=null|[] | 实际=' + fmtJsonBrief(pay.deductions), function () {
    pm.expect(emptyOrNullArr(pay.deductions)).to.eql(true);
  });
}
function assertPendingNoActivation(label, data) {
  var act = data && data.extra && data.extra.activation;
  var ok = act === null || act === undefined || (Array.isArray(act) && act.length === 0) ||
    (typeof act === 'object' && !act.activationCode && !act.redemptionCode && !act.membershipId);
  pm.test(label + ': 待支付无可用激活凭据 | 期望=无凭据 | 实际=' + fmtJsonBrief(act), function () {
    pm.expect(ok).to.eql(true);
  });
}
function assertCreateOrderMeta(label, data) {
  assertCheck(label + ': orderId 非空', true, !!(data && data.orderId && String(data.orderId)));
  pm.test(label + ': orderCreatedDate 存在 | 期望=非空 | 实际=' + fmtJsonBrief(data && data.orderCreatedDate), function () {
    pm.expect(!!(data && data.orderCreatedDate && String(data.orderCreatedDate).trim()), 'orderCreatedDate 缺失').to.eql(true);
  });
  pm.test(label + ': orderCancelledDate 为 null | 期望=null | 实际=' + fmtJsonBrief(data && data.orderCancelledDate), function () {
    pm.expect(data && data.orderCancelledDate === null, '创建时应未取消').to.eql(true);
  });
}
function assertExtraEchoRequest(label, extra, cfg) {
  extra = extra || {};
  if (cfg.expectAppId !== undefined) {
    assertCheck(label + ': extra.appId', cfg.expectAppId, extra.appId);
  }
  if (cfg.expectAutoRenewal !== undefined) {
    assertCheck(label + ': extra.autoRenewal', cfg.expectAutoRenewal, extra.autoRenewal);
  }
  if (cfg.expectCouponCode !== undefined && cfg.expectCouponCode !== '') {
    assertCheck(label + ': extra.couponCode', String(cfg.expectCouponCode), String(extra.couponCode || ''));
  }
  var prof = extra.profile || {};
  if (cfg.expectEmail !== undefined && cfg.expectEmail !== '') {
    assertCheck(label + ': extra.profile.email', String(cfg.expectEmail), String(prof.email || ''));
  }
  if (cfg.expectClientUserId !== undefined && cfg.expectClientUserId !== '') {
    assertCheck(label + ': extra.profile.clientUserId', String(cfg.expectClientUserId), String(prof.clientUserId || ''));
  }
}
"""
    return [ln for ln in js.strip().split("\n")]


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
        "pm.test('Auth: accessToken 已写入运行时', function () {",
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
        "  try { if (pm.iterationData) _pid = String(pm.iterationData.get('ProgramID') || '').trim(); } catch (ePid) {}",
        # 与 P1 种子一致：勾选鉴权行常在 Environment，优先于可能残留的旧 variables
        "  if (!_pid) { try { _pid = String((pm.environment && pm.environment.get('ProgramID')) || '').trim(); } catch (eP2) {} }",
        "  if (!_pid) { try { _pid = String(pm.variables.get('ProgramID') || '').trim(); } catch (eP0) {} }",
        "  if (!_pid) { try { _pid = String(pm.collectionVariables.get('ProgramID') || '').trim(); } catch (eP1) {} }",
        "  if (!_pid) { try { _pid = String((pm.globals && pm.globals.get('ProgramID')) || '').trim(); } catch (eP3) {} }",
        "  if (_pid) {",
        "    try { pm.variables.set('ProgramID', _pid); } catch (ePS) {}",
        "    try { pm.collectionVariables.set('ProgramID', _pid); } catch (ePC) {}",
        "    try { if (pm.environment) pm.environment.set('ProgramID', _pid); } catch (ePE) {}",
        "    try { if (pm.globals && typeof pm.globals.set === 'function') pm.globals.set('ProgramID', _pid); } catch (ePG) {}",
        "    try {",
        "      if (pm.request && pm.request.headers && typeof pm.request.headers.upsert === 'function') {",
        "        pm.request.headers.upsert({ key: 'X-Program-ID', value: _pid });",
        "      }",
        "    } catch (ePH) {}",
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
        "  try {",
        "    var _rawTok = pm.variables.get('accessToken');",
        "    if (_rawTok !== undefined && _rawTok !== null && String(_rawTok).trim() === '') {",
        "      try { pm.variables.unset('accessToken'); } catch (eUn) {}",
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
        "    } catch (eH) {}",
        "  }",
        "} catch (eAll) {}",
        *Lines_EnsureRequestIdHeader(),
    ]


def Lines_UniqueProfilePrerequest(prefix: str) -> List[str]:
    """为每条链路写入独立 UniqueProfile（email / clientUserId）。"""
    return [
        "try {",
        f"  var _ts = String(Date.now());",
        f"  var _email = '{prefix}_' + _ts + '@example.com';",
        f"  var _cuid = '{prefix}_' + _ts;",
        "  try { pm.variables.set('uniqueProfileEmail', _email); } catch (e1) {}",
        "  try { pm.collectionVariables.set('uniqueProfileEmail', _email); } catch (e2) {}",
        "  try { pm.variables.set('uniqueProfileClientUserId', _cuid); } catch (e3) {}",
        "  try { pm.collectionVariables.set('uniqueProfileClientUserId', _cuid); } catch (e4) {}",
        "} catch (eAll) {}",
    ]


def Lines_InjectOrderIdPrerequest(order_var: str) -> List[str]:
    return [
        "try {",
        f"  var _oid = '';",
        f"  try {{ _oid = String(pm.variables.get('{order_var}') || '').trim(); }} catch (e0) {{}}",
        f"  if (!_oid) {{ try {{ _oid = String(pm.collectionVariables.get('{order_var}') || '').trim(); }} catch (e1) {{}} }}",
        f"  if (!_oid) {{ try {{ _oid = String((pm.environment && pm.environment.get('{order_var}')) || '').trim(); }} catch (e2) {{}} }}",
        "  if (_oid && pm.request && pm.request.body && pm.request.body.raw) {",
        "    var raw = String(pm.request.body.raw);",
        f"    raw = raw.replace(/{{{{{order_var}}}}}/g, _oid);",
        "    pm.request.body.raw = raw;",
        "  }",
        "} catch (eAll) {}",
    ]


def Lines_InjectProfilePrerequest() -> List[str]:
    return [
        "try {",
        "  var _email = ''; var _cuid = '';",
        "  try { _email = String(pm.variables.get('uniqueProfileEmail') || '').trim(); } catch (e0) {}",
        "  if (!_email) { try { _email = String(pm.collectionVariables.get('uniqueProfileEmail') || '').trim(); } catch (e1) {} }",
        "  try { _cuid = String(pm.variables.get('uniqueProfileClientUserId') || '').trim(); } catch (e2) {}",
        "  if (!_cuid) { try { _cuid = String(pm.collectionVariables.get('uniqueProfileClientUserId') || '').trim(); } catch (e3) {} }",
        "  if (pm.request && pm.request.body && pm.request.body.raw) {",
        "    var raw = String(pm.request.body.raw);",
        "    if (_email) raw = raw.replace(/{{uniqueProfileEmail}}/g, _email);",
        "    if (_cuid) raw = raw.replace(/{{uniqueProfileClientUserId}}/g, _cuid);",
        "    pm.request.body.raw = raw;",
        "  }",
        "} catch (eAll) {}",
    ]


def AuthJsonHeaders() -> List[JsonObject]:
    return [
        {"key": "X-Program-ID", "value": "{{ProgramID}}"},
        {"key": "x-version", "value": "{{x-version}}"},
        {"key": "X-Request-ID", "value": "{{$guid}}"},
        {"key": "Content-Type", "value": "application/json"},
        {"key": "Accept", "value": "*/*"},
    ]


def BearerJsonHeaders() -> List[JsonObject]:
    # 必须用 {{ProgramID}}：禁止生成时把 .env 写死进头，否则勾选其它鉴权数据集行无效
    return [
        {"key": "X-Program-ID", "value": "{{ProgramID}}"},
        {"key": "x-version", "value": "{{x-version}}"},
        {"key": "X-Request-ID", "value": "{{$guid}}"},
        {"key": "Authorization", "value": "Bearer {{accessToken}}"},
        {"key": "Content-Type", "value": "application/json"},
        {"key": "Accept", "value": "*/*"},
    ]


def PostmanUrl(url_path: str) -> JsonObject:
    # 私有化 CLI 下 Environment 的 {{baseUrl}} 常无法注入；P0 使用字面量基址。
    LoadDotEnv()
    base = (os.environ.get("MP_P0_BASE_URL") or "").strip() or DEFAULT_BUSINESS_ENV.get("baseUrl") or ""
    raw = base + url_path
    path_parts = [part for part in url_path.split("/") if part]
    return {"raw": raw, "host": [base], "path": path_parts}


def PostmanJsonRawBody(raw: str) -> JsonObject:
    return {"mode": "raw", "raw": raw, "options": {"raw": {"language": "json"}}}


def CollectionVariable(key: str, value: str) -> JsonObject:
    return {"key": key, "value": value, "type": "string"}


def PurposeName(purpose: str, step_id: str, method: str, path_hint: str = "") -> str:
    hint = (path_hint or "").strip()
    if hint:
        return f"【{purpose}】| {step_id} | {method} {hint}"
    return f"【{purpose}】| {step_id} | {method}"


def MakeTestEvent(
    *,
    save_token: bool = False,
    extra_lines: Optional[Sequence[str]] = None,
) -> List[JsonObject]:
    lines: List[str] = []
    lines.extend(BuildHelpersJsLines())
    if save_token:
        lines.extend(SaveTokenLines())
    if extra_lines:
        lines.extend(list(extra_lines))
    return [{"listen": "test", "script": {"exec": lines, "type": "text/javascript"}}]


def RequestItem(
    *,
    name: str,
    method: str,
    url_path: str,
    body: Optional[str],
    headers: List[JsonObject],
    description: str,
    save_token: bool = False,
    test_lines: Optional[Sequence[str]] = None,
    prerequest_extra: Optional[Sequence[str]] = None,
) -> JsonObject:
    req: JsonObject = {
        "method": method,
        "header": headers,
        "url": PostmanUrl(url_path),
        "description": description,
    }
    if body is not None:
        req["body"] = PostmanJsonRawBody(body)
    out: JsonObject = {"name": name, "request": req}
    pre_lines = list(Lines_SeedRuntimeEnv()) + list(Lines_EnsureAuthPrerequest())
    if prerequest_extra:
        pre_lines.extend(list(prerequest_extra))
    out["event"] = [
        {"listen": "prerequest", "script": {"exec": pre_lines, "type": "text/javascript"}},
        MakeTestEvent(save_token=save_token, extra_lines=test_lines)[0],
    ]
    return out


def Folder(name: str, items: Sequence[Union[JsonObject, Mapping[str, Any]]], description: str = "") -> JsonObject:
    folder: JsonObject = {"name": name, "item": list(items)}
    if description:
        folder["description"] = description
    return folder


def BodyPreviewCreate(*, with_coupon: bool, auto_renewal: bool) -> str:
    payload: JsonObject = {
        "appId": 1,
        "autoRenewal": auto_renewal,
        "profile": {
            "email": "{{uniqueProfileEmail}}",
            "clientUserId": "{{uniqueProfileClientUserId}}",
        },
    }
    if with_coupon:
        payload["couponCode"] = "{{CouponIntroValid}}"
    return json.dumps(payload, ensure_ascii=False, indent=2)


def Lines_Auth() -> List[str]:
    return [
        "var j = parseJson() || {};",
        "assertHttp('Auth: HTTP', 200);",
        "var d = j.data !== undefined ? j.data : j;",
        "var t = d && (d.accessToken || d.token || d.access_token);",
        "assertCheck('Auth: accessToken 非空', true, !!t);",
    ]


def Lines_PreviewProductB() -> List[str]:
    return [
        "var j = assertBizOk('B-PRE');",
        "var data = j.data || {};",
        "var extra = data.extra || {};",
        "assertExtraEchoRequest('B-PRE', extra, {",
        "  expectAppId: 1,",
        "  expectAutoRenewal: false,",
        "  expectEmail: getEnv('uniqueProfileEmail'),",
        "  expectClientUserId: getEnv('uniqueProfileClientUserId')",
        "});",
        "var pay = data.payment || {};",
        "pm.test('B-PRE: paymentStatus/timeline 为 null | 期望=null | 实际=' + fmtJsonBrief({ ps: pay.paymentStatus, tl: pay.timeline }), function () {",
        "  pm.expect(pay.paymentStatus === null || pay.paymentStatus === undefined).to.eql(true);",
        "  pm.expect(pay.timeline === null || pay.timeline === undefined).to.eql(true);",
        "});",
        "assertPriceBlock('B-PRE', pay, {",
        "  expectCurrency: getEnv('productBCurrency') || 'EUR',",
        "  expectOriginal: getEnv('productBPrice') || '15',",
        "  expectPayable: getEnv('productBPrice') || '15',",
        "  expectDeduction: '0',",
        "  expectPaxType: 'CARDHOLDER',",
        "  expectQuantity: 1,",
        "  expectUnitPrice: getEnv('productBPrice') || '15'",
        "});",
    ]


def Lines_CreateProductB(order_var: str) -> List[str]:
    return [
        "var j = assertBizOk('B-CRT');",
        "var data = j.data || {};",
        "assertCheck('B-CRT: status=9 待支付', 9, data.status);",
        "assertCreateOrderMeta('B-CRT', data);",
        f"setRuntime('{order_var}', data.orderId);",
        "var extra = data.extra || {};",
        "assertCheck('B-CRT: extra.programId', getEnv('productBProgramId'), String(extra.programId || ''));",
        "assertCheck('B-CRT: extra.programName', getEnv('productBProgramName'), String(extra.programName || ''));",
        "assertExtraEchoRequest('B-CRT', extra, {",
        "  expectAppId: 1,",
        "  expectAutoRenewal: false,",
        "  expectEmail: getEnv('uniqueProfileEmail'),",
        "  expectClientUserId: getEnv('uniqueProfileClientUserId')",
        "});",
        "var pay = data.payment || {};",
        "assertCheck('B-CRT: paymentStatus', 'PENDING_PAYMENT', String(pay.paymentStatus || ''));",
        "assertPriceBlock('B-CRT', pay, {",
        "  expectCurrency: getEnv('productBCurrency') || 'EUR',",
        "  expectOriginal: getEnv('productBPrice') || '15',",
        "  expectPayable: getEnv('productBPrice') || '15',",
        "  expectDeduction: '0',",
        "  expectPaxType: 'CARDHOLDER',",
        "  expectQuantity: 1,",
        "  expectUnitPrice: getEnv('productBPrice') || '15'",
        "});",
    ]


def Lines_DetailsPending(label: str, order_var: str, *, program_id_env: str, program_name_env: str, currency_env: str, price_env: str, payable_env: str, deduction_env: str, auto_renewal: bool) -> List[str]:
    # deduction_env 保留调用方兼容；期望一律 money2(original−payable)，与 Preview/Create / A-DET1 手写一致
    _ = deduction_env
    return [
        f"var j = assertBizOk('{label}');",
        "var data = j.data || {};",
        f"var expectOid = getEnv('{order_var}') || pm.variables.get('{order_var}') || pm.collectionVariables.get('{order_var}');",
        f"assertCheck('{label}: orderId', String(expectOid || ''), String(data.orderId || ''));",
        f"assertCheck('{label}: status=9', 9, data.status);",
        "var extra = data.extra || {};",
        f"assertCheck('{label}: extra.programId', getEnv('{program_id_env}'), String(extra.programId || ''));",
        f"assertCheck('{label}: extra.programName', getEnv('{program_name_env}'), String(extra.programName || ''));",
        f"assertCheck('{label}: extra.autoRenewal', {str(auto_renewal).lower()}, extra.autoRenewal);",
        f"assertPendingNoActivation('{label}', data);",
        "var pay = data.payment || {};",
        f"assertCheck('{label}: paymentStatus', 'PENDING_PAYMENT', String(pay.paymentStatus || ''));",
        f"var orig = getEnv('{price_env}');",
        f"var payable = getEnv('{payable_env}');",
        "if (payable === '' || payable === undefined || payable === null) payable = orig;",
        "var deduction = money2(Number(orig) - Number(payable));",
        "assertPriceBlock('" + label + "', pay, {",
        f"  expectCurrency: getEnv('{currency_env}'),",
        "  expectOriginal: orig,",
        "  expectPayable: payable,",
        "  expectDeduction: deduction,",
        "  expectPaxType: 'CARDHOLDER',",
        "  expectQuantity: 1,",
        "  expectUnitPrice: orig",
        "});",
    ]


def Lines_PaymentsH5(label: str, order_var: str, *, allow_zero_payable: bool = False) -> List[str]:
    lines = [
        f"var expectOid = getEnv('{order_var}') || pm.variables.get('{order_var}') || pm.collectionVariables.get('{order_var}');",
        "var j = parseJson() || {};",
        "assertHttp('" + label + ": HTTP', 200);",
    ]
    if allow_zero_payable:
        lines.extend(
            [
                "var payable = Number(getEnv('productAPayableAmount') || '0');",
                "if (payable === 0) {",
                "  var okFail = !isBusinessSuccess(j);",
                "  pm.test('" + label + ": 应付0元不得发起收银台 | 期望=业务失败(如802) | 实际=' + fmtJsonBrief({ code: j.code, errCode: j.errCode, msg: j.msg }), function () {",
                "    pm.expect(okFail, '0元订单不应成功取H5链').to.eql(true);",
                "  });",
                "  return;",
                "}",
            ]
        )
    lines.extend(
        [
            "var ok = isBusinessSuccess(j);",
            "pm.test('" + label + ": 业务成功 | 期望=code=0 | 实际=' + fmtJsonBrief({ code: j.code, errCode: j.errCode, msg: j.msg }), function () {",
            "  pm.expect(ok).to.eql(true);",
            "});",
            "if (!ok) return;",
            "var data = (j.data !== undefined && j.data !== null) ? j.data : j;",
            "assertCheck('" + label + ": orderId', String(expectOid || ''), String(data.orderId || ''));",
            "assertCheck('" + label + ": paymentStatus', 'PENDING_PAYMENT', String(data.paymentStatus || ''));",
            "var action = data.paymentAction || {};",
            "assertCheck('" + label + ": paymentAction.type', 'REDIRECT', String(action.type || ''));",
            "assertCheck('" + label + ": paymentAction.url 非空HTTPS', true, !!(action.url && String(action.url).indexOf('https://') === 0));",
            "assertCheck('" + label + ": validUntil 为数字', 'number', typeof action.validUntil);",
        ]
    )
    return lines


def Lines_PreviewProductA() -> List[str]:
    return [
        "var j = assertBizOk('A-PRE');",
        "var data = j.data || {};",
        "var coupon = data.coupon || {};",
        "assertCheck('A-PRE: coupon.valid', true, coupon.valid === true);",
        "var details = coupon.details || {};",
        "assertCheck('A-PRE: details.couponType=4 INTRODUCTORY_PRICING', 4, details.couponType);",
        "assertCheck('A-PRE: details.description', getEnv('CouponIntroValidName'), String(details.description || ''));",
        "pm.test('A-PRE: details.currency 为 null | 期望=null | 实际=' + fmtJsonBrief(details.currency), function () {",
        "  pm.expect(details.currency === null, 'currency 应为 null').to.eql(true);",
        "});",
        "pm.test('A-PRE: details.discount 为 null | 期望=null | 实际=' + fmtJsonBrief(details.discount), function () {",
        "  pm.expect(details.discount === null, 'discount 应为 null').to.eql(true);",
        "});",
        "var extra = data.extra || {};",
        "assertExtraEchoRequest('A-PRE', extra, {",
        "  expectAppId: 1,",
        "  expectAutoRenewal: true,",
        "  expectCouponCode: getEnv('CouponIntroValid'),",
        "  expectEmail: getEnv('uniqueProfileEmail'),",
        "  expectClientUserId: getEnv('uniqueProfileClientUserId')",
        "});",
        "var pay = data.payment || {};",
        "pm.test('A-PRE: paymentStatus/timeline 为 null | 期望=null | 实际=' + fmtJsonBrief({ ps: pay.paymentStatus, tl: pay.timeline }), function () {",
        "  pm.expect(pay.paymentStatus === null || pay.paymentStatus === undefined).to.eql(true);",
        "  pm.expect(pay.timeline === null || pay.timeline === undefined).to.eql(true);",
        "});",
        "var orig = getEnv('productAPrice') || '10';",
        "var payable = getEnv('productAPayableAmount');",
        "if (payable === '') payable = '0';",
        "var deduction = money2(Number(orig) - Number(payable));",
        "assertPriceBlock('A-PRE', pay, {",
        "  expectCurrency: getEnv('productACurrency') || 'USD',",
        "  expectOriginal: orig,",
        "  expectPayable: payable,",
        "  expectDeduction: deduction,",
        "  expectPaxType: 'CARDHOLDER',",
        "  expectQuantity: 1,",
        "  expectUnitPrice: orig",
        "});",
    ]


def Lines_CreateProductA(order_var: str) -> List[str]:
    return [
        "var j = assertBizOk('A-CRT');",
        "var data = j.data || {};",
        "assertCreateOrderMeta('A-CRT', data);",
        f"setRuntime('{order_var}', data.orderId);",
        "var extra = data.extra || {};",
        "assertCheck('A-CRT: extra.programId', getEnv('productAProgramId'), String(extra.programId || ''));",
        "assertCheck('A-CRT: extra.programName', getEnv('productAProgramName'), String(extra.programName || ''));",
        "assertExtraEchoRequest('A-CRT', extra, {",
        "  expectAppId: 1,",
        "  expectAutoRenewal: true,",
        "  expectCouponCode: getEnv('CouponIntroValid'),",
        "  expectEmail: getEnv('uniqueProfileEmail'),",
        "  expectClientUserId: getEnv('uniqueProfileClientUserId')",
        "});",
        "var orig = getEnv('productAPrice') || '10';",
        "var payable = getEnv('productAPayableAmount');",
        "if (payable === '') payable = '0';",
        "var deduction = money2(Number(orig) - Number(payable));",
        "var pay = data.payment || {};",
        "if (Number(payable) > 0) {",
        "  assertCheck('A-CRT: status=9', 9, data.status);",
        "  assertCheck('A-CRT: paymentStatus', 'PENDING_PAYMENT', String(pay.paymentStatus || ''));",
        "} else {",
        "  assertInfo('A-CRT: 0元订单 status/paymentStatus', '记录实际态', { status: data.status, paymentStatus: pay.paymentStatus });",
        "}",
        "assertPriceBlock('A-CRT', pay, {",
        "  expectCurrency: getEnv('productACurrency') || 'USD',",
        "  expectOriginal: orig,",
        "  expectPayable: payable,",
        "  expectDeduction: deduction,",
        "  expectPaxType: 'CARDHOLDER',",
        "  expectQuantity: 1,",
        "  expectUnitPrice: orig",
        "});",
    ]


def Lines_CancelOrder(label: str, order_var: str) -> List[str]:
    return [
        f"var expectOid = getEnv('{order_var}') || pm.variables.get('{order_var}') || pm.collectionVariables.get('{order_var}');",
        "var j = parseJson() || {};",
        "assertHttp('" + label + ": HTTP', 200);",
        "var ok = isBusinessSuccess(j);",
        "var msg = String(j.msg || '');",
        "var pendingBlocked = msg.indexOf('Order cancellation failed') >= 0;",
        "pm.test('" + label + ": 取消成功或待支付不可取消 | 期望=code=0或已知取消失败文案 | 实际=' + fmtJsonBrief({ code: j.code, errCode: j.errCode, msg: j.msg }), function () {",
        "  pm.expect(ok || pendingBlocked, '取消既未成功也非待支付拦截').to.eql(true);",
        "});",
        "setRuntime('" + label + "_cancelOk', ok ? '1' : '0');",
        "assertInfo('" + label + ": orderId', String(expectOid || ''), { orderId: expectOid, cancelOk: ok });",
    ]


def Lines_DetailsAfterCancel(label: str, order_var: str, cancel_label: str) -> List[str]:
    flag = f"{cancel_label}_cancelOk"
    return [
        f"var j = assertBizOk('{label}');",
        "var data = j.data || {};",
        f"var expectOid = getEnv('{order_var}') || pm.variables.get('{order_var}') || pm.collectionVariables.get('{order_var}');",
        f"assertCheck('{label}: orderId', String(expectOid || ''), String(data.orderId || ''));",
        f"var cancelOk = String(getEnv('{flag}') || pm.variables.get('{flag}') || '') === '1';",
        "if (cancelOk) {",
        f"  assertCheck('{label}: status=3 已取消', 3, data.status);",
        "  assertInfo('" + label + ": paymentStatus/timeline', '取消后快照', { paymentStatus: (data.payment || {}).paymentStatus, timeline: (data.payment || {}).timeline, cancelledDate: data.orderCancelledDate });",
        "} else {",
        "  assertInfo('" + label + ": 取消未成功时订单态', '通常仍为待支付9', { status: data.status, paymentStatus: (data.payment || {}).paymentStatus });",
        "}",
    ]


def BuildCancelAndDetailsAfterItems(
    *,
    cancel_label: str,
    details_label: str,
    order_var: str,
    purpose_cancel: str,
    purpose_details: str,
) -> List[JsonObject]:
    """E2E 尾部：Cancel + 取消后 Details。"""
    return [
        RequestItem(
            name=PurposeName(purpose_cancel, cancel_label, "PATCH", PATH_CANCEL),
            method="PATCH",
            url_path=PATH_CANCEL,
            body=json.dumps({"status": 3, "orderId": "{{" + order_var + "}}"}, ensure_ascii=False, indent=2),
            headers=BearerJsonHeaders(),
            description=f"PATCH /v2/orders 取消；待支付可能被业务拦截（{cancel_label}）。",
            test_lines=Lines_CancelOrder(cancel_label, order_var),
            prerequest_extra=Lines_InjectOrderIdPrerequest(order_var),
        ),
        RequestItem(
            name=PurposeName(purpose_details, details_label, "POST", PATH_DETAILS),
            method="POST",
            url_path=PATH_DETAILS,
            body=json.dumps({"orderId": "{{" + order_var + "}}"}, ensure_ascii=False, indent=2),
            headers=BearerJsonHeaders(),
            description=f"取消后 Details（{details_label}）。",
            test_lines=Lines_DetailsAfterCancel(details_label, order_var, cancel_label),
            prerequest_extra=Lines_InjectOrderIdPrerequest(order_var),
        ),
    ]


def BuildProductBFolder() -> JsonObject:
    order_var = "orderIdProductB"
    announce_pre, announce_test = Lines_AnnounceGroupEnv(
        "商品B-无券-原价EUR",
        [
            "productBProgramId",
            "productBProgramName",
            "productBPrice",
            "productBCurrency",
            "productBDeduction",
            "returnUrl",
        ],
        fixed_notes=[
            "不传 couponCode",
            "autoRenewal=false（脚本写死）",
            "payable 期望 = productBPrice − productBDeduction",
        ],
    )
    folder_desc = FormatGroupEnvGuideText(
        "商品B-无券-原价EUR",
        [
            "productBProgramId",
            "productBProgramName",
            "productBPrice",
            "productBCurrency",
            "productBDeduction",
            "returnUrl",
        ],
        fixed_notes=[
            "不传 couponCode",
            "autoRenewal=false（脚本写死）",
            "payable 期望 = productBPrice − productBDeduction",
        ],
    )
    return Folder(
        "商品B-无券-原价EUR",
        [
            RequestItem(
                name=PurposeName("不传券预览商品B原价", "B-PRE", "POST", PATH_PREVIEW),
                method="POST",
                url_path=PATH_PREVIEW,
                body=BodyPreviewCreate(with_coupon=False, auto_renewal=False),
                headers=BearerJsonHeaders(),
                description="P0 场景1 · Preview：默认商品 B、EUR 原价。跑本步看 Console/断言「填写指南」。",
                test_lines=announce_test + Lines_PreviewProductB(),
                prerequest_extra=announce_pre + Lines_UniqueProfilePrerequest("mp_b"),
            ),
            RequestItem(
                name=PurposeName("不传券创建商品B待支付订单", "B-CRT", "POST", PATH_CREATE),
                method="POST",
                url_path=PATH_CREATE,
                body=BodyPreviewCreate(with_coupon=False, auto_renewal=False),
                headers=BearerJsonHeaders(),
                description="P0 场景1 · Create：保存 orderId。",
                test_lines=Lines_CreateProductB(order_var),
                prerequest_extra=Lines_InjectProfilePrerequest(),
            ),
            RequestItem(
                name=PurposeName("待支付Details形态-商品B", "B-DET1", "POST", PATH_DETAILS),
                method="POST",
                url_path=PATH_DETAILS,
                body=json.dumps({"orderId": "{{" + order_var + "}}"}, ensure_ascii=False, indent=2),
                headers=BearerJsonHeaders(),
                description="P0 场景1 · Details（支付前）。",
                test_lines=Lines_DetailsPending(
                    "B-DET1",
                    order_var,
                    program_id_env="productBProgramId",
                    program_name_env="productBProgramName",
                    currency_env="productBCurrency",
                    price_env="productBPrice",
                    payable_env="productBPrice",
                    deduction_env="productBDeduction",
                    auto_renewal=False,
                ),
                prerequest_extra=Lines_InjectOrderIdPrerequest(order_var),
            ),
            RequestItem(
                name=PurposeName("待支付订单取H5收银台", "B-PAY", "POST", PATH_PAYMENTS),
                method="POST",
                url_path=PATH_PAYMENTS,
                body=json.dumps(
                    {
                        "orderId": "{{" + order_var + "}}",
                        "returnUrl": "{{returnUrl}}",
                        "paymentMethod": "H5_CASHIER",
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                headers=BearerJsonHeaders(),
                description="P0 场景1 · Payments H5。",
                test_lines=Lines_PaymentsH5("B-PAY", order_var, allow_zero_payable=False),
                prerequest_extra=Lines_InjectOrderIdPrerequest(order_var),
            ),
            RequestItem(
                name=PurposeName("取链后Details仍待支付-商品B", "B-DET2", "POST", PATH_DETAILS),
                method="POST",
                url_path=PATH_DETAILS,
                body=json.dumps({"orderId": "{{" + order_var + "}}"}, ensure_ascii=False, indent=2),
                headers=BearerJsonHeaders(),
                description="P0 场景1 · Details（取链后，未实付仍 pending）。",
                test_lines=Lines_DetailsPending(
                    "B-DET2",
                    order_var,
                    program_id_env="productBProgramId",
                    program_name_env="productBProgramName",
                    currency_env="productBCurrency",
                    price_env="productBPrice",
                    payable_env="productBPrice",
                    deduction_env="productBDeduction",
                    auto_renewal=False,
                ),
                prerequest_extra=Lines_InjectOrderIdPrerequest(order_var),
            ),
        ]
        + BuildCancelAndDetailsAfterItems(
            cancel_label="B-CAN",
            details_label="B-DET3",
            order_var=order_var,
            purpose_cancel="取链后取消商品B订单",
            purpose_details="取消后Details-商品B",
        ),
        description=folder_desc,
    )


def BuildProductAFolder() -> JsonObject:
    order_var = "orderIdProductA"
    announce_pre, announce_test = Lines_AnnounceGroupEnv(
        "商品A-传券-订阅引导期USD",
        [
            "CouponIntroValid",
            "CouponIntroValidName",
            "productAProgramId",
            "productAProgramName",
            "productAPrice",
            "productAPayableAmount",
            "productACurrency",
            "returnUrl",
        ],
        fixed_notes=[
            "autoRenewal=true（脚本写死）",
            "deduction 期望 = money2(productAPrice − productAPayableAmount)",
            "应付 0 时 Create status=9，Payments 可业务失败",
        ],
    )
    folder_desc = FormatGroupEnvGuideText(
        "商品A-传券-订阅引导期USD",
        [
            "CouponIntroValid",
            "CouponIntroValidName",
            "productAProgramId",
            "productAProgramName",
            "productAPrice",
            "productAPayableAmount",
            "productACurrency",
            "returnUrl",
        ],
        fixed_notes=[
            "autoRenewal=true（脚本写死）",
            "deduction 期望 = money2(productAPrice − productAPayableAmount)",
            "应付 0 时 Create status=9，Payments 可业务失败",
        ],
    )
    return Folder(
        "商品A-传券-订阅引导期USD",
        [
            RequestItem(
                name=PurposeName("传券预览商品A引导期价", "A-PRE", "POST", PATH_PREVIEW),
                method="POST",
                url_path=PATH_PREVIEW,
                body=BodyPreviewCreate(with_coupon=True, auto_renewal=True),
                headers=BearerJsonHeaders(),
                description="P0 场景2 · Preview：CouponIntroValid + autoRenewal=true。跑本步看 Console/断言「填写指南」。",
                test_lines=announce_test + Lines_PreviewProductA(),
                prerequest_extra=announce_pre + Lines_UniqueProfilePrerequest("mp_a"),
            ),
            RequestItem(
                name=PurposeName("传券创建商品A订单", "A-CRT", "POST", PATH_CREATE),
                method="POST",
                url_path=PATH_CREATE,
                body=BodyPreviewCreate(with_coupon=True, auto_renewal=True),
                headers=BearerJsonHeaders(),
                description="P0 场景2 · Create。",
                test_lines=Lines_CreateProductA(order_var),
                prerequest_extra=Lines_InjectProfilePrerequest(),
            ),
            RequestItem(
                name=PurposeName("Create后Details-商品A", "A-DET1", "POST", PATH_DETAILS),
                method="POST",
                url_path=PATH_DETAILS,
                body=json.dumps({"orderId": "{{" + order_var + "}}"}, ensure_ascii=False, indent=2),
                headers=BearerJsonHeaders(),
                description="P0 场景2 · Details（Create 后）。",
                prerequest_extra=Lines_InjectOrderIdPrerequest(order_var),
                test_lines=[
                    "var j = assertBizOk('A-DET1');",
                    "var data = j.data || {};",
                    "var expectOid = getEnv('orderIdProductA') || pm.variables.get('orderIdProductA') || pm.collectionVariables.get('orderIdProductA');",
                    "assertCheck('A-DET1: orderId', String(expectOid || ''), String(data.orderId || ''));",
                    "var extra = data.extra || {};",
                    "assertCheck('A-DET1: extra.programId', getEnv('productAProgramId'), String(extra.programId || ''));",
                    "assertCheck('A-DET1: extra.programName', getEnv('productAProgramName'), String(extra.programName || ''));",
                    "assertCheck('A-DET1: extra.autoRenewal', true, extra.autoRenewal);",
                    "assertPendingNoActivation('A-DET1', data);",
                    "var orig = getEnv('productAPrice') || '10';",
                    "var payable = getEnv('productAPayableAmount');",
                    "if (payable === '') payable = '0';",
                    "var deduction = money2(Number(orig) - Number(payable));",
                    "assertPriceBlock('A-DET1', data.payment || {}, {",
                    "  expectCurrency: getEnv('productACurrency') || 'USD',",
                    "  expectOriginal: orig,",
                    "  expectPayable: payable,",
                    "  expectDeduction: deduction,",
                    "  expectPaxType: 'CARDHOLDER',",
                    "  expectQuantity: 1,",
                    "  expectUnitPrice: orig",
                    "});",
                ],
            ),
            RequestItem(
                name=PurposeName("商品A发起Payments", "A-PAY", "POST", PATH_PAYMENTS),
                method="POST",
                url_path=PATH_PAYMENTS,
                body=json.dumps(
                    {
                        "orderId": "{{" + order_var + "}}",
                        "returnUrl": "{{returnUrl}}",
                        "paymentMethod": "H5_CASHIER",
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                headers=BearerJsonHeaders(),
                description="P0 场景2 · Payments；应付0元时期望业务失败（不可取收银）。",
                test_lines=Lines_PaymentsH5("A-PAY", order_var, allow_zero_payable=True),
                prerequest_extra=Lines_InjectOrderIdPrerequest(order_var),
            ),
            RequestItem(
                name=PurposeName("Payments后Details-商品A", "A-DET2", "POST", PATH_DETAILS),
                method="POST",
                url_path=PATH_DETAILS,
                body=json.dumps({"orderId": "{{" + order_var + "}}"}, ensure_ascii=False, indent=2),
                headers=BearerJsonHeaders(),
                description="P0 场景2 · Details（Payments 后）。",
                prerequest_extra=Lines_InjectOrderIdPrerequest(order_var),
                test_lines=[
                    "var j = assertBizOk('A-DET2');",
                    "var data = j.data || {};",
                    "var expectOid = getEnv('orderIdProductA') || pm.variables.get('orderIdProductA') || pm.collectionVariables.get('orderIdProductA');",
                    "assertCheck('A-DET2: orderId', String(expectOid || ''), String(data.orderId || ''));",
                    "assertPendingNoActivation('A-DET2', data);",
                    "assertInfo('A-DET2: status/paymentStatus', '记录Payments后态', { status: data.status, paymentStatus: (data.payment || {}).paymentStatus });",
                ],
            ),
        ]
        + BuildCancelAndDetailsAfterItems(
            cancel_label="A-CAN",
            details_label="A-DET3",
            order_var=order_var,
            purpose_cancel="Payments后取消商品A订单",
            purpose_details="取消后Details-商品A",
        ),
        description=folder_desc,
    )


def BuildCollection() -> JsonObject:
    auth_folder = Folder(
        "00 Auth",
        [
            RequestItem(
                name=PurposeName("鉴权获取访问令牌", "Auth", "POST", PATH_AUTH),
                method="POST",
                url_path=PATH_AUTH,
                body=json.dumps(
                    {
                        "clientId": AuthCredentials().get("clientId") or "{{clientId}}",
                        "secret": AuthCredentials().get("secret") or "{{secret}}",
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                headers=[
                    {
                        "key": "X-Program-ID",
                        "value": AuthCredentials().get("ProgramID") or "{{ProgramID}}",
                    },
                    {"key": "x-version", "value": "{{x-version}}"},
                    {"key": "X-Request-ID", "value": "{{$guid}}"},
                    {"key": "Content-Type", "value": "application/json"},
                    {"key": "Accept", "value": "*/*"},
                ],
                description="写入 accessToken；鉴权来自本机 .env 的 MP_P0_*（生成时写入 body）。",
                save_token=True,
                test_lines=Lines_Auth(),
            ),
        ],
        description="先执行以写入 accessToken。",
    )
    return {
        "info": {
            "name": COLLECTION_DISPLAY_NAME,
            "description": BuildScenarioDescription(),
            "schema": POSTMAN_SCHEMA,
        },
        "variable": [
            CollectionVariable("baseUrl", ""),
            CollectionVariable("x-version", ""),
            CollectionVariable("returnUrl", "https://www.ly.com"),
            CollectionVariable("productBDeduction", "0"),
            CollectionVariable("productADeduction", "0"),
        ],
        "item": [auth_folder, BuildProductBFolder(), BuildProductAFolder()],
    }


def Main() -> None:
    out = CollectionPath(OUT_NAME)
    payload = BuildCollection()
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    Main()
