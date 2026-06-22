"""
生成 Resource Details 全量扫描 Postman Collection v2.1 JSON。

对齐手工 sandbox 核对场景：

- **module=1**：分页拉列表 → 详情 ``prebookingPolicy.prebookingRequiredInfo === [1, 2]``
  （可选 26 语种 i18n 扫描）
- **module=2/3/4/6/7/8/11**：分页拉列表 → 详情 ``code === 0``（en-US）

扫描在后置脚本内用 ``pm.sendRequest`` 串行完成（非逐条静态 HTTP 步骤）。

用法（仓库根目录）::

    python api-testcases/api_tests/postman/GeneratePostmanCollectionResourceDetailsScan.py

环境变量对齐 ``env/.env.canary`` 中 ``DP_MEMBERSHIP_*``（Program 1919256841868288）。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Final, List, Sequence

from collection_builder_common import (
    AuthJsonHeaders,
    BearerJsonHeaders,
    CollectionVariable,
    Folder,
    Lines_Step,
    POSTMAN_SCHEMA,
    PurposeName,
    RequestItem,
    WriteCollectionJson,
)

JsonObject = Dict[str, object]

COLLECTION_DISPLAY_NAME: Final[str] = "Resource Details · 全量扫描（prebookingRequiredInfo / code=0）"
OUT_NAME: Final[str] = "Resource-Details-Scan.postman_collection.json"
ENV_OUT_NAME: Final[str] = "Resource-Details-Scan-sandbox.postman_environment.json"

I18N_LANGUAGES: Final[tuple[str, ...]] = (
    "en-US",
    "ja-JP",
    "de-DE",
    "es-ES",
    "fr-FR",
    "it-IT",
    "pl-PL",
    "pt-PT",
    "ru-RU",
    "th-TH",
    "uk-UA",
    "vi-VN",
    "ko-KR",
    "es-419",
    "fr-CA",
    "ar-SA",
    "ro-RO",
    "bs-BA",
    "sr-SP",
    "sr-ME",
    "hr-HR",
    "nl-NL",
    "el-GR",
    "si-SI",
    "he-IL",
    "hu-HU",
)

CODE0_MODULES: Final[tuple[int, ...]] = (2, 3, 4, 6, 7, 8, 11)
EXPECTED_PREBOOKING_REQUIRED_INFO: Final[List[int]] = [1, 2]


def BuildResourceDetailsScanJsHelpersLines() -> List[str]:
    """集合级公共 JS：列表分页、详情扫描、断言汇总。"""
    langs_json = json.dumps(list(I18N_LANGUAGES))
    modules_json = json.dumps(list(CODE0_MODULES))
    expected_json = json.dumps(EXPECTED_PREBOOKING_REQUIRED_INFO)
    js = rf"""
var RD_I18N_LANGUAGES = {langs_json};
var RD_CODE0_MODULES = {modules_json};
var RD_EXPECTED_PREBOOKING_REQUIRED_INFO = {expected_json};

