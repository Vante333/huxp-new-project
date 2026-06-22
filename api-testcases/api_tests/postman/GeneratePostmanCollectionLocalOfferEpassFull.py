"""
生成 Local Offer ePass **Full (pytest-sync)** Postman Collection v2.1 JSON。

覆盖 ``tests/features/test_local_offer_epass.py`` 主链路 E2E 与
``tests/features/local_offer_epass/`` 分模块用例（与 P0 核心集合并存，不写入 P0 文件）。

用法（仓库根目录）::

    python api-testcases/api_tests/postman/GeneratePostmanCollectionLocalOfferEpassFull.py
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Final, List, Optional, Sequence

JsonObject = Dict[str, Any]

COLLECTION_DISPLAY_NAME: Final[str] = "Local Offer ePass · Full (pytest-sync)"
COLLECTION_P1_FULL_DISPLAY_NAME: Final[str] = "Local Offer ePass · P1 Full (pytest-sync)"
OUT_NAME: Final[str] = "LocalOffer-ePass-full-pytest-sync.postman_collection.json"
APIFOX_IMPORT_NAME: Final[str] = "LocalOffer-ePass-full-pytest-sync.apifox-2.7.43-import.json"
# 兼容旧导入习惯（100+ HTTP 步骤 · 与 OUT_NAME 同内容）
FULL_LEGACY_OUT_NAMES: Final[tuple[str, ...]] = (
    "LocalOffer-ePass-P1-full.postman_collection.json",
    "LocalOffer-ePass-full.postman_collection.json",
)
FULL_LEGACY_APIFOX_NAME: Final[str] = "LocalOffer-ePass-P1-full.apifox-2.7.43-import.json"
INVALID_TOKEN: Final[str] = "00000000-0000-0000-0000-000000000000"
FAKE_ORDER_ID: Final[str] = "00000000-0000-0000-0000-000000000099"
PAST_PREBOOKING_DATE: Final[str] = "2020-01-01T10:30"

# 以下 pytest 用例不写入 Full 集合（索引见 postman/README.md 与 testcases 自动化对应表）
PYTEST_ONLY_NOT_IN_FULL: Final[str] = (
    "testcases/2026Q2_SP3/LocalOffer订单相关-epass-自动化用例与pytest对应表.md"
)

_EXTRA_JS: Final[str] = r"""
function loSaveFirstResourceIdFromList(label) {
  pm.test(label + ': 解析首个 resourceId（lifestyleResources/transportHubResources）', function () {
    var data = loGetInnerData(pm.response.json());
    var list = loCollectResourcesEntries(data);
    pm.expect(list.length, 'resources 条目').to.be.above(0);
    var rid = list[0].resourceId || list[0].id;
    pm.expect(rid).to.be.a('string').and.not.empty;
    pm.collectionVariables.set('discoveredResourceId', String(rid));
  });
}
function loSaveFirstCountryFromList(label) {
  pm.test(label + ': 解析首个 countryOrRegion', function () {
    var data = loGetInnerData(pm.response.json());
    var list = loCollectResourcesEntries(data);
    var code = null;
    for (var i = 0; i < list.length; i++) {
      var item = list[i];
      if (!item) continue;
      var loc = item.locationInfo || item.location;
      code = (loc && loc.countryOrRegion) || item.countryOrRegion || item.country;
      if (code) break;
    }
    if (!code) {
      console.warn(label + ': 未解析 countryOrRegion，后续步骤可能需手填');
      return;
    }
    pm.collectionVariables.set('discoveredCountryOrRegion', String(code));
  });
}
function loManualPytestOnly(label, pytestRef) {
  pm.test(label + ': 请用 pytest 跑完整场景', function () {
    console.warn('Postman 仅索引步骤；权威: pytest ' + pytestRef);
  });
}
function loNoteSaasManual(label) {
  pm.test(label + ': SaaS 人工核对', function () {
    console.warn(label + ': 接口成功后请在 SaaS 核对权益；pytest 带 needs_saas_manual_verify');
  });
}
"""


def _LoadLoGeneratorModule() -> Any:
    script_dir = Path(__file__).resolve().parent
    path = script_dir / "GeneratePostmanCollectionLocalOfferEpass.py"
    spec = importlib.util.spec_from_file_location("lo_epass_gen", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载生成器模块: {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["lo_epass_gen"] = mod
    spec.loader.exec_module(mod)
    return mod


lo = _LoadLoGeneratorModule()

_ORIGINAL_JS_BUILDER: Callable[[], List[str]] = lo.BuildLocalOfferJsHelpersLines


def BuildFullJsHelpersLines() -> List[str]:
    return _ORIGINAL_JS_BUILDER() + [ln for ln in _EXTRA_JS.strip().split("\n")]


lo.BuildLocalOfferJsHelpersLines = BuildFullJsHelpersLines  # type: ignore[method-assign]


_RESOURCES_QUERY_11: Final[Dict[str, str]] = {"module": "11", "pageNumber": "1", "pageSize": "50"}
_RESOURCES_QUERY_8: Final[Dict[str, str]] = {"module": "8", "pageNumber": "1", "pageSize": "10"}


@dataclass
class StepSpec:
    """单条 Postman 请求规格。"""

    purpose: str
    step_id: str
    method: str
    url_path: str
    path_hint: str = ""
    name: str = ""
    body: Optional[str] = None
    test_lines: List[str] = field(default_factory=list)
    prerequest_lines: List[str] = field(default_factory=list)
    description: str = ""
    save_token: bool = False
    url_query: Optional[Dict[str, str]] = None


def _ShortPathHint(url_path: str) -> str:
    """列表展示用路径简写。"""
    clean = url_path.split("?", 1)[0]
    return clean if len(clean) <= 48 else clean


def _DisplayName(spec: StepSpec) -> str:
    if spec.name.strip():
        return spec.name.strip()
    hint = spec.path_hint.strip() or _ShortPathHint(spec.url_path)
    return lo.PurposeName(spec.purpose, spec.step_id, spec.method, hint)


def _PrebookingBody() -> str:
    return json.dumps(
        {
            "module": 11,
            "ePassId": "{{ePassId}}",
            "extra": {"prebookingToken": "{{prebookingToken}}"},
            "async": False,
        },
        ensure_ascii=False,
        indent=2,
    )


def _BundleBody() -> str:
    return json.dumps(
        {
            "module": 11,
            "clientUserId": "{{clientUserId}}",
            "extra": {"prebookingToken": "{{prebookingToken}}"},
            "async": False,
        },
        ensure_ascii=False,
        indent=2,
    )


def _ErrCodesJson(codes: Sequence[str]) -> str:
    return json.dumps(list(codes))


def _CreatePayload(**allowed_resources: object) -> str:
    payload: JsonObject = {
        "module": 11,
        "clientUserId": "{{clientUserId}}",
        "extra": {
            "firstName": lo.CREATE_FIRST_NAME,
            "lastName": lo.CREATE_LAST_NAME,
            "expirationDate": lo.CREATE_EXPIRATION_DATE,
            "availableUsages": lo.CREATE_AVAILABLE_USAGES,
            "allowedResources": {
                "resourceIds": [],
                "iata": [],
                "countryOrRegion": [],
            },
        },
    }
    ar = payload["extra"]["allowedResources"]  # type: ignore[index]
    if isinstance(ar, dict):
        ar.update(allowed_resources)
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _GetResourcesStep(
    step_id: str,
    *,
    module: int,
    purpose: str,
    extra_tests: Optional[List[str]] = None,
) -> StepSpec:
    query = dict(_RESOURCES_QUERY_11 if module == 11 else _RESOURCES_QUERY_8)
    tests = ["loAssertHttpBusinessOk('" + step_id + "');"]
    if extra_tests:
        tests.extend(extra_tests)
    return StepSpec(
        purpose=purpose,
        step_id=step_id,
        method="GET",
        url_path="/v2/resources",
        path_hint="/v2/resources",
        url_query=query,
        test_lines=tests,
        description=f"``GET /v2/resources`` module={module}（query 参数）。",
    )


def _Step(spec: StepSpec) -> JsonObject:
    return lo.RequestItem(
        name=_DisplayName(spec),
        method=spec.method,
        url_path=spec.url_path,
        body=spec.body,
        headers=lo.BearerJsonHeaders(),
        description=spec.description,
        save_token=spec.save_token,
        test_lines=spec.test_lines,
        prerequest_lines=spec.prerequest_lines or None,
        url_query=spec.url_query,
    )


def _AuthStep() -> JsonObject:
    return lo.RequestItem(
        name=lo.PurposeName("鉴权获取 accessToken", "Auth", "POST", "/auth/token"),
        method="POST",
        url_path="/v2/auth/token",
        body=json.dumps({"clientId": "{{clientId}}", "secret": "{{secret}}"}, indent=2),
        headers=lo.AuthJsonHeaders(),
        description="鉴权；写入 accessToken。",
        save_token=True,
        test_lines=lo.Lines_Auth(),
        prerequest_lines=lo.Prerequest_EnsurePrebookingDate(),
    )


def _CancelPurchaseStep(
    step_id: str,
    *,
    purpose: str = "取消 MS 购买单",
    extra_test_lines: Optional[List[str]] = None,
) -> StepSpec:
    tests = ["loAssertCancelOrderSuccess('" + step_id + "');"]
    if extra_test_lines:
        tests.extend(extra_test_lines)
    return StepSpec(
        purpose=purpose,
        step_id=step_id,
        method="PATCH",
        url_path="/v2/orders",
        path_hint="/orders",
        body=json.dumps({"status": 3, "orderId": "{{purchaseOrderId}}"}, indent=2),
        test_lines=tests,
        description="``CancelPurchaseOrderAndVerifyPostCancelRetrieve`` 收尾。",
    )


def _CancelUsageStep(step_id: str, *, purpose: str = "取消 usage 预订单") -> StepSpec:
    return StepSpec(
        purpose=purpose,
        step_id=step_id,
        method="PATCH",
        url_path="/v2/orders",
        path_hint="/orders",
        body=json.dumps({"status": 3, "orderId": "{{usageOrderId}}"}, indent=2),
        test_lines=["loAssertCancelOrderSuccess('" + step_id + "');"],
        description="``CancelUsageOrderAndVerifyPostCancelRetrieve``。",
    )


_ESIM_RESOURCE_SAVE_JS: Final[str] = "loSaveFirstEsimResourceFromList('{label}');"

APIFOX_NEGATIVE_STEP_HINT: Final[str] = (
    "Apifox：负向/HTTP400 步骤请关闭本步「校验响应」（项目设置→响应校验→测试步骤），"
    "避免「HTTP状态码应当是200」与脚本断言重复。"
)


def _MembershipRegisterStep(step_id: str, *, purpose: str = "注册会籍获取 membershipId") -> StepSpec:
    return StepSpec(
        purpose=purpose,
        step_id=step_id,
        method="POST",
        url_path="/v2/memberships",
        path_hint="/memberships",
        body=lo.MEMBERSHIP_REGISTER_PAYLOAD,
        test_lines=[f"loAssertMembershipRegisterSuccess('{step_id}');"],
        description="``POST /v2/memberships`` · 写入 ``membershipId``（对齐 pytest ``ResolveMembershipIdForAvailabilityOrSkip`` 前置）。",
    )


def _CreateEpassStep(
    step_id: str,
    *,
    purpose: str,
    payload: str,
    assert_create: bool = True,
    expect_business_failure: Optional[Sequence[str]] = None,
    failure_msg_from_request: bool = False,
    accept_http_400: bool = False,
    save_first_epass_id: bool = False,
) -> StepSpec:
    tests: List[str] = []
    desc_extra = ""
    if expect_business_failure:
        accept_arg = "true" if accept_http_400 else "false"
        tests.append(
            f"loAssertBusinessFailure('{step_id}', {_ErrCodesJson(expect_business_failure)}, {accept_arg});"
        )
        if failure_msg_from_request:
            tests.append(f"loAssertBusinessFailureMsgContainsRequestResourceIds('{step_id}');")
        desc_extra = APIFOX_NEGATIVE_STEP_HINT
    else:
        tests.append(f"loAssertHttpBusinessOk('{step_id}');")
        if assert_create:
            tests.append(f"loAssertCreateCoreFields('{step_id}');")
    if save_first_epass_id:
        tests.append(
            "pm.test('" + step_id + ": 固化 firstEPassId', function () {"
            "  pm.collectionVariables.set('firstEPassId', pm.collectionVariables.get('ePassId'));"
            "});"
        )
    return StepSpec(
        purpose=purpose,
        step_id=step_id,
        method="POST",
        url_path="/v2/orders/localOffers/ePasses",
        path_hint="/localOffers/ePasses",
        body=payload,
        prerequest_lines=lo.Prerequest_NewClientUserId(),
        test_lines=tests,
        description="``PostOrdersLocalOffersEPasses`` / ``CreateLocalOfferEpass``。" + desc_extra,
    )


def _AvailabilityStep(
    step_id: str,
    *,
    purpose: str,
    with_epass: bool,
    adult: int = 1,
    child: int = 0,
    extra_body: Optional[JsonObject] = None,
    expect_success: bool = True,
    failure_err_codes: Optional[Sequence[str]] = None,
) -> StepSpec:
    body: JsonObject = {
        "module": 11,
        "resourceId": "{{resourceId}}",
        "optionId": "{{optionId}}",
        "prebookingDate": lo.PREBOOKING_DATE_APIFOX,
        "adultCount": adult,
        "childCount": child,
    }
    if with_epass:
        body["ePassId"] = "{{ePassId}}"
    if extra_body:
        body.update(extra_body)
    prerequest = list(lo.Prerequest_SyncPrebookingDateFromApifox())
    uses_esim_vars = "{{esimResourceId}}" in json.dumps(body, ensure_ascii=False)
    if uses_esim_vars:
        prerequest.append(f"loPatchAvailabilityBodyEsimVars('{step_id}');")
    if expect_success:
        test_lines = [f"loAssertAvailabilitySuccess('{step_id}');"]
        desc = "``PostPrebookingAvailability`` / ``AssertPrebookingAvailabilitySuccess``。"
    else:
        codes = failure_err_codes or ["500.020.029"]
        test_lines = [f"loAssertBusinessFailure('{step_id}', {_ErrCodesJson(codes)});"]
        desc = "``PostPrebookingAvailability`` 负向。" + APIFOX_NEGATIVE_STEP_HINT
    if uses_esim_vars:
        desc += " 使用集合变量 ``esimResourceId``/``esimOptionId``（非 LO 的 resourceId）；可先跑 GET resources module=8。"
    return StepSpec(
        purpose=purpose,
        step_id=step_id,
        method="POST",
        url_path="/v2/resources/options/prebookings/availability",
        path_hint="/prebookings/availability",
        body=json.dumps(body, ensure_ascii=False, indent=2),
        prerequest_lines=prerequest,
        test_lines=test_lines,
        description=desc,
    )


def _PrebookStep(step_id: str, *, purpose: str, expect_success: bool = True) -> StepSpec:
    if expect_success:
        tests = [
            "loAssertHttpBusinessOk('" + step_id + "');",
            "loAssertPrebookingOrderSuccess('" + step_id + "');",
        ]
    else:
        tests = ["loAssertBusinessFailure('" + step_id + "', ['500.110.028','500.110.027','500.110.019']);"]
    return StepSpec(
        purpose=purpose,
        step_id=step_id,
        method="POST",
        url_path="/v2/orders/localOffers/ePasses/prebooking",
        path_hint="/ePasses/prebooking",
        body=_PrebookingBody(),
        test_lines=tests,
        description="``PostOrdersLocalOffersEPassesPrebooking``。",
    )


def _BundleStep(step_id: str, *, purpose: str, expect_success: bool = True) -> StepSpec:
    if expect_success:
        tests = [
            "loAssertHttpBusinessOk('" + step_id + "');",
            "loAssertBundleOrderSuccess('" + step_id + "');",
        ]
    else:
        tests = ["loAssertBusinessFailure('" + step_id + "', ['500.110.028','500.110.027']);"]
    return StepSpec(
        purpose=purpose,
        step_id=step_id,
        method="POST",
        url_path="/v2/orders/localOffers/ePasses/bundle",
        path_hint="/ePasses/bundle",
        body=_BundleBody(),
        prerequest_lines=lo.Prerequest_NewClientUserId(),
        test_lines=tests,
        description="``PostOrdersLocalOffersEPassesBundle``。",
    )


def _OptionalModuleFolder(name: str, items: List[JsonObject], description: str) -> Optional[JsonObject]:
    """模块下无可运行 HTTP 步骤时不输出文件夹。"""
    if not items:
        return None
    return lo.Folder(name, items, description)


def _TestFolder(
    folder_name: str,
    pytest_ref: str,
    steps: Sequence[StepSpec],
    *,
    folder_description: str = "",
) -> JsonObject:
    desc = folder_description or f"pytest: ``{pytest_ref}``"
    return lo.Folder(folder_name, [_Step(s) for s in steps], desc)


def BuildModuleCreateFolder() -> JsonObject:
    items: List[JsonObject] = [
        _TestFolder(
            "Create_WithMatchingResourceIds",
            "test_create.py::test_LocalOfferEpass_Create_WithMatchingResourceIds",
            [
                _GetResourcesStep(
                    "S01",
                    module=11,
                    purpose="拉取 module=11 资源并解析 resourceId",
                    extra_tests=["loSaveFirstResourceIdFromList('S01');"],
                ),
                _CreateEpassStep(
                    "S02",
                    purpose="限制 resourceIds 后创建成功",
                    payload=_CreatePayload(resourceIds=["{{discoveredResourceId}}"]),
                ),
                _CancelPurchaseStep("S03"),
            ],
        ),
        _TestFolder(
            "Create_WithMatchingCountryOrRegion",
            "test_create.py::test_LocalOfferEpass_Create_WithMatchingCountryOrRegion",
            [
                _GetResourcesStep(
                    "S01",
                    module=11,
                    purpose="拉取资源并解析 countryOrRegion",
                    extra_tests=["loSaveFirstCountryFromList('S01');"],
                ),
                _CreateEpassStep(
                    "S02",
                    purpose="限制 countryOrRegion 后创建成功",
                    payload=_CreatePayload(countryOrRegion=["{{discoveredCountryOrRegion}}"]),
                ),
                _CancelPurchaseStep("S03"),
            ],
        ),
        _TestFolder(
            "Create_IataRestrictionRejected",
            "test_create.py::test_LocalOfferEpass_Create_IataRestrictionRejected",
            [
                _CreateEpassStep(
                    "S01",
                    purpose="负向：iata 限制应拒绝",
                    payload=_CreatePayload(iata=["MAN"]),
                    expect_business_failure=["500.110.026"],
                ),
            ],
            folder_description="负向：期望 500.110.026。",
        ),
        _TestFolder(
            "Create_MixedModuleResourceIdsRejected",
            "test_create.py::test_LocalOfferEpass_Create_MixedModuleResourceIdsRejected",
            [
                _GetResourcesStep(
                    "S01",
                    module=11,
                    purpose="拉取 LO resourceId",
                    extra_tests=["loSaveFirstResourceIdFromList('S01');"],
                ),
                _GetResourcesStep(
                    "S02",
                    module=8,
                    purpose="拉取 eSIM resourceId",
                    extra_tests=[_ESIM_RESOURCE_SAVE_JS.format(label="S02")],
                ),
                _CreateEpassStep(
                    "S03",
                    purpose="负向：混合 LO+eSIM resourceIds",
                    payload=_CreatePayload(resourceIds=["{{discoveredResourceId}}", "{{esimResourceId}}"]),
                    expect_business_failure=["500.000.017"],
                    failure_msg_from_request=True,
                ),
            ],
            folder_description="负向：混合 module resourceIds。",
        ),
        _TestFolder(
            "Create_MultipleRestrictionsRejected",
            "test_create.py::test_LocalOfferEpass_Create_MultipleRestrictionsRejected",
            [
                _GetResourcesStep(
                    "S01",
                    module=11,
                    purpose="拉取 resourceId 与 countryOrRegion",
                    extra_tests=["loSaveFirstResourceIdFromList('S01');", "loSaveFirstCountryFromList('S01');"],
                ),
                _CreateEpassStep(
                    "S02",
                    purpose="负向：resourceIds+countryOrRegion 同时限制",
                    payload=_CreatePayload(
                        resourceIds=["{{discoveredResourceId}}"],
                        countryOrRegion=["{{discoveredCountryOrRegion}}"],
                    ),
                    expect_business_failure=["500.110.015"],
                ),
            ],
            folder_description="负向：500.110.015 / 500.110.026。",
        ),
        _TestFolder(
            "Create_ResourceIdsOverLimitRejected",
            "test_create.py::test_LocalOfferEpass_Create_ResourceIdsOverLimitRejected",
            [
                StepSpec(
                    purpose="负向：resourceIds 超过 30 条",
                    step_id="S01",
                    method="POST",
                    url_path="/v2/orders/localOffers/ePasses",
                    path_hint="/localOffers/ePasses",
                    body=_CreatePayload(
                        resourceIds=[f"R{i:05d}" for i in range(31)],
                    ),
                    prerequest_lines=lo.Prerequest_NewClientUserId(),
                    test_lines=["loAssertBusinessFailure('S01', ['500.110.002'], true);"],
                    description=APIFOX_NEGATIVE_STEP_HINT,
                ),
            ],
        ),
        _TestFolder(
            "Create_DuplicateClientUserIdRejected",
            "test_create.py::test_LocalOfferEpass_Create_DuplicateClientUserIdRejected",
            [
                _CreateEpassStep("S01", purpose="首次创建 ePass", payload=lo.CREATE_PAYLOAD_TEMPLATE),
                _CancelPurchaseStep("S02"),
                StepSpec(
                    purpose="负向：同 clientUserId 重复创建",
                    step_id="S03",
                    method="POST",
                    url_path="/v2/orders/localOffers/ePasses",
                    path_hint="/localOffers/ePasses",
                    body=json.dumps(
                        {
                            "module": 11,
                            "clientUserId": "{{clientUserId}}",
                            "extra": {
                                "firstName": "Dup",
                                "lastName": "User",
                                "expirationDate": lo.CREATE_EXPIRATION_DATE,
                                "availableUsages": lo.CREATE_AVAILABLE_USAGES,
                                "allowedResources": {"resourceIds": [], "iata": [], "countryOrRegion": []},
                            },
                        },
                        indent=2,
                    ),
                    test_lines=["loAssertBusinessFailure('S03', ['500.110.011','500.080.011']);"],
                ),
            ],
        ),
        _TestFolder(
            "Create_EsimResourceIdRejected",
            "test_create.py::test_LocalOfferEpass_Create_EsimResourceIdRejected",
            [
                _GetResourcesStep(
                    "S01",
                    module=8,
                    purpose="拉取 eSIM resourceId",
                    extra_tests=[_ESIM_RESOURCE_SAVE_JS.format(label="S01")],
                ),
                _CreateEpassStep(
                    "S02",
                    purpose="负向：仅 eSIM resourceId 创建 LO",
                    payload=_CreatePayload(resourceIds=["{{esimResourceId}}"]),
                    expect_business_failure=["500.000.017"],
                    failure_msg_from_request=True,
                ),
            ],
            folder_description="需先 S01 GET module=8 写入 esimResourceId（默认 GR0005901）。",
        ),
        _TestFolder(
            "Create_WithoutAllowedResources",
            "test_create.py::test_LocalOfferEpass_Create_WithoutAllowedResources",
            [
                _CreateEpassStep("S01", purpose="无 allowedResources 限制创建", payload=lo.CREATE_PAYLOAD_TEMPLATE),
                StepSpec(
                    purpose="创建后 orders 列表（可为空）",
                    step_id="S02",
                    method="POST",
                    url_path="/v2/orders/ePasses",
                    path_hint="/ePasses",
                    body=lo.OrdersListBody(),
                    test_lines=["loAssertHttpBusinessOk('S02');", "loAssertOrderListPagination('S02', true, true);"],
                ),
                _CancelPurchaseStep("S03"),
            ],
        ),
    ]
    return lo.Folder(
        "M01 · test_create.py",
        items,
        "CreateEpassOrder 正向/负向。",
    )


def BuildModulePrebookingFolder() -> JsonObject:
    return lo.Folder(
        "M02 · test_prebooking.py",
        [
            _TestFolder(
                "Prebooking_InvalidTokenRejected",
                "test_prebooking.py::test_LocalOfferEpass_Prebooking_InvalidTokenRejected",
                [
                    _CreateEpassStep("S01", purpose="创建 ePass", payload=lo.CREATE_PAYLOAD_TEMPLATE),
                    StepSpec(
                        purpose="负向：无效 prebookingToken 预约",
                        step_id="S02",
                        method="POST",
                        url_path="/v2/orders/localOffers/ePasses/prebooking",
                        path_hint="/ePasses/prebooking",
                        body=json.dumps(
                            {
                                "module": 11,
                                "ePassId": "{{ePassId}}",
                                "extra": {"prebookingToken": INVALID_TOKEN},
                                "async": False,
                            },
                            indent=2,
                        ),
                        test_lines=["loAssertBusinessFailure('S02', ['500.110.028']);"],
                    ),
                    _CancelPurchaseStep("S03"),
                ],
            ),
            _TestFolder(
                "Prebooking_ReuseTokenRejected",
                "test_prebooking.py::test_LocalOfferEpass_Prebooking_ReuseTokenRejected",
                [
                    _CreateEpassStep("S01", purpose="创建 ePass", payload=lo.CREATE_PAYLOAD_TEMPLATE),
                    _AvailabilityStep("S02", purpose="可用性取 token", with_epass=True),
                    _PrebookStep("S03", purpose="首次预约成功", expect_success=True),
                    _CancelUsageStep("S04"),
                    _PrebookStep("S05", purpose="负向：复用已消费 token", expect_success=False),
                    _CancelPurchaseStep("S06"),
                ],
            ),
            _TestFolder(
                "Prebooking_VoucherTypeAndRedemptionUrl",
                "test_prebooking.py::test_LocalOfferEpass_Prebooking_VoucherTypeAndRedemptionUrl",
                [
                    _CreateEpassStep("S01", purpose="创建 ePass", payload=lo.CREATE_PAYLOAD_TEMPLATE),
                    _AvailabilityStep("S02", purpose="可用性取 token", with_epass=True),
                    _PrebookStep("S03", purpose="预约成功（voucher/redemption 见 pytest）"),
                    _CancelUsageStep("S04"),
                    _CancelPurchaseStep("S05"),
                ],
                folder_description="断言 voucherType=1 与 redemptionUrl（见 pytest）。",
            ),
        ],
        "Create E-pass Prebooking Order。",
    )


def BuildModulePrebookingTokenFolder() -> JsonObject:
    return lo.Folder(
        "M03 · test_prebooking_token.py",
        [
            _TestFolder(
                "Prebooking_WithoutEpassIdToken_Success",
                "test_prebooking_token.py::test_LocalOfferEpass_Prebooking_WithoutEpassIdToken_Success",
                [
                    _CreateEpassStep("S01", purpose="创建 ePass", payload=lo.CREATE_PAYLOAD_TEMPLATE),
                    _AvailabilityStep("S02", purpose="无 ePassId 可用性取 token", with_epass=False),
                    _PrebookStep("S03", purpose="预约成功（token 未绑 ePassId）"),
                    _CancelUsageStep("S04"),
                    _CancelPurchaseStep("S05"),
                ],
            ),
            _TestFolder(
                "Prebooking_EpassIdMatch_Success",
                "test_prebooking_token.py::test_LocalOfferEpass_Prebooking_EpassIdMatch_Success",
                [
                    _CreateEpassStep("S01", purpose="创建 ePass", payload=lo.CREATE_PAYLOAD_TEMPLATE),
                    _AvailabilityStep("S02", purpose="带 ePassId 可用性取 token", with_epass=True),
                    _PrebookStep("S03", purpose="ePassId 与 token 一致预约成功"),
                    _CancelUsageStep("S04"),
                    _CancelPurchaseStep("S05"),
                ],
            ),
            _TestFolder(
                "Prebooking_EpassIdMismatch_Rejected",
                "test_prebooking_token.py::test_LocalOfferEpass_Prebooking_EpassIdMismatch_Rejected",
                [
                    _CreateEpassStep(
                        "S01",
                        purpose="创建 ePass A 并固化 firstEPassId",
                        payload=lo.CREATE_PAYLOAD_TEMPLATE,
                        save_first_epass_id=True,
                    ),
                    _CreateEpassStep("S03", purpose="创建 ePass B", payload=lo.CREATE_PAYLOAD_TEMPLATE),
                    StepSpec(
                        purpose="为 ePass A 取 prebookingToken",
                        step_id="S04",
                        method="POST",
                        url_path="/v2/resources/options/prebookings/availability",
                        path_hint="/prebookings/availability",
                        body=json.dumps(
                            {
                                "module": 11,
                                "ePassId": "{{firstEPassId}}",
                                "resourceId": "{{resourceId}}",
                                "optionId": "{{optionId}}",
                                "prebookingDate": lo.PREBOOKING_DATE_APIFOX,
                                "adultCount": 1,
                                "childCount": 0,
                            },
                            indent=2,
                        ),
                        prerequest_lines=lo.Prerequest_SyncPrebookingDateFromApifox(),
                        test_lines=["loAssertAvailabilitySuccess('S04');"],
                    ),
                    StepSpec(
                        purpose="负向：ePass B 使用 A 的 token",
                        step_id="S05",
                        method="POST",
                        url_path="/v2/orders/localOffers/ePasses/prebooking",
                        path_hint="/ePasses/prebooking",
                        body=json.dumps(
                            {
                                "module": 11,
                                "ePassId": "{{ePassId}}",
                                "extra": {"prebookingToken": "{{prebookingToken}}"},
                                "async": False,
                            },
                            indent=2,
                        ),
                        test_lines=["loAssertBusinessFailure('S05', ['500.110.028','500.110.019']);"],
                    ),
                ],
                folder_description="两个 ePass；token 绑定第一个。",
            ),
            _TestFolder(
                "Prebooking_EsimAvailabilityToken_Rejected",
                "test_prebooking_token.py::test_LocalOfferEpass_Prebooking_EsimAvailabilityToken_Rejected",
                [
                    _CreateEpassStep("S01", purpose="创建 ePass", payload=lo.CREATE_PAYLOAD_TEMPLATE),
                    _AvailabilityStep(
                        "S02",
                        purpose="负向：eSIM 网点可用性取 token",
                        with_epass=True,
                        extra_body={
                            "module": 8,
                            "resourceId": "{{esimResourceId}}",
                            "optionId": "{{esimOptionId}}",
                        },
                    ),
                    _PrebookStep("S03", purpose="负向：eSIM token 预约 LO", expect_success=False),
                    _CancelPurchaseStep("S04"),
                ],
            ),
        ],
        "prebookingToken 绑定与跨模块 token。",
    )


def BuildModulePrebookingRestrictionsFolder() -> Optional[JsonObject]:
    """M04 全部用例需复杂造数/双模式 availability，不导出 Postman。"""
    return None


def BuildModulePrebookingEntitlementsFolder() -> JsonObject:
    return _OptionalModuleFolder(
        "M05 · test_prebooking_entitlements.py",
        [
            _TestFolder(
                "Prebooking_ZeroAvailableUsages_Rejected",
                "test_prebooking_entitlements.py::test_LocalOfferEpass_Prebooking_ZeroAvailableUsages_Rejected",
                [
                    _CreateEpassStep(
                        "S01",
                        purpose="负向：availableUsages=0 创建拒绝",
                        payload=json.dumps(
                            {
                                "module": 11,
                                "clientUserId": "{{clientUserId}}",
                                "extra": {
                                    "firstName": lo.CREATE_FIRST_NAME,
                                    "lastName": lo.CREATE_LAST_NAME,
                                    "expirationDate": lo.CREATE_EXPIRATION_DATE,
                                    "availableUsages": 0,
                                    "allowedResources": {"resourceIds": [], "iata": [], "countryOrRegion": []},
                                },
                            },
                            indent=2,
                        ),
                        expect_business_failure=["301.110.001"],
                        accept_http_400=True,
                    ),
                ],
                folder_description="创建层拒绝；" + APIFOX_NEGATIVE_STEP_HINT,
            ),
        ],
        "权益点数（其余用例见 pytest 对应表，未导出 Postman）。",
    )


def BuildModuleBundleFolder() -> JsonObject:
    return lo.Folder(
        "M06 · test_bundle.py + test_bundle_token.py",
        [
            _TestFolder(
                "Bundle_InvalidTokenRejected",
                "test_bundle.py::test_LocalOfferEpass_Bundle_InvalidTokenRejected",
                [
                    StepSpec(
                        purpose="负向：无效 token Bundle",
                        step_id="S01",
                        method="POST",
                        url_path="/v2/orders/localOffers/ePasses/bundle",
                        path_hint="/ePasses/bundle",
                        body=json.dumps(
                            {
                                "module": 11,
                                "clientUserId": "{{$guid}}",
                                "extra": {"prebookingToken": INVALID_TOKEN},
                                "async": False,
                            },
                            indent=2,
                        ),
                        test_lines=["loAssertBusinessFailure('S01', ['500.110.028']);"],
                    ),
                ],
            ),
            _TestFolder(
                "Bundle_ReuseTokenRejected",
                "test_bundle.py::test_LocalOfferEpass_Bundle_ReuseTokenRejected",
                [
                    _AvailabilityStep("S01", purpose="Bundle 可用性取 token", with_epass=False),
                    _BundleStep("S02", purpose="首次 Bundle 成功"),
                    _CancelUsageStep("S03"),
                    StepSpec(
                        purpose="负向：复用已消费 token Bundle",
                        step_id="S04",
                        method="POST",
                        url_path="/v2/orders/localOffers/ePasses/bundle",
                        path_hint="/ePasses/bundle",
                        body=_BundleBody(),
                        prerequest_lines=lo.Prerequest_NewClientUserId(),
                        test_lines=["loAssertBusinessFailure('S04', ['500.110.028','500.110.027']);"],
                    ),
                ],
            ),
            _TestFolder(
                "Bundle_VoucherTypeAndRedemptionUrl",
                "test_bundle.py::test_LocalOfferEpass_Bundle_VoucherTypeAndRedemptionUrl",
                [
                    _AvailabilityStep("S01", purpose="Bundle 可用性取 token", with_epass=False),
                    _BundleStep("S02", purpose="Bundle 成功（voucher 见 pytest）"),
                    _CancelUsageStep("S03"),
                ],
            ),
            _TestFolder(
                "Bundle_EpassIdBoundToken_Rejected",
                "test_bundle_token.py::test_LocalOfferEpass_Bundle_EpassIdBoundToken_Rejected",
                [
                    _CreateEpassStep("S01", purpose="创建 ePass", payload=lo.CREATE_PAYLOAD_TEMPLATE),
                    _AvailabilityStep("S02", purpose="ePass 绑定 token 可用性", with_epass=True),
                    _BundleStep("S03", purpose="负向：ePass 绑定 token 不可 Bundle", expect_success=False),
                ],
            ),
            _TestFolder(
                "Bundle_EsimAvailabilityToken_Rejected",
                "test_bundle_token.py::test_LocalOfferEpass_Bundle_EsimAvailabilityToken_Rejected",
                [
                    _AvailabilityStep(
                        "S01",
                        purpose="eSIM 网点可用性取 token",
                        with_epass=False,
                        extra_body={"module": 8, "resourceId": "{{esimResourceId}}", "optionId": "{{esimOptionId}}"},
                    ),
                    _BundleStep("S02", purpose="负向：eSIM token Bundle LO", expect_success=False),
                ],
            ),
            _TestFolder(
                "Bundle_WithoutEpassIdToken_Success",
                "test_bundle_token.py::test_LocalOfferEpass_Bundle_WithoutEpassIdToken_Success",
                [
                    _AvailabilityStep("S01", purpose="无 ePassId 可用性取 token", with_epass=False),
                    _BundleStep("S02", purpose="Bundle 一步下单成功"),
                    _CancelUsageStep("S03"),
                    StepSpec(
                        purpose="search 按 ePassId 校验",
                        step_id="S04",
                        method="POST",
                        url_path="/v2/orders/ePasses/search",
                        path_hint="/ePasses/search",
                        body='{"ePassId": "{{ePassId}}"}',
                        test_lines=["loAssertHttpBusinessOk('S04');"],
                    ),
                ],
            ),
        ],
        "Bundle 一步下单与 token。",
    )


def BuildModuleAvailabilityFolder() -> JsonObject:
    return lo.Folder(
        "M07 · test_availability.py",
        [
            _TestFolder(
                "Availability_Adult1Child0_Success",
                "test_availability.py::test_LocalOfferEpass_Availability_Adult1Child0_Success",
                [
                    _CreateEpassStep("S01", purpose="创建 ePass", payload=lo.CREATE_PAYLOAD_TEMPLATE),
                    _AvailabilityStep("S02", purpose="成人1儿童0可用性成功", with_epass=True, adult=1, child=0),
                    _CancelPurchaseStep("S03"),
                ],
            ),
            _TestFolder(
                "Availability_InvalidGuestCountsRejected",
                "test_availability.py::test_LocalOfferEpass_Availability_InvalidGuestCountsRejected",
                [
                    _CreateEpassStep("S01", purpose="创建 ePass", payload=lo.CREATE_PAYLOAD_TEMPLATE),
                    _AvailabilityStep(
                        "S02",
                        purpose="负向：成人1儿童1",
                        with_epass=True,
                        adult=1,
                        child=1,
                        expect_success=False,
                        failure_err_codes=["500.020.029"],
                    ),
                    _AvailabilityStep(
                        "S03",
                        purpose="负向：成人0儿童1",
                        with_epass=True,
                        adult=0,
                        child=1,
                        expect_success=False,
                        failure_err_codes=["500.020.029"],
                    ),
                    _AvailabilityStep(
                        "S04",
                        purpose="负向：成人0儿童0",
                        with_epass=True,
                        adult=0,
                        child=0,
                        expect_success=False,
                        failure_err_codes=["500.020.029"],
                    ),
                ],
                folder_description="三组负向；见 pytest 参数化断言。",
            ),
            _TestFolder(
                "Availability_PastDateRejected",
                "test_availability.py::test_LocalOfferEpass_Availability_PastDateRejected",
                [
                    _CreateEpassStep("S01", purpose="创建 ePass", payload=lo.CREATE_PAYLOAD_TEMPLATE),
                    StepSpec(
                        purpose="负向：过期 prebookingDate",
                        step_id="S02",
                        method="POST",
                        url_path="/v2/resources/options/prebookings/availability",
                        path_hint="/prebookings/availability",
                        body=json.dumps(
                            {
                                "module": 11,
                                "ePassId": "{{ePassId}}",
                                "resourceId": "{{resourceId}}",
                                "optionId": "{{optionId}}",
                                "prebookingDate": PAST_PREBOOKING_DATE,
                                "adultCount": 1,
                                "childCount": 0,
                            },
                            indent=2,
                        ),
                        test_lines=["loAssertBusinessFailure('S02', ['500.110.019','500.020.009']);"],
                    ),
                ],
            ),
            _TestFolder(
                "Availability_EsimResourceOnModule11Rejected",
                "test_availability.py::test_LocalOfferEpass_Availability_EsimResourceOnModule11Rejected",
                [
                    _CreateEpassStep("S01", purpose="创建 ePass", payload=lo.CREATE_PAYLOAD_TEMPLATE),
                    _AvailabilityStep(
                        "S02",
                        purpose="负向：module11 使用 eSIM 网点",
                        with_epass=True,
                        extra_body={"resourceId": "{{esimResourceId}}", "optionId": "{{esimOptionId}}"},
                        expect_success=False,
                        failure_err_codes=["500.020.007"],
                    ),
                ],
            ),
        ],
        "可用性查询（manual 异常 ID 见 pytest 对应表）。",
    )


def BuildModuleRetrieveFolder() -> JsonObject:
    return _OptionalModuleFolder(
        "M08 · test_retrieve.py",
        [
            _TestFolder(
                "SearchDetails_OrderNotFound",
                "test_retrieve.py::test_LocalOfferEpass_SearchDetails_OrderNotFound",
                [
                    StepSpec(
                        purpose="负向：不存在 orderId search",
                        step_id="S01",
                        method="POST",
                        url_path="/v2/orders/ePasses/search",
                        path_hint="/ePasses/search",
                        body=json.dumps({"orderId": FAKE_ORDER_ID}, indent=2),
                        test_lines=["loAssertBusinessFailure('S01', ['500.080.004','500.000.004']);"],
                    ),
                ],
            ),
            _TestFolder(
                "UsageDetails_OrderNotFound",
                "test_retrieve.py::test_LocalOfferEpass_UsageDetails_OrderNotFound",
                [
                    StepSpec(
                        purpose="负向：不存在 orderId details",
                        step_id="S01",
                        method="POST",
                        url_path="/v2/orders/ePasses/details",
                        path_hint="/ePasses/details",
                        body=json.dumps({"orderId": FAKE_ORDER_ID}, indent=2),
                        test_lines=["loAssertBusinessFailure('S01', ['500.110.004','500.000.004']);"],
                    ),
                ],
            ),
            _TestFolder(
                "OrderList_AfterCreateOnly",
                "test_retrieve.py::test_LocalOfferEpass_OrderList_AfterCreateOnly",
                [
                    _CreateEpassStep("S01", purpose="创建 ePass", payload=lo.CREATE_PAYLOAD_TEMPLATE),
                    StepSpec(
                        purpose="创建后 orders 列表分页",
                        step_id="S02",
                        method="POST",
                        url_path="/v2/orders/ePasses",
                        path_hint="/ePasses",
                        body=lo.OrdersListBody(),
                        test_lines=["loAssertHttpBusinessOk('S02');", "loAssertOrderListPagination('S02', true, true);"],
                    ),
                    _CancelPurchaseStep("S03"),
                ],
            ),
            _TestFolder(
                "SearchDetails_ByEPassId_Only",
                "test_retrieve.py::test_LocalOfferEpass_SearchDetails_ByEPassId_Only",
                [
                    _CreateEpassStep("S01", purpose="创建 ePass", payload=lo.CREATE_PAYLOAD_TEMPLATE),
                    StepSpec(
                        purpose="search 按 ePassId 查 MS 详情",
                        step_id="S02",
                        method="POST",
                        url_path="/v2/orders/ePasses/search",
                        path_hint="/ePasses/search",
                        body='{"ePassId": "{{ePassId}}"}',
                        test_lines=["loAssertHttpBusinessOk('S02');", "loAssertSearchPurchaseDetails('S02', false);"],
                    ),
                    _CancelPurchaseStep("S03"),
                ],
            ),
        ],
        "查询/列表/详情（扩展字段与 module 隔离见 pytest）。",
    )


def BuildModuleCancelFolder() -> JsonObject:
    return lo.Folder(
        "M09 · test_cancel.py",
        [
            _TestFolder(
                "CancelPurchaseOrder",
                "test_cancel.py::test_LocalOfferEpass_CancelPurchaseOrder",
                [
                    _CreateEpassStep("S01", purpose="创建 ePass", payload=lo.CREATE_PAYLOAD_TEMPLATE),
                    _CancelPurchaseStep("S02"),
                    StepSpec(
                        purpose="取消 MS 后 search 显示 Cancelled",
                        step_id="S03",
                        method="POST",
                        url_path="/v2/orders/ePasses/search",
                        path_hint="/ePasses/search",
                        body='{"ePassId": "{{ePassId}}"}',
                        test_lines=[
                            "loAssertHttpBusinessOk('S03');",
                            "loAssertSearchCancelledAfterPurchaseCancel('S03', true);",
                            "loNoteSaasManual('S03');",
                        ],
                    ),
                ],
            ),
        ],
        "会籍购买单取消。",
    )


def BuildModuleSaasFolder() -> JsonObject:
    return _OptionalModuleFolder(
        "M10 · test_saas_manual_checkpoint.py",
        [
            _TestFolder(
                "SaasCheckpoint_Create_NoResourceIdsRestriction",
                "test_saas_manual_checkpoint.py::test_LocalOfferEpass_SaasCheckpoint_Create_NoResourceIdsRestriction",
                [
                    _CreateEpassStep("S01", purpose="创建 ePass（SaaS 核对）", payload=lo.CREATE_PAYLOAD_TEMPLATE),
                    _CancelPurchaseStep(
                        "S02",
                        extra_test_lines=["loNoteSaasManual('S02');"],
                    ),
                ],
                folder_description="取消后见 S02 控制台 SaaS 核对提示；``needs_saas_manual_verify``。",
            ),
        ],
        "其余 SaaS 场景见 pytest；本集合仅导出一条可跑链。",
    )


def BuildModuleSandboxFolder() -> Optional[JsonObject]:
    return None


def BuildFullCollection() -> JsonObject:
    variables: List[JsonObject] = [
        lo.CollectionVariable("baseUrl", "https://developer-sandbox.dragonpass.com/api"),
        lo.CollectionVariable("ProgramID", ""),
        lo.CollectionVariable("clientId", ""),
        lo.CollectionVariable("secret", ""),
        lo.CollectionVariable("x-version", ""),
        lo.CollectionVariable("prebookingDate", ""),
        lo.CollectionVariable("accessToken", ""),
        lo.CollectionVariable("clientUserId", ""),
        lo.CollectionVariable("ePassId", ""),
        lo.CollectionVariable("purchaseOrderId", ""),
        lo.CollectionVariable("usageOrderId", ""),
        lo.CollectionVariable("prebookingToken", ""),
        lo.CollectionVariable("discoveredResourceId", ""),
        lo.CollectionVariable("discoveredCountryOrRegion", ""),
        lo.CollectionVariable("esimResourceId", "GR0005901"),
        lo.CollectionVariable("esimOptionId", "SKU-GS0010955"),
        lo.CollectionVariable("firstEPassId", ""),
        lo.CollectionVariable("membershipId", ""),
    ]
    info: JsonObject = {
        "name": COLLECTION_DISPLAY_NAME,
        "description": (
            "由 GeneratePostmanCollectionLocalOfferEpassFull.py 生成。\n\n"
            "覆盖 **test_local_offer_epass.py** 三条 E2E 主链路 + **local_offer_epass/** 分模块用例。\n"
            "与 **P0 E2E 核心** / **P1 E2E (pytest-sync)** 并存，勿覆盖手工 P0 集合。\n\n"
            "**环境变量**：ProgramID、clientId、secret、resourceId、optionId（见 ``LocalOffer-ePass-sandbox.postman_environment.json``）。\n"
            "``esimResourceId``/``esimOptionId`` 默认 GR0005901/SKU-GS0010955；负向可用性/创建会用 **esim** 变量（非 LO ``resourceId``）。\n"
            "Apifox 负向/HTTP400 步骤：关闭「校验响应」避免「HTTP状态码应当是200」（见各步 description）。\n"
            f"未导出 Postman 的 pytest 用例索引：``{PYTEST_ONLY_NOT_IN_FULL}``（M04/M11 整模块及复杂造数/扩展字段等）。"
            "可运行步骤权威仍以 pytest + Allure 为准。"
        ),
        "schema": lo.POSTMAN_SCHEMA,
    }
    module_items: List[JsonObject] = [
        BuildModuleCreateFolder(),
        BuildModulePrebookingFolder(),
        BuildModulePrebookingTokenFolder(),
        BuildModulePrebookingRestrictionsFolder(),
        BuildModulePrebookingEntitlementsFolder(),
        BuildModuleBundleFolder(),
        BuildModuleAvailabilityFolder(),
        BuildModuleRetrieveFolder(),
        BuildModuleCancelFolder(),
        BuildModuleSaasFolder(),
        BuildModuleSandboxFolder(),
    ]
    module_items = [f for f in module_items if f is not None]
    return {
        "info": info,
        "variable": variables,
        "item": [
            lo.Folder("00 Auth", [_AuthStep()], "先执行。"),
            lo.Folder(
                "E2E · test_local_offer_epass.py",
                [
                    lo.BuildCreateE2EFolder(),
                    lo.BuildPrebookingE2EFolder(),
                    lo.BuildBundleE2EFolder(),
                ],
                "三条 RunLocalOfferEpass*MainE2EScenario（与 P1 相同步骤）。",
            ),
            *module_items,
        ],
    }


def Main() -> None:
    script_dir = os.path.dirname(__file__)
    payload = BuildFullCollection()
    step_count = lo.CountPostmanRequests(payload)
    out_path = os.path.join(script_dir, OUT_NAME)
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(f"Wrote {out_path} ({step_count} HTTP steps)")

    apifox_path = os.path.join(script_dir, APIFOX_IMPORT_NAME)
    apifox_payload = lo.BuildApifox2743ImportPayload(payload)
    with open(apifox_path, "w", encoding="utf-8") as handle:
        json.dump(apifox_payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(f"Wrote {apifox_path}")

    p1_full_payload = lo.CloneCollectionWithDisplayName(payload, COLLECTION_P1_FULL_DISPLAY_NAME)
    for legacy_name in FULL_LEGACY_OUT_NAMES:
        legacy_path = os.path.join(script_dir, legacy_name)
        with open(legacy_path, "w", encoding="utf-8") as handle:
            json.dump(p1_full_payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        print(f"Wrote {legacy_path} ({step_count} HTTP steps)")

    legacy_apifox = lo.BuildApifox2743ImportPayload(p1_full_payload)
    for col in legacy_apifox.get("apiTestCaseCollection", []):
        for item in col.get("items", []):
            if str(item.get("name", "")).startswith("P1 E2E pytest-sync"):
                item["name"] = f"P1 Full（{step_count} 步 · E2E + 分模块）"
    legacy_apifox_path = os.path.join(script_dir, FULL_LEGACY_APIFOX_NAME)
    with open(legacy_apifox_path, "w", encoding="utf-8") as handle:
        json.dump(legacy_apifox, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(f"Wrote {legacy_apifox_path}")

    print(
        f"Full 合计 {step_count} 个 HTTP 步骤（E2E + M01～M10 分模块；"
        "仅 37 步 E2E 核心见 LocalOffer-ePass-P1-e2e-core.postman_collection.json）"
    )

    p0_path = os.path.join(script_dir, lo.P0_COLLECTION_JSON_NAME)
    if os.path.isfile(p0_path):
        print(f"Left unchanged (manual P0): {p0_path}")


if __name__ == "__main__":
    Main()
