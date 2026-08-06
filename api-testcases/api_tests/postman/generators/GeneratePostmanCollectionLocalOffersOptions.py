"""
根据 tests/features/test_local_offers_options.py / services/local_offers_options_service.py
生成 Postman Collection v2.1 JSON。

含与 helpers 对齐的 Tests（JavaScript）；Apifox CLI Repo-first 真相源。
鉴权三列统一 ``ProgramID`` / ``clientId`` / ``secret``（对齐 ``GetAccessToken`` /
``DP_PROGRAM_ID`` / ``DP_CLIENT_ID`` / ``DP_CLIENT_SECRET``）。
正向资源 ID / option ID **只从 Apifox Environment 读取** ``resourceId`` / ``optionId``
（对齐 ``DP_LOCAL_OFFER_RESOURCE_ID``；与 Local Offer ePass 同名）。路径使用 ``{{resourceId}}`` /
``{{optionId}}``，**不写死**具体网点值；前置脚本从环境注入并改写未解析占位符。

用法（仓库根目录）::

    python api-testcases/api_tests/postman/generators/GeneratePostmanCollectionLocalOffersOptions.py
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Final, List, Mapping, Optional, Sequence, Union

from collection_builder_common import CollectionPath, Lines_EnsureRequestIdHeader

JsonObject = Dict[str, Any]

POSTMAN_SCHEMA: Final[str] = "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
OUT_NAME: Final[str] = "LocalOffers-Options-P1.postman_collection.json"
COLLECTION_DISPLAY_NAME: Final[str] = "Local Offers options · P1（只读查询）"
OPTIONS_PATH_HINT: Final[str] = "/resources/localOffers/{resourceId}/options"
OPTION_DETAIL_PATH_HINT: Final[str] = "/resources/localOffers/{resourceId}/options/{optionId}"
APIFOX_NEGATIVE_STEP_HINT: Final[str] = (
    "【Apifox】负向步骤可能 HTTP 4xx：请以「断言结果」后置脚本为准；"
    "若平台「校验响应」仍要求 200，请在项目/步骤中关闭 HTTP 状态码校验。"
)


def BuildLoOptionsJsHelpersLines() -> List[str]:
    """与 local_offers_options_service 断言语义对齐的 Postman Tests 公共脚本。"""
    js = r"""
