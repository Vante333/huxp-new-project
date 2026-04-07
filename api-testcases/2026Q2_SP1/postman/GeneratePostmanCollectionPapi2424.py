"""
根据 test_papi_2424_ePasses_details_ms_order_hint.py / papi2424_helpers.py 生成 Postman Collection v2.1 JSON。

ePass 鉴权与 ``GetAccessTokenForEpass`` 对齐；Tests 内联 ``BuildP2424JsHelpersLines()``（与 papi2424_helpers 断言语义对齐）。

用法（仓库根目录）::

    python api-testcases/2026Q2_SP1/postman/GeneratePostmanCollectionPapi2424.py
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Final, List, Mapping, Optional, Sequence, Union

JsonObject = Dict[str, Any]

POSTMAN_SCHEMA: Final[str] = "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
OUT_NAME: Final[str] = "PAPI-2424-ePasses-details-ms-order-hint.postman_collection.json"
_POSTMAN_ID: Final[str] = "a1b2c3d4-papi-2424-pytest-parity"

# 与 papi2424_helpers 一致
P2424_MS_HINT_ERR: Final[str] = "500.000.024"
P2424_MS_HINT_MSG: Final[str] = (
    "The order ID you entered is not a usage order ID. If you want to query E-pass details, "
    "please use the /orders/ePasses/search API."
)


def BuildP2424JsHelpersLines() -> List[str]:
    """与 papi2424_helpers 中 MS 提示/非 MS/usage 回归/大小写分支语义对齐的 Postman Tests 公共脚本。"""
    err_lit = json.dumps(P2424_MS_HINT_ERR, ensure_ascii=False)
    msg_lit = json.dumps(P2424_MS_HINT_MSG, ensure_ascii=False)
    js = rf"""
var P2424_MS_HINT_ERR = {err_lit};
var P2424_MS_HINT_MSG = {msg_lit};

function p2424IsBusinessSuccess(json) {{
  if (!json || typeof json !== "object") return false;
  var c = json.code;
  return c === 0 || c === "0";
}}

function p2424MsPrefixCaseInsensitiveFromEnv(pm) {{
  var v = String(pm.collectionVariables.get("DP_P2424_MS_PREFIX_CASE_INSENSITIVE") || "")
    .trim()
    .toLowerCase();
  return v === "1" || v === "true" || v === "yes" || v === "on";
}}

/** 对齐 ``AssertHttp200MsUsageOrderHintEnvelope`` */
function p2424AssertMsUsageOrderHintEnvelope(pm, context) {{
  context = context || "PAPI-2424";
  pm.test(context + "：HTTP 200；code=-1；errCode=500.000.024；msg 全文一致", function () {{
    pm.response.to.have.status(200);
    var root = pm.response.json();
    pm.expect(root).to.be.an("object");
    pm.expect(root.code).to.eql(-1);
    var err = root.errCode;
    pm.expect(String(err)).to.eql(P2424_MS_HINT_ERR);
    pm.expect(root.msg).to.eql(P2424_MS_HINT_MSG);
  }});
}}

/** 对齐 ``AssertHttp200NotMsUsageOrderHint`` */
function p2424AssertNotMsUsageOrderHint(pm, context) {{
  context = context || "PAPI-2424";
  pm.test(context + "：HTTP 200；排除 MS 专用 errCode 与全文 msg", function () {{
    pm.response.to.have.status(200);
    var root = pm.response.json();
    pm.expect(root).to.be.an("object");
    var errS = root.errCode === undefined || root.errCode === null ? "" : String(root.errCode);
    pm.expect(errS).to.not.eql(P2424_MS_HINT_ERR);
    var msg = root.msg;
    if (typeof msg === "string" && msg) {{
      pm.expect(msg).to.not.eql(P2424_MS_HINT_MSG);
    }}
  }});
}}

/** 对齐 ``AssertUsageOrderRegressionNotMsHint`` */
function p2424AssertUsageOrderRegressionNotMsHint(pm, context) {{
  context = context || "PAPI-2424-usage";
  pm.test(context + "：HTTP 200；usage 不命中 500.000.024", function () {{
    pm.response.to.have.status(200);
    var root = pm.response.json();
    pm.expect(root).to.be.an("object");
    var errS = root.errCode === undefined || root.errCode === null ? "" : String(root.errCode);
    pm.expect(errS).to.not.eql(P2424_MS_HINT_ERR);
  }});
}}

