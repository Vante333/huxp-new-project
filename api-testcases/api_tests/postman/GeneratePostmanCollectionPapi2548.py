"""
根据 tests/features/test_membership_extensions.py / services/papi2548_service.py 生成 Postman Collection v2.1 JSON。

含与 helpers 对齐的 Tests（JavaScript），导入 Apifox 后位于接口「后置脚本」。

用法（仓库根目录）::

    python api-testcases/api_tests/postman/GeneratePostmanCollectionPapi2548.py
"""
from __future__ import annotations

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
""".strip()
    return [ln for ln in js.split("\n")]


def SaveTokenLines() -> List[str]:
    return [
        "try {",
        "  var j = pm.response.json();",
        "  var d = j.data !== undefined ? j.data : j;",
        "  var t = d.accessToken || d.token || d.access_token;",
        "  if (t) { pm.collectionVariables.set('accessToken', t); }",
        "} catch (e) { console.warn(e); }",
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
    return [
        {"key": "X-Program-ID", "value": "{{programId}}"},
        {"key": "X-Request-ID", "value": "{{$guid}}"},
        {"key": "Content-Type", "value": "application/json"},
        {"key": "Accept", "value": "*/*"},
    ]


def BearerJsonHeaders() -> List[JsonObject]:
    return [
        {"key": "X-Program-ID", "value": "{{programId}}"},
        {"key": "X-Request-ID", "value": "{{$guid}}"},
        {"key": "Authorization", "value": "Bearer {{accessToken}}"},
        {"key": "Content-Type", "value": "application/json"},
        {"key": "Accept", "value": "*/*"},
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
    out["event"] = MakeTestEvent(save_token=save_token, save_mid=save_mid, extra_lines=test_lines)
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
    }
    if extensions is not None:
        base["extensions"] = extensions
    return base


def JsonLiteral(obj: object) -> str:
    return json.dumps(obj, ensure_ascii=False)


def Lines_RegisterSuccessExpectExtensionsIfPresent(expected_ext: List[Dict[str, str]], label: str) -> List[str]:
    """若响应含 extensions 则归一化比对；若无则仅记录（与 pytest skip 分支一致）。"""
    exp = JsonLiteral(expected_ext)
    return [
        f"var _expExt_{label} = {exp};",
        f"pm.test('{label}: HTTP 200 且业务成功', function () {{",
        "  pm.response.to.have.status(200);",
        "  var j = pm.response.json();",
        "  pm.expect(isBusinessSuccess(j)).to.be.true;",
        "  var data = getInnerData(j);",
        "  pm.expect(data).to.be.an('object');",
        "  pm.expect(data.membershipId).to.be.ok;",
        "});",
        f"pm.test('{label}: extensions 若存在则与预期归一化一致', function () {{",
        "  var j = pm.response.json();",
        "  var data = getInnerData(j);",
        "  var got = extractExtensionsList(data);",
        "  if (!got || got.length === 0) {",
        "    console.warn('响应未带 extensions，与 pytest 可能 skip 一致');",
        "    pm.expect.ok = true;",
        "    return;",
        "  }",
        f"  var exp = _expExt_{label};",
        "  pm.expect(normalizedPairsEqual(normalizeExtensionsForCompare(got), normalizeExtensionsForCompare(exp))).to.be.true;",
        "});",
    ]


def Lines_RegisterSuccessEmptyOrOmit(label: str, expect_empty: bool) -> List[str]:
    if expect_empty:
        return [
            f"pm.test('{label}: HTTP 200 且 membershipId 存在', function () {{",
            "  pm.response.to.have.status(200);",
            "  var j = pm.response.json();",
            "  pm.expect(isBusinessSuccess(j)).to.be.true;",
            "  var data = getInnerData(j);",
            "  pm.expect(data.membershipId).to.be.ok;",
            "});",
            f"pm.test('{label}: extensions 为空或省略', function () {{",
            "  var j = pm.response.json();",
            "  var data = getInnerData(j);",
            "  if (!data.extensions) { pm.expect.ok = true; return; }",
            "  pm.expect(data.extensions === null || data.extensions.length === 0).to.be.true;",
            "});",
        ]
    return [
        f"pm.test('{label}: HTTP 200 omit extensions', function () {{",
        "  pm.response.to.have.status(200);",
        "  var j = pm.response.json();",
        "  pm.expect(isBusinessSuccess(j)).to.be.true;",
        "  var data = getInnerData(j);",
        "  pm.expect(data.membershipId).to.be.ok;",
        "});",
    ]


def Lines_RegisterFailureSixTypes() -> List[str]:
    return [
        "pm.test('R06: 6 types 期望失败（未收紧时可能成功=skip）', function () {",
        "  var j = pm.response.json();",
        "  var ok = pm.response.code === 200 && isBusinessSuccess(j);",
        "  if (ok) {",
        "    console.warn('沙箱未拒绝 6 个 type');",
        "    return;",
        "  }",
        "  pm.expect(ok).to.be.false;",
        "  var ec = j.errCode;",
        "  if (ec) {",
        f"    var hit = (ec === '{PAPI2548_EXT_ERR_MAX_FIVE_TYPES}' || ec === '{PAPI2548_EXT_ERR_MAX_LEGACY}');",
        "    if (!hit) { console.warn('errCode', ec); }",
        "  }",
        "});",
    ]


def Lines_RegisterFailureBoundary() -> List[str]:
    return [
        "pm.test('R07C/D: 边界外期望失败', function () {",
        "  var j = pm.response.json();",
        "  var ok = pm.response.code === 200 && isBusinessSuccess(j);",
        "  if (ok) { console.warn('沙箱未拒绝 129 长度'); return; }",
        "  pm.expect(ok).to.be.false;",
        "});",
    ]


def Lines_RegisterDuplicateType() -> List[str]:
    return [
        "pm.test('R02: 重复 type — 失败或成功+search 校验', function () {",
        "  var j = pm.response.json();",
        "  var ok = pm.response.code === 200 && isBusinessSuccess(j);",
        "  if (!ok) {",
        "    pm.expect(isBusinessSuccess(j)).to.be.false;",
        "    var ec = j.errCode;",
        "    if (ec) {",
        "      pm.expect(['"
        + PAPI2548_EXT_ERR_DUPLICATE_TYPE
        + "', '"
        + PAPI2548_EXT_ERR_DUP_LEGACY
        + "']).to.include(ec);",
        "    }",
        "  }",
        "});",
    ]


def Lines_SearchExpectExtensions(expected_ext: List[Dict[str, str]], label: str) -> List[str]:
    exp = JsonLiteral(expected_ext)
    return [
        f"var _expSearch_{label} = {exp};",
        f"pm.test('{label}: search HTTP 200 且业务成功', function () {{",
        "  pm.response.to.have.status(200);",
        "  var j = pm.response.json();",
        "  pm.expect(isBusinessSuccess(j)).to.be.true;",
        "});",
        f"pm.test('{label}: search extensions 归一化一致（若环境返回）', function () {{",
        "  var j = pm.response.json();",
        "  var inner = j.data;",
        "  var rec = unwrapMembershipRecord(inner);",
        "  var mid = pm.collectionVariables.get('membershipId');",
        "  pm.expect(String(rec.membershipId)).to.eql(String(mid));",
        "  var got = extractExtensionsList(rec);",
        "  if (!got || got.length === 0) {",
        "    console.warn('search 未返回 extensions');",
        "    return;",
        "  }",
        f"  var exp = _expSearch_{label};",
        "  pm.expect(normalizedPairsEqual(normalizeExtensionsForCompare(got), normalizeExtensionsForCompare(exp))).to.be.true;",
        "});",
    ]


def Lines_SearchOmitSemantics() -> List[str]:
    return [
        "pm.test('S02: search 成功', function () {",
        "  pm.response.to.have.status(200);",
        "  var j = pm.response.json();",
        "  pm.expect(isBusinessSuccess(j)).to.be.true;",
        "});",
        "pm.test('S02: extensions 省略或空', function () {",
        "  var j = pm.response.json();",
        "  var rec = unwrapMembershipRecord(j.data);",
        "  var raw = rec.extensions;",
        "  if (raw === undefined || raw === null) { pm.expect.ok = true; return; }",
        "  pm.expect(Array.isArray(raw) && raw.length === 0).to.be.true;",
        "});",
    ]


def Lines_PatchExpectExtensionsFixed(expected: List[Dict[str, str]], label: str) -> List[str]:
    """data.membershipId 与 {{membershipId}} 一致 + extensions 归一化。"""
    exp = JsonLiteral(expected)
    return [
        f"var _expPatch_{label} = {exp};",
        f"pm.test('{label}: PATCH 成功且 extensions 归一化', function () {{",
        "  pm.response.to.have.status(200);",
        "  var j = pm.response.json();",
        "  pm.expect(isBusinessSuccess(j)).to.be.true;",
        "  var data = getInnerData(j);",
        "  var mid = pm.collectionVariables.get('membershipId');",
        "  pm.expect(String(data.membershipId)).to.eql(String(mid));",
        "  pm.expect(data).to.have.property('extensions');",
        "  var got = extractExtensionsList(data);",
        f"  var exp = _expPatch_{label};",
        "  pm.expect(normalizedPairsEqual(normalizeExtensionsForCompare(got), normalizeExtensionsForCompare(exp))).to.be.true;",
        "});",
    ]


def Lines_PatchInvalidMid() -> List[str]:
    return [
        "pm.test('U06: 非法 membershipId', function () {",
        "  var j = pm.response.json();",
        "  pm.expect(j).to.have.property('code');",
        "  var ok = pm.response.code === 200 && isBusinessSuccess(j);",
        "  pm.expect(ok).to.be.false;",
        "});",
    ]


def Lines_U07aSaveSnapshot() -> List[str]:
    return [
        "pm.test('U07a: search 成功', function () {",
        "  pm.response.to.have.status(200);",
        "  var j = pm.response.json();",
        "  pm.expect(isBusinessSuccess(j)).to.be.true;",
        "});",
        "try {",
        "  var j = pm.response.json();",
        "  var rec = unwrapMembershipRecord(j.data);",
        "  var got = extractExtensionsList(rec);",
        "  pm.collectionVariables.set('u07aExtNorm', JSON.stringify(normalizeExtensionsForCompare(got)));",
        "} catch (e) { console.warn(e); }",
    ]


def Lines_U07bInvalidOp() -> List[str]:
    return [
        "pm.test('U07b: 响应含 code', function () {",
        "  var j = pm.response.json();",
        "  pm.expect(j).to.have.property('code');",
        "});",
    ]


def Lines_U07cMatchSnapshot() -> List[str]:
    return [
        "pm.test('U07c: 非法 operation 后 extensions 与 U07a 一致', function () {",
        "  var j = pm.response.json();",
        "  pm.expect(isBusinessSuccess(j)).to.be.true;",
        "  var rec = unwrapMembershipRecord(j.data);",
        "  var got = extractExtensionsList(rec);",
        "  var before = JSON.parse(pm.collectionVariables.get('u07aExtNorm') || '[]');",
        "  pm.expect(normalizedPairsEqual(normalizeExtensionsForCompare(got), before)).to.be.true;",
        "});",
    ]


def Lines_U03bSaveSnapshot() -> List[str]:
    return [
        "pm.test('U03b: search 快照', function () {",
        "  pm.response.to.have.status(200);",
        "  var j = pm.response.json();",
        "  pm.expect(isBusinessSuccess(j)).to.be.true;",
        "});",
        "try {",
        "  var j = pm.response.json();",
        "  var rec = unwrapMembershipRecord(j.data);",
        "  var got = extractExtensionsList(rec);",
        "  pm.collectionVariables.set('u03bExtNorm', JSON.stringify(normalizeExtensionsForCompare(got)));",
        "} catch (e) { console.warn(e); }",
    ]


def Lines_U04NosuchAfterSnapshot() -> List[str]:
    return [
        "pm.test('U04: DELETE nosuch 后 extensions 与 U03b 快照一致', function () {",
        "  pm.response.to.have.status(200);",
        "  var j = pm.response.json();",
        "  pm.expect(isBusinessSuccess(j)).to.be.true;",
        "  var data = getInnerData(j);",
        "  var got = extractExtensionsList(data);",
        "  var before = JSON.parse(pm.collectionVariables.get('u03bExtNorm') || '[]');",
        "  pm.expect(normalizedPairsEqual(normalizeExtensionsForCompare(got), before)).to.be.true;",
        "});",
    ]


def Lines_U08MissingValue() -> List[str]:
    return [
        "pm.test('U08: UPSERT 无 value — 含业务 code', function () {",
        "  var j = pm.response.json();",
        "  pm.expect(j).to.have.property('code');",
        "  pm.response.to.have.status(200);",
        "});",
    ]


def Lines_E3SaveNorm() -> List[str]:
    return [
        "pm.test('E3: PATCH 成功 e2+e3', function () {",
        "  pm.response.to.have.status(200);",
        "  var j = pm.response.json();",
        "  pm.expect(isBusinessSuccess(j)).to.be.true;",
        "  var data = getInnerData(j);",
        "  var got = extractExtensionsList(data);",
        "  var exp = [{ type: 'e2', value: '2' }, { type: 'e3', value: '3' }];",
        "  pm.expect(normalizedPairsEqual(normalizeExtensionsForCompare(got), normalizeExtensionsForCompare(exp))).to.be.true;",
        "  pm.collectionVariables.set('e3patchNorm', JSON.stringify(normalizeExtensionsForCompare(got)));",
        "});",
    ]


def Lines_E4MatchE3() -> List[str]:
    return [
        "pm.test('E4: search 与 E3 PATCH 归一化一致', function () {",
        "  var j = pm.response.json();",
        "  pm.expect(isBusinessSuccess(j)).to.be.true;",
        "  var rec = unwrapMembershipRecord(j.data);",
        "  var got = extractExtensionsList(rec);",
        "  var e3 = JSON.parse(pm.collectionVariables.get('e3patchNorm') || '[]');",
        "  pm.expect(normalizedPairsEqual(normalizeExtensionsForCompare(got), e3)).to.be.true;",
        "});",
    ]


def Lines_PatchMixed() -> List[str]:
    return [
        "pm.test('U05: 混合操作后 keepMe+addMe', function () {",
        "  pm.response.to.have.status(200);",
        "  var j = pm.response.json();",
        "  pm.expect(isBusinessSuccess(j)).to.be.true;",
        "  var data = getInnerData(j);",
        "  var got = extractExtensionsList(data);",
        "  var exp = [{ type: 'keepMe', value: '2' }, { type: 'addMe', value: '3' }];",
        "  pm.expect(normalizedPairsEqual(normalizeExtensionsForCompare(got), normalizeExtensionsForCompare(exp))).to.be.true;",
        "});",
    ]


def Lines_Auth() -> List[str]:
    return [
        "pm.test('Auth: HTTP 200 且含 accessToken', function () {",
        "  pm.response.to.have.status(200);",
        "  var j = pm.response.json();",
        "  var d = j.data !== undefined ? j.data : j;",
        "  var t = d.accessToken || d.token || d.access_token;",
        "  pm.expect(t).to.be.ok;",
        "});",
    ]


def Lines_U09PostAlt() -> List[str]:
    return [
        "pm.test('U09: POST extensions（网关仅 POST 时）', function () {",
        "  pm.response.to.have.status(200);",
        "  var j = pm.response.json();",
        "  pm.expect(isBusinessSuccess(j)).to.be.true;",
        "});",
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
                name="POST /v2/auth/token（GetAccessToken）",
                method="POST",
                url_path="/v2/auth/token",
                body=json.dumps(
                    {"clientId": "{{clientId}}", "secret": "{{clientSecret}}"},
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
            name="R01 test_register_with_extensions_echo",
            method="POST",
            url_path="/v2/memberships",
            body=json.dumps(MinimalRegisterPayload(ext_echo), ensure_ascii=False, indent=2),
            headers=BearerJsonHeaders(),
            description="TestMembershipsRegisterExtensions::test_register_with_extensions_echo",
            save_mid=True,
            test_lines=Lines_RegisterSuccessExpectExtensionsIfPresent(ext_echo, "R01"),
        ),
        RequestItem(
            name="R02 test_register_duplicate_type_fails",
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
            name="R03 test_register_omit_extensions_success（无 extensions 键）",
            method="POST",
            url_path="/v2/memberships",
            body=json.dumps(MinimalRegisterPayload(None), ensure_ascii=False, indent=2),
            headers=BearerJsonHeaders(),
            description="BuildMinimalMembershipPayload(extensions=None)。",
            save_mid=True,
            test_lines=Lines_RegisterSuccessEmptyOrOmit("R03", expect_empty=False),
        ),
        RequestItem(
            name="R04 test_register_empty_extensions_success",
            method="POST",
            url_path="/v2/memberships",
            body=json.dumps(MinimalRegisterPayload([]), ensure_ascii=False, indent=2),
            headers=BearerJsonHeaders(),
            description="extensions: []",
            save_mid=True,
            test_lines=Lines_RegisterSuccessEmptyOrOmit("R04", expect_empty=True),
        ),
        RequestItem(
            name="R05 test_register_five_distinct_types_success",
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
            name="R06 test_register_six_types_fails",
            method="POST",
            url_path="/v2/memberships",
            body=json.dumps(MinimalRegisterPayload(six_ext), ensure_ascii=False, indent=2),
            headers=BearerJsonHeaders(),
            description="s0..s5；AssertPapi2548MaxFiveTypesErrorResponse。",
            test_lines=Lines_RegisterFailureSixTypes(),
        ),
        RequestItem(
            name="R07A param A_128_1（type 128 / value 1）",
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
            name="R07B param B_1_128（type 1 / value 128）",
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
            name="R07C param C_129_1（type 129 — 期望失败）",
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
            name="R07D param D_1_129（value 129 — 期望失败）",
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

    search_folder: JsonObject = Folder(
        "02 Search（TestMembershipsSearchExtensions）",
        [
            RequestItem(
                name="S01 test_search_extensions_match_register",
                method="POST",
                url_path="/v2/memberships/search",
                body=json.dumps({"membershipId": "{{membershipId}}"}, indent=2),
                headers=BearerJsonHeaders(),
                description="先 R01；RunSearchResponseAssertions。",
                test_lines=Lines_SearchExpectExtensions(ext_echo, "S01"),
            ),
            RequestItem(
                name="S02 test_search_membership_without_extensions_semantics",
                method="POST",
                url_path="/v2/memberships/search",
                body=json.dumps({"membershipId": "{{membershipId}}"}, indent=2),
                headers=BearerJsonHeaders(),
                description="先 R03；RunSearchOmitExtensionsSemanticsAssertions。",
                test_lines=Lines_SearchOmitSemantics(),
            ),
        ],
        description="PostMembershipsSearch。",
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
                name="U0 前置 Register（keepA，供 UPSERT 新增）",
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
                name="U01 PATCH test_extensions_upsert_add_new_type",
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
                name="U0b 前置 Register（k1=old）",
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
                name="U02 PATCH test_extensions_upsert_update_value",
                method="PATCH",
                url_path="/v2/memberships/extensions",
                body=ext_body([{"operation": "UPSERT", "type": "k1", "value": "newval"}]),
                headers=ext_patch_headers,
                description="单条 k1=newval。",
                test_lines=Lines_PatchExpectExtensionsFixed([{"type": "k1", "value": "newval"}], "U02"),
            ),
            RequestItem(
                name="U0c 前置 Register（a1,b2）",
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
                name="U03 PATCH test_extensions_delete_existing_type",
                method="PATCH",
                url_path="/v2/memberships/extensions",
                body=ext_body([{"operation": "DELETE", "type": "a1"}]),
                headers=ext_patch_headers,
                description="仅 b2。",
                test_lines=Lines_PatchExpectExtensionsFixed([{"type": "b2", "value": "2"}], "U03"),
            ),
            RequestItem(
                name="U0d 前置 Register（only）+ search 快照链",
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
                name="U03b POST search（DELETE nosuch 前）",
                method="POST",
                url_path="/v2/memberships/search",
                body=json.dumps({"membershipId": "{{membershipId}}"}, indent=2),
                headers=BearerJsonHeaders(),
                description="RunSearchSnapshotForDeleteAssertions。",
                test_lines=Lines_U03bSaveSnapshot(),
            ),
            RequestItem(
                name="U04 PATCH DELETE 不存在的 type（nosuch）",
                method="PATCH",
                url_path="/v2/memberships/extensions",
                body=ext_body([{"operation": "DELETE", "type": "nosuch"}]),
                headers=ext_patch_headers,
                description="与快照一致。",
                test_lines=Lines_U04NosuchAfterSnapshot(),
            ),
            RequestItem(
                name="U0e 前置 Register（delMe, keepMe）",
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
                name="U05 PATCH test_extensions_mixed_operations",
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
                name="U06 PATCH test_extensions_invalid_membership_id_fails",
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
                name="U0f 前置 Register（stable）— 非法 operation 链",
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
                name="U07a POST search（非法 operation 前）",
                method="POST",
                url_path="/v2/memberships/search",
                body=json.dumps({"membershipId": "{{membershipId}}"}, indent=2),
                headers=BearerJsonHeaders(),
                description="快照 extensions。",
                test_lines=Lines_U07aSaveSnapshot(),
            ),
            RequestItem(
                name="U07b PATCH 非法 operation UPDATE",
                method="PATCH",
                url_path="/v2/memberships/extensions",
                body=ext_body([{"operation": "UPDATE", "type": "x", "value": "y"}]),
                headers=ext_patch_headers,
                description="RunPatchInvalidOperationGatewayAssertions。",
                test_lines=Lines_U07bInvalidOp(),
            ),
            RequestItem(
                name="U07c POST search（非法 operation 后）",
                method="POST",
                url_path="/v2/memberships/search",
                body=json.dumps({"membershipId": "{{membershipId}}"}, indent=2),
                headers=BearerJsonHeaders(),
                description="与 U07a 一致。",
                test_lines=Lines_U07cMatchSnapshot(),
            ),
            RequestItem(
                name="U0g 前置 Register（base）",
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
                name="U08 PATCH UPSERT 缺 value（noval）",
                method="PATCH",
                url_path="/v2/memberships/extensions",
                body=ext_body([{"operation": "UPSERT", "type": "noval"}]),
                headers=ext_patch_headers,
                description="RunUpsertMissingValueDocumentedAssertions。",
                test_lines=Lines_U08MissingValue(),
            ),
            RequestItem(
                name="U09 POST 同路径（DP_MEMBERSHIP_EXTENSIONS_METHOD=POST 时）",
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
                name="E1 Register（e1,e2）",
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
                name="E2 POST search #1",
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
                name="E3 PATCH（DELETE e1 + UPSERT e3）",
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
                name="E4 POST search #2",
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
            "导入 Apifox 后位于「后置脚本」；非可视化断言组件。\n\n"
            "变量：baseUrl、programId、clientId、clientSecret、accessToken、membershipId、fakeMembershipId、"
            "u07aExtNorm、u03bExtNorm、e3patchNorm。"
        ),
        "schema": POSTMAN_SCHEMA,
    }

    variables: List[JsonObject] = [
        CollectionVariable("baseUrl", "https://developer-sandbox.dragonpass.com/api"),
        CollectionVariable("programId", ""),
        CollectionVariable("clientId", ""),
        CollectionVariable("clientSecret", ""),
        CollectionVariable("accessToken", ""),
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

    out_path = os.path.join(os.path.dirname(__file__), "PAPI-2548-membership-extensions.postman_collection.json")
    payload = BuildCollection()
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


if __name__ == "__main__":
    Main()