function loIsBusinessSuccess(env) {
  if (!env || typeof env !== 'object') return false;
  if (!Object.prototype.hasOwnProperty.call(env, 'code')) return true;
  var c = env.code;
  return c === 0 || c === '0';
}
function fmtJsonBrief(v, maxLen) {
  maxLen = maxLen || 240;
  var s;
  try { s = JSON.stringify(v); } catch (e) { s = String(v); }
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
function loParseJson() {
  try { return pm.response.json(); } catch (e) { return null; }
}
function loAssertEnvelopeCode(checkpoint, body) {
  var code = body && body.code;
  var title = checkpoint + ' | 期望=0|-1 | 实际=' + fmtJsonBrief(code);
  pm.test(title, function () {
    pm.expect(code === 0 || code === '0' || code === -1 || code === '-1').to.eql(true);
  });
  return code;
}
function loAssertValidity(validity, index, label) {
  var prefix = label + ': optionList[' + index + '].validity';
  assertCheck(prefix + ' 为对象', 'object', (!validity || typeof validity !== 'object' || Array.isArray(validity)) ? typeof validity : 'object');
  var t = validity && validity.type;
  var title = prefix + '.type 枚举 | 期望=1|2|3 | 实际=' + fmtJsonBrief(t);
  pm.test(title, function () {
    pm.expect([1, 2, 3].indexOf(t) >= 0).to.eql(true);
  });
  if (t === 1) {
    assertCheck(prefix + '.startTime 非空', true, !!(validity.startTime && String(validity.startTime)));
    assertCheck(prefix + '.endTime 非空', true, !!(validity.endTime && String(validity.endTime)));
  } else if (t === 2) {
    assertCheck(prefix + '.value 为整数', 'number', typeof validity.value);
    var unitTitle = prefix + '.unit 枚举 | 期望=DAY|MONTH|YEAR | 实际=' + fmtJsonBrief(validity.unit);
    pm.test(unitTitle, function () {
      pm.expect(['DAY', 'MONTH', 'YEAR'].indexOf(validity.unit) >= 0).to.eql(true);
    });
  }
}
function loAssertOptionItem(item, index, label) {
  var prefix = label + ': optionList[' + index + ']';
  assertCheck(prefix + ' 为对象', 'object', (!item || typeof item !== 'object' || Array.isArray(item)) ? typeof item : 'object');
  assertCheck(prefix + '.optionId 非空', true, !!(item && item.optionId && String(item.optionId)));
  assertCheck(prefix + '.optionName 非空', true, !!(item && item.optionName && String(item.optionName)));
  var tags = item && item.marketingTag;
  assertCheck(prefix + '.marketingTag 为数组', true, Array.isArray(tags));
  if (Array.isArray(tags)) {
    for (var i = 0; i < tags.length; i++) {
      var tagS = String(tags[i]);
      var tTitle = prefix + '.marketingTag[' + i + '] 枚举 | 期望=1|2|3|4 | 实际=' + tagS;
      pm.test(tTitle, function () {
        pm.expect(['1', '2', '3', '4'].indexOf(tagS) >= 0).to.eql(true);
      });
    }
  }
  loAssertValidity(item && item.validity, index, label);
}
/** 对齐 AssertLocalOfferOptionsSuccessContract；业务失败（code!=0）硬失败，不可跳过 */
function loAssertSuccessContract(label, options) {
  options = options || {};
  assertHttp(label + ': HTTP 状态码', 200);
  var body = loParseJson();
  assertCheck(label + ': 响应为对象', 'object', (!body || typeof body !== 'object' || Array.isArray(body)) ? typeof body : 'object');
  if (!body) return;
  loAssertEnvelopeCode(label + ': code 信封', body);
  var code = body.code;
  var bizOk = loIsBusinessSuccess(body);
  var bizTitle = label + ': 业务成功 | 期望=code=0 | 实际=' + fmtJsonBrief({ code: code, errCode: body.errCode, msg: body.msg });
  pm.test(bizTitle, function () {
    pm.expect(bizOk, '正向步骤业务失败不可跳过').to.eql(true);
  });
  if (!bizOk) return;
  assertCheck(label + ': 业务成功 code', 0, (code === '0' ? 0 : code));
  var data = body.data;
  assertCheck(label + ': data 为对象', 'object', (!data || typeof data !== 'object' || Array.isArray(data)) ? typeof data : 'object');
  if (!data) return;
  ['pagination', 'resourceId', 'resourceName', 'optionList'].forEach(function (k) {
    assertCheck(label + ': data.' + k + ' 存在', true, Object.prototype.hasOwnProperty.call(data, k));
  });
  var pagination = data.pagination;
  assertCheck(label + ': pagination 为对象', 'object', (!pagination || typeof pagination !== 'object' || Array.isArray(pagination)) ? typeof pagination : 'object');
  if (pagination && typeof pagination === 'object') {
    ['pageSize', 'pageNumber', 'totalNumber'].forEach(function (k) {
      assertCheck(label + ': pagination.' + k + ' 为整数', 'number', typeof pagination[k]);
    });
    if (typeof pagination.pageSize === 'number') {
      assertCheck(label + ': pageSize 范围 1..100', true, pagination.pageSize >= 1 && pagination.pageSize <= 100);
    }
    if (typeof pagination.pageNumber === 'number') {
      assertCheck(label + ': pageNumber 范围 1..100', true, pagination.pageNumber >= 1 && pagination.pageNumber <= 100);
    }
    if (typeof pagination.totalNumber === 'number') {
      assertCheck(label + ': totalNumber>=0', true, pagination.totalNumber >= 0);
    }
    if (options.expectedPageSize !== undefined && options.expectedPageSize !== null) {
      assertCheck(label + ': pageSize 回显', options.expectedPageSize, pagination.pageSize);
    }
    if (options.expectedPageNumber !== undefined && options.expectedPageNumber !== null) {
      assertCheck(label + ': pageNumber 回显', options.expectedPageNumber, pagination.pageNumber);
    }
  }
  assertCheck(label + ': resourceId 非空', true, !!(data.resourceId && String(data.resourceId)));
  if (options.expectedResourceId) {
    assertCheck(label + ': resourceId 回显', String(options.expectedResourceId), String(data.resourceId));
  }
  assertCheck(label + ': resourceName 非空', true, !!(data.resourceName && String(data.resourceName)));
  var list = data.optionList;
  assertCheck(label + ': optionList 为数组', true, Array.isArray(list));
  if (Array.isArray(list)) {
    for (var i = 0; i < list.length; i++) {
      loAssertOptionItem(list[i], i, label);
    }
  }
}
/** 字段非法入参固定文案：仅 fieldName 不同 */
function loInvalidFieldMsg(fieldName) {
  return "The field '" + fieldName + "' contains invalid characters or format is incorrect.";
}
/**
 * 非法 query 字段断言：code=-1 + 固定 msg（字段名代入）+ 可选 errCode。
 * 例：pageSize → 301.020.001；language → 300.020.001
 */
function loAssertInvalidFieldRejected(label, fieldName, expectedErrCode) {
  assertHttp(label + ': HTTP 状态码', 200);
  var body = loParseJson();
  assertCheck(label + ': 响应为对象', 'object', (!body || typeof body !== 'object' || Array.isArray(body)) ? typeof body : 'object');
  if (!body) return;
  var expectedMsg = loInvalidFieldMsg(fieldName);
  var codeOk = body.code === -1 || body.code === '-1';
  pm.test(label + ': code=-1 | 期望=-1 | 实际=' + fmtJsonBrief(body.code), function () {
    pm.expect(codeOk).to.eql(true);
  });
  assertCheck(label + ': msg 固定非法入参文案', expectedMsg, body.msg);
  if (expectedErrCode) {
    assertCheck(label + ': errCode', String(expectedErrCode), String(body.errCode || ''));
  } else {
    assertCheck(label + ': errCode 非空', true, !!(body.errCode && String(body.errCode)));
  }
}
/** 对齐 AssertLocalOfferOptionsRequestRejected（非固定文案类负向） */
function loAssertRejected(label) {
  var body = loParseJson();
  if (body === null) {
    var title = label + ' | 期望=HTTP>=400 | 实际=' + pm.response.code;
    pm.test(title, function () {
      pm.expect(pm.response.code >= 400).to.eql(true);
    });
    return;
  }
  assertCheck(label + ': 响应为对象', 'object', (typeof body !== 'object' || Array.isArray(body)) ? typeof body : 'object');
  if (pm.response.code === 200) {
    var ok = loIsBusinessSuccess(body);
    var actual = { http: pm.response.code, code: body.code, errCode: body.errCode, businessSuccess: ok };
    var title2 = label + ' | 期望=businessSuccess=false | 实际=' + fmtJsonBrief(actual);
    pm.test(title2, function () {
      pm.expect(ok).to.eql(false);
    });
    if (body.code === -1 || body.code === '-1') {
      assertCheck(label + ': errCode 非空', true, !!(body.errCode && String(body.errCode)));
      assertCheck(label + ': msg 非空', true, !!(body.msg && String(body.msg)));
    }
    return;
  }
  var title3 = label + ' | 期望=HTTP>=400 | 实际=' + pm.response.code;
  pm.test(title3, function () {
    pm.expect(pm.response.code >= 400).to.eql(true);
  });
}
/** canary 已知缺口：服务端未拒绝时软通过（对齐 pytest xfail） */
function loAssertRejectedOrKnownGap(label, gapNote, fieldName, expectedErrCode) {
  var body = loParseJson();
  var ok = pm.response.code === 200 && body && loIsBusinessSuccess(body);
  if (ok) {
    assertInfo(label + ': 已知缺口可观察', gapNote || '服务端未拒绝', body);
    return;
  }
  if (fieldName) {
    loAssertInvalidFieldRejected(label, fieldName, expectedErrCode);
    return;
  }
  loAssertRejected(label);
}
/** 对齐 GET .../options/{optionId} 成功契约；业务失败硬失败，不可跳过 */
function loAssertOptionDetailSuccess(label, expectedOptionId) {
  assertHttp(label + ': HTTP 状态码', 200);
  var body = loParseJson();
  assertCheck(label + ': 响应为对象', 'object', (!body || typeof body !== 'object' || Array.isArray(body)) ? typeof body : 'object');
  if (!body) return;
  loAssertEnvelopeCode(label + ': code 信封', body);
  var code = body.code;
  var bizOk = loIsBusinessSuccess(body);
  var bizTitle = label + ': 业务成功 | 期望=code=0 | 实际=' + fmtJsonBrief({ code: code, errCode: body.errCode, msg: body.msg });
  pm.test(bizTitle, function () {
    pm.expect(bizOk, '正向步骤业务失败不可跳过').to.eql(true);
  });
  if (!bizOk) return;
  assertCheck(label + ': 业务成功 code', 0, (code === '0' ? 0 : code));
  var data = body.data;
  assertCheck(label + ': data 为对象', 'object', (!data || typeof data !== 'object' || Array.isArray(data)) ? typeof data : 'object');
  if (!data) return;
  assertCheck(label + ': optionId 非空', true, !!(data.optionId && String(data.optionId)));
  if (expectedOptionId) {
    assertCheck(label + ': optionId 回显', String(expectedOptionId), String(data.optionId));
  }
  assertCheck(label + ': optionName 非空', true, !!(data.optionName && String(data.optionName)));
  var tags = data.marketingTag;
  assertCheck(label + ': marketingTag 为数组', true, Array.isArray(tags));
  loAssertValidity(data.validity, 0, label);
}
""".strip()
    return js.splitlines()


def SaveTokenLines() -> List[str]:
    """Auth 后置：把响应令牌写入多作用域。"""
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


def Lines_Auth() -> List[str]:
    return [
        "assertHttp('Auth: HTTP 状态码', 200);",
        "var _j_Auth = (function () { try { return pm.response.json(); } catch (e) { return {}; } })();",
        "var _d_Auth = _j_Auth.data !== undefined ? _j_Auth.data : _j_Auth;",
        "var _t_Auth = _d_Auth && (_d_Auth.accessToken || _d_Auth.token || _d_Auth.access_token);",
        "assertCheck('Auth: accessToken 非空', true, !!_t_Auth);",
        "assertInfo('Auth: accessToken 前缀', '非空令牌', _t_Auth ? (String(_t_Auth).slice(0, 12) + '...') : null);",
    ]


def MakeLoOptionsTestEvent(
    *,
    save_token: bool = False,
    extra_lines: Optional[Sequence[str]] = None,
) -> List[JsonObject]:
    lines: List[str] = []
    lines.extend(BuildLoOptionsJsHelpersLines())
    if save_token:
        lines.extend(SaveTokenLines())
    if extra_lines:
        lines.extend(list(extra_lines))
    return [{"listen": "test", "script": {"exec": lines, "type": "text/javascript"}}]


def AuthJsonHeaders() -> List[JsonObject]:
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
    """发送前：补齐 baseUrl/ProgramID/x-version/resourceId；强制注入 Authorization；改写未解析 path。"""
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
        "  // resourceId / optionId：Environment 优先，勿写死网点；兼容 localOfferResourceId 别名",
        "  var _rid = '';",
        "  try { _rid = String((pm.environment && pm.environment.get('resourceId')) || '').trim(); } catch (eR0) {}",
        "  if (!_rid) { try { _rid = String((pm.environment && pm.environment.get('localOfferResourceId')) || '').trim(); } catch (eR0b) {} }",
        "  if (!_rid) { try { _rid = String(pm.variables.get('resourceId') || '').trim(); } catch (eR1) {} }",
        "  if (!_rid) { try { _rid = String(pm.collectionVariables.get('resourceId') || '').trim(); } catch (eR2) {} }",
        "  if (!_rid) { try { _rid = String(pm.collectionVariables.get('localOfferResourceId') || '').trim(); } catch (eR3) {} }",
        "  var _oid = '';",
        "  try { _oid = String((pm.environment && pm.environment.get('optionId')) || '').trim(); } catch (eO0) {}",
        "  if (!_oid) { try { _oid = String(pm.variables.get('optionId') || '').trim(); } catch (eO1) {} }",
        "  if (!_oid) { try { _oid = String(pm.collectionVariables.get('optionId') || '').trim(); } catch (eO2) {} }",
        "  if (_rid) {",
        "    try { pm.variables.set('resourceId', _rid); } catch (eRS1) {}",
        "    try { pm.collectionVariables.set('resourceId', _rid); } catch (eRS2) {}",
        "  }",
        "  if (_oid) {",
        "    try { pm.variables.set('optionId', _oid); } catch (eOS1) {}",
        "    try { pm.collectionVariables.set('optionId', _oid); } catch (eOS2) {}",
        "  }",
        "  // Apifox customHttp 有时不替换 path 占位符：用环境值改写 URL",
        "  try {",
        "    var _url = pm.request && pm.request.url;",
        "    var _raw = '';",
        "    if (typeof _url === 'string') _raw = _url;",
        "    else if (_url && typeof _url.toString === 'function') _raw = String(_url.toString());",
        "    else if (_url && _url.raw) _raw = String(_url.raw);",
        "    if (_raw && (_rid || _oid)) {",
        "      var _next = _raw;",
        "      if (_rid) {",
        "        _next = _next.split('{{resourceId}}').join(_rid)",
        "          .split('{{localOfferResourceId}}').join(_rid)",
        "          .split('%7B%7BresourceId%7D%7D').join(encodeURIComponent(_rid))",
        "          .split('%7B%7BlocalOfferResourceId%7D%7D').join(encodeURIComponent(_rid));",
        "      }",
        "      if (_oid) {",
        "        _next = _next.split('{{optionId}}').join(_oid)",
        "          .split('%7B%7BoptionId%7D%7D').join(encodeURIComponent(_oid));",
        "      }",
        "      if (_next !== _raw) {",
        "        if (_url && typeof _url === 'object') {",
        "          try { _url.raw = _next; } catch (eU1) {}",
        "          try {",
        "            if (Array.isArray(_url.path)) {",
        "              _url.path = _url.path.map(function (p) {",
        "                var s = String(p || '');",
        "                if (_rid && (s === '{{resourceId}}' || s === '{{localOfferResourceId}}')) return _rid;",
        "                if (_oid && s === '{{optionId}}') return _oid;",
        "                if (_rid) s = s.split('{{resourceId}}').join(_rid).split('{{localOfferResourceId}}').join(_rid);",
        "                if (_oid) s = s.split('{{optionId}}').join(_oid);",
        "                return s;",
        "              });",
        "            }",
        "          } catch (eU2) {}",
        "        } else {",
        "          try { pm.request.url = _next; } catch (eU3) {}",
        "        }",
        "      }",
        "    }",
        "  } catch (eUrl) {}",
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
        "    } catch (eH) { console.warn('LO options ensure bearer', eH); }",
        "  }",
        "} catch (eAll) {}",
        *Lines_EnsureRequestIdHeader(),
    ]


def PostmanUrl(url_path: str, query: Optional[Dict[str, str]] = None) -> JsonObject:
    """构建 Postman URL；支持 query（Apifox/Postman 才会带上分页等参数）。"""
    path_only = url_path.split("?", 1)[0]
    merged_query: Dict[str, str] = {}
    if "?" in url_path:
        for part in url_path.split("?", 1)[1].split("&"):
            if "=" in part:
                key, value = part.split("=", 1)
                merged_query[key] = value
    if query:
        merged_query.update({str(k): str(v) for k, v in query.items()})
    path_parts: List[str] = [part for part in path_only.split("/") if part]
    # 空 resourceId：保留 // 语义 → path 中插入空段
    if "/localOffers//options" in path_only:
        path_parts = []
        for part in path_only.split("/"):
            if part == "":
                continue
            path_parts.append(part)
        # 强制在 localOffers 与 options 之间插入空段（部分客户端用 raw）
        raw = "{{baseUrl}}" + path_only
        url_obj: JsonObject = {"raw": raw, "host": ["{{baseUrl}}"], "path": ["v2", "resources", "localOffers", "", "options"]}
    else:
        raw = "{{baseUrl}}/" + "/".join(path_parts) if path_parts else "{{baseUrl}}"
        url_obj = {"raw": raw, "host": ["{{baseUrl}}"], "path": path_parts}
    if merged_query:
        url_obj["query"] = [{"key": k, "value": v} for k, v in merged_query.items()]
        url_obj["raw"] = str(url_obj["raw"]) + "?" + "&".join(f"{k}={v}" for k, v in merged_query.items())
    return url_obj


def PostmanJsonRawBody(raw: str) -> JsonObject:
    return {"mode": "raw", "raw": raw, "options": {"raw": {"language": "json"}}}


def CollectionVariable(key: str, value: str) -> JsonObject:
    return {"key": key, "value": value, "type": "string"}


def PurposeName(purpose: str, step_id: str, method: str, path_hint: str = "") -> str:
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
    test_lines: Optional[Sequence[str]] = None,
    query: Optional[Dict[str, str]] = None,
) -> JsonObject:
    req: JsonObject = {
        "method": method,
        "header": headers,
        "url": PostmanUrl(url_path, query=query),
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
        MakeLoOptionsTestEvent(save_token=save_token, extra_lines=test_lines)[0],
    ]
    return out


def Folder(name: str, items: Sequence[Union[JsonObject, Mapping[str, Any]]], description: str = "") -> JsonObject:
    folder: JsonObject = {"name": name, "item": list(items)}
    if description:
        folder["description"] = description
    return folder


def OptionsUrlPath(resource_id_expr: str) -> str:
    return f"/v2/resources/localOffers/{resource_id_expr}/options"


def Lines_ResolveResourceIdJs() -> List[str]:
    """断言侧解析 resourceId：Environment 优先。"""
    return [
        "var _rid = '';",
        "try { _rid = String((pm.environment && pm.environment.get('resourceId')) || '').trim(); } catch (e0) {}",
        "if (!_rid) { try { _rid = String(pm.variables.get('resourceId') || '').trim(); } catch (e1) {} }",
        "if (!_rid) { try { _rid = String(pm.collectionVariables.get('resourceId') || '').trim(); } catch (e2) {} }",
    ]


def Lines_SuccessMinimal(label: str) -> List[str]:
    return Lines_ResolveResourceIdJs() + [
        f"loAssertSuccessContract('{label}', {{ expectedResourceId: _rid || null, expectedPageSize: 10, expectedPageNumber: 1 }});",
    ]


def Lines_SuccessQueryCombo(label: str) -> List[str]:
    return Lines_ResolveResourceIdJs() + [
        f"loAssertSuccessContract('{label}', {{ expectedResourceId: _rid || null, expectedPageSize: 5, expectedPageNumber: 1 }});",
    ]


def Lines_OptionDetail(label: str) -> List[str]:
    return [
        "var _oid = '';",
        "try { _oid = String((pm.environment && pm.environment.get('optionId')) || '').trim(); } catch (e0) {}",
        "if (!_oid) { try { _oid = String(pm.variables.get('optionId') || '').trim(); } catch (e1) {} }",
        "if (!_oid) { try { _oid = String(pm.collectionVariables.get('optionId') || '').trim(); } catch (e2) {} }",
        f"loAssertOptionDetailSuccess('{label}', _oid || null);",
    ]


def BuildCollection() -> JsonObject:
    default_query: Dict[str, str] = {"pageSize": "10", "pageNumber": "1"}
    # 只取 Environment：{{resourceId}} / {{optionId}}；前置从环境注入并改写未解析占位符
    path_var = OptionsUrlPath("{{resourceId}}")
    detail_path = "/v2/resources/localOffers/{{resourceId}}/options/{{optionId}}"

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
                description="与 GetAccessToken 一致；数据集三列 ProgramID/clientId/secret。",
                save_token=True,
                test_lines=Lines_Auth(),
            ),
        ],
        description="先执行以写入 accessToken。",
    )

    positive_folder: JsonObject = Folder(
        "01 正向（契约）",
        [
            RequestItem(
                name=PurposeName("最小必填查询返回 options 列表", "P01", "GET", OPTIONS_PATH_HINT),
                method="GET",
                url_path=path_var,
                body=None,
                headers=BearerJsonHeaders(),
                description=(
                    "对齐 test_LocalOffersOptions_MinimalRequired_Smoke；"
                    "path 使用 Environment ``resourceId``；业务失败（code!=0）硬失败。"
                ),
                query=default_query,
                test_lines=Lines_SuccessMinimal("P01"),
            ),
            RequestItem(
                name=PurposeName("查询参数组合保持契约并回显分页", "P02", "GET", OPTIONS_PATH_HINT),
                method="GET",
                url_path=path_var,
                body=None,
                headers=BearerJsonHeaders(),
                description="对齐 test_LocalOffersOptions_QueryParameters_ShouldEchoPaginationAndKeepContract。",
                query={
                    "pageSize": "5",
                    "pageNumber": "1",
                    "language": "en-US",
                    "duration": "7",
                },
                test_lines=Lines_SuccessQueryCombo("P02"),
            ),
            RequestItem(
                name=PurposeName("查询 option 详情（SKU）", "P03", "GET", OPTION_DETAIL_PATH_HINT),
                method="GET",
                url_path=detail_path,
                body=None,
                headers=BearerJsonHeaders(),
                description=(
                    "GET .../options/{{optionId}}；``resourceId`` / ``optionId`` 均取自 Environment。"
                ),
                query={"language": "en-US"},
                test_lines=Lines_OptionDetail("P03"),
            ),
        ],
        description="正向 path 使用 ``{{resourceId}}`` / ``{{optionId}}``（Environment 注入，不写死）。",
    )

    negative_rid_folder: JsonObject = Folder(
        "02 负向 · resourceId",
        [
            RequestItem(
                name=PurposeName("不存在的 resourceId 应失败", "N01", "GET", OPTIONS_PATH_HINT),
                method="GET",
                url_path=OptionsUrlPath("LO_NOT_EXIST_000000"),
                body=None,
                headers=BearerJsonHeaders(),
                description="对齐 test_LocalOffersOptions_UnknownResourceId_ShouldFail。" + APIFOX_NEGATIVE_STEP_HINT,
                query=default_query,
                test_lines=["loAssertRejected('N01');"],
            ),
            RequestItem(
                name=PurposeName("空 resourceId 应失败", "N02", "GET", OPTIONS_PATH_HINT),
                method="GET",
                url_path="/v2/resources/localOffers//options",
                body=None,
                headers=BearerJsonHeaders(),
                description="对齐 test_LocalOffersOptions_EmptyResourceId_ShouldFail。" + APIFOX_NEGATIVE_STEP_HINT,
                query=default_query,
                test_lines=["loAssertRejected('N02');"],
            ),
            RequestItem(
                name=PurposeName("resourceId 含特殊字符应失败", "N03a", "GET", OPTIONS_PATH_HINT),
                method="GET",
                url_path=OptionsUrlPath("GR0006116!"),
                body=None,
                headers=BearerJsonHeaders(),
                description="对齐 InvalidResourceIdFormat special_char。" + APIFOX_NEGATIVE_STEP_HINT,
                query=default_query,
                test_lines=["loAssertRejected('N03a');"],
            ),
            RequestItem(
                name=PurposeName("resourceId 路径穿透样式应失败", "N03b", "GET", OPTIONS_PATH_HINT),
                method="GET",
                url_path=OptionsUrlPath("GR0006116%2F..%2Foptions"),
                body=None,
                headers=BearerJsonHeaders(),
                description="对齐 path_like；URL 编码避免破坏路径解析。" + APIFOX_NEGATIVE_STEP_HINT,
                query=default_query,
                test_lines=["loAssertRejected('N03b');"],
            ),
            RequestItem(
                name=PurposeName("resourceId 超长 129 应失败", "N03c", "GET", OPTIONS_PATH_HINT),
                method="GET",
                url_path=OptionsUrlPath("R" * 129),
                body=None,
                headers=BearerJsonHeaders(),
                description="对齐 over_128_chars。" + APIFOX_NEGATIVE_STEP_HINT,
                query=default_query,
                test_lines=["loAssertRejected('N03c');"],
            ),
        ],
        description="负向 resourceId；" + APIFOX_NEGATIVE_STEP_HINT,
    )

    # (step_id, query, purpose_tail, field_name) — 非法入参固定 msg，仅字段名不同
    pagination_cases: Sequence[tuple[str, Dict[str, str], str, str]] = (
        ("N04a", {"pageSize": "0", "pageNumber": "1"}, "pageSize=0", "pageSize"),
        ("N04b", {"pageSize": "101", "pageNumber": "1"}, "pageSize=101", "pageSize"),
        ("N04c", {"pageSize": "10", "pageNumber": "0"}, "pageNumber=0", "pageNumber"),
        ("N04d", {"pageSize": "10", "pageNumber": "101"}, "pageNumber=101", "pageNumber"),
        ("N04e", {"pageSize": "-1", "pageNumber": "1"}, "pageSize=-1", "pageSize"),
        ("N04f", {"pageSize": "abc", "pageNumber": "1"}, "pageSize=abc", "pageSize"),
    )
    pagination_items: List[JsonObject] = []
    for step_id, query, purpose_tail, field_name in pagination_cases:
        pagination_items.append(
            RequestItem(
                name=PurposeName(f"非法分页 {purpose_tail} 应失败", step_id, "GET", OPTIONS_PATH_HINT),
                method="GET",
                url_path=path_var,
                body=None,
                headers=BearerJsonHeaders(),
                description=(
                    f"对齐 InvalidPagination {purpose_tail}；"
                    f"断言固定非法入参文案（字段={field_name}）+ errCode=301.020.001。"
                    + APIFOX_NEGATIVE_STEP_HINT
                ),
                query=query,
                test_lines=[
                    f"loAssertInvalidFieldRejected('{step_id}', '{field_name}', '301.020.001');",
                ],
            )
        )

    optional_folder: JsonObject = Folder(
        "04 负向 · 可选 query",
        [
            RequestItem(
                name=PurposeName("非法 language 格式应失败", "N05a", "GET", OPTIONS_PATH_HINT),
                method="GET",
                url_path=path_var,
                body=None,
                headers=BearerJsonHeaders(),
                description=(
                    "对齐 language_invalid_format；固定非法入参文案（字段=language）+ errCode=300.020.001。"
                    + APIFOX_NEGATIVE_STEP_HINT
                ),
                query={"pageSize": "10", "pageNumber": "1", "language": "invalid-lang"},
                test_lines=["loAssertInvalidFieldRejected('N05a', 'language', '300.020.001');"],
            ),
            RequestItem(
                name=PurposeName("language 超长 65 应失败", "N05b", "GET", OPTIONS_PATH_HINT),
                method="GET",
                url_path=path_var,
                body=None,
                headers=BearerJsonHeaders(),
                description=(
                    "对齐 language_over_64_chars；固定非法入参文案（字段=language）+ errCode=300.020.001。"
                    + APIFOX_NEGATIVE_STEP_HINT
                ),
                query={"pageSize": "10", "pageNumber": "1", "language": "x" * 65},
                test_lines=["loAssertInvalidFieldRejected('N05b', 'language', '300.020.001');"],
            ),
            RequestItem(
                name=PurposeName("负数 duration（已知缺口观察）", "N05c", "GET", OPTIONS_PATH_HINT),
                method="GET",
                url_path=path_var,
                body=None,
                headers=BearerJsonHeaders(),
                description=(
                    "对齐 pytest xfail duration_negative：canary 若未拒绝则软通过；"
                    "若拒绝则断言固定非法入参文案（字段=duration）。"
                    + APIFOX_NEGATIVE_STEP_HINT
                ),
                query={"pageSize": "10", "pageNumber": "1", "duration": "-1"},
                test_lines=[
                    "loAssertRejectedOrKnownGap('N05c', 'canary 未按 integer 拒绝负数 duration', 'duration', null);",
                ],
            ),
            RequestItem(
                name=PurposeName("字符串 duration（已知缺口观察）", "N05d", "GET", OPTIONS_PATH_HINT),
                method="GET",
                url_path=path_var,
                body=None,
                headers=BearerJsonHeaders(),
                description=(
                    "对齐 pytest xfail duration_string：canary 若未拒绝则软通过；"
                    "若拒绝则断言固定非法入参文案（字段=duration）。"
                    + APIFOX_NEGATIVE_STEP_HINT
                ),
                query={"pageSize": "10", "pageNumber": "1", "duration": "seven"},
                test_lines=[
                    "loAssertRejectedOrKnownGap('N05d', 'canary 未按 integer 拒绝字符串 duration', 'duration', null);",
                ],
            ),
        ],
        description="可选参数负向；非法字段断言固定 msg 模板。",
    )

    info: JsonObject = {
        "name": COLLECTION_DISPLAY_NAME,
        "description": (
            "由 GeneratePostmanCollectionLocalOffersOptions.py 生成；"
            "对齐 test_local_offers_options.py / local_offers_options_service。\n"
            "请求名：``【测试目的】| 步骤ID | METHOD /path``。\n"
            "**多环境**：``baseUrl``、``x-version`` 由 Apifox Environment 注入。\n"
            "**数据集鉴权三列**：``ProgramID``、``clientId``、``secret``"
            "（DP_PROGRAM_ID / DP_CLIENT_ID / DP_CLIENT_SECRET）。\n"
            "**业务变量**：``resourceId``、``optionId`` 由 Apifox Environment 注入"
            "（集合不预置，避免空/旧值盖住环境）。"
        ),
        "schema": POSTMAN_SCHEMA,
    }

    variables: List[JsonObject] = [
        # baseUrl / x-version / resourceId / optionId 均留空，由 Environment 注入
        CollectionVariable("baseUrl", ""),
        CollectionVariable("x-version", ""),
    ]

    root: JsonObject = {
        "info": info,
        "variable": variables,
        "item": [
            auth_folder,
            positive_folder,
            negative_rid_folder,
            Folder("03 负向 · 分页", pagination_items, description="对齐 InvalidPagination。" + APIFOX_NEGATIVE_STEP_HINT),
            optional_folder,
        ],
    }
    return root


def Main() -> None:
    out_path: Path = CollectionPath(OUT_NAME)
    payload: JsonObject = BuildCollection()
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    Main()