/** 对齐 ``AssertLowercaseMsPrefixBehavior``（依赖集合变量 DP_P2424_MS_PREFIX_CASE_INSENSITIVE） */
function p2424AssertLowercaseMsPrefixBehavior(pm, context) {{
  context = context || "PAPI-2424-case";
  var insensitive = p2424MsPrefixCaseInsensitiveFromEnv(pm);
  if (insensitive) {{
    p2424AssertMsUsageOrderHintEnvelope(pm, context);
  }} else {{
    p2424AssertNotMsUsageOrderHint(pm, context);
  }}
}}
""".strip()
    return js.splitlines()


def MakeP2424TestEvent(
    *,
    save_token: bool = False,
    extra_lines: Optional[Sequence[str]] = None,
) -> List[JsonObject]:
    lines: List[str] = []
    lines.extend(BuildP2424JsHelpersLines())
    if save_token:
        lines.extend(
            [
                "pm.test('Auth：HTTP 200 且写入 accessToken（ePass client）', function () {",
                "  pm.response.to.have.status(200);",
                "  var j = pm.response.json();",
                "  pm.expect(p2424IsBusinessSuccess(j)).to.be.true;",
                "  var t = j.data && j.data.accessToken;",
                "  pm.expect(t).to.be.ok;",
                "  pm.collectionVariables.set('accessToken', String(t));",
                "});",
            ]
        )
    if extra_lines:
        lines.extend(list(extra_lines))
    return [{"listen": "test", "script": {"exec": lines, "type": "text/javascript"}}]


def AuthEpassJsonHeaders() -> List[JsonObject]:
    """取 token：X-Program-ID 使用 epassProgramId（与 GetAccessTokenForEpass 一致）。"""
    return [
        {"key": "X-Program-ID", "value": "{{epassProgramId}}"},
        {"key": "X-Request-ID", "value": "{{$guid}}"},
        {"key": "Content-Type", "value": "application/json"},
        {"key": "Accept", "value": "*/*"},
        {
            "key": "Authorization",
            "value": "{{epassTokenRequestBearer}}",
            "description": "填完整 Authorization 值（可含 Bearer）；不需要则保持禁用本头",
            "disabled": True,
        },
    ]


def BearerEpassJsonHeaders() -> List[JsonObject]:
    """业务请求：Program 与 pytest RequestWithAllure(x_program_id=DP_EPASS_PROGRAM_ID) 一致。"""
    return [
        {"key": "X-Program-ID", "value": "{{epassProgramId}}"},
        {"key": "X-Request-ID", "value": "{{$guid}}"},
        {"key": "Authorization", "value": "Bearer {{accessToken}}"},
        {"key": "Content-Type", "value": "application/json"},
        {"key": "Accept", "value": "*/*"},
    ]


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
) -> JsonObject:
    req: JsonObject = {
        "method": method,
        "header": headers,
        "url": "{{baseUrl}}" + url_path,
        "description": description,
    }
    if body is not None:
        req["body"] = {"mode": "raw", "raw": body}
    out: JsonObject = {"name": name, "request": req}
    out["event"] = MakeP2424TestEvent(save_token=save_token, extra_lines=test_lines)
    return out


def Folder(name: str, items: Sequence[Union[JsonObject, Mapping[str, Any]]], description: str = "") -> JsonObject:
    folder: JsonObject = {"name": name, "item": list(items)}
    if description:
        folder["description"] = description
    return folder


def DetailsBodyRaw(order_id_var: str) -> str:
    return json.dumps({"orderId": "{{" + order_id_var + "}}"}, ensure_ascii=False, indent=2)


def BuildCollection() -> JsonObject:
    auth_folder: JsonObject = Folder(
        "00 Auth（ePass）",
        [
            RequestItem(
                name="POST /v2/auth/token（GetAccessTokenForEpass）",
                method="POST",
                url_path="/v2/auth/token",
                body=json.dumps(
                    {"clientId": "{{epassClientId}}", "secret": "{{epassClientSecret}}"},
                    ensure_ascii=False,
                    indent=2,
                ),
                headers=AuthEpassJsonHeaders(),
                description=(
                    "与 papi2548_helpers.GetAccessTokenForEpass 一致；集合变量 epassProgramId / epassClientId / epassClientSecret。\n"
                    "若网关要求父级 Bearer，启用 Authorization 头并填入完整值（与 DP_EPASS_TOKEN_REQUEST_BEARER 或 DP_TOKEN_REQUEST_BEARER 对应）。\n"
                    "与 pytest 一致不传 X-Program-ID 时：不在本集合实现 DP_TOKEN_OMIT_PROGRAM_ID，请在环境按需删头或改生成器。"
                ),
                save_token=True,
            ),
        ],
    )

    ms_folder: JsonObject = Folder(
        "01 tc-P2-EPASS-001（MS 前缀 → 500.000.024）",
        [
            RequestItem(
                name="test_ms_prefix_returns_search_hint — 最短前缀 MS",
                method="POST",
                url_path="{{p2424V2DetailsPath}}",
                body=DetailsBodyRaw("p2424OrderIdMsShort"),
                headers=BearerEpassJsonHeaders(),
                description="参数化 orderId=MS；对齐 test_ms_prefix_returns_search_hint。",
                test_lines=["p2424AssertMsUsageOrderHintEnvelope(pm, 'PAPI-2424-MS-short');"],
            ),
            RequestItem(
                name="test_ms_prefix_returns_search_hint — 典型 MS00000000000001",
                method="POST",
                url_path="{{p2424V2DetailsPath}}",
                body=DetailsBodyRaw("p2424OrderIdMsTypical"),
                headers=BearerEpassJsonHeaders(),
                description="参数化 orderId=MS00000000000001。",
                test_lines=["p2424AssertMsUsageOrderHintEnvelope(pm, 'PAPI-2424-MS-typical');"],
            ),
        ],
    )

    non_ms_folder: JsonObject = Folder(
        "02 tc-P1 / tc-P3（非 MS 子串与 usage）",
        [
            RequestItem(
                name="test_usage_order_id_not_ms_hint（需填 p2424UsageOrderId）",
                method="POST",
                url_path="{{p2424V2DetailsPath}}",
                body=DetailsBodyRaw("p2424UsageOrderId"),
                headers=BearerEpassJsonHeaders(),
                description=(
                    "对齐 test_usage_order_id_not_ms_hint；须为非 MS 开头的真实 usage 订单号（DP_P2424_USAGE_ORDER_ID）。\n"
                    "未填写时请求体会无效，请先填集合变量。"
                ),
                test_lines=["p2424AssertUsageOrderRegressionNotMsHint(pm, 'PAPI-2424-usage');"],
            ),
            RequestItem(
                name="test_substring_ms_not_prefix_dp_style — DP000MS00000001",
                method="POST",
                url_path="{{p2424V2DetailsPath}}",
                body=DetailsBodyRaw("p2424OrderIdSubstringDp"),
                headers=BearerEpassJsonHeaders(),
                description="含 MS 子串但非前缀。",
                test_lines=["p2424AssertNotMsUsageOrderHint(pm, 'PAPI-2424-substring-DP');"],
            ),
            RequestItem(
                name="test_substring_ms_not_prefix_sl_style — SL20260129BBMSXV9",
                method="POST",
                url_path="{{p2424V2DetailsPath}}",
                body=DetailsBodyRaw("p2424OrderIdSubstringSl"),
                headers=BearerEpassJsonHeaders(),
                description="SL 样例。",
                test_lines=["p2424AssertNotMsUsageOrderHint(pm, 'PAPI-2424-substring-SL');"],
            ),
        ],
    )

    case_folder: JsonObject = Folder(
        "03 tc-P3-EPASS-002（MS vs ms，依赖 DP_P2424_MS_PREFIX_CASE_INSENSITIVE）",
        [
            RequestItem(
                name="test_uppercase_ms_always_hint — MS00000000000001",
                method="POST",
                url_path="{{p2424V2DetailsPath}}",
                body=DetailsBodyRaw("p2424OrderIdMsTypical"),
                headers=BearerEpassJsonHeaders(),
                description="大写 MS 前缀恒为 500.000.024 信封。",
                test_lines=["p2424AssertMsUsageOrderHintEnvelope(pm, 'PAPI-2424-upper-MS');"],
            ),
            RequestItem(
                name="test_lowercase_ms_depends_on_env — ms00000000000001",
                method="POST",
                url_path="{{p2424V2DetailsPath}}",
                body=DetailsBodyRaw("p2424OrderIdLowerMs"),
                headers=BearerEpassJsonHeaders(),
                description=(
                    "小写 ms：集合变量 DP_P2424_MS_PREFIX_CASE_INSENSITIVE 为 1/true/yes/on 时期望与大写相同；否则期望非 MS 专用码/全文 msg。"
                ),
                test_lines=["p2424AssertLowercaseMsPrefixBehavior(pm, 'PAPI-2424-lower-ms');"],
            ),
        ],
    )

    v1v2_folder: JsonObject = Folder(
        "04 tc-P2-EPASS-002（V1/V2 路径对拍，需配置 p2424V1DetailsPath）",
        [
            RequestItem(
                name="test_v1_v2_ms_prefix_same_envelope — V1",
                method="POST",
                url_path="{{p2424V1DetailsPath}}",
                body=DetailsBodyRaw("p2424OrderIdMsTypical"),
                headers=BearerEpassJsonHeaders(),
                description="须将 p2424V1DetailsPath 设为网关真实 V1 路径（如 /v1/orders/ePasses/details）。",
                test_lines=["p2424AssertMsUsageOrderHintEnvelope(pm, 'PAPI-2424-V1');"],
            ),
            RequestItem(
                name="test_v1_v2_ms_prefix_same_envelope — V2",
                method="POST",
                url_path="{{p2424V2DetailsPath}}",
                body=DetailsBodyRaw("p2424OrderIdMsTypical"),
                headers=BearerEpassJsonHeaders(),
                description="默认 V2；可用 DP_P2424_V2_ORDERS_EPASSES_DETAILS_PATH 覆盖路径时同步改集合变量。",
                test_lines=["p2424AssertMsUsageOrderHintEnvelope(pm, 'PAPI-2424-V2');"],
            ),
        ],
    )

    info: JsonObject = {
        "_postman_id": _POSTMAN_ID,
        "name": "PAPI-2424 ePasses/details MS 订单提示（对齐 test_papi_2424 + papi2424_helpers）",
        "description": (
            "由 GeneratePostmanCollectionPapi2424.py 生成；Tests 内联 BuildP2424JsHelpersLines。\n"
            "环境变量对照：DP_EPASS_PROGRAM_ID→epassProgramId，DP_EPASS_CLIENT_ID→epassClientId，"
            "DP_EPASS_CLIENT_SECRET→epassClientSecret；DP_P2424_USAGE_ORDER_ID→p2424UsageOrderId；"
            "DP_P2424_V1_ORDERS_EPASSES_DETAILS_PATH→p2424V1DetailsPath；"
            "DP_P2424_V2_ORDERS_EPASSES_DETAILS_PATH→p2424V2DetailsPath；"
            "DP_P2424_MS_PREFIX_CASE_INSENSITIVE 同名集合变量。"
        ),
        "schema": POSTMAN_SCHEMA,
    }

    variables: List[JsonObject] = [
        {"key": "baseUrl", "value": "https://developer-sandbox.dragonpass.com/api"},
        {"key": "epassProgramId", "value": ""},
        {"key": "epassClientId", "value": ""},
        {"key": "epassClientSecret", "value": ""},
        {"key": "epassTokenRequestBearer", "value": ""},
        {"key": "accessToken", "value": ""},
        {"key": "p2424V2DetailsPath", "value": "/v2/orders/ePasses/details"},
        {"key": "p2424V1DetailsPath", "value": "/v1/orders/ePasses/details"},
        {"key": "p2424OrderIdMsShort", "value": "MS"},
        {"key": "p2424OrderIdMsTypical", "value": "MS00000000000001"},
        {"key": "p2424OrderIdLowerMs", "value": "ms00000000000001"},
        {"key": "p2424OrderIdSubstringDp", "value": "DP000MS00000001"},
        {"key": "p2424OrderIdSubstringSl", "value": "SL20260129BBMSXV9"},
        {"key": "p2424UsageOrderId", "value": ""},
        {"key": "DP_P2424_MS_PREFIX_CASE_INSENSITIVE", "value": ""},
    ]

    root: JsonObject = {
        "info": info,
        "variable": variables,
        "item": [auth_folder, ms_folder, non_ms_folder, case_folder, v1v2_folder],
    }
    return root


def Main() -> None:
    out_path: Path = Path(__file__).resolve().parent / OUT_NAME
    payload: JsonObject = BuildCollection()
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    Main()
