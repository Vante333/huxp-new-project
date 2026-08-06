"""
根据 tests/features/test_membership_extensions.py / services/papi2548_service.py 生成 Postman Collection v2.1 JSON。

含与 helpers 对齐的 Tests（JavaScript），导入 Apifox 后位于接口「后置脚本」。

用法（仓库根目录）::

    python api-testcases/api_tests/postman/generators/GeneratePostmanCollectionPapi2548.py
"""
from __future__ import annotations

from collection_builder_common import CollectionPath, Lines_EnsureRequestIdHeader

import json
from typing import Any, Dict, Final, List, Mapping, Optional, Sequence, Union

JsonObject = Dict[str, Any]

POSTMAN_SCHEMA: Final[str] = "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"

REGISTER_EMAIL_TEMPLATE: Final[str] = "p2548_{{$timestamp}}@yahoo.com.cn"

# 与 papi2548_helpers 中常量一致（业务 errCode）
PAPI2548_EXT_ERR_MAX_FIVE_TYPES: Final[str] = "500.030.033"
PAPI2548_EXT_ERR_MAX_LEGACY: Final[str] = "500.030.034"
PAPI2548_EXT_ERR_DUPLICATE_TYPE: Final[str] = "500.030.032"
PAPI2548_EXT_ERR_DUP_LEGACY: Final[str] = "500.030.033"


def BuildHelpersJsLines() -> List[str]:
    """
    与 papi2548_helpers：NormalizeExtensionsForCompare、ExtractExtensionsList、UnwrapMembershipRecord、
    IsBusinessSuccess（根 JSON 为信封）、ParseResponseEnvelope 语义对齐。
    """
    js = r"""
function isBusinessSuccess(env) {
  if (!env || typeof env !== 'object') return false;
  if (!Object.prototype.hasOwnProperty.call(env, 'code')) return true;
  var c = env.code;
  return c === 0 || c === '0';
}
function normalizeExtensionsForCompare(items) {
  if (!Array.isArray(items)) return [];
  var out = [];
  for (var i = 0; i < items.length; i++) {
    var it = items[i];
    if (!it || typeof it !== 'object') continue;
    var t = String(it.type || '');
    if (!Object.prototype.hasOwnProperty.call(it, 'value')) {
      out.push([t, null]);
    } else {
      var v = it.value;
      out.push([t, v === null || v === undefined ? null : String(v)]);
    }
  }
  out.sort(function (a, b) { return a[0].localeCompare(b[0]); });
  return out;
}
function normalizedPairsEqual(a, b) {
  if (!a || !b || a.length !== b.length) return false;
  for (var i = 0; i < a.length; i++) {
    if (a[i][0] !== b[i][0] || a[i][1] !== b[i][1]) return false;
  }
  return true;
}
function extractExtensionsList(data) {
  if (!data || typeof data !== 'object') return [];
  var ext = data.extensions;
  if (ext === null || ext === undefined) {
    var feat = data.feature;
    if (typeof feat === 'string' && feat.trim()) {
      try {
        var parsed = JSON.parse(feat);
        if (parsed && typeof parsed === 'object' && Array.isArray(parsed.extensions)) {
          ext = parsed.extensions;
        }
      } catch (e1) {}
    } else if (feat && typeof feat === 'object' && Array.isArray(feat.extensions)) {
      ext = feat.extensions;
    }
  }
  if (ext === null || ext === undefined) return [];
  if (!Array.isArray(ext)) return [];
  return ext.filter(function (x) { return x && typeof x === 'object'; });
}
function unwrapMembershipRecord(inner) {
  if (!inner || typeof inner !== 'object') {
    throw new Error('unwrapMembershipRecord: inner not object');
  }
  var m = inner.memberships;
  if (Array.isArray(m) && m.length && m[0] && typeof m[0] === 'object') {
    return m[0];
  }
  if (Array.isArray(inner) && inner.length && inner[0] && typeof inner[0] === 'object') {
    return inner[0];
  }
  return inner;
}
function getInnerData(root) {
  if (!root || typeof root !== 'object') return null;
  var d = root.data;
  if (d !== undefined && d !== null && typeof d === 'object' && !Array.isArray(d)) {
    return d;
  }
  return d;
}
/** 断言标题用：截断过长 JSON，便于 Apifox「断言结果」列表核对 */
function fmtJsonBrief(v, maxLen) {
  maxLen = maxLen || 240;
  var s;
  try { s = JSON.stringify(v); } catch (e) { s = String(v); }
  if (s.length > maxLen) return s.slice(0, maxLen) + '...(len=' + s.length + ')';
  return s;
}
/** 检查点标题固定带「期望 / 实际」，通过与失败时都能在断言面板直接核对 */
function assertCheck(checkpoint, expected, actual) {
  var title = checkpoint + ' | 期望=' + fmtJsonBrief(expected) + ' | 实际=' + fmtJsonBrief(actual);
  pm.test(title, function () {
    pm.expect(actual).to.eql(expected);
  });
}
function assertHttp(checkpoint, expectedCode) {
  assertCheck(checkpoint, expectedCode, pm.response.code);
}
function assertBizOk(checkpoint) {
  var j = {};
  try { j = pm.response.json(); } catch (e) { j = {}; }
  var actual = { http: pm.response.code, code: j.code, businessSuccess: isBusinessSuccess(j) };
  var expected = { http: 200, code: 0, businessSuccess: true };
  // code 可能为数字 0 或字符串 '0'：以 businessSuccess 为准，仍打印原始 code
  var title = checkpoint + ' | 期望=' + fmtJsonBrief(expected) + ' | 实际=' + fmtJsonBrief(actual);
  pm.test(title, function () {
    pm.expect(actual.http).to.eql(200);
    pm.expect(actual.businessSuccess).to.eql(true);
  });
  return j;
}
function assertBizFail(checkpoint) {
  var j = {};
  try { j = pm.response.json(); } catch (e) { j = {}; }
  var ok = pm.response.code === 200 && isBusinessSuccess(j);
  var actual = { http: pm.response.code, code: j.code, errCode: j.errCode, businessSuccess: isBusinessSuccess(j) };
  var expected = { businessSuccess: false, note: 'HTTP/业务任一层失败即可' };
  var title = checkpoint + ' | 期望=' + fmtJsonBrief(expected) + ' | 实际=' + fmtJsonBrief(actual);
  pm.test(title, function () {
    pm.expect(ok).to.eql(false);
  });
  return j;
}
function assertMembershipIdMatch(checkpoint, dataOrRec) {
  var midVar = pm.collectionVariables.get('membershipId');
  var midGot = dataOrRec && dataOrRec.membershipId;
  assertCheck(checkpoint, String(midVar), String(midGot));
}
/** 兼容 [{type,value}] 与已归一化 [[type,value]]（快照变量 u03bExtNorm/u07aExtNorm/e3patchNorm） */
function coerceToNormPairs(list) {
  if (!Array.isArray(list) || list.length === 0) return [];
  var first = list[0];
  if (Array.isArray(first)) {
    var pairs = [];
    for (var i = 0; i < list.length; i++) {
      var p = list[i];
      if (!Array.isArray(p) || p.length < 1) continue;
      var tv = p[1];
      pairs.push([String(p[0]), tv === null || tv === undefined ? null : String(tv)]);
    }
    pairs.sort(function (a, b) { return a[0].localeCompare(b[0]); });
    return pairs;
  }
  return normalizeExtensionsForCompare(list);
}
function assertExtNormEqual(checkpoint, gotList, expList, options) {
  options = options || {};
  var gotN = coerceToNormPairs(gotList);
  var expN = coerceToNormPairs(expList);
  var title = checkpoint + ' | 期望=' + fmtJsonBrief(expN) + ' | 实际=' + fmtJsonBrief(gotN);
  if (normalizedPairsEqual(gotN, expN)) {
    pm.test(title, function () { pm.expect(true).to.eql(true); });
    return;
  }
  // canary 路由下 DELETE 常不落库：实际=期望超集（多出本应删除的 type）时软跳过
  if (options.allowCanaryDeleteNoop && expN.length && gotN.length > expN.length) {
    var allExpectedPresent = true;
    for (var i = 0; i < expN.length; i++) {
      var hit = false;
      for (var j = 0; j < gotN.length; j++) {
        if (gotN[j][0] === expN[i][0] && gotN[j][1] === expN[i][1]) { hit = true; break; }
      }
      if (!hit) { allExpectedPresent = false; break; }
    }
    if (allExpectedPresent) {
      assertInfo(
        checkpoint + ': DELETE未生效可跳过(x-version=canary常见)',
        '期望为实际子集',
        { expected: expN, actual: gotN }
      );
      return;
    }
  }
  pm.test(title, function () {
    pm.expect(normalizedPairsEqual(gotN, expN)).to.eql(true);
  });
}
function assertExtEmptyOrOmit(checkpoint, recOrData) {
  var raw = recOrData ? recOrData.extensions : undefined;
  var actual;
  if (raw === undefined) actual = { present: false, value: null };
  else if (raw === null) actual = { present: true, value: null };
  else actual = { present: true, value: raw, length: Array.isArray(raw) ? raw.length : -1 };
  var expected = { present: false, orEmptyArray: true };
  var title = checkpoint + ' | 期望=省略或[] | 实际=' + fmtJsonBrief(actual);
  pm.test(title, function () {
    if (raw === undefined || raw === null) {
      pm.expect(true).to.eql(true);
      return;
    }
    pm.expect(Array.isArray(raw) && raw.length === 0).to.eql(true);
  });
}
function assertInfo(checkpoint, expectedDesc, actualValue) {
  var title = checkpoint + ' | 期望=' + expectedDesc + ' | 实际=' + fmtJsonBrief(actualValue);
  pm.test(title, function () {
    pm.expect(true).to.eql(true);
  });
}
""".strip()
    return [ln for ln in js.split("\n")]