function rdIsCodeZero(env) {{
  if (!env || typeof env !== 'object') return false;
  if (!Object.prototype.hasOwnProperty.call(env, 'code')) return true;
  var c = env.code;
  return c === 0 || c === '0';
}}
function rdGetInnerData(root) {{
  if (!root || typeof root !== 'object') return null;
  var d = root.data;
  if (d !== undefined && d !== null) return d;
  return null;
}}
function rdParseJsonResponse(res) {{
  try {{
    return res.json();
  }} catch (e) {{
    return {{ code: -1, msg: 'response not json: ' + String(e) }};
  }}
}}
function rdBuildAuthHeaders() {{
  var auth = pm.variables.replaceIn('{{{{accessToken}}}}');
  return [
    {{ key: 'X-Program-ID', value: pm.variables.replaceIn('{{{{ProgramID}}}}') }},
    {{ key: 'x-version', value: pm.variables.replaceIn('{{{{x-version}}}}') }},
    {{ key: 'X-Request-ID', value: pm.variables.replaceIn('{{{{$guid}}}}') }},
    {{ key: 'Authorization', value: 'Bearer ' + auth }},
    {{ key: 'Accept', value: '*/*' }},
    {{ key: 'Content-Type', value: 'application/json' }}
  ];
}}
function rdBuildGetRequest(path) {{
  var base = pm.variables.replaceIn('{{{{baseUrl}}}}');
  return {{ url: base + path, method: 'GET', header: rdBuildAuthHeaders() }};
}}
function rdCollectResourceIds(data) {{
  var ids = [];
  var resources = (data && data.resources) || {{}};
  ['transportHubResources', 'lifestyleResources'].forEach(function (key) {{
    var arr = resources[key] || [];
    for (var i = 0; i < arr.length; i++) {{
      var rid = arr[i] && (arr[i].resourceId || arr[i].id);
      if (rid) ids.push(String(rid));
    }}
  }});
  return ids;
}}
function rdUnique(arr) {{
  var seen = {{}};
  var out = [];
  for (var i = 0; i < arr.length; i++) {{
    var v = arr[i];
    if (!seen[v]) {{ seen[v] = true; out.push(v); }}
  }}
  return out;
}}
function rdGetPageSize() {{
  var raw = String(pm.variables.get('scanPageSize') || '100').trim();
  var n = parseInt(raw, 10);
  return isNaN(n) || n < 1 ? 100 : n;
}}
function rdGetMaxDetails() {{
  var raw = String(pm.variables.get('scanMaxDetails') || '0').trim();
  var n = parseInt(raw, 10);
  return isNaN(n) || n < 0 ? 0 : n;
}}
function rdSendRequestAsync(req) {{
  return new Promise(function (resolve, reject) {{
    pm.sendRequest(req, function (err, res) {{
      if (err) return reject(err);
      resolve(res);
    }});
  }});
}}
function rdFetchListPage(module, pageNumber, pageSize) {{
  var path = '/v2/resources?module=' + module + '&pageNumber=' + pageNumber + '&pageSize=' + pageSize;
  return rdSendRequestAsync(rdBuildGetRequest(path)).then(function (res) {{
    return rdParseJsonResponse(res);
  }});
}}
function rdFetchAllResourceIds(module) {{
  var pageSize = rdGetPageSize();
  return rdFetchListPage(module, 1, pageSize).then(function (first) {{
    if (!rdIsCodeZero(first)) {{
      throw new Error('list page 1 code!=0 module=' + module + ' msg=' + (first.msg || first.errCode || ''));
    }}
    var data = rdGetInnerData(first) || {{}};
    var ids = rdCollectResourceIds(data);
    var pag = data.pagination || {{}};
    var total = parseInt(pag.totalNumber, 10);
    if (isNaN(total)) total = ids.length;
    var totalPages = Math.max(1, Math.ceil(total / pageSize));
    var chain = Promise.resolve();
    for (var p = 2; p <= totalPages; p++) {{
      (function (page) {{
        chain = chain.then(function () {{
          return rdFetchListPage(module, page, pageSize).then(function (env) {{
            if (!rdIsCodeZero(env)) {{
              throw new Error('list page ' + page + ' code!=0 module=' + module);
            }}
            var inner = rdGetInnerData(env) || {{}};
            ids = ids.concat(rdCollectResourceIds(inner));
          }});
        }});
      }})(p);
    }}
    return chain.then(function () {{ return rdUnique(ids); }});
  }});
}}
function rdFetchDetail(module, resourceId, language) {{
  var path = '/v2/resources/' + encodeURIComponent(resourceId)
    + '?module=' + module + '&language=' + encodeURIComponent(language) + '&fallbackAllowed=true';
  return rdSendRequestAsync(rdBuildGetRequest(path)).then(function (res) {{
    return rdParseJsonResponse(res);
  }});
}}
function rdFormatFailureDetail(failure) {{
  return JSON.stringify(failure, null, 2);
}}
function rdPrintCodeNonZeroDetail(module, language, resourceId, env) {{
  var detail = {{
    resourceId: resourceId,
    module: module,
    language: language,
    code: env && env.code,
    msg: (env && (env.msg || env.errCode)) || '',
    response: env
  }};
  console.error('[code!=0] ' + rdFormatFailureDetail(detail));
  return detail;
}}
function rdPrintPrebookingFailureDetail(module, language, resourceId, env, reason) {{
  var detail = {{
    resourceId: resourceId,
    module: module,
    language: language,
    reason: reason,
    code: env && env.code,
    msg: (env && (env.msg || env.errCode)) || '',
    response: env
  }};
  console.error('[prebookingRequiredInfo!=expected] ' + rdFormatFailureDetail(detail));
  return detail;
}}
function rdAssertPrebookingRequiredInfo(env, resourceId, language) {{
  if (!rdIsCodeZero(env)) {{
    rdPrintPrebookingFailureDetail(1, language, resourceId, env, env.msg || env.errCode || 'code!=0');
    return {{ ok: false, resourceId: resourceId, language: language, reason: env.msg || env.errCode || 'code!=0' }};
  }}
  var body = rdGetInnerData(env) || {{}};
  var pol = body.prebookingPolicy;
  var val = pol && pol.prebookingRequiredInfo;
  if (!Array.isArray(val)) {{
    rdPrintPrebookingFailureDetail(1, language, resourceId, env, 'missing prebookingPolicy.prebookingRequiredInfo');
    return {{ ok: false, resourceId: resourceId, language: language, reason: 'missing prebookingPolicy.prebookingRequiredInfo' }};
  }}
  var expected = RD_EXPECTED_PREBOOKING_REQUIRED_INFO;
  if (val.length !== expected.length) {{
    rdPrintPrebookingFailureDetail(1, language, resourceId, env, 'prebookingRequiredInfo=' + JSON.stringify(val));
    return {{ ok: false, resourceId: resourceId, language: language, reason: 'prebookingRequiredInfo=' + JSON.stringify(val) }};
  }}
  for (var i = 0; i < expected.length; i++) {{
    if (val[i] !== expected[i]) {{
      rdPrintPrebookingFailureDetail(1, language, resourceId, env, 'prebookingRequiredInfo=' + JSON.stringify(val));
      return {{ ok: false, resourceId: resourceId, language: language, reason: 'prebookingRequiredInfo=' + JSON.stringify(val) }};
    }}
  }}
  return {{ ok: true }};
}}
function rdScanModulePrebooking(module, languages, label) {{
  return rdFetchAllResourceIds(module).then(function (ids) {{
    var maxDetails = rdGetMaxDetails();
    if (maxDetails > 0) ids = ids.slice(0, maxDetails);
    var failures = [];
    var okCount = 0;
    var chain = Promise.resolve();
    languages.forEach(function (lang) {{
      chain = chain.then(function () {{
        var langChain = Promise.resolve();
        ids.forEach(function (rid) {{
          langChain = langChain.then(function () {{
            return rdFetchDetail(module, rid, lang).then(function (env) {{
              var verdict = rdAssertPrebookingRequiredInfo(env, rid, lang);
              if (verdict.ok) okCount += 1;
              else failures.push(verdict);
            }});
          }});
        }});
        return langChain;
      }});
    }});
    return chain.then(function () {{
      return {{ label: label, module: module, languages: languages, totalIds: ids.length, okCount: okCount, failures: failures }};
    }});
  }});
}}
function rdScanModuleCodeZero(module, language, label) {{
  return rdFetchAllResourceIds(module).then(function (ids) {{
    var maxDetails = rdGetMaxDetails();
    if (maxDetails > 0) ids = ids.slice(0, maxDetails);
    var failures = [];
    var okCount = 0;
    var chain = Promise.resolve();
    ids.forEach(function (rid) {{
      chain = chain.then(function () {{
        return rdFetchDetail(module, rid, language).then(function (env) {{
          if (rdIsCodeZero(env)) {{
            okCount += 1;
          }} else {{
            failures.push(rdPrintCodeNonZeroDetail(module, language, rid, env));
          }}
        }});
      }});
    }});
    return chain.then(function () {{
      return {{ label: label, module: module, language: language, totalIds: ids.length, okCount: okCount, failures: failures }};
    }});
  }});
}}
function rdRunScanPromise(runScanFn, label) {{
  return runScanFn().then(function (summary) {{
    pm.collectionVariables.set('scanLastSummary', JSON.stringify(summary));
    pm.test(label + ': 扫描完成', function () {{
      pm.expect(summary.failures.length, 'failure count').to.eql(0);
    }});
    if (summary.failures.length) {{
      console.error(label + ': 非预期共 ' + summary.failures.length + ' 条（资源详情见上方 [code!=0] / [prebookingRequiredInfo!=expected] 输出）');
    }} else {{
      console.log(label + ': 全部通过，共 ' + summary.okCount + ' 条（code=0 / 断言符合，无逐条输出）');
    }}
  }}).catch(function (err) {{
    pm.test(label + ': 扫描异常', function () {{
      throw err;
    }});
  }});
}}
"""
    return [ln for ln in js.strip().split("\n")]


def _JsHelpers() -> List[str]:
    return BuildResourceDetailsScanJsHelpersLines()


def _AuthStep() -> JsonObject:
    return RequestItem(
        js_helpers=_JsHelpers,
        name=PurposeName("鉴权获取 accessToken", "Auth", "POST", "/auth/token"),
        method="POST",
        url_path="/v2/auth/token",
        body=json.dumps({"clientId": "{{clientId}}", "secret": "{{secret}}"}, indent=2),
        headers=AuthJsonHeaders(),
        description="写入集合变量 accessToken；Program 对齐 DP_MEMBERSHIP_PROGRAM_ID。",
        save_token=True,
        test_lines=Lines_Step("Auth", ["pm.test('Auth: HTTP 200', function () { pm.response.to.have.status(200); });"]),
    )


def _ScanPrebookingStep(step_id: str, purpose: str, *, i18n: bool) -> JsonObject:
    if i18n:
        run_lines = [
            "rdRunScanPromise(function () {",
            "  return rdScanModulePrebooking(1, RD_I18N_LANGUAGES.slice(), '" + step_id + "');",
            "}, '" + step_id + "');",
        ]
        desc = (
            "module=1 全量列表 + 26 语种详情；断言 "
            "`prebookingPolicy.prebookingRequiredInfo === [1,2]`。"
            "全量扫描耗时较长，可设 scanMaxDetails 抽样。"
        )
    else:
        run_lines = [
            "rdRunScanPromise(function () {",
            "  return rdScanModulePrebooking(1, ['en-US'], '" + step_id + "');",
            "}, '" + step_id + "');",
        ]
        desc = "module=1 全量列表 + en-US 详情；断言 prebookingPolicy.prebookingRequiredInfo === [1,2]。"

    return RequestItem(
        js_helpers=_JsHelpers,
        name=PurposeName(purpose, step_id, "GET", "/resources scan"),
        method="GET",
        url_path="/v2/resources?module=1&pageNumber=1&pageSize={{scanPageSize}}",
        body=None,
        headers=BearerJsonHeaders(),
        description=desc,
        test_lines=run_lines,
    )


def _ScanCodeZeroStep(step_id: str, purpose: str, module: int) -> JsonObject:
    run_lines = [
        "rdRunScanPromise(function () {",
        "  return rdScanModuleCodeZero(" + str(module) + ", 'en-US', '" + step_id + "');",
        "}, '" + step_id + "');",
    ]
    return RequestItem(
        js_helpers=_JsHelpers,
        name=PurposeName(purpose, step_id, "GET", "/resources?module=" + str(module)),
        method="GET",
        url_path="/v2/resources?module=" + str(module) + "&pageNumber=1&pageSize={{scanPageSize}}",
        body=None,
        headers=BearerJsonHeaders(),
        description=(
            f"module={module} 全量列表 + en-US 详情；断言 code=0。"
        ),
        test_lines=run_lines,
    )


def BuildCollection() -> JsonObject:
    code0_items: List[JsonObject] = []
    module_purpose: Dict[int, str] = {
        2: "FastTrack 详情 code=0",
        3: "Set Meal 详情 code=0",
        4: "Dining 详情 code=0",
        6: "Fitness 详情 code=0",
        7: "eSIM 详情 code=0",
        8: "Fitness/eSIM 变体 详情 code=0",
        11: "Local Offer 详情 code=0",
    }
    for mod in CODE0_MODULES:
        step_id = "SCAN-M" + str(mod)
        code0_items.append(_ScanCodeZeroStep(step_id, module_purpose.get(mod, "详情 code=0"), mod))

    return {
        "info": {
            "name": COLLECTION_DISPLAY_NAME,
            "description": (
                "由 GeneratePostmanCollectionResourceDetailsScan.py 生成。\n\n"
                "**扫描方式**：每条「SCAN-*」步骤在后置脚本内用 pm.sendRequest 分页拉列表并逐条查详情。\n"
                "**变量**：ProgramID / clientId / secret / x-version / scanPageSize(默认100) / "
                "scanMaxDetails(0=全量，>0 抽样)。\n"
                "**对齐 sandbox 手工核对**：module=1 prebookingRequiredInfo [1,2]；"
                "module 2/3/4/6/7/8/11 详情 code=0。"
            ),
            "schema": POSTMAN_SCHEMA,
        },
        "item": [
            Folder("00 Auth", [_AuthStep()], description="先执行 Auth 写入 accessToken。"),
            Folder(
                "P1 · module=1 · prebookingRequiredInfo",
                [
                    _ScanPrebookingStep(
                        "SCAN-M1-EN",
                        "module=1 全量 prebookingRequiredInfo [1,2]（en-US）",
                        i18n=False,
                    ),
                    _ScanPrebookingStep(
                        "SCAN-M1-I18N",
                        "module=1 全量 prebookingRequiredInfo [1,2]（26 语种）",
                        i18n=True,
                    ),
                ],
                description="Lounge module=1；断言 prebookingPolicy.prebookingRequiredInfo。",
            ),
            Folder(
                "P1 · modules · detail code=0（en-US）",
                code0_items,
                description="各 module 独立 SCAN 步骤；详情 language=en-US。",
            ),
        ],
        "variable": [
            CollectionVariable("baseUrl", "https://developer-sandbox.dragonpass.com/api"),
            CollectionVariable("ProgramID", ""),
            CollectionVariable("clientId", ""),
            CollectionVariable("secret", ""),
            CollectionVariable("x-version", "canary"),
            CollectionVariable("accessToken", ""),
            CollectionVariable("scanPageSize", "100"),
            CollectionVariable("scanMaxDetails", "0"),
            CollectionVariable("scanLastSummary", ""),
        ],
    }


def BuildEnvironmentJson() -> JsonObject:
    return {
        "id": "resource-details-scan-sandbox-env",
        "name": "Resource Details Scan sandbox（DP_MEMBERSHIP_*）",
        "values": [
            {"key": "baseUrl", "value": "https://developer-sandbox.dragonpass.com/api", "enabled": True},
            {"key": "ProgramID", "value": "", "enabled": True},
            {"key": "clientId", "value": "", "enabled": True},
            {"key": "secret", "value": "", "enabled": True},
            {"key": "x-version", "value": "canary", "enabled": True},
            {"key": "scanPageSize", "value": "100", "enabled": True},
            {"key": "scanMaxDetails", "value": "0", "enabled": True},
        ],
        "_postman_variable_scope": "environment",
        "_postman_exported_using": "GeneratePostmanCollectionResourceDetailsScan.py",
    }


def Main() -> None:
    script_dir = Path(__file__).resolve().parent
    collection = BuildCollection()
    out_path = script_dir / OUT_NAME
    env_path = script_dir / ENV_OUT_NAME
    WriteCollectionJson(str(out_path), collection)
    WriteCollectionJson(str(env_path), BuildEnvironmentJson())
    print("Wrote", out_path)
    print("Wrote", env_path)


if __name__ == "__main__":
    Main()