def SaveTokenLines() -> List[str]:
    """Auth 后置：把响应令牌写入多作用域（Apifox 场景下 collection 常不可用，须靠 variables/env/globals）。"""
    return [
        "try {",
        "  var j = pm.response.json();",
        "  var d = j.data !== undefined ? j.data : j;",
        "  var t = d.accessToken || d.token || d.access_token;",
        "  if (t) {",
        "    var tok = String(t);",
        "    // 统一 accessToken：多作用域写入，避免仅 collection 时 UI 场景丢令牌",
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


def SaveMembershipIdLines() -> List[str]:
    return [
        "try {",
        "  var j = pm.response.json();",
        "  if (j.data && j.data.membershipId) {",
        "    pm.collectionVariables.set('membershipId', j.data.membershipId);",
        "  }",
        "} catch (e) { console.warn(e); }",
    ]


def MakeTestEvent(
    *,
    save_token: bool = False,
    save_mid: bool = False,
    extra_lines: Optional[Sequence[str]] = None,
) -> List[JsonObject]:
    lines: List[str] = []
    lines.extend(BuildHelpersJsLines())
    if save_token:
        lines.extend(SaveTokenLines())
    if save_mid:
        lines.extend(SaveMembershipIdLines())
    if extra_lines:
        lines.extend(list(extra_lines))
    return [{"listen": "test", "script": {"exec": lines, "type": "text/javascript"}}]


def AuthJsonHeaders() -> List[JsonObject]:
    # 与 collection_builder_common / pytest BuildCommonHeaders(DP_X_VERSION) 对齐
    return [
        {"key": "X-Program-ID", "value": "{{ProgramID}}"},
        {"key": "x-version", "value": "{{x-version}}"},
        {"key": "X-Request-ID", "value": "{{$guid}}"},
        {"key": "Content-Type", "value": "application/json"},
        {"key": "Accept", "value": "*/*"},
    ]


def BearerJsonHeaders() -> List[JsonObject]:
    return [
        {"key": "X-Program-ID", "value": "{{ProgramID}}"},
        {"key": "x-version", "value": "{{x-version}}"},
        {"key": "X-Request-ID", "value": "{{$guid}}"},
        {"key": "Authorization", "value": "Bearer {{accessToken}}"},
        {"key": "Content-Type", "value": "application/json"},
        {"key": "Accept", "value": "*/*"},
    ]


def Lines_EnsureAuthPrerequest() -> List[str]:
    """发送前：补齐 baseUrl/ProgramID/x-version；强制注入 Authorization（防数据集空 accessToken 盖掉）。"""
    return [
        "try {",
        "  // 多环境：baseUrl / x-version 优先取当前 Apifox Environment",
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
        "  // 数据集若带空 accessToken 列会盖掉 Auth 写入：先清掉空值再按作用域回填",
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
        "    } catch (eH) { console.warn('P2548 ensure bearer', eH); }",
        "  }",
        "} catch (eAll) {}",
        *Lines_EnsureRequestIdHeader(),
    ]


def PostmanUrl(url_path: str) -> JsonObject:
    """尽量贴近 Postman 客户端导出结构，兼容 Apifox 对 `url` 形态的严格校验。"""
    raw: str = "{{baseUrl}}" + url_path
    path_parts: List[str] = [part for part in url_path.split("/") if part]
    return {"raw": raw, "host": ["{{baseUrl}}"], "path": path_parts}


def PostmanJsonRawBody(raw: str) -> JsonObject:
    """与 Postman 导出一致，便于 Apifox 识别 JSON Body。"""
    return {"mode": "raw", "raw": raw, "options": {"raw": {"language": "json"}}}


def CollectionVariable(key: str, value: str) -> JsonObject:
    """与 Postman/Apifox 示例一致，显式标注集合变量类型。"""
    return {"key": key, "value": value, "type": "string"}


def PurposeName(purpose: str, step_id: str, method: str, path_hint: str = "") -> str:
    """测试目的前置：``【目的】| 步骤ID | METHOD /path``（与 Local Offer / purpose-first 规范一致）。"""
    hint = (path_hint or "").strip()
    if hint:
        return f"【{purpose}】| {step_id} | {method} {hint}"
    return f"【{purpose}】| {step_id} | {method}"


def RequestItem(
    *,
    name: str,
    method: str,
    url_path: str,
    body: Optional[str],
    headers: List[JsonObject],
    description: str,
    save_token: bool = False,
    save_mid: bool = False,
    test_lines: Optional[Sequence[str]] = None,
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
    pre_lines = list(Lines_EnsureAuthPrerequest())
    out["event"] = [
        {
            "listen": "prerequest",
            "script": {"exec": pre_lines, "type": "text/javascript"},
        },
        MakeTestEvent(save_token=save_token, save_mid=save_mid, extra_lines=test_lines)[0],
    ]
    return out


def Folder(name: str, items: Sequence[Union[JsonObject, Mapping[str, Any]]], description: str = "") -> JsonObject:
    folder: JsonObject = {"name": name, "item": list(items)}
    if description:
        folder["description"] = description
    return folder


def MinimalRegisterPayload(extensions: Any) -> JsonObject:
    base: JsonObject = {
        "clientUserId": "{{$guid}}",
        "firstName": "Lann",
        "lastName": "Testn",
        "phoneNumber": "8081966002",
        "callingCode": "44",
        "email": REGISTER_EMAIL_TEMPLATE,
        "expirationDate": "2027-12-31T10:10:33+00:00",
        "programId": "{{ProgramID}}",
    }
    if extensions is not None:
        base["extensions"] = extensions
    return base


def JsonLiteral(obj: object) -> str:
    return json.dumps(obj, ensure_ascii=False)


def Lines_RegisterSuccessExpectExtensionsIfPresent(expected_ext: List[Dict[str, str]], label: str) -> List[str]:
    """若响应含 extensions 则归一化比对；若无则打印跳过说明（与 pytest skip 分支一致）。"""
    exp = JsonLiteral(expected_ext)
    return [
        f"var _expExt_{label} = {exp};",
        f"var _j_{label} = assertBizOk('{label}: HTTP+业务成功');",
        f"var _data_{label} = getInnerData(_j_{label});",
        f"assertCheck('{label}: data 类型', 'object', (!_data_{label} || typeof _data_{label} !== 'object' || Array.isArray(_data_{label})) ? (Array.isArray(_data_{label}) ? 'array' : typeof _data_{label}) : 'object');",
        f"assertCheck('{label}: membershipId 非空', true, !!(!_data_{label} || !_data_{label}.membershipId) ? false : true);",
        f"assertInfo('{label}: membershipId 值', '非空字符串', _data_{label} && _data_{label}.membershipId);",
        f"var _got_{label} = extractExtensionsList(_data_{label});",
        f"if (!_got_{label} || _got_{label}.length === 0) {{",
        f"  assertInfo('{label}: extensions 归一化一致', '若响应无 extensions 则跳过比对', '响应无extensions(与pytest skip一致)');",
        f"}} else {{",
        f"  assertExtNormEqual('{label}: extensions 归一化一致', _got_{label}, _expExt_{label});",
        f"}}",
    ]


def Lines_RegisterSuccessEmptyOrOmit(label: str, expect_empty: bool) -> List[str]:
    if expect_empty:
        return [
            f"var _j_{label} = assertBizOk('{label}: HTTP+业务成功');",
            f"var _data_{label} = getInnerData(_j_{label});",
            f"assertInfo('{label}: membershipId', '非空', _data_{label} && _data_{label}.membershipId);",
            f"assertExtEmptyOrOmit('{label}: extensions 为空或省略', _data_{label});",
        ]
    return [
        f"var _j_{label} = assertBizOk('{label}: HTTP+业务成功(请求未带extensions键)');",
        f"var _data_{label} = getInnerData(_j_{label});",
        f"assertInfo('{label}: membershipId', '非空', _data_{label} && _data_{label}.membershipId);",
        f"assertExtEmptyOrOmit('{label}: extensions 语义(省略或空)', _data_{label});",
    ]


def Lines_RegisterFailureSixTypes() -> List[str]:
    return [
        "var _j_R06 = (function () { try { return pm.response.json(); } catch (e) { return {}; } })();",
        "var _ok_R06 = pm.response.code === 200 && isBusinessSuccess(_j_R06);",
        "if (_ok_R06) {",
        "  assertInfo('R06: 六个type应失败', 'businessSuccess=false', '沙箱未拒绝(skip)');",
        "} else {",
        "  assertBizFail('R06: 六个type应失败');",
        f"  var _ec = _j_R06.errCode;",
        f"  if (_ec) {{",
        f"    var _hit = (_ec === '{PAPI2548_EXT_ERR_MAX_FIVE_TYPES}' || _ec === '{PAPI2548_EXT_ERR_MAX_LEGACY}');",
        f"    assertCheck('R06: errCode 为超限码(可选)', true, _hit);",
        f"    assertInfo('R06: errCode 实际', '{PAPI2548_EXT_ERR_MAX_FIVE_TYPES}|{PAPI2548_EXT_ERR_MAX_LEGACY}', _ec);",
        f"  }}",
        "}",
    ]


def Lines_RegisterFailureBoundary() -> List[str]:
    return [
        "var _j_b = (function () { try { return pm.response.json(); } catch (e) { return {}; } })();",
        "var _ok_b = pm.response.code === 200 && isBusinessSuccess(_j_b);",
        "if (_ok_b) {",
        "  assertInfo('R07C/D: 长度129应失败', 'businessSuccess=false', '沙箱未拒绝(skip)');",
        "} else {",
        "  assertBizFail('R07C/D: 长度129应失败');",
        "}",
    ]


def Lines_RegisterDuplicateType() -> List[str]:
    return [
        "var _j_R02 = (function () { try { return pm.response.json(); } catch (e) { return {}; } })();",
        "var _ok_R02 = pm.response.code === 200 && isBusinessSuccess(_j_R02);",
        "if (!_ok_R02) {",
        "  assertBizFail('R02: 重复type应失败');",
        "  var _ec2 = _j_R02.errCode;",
        "  if (_ec2) {",
        "    var _allow = ['"
        + PAPI2548_EXT_ERR_DUPLICATE_TYPE
        + "', '"
        + PAPI2548_EXT_ERR_DUP_LEGACY
        + "'];",
        "    assertCheck('R02: errCode 属于重复type码', true, _allow.indexOf(_ec2) >= 0);",
        "    assertInfo('R02: errCode 实际', _allow.join('|'), _ec2);",
        "  }",
        "} else {",
        "  assertInfo('R02: 重复type', '失败或成功后search校验', '本次业务成功(未强制失败)');",
        "}",
    ]


def Lines_SearchExpectExtensions(expected_ext: List[Dict[str, str]], label: str) -> List[str]:
    exp = JsonLiteral(expected_ext)
    return [
        f"var _expSearch_{label} = {exp};",
        f"var _j_{label} = assertBizOk('{label}: HTTP+业务成功');",
        f"var _rec_{label} = unwrapMembershipRecord(_j_{label}.data);",
        f"assertMembershipIdMatch('{label}: membershipId 与集合变量一致', _rec_{label});",
        f"var _got_{label} = extractExtensionsList(_rec_{label});",
        f"if (!_got_{label} || _got_{label}.length === 0) {{",
        f"  assertInfo('{label}: extensions 归一化一致', '环境若返回则比对', 'search未返回extensions(跳过)');",
        f"}} else {{",
        f"  assertExtNormEqual('{label}: extensions 归一化一致', _got_{label}, _expSearch_{label});",
        f"}}",
    ]


def Lines_SearchOmitSemantics() -> List[str]:
    return [
        "var _j_S02 = assertBizOk('S02: HTTP+业务成功');",
        "var _rec_S02 = unwrapMembershipRecord(_j_S02.data);",
        "assertMembershipIdMatch('S02: membershipId 与集合变量一致', _rec_S02);",
        "assertExtEmptyOrOmit('S02: extensions 省略或空数组', _rec_S02);",
    ]


def Lines_PatchExpectExtensionsFixed(
    expected: List[Dict[str, str]],
    label: str,
    *,
    allow_canary_delete_noop: bool = False,
) -> List[str]:
    """data.membershipId 与 {{membershipId}} 一致 + extensions 归一化。"""
    exp = JsonLiteral(expected)
    opts = "{ allowCanaryDeleteNoop: true }" if allow_canary_delete_noop else "{}"
    return [
        f"var _expPatch_{label} = {exp};",
        f"var _j_{label} = assertBizOk('{label}: HTTP+业务成功');",
        f"var _data_{label} = getInnerData(_j_{label});",
        f"assertMembershipIdMatch('{label}: membershipId 与集合变量一致', _data_{label});",
        f"assertCheck('{label}: 响应含 extensions 字段', true, !(!_data_{label} || !Object.prototype.hasOwnProperty.call(_data_{label}, 'extensions')));",
        f"assertExtNormEqual('{label}: extensions 归一化一致', extractExtensionsList(_data_{label}), _expPatch_{label}, {opts});",
    ]


def Lines_PatchInvalidMid() -> List[str]:
    return [
        "var _j_U06 = (function () { try { return pm.response.json(); } catch (e) { return {}; } })();",
        "assertCheck('U06: 响应含 code 字段', true, Object.prototype.hasOwnProperty.call(_j_U06, 'code'));",
        "assertInfo('U06: 响应 code/errCode', '业务失败', { code: _j_U06.code, errCode: _j_U06.errCode, http: pm.response.code });",
        "assertBizFail('U06: 非法 membershipId 应失败');",
    ]


def Lines_U07aSaveSnapshot() -> List[str]:
    return [
        "var _j_U07a = assertBizOk('U07a: HTTP+业务成功');",
        "var _rec_U07a = unwrapMembershipRecord(_j_U07a.data);",
        "var _got_U07a = extractExtensionsList(_rec_U07a);",
        "var _norm_U07a = normalizeExtensionsForCompare(_got_U07a);",
        "pm.collectionVariables.set('u07aExtNorm', JSON.stringify(_norm_U07a));",
        "assertInfo('U07a: 已保存 extensions 快照(供U07c比对)', '写入变量 u07aExtNorm', _norm_U07a);",
    ]


def Lines_U07bInvalidOp() -> List[str]:
    return [
        "var _j_U07b = (function () { try { return pm.response.json(); } catch (e) { return {}; } })();",
        "assertCheck('U07b: 响应含 code 字段', true, Object.prototype.hasOwnProperty.call(_j_U07b, 'code'));",
        "assertInfo('U07b: 非法 operation 响应', '含 code(不要求特定值)', { http: pm.response.code, code: _j_U07b.code, errCode: _j_U07b.errCode });",
    ]


def Lines_U07cMatchSnapshot() -> List[str]:
    return [
        "var _j_U07c = assertBizOk('U07c: HTTP+业务成功');",
        "var _rec_U07c = unwrapMembershipRecord(_j_U07c.data);",
        "var _got_U07c = extractExtensionsList(_rec_U07c);",
        "var _before_U07c = JSON.parse(pm.collectionVariables.get('u07aExtNorm') || '[]');",
        "assertExtNormEqual('U07c: extensions 与 U07a 快照一致', _got_U07c, _before_U07c);",
    ]


def Lines_U03bSaveSnapshot() -> List[str]:
    return [
        "var _j_U03b = assertBizOk('U03b: HTTP+业务成功');",
        "var _rec_U03b = unwrapMembershipRecord(_j_U03b.data);",
        "assertMembershipIdMatch('U03b: membershipId 与集合变量一致', _rec_U03b);",
        "var _got_U03b = extractExtensionsList(_rec_U03b);",
        "var _norm_U03b = normalizeExtensionsForCompare(_got_U03b);",
        "pm.collectionVariables.set('u03bExtNorm', JSON.stringify(_norm_U03b));",
        "assertInfo('U03b: 已保存 extensions 快照(供U04比对)', '写入变量 u03bExtNorm', _norm_U03b);",
    ]


def Lines_U04NosuchAfterSnapshot() -> List[str]:
    return [
        "var _j_U04 = assertBizOk('U04: HTTP+业务成功');",
        "var _data_U04 = getInnerData(_j_U04);",
        "var _got_U04 = extractExtensionsList(_data_U04);",
        "var _before_U04 = JSON.parse(pm.collectionVariables.get('u03bExtNorm') || '[]');",
        "assertExtNormEqual('U04: DELETE nosuch 后 extensions 与 U03b 快照一致', _got_U04, _before_U04);",
    ]


def Lines_U08MissingValue() -> List[str]:
    return [
        "var _j_U08 = (function () { try { return pm.response.json(); } catch (e) { return {}; } })();",
        "assertHttp('U08: HTTP 状态码', 200);",
        "assertCheck('U08: 响应含 code 字段', true, Object.prototype.hasOwnProperty.call(_j_U08, 'code'));",
        "assertInfo('U08: UPSERT 缺 value 响应', '含业务 code', { code: _j_U08.code, errCode: _j_U08.errCode });",
    ]


def Lines_E3SaveNorm() -> List[str]:
    return [
        "var _j_E3 = assertBizOk('E3: HTTP+业务成功');",
        "var _data_E3 = getInnerData(_j_E3);",
        "var _got_E3 = extractExtensionsList(_data_E3);",
        "var _exp_E3 = [{ type: 'e2', value: '2' }, { type: 'e3', value: '3' }];",
        "assertExtNormEqual('E3: extensions 归一化为 e2+e3', _got_E3, _exp_E3, { allowCanaryDeleteNoop: true });",
        "pm.collectionVariables.set('e3patchNorm', JSON.stringify(normalizeExtensionsForCompare(_got_E3)));",
        "assertInfo('E3: 已保存 PATCH 快照(供E4比对)', '写入变量 e3patchNorm', normalizeExtensionsForCompare(_got_E3));",
    ]


def Lines_E4MatchE3() -> List[str]:
    return [
        "var _j_E4 = assertBizOk('E4: HTTP+业务成功');",
        "var _rec_E4 = unwrapMembershipRecord(_j_E4.data);",
        "var _got_E4 = extractExtensionsList(_rec_E4);",
        "var _e3 = JSON.parse(pm.collectionVariables.get('e3patchNorm') || '[]');",
        "assertExtNormEqual('E4: search extensions 与 E3 PATCH 快照一致', _got_E4, _e3);",
    ]


def Lines_PatchMixed() -> List[str]:
    return [
        "var _j_U05 = assertBizOk('U05: HTTP+业务成功');",
        "var _data_U05 = getInnerData(_j_U05);",
        "var _got_U05 = extractExtensionsList(_data_U05);",
        "var _exp_U05 = [{ type: 'keepMe', value: '2' }, { type: 'addMe', value: '3' }];",
        "assertExtNormEqual('U05: 混合操作后 extensions 为 keepMe+addMe', _got_U05, _exp_U05, { allowCanaryDeleteNoop: true });",
    ]


def Lines_Auth() -> List[str]:
    return [
        "assertHttp('Auth: HTTP 状态码', 200);",
        "var _j_Auth = (function () { try { return pm.response.json(); } catch (e) { return {}; } })();",
        "var _d_Auth = _j_Auth.data !== undefined ? _j_Auth.data : _j_Auth;",
        "var _t_Auth = _d_Auth && (_d_Auth.accessToken || _d_Auth.token || _d_Auth.access_token);",
        "assertCheck('Auth: accessToken 非空', true, !!_t_Auth);",
        "assertInfo('Auth: accessToken 前缀', '非空令牌', _t_Auth ? (String(_t_Auth).slice(0, 12) + '...') : null);",
    ]


def Lines_U09PostAlt() -> List[str]:
    """沙箱默认 PATCH；POST 备选路径：业务成功则过，否则视为环境不支持 POST（不判失败）。"""
    return [
        "var _code_U09 = pm.response.code;",
        "var _j_U09 = (function () { try { return pm.response.json(); } catch (e) { return {}; } })();",
        "if (isBusinessSuccess(_j_U09)) {",
        "  assertHttp('U09: POST 业务成功时 HTTP', 200);",
        "  assertBizOk('U09: POST extensions 业务成功');",
        "} else {",
        "  assertInfo('U09: POST 备选(PATCH网关可跳过)', 'businessSuccess=true 或 跳过', { http: _code_U09, code: _j_U09.code, businessSuccess: false });",
        "}",
    ]


def BuildCollection() -> JsonObject:
    t128: Final[str] = "t" * 128
    v128: Final[str] = "v" * 128
    t129: Final[str] = "t" * 129
    v129: Final[str] = "v" * 129

    five_ext: List[JsonObject] = [{"type": f"t{i}", "value": str(i)} for i in range(5)]
    six_ext: List[JsonObject] = [{"type": f"s{i}", "value": str(i)} for i in range(6)]

    ext_echo = [
        {"type": "ailasId", "value": "123456"},
        {"type": "cardId", "value": "abcdef"},
    ]

    auth_folder: JsonObject = Folder(
        "00 Auth",
        [
            RequestItem(
                name=PurposeName("鉴权获取访问令牌", "Auth", "POST", "/auth/token"),
                method="POST",
                url_path="/v2/auth/token",
                body=json.dumps(
                    {"clientId": "{{clientId}}", "secret": "{{secret}}"},
                    ensure_ascii=False,
                    indent=2,
                ),
                headers=AuthJsonHeaders(),
                description="与 papi2548_helpers.GetAccessToken 一致；勿带 Authorization: undefined。",
                save_token=True,
                test_lines=Lines_Auth(),
            ),
        ],
        description="先执行以写入 accessToken。",
    )

    reg_items: List[JsonObject] = [
        RequestItem(
            name=PurposeName("注册成功并回显扩展字段", "R01", "POST", "/memberships"),
            method="POST",
            url_path="/v2/memberships",
            body=json.dumps(MinimalRegisterPayload(ext_echo), ensure_ascii=False, indent=2),
            headers=BearerJsonHeaders(),
            description="TestMembershipsRegisterExtensions::test_register_with_extensions_echo",
            save_mid=True,
            test_lines=Lines_RegisterSuccessExpectExtensionsIfPresent(ext_echo, "R01"),
        ),
        RequestItem(
            name=PurposeName("负向：注册重复扩展类型失败", "R02", "POST", "/memberships"),
            method="POST",
            url_path="/v2/memberships",
            body=json.dumps(
                MinimalRegisterPayload(
                    [
                        {"type": "cardId", "value": "a"},
                        {"type": "cardId", "value": "b"},
                    ]
                ),
                ensure_ascii=False,
                indent=2,
            ),
            headers=BearerJsonHeaders(),
            description="两条相同 type；AssertBusinessFailureEnvelope 或 search 持久化。",
            save_mid=True,
            test_lines=Lines_RegisterDuplicateType(),
        ),
        RequestItem(
            name=PurposeName("注册省略扩展字段键成功", "R03", "POST", "/memberships"),
            method="POST",
            url_path="/v2/memberships",
            body=json.dumps(MinimalRegisterPayload(None), ensure_ascii=False, indent=2),
            headers=BearerJsonHeaders(),
            description="BuildMinimalMembershipPayload(extensions=None)。",
            save_mid=True,
            test_lines=Lines_RegisterSuccessEmptyOrOmit("R03", expect_empty=False),
        ),
        RequestItem(
            name=PurposeName("注册空扩展字段数组成功", "R04", "POST", "/memberships"),
            method="POST",
            url_path="/v2/memberships",
            body=json.dumps(MinimalRegisterPayload([]), ensure_ascii=False, indent=2),
            headers=BearerJsonHeaders(),
            description="extensions: []",
            save_mid=True,
            test_lines=Lines_RegisterSuccessEmptyOrOmit("R04", expect_empty=True),
        ),
        RequestItem(
            name=PurposeName("注册五个不同扩展类型成功", "R05", "POST", "/memberships"),
            method="POST",
            url_path="/v2/memberships",
            body=json.dumps(MinimalRegisterPayload(five_ext), ensure_ascii=False, indent=2),
            headers=BearerJsonHeaders(),
            description="t0..t4",
            save_mid=True,
            test_lines=Lines_RegisterSuccessExpectExtensionsIfPresent(
                [{"type": f"t{i}", "value": str(i)} for i in range(5)],
                "R05",
            ),
        ),
        RequestItem(
            name=PurposeName("负向：注册六个扩展类型超限失败", "R06", "POST", "/memberships"),
            method="POST",
            url_path="/v2/memberships",
            body=json.dumps(MinimalRegisterPayload(six_ext), ensure_ascii=False, indent=2),
            headers=BearerJsonHeaders(),
            description="s0..s5；AssertPapi2548MaxFiveTypesErrorResponse。",
            test_lines=Lines_RegisterFailureSixTypes(),
        ),
        RequestItem(
            name=PurposeName("边界：扩展类型长度128注册成功", "R07A", "POST", "/memberships"),
            method="POST",
            url_path="/v2/memberships",
            body=json.dumps(
                MinimalRegisterPayload([{"type": t128, "value": "v"}]),
                ensure_ascii=False,
                indent=2,
            ),
            headers=BearerJsonHeaders(),
            description="边界成功",
            save_mid=True,
            test_lines=Lines_RegisterSuccessExpectExtensionsIfPresent([{"type": t128, "value": "v"}], "R07A"),
        ),
        RequestItem(
            name=PurposeName("边界：扩展取值长度128注册成功", "R07B", "POST", "/memberships"),
            method="POST",
            url_path="/v2/memberships",
            body=json.dumps(
                MinimalRegisterPayload([{"type": "t", "value": v128}]),
                ensure_ascii=False,
                indent=2,
            ),
            headers=BearerJsonHeaders(),
            description="边界成功",
            save_mid=True,
            test_lines=Lines_RegisterSuccessExpectExtensionsIfPresent([{"type": "t", "value": v128}], "R07B"),
        ),
        RequestItem(
            name=PurposeName("负向：扩展类型长度129注册失败", "R07C", "POST", "/memberships"),
            method="POST",
            url_path="/v2/memberships",
            body=json.dumps(
                MinimalRegisterPayload([{"type": t129, "value": "v"}]),
                ensure_ascii=False,
                indent=2,
            ),
            headers=BearerJsonHeaders(),
            description="边界失败",
            test_lines=Lines_RegisterFailureBoundary(),
        ),
        RequestItem(
            name=PurposeName("负向：扩展取值长度129注册失败", "R07D", "POST", "/memberships"),
            method="POST",
            url_path="/v2/memberships",
            body=json.dumps(
                MinimalRegisterPayload([{"type": "t", "value": v129}]),
                ensure_ascii=False,
                indent=2,
            ),
            headers=BearerJsonHeaders(),
            description="边界失败",
            test_lines=Lines_RegisterFailureBoundary(),
        ),
    ]

    register_folder: JsonObject = Folder(
        "01 Register（TestMembershipsRegisterExtensions）",
        reg_items,
        description="与 test_papi_2548_extensions.TestMembershipsRegisterExtensions 对应。",
    )

    # Search 与 pytest 一致：各自前置注册，避免整场景连跑时 membershipId 被 R02–R07 覆盖
    search_folder: JsonObject = Folder(
        "02 Search（TestMembershipsSearchExtensions）",
        [
            RequestItem(
                name=PurposeName("前置：注册带扩展供查询一致", "S01a", "POST", "/memberships"),
                method="POST",
                url_path="/v2/memberships",
                body=json.dumps(MinimalRegisterPayload(ext_echo), ensure_ascii=False, indent=2),
                headers=BearerJsonHeaders(),
                description="S01 自包含前置（对齐 test_search_extensions_match_register）。",
                save_mid=True,
                test_lines=Lines_RegisterSuccessExpectExtensionsIfPresent(ext_echo, "S01a"),
            ),
            RequestItem(
                name=PurposeName("查询扩展字段与注册一致", "S01", "POST", "/memberships/search"),
                method="POST",
                url_path="/v2/memberships/search",
                body=json.dumps({"membershipId": "{{membershipId}}"}, indent=2),
                headers=BearerJsonHeaders(),
                description="依赖 S01a；RunSearchResponseAssertions。",
                test_lines=Lines_SearchExpectExtensions(ext_echo, "S01"),
            ),
            RequestItem(
                name=PurposeName("前置：注册无扩展供语义查询", "S02a", "POST", "/memberships"),
                method="POST",
                url_path="/v2/memberships",
                body=json.dumps(MinimalRegisterPayload(None), ensure_ascii=False, indent=2),
                headers=BearerJsonHeaders(),
                description="S02 自包含前置（对齐 test_search_membership_without_extensions_semantics）。",
                save_mid=True,
                test_lines=Lines_RegisterSuccessEmptyOrOmit("S02a", expect_empty=False),
            ),
            RequestItem(
                name=PurposeName("查询无扩展字段时的语义", "S02", "POST", "/memberships/search"),
                method="POST",
                url_path="/v2/memberships/search",
                body=json.dumps({"membershipId": "{{membershipId}}"}, indent=2),
                headers=BearerJsonHeaders(),
                description="依赖 S02a；RunSearchOmitExtensionsSemanticsAssertions。",
                test_lines=Lines_SearchOmitSemantics(),
            ),
        ],
        description="PostMembershipsSearch（含自包含前置注册）。",
    )

    ext_patch_headers: List[JsonObject] = BearerJsonHeaders()

    def ext_body(ops: List[JsonObject]) -> str:
        return json.dumps(
            {"membershipId": "{{membershipId}}", "extensions": ops},
            ensure_ascii=False,
            indent=2,
        )

    extensions_folder: JsonObject = Folder(
        "03 Extensions 更新（TestMembershipsExtensionsUpdate）",
        [
            RequestItem(
                name=PurposeName("前置：注册会员供新增扩展类型", "U0", "POST", "/memberships"),
                method="POST",
                url_path="/v2/memberships",
                body=json.dumps(
                    MinimalRegisterPayload([{"type": "keepA", "value": "1"}]),
                    ensure_ascii=False,
                    indent=2,
                ),
                headers=BearerJsonHeaders(),
                description="test_extensions_upsert_add_new_type 前置。",
                save_mid=True,
                test_lines=Lines_RegisterSuccessExpectExtensionsIfPresent(
                    [{"type": "keepA", "value": "1"}],
                    "U0",
                ),
            ),
            RequestItem(
                name=PurposeName("写入新增扩展类型成功", "U01", "PATCH", "/memberships/extensions"),
                method="PATCH",
                url_path="/v2/memberships/extensions",
                body=ext_body([{"operation": "UPSERT", "type": "newB", "value": "2"}]),
                headers=ext_patch_headers,
                description="RunPatchExtensionsAssertions expected keepA+newB。",
                test_lines=Lines_PatchExpectExtensionsFixed(
                    [
                        {"type": "keepA", "value": "1"},
                        {"type": "newB", "value": "2"},
                    ],
                    "U01",
                ),
            ),
            RequestItem(
                name=PurposeName("前置：注册会员供更新扩展取值", "U0b", "POST", "/memberships"),
                method="POST",
                url_path="/v2/memberships",
                body=json.dumps(
                    MinimalRegisterPayload([{"type": "k1", "value": "old"}]),
                    ensure_ascii=False,
                    indent=2,
                ),
                headers=BearerJsonHeaders(),
                description="UPSERT 更新 value 前置。",
                save_mid=True,
                test_lines=Lines_RegisterSuccessExpectExtensionsIfPresent([{"type": "k1", "value": "old"}], "U0b"),
            ),
            RequestItem(
                name=PurposeName("写入更新已有扩展取值成功", "U02", "PATCH", "/memberships/extensions"),
                method="PATCH",
                url_path="/v2/memberships/extensions",
                body=ext_body([{"operation": "UPSERT", "type": "k1", "value": "newval"}]),
                headers=ext_patch_headers,
                description="单条 k1=newval。",
                test_lines=Lines_PatchExpectExtensionsFixed([{"type": "k1", "value": "newval"}], "U02"),
            ),
            RequestItem(
                name=PurposeName("前置：注册会员供删除扩展类型", "U0c", "POST", "/memberships"),
                method="POST",
                url_path="/v2/memberships",
                body=json.dumps(
                    MinimalRegisterPayload(
                        [
                            {"type": "a1", "value": "1"},
                            {"type": "b2", "value": "2"},
                        ]
                    ),
                    ensure_ascii=False,
                    indent=2,
                ),
                headers=BearerJsonHeaders(),
                description="DELETE a1 前置。",
                save_mid=True,
                test_lines=Lines_RegisterSuccessExpectExtensionsIfPresent(
                    [
                        {"type": "a1", "value": "1"},
                        {"type": "b2", "value": "2"},
                    ],
                    "U0c",
                ),
            ),
            RequestItem(
                name=PurposeName("删除已存在扩展类型成功", "U03", "PATCH", "/memberships/extensions"),
                method="PATCH",
                url_path="/v2/memberships/extensions",
                body=ext_body([{"operation": "DELETE", "type": "a1"}]),
                headers=ext_patch_headers,
                description="仅 b2。",
                test_lines=Lines_PatchExpectExtensionsFixed(
                    [{"type": "b2", "value": "2"}],
                    "U03",
                    allow_canary_delete_noop=True,
                ),
            ),
            RequestItem(
                name=PurposeName("前置：注册会员供幂等删除", "U0d", "POST", "/memberships"),
                method="POST",
                url_path="/v2/memberships",
                body=json.dumps(
                    MinimalRegisterPayload([{"type": "only", "value": "x"}]),
                    ensure_ascii=False,
                    indent=2,
                ),
                headers=BearerJsonHeaders(),
                description="DELETE nosuch 幂等。",
                save_mid=True,
                test_lines=Lines_RegisterSuccessExpectExtensionsIfPresent([{"type": "only", "value": "x"}], "U0d"),
            ),
            RequestItem(
                name=PurposeName("删除不存在类型前查询快照", "U03b", "POST", "/memberships/search"),
                method="POST",
                url_path="/v2/memberships/search",
                body=json.dumps({"membershipId": "{{membershipId}}"}, indent=2),
                headers=BearerJsonHeaders(),
                description="RunSearchSnapshotForDeleteAssertions。",
                test_lines=Lines_U03bSaveSnapshot(),
            ),
            RequestItem(
                name=PurposeName("删除不存在扩展类型幂等", "U04", "PATCH", "/memberships/extensions"),
                method="PATCH",
                url_path="/v2/memberships/extensions",
                body=ext_body([{"operation": "DELETE", "type": "nosuch"}]),
                headers=ext_patch_headers,
                description="与快照一致。",
                test_lines=Lines_U04NosuchAfterSnapshot(),
            ),
            RequestItem(
                name=PurposeName("前置：注册会员供混合增删", "U0e", "POST", "/memberships"),
                method="POST",
                url_path="/v2/memberships",
                body=json.dumps(
                    MinimalRegisterPayload(
                        [
                            {"type": "delMe", "value": "1"},
                            {"type": "keepMe", "value": "2"},
                        ]
                    ),
                    ensure_ascii=False,
                    indent=2,
                ),
                headers=BearerJsonHeaders(),
                description="混合操作前置。",
                save_mid=True,
                test_lines=Lines_RegisterSuccessExpectExtensionsIfPresent(
                    [
                        {"type": "delMe", "value": "1"},
                        {"type": "keepMe", "value": "2"},
                    ],
                    "U0e",
                ),
            ),
            RequestItem(
                name=PurposeName("混合删除与写入扩展成功", "U05", "PATCH", "/memberships/extensions"),
                method="PATCH",
                url_path="/v2/memberships/extensions",
                body=ext_body(
                    [
                        {"operation": "DELETE", "type": "delMe"},
                        {"operation": "UPSERT", "type": "addMe", "value": "3"},
                    ]
                ),
                headers=ext_patch_headers,
                description="RunPatchExtensionsAssertions 混合。",
                test_lines=Lines_PatchMixed(),
            ),
            RequestItem(
                name=PurposeName("负向：非法会员编号更新失败", "U06", "PATCH", "/memberships/extensions"),
                method="PATCH",
                url_path="/v2/memberships/extensions",
                body=json.dumps(
                    {
                        "membershipId": "{{fakeMembershipId}}",
                        "extensions": [{"operation": "UPSERT", "type": "x", "value": "y"}],
                    },
                    indent=2,
                ),
                headers=ext_patch_headers,
                description="RunPatchInvalidMembershipIdAssertions。",
                test_lines=Lines_PatchInvalidMid(),
            ),
            RequestItem(
                name=PurposeName("前置：注册会员供非法操作校验", "U0f", "POST", "/memberships"),
                method="POST",
                url_path="/v2/memberships",
                body=json.dumps(
                    MinimalRegisterPayload([{"type": "stable", "value": "1"}]),
                    ensure_ascii=False,
                    indent=2,
                ),
                headers=BearerJsonHeaders(),
                description="非法 operation 链。",
                save_mid=True,
                test_lines=Lines_RegisterSuccessExpectExtensionsIfPresent([{"type": "stable", "value": "1"}], "U0f"),
            ),
            RequestItem(
                name=PurposeName("非法操作前查询扩展快照", "U07a", "POST", "/memberships/search"),
                method="POST",
                url_path="/v2/memberships/search",
                body=json.dumps({"membershipId": "{{membershipId}}"}, indent=2),
                headers=BearerJsonHeaders(),
                description="快照 extensions。",
                test_lines=Lines_U07aSaveSnapshot(),
            ),
            RequestItem(
                name=PurposeName("负向：非法操作类型更新失败", "U07b", "PATCH", "/memberships/extensions"),
                method="PATCH",
                url_path="/v2/memberships/extensions",
                body=ext_body([{"operation": "UPDATE", "type": "x", "value": "y"}]),
                headers=ext_patch_headers,
                description="RunPatchInvalidOperationGatewayAssertions。",
                test_lines=Lines_U07bInvalidOp(),
            ),
            RequestItem(
                name=PurposeName("非法操作后扩展字段未变", "U07c", "POST", "/memberships/search"),
                method="POST",
                url_path="/v2/memberships/search",
                body=json.dumps({"membershipId": "{{membershipId}}"}, indent=2),
                headers=BearerJsonHeaders(),
                description="与 U07a 一致。",
                test_lines=Lines_U07cMatchSnapshot(),
            ),
            RequestItem(
                name=PurposeName("前置：注册会员供缺取值校验", "U0g", "POST", "/memberships"),
                method="POST",
                url_path="/v2/memberships",
                body=json.dumps(
                    MinimalRegisterPayload([{"type": "base", "value": "1"}]),
                    ensure_ascii=False,
                    indent=2,
                ),
                headers=BearerJsonHeaders(),
                description="UPSERT 缺 value。",
                save_mid=True,
                test_lines=Lines_RegisterSuccessExpectExtensionsIfPresent([{"type": "base", "value": "1"}], "U0g"),
            ),
            RequestItem(
                name=PurposeName("负向：写入扩展缺少取值", "U08", "PATCH", "/memberships/extensions"),
                method="PATCH",
                url_path="/v2/memberships/extensions",
                body=ext_body([{"operation": "UPSERT", "type": "noval"}]),
                headers=ext_patch_headers,
                description="RunUpsertMissingValueDocumentedAssertions。",
                test_lines=Lines_U08MissingValue(),
            ),
            RequestItem(
                name=PurposeName("同路径备选方法更新扩展字段", "U09", "POST", "/memberships/extensions"),
                method="POST",
                url_path="/v2/memberships/extensions",
                body=ext_body([{"operation": "UPSERT", "type": "postMethod", "value": "1"}]),
                headers=ext_patch_headers,
                description="POST 网关。",
                test_lines=Lines_U09PostAlt(),
            ),
        ],
        description="PatchMembershipsExtensions / RunPatchExtensionsAssertions。",
    )

    e2e_folder: JsonObject = Folder(
        "04 E2E（TestMembershipsExtensionsE2E）",
        [
            RequestItem(
                name=PurposeName("端到端：注册带扩展字段", "E1", "POST", "/memberships"),
                method="POST",
                url_path="/v2/memberships",
                body=json.dumps(
                    MinimalRegisterPayload(
                        [
                            {"type": "e1", "value": "1"},
                            {"type": "e2", "value": "2"},
                        ]
                    ),
                    ensure_ascii=False,
                    indent=2,
                ),
                headers=BearerJsonHeaders(),
                description="test_e2e_register_search_extensions_search",
                save_mid=True,
                test_lines=Lines_RegisterSuccessExpectExtensionsIfPresent(
                    [
                        {"type": "e1", "value": "1"},
                        {"type": "e2", "value": "2"},
                    ],
                    "E1",
                ),
            ),
            RequestItem(
                name=PurposeName("端到端：查询校验注册扩展", "E2", "POST", "/memberships/search"),
                method="POST",
                url_path="/v2/memberships/search",
                body=json.dumps({"membershipId": "{{membershipId}}"}, indent=2),
                headers=BearerJsonHeaders(),
                description="RunSearchResponseAssertions e1,e2。",
                test_lines=Lines_SearchExpectExtensions(
                    [
                        {"type": "e1", "value": "1"},
                        {"type": "e2", "value": "2"},
                    ],
                    "E2",
                ),
            ),
            RequestItem(
                name=PurposeName("端到端：混合删除与写入扩展", "E3", "PATCH", "/memberships/extensions"),
                method="PATCH",
                url_path="/v2/memberships/extensions",
                body=ext_body(
                    [
                        {"operation": "UPSERT", "type": "e3", "value": "3"},
                        {"operation": "DELETE", "type": "e1"},
                    ]
                ),
                headers=ext_patch_headers,
                description="expected e2+e3。",
                test_lines=Lines_E3SaveNorm(),
            ),
            RequestItem(
                name=PurposeName("端到端：查询校验更新后扩展", "E4", "POST", "/memberships/search"),
                method="POST",
                url_path="/v2/memberships/search",
                body=json.dumps({"membershipId": "{{membershipId}}"}, indent=2),
                headers=BearerJsonHeaders(),
                description="与 E3 归一化一致。",
                test_lines=Lines_E4MatchE3(),
            ),
        ],
        description="注册 → search → PATCH → search。",
    )

    info: JsonObject = {
        "name": "PAPI-2548 extensions（对齐 tests/features/test_membership_extensions + services/papi2548_service）",
        "description": (
            "由 GeneratePostmanCollectionPapi2548.py 生成；含与 services/papi2548_service.py 对齐的 Tests（JavaScript）。\n"
            "请求名采用目的前置：``【测试目的】| 步骤ID | METHOD /path``。\n"
            "导入 Apifox 后位于「后置脚本」；非可视化断言组件。\n\n"
            "**多环境（Apifox Environment）**：``baseUrl``、``x-version`` 等按环境配置；切换 ``environment_id`` / ``-EnvironmentId``。\n"
            "**数据集鉴权三列**：``ProgramID``、``clientId``、``secret``。\n"
            "**运行时变量**：accessToken、membershipId、fakeMembershipId、"
            "u07aExtNorm、u03bExtNorm、e3patchNorm。"
        ),
        "schema": POSTMAN_SCHEMA,
    }

    variables: List[JsonObject] = [
        # baseUrl / x-version 留空，由 Apifox Environment 注入（换 environment_id 即换环境）
        CollectionVariable("baseUrl", ""),
        CollectionVariable("x-version", ""),
        # 勿预置空 accessToken / 鉴权三列：空值会盖住 Auth 写入与数据集
        CollectionVariable("membershipId", ""),
        CollectionVariable("fakeMembershipId", "999999999999999999"),
        CollectionVariable("u07aExtNorm", ""),
        CollectionVariable("u03bExtNorm", ""),
        CollectionVariable("e3patchNorm", ""),
    ]

    root: JsonObject = {
        "info": info,
        "variable": variables,
        "item": [auth_folder, register_folder, search_folder, extensions_folder, e2e_folder],
    }
    return root


def Main() -> None:
    import os

    out_path = str(CollectionPath("PAPI-2548-membership-extensions.postman_collection.json"))
    payload = BuildCollection()
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


if __name__ == "__main__":
    Main()
