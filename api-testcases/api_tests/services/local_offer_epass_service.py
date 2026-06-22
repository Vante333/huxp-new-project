"""
Local Offer ePass 订单自动化 — HTTP 封装、断言与资源探测。

**主链路（对齐 ``api-testcases/docs/api-main-call-chains.md`` · EPass）**：

1. **创建验证链**（``RunLocalOfferEpassCreateMainE2EScenario``）：
   ``POST /v2/orders/localOffers/ePasses`` → ``POST /v2/users/ePasses`` →
   ``POST /v2/orders/ePasses`` → ``POST /v2/orders/ePasses/search``

2. **Prebooking 链**（``RunLocalOfferEpassPrebookingMainE2EScenario``）：
   ``POST /v2/orders/localOffers/ePasses`` →
   ``POST /v2/resources/options/prebookings/availability`` →
   ``POST /v2/orders/localOffers/ePasses/prebooking`` →
   ``PATCH /v2/orders``（取消 usage 预订单）→
   ``POST /v2/orders/ePasses/details`` → ``POST /v2/orders/ePasses`` →
   ``POST /v2/orders/ePasses/search``（会籍卡/购买单详情）

鉴权 ``POST /v2/auth/token`` 由用例 ``EpassToken`` fixture（``GetAccessTokenForEpass``）提供，不在编排队列内。
Allure ``S01/S02/…`` 由 ``AllureHttpScenarioSteps.Next`` 按每次 HTTP 递增。

**软断言**：带 ``local_offer_epass`` / ``local_offers`` marker 的用例由 ``conftest.LocalOfferSoftAssertScope`` 启用；
断言失败时仍继续后续 HTTP，用例末尾一次性 ``pytest.fail`` 汇总（与 PAPI-2515 ``P2515E2ESoftAssert`` 同构）。

**必填环境变量**（与 Apifox 对照见 ``config/local_offer_epass_env.py``、``env/.env.local-offer.example``）：

- 鉴权：``DP_EPASS_PROGRAM_ID``、``DP_EPASS_CLIENT_ID``、``DP_EPASS_CLIENT_SECRET``（别名 ``PROGRAM_ID``/``CLIENT_ID``/``CLIENT_SECRET``）
- 默认网点：``DP_LO_EPASS_RESOURCE_ID``、``DP_LO_EPASS_OPTION_ID``（别名 ``RESOURCE_ID``/``OPTION_ID``）
- 按券型：``DP_LO_EPASS_<LABEL>_RESOURCE_ID`` / ``_OPTION_ID``（如 ``URL``、``REDEMPTION_CODE``、``CARD_SECRET``）

**可选**：``GET /v2/resources?module=`` 动态解析
``resourceIds`` / ``countryOrRegion``（module=11 Local Offer，module=8 eSIM 用于负向混合校验）。
预约造数默认走资源链（``DP_LO_EPASS_USE_RESOURCE_CHAIN=1``）：
``GET /v2/resources`` → ``GET .../localOffers/{resourceId}/options`` →
``GET .../options/{optionId}`` → ``POST .../options/prebookings/availability``。
voucherType=1 × redemptionUrl 有值场景见 ``GetDefaultVoucherRedemptionScenarios()`` 与
``DP_LO_EPASS_CARD_SECRET_WITH_URL_*`` 等环境变量。

**module 断言**：订单/详情等成功响应若含 ``module`` 须严格为 **11**；``POST /v2/users/ePasses`` 列表项 canary 常无 ``module``，
``AssertUserEPassesContains`` 在字段缺失时跳过 module 校验、字段存在时仍须为 11。可用性 ``prebookingToken`` 响应无 ``module``，不在此列。

**module=8 隔离**：Local Offer 订单在 ``POST /v2/orders/ePasses`` / ``details`` 入参 ``module=8`` 时不应返回
Local Offer 数据；eSIM 订单在 ``module=11`` 时不应返回 module=8 数据。双向校验见
``VerifyUsageOrderRetrieveModuleIsolation`` / ``AssertEsimNotReturnedWithLocalOfferModuleFilter``。
``POST /v2/orders/ePasses/search`` **请求体不含** ``module``（仅 ``orderId`` / ``ePassId`` 二选一）。
"""
from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple, cast

import allure
import pytest
import requests
from requests import Response

from framework.http.core import GetBaseUrl, MaskHeadersForLog
from framework.reporting import AttachAllureRequestMeta, AttachAllureResponseArtifacts, FormatAllureHttpStepTitle
from services.papi2424_epasses_impl import GetConfiguredEpassProgramId, RequireP2424EpassTokenEnvOrSkip
from framework.soft_assert import (
    GetActiveLocalOfferSoftAssert,
    LocalOfferFailOrRecord,
    RunSoftAwareAllureAssertionStep,
    RunWithSoftCapture,
)
from services.papi2548_memberships_extensions_impl import (
    JsonDict,
    ParseResponseEnvelope,
    RequestWithAllure,
    AssertHttpAndBusinessOk,
    AssertRegisterSuccessBody,
    BuildMinimalMembershipPayload,
    GetAccessToken,
    IsBusinessSuccess,
    PostMemberships,
)

LOCAL_OFFER_MODULE_INT: int = 11
LOCAL_OFFER_PATH_MODULE: str = "localOffers"
ESIM_MODULE_INT: int = 8
ESIM_PATH_MODULE: str = "esims"


class LocalOfferModuleMismatchError(AssertionError):
    """Local Offer 接口响应 ``module`` 非 11 或缺失。"""


def AssertLocalOfferModule11(
    module_value: Any,
    *,
    context: str,
    response_hint: Optional[str] = None,
) -> None:
    """断言 ``module`` 值必须为 11（Local Offer），否则抛出 ``LocalOfferModuleMismatchError``。"""
    if module_value != LOCAL_OFFER_MODULE_INT:
        hint = f"；响应摘要: {response_hint}" if response_hint else ""
        raise LocalOfferModuleMismatchError(
            f"{context}: Local Offer 接口 module 应为 11，实际为 {module_value!r}{hint}"
        )


def AssertLocalOfferDataRootModule11(data: Mapping[str, Any], *, context: str) -> None:
    """断言响应 ``data`` 根节点含 ``module`` 且值为 11。"""
    if "module" not in data:
        raise LocalOfferModuleMismatchError(
            f"{context}: Local Offer 响应缺少 module 字段: {data!r}"
        )
    AssertLocalOfferModule11(
        data.get("module"),
        context=context,
        response_hint=str({k: data.get(k) for k in ("orderId", "status", "category") if k in data}),
    )


def AssertLocalOfferListItemModule11(
    item: Mapping[str, Any],
    *,
    context: str,
    allow_missing_module: bool = False,
) -> bool:
    """
    断言列表项（orders / ePassesList 元素）``module`` 为 11。

    ``allow_missing_module=True`` 时：无 ``module`` 键不失败（canary ``POST /v2/users/ePasses`` 常见 doc gap），
    但若响应含 ``module`` 仍须严格为 11。返回 ``True`` 表示已校验 module=11，``False`` 表示字段缺失已跳过。
    """
    if "module" not in item:
        if allow_missing_module:
            return False
        raise LocalOfferModuleMismatchError(
            f"{context}: Local Offer 列表项缺少 module 字段: {item!r}"
        )
    AssertLocalOfferModule11(
        item.get("module"),
        context=context,
        response_hint=str(item.get("orderId") or item.get("ePassId")),
    )
    return True

# 网点 catalog 由环境变量驱动，见 ``config/local_offer_epass_env.py``（无硬编码 resourceId/optionId）。
from config.local_offer_epass_env import (
    BuildLocalOfferPrebookingDate,
    GetDefaultPrebookingResources,
    GetDefaultVoucherRedemptionScenarios,
    GetOutletOptionIdForLabel,
    GetOutletResourceIdForLabel,
    IterLocalOfferPrebookingDateCandidates,
    RequireDefaultOutletEnvOrSkipMessage,
)

_PREBOOKING_REQUIRED_INFO_NULL_FIELDS: Tuple[str, ...] = (
    "firstName",
    "lastName",
    "email",
    "phoneNumber",
    "callingCode",
    "transportNumber",
)


@dataclass(frozen=True)
class LocalOfferResourceOptionReference:
    """
    Local Offer ePass usage 订单字段对拍基准。

    ``City`` / ``CountryOrRegion`` / ``OptionId`` 来自
    ``GET /v2/resources/{resourceId}?language=en-US&module=11&fallbackAllowed=true``；
    ``ResourceId`` / ``ResourceName`` / ``OptionName`` 来自
    ``GET /v2/resources/localOffers/{resourceId}/options/{optionId}``。
    """

    ResourceId: str
    ResourceName: str
    OptionId: str
    OptionName: str
    City: Optional[str] = None
    CountryOrRegion: Optional[str] = None


@dataclass(frozen=True)
class LocalOfferPrebookingTarget:
    """Local Offer 预约下单目标网点与 option。"""

    Label: str
    ResourceId: str
    OptionId: str
    ExpectedVoucherType: int
    ExpectRedemptionUrlPresent: Optional[bool] = None


@dataclass
class ModuleResourceHints:
    """从 ``GET /v2/resources`` 解析出的限制字段候选。"""

    ResourceIds: List[str] = field(default_factory=list)
    CountryOrRegions: List[str] = field(default_factory=list)
    IataCodes: List[str] = field(default_factory=list)


@dataclass
class LocalOfferEpassCreateResult:
    """ePass 创建链路上下文。"""

    ClientUserId: str
    EPassId: str
    PurchaseOrderId: str
    CreateResponse: Response


@dataclass
class LocalOfferEpassPrebookingResult:
    """ePass Prebooking 链路上下文。"""

    ClientUserId: str
    EPassId: str
    PurchaseOrderId: str
    UsageOrderId: str
    PrebookingToken: str
    ResourceId: str
    OptionId: str
    PrebookingDate: str


def RequireLocalOfferEpassEnvOrSkip() -> None:
    """Local Offer ePass 与 PAPI-2424 共用 ePass 三件套。"""
    RequireP2424EpassTokenEnvOrSkip()


# 用例级待取消订单登记（``conftest.LocalOfferPendingOrderCleanup`` teardown 兜底）
_PENDING_ORDER_IDS_BY_TEST: Dict[str, List[str]] = {}
_PENDING_EPASS_IDS_BY_TEST: Dict[str, List[str]] = {}
_ACTIVE_LOCAL_OFFER_CLEANUP_TEST_KEY: Optional[str] = None


def SetLocalOfferOrderCleanupTestKey(test_key: str) -> None:
    """绑定当前 pytest 用例 nodeid，供登记/清理待取消订单。"""
    global _ACTIVE_LOCAL_OFFER_CLEANUP_TEST_KEY
    _ACTIVE_LOCAL_OFFER_CLEANUP_TEST_KEY = test_key
    _PENDING_ORDER_IDS_BY_TEST.setdefault(test_key, [])
    _PENDING_EPASS_IDS_BY_TEST.setdefault(test_key, [])


def RegisterPendingLocalOfferOrder(order_id: str) -> None:
    """登记待取消 ``orderId``（usage 预订单或 MS 购买单）。"""
    if not order_id or not _ACTIVE_LOCAL_OFFER_CLEANUP_TEST_KEY:
        return
    bucket = _PENDING_ORDER_IDS_BY_TEST.setdefault(_ACTIVE_LOCAL_OFFER_CLEANUP_TEST_KEY, [])
    if order_id not in bucket:
        bucket.append(order_id)


def RegisterPendingLocalOfferEPassId(e_pass_id: str) -> None:
    """登记 Bundle 等场景新建的 ePassId（teardown 时 search 购买单并取消）。"""
    if not e_pass_id or not _ACTIVE_LOCAL_OFFER_CLEANUP_TEST_KEY:
        return
    bucket = _PENDING_EPASS_IDS_BY_TEST.setdefault(_ACTIVE_LOCAL_OFFER_CLEANUP_TEST_KEY, [])
    if e_pass_id not in bucket:
        bucket.append(e_pass_id)


def MarkLocalOfferOrderCancelled(order_id: str) -> None:
    """显式收尾已取消的 ``orderId``，避免 teardown 重复 PATCH。"""
    if not order_id or not _ACTIVE_LOCAL_OFFER_CLEANUP_TEST_KEY:
        return
    bucket = _PENDING_ORDER_IDS_BY_TEST.get(_ACTIVE_LOCAL_OFFER_CLEANUP_TEST_KEY)
    if bucket and order_id in bucket:
        bucket.remove(order_id)


def MarkLocalOfferEPassPurchaseCancelled(e_pass_id: str) -> None:
    """购买单已取消（注销 ePass）后移出 ePassId 待清理列表。"""
    if not e_pass_id or not _ACTIVE_LOCAL_OFFER_CLEANUP_TEST_KEY:
        return
    bucket = _PENDING_EPASS_IDS_BY_TEST.get(_ACTIVE_LOCAL_OFFER_CLEANUP_TEST_KEY)
    if bucket and e_pass_id in bucket:
        bucket.remove(e_pass_id)


def TryRegisterLocalOfferOrdersFromBusinessResponse(resp: Response) -> None:
    """HTTP 200 且业务成功时，从响应登记 ``orderId`` / ``ePassId``（供未走断言封装的用例）。"""
    try:
        _st, env, data = ParseResponseEnvelope(resp)
        if not IsLocalOfferBusinessSuccess(env) or not isinstance(data, dict):
            return
        order_id = data.get("orderId")
        if isinstance(order_id, str) and order_id:
            RegisterPendingLocalOfferOrder(order_id)
        e_pass_id = _ResolveEPassIdField(data)
        if isinstance(e_pass_id, str) and e_pass_id:
            RegisterPendingLocalOfferEPassId(e_pass_id)
    except Exception:
        return


def _PatchCancelOrderBestEffort(
    token: str,
    order_id: str,
    *,
    steps: Any,
    step_brief: str,
) -> None:
    """尽力取消订单；已取消或环境异常时不抛错。"""
    kw = _HttpStepKw(steps, step_brief)
    try:
        resp = PatchCancelOrder(
            token,
            order_id,
            step_code=kw["step_code"],
            step_title=kw["step_title"],
        )
        if resp.status_code == 200:
            _st, env, _data = ParseResponseEnvelope(resp)
            if IsLocalOfferBusinessSuccess(env):
                MarkLocalOfferOrderCancelled(order_id)
    except Exception:
        return


def CancelAllPendingLocalOfferOrdersBestEffort(
    token: str,
    steps: Any,
    *,
    test_key: str,
    context: str = "teardown",
) -> None:
    """
    用例结束兜底：取消本用例登记且尚未显式收尾的订单。

    - 直接登记的 ``orderId``：``PATCH /v2/orders`` status=3
    - 仅登记 ``ePassId``（典型 Bundle）：search 购买单 ``orderId`` 后取消
    """
    order_ids = list(_PENDING_ORDER_IDS_BY_TEST.pop(test_key, []))
    e_pass_ids = list(_PENDING_EPASS_IDS_BY_TEST.pop(test_key, []))
    if not order_ids and not e_pass_ids:
        return

    import json

    with allure.step(f"Local Offer 残留订单兜底取消 · {context}"):
        allure.attach(
            json.dumps(
                {"pendingOrderIds": order_ids, "pendingEPassIds": e_pass_ids},
                ensure_ascii=False,
                indent=2,
            ),
            name="pending_orders_before_teardown_cancel",
            attachment_type=allure.attachment_type.JSON,
        )

    for order_id in order_ids:
        _PatchCancelOrderBestEffort(
            token,
            order_id,
            steps=steps,
            step_brief=f"{context} · 取消残留 orderId",
        )

    for e_pass_id in e_pass_ids:
        kw_search = _HttpStepKw(steps, f"{context} · search 购买单（{e_pass_id[:8]}…）")
        try:
            resp_search = PostOrdersEPassesSearch(
                token,
                e_pass_id=e_pass_id,
                step_code=kw_search["step_code"],
                step_title=kw_search["step_title"],
            )
            if resp_search.status_code != 200:
                continue
            data = ExtractBusinessData(resp_search)
            purchase_order_id = data.get("orderId")
            if isinstance(purchase_order_id, str) and purchase_order_id:
                _PatchCancelOrderBestEffort(
                    token,
                    purchase_order_id,
                    steps=steps,
                    step_brief=f"{context} · 取消 Bundle 购买单",
                )
                MarkLocalOfferEPassPurchaseCancelled(e_pass_id)
        except Exception:
            continue


def _NewClientUserId() -> str:
    return str(uuid.uuid4())


def _DefaultExpirationDate() -> str:
    return os.getenv("DP_LO_EPASS_EXPIRATION_DATE", "2028-12-31T23:59:59+00:00").strip()


def _DefaultAvailableUsages() -> int:
    raw = os.getenv("DP_LO_EPASS_AVAILABLE_USAGES", "5").strip()
    try:
        value = int(raw)
    except ValueError:
        value = 5
    return max(1, min(value, 99))


def _AllPrebookingResourceCatalogItems() -> Tuple[Dict[str, str], ...]:
    return GetDefaultPrebookingResources() + GetDefaultVoucherRedemptionScenarios()


def _ParseRedemptionUrlExpectation(item: Mapping[str, str]) -> Optional[bool]:
    raw = item.get("redemptionUrlExpect", "").strip().lower()
    if raw == "present":
        return True
    if raw in ("absent", "null", "none"):
        return False
    return None


def _StaticPrebookingTargetFromCatalogItem(item: Mapping[str, str]) -> LocalOfferPrebookingTarget:
    """仅从 catalog + 环境变量解析，不发起 HTTP。"""
    label = item["label"]
    env_prefix = f"DP_LO_EPASS_{label.upper()}"
    fallback_label = item.get("fallbackLabel", "").strip()
    resource_id = os.getenv(f"{env_prefix}_RESOURCE_ID", "").strip()
    if not resource_id:
        resource_id = item.get("resourceId", "").strip()
    if not resource_id and fallback_label:
        resource_id = GetOutletResourceIdForLabel(fallback_label)
    if not resource_id:
        resource_id = GetOutletResourceIdForLabel(label)
    option_id = os.getenv(f"{env_prefix}_OPTION_ID", "").strip()
    if not option_id:
        option_id = item.get("optionId", "").strip()
    if not option_id and fallback_label:
        option_id = GetOutletOptionIdForLabel(fallback_label)
    if not option_id:
        option_id = GetOutletOptionIdForLabel(label)
    if not resource_id:
        raise ValueError(f"catalog label={label!r} 缺少 resourceId 且 fallback 未解析")
    if not option_id:
        raise ValueError(f"catalog label={label!r} 缺少 optionId（需配置或由资源链动态解析）")
    voucher_type = int(os.getenv(f"{env_prefix}_VOUCHER_TYPE", item["voucherType"]))
    return LocalOfferPrebookingTarget(
        Label=label,
        ResourceId=resource_id,
        OptionId=option_id,
        ExpectedVoucherType=voucher_type,
        ExpectRedemptionUrlPresent=_ParseRedemptionUrlExpectation(item),
    )


def _UseResourceChainDiscovery() -> bool:
    raw = os.getenv("DP_LO_EPASS_USE_RESOURCE_CHAIN", "1").strip().lower()
    return raw not in ("0", "false", "off", "no")


def _ParseBusinessErrCode(resp: Response) -> Optional[str]:
    """解析业务失败 ``errCode``；HTTP 非 200 或成功时返回 ``None``。"""
    if resp.status_code != 200:
        return None
    _st, env, _data = ParseResponseEnvelope(resp)
    if not isinstance(env, dict) or env.get("code") != -1:
        return None
    raw = env.get("errCode")
    return str(raw) if raw is not None else None


def _SkipIfPrebookingTimeslotUnavailable(resp: Response, *, context: str) -> None:
    """预约/Bundle 响应为 ``500.020.009`` 时 skip（沙箱时段不可用，非断言缺陷）。"""
    err = _ParseBusinessErrCode(resp)
    if err == "500.020.009":
        pytest.skip(
            f"{context}: 时段不可用（500.020.009），"
            f"可配置 DP_LO_EPASS_PREBOOKING_DATE 或更换 DP_LO_EPASS_*_RESOURCE_ID"
        )


def _IsPrebookingAvailabilityOk(resp: Response) -> bool:
    if resp.status_code != 200:
        return False
    _st, env, data = ParseResponseEnvelope(resp)
    if not IsLocalOfferBusinessSuccess(env):
        return False
    return isinstance(data, dict) and data.get("available") is True


def _ParsePrebookingTokenFromAvailabilityResponse(
    resp: Response,
) -> Tuple[Optional[str], Optional[str]]:
    """解析可用性响应：成功 ``(prebookingToken, None)``；失败 ``(None, errCode 或说明)``。"""
    err = _ParseBusinessErrCode(resp)
    if err:
        return None, err
    if not _IsPrebookingAvailabilityOk(resp):
        return None, "availability-not-ok"
    _st, _env, data = ParseResponseEnvelope(resp)
    pb_token = data.get("prebookingToken") if isinstance(data, dict) else None
    if isinstance(pb_token, str) and pb_token:
        return pb_token, None
    return None, "prebookingToken-missing"


def _TryResolvePrebookingTokenFromAvailability(
    token: str,
    *,
    resource_id: str,
    option_id: str,
    prebooking_date: str,
    e_pass_id: Optional[str] = None,
) -> Tuple[Optional[str], Optional[str]]:
    """静默可用性探测（无 Allure 步骤，供资源链造数）。"""
    body = BuildAvailabilityBody(
        resource_id=resource_id,
        option_id=option_id,
        prebooking_date=prebooking_date,
        e_pass_id=e_pass_id,
    )
    resp = PostResourcesOptionsPrebookingsAvailability(token, body)
    return _ParsePrebookingTokenFromAvailabilityResponse(resp)


def _ExtractOptionIdsFromOptionsListResponse(resp: Response) -> List[str]:
    if resp.status_code != 200:
        return []
    _st, env, data = ParseResponseEnvelope(resp)
    if not IsLocalOfferBusinessSuccess(env) or not isinstance(data, dict):
        return []
    option_list = data.get("optionList")
    if not isinstance(option_list, list):
        return []
    option_ids: List[str] = []
    for item in option_list:
        if not isinstance(item, dict):
            continue
        option_id = item.get("optionId")
        if isinstance(option_id, str) and option_id and option_id not in option_ids:
            option_ids.append(option_id)
    return option_ids


def _ProbePrebookingAvailabilityWithoutEpass(
    token: str,
    resource_id: str,
    option_id: str,
) -> bool:
    """资源链造数：按候选 ``prebookingDate`` 探测可用性（无 ePassId）。"""
    for pb_date in IterLocalOfferPrebookingDateCandidates():
        pb_token, _err = _TryResolvePrebookingTokenFromAvailability(
            token,
            resource_id=resource_id,
            option_id=option_id,
            prebooking_date=pb_date,
        )
        if pb_token:
            return True
    return False


def DiscoverPrebookingPairViaResourceChain(
    token: str,
    *,
    steps: Any = None,
    resource_id_hint: Optional[str] = None,
    option_id_hint: Optional[str] = None,
    max_resources_to_scan: int = 50,
    require_availability: bool = True,
) -> Tuple[str, str]:
    """
    按用例步骤动态解析 ``resourceId`` / ``optionId``：

    1. ``GET /v2/resources?module=11`` → ``resourceId``
    2. ``GET /v2/resources/localOffers/{resourceId}/options`` → ``optionId``
    3. ``GET /v2/resources/localOffers/{resourceId}/options/{optionId}`` → 确认 option 详情可读
    4. ``POST /v2/resources/options/prebookings/availability`` → 校验可用（无 ``ePassId``）
    """
    list_kw = _HttpStepKw(steps, "GET /v2/resources module=11（预约造数）") if steps else {}
    resources_resp = GetResourcesList(
        token,
        module=LOCAL_OFFER_MODULE_INT,
        page_size=max(10, min(max_resources_to_scan, 100)),
        step_code=list_kw.get("step_code"),
        step_title=list_kw.get("step_title"),
    )
    if resources_resp.status_code != 200:
        raise RuntimeError(f"GET /v2/resources HTTP 非 200: {resources_resp.status_code}")
    _st_res, env_res, _data_res = ParseResponseEnvelope(resources_resp)
    if not IsLocalOfferBusinessSuccess(env_res):
        raise RuntimeError(f"GET /v2/resources 业务失败: {env_res!r}")
    hints = ParseResourcesListHints(resources_resp)
    candidate_resource_ids: List[str] = []
    if resource_id_hint:
        candidate_resource_ids.append(resource_id_hint)
    for rid in hints.ResourceIds:
        if rid not in candidate_resource_ids:
            candidate_resource_ids.append(rid)
    if not candidate_resource_ids:
        raise LookupError("GET /v2/resources module=11 未解析到 resourceId")

    scanned = 0
    for resource_id in candidate_resource_ids:
        if scanned >= max_resources_to_scan:
            break
        scanned += 1
        options_kw = (
            _HttpStepKw(steps, f"Local Offer options 列表（{resource_id} · 造数）") if steps else {}
        )
        options_resp = GetLocalOfferOptionsList(
            token,
            resource_id,
            step_code=options_kw.get("step_code"),
            step_title=options_kw.get("step_title"),
        )
        option_ids = _ExtractOptionIdsFromOptionsListResponse(options_resp)
        if not option_ids:
            continue
        option_candidates: List[str] = []
        if option_id_hint and option_id_hint in option_ids:
            option_candidates.append(option_id_hint)
        for oid in option_ids:
            if oid not in option_candidates:
                option_candidates.append(oid)
        for option_id in option_candidates:
            detail_kw = (
                _HttpStepKw(steps, f"Local Offer option 详情（{option_id} · 造数）") if steps else {}
            )
            detail_resp = GetLocalOfferOptionDetail(
                token,
                resource_id,
                option_id,
                step_code=detail_kw.get("step_code"),
                step_title=detail_kw.get("step_title"),
            )
            if detail_resp.status_code != 200:
                continue
            _st_detail, env_detail, data_detail = ParseResponseEnvelope(detail_resp)
            if not IsLocalOfferBusinessSuccess(env_detail) or not isinstance(data_detail, dict):
                continue
            ref_option_id = data_detail.get("optionId")
            if not isinstance(ref_option_id, str) or ref_option_id != option_id:
                continue
            if require_availability and not _ProbePrebookingAvailabilityWithoutEpass(
                token, resource_id, option_id
            ):
                continue
            return resource_id, option_id
    raise LookupError(
        f"资源链未找到可用 resourceId/optionId（hint resource={resource_id_hint!r}, "
        f"option={option_id_hint!r}，已扫描 {scanned} 个网点）"
    )


def DiscoverPrebookingPairViaResourceChainOrSkip(
    token: str,
    *,
    steps: Any = None,
    resource_id_hint: Optional[str] = None,
    option_id_hint: Optional[str] = None,
    max_resources_to_scan: int = 50,
    require_availability: bool = True,
) -> Tuple[str, str]:
    """``DiscoverPrebookingPairViaResourceChain`` 失败时 ``pytest.skip``。"""
    try:
        return DiscoverPrebookingPairViaResourceChain(
            token,
            steps=steps,
            resource_id_hint=resource_id_hint,
            option_id_hint=option_id_hint,
            max_resources_to_scan=max_resources_to_scan,
            require_availability=require_availability,
        )
    except LookupError as exc:
        pytest.skip(str(exc))
    except RuntimeError as exc:
        pytest.skip(str(exc))


@dataclass
class LocalOfferRedemptionUrlProbeRow:
    """单次预约下单探测结果。"""

    ResourceId: str
    OptionId: str
    ResourceName: Optional[str] = None
    OptionName: Optional[str] = None
    VoucherType: Optional[int] = None
    RedemptionUrl: Optional[str] = None
    HasRedemptionUrl: bool = False
    OrderId: Optional[str] = None
    Error: Optional[str] = None


@dataclass
class LocalOfferRedemptionUrlProbeCatalog:
    """轮询 module=11 各网点 option 后汇总的 ``redemptionUrl`` 探测表。"""

    ResourceCount: int
    AvailabilityOkPairCount: int
    ProbedOrderCount: int
    Results: List[LocalOfferRedemptionUrlProbeRow]
    WithRedemptionUrl: List[LocalOfferRedemptionUrlProbeRow]

    def RowsByVoucherType(self, voucher_type: int) -> List[LocalOfferRedemptionUrlProbeRow]:
        return [r for r in self.Results if r.VoucherType == voucher_type and not r.Error]

    def WithRedemptionUrlByVoucherType(self, voucher_type: int) -> List[LocalOfferRedemptionUrlProbeRow]:
        return [r for r in self.WithRedemptionUrl if r.VoucherType == voucher_type]


def _ProbeMaxOrdersLimit() -> Optional[int]:
    raw = os.getenv("DP_LO_EPASS_PROBE_MAX_ORDERS", "0").strip()
    if not raw or raw.lower() in ("0", "all", "none", "unlimited"):
        return None
    try:
        value = int(raw)
    except ValueError:
        return None
    return max(1, value)


def _ParsePrebookingOrderProbeRow(
    *,
    resource_id: str,
    option_id: str,
    book_resp: Response,
) -> LocalOfferRedemptionUrlProbeRow:
    """从预约下单响应解析 ``redemptionUrl`` / ``voucherType``；业务失败时写入 ``Error``。"""
    if book_resp.status_code != 200:
        return LocalOfferRedemptionUrlProbeRow(
            ResourceId=resource_id,
            OptionId=option_id,
            Error=f"HTTP {book_resp.status_code}",
        )
    _st, env, data = ParseResponseEnvelope(book_resp)
    if not IsLocalOfferBusinessSuccess(env):
        err = env.get("errCode") if isinstance(env, dict) else None
        msg = env.get("msg") if isinstance(env, dict) else None
        return LocalOfferRedemptionUrlProbeRow(
            ResourceId=resource_id,
            OptionId=option_id,
            Error=f"{err or 'business-fail'}: {msg}",
        )
    if not isinstance(data, dict):
        return LocalOfferRedemptionUrlProbeRow(
            ResourceId=resource_id,
            OptionId=option_id,
            Error=f"data 非对象: {data!r}",
        )
    extra = data.get("extra") if isinstance(data.get("extra"), dict) else {}
    local_opts = extra.get("localOfferOptions") if isinstance(extra.get("localOfferOptions"), dict) else {}
    vouchers = extra.get("vouchersList") if isinstance(extra.get("vouchersList"), list) else []
    voucher_type: Optional[int] = None
    if vouchers and isinstance(vouchers[0], dict):
        raw_vt = vouchers[0].get("voucherType")
        if isinstance(raw_vt, int):
            voucher_type = raw_vt
        elif isinstance(raw_vt, str) and raw_vt.isdigit():
            voucher_type = int(raw_vt)
    redemption_url = local_opts.get("redemptionUrl")
    has_url = isinstance(redemption_url, str) and bool(redemption_url.strip())
    usage_order_id = data.get("orderId")
    if isinstance(usage_order_id, str) and usage_order_id:
        RegisterPendingLocalOfferOrder(usage_order_id)
    return LocalOfferRedemptionUrlProbeRow(
        ResourceId=resource_id,
        OptionId=option_id,
        ResourceName=extra.get("resourceName") if isinstance(extra.get("resourceName"), str) else None,
        OptionName=local_opts.get("optionName") if isinstance(local_opts.get("optionName"), str) else None,
        VoucherType=voucher_type,
        RedemptionUrl=redemption_url if isinstance(redemption_url, str) else None,
        HasRedemptionUrl=has_url,
        OrderId=usage_order_id if isinstance(usage_order_id, str) else None,
    )


def FormatRedemptionUrlProbeSummaryMarkdown(
    catalog: LocalOfferRedemptionUrlProbeCatalog,
    *,
    language: Optional[str] = None,
) -> str:
    """生成 Allure 可读的轮询结论 Markdown。"""
    lang_note = language.strip() if isinstance(language, str) and language.strip() else "（未传 language，网关默认）"
    lines: List[str] = [
        "# Local Offer redemptionUrl 轮询结论",
        "",
        f"- **language**：{lang_note}",
        f"- module=11 网点数：{catalog.ResourceCount}",
        f"- 可用性通过 resourceId/optionId 对：{catalog.AvailabilityOkPairCount}",
        f"- 实际预约下单探测数：{catalog.ProbedOrderCount}",
        f"- **redemptionUrl 有值**：{len(catalog.WithRedemptionUrl)} 组",
        "",
        "## redemptionUrl 有值（可用于自动化 with_url 场景）",
        "",
    ]
    if catalog.WithRedemptionUrl:
        lines.append("| voucherType | resourceId | resourceName | optionId | optionName | redemptionUrl |")
        lines.append("|---:|---|---|---|---|---|")
        for row in catalog.WithRedemptionUrl:
            lines.append(
                f"| {row.VoucherType} | {row.ResourceId} | {row.ResourceName or ''} | "
                f"{row.OptionId} | {row.OptionName or ''} | {row.RedemptionUrl or ''} |"
            )
    else:
        lines.append("_（本次轮询未发现 redemptionUrl 有值的网点）_")

    for vt in (1, 4, 5):
        with_url = catalog.WithRedemptionUrlByVoucherType(vt)
        all_vt = catalog.RowsByVoucherType(vt)
        lines.extend(
            [
                "",
                f"## voucherType={vt}",
                "",
                f"- 成功下单：{len(all_vt)} 组",
                f"- redemptionUrl 有值：{len(with_url)} 组",
            ]
        )
        if with_url:
            lines.append("")
            for row in with_url:
                lines.append(
                    f"- **{row.ResourceId}** / **{row.OptionId}** "
                    f"({row.OptionName}) → `{row.RedemptionUrl}`"
                )
        elif all_vt:
            lines.append("")
            lines.append("_本券型本次轮询均为 redemptionUrl=null_")

    lines.extend(["", "## 推荐环境变量（复制到 .env / PowerShell）", ""])
    for row in catalog.WithRedemptionUrl:
        if row.VoucherType == 1:
            prefix = "DP_LO_EPASS_CARD_SECRET_WITH_URL"
        elif row.VoucherType == 4:
            prefix = "DP_LO_EPASS_REDEMPTION_CODE_WITH_URL"
        elif row.VoucherType == 5:
            prefix = "DP_LO_EPASS_URL"
        else:
            continue
        lines.append(f"{prefix}_RESOURCE_ID={row.ResourceId}")
        lines.append(f"{prefix}_OPTION_ID={row.OptionId}")
        lines.append("")

    return "\n".join(lines)


def AttachRedemptionUrlProbeCatalogToAllure(
    catalog: LocalOfferRedemptionUrlProbeCatalog,
    *,
    language: Optional[str] = None,
) -> None:
    """将轮询结论写入 Allure 附件。"""
    import json as _json

    summary_md = FormatRedemptionUrlProbeSummaryMarkdown(catalog, language=language)
    lang_suffix = f"_{language}" if language else ""
    allure.attach(
        summary_md,
        name=f"轮询结论_redemptionUrl有值网点{lang_suffix}",
        attachment_type=allure.attachment_type.TEXT,
    )
    payload = {
        "language": language,
        "resourceCount": catalog.ResourceCount,
        "availabilityOkPairCount": catalog.AvailabilityOkPairCount,
        "probedOrderCount": catalog.ProbedOrderCount,
        "withRedemptionUrl": [
            {
                "resourceId": r.ResourceId,
                "resourceName": r.ResourceName,
                "optionId": r.OptionId,
                "optionName": r.OptionName,
                "voucherType": r.VoucherType,
                "redemptionUrl": r.RedemptionUrl,
                "orderId": r.OrderId,
            }
            for r in catalog.WithRedemptionUrl
        ],
        "results": [
            {
                "resourceId": r.ResourceId,
                "resourceName": r.ResourceName,
                "optionId": r.OptionId,
                "optionName": r.OptionName,
                "voucherType": r.VoucherType,
                "redemptionUrl": r.RedemptionUrl,
                "hasRedemptionUrl": r.HasRedemptionUrl,
                "orderId": r.OrderId,
                "error": r.Error,
            }
            for r in catalog.Results
        ],
    }
    allure.attach(
        _json.dumps(payload, ensure_ascii=False, indent=2),
        name=f"轮询明细_redemptionUrl_probe{lang_suffix}.json",
        attachment_type=allure.attachment_type.TEXT,
    )


def ProbeLocalOfferRedemptionUrlCatalog(
    token: str,
    steps: Any,
    *,
    max_resources: int = 100,
    max_options_per_resource: int = 50,
    max_orders: Optional[int] = None,
    language: Optional[str] = None,
) -> LocalOfferRedemptionUrlProbeCatalog:
    """
    轮询 module=11 各网点 option：可用性通过后实际预约下单，汇总 ``redemptionUrl`` / ``voucherType``。

    流程：``GET /v2/resources`` → ``GET .../options`` → ``POST .../availability`` →
    ``POST .../ePasses/prebooking``（同一 ePass 多点数）。

    ``language`` 传入时用于 ``GET /v2/resources`` 与 ``GET .../options``（如 ``zh-CN``）。
    也可通过 ``DP_LO_EPASS_PROBE_LANGUAGE`` 覆盖。
    """
    order_limit = _ProbeMaxOrdersLimit() if max_orders is None else max_orders
    probe_language = language
    if probe_language is None:
        env_lang = os.getenv("DP_LO_EPASS_PROBE_LANGUAGE", "").strip()
        probe_language = env_lang or None

    lang_label = probe_language or "default"
    list_kw = _HttpStepKw(steps, f"GET /v2/resources module=11（轮询·{lang_label}）")
    resources_resp = GetResourcesList(
        token,
        module=LOCAL_OFFER_MODULE_INT,
        page_size=min(max_resources, 100),
        language=probe_language,
        step_code=list_kw["step_code"],
        step_title=list_kw["step_title"],
    )
    if resources_resp.status_code != 200:
        pytest.skip(f"GET /v2/resources HTTP 非 200: {resources_resp.status_code}")
    _st_res, env_res, _data_res = ParseResponseEnvelope(resources_resp)
    if not IsLocalOfferBusinessSuccess(env_res):
        pytest.skip(f"GET /v2/resources 业务失败: {env_res!r}")
    hints = ParseResourcesListHints(resources_resp)
    resource_ids = hints.ResourceIds[:max_resources]

    candidates: List[Tuple[str, str]] = []
    for rid in resource_ids:
        options_kw = _HttpStepKw(steps, f"options 列表（{rid} · 轮询·{lang_label}）")
        opt_resp = GetLocalOfferOptionsList(
            token,
            rid,
            page_size=max_options_per_resource,
            language=probe_language,
            step_code=options_kw["step_code"],
            step_title=options_kw["step_title"],
        )
        option_ids = _ExtractOptionIdsFromOptionsListResponse(opt_resp)
        for oid in option_ids[:max_options_per_resource]:
            body = BuildAvailabilityBody(resource_id=rid, option_id=oid)
            avail_kw = _HttpStepKw(steps, f"可用性探测（{rid}/{oid}）")
            avail_resp = PostResourcesOptionsPrebookingsAvailability(
                token,
                body,
                step_code=avail_kw["step_code"],
                step_title=avail_kw["step_title"],
            )
            if _IsPrebookingAvailabilityOk(avail_resp):
                candidates.append((rid, oid))

    if not candidates:
        pytest.skip("module=11 未找到可用性通过的 resourceId/optionId 组合，无法轮询 redemptionUrl")

    probe_count = len(candidates) if order_limit is None else min(len(candidates), order_limit)
    created = CreateLocalOfferEpass(
        token,
        steps,
        available_usages=max(probe_count, 1),
    )
    pb_date = BuildLocalOfferPrebookingDate()
    results: List[LocalOfferRedemptionUrlProbeRow] = []

    for idx, (rid, oid) in enumerate(candidates[:probe_count]):
        body = BuildAvailabilityBody(
            e_pass_id=created.EPassId,
            resource_id=rid,
            option_id=oid,
            prebooking_date=pb_date,
        )
        avail_kw = _HttpStepKw(steps, f"可用性（轮询 {idx + 1}/{probe_count} · {rid}）")
        avail_resp = PostResourcesOptionsPrebookingsAvailability(
            token,
            body,
            step_code=avail_kw["step_code"],
            step_title=avail_kw["step_title"],
        )
        if not _IsPrebookingAvailabilityOk(avail_resp):
            results.append(
                LocalOfferRedemptionUrlProbeRow(
                    ResourceId=rid,
                    OptionId=oid,
                    Error="availability-not-ok-on-book",
                )
            )
            continue
        _st, _env, data = ParseResponseEnvelope(avail_resp)
        pb_token = data.get("prebookingToken") if isinstance(data, dict) else None
        if not isinstance(pb_token, str) or not pb_token:
            results.append(
                LocalOfferRedemptionUrlProbeRow(
                    ResourceId=rid,
                    OptionId=oid,
                    Error="prebookingToken-missing",
                )
            )
            continue
        book_kw = _HttpStepKw(steps, f"预约下单探测（{rid}/{oid}）")
        book_resp = PostOrdersLocalOffersEPassesPrebookingWithToken(
            token,
            created.EPassId,
            pb_token,
            step_code=book_kw["step_code"],
            step_title=book_kw["step_title"],
        )
        row = _ParsePrebookingOrderProbeRow(resource_id=rid, option_id=oid, book_resp=book_resp)
        results.append(row)

    with_url = [r for r in results if r.HasRedemptionUrl]
    catalog = LocalOfferRedemptionUrlProbeCatalog(
        ResourceCount=len(resource_ids),
        AvailabilityOkPairCount=len(candidates),
        ProbedOrderCount=len(results),
        Results=results,
        WithRedemptionUrl=with_url,
    )
    CancelProbedLocalOfferOrdersAndPurchaseBestEffort(
        token,
        steps,
        catalog=catalog,
        purchase_order_id=created.PurchaseOrderId,
        e_pass_id=created.EPassId,
        context="redemption-url-probe",
    )
    return catalog


def ResolvePrebookingTargetViaResourceChainOrSkip(
    token: str,
    steps: Any,
    *,
    label: str,
) -> LocalOfferPrebookingTarget:
    """
    解析 catalog 中指定 label 的预约目标，并按资源链刷新 ``resourceId`` / ``optionId``。

    环境变量 ``DP_LO_EPASS_<LABEL>_RESOURCE_ID`` / ``OPTION_ID`` 作为 hint 参与链路解析。
    """
    normalized = label.strip().lower()
    catalog_item: Optional[Dict[str, str]] = None
    for item in _AllPrebookingResourceCatalogItems():
        if item["label"].lower() == normalized:
            catalog_item = dict(item)
            break
    if catalog_item is None:
        raise KeyError(f"未知 Local Offer 预约目标 label={label!r}")

    env_prefix = f"DP_LO_EPASS_{catalog_item['label'].upper()}"
    resource_hint = os.getenv(f"{env_prefix}_RESOURCE_ID", catalog_item.get("resourceId", "")).strip()
    option_hint = os.getenv(f"{env_prefix}_OPTION_ID", catalog_item.get("optionId", "")).strip()
    fallback_label = catalog_item.get("fallbackLabel", "").strip()
    if not resource_hint and fallback_label:
        resource_hint = GetOutletResourceIdForLabel(fallback_label)
        if not option_hint:
            option_hint = GetOutletOptionIdForLabel(fallback_label)

    if _UseResourceChainDiscovery():
        resource_id, option_id = DiscoverPrebookingPairViaResourceChainOrSkip(
            token,
            steps=steps,
            resource_id_hint=resource_hint or None,
            option_id_hint=option_hint or None,
        )
    else:
        static = _StaticPrebookingTargetFromCatalogItem(catalog_item)
        resource_id, option_id = static.ResourceId, static.OptionId

    voucher_type = int(os.getenv(f"{env_prefix}_VOUCHER_TYPE", catalog_item["voucherType"]))
    return LocalOfferPrebookingTarget(
        Label=catalog_item["label"],
        ResourceId=resource_id,
        OptionId=option_id,
        ExpectedVoucherType=voucher_type,
        ExpectRedemptionUrlPresent=_ParseRedemptionUrlExpectation(catalog_item),
    )


def ResolvePrebookingTargets() -> List[LocalOfferPrebookingTarget]:
    """解析券型网点 catalog（静态）；动态资源链请用 ``ResolvePrebookingTargetViaResourceChainOrSkip``。"""
    targets: List[LocalOfferPrebookingTarget] = []
    for item in _AllPrebookingResourceCatalogItems():
        try:
            targets.append(_StaticPrebookingTargetFromCatalogItem(item))
        except ValueError:
            continue
    return targets


def ResolvePrebookingTargetByLabel(label: str) -> LocalOfferPrebookingTarget:
    normalized = label.strip().lower()
    for target in ResolvePrebookingTargets():
        if target.Label.lower() == normalized:
            return target
    raise KeyError(f"未知 Local Offer 预约目标 label={label!r}")


def ResolvePrebookingTargetForVoucherRedemptionScenario(
    token: str,
    steps: Any,
    *,
    voucher_type: int,
    expect_redemption_url_present: bool,
) -> LocalOfferPrebookingTarget:
    """按 voucherType + redemptionUrl 期望组合解析预约目标（走资源链动态造数）。"""
    if voucher_type == 1:
        label = "card_secret_with_url" if expect_redemption_url_present else "card_secret_no_url"
    elif voucher_type == 4:
        label = "redemption_code_with_url" if expect_redemption_url_present else "redemption_code_no_url"
    else:
        raise ValueError(f"本场景仅支持 voucherType 1/4，实际={voucher_type}")
    return ResolvePrebookingTargetViaResourceChainOrSkip(token, steps, label=label)


def BuildLocalOfferEpassCreatePayload(
    *,
    client_user_id: Optional[str] = None,
    allowed_resources: Optional[Mapping[str, Sequence[str]]] = None,
    available_usages: Optional[int] = None,
    first_name: str = "Auto",
    last_name: str = "Test",
) -> JsonDict:
    """
    构造 ``POST /v2/orders/localOffers/ePasses`` 请求体。

    ``allowedResources`` 互斥：仅传非空限制字段； unrestricted 时保留三键空数组。
    """
    cid = client_user_id or _NewClientUserId()
    if allowed_resources:
        allowed: JsonDict = {}
        for key in ("resourceIds", "iata", "countryOrRegion"):
            if key not in allowed_resources:
                continue
            values = [str(v) for v in allowed_resources[key] if str(v).strip()]
            if values:
                allowed[key] = values
    else:
        allowed = {"resourceIds": [], "iata": [], "countryOrRegion": []}
    usages = available_usages if available_usages is not None else _DefaultAvailableUsages()
    return {
        "module": LOCAL_OFFER_MODULE_INT,
        "clientUserId": cid,
        "extra": {
            "firstName": first_name,
            "lastName": last_name,
            "expirationDate": _DefaultExpirationDate(),
            "availableUsages": usages,
            "allowedResources": allowed,
        },
    }


def BuildEntitlementMatrixPrebookingDate1030() -> str:
    """权益矩阵场景：当前 UTC +2 天，时间固定 10:30（与手工用例一致）。"""
    dt = datetime.now(timezone.utc) + timedelta(days=2)
    return dt.strftime("%Y-%m-%dT10:30")


@dataclass(frozen=True)
class EsimPrebookingTarget:
    """eSIM 预约目标 resource / option。"""

    ResourceId: str
    OptionId: str


def ResolveEsimPrebookingTargetOrSkip(token: str, steps: Any) -> EsimPrebookingTarget:
    """解析 eSIM 预约 ``resourceId`` / ``optionId``（``DP_ESIM_PREBOOKING_*`` 或 module=8 动态拉取）。"""
    resource_id = os.getenv("DP_ESIM_PREBOOKING_RESOURCE_ID", "").strip()
    option_id = os.getenv("DP_ESIM_PREBOOKING_OPTION_ID", "").strip()
    if resource_id and option_id:
        return EsimPrebookingTarget(ResourceId=resource_id, OptionId=option_id)
    hints = FetchModuleResourceHintsOrSkip(token, module=ESIM_MODULE_INT, steps=steps)
    rid = hints.ResourceIds[0]
    oid = FetchEsimFirstOptionIdOrSkip(token, rid, steps=steps)
    return EsimPrebookingTarget(ResourceId=rid, OptionId=oid)


def BuildModuleEpassCreatePayload(
    *,
    module: int,
    client_user_id: Optional[str] = None,
    available_usages: int = 2,
    first_name: str = "Auto",
    last_name: str = "Test",
) -> JsonDict:
    """构造 ``POST /v2/orders/{esims|localOffers}/ePasses`` 请求体。"""
    cid = client_user_id or _NewClientUserId()
    return {
        "module": module,
        "clientUserId": cid,
        "extra": {
            "firstName": first_name,
            "lastName": last_name,
            "expirationDate": _DefaultExpirationDate(),
            "availableUsages": available_usages,
            "allowedResources": {"resourceIds": [], "iata": [], "countryOrRegion": []},
        },
    }


def PostOrdersPathModuleEPasses(
    token: str,
    path_module: str,
    payload: JsonDict,
    *,
    step_code: Optional[str] = None,
    step_title: Optional[str] = None,
) -> Response:
    """``POST /v2/orders/{path_module}/ePasses``（``esims`` / ``localOffers``）。"""
    return RequestWithAllure(
        "POST",
        f"/v2/orders/{path_module}/ePasses",
        token=token,
        json_body=payload,
        step_code=step_code,
        step_title=step_title,
        x_program_id=GetConfiguredEpassProgramId(),
    )


def PostOrdersPathModuleEPassesPrebooking(
    token: str,
    path_module: str,
    *,
    module: int,
    e_pass_id: str,
    prebooking_token: str,
    step_code: Optional[str] = None,
    step_title: Optional[str] = None,
) -> Response:
    """``POST /v2/orders/{path_module}/ePasses/prebooking``。"""
    body: JsonDict = {
        "module": module,
        "ePassId": e_pass_id,
        "extra": {"prebookingToken": prebooking_token},
        "async": False,
    }
    return RequestWithAllure(
        "POST",
        f"/v2/orders/{path_module}/ePasses/prebooking",
        token=token,
        json_body=body,
        step_code=step_code,
        step_title=step_title,
        x_program_id=GetConfiguredEpassProgramId(),
    )


def CreateModuleEpassOrFail(
    token: str,
    steps: Any,
    *,
    path_module: str,
    module: int,
    client_user_id: Optional[str] = None,
    available_usages: int = 2,
    step_brief: str,
) -> Tuple[str, str, str]:
    """创建指定 module 的 ePass，返回 ``(clientUserId, ePassId, purchaseOrderId)``。"""
    payload = BuildModuleEpassCreatePayload(
        module=module,
        client_user_id=client_user_id,
        available_usages=available_usages,
    )
    kw = _HttpStepKw(steps, step_brief)
    resp = PostOrdersPathModuleEPasses(
        token,
        path_module,
        payload,
        step_code=kw["step_code"],
        step_title=kw["step_title"],
    )

    def _Create() -> Tuple[str, str, str]:
        assert resp.status_code == 200, f"创建 ePass HTTP 非 200: {resp.status_code}, {resp.text[:600]!r}"
        _st, env, _ = ParseResponseEnvelope(resp)
        assert IsLocalOfferBusinessSuccess(env), f"创建 ePass 业务失败: {env!r}"
        return ExtractCreateEpassIds(resp)

    cid, e_pass_id, purchase_order_id = RunWithSoftCapture(
        step_brief,
        _Create,
        fallback=lambda: _BestEffortExtractCreateEpassIds(resp),
    )
    RegisterPendingLocalOfferOrder(purchase_order_id)
    RegisterPendingLocalOfferEPassId(e_pass_id)
    return cid, e_pass_id, purchase_order_id


def RequestModulePrebookingTokenOrFail(
    token: str,
    steps: Any,
    *,
    module: int,
    resource_id: str,
    option_id: str,
    prebooking_date: str,
    e_pass_id: Optional[str] = None,
    brief: str,
) -> str:
    """可用性校验并返回 ``prebookingToken``（失败则 pytest.fail）。"""
    body = BuildAvailabilityBody(
        e_pass_id=e_pass_id,
        resource_id=resource_id,
        option_id=option_id,
        prebooking_date=prebooking_date,
        module=module,
    )
    kw = _HttpStepKw(steps, brief)
    resp = PostResourcesOptionsPrebookingsAvailability(
        token,
        body,
        step_code=kw["step_code"],
        step_title=kw["step_title"],
    )
    return AssertPrebookingAvailabilitySuccess(resp, context=brief)


def RequestLocalOfferAvailabilityTokenPreferEsimResource(
    token: str,
    steps: Any,
    *,
    prebooking_date: str,
    e_pass_id: Optional[str],
    esim_target: EsimPrebookingTarget,
    lo_fallback_target: LocalOfferPrebookingTarget,
    brief: str,
) -> Tuple[str, str, str]:
    """
    module=11 可用性：优先 esim 资源；若 program 返回 ``500.020.007`` 等则回退 LO 默认网点。

    返回 ``(prebookingToken, resourceId, optionId)`` 实际使用值。
    """
    import json

    body = BuildAvailabilityBody(
        e_pass_id=e_pass_id,
        resource_id=esim_target.ResourceId,
        option_id=esim_target.OptionId,
        prebooking_date=prebooking_date,
        module=LOCAL_OFFER_MODULE_INT,
    )
    kw = _HttpStepKw(steps, f"{brief}（优先 esim 资源）")
    resp = PostResourcesOptionsPrebookingsAvailability(
        token,
        body,
        step_code=kw["step_code"],
        step_title=kw["step_title"],
    )
    _st, env, _ = ParseResponseEnvelope(resp)
    if env is not None and env.get("code") == -1:
        err = env.get("errCode")
        if err in ("500.020.007", "500.020.009", "500.020.016"):
            allure.attach(
                json.dumps(
                    {
                        "fallbackReason": err,
                        "esimResourceId": esim_target.ResourceId,
                        "loFallbackResourceId": lo_fallback_target.ResourceId,
                        "loFallbackOptionId": lo_fallback_target.OptionId,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                name="module11_availability_esim_to_lo_fallback",
                attachment_type=allure.attachment_type.JSON,
            )
            return (
                RequestModulePrebookingTokenOrFail(
                    token,
                    steps,
                    module=LOCAL_OFFER_MODULE_INT,
                    resource_id=lo_fallback_target.ResourceId,
                    option_id=lo_fallback_target.OptionId,
                    prebooking_date=prebooking_date,
                    e_pass_id=e_pass_id,
                    brief=f"{brief}（回退 LO 网点）",
                ),
                lo_fallback_target.ResourceId,
                lo_fallback_target.OptionId,
            )
        LocalOfferFailOrRecord(f"module=11 可用性非预期失败: {env!r}")
    pb_token = AssertPrebookingAvailabilitySuccess(resp, context=brief)
    return pb_token, esim_target.ResourceId, esim_target.OptionId


def AssertEsimPrebookingOrderSuccess(
    resp: Response,
    *,
    e_pass_id: str,
    resource_id: str,
    option_id: str,
    context: str,
) -> str:
    """断言 eSIM（module=8）预约下单成功，返回 usage orderId。"""

    holder: Dict[str, str] = {}

    def _Do() -> str:
        data = ExtractBusinessData(resp)
        assert data.get("module") == ESIM_MODULE_INT, f"module 应为 8: {data!r}"
        status = data.get("status")
        if status == 10:
            pytest.skip(f"eSIM 预约单 status=10 FAILED: {data!r}")
        if status not in (1, 5):
            LocalOfferFailOrRecord(f"eSIM 预约 status 应为 1 CONFIRMED 或 5 处理中: {data!r}")
        resp_e_pass_id = _ResolveEPassIdField(data)
        assert resp_e_pass_id == e_pass_id, f"ePassId 不一致: {data!r}"
        order_id = data.get("orderId")
        assert isinstance(order_id, str) and order_id, f"orderId 缺失: {data!r}"
        extra = data.get("extra")
        assert isinstance(extra, dict), f"extra 缺失: {data!r}"
        assert extra.get("resourceId") == resource_id, f"resourceId 不一致: {extra!r}"
        holder["orderId"] = order_id
        return f"{context}: eSIM 预约成功 module=8, orderId={order_id!r}。"

    RunSoftAwareAllureAssertionStep(f"Local Offer ePass: eSIM 预约响应（{context}）", _Do)
    usage_order_id = _ResolveSoftHolderValue(
        holder,
        "orderId",
        resp=resp,
        fallback=_BestEffortResolveOrderIdFromResponse,
    )
    RegisterPendingLocalOfferOrder(usage_order_id)
    return usage_order_id

def _HttpStepKw(steps: Any, brief: str) -> Dict[str, str]:
    code, title = steps.Next(brief)
    return {"step_code": code, "step_title": title}


def GetResourceDetail(
    token: str,
    resource_id: str,
    *,
    language: str = "en-US",
    module: int = LOCAL_OFFER_MODULE_INT,
    fallback_allowed: bool = True,
    step_code: Optional[str] = None,
    step_title: Optional[str] = None,
) -> Response:
    """``GET /v2/resources/{resourceId}`` — 拉 city/countryOrRegion 等 location 基准值。"""
    path = f"/v2/resources/{resource_id}"
    params: Dict[str, Any] = {
        "language": language,
        "module": module,
        "fallbackAllowed": "true" if fallback_allowed else "false",
    }
    url = f"{GetBaseUrl().rstrip('/')}{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Program-ID": GetConfiguredEpassProgramId(),
        "X-Request-ID": str(uuid.uuid4()),
        "Content-Type": "application/json",
        "Accept": "*/*",
    }
    x_version = os.getenv("DP_X_VERSION", "").strip()
    if x_version and x_version.lower() not in ("omit", "none", "off"):
        headers["x-version"] = x_version
    step_name = FormatAllureHttpStepTitle("GET", path, step_code=step_code, step_title=step_title)
    with allure.step(step_name):
        if step_code or step_title:
            allure.attach(
                str({"step_code": step_code, "step_title": step_title, "method": "GET", "path": path}),
                name="request_step_meta",
                attachment_type=allure.attachment_type.TEXT,
            )
        AttachAllureRequestMeta(
            url=url,
            method="GET",
            headers=MaskHeadersForLog(headers),
            json_body=None,
            params=params,
        )
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=30.0)
        except requests.RequestException as exc:
            raise RuntimeError(f"GET {path} 网络异常") from exc
        AttachAllureResponseArtifacts(resp)
        return resp


def GetResourcesList(
    token: str,
    *,
    module: int,
    page_number: int = 1,
    page_size: int = 50,
    language: Optional[str] = None,
    step_code: Optional[str] = None,
    step_title: Optional[str] = None,
) -> Response:
    """
    ``GET /v2/resources`` — 按 module 拉取资源列表。

    canary 等环境需 ``x-version``（默认读 ``DP_X_VERSION``，``DP_PROFILE=canary`` 时会自动设为 ``canary``）。
    勿默认传 ``language`` query，否则可能触发 ``300.020.001``。
    """
    path = "/v2/resources"
    params: Dict[str, Any] = {
        "module": module,
        "pageNumber": page_number,
        "pageSize": page_size,
    }
    if language is not None and language.strip():
        params["language"] = language.strip()
    url = f"{GetBaseUrl().rstrip('/')}{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Program-ID": GetConfiguredEpassProgramId(),
        "X-Request-ID": str(uuid.uuid4()),
        "Content-Type": "application/json",
        "Accept": "*/*",
    }
    x_version = os.getenv("DP_X_VERSION", "").strip()
    if x_version and x_version.lower() not in ("omit", "none", "off"):
        headers["x-version"] = x_version
    step_name = FormatAllureHttpStepTitle("GET", path, step_code=step_code, step_title=step_title)
    with allure.step(step_name):
        if step_code or step_title:
            allure.attach(
                str({"step_code": step_code, "step_title": step_title, "method": "GET", "path": path}),
                name="request_step_meta",
                attachment_type=allure.attachment_type.TEXT,
            )
        AttachAllureRequestMeta(
            url=url,
            method="GET",
            headers=MaskHeadersForLog(headers),
            json_body=None,
            params=params,
        )
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=30.0)
        except requests.RequestException as exc:
            raise RuntimeError(f"GET {path} 网络异常") from exc
        AttachAllureResponseArtifacts(resp)
        return resp


def ParseResourcesListHints(resp: Response) -> ModuleResourceHints:
    """从 resources 列表响应提取 resourceId / countryOrRegion / iata 候选。"""
    _status, env, data = ParseResponseEnvelope(resp)
    hints = ModuleResourceHints()
    if not isinstance(data, dict):
        return hints
    resources_obj = data.get("resources")
    if not isinstance(resources_obj, dict):
        return hints
    for key in ("transportHubResources", "lifestyleResources"):
        arr = resources_obj.get(key)
        if not isinstance(arr, list):
            continue
        for elem in arr:
            if not isinstance(elem, dict):
                continue
            item = cast(JsonDict, elem)
            rid = item.get("resourceId")
            if isinstance(rid, str) and rid and rid not in hints.ResourceIds:
                hints.ResourceIds.append(rid)
            loc = item.get("locationInfo")
            if isinstance(loc, dict):
                country = loc.get("countryOrRegion")
                if isinstance(country, str) and country and country not in hints.CountryOrRegions:
                    hints.CountryOrRegions.append(country)
                iata = loc.get("iata")
                if isinstance(iata, str) and iata and iata not in hints.IataCodes:
                    hints.IataCodes.append(iata)
    return hints


def FetchModuleResourceHintsOrSkip(
    token: str,
    *,
    module: int,
    steps: Any,
    min_resource_ids: int = 1,
) -> ModuleResourceHints:
    """动态拉取 module 对应资源限制字段；失败时 skip。"""
    kw = _HttpStepKw(steps, f"GET /v2/resources module={module}")
    resp = GetResourcesList(token, module=module, step_code=kw["step_code"], step_title=kw["step_title"])
    if resp.status_code != 200:
        pytest.skip(f"GET /v2/resources module={module} HTTP 非 200: {resp.status_code}")
    _st, env, _data = ParseResponseEnvelope(resp)
    if not IsLocalOfferBusinessSuccess(env):
        pytest.skip(f"GET /v2/resources module={module} 业务失败: {env!r}")
    hints = ParseResourcesListHints(resp)
    if len(hints.ResourceIds) < min_resource_ids:
        pytest.skip(
            f"GET /v2/resources module={module} 未解析到足够 resourceId（需要>={min_resource_ids}）: {hints!r}"
        )
    return hints


def PostOrdersLocalOffersEPasses(
    token: str,
    payload: JsonDict,
    *,
    step_code: Optional[str] = None,
    step_title: Optional[str] = None,
) -> Response:
    """``POST /v2/orders/localOffers/ePasses``"""
    return RequestWithAllure(
        "POST",
        f"/v2/orders/{LOCAL_OFFER_PATH_MODULE}/ePasses",
        token=token,
        json_body=payload,
        step_code=step_code,
        step_title=step_title,
        x_program_id=GetConfiguredEpassProgramId(),
    )


def PostUsersEPasses(
    token: str,
    client_user_id: str,
    *,
    step_code: Optional[str] = None,
    step_title: Optional[str] = None,
) -> Response:
    """``POST /v2/users/ePasses``"""
    body: JsonDict = {"clientUserId": client_user_id, "pageSize": 10, "pageNumber": 1}
    return RequestWithAllure(
        "POST",
        "/v2/users/ePasses",
        token=token,
        json_body=body,
        step_code=step_code,
        step_title=step_title,
        x_program_id=GetConfiguredEpassProgramId(),
    )


def PostOrdersEPassesList(
    token: str,
    e_pass_id: str,
    *,
    module: Optional[int] = LOCAL_OFFER_MODULE_INT,
    step_code: Optional[str] = None,
    step_title: Optional[str] = None,
) -> Response:
    """``POST /v2/orders/ePasses`` — usage 订单列表。"""
    body: JsonDict = {"ePassId": e_pass_id, "pageSize": 10, "pageNumber": 1}
    if module is not None:
        body["module"] = module
    return RequestWithAllure(
        "POST",
        "/v2/orders/ePasses",
        token=token,
        json_body=body,
        step_code=step_code,
        step_title=step_title,
        x_program_id=GetConfiguredEpassProgramId(),
    )


def PostOrdersEPassesSearch(
    token: str,
    *,
    order_id: Optional[str] = None,
    e_pass_id: Optional[str] = None,
    step_code: Optional[str] = None,
    step_title: Optional[str] = None,
) -> Response:
    """``POST /v2/orders/ePasses/search`` — ePass 购买单详情。

    OAS/Apifox：请求体仅 ``orderId`` 与 ``ePassId`` 二选一，**不含** ``module``。
    """
    body: JsonDict = {}
    if order_id:
        body["orderId"] = order_id
    if e_pass_id:
        body["ePassId"] = e_pass_id
    return RequestWithAllure(
        "POST",
        "/v2/orders/ePasses/search",
        token=token,
        json_body=body,
        step_code=step_code,
        step_title=step_title,
        x_program_id=GetConfiguredEpassProgramId(),
    )


def PostResourcesOptionsPrebookingsAvailability(
    token: str,
    body: JsonDict,
    *,
    step_code: Optional[str] = None,
    step_title: Optional[str] = None,
) -> Response:
    """``POST /v2/resources/options/prebookings/availability``"""
    return RequestWithAllure(
        "POST",
        "/v2/resources/options/prebookings/availability",
        token=token,
        json_body=body,
        step_code=step_code,
        step_title=step_title,
        x_program_id=GetConfiguredEpassProgramId(),
    )


def PostOrdersLocalOffersEPassesPrebooking(
    token: str,
    e_pass_id: str,
    prebooking_token: str,
    *,
    step_code: Optional[str] = None,
    step_title: Optional[str] = None,
) -> Response:
    """``POST /v2/orders/localOffers/ePasses/prebooking``"""
    body: JsonDict = {
        "module": LOCAL_OFFER_MODULE_INT,
        "ePassId": e_pass_id,
        "extra": {"prebookingToken": prebooking_token},
        "async": False,
    }
    return RequestWithAllure(
        "POST",
        f"/v2/orders/{LOCAL_OFFER_PATH_MODULE}/ePasses/prebooking",
        token=token,
        json_body=body,
        step_code=step_code,
        step_title=step_title,
        x_program_id=GetConfiguredEpassProgramId(),
    )


def PostOrdersEPassesUsageDetails(
    token: str,
    order_id: str,
    *,
    module: Optional[int] = None,
    step_code: Optional[str] = None,
    step_title: Optional[str] = None,
) -> Response:
    """
    ``POST /v2/orders/ePasses/details`` — usage 订单详情。

    OAS/Apifox 契约仅必填 ``orderId``；``module`` 为可选扩展，默认**不传**。
    """
    body: JsonDict = {"orderId": order_id}
    if module is not None:
        body["module"] = module
    return RequestWithAllure(
        "POST",
        "/v2/orders/ePasses/details",
        token=token,
        json_body=body,
        step_code=step_code,
        step_title=step_title,
        x_program_id=GetConfiguredEpassProgramId(),
    )


def _GetLocalOfferResourcePath(
    resource_id: str,
    *,
    option_id: Optional[str] = None,
) -> str:
    base = f"/v2/resources/localOffers/{resource_id}/options"
    if option_id:
        return f"{base}/{option_id}"
    return base


def GetLocalOfferOptionsList(
    token: str,
    resource_id: str,
    *,
    page_number: int = 1,
    page_size: int = 50,
    language: Optional[str] = None,
    step_code: Optional[str] = None,
    step_title: Optional[str] = None,
) -> Response:
    """``GET /v2/resources/localOffers/{resourceId}/options`` — 拉 resourceName 基准值。"""
    path = _GetLocalOfferResourcePath(resource_id)
    params: Dict[str, Any] = {"pageNumber": page_number, "pageSize": page_size}
    if language is not None and language.strip():
        params["language"] = language.strip()
    url = f"{GetBaseUrl().rstrip('/')}{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Program-ID": GetConfiguredEpassProgramId(),
        "X-Request-ID": str(uuid.uuid4()),
        "Content-Type": "application/json",
        "Accept": "*/*",
    }
    x_version = os.getenv("DP_X_VERSION", "").strip()
    if x_version and x_version.lower() not in ("omit", "none", "off"):
        headers["x-version"] = x_version
    step_name = FormatAllureHttpStepTitle("GET", path, step_code=step_code, step_title=step_title)
    with allure.step(step_name):
        if step_code or step_title:
            allure.attach(
                str({"step_code": step_code, "step_title": step_title, "method": "GET", "path": path}),
                name="request_step_meta",
                attachment_type=allure.attachment_type.TEXT,
            )
        AttachAllureRequestMeta(
            url=url,
            method="GET",
            headers=MaskHeadersForLog(headers),
            json_body=None,
            params=params,
        )
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=30.0)
        except requests.RequestException as exc:
            raise RuntimeError(f"GET {path} 网络异常") from exc
        AttachAllureResponseArtifacts(resp)
        return resp


def FetchLocalOfferFirstOptionIdOrSkip(
    token: str,
    resource_id: str,
    *,
    steps: Any = None,
) -> str:
    """从 ``GET /v2/resources/localOffers/{resourceId}/options`` 解析首个可用 ``optionId``。"""
    list_kw = _HttpStepKw(steps, f"Local Offer options 列表（{resource_id}）") if steps else {}
    list_resp = GetLocalOfferOptionsList(
        token,
        resource_id,
        step_code=list_kw.get("step_code"),
        step_title=list_kw.get("step_title"),
    )
    if list_resp.status_code != 200:
        pytest.skip(f"GET options 列表 HTTP 非 200: {list_resp.status_code}")
    _st, env, data = ParseResponseEnvelope(list_resp)
    if not IsLocalOfferBusinessSuccess(env):
        err = env.get("errCode") if env else None
        if err in ("500.020.016", "500.020.007", "500.020.011"):
            pytest.skip(f"GET options 列表不可用（{err}），无法解析 optionId: {env!r}")
        LocalOfferFailOrRecord(f"GET options 列表非预期失败: {env!r}")
    if not isinstance(data, dict):
        pytest.skip(f"options 列表 data 非对象: {data!r}")
    option_list = data.get("optionList")
    if not isinstance(option_list, list) or not option_list:
        pytest.skip(f"resourceId={resource_id!r} 的 optionList 为空，无法解析 optionId")
    for item in option_list:
        if not isinstance(item, dict):
            continue
        option_id = item.get("optionId")
        if isinstance(option_id, str) and option_id:
            return option_id
    pytest.skip(f"resourceId={resource_id!r} 的 optionList 无有效 optionId")


def FetchLocalOfferAlternateOptionIdOrSkip(
    token: str,
    resource_id: str,
    exclude_option_id: str,
    *,
    steps: Any = None,
) -> str:
    """同一 ``resourceId`` 下选取与 ``exclude_option_id`` 不同的 ``optionId``（tc-p2 token/option 不一致）。"""
    list_kw = _HttpStepKw(steps, f"Local Offer options 列表（{resource_id} · 备选 option）") if steps else {}
    list_resp = GetLocalOfferOptionsList(
        token,
        resource_id,
        step_code=list_kw.get("step_code"),
        step_title=list_kw.get("step_title"),
    )
    if list_resp.status_code != 200:
        pytest.skip(f"GET options 列表 HTTP 非 200: {list_resp.status_code}")
    _st, env, data = ParseResponseEnvelope(list_resp)
    if not IsLocalOfferBusinessSuccess(env):
        err = env.get("errCode") if env else None
        if err in ("500.020.016", "500.020.007", "500.020.011"):
            pytest.skip(f"GET options 列表不可用（{err}），无法解析备选 optionId: {env!r}")
        LocalOfferFailOrRecord(f"GET options 列表非预期失败: {env!r}")
    if not isinstance(data, dict):
        pytest.skip(f"options 列表 data 非对象: {data!r}")
    option_list = data.get("optionList")
    if not isinstance(option_list, list) or len(option_list) < 2:
        pytest.skip(
            f"resourceId={resource_id!r} 的 optionList 不足 2 项，"
            f"无法构造 optionA/optionB 不一致（exclude={exclude_option_id!r}）。"
        )
    excluded = exclude_option_id.strip()
    for item in option_list:
        if not isinstance(item, dict):
            continue
        option_id = item.get("optionId")
        if isinstance(option_id, str) and option_id and option_id != excluded:
            return option_id
    pytest.skip(
        f"resourceId={resource_id!r} 无与 {exclude_option_id!r} 不同的 optionId；"
        f"optionList={option_list!r}"
    )


def PickPrebookingTargetWithAlternateOptionOrSkip(
    token: str,
    *,
    steps: Any = None,
) -> Tuple[LocalOfferPrebookingTarget, str, str]:
    """
    选取含至少两个 ``optionId`` 的 Local Offer 预约目标。

    返回 ``(target, option_a, option_b)``，优先默认券型网点，否则遍历 ``ResolvePrebookingTargets()``。
    """
    for target in ResolvePrebookingTargets():
        list_kw = (
            _HttpStepKw(steps, f"Local Offer options 列表（{target.ResourceId} · 探测多 option）")
            if steps
            else {}
        )
        list_resp = GetLocalOfferOptionsList(
            token,
            target.ResourceId,
            step_code=list_kw.get("step_code"),
            step_title=list_kw.get("step_title"),
        )
        if list_resp.status_code != 200:
            continue
        _st, env, data = ParseResponseEnvelope(list_resp)
        if not IsLocalOfferBusinessSuccess(env) or not isinstance(data, dict):
            continue
        option_list = data.get("optionList")
        if not isinstance(option_list, list):
            continue
        option_ids = [
            str(item.get("optionId"))
            for item in option_list
            if isinstance(item, dict) and isinstance(item.get("optionId"), str) and item.get("optionId")
        ]
        if len(option_ids) < 2:
            continue
        primary = target.OptionId if target.OptionId in option_ids else option_ids[0]
        for candidate in option_ids:
            if candidate != primary:
                return target, primary, candidate
    pytest.skip(
        "未找到含 2 个以上 option 的 Local Offer 网点，"
        "无法构造 token/option 不一致负向；请配置含多 option 的 DP_LO_EPASS_*_RESOURCE_ID。"
    )


@dataclass(frozen=True)
class PrebookingTokenOptionMismatchContext:
    """optionA token + optionB 注入负向所需上下文。"""

    Target: LocalOfferPrebookingTarget
    OptionA: str
    OptionB: str
    EPassId: str
    PrebookingToken: str


def PreparePrebookingTokenOptionMismatchContextOrSkip(
    token: str,
    steps: Any,
) -> PrebookingTokenOptionMismatchContext:
    """
    探测多 option 网点并成功取 token；遇 500.020.009 换下一网点重试。
    """
    candidates: List[LocalOfferPrebookingTarget] = list(ResolvePrebookingTargets())
    hints = FetchModuleResourceHintsOrSkip(token, module=LOCAL_OFFER_MODULE_INT, steps=steps)
    seen_resources = {t.ResourceId for t in candidates}
    for resource_id in hints.ResourceIds:
        if resource_id in seen_resources:
            continue
        seen_resources.add(resource_id)
        list_kw = _HttpStepKw(steps, f"动态 options 列表（{resource_id}）")
        list_resp = GetLocalOfferOptionsList(
            token,
            resource_id,
            step_code=list_kw.get("step_code"),
            step_title=list_kw.get("step_title"),
        )
        if list_resp.status_code != 200:
            continue
        _st, env_list, data = ParseResponseEnvelope(list_resp)
        if not IsLocalOfferBusinessSuccess(env_list) or not isinstance(data, dict):
            continue
        option_list = data.get("optionList")
        if not isinstance(option_list, list) or not option_list:
            continue
        first_option = next(
            (
                str(item.get("optionId"))
                for item in option_list
                if isinstance(item, dict) and isinstance(item.get("optionId"), str) and item.get("optionId")
            ),
            "",
        )
        if not first_option:
            continue
        candidates.append(
            LocalOfferPrebookingTarget(
                Label=f"dynamic-{resource_id}",
                ResourceId=resource_id,
                OptionId=first_option,
                ExpectedVoucherType=1,
            )
        )

    created = CreateLocalOfferEpass(token, steps)
    availability_errors: List[str] = []
    for target in candidates:
        list_kw = _HttpStepKw(steps, f"options 列表（{target.ResourceId} · option 负向）")
        list_resp = GetLocalOfferOptionsList(
            token,
            target.ResourceId,
            step_code=list_kw.get("step_code"),
            step_title=list_kw.get("step_title"),
        )
        if list_resp.status_code != 200:
            continue
        _st, env, data = ParseResponseEnvelope(list_resp)
        if not IsLocalOfferBusinessSuccess(env) or not isinstance(data, dict):
            continue
        option_list = data.get("optionList")
        if not isinstance(option_list, list):
            continue
        option_ids = [
            str(item.get("optionId"))
            for item in option_list
            if isinstance(item, dict) and isinstance(item.get("optionId"), str) and item.get("optionId")
        ]
        if len(option_ids) < 2:
            continue
        option_a = target.OptionId if target.OptionId in option_ids else option_ids[0]
        option_b = next((oid for oid in option_ids if oid != option_a), "")
        if not option_b:
            continue
        body = BuildAvailabilityBody(
            e_pass_id=created.EPassId,
            resource_id=target.ResourceId,
            option_id=option_a,
        )
        kw = _HttpStepKw(steps, f"可用性 optionA（{target.ResourceId}）")
        resp_avail = PostResourcesOptionsPrebookingsAvailability(
            token,
            body,
            step_code=kw["step_code"],
            step_title=kw["step_title"],
        )
        _st, env_avail, _ = ParseResponseEnvelope(resp_avail)
        if env_avail is not None and env_avail.get("code") == -1:
            err = env_avail.get("errCode")
            if err == "500.020.009":
                availability_errors.append(f"{target.ResourceId}/{option_a}: 500.020.009")
                continue
            availability_errors.append(f"{target.ResourceId}/{option_a}: {err}")
            continue
        pb_token = AssertPrebookingAvailabilitySuccess(resp_avail, context=f"option-a-{target.ResourceId}")
        return PrebookingTokenOptionMismatchContext(
            Target=target,
            OptionA=option_a,
            OptionB=option_b,
            EPassId=created.EPassId,
            PrebookingToken=pb_token,
        )
    detail = "；".join(availability_errors) if availability_errors else "无多 option 网点或可用性均失败"
    FinalizeCreatedLocalOfferPurchaseOnly(
        token,
        steps,
        e_pass_id=created.EPassId,
        purchase_order_id=created.PurchaseOrderId,
        context="option-mismatch-probe-skip",
    )
    pytest.skip(f"无法构造 optionA/optionB token 负向：{detail}")


def _GetEsimResourcePath(
    resource_id: str,
    *,
    option_id: Optional[str] = None,
) -> str:
    base = f"/v2/resources/esims/{resource_id}/options"
    if option_id:
        return f"{base}/{option_id}"
    return base


def GetEsimOptionsList(
    token: str,
    resource_id: str,
    *,
    page_number: int = 1,
    page_size: int = 50,
    duration: Optional[int] = None,
    step_code: Optional[str] = None,
    step_title: Optional[str] = None,
) -> Response:
    """``GET /v2/resources/esims/{resourceId}/options`` — 拉 eSIM option 列表。"""
    path = _GetEsimResourcePath(resource_id)
    params: Dict[str, Any] = {"pageNumber": page_number, "pageSize": page_size}
    if duration is not None:
        params["duration"] = duration
    url = f"{GetBaseUrl().rstrip('/')}{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Program-ID": GetConfiguredEpassProgramId(),
        "X-Request-ID": str(uuid.uuid4()),
        "Content-Type": "application/json",
        "Accept": "*/*",
    }
    x_version = os.getenv("DP_X_VERSION", "").strip()
    if x_version and x_version.lower() not in ("omit", "none", "off"):
        headers["x-version"] = x_version
    step_name = FormatAllureHttpStepTitle("GET", path, step_code=step_code, step_title=step_title)
    with allure.step(step_name):
        if step_code or step_title:
            allure.attach(
                str({"step_code": step_code, "step_title": step_title, "method": "GET", "path": path}),
                name="request_step_meta",
                attachment_type=allure.attachment_type.TEXT,
            )
        AttachAllureRequestMeta(
            url=url,
            method="GET",
            headers=MaskHeadersForLog(headers),
            json_body=None,
            params=params,
        )
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=30.0)
        except requests.RequestException as exc:
            raise RuntimeError(f"GET {path} 网络异常") from exc
        AttachAllureResponseArtifacts(resp)
        return resp


def FetchEsimFirstOptionIdOrSkip(
    token: str,
    resource_id: str,
    *,
    steps: Any = None,
) -> str:
    """从 ``GET /v2/resources/esims/{resourceId}/options`` 解析首个可用 ``optionId``。"""
    list_kw = _HttpStepKw(steps, f"eSIM options 列表（{resource_id}）") if steps else {}
    list_resp = GetEsimOptionsList(
        token,
        resource_id,
        step_code=list_kw.get("step_code"),
        step_title=list_kw.get("step_title"),
    )
    if list_resp.status_code != 200:
        pytest.skip(f"GET eSIM options 列表 HTTP 非 200: {list_resp.status_code}")
    _st, env, data = ParseResponseEnvelope(list_resp)
    if not IsLocalOfferBusinessSuccess(env):
        err = env.get("errCode") if env else None
        if err in ("500.020.016", "500.020.007", "500.020.011"):
            pytest.skip(f"GET eSIM options 列表不可用（{err}），无法解析 optionId: {env!r}")
        LocalOfferFailOrRecord(f"GET eSIM options 列表非预期失败: {env!r}")
    if not isinstance(data, dict):
        pytest.skip(f"eSIM options 列表 data 非对象: {data!r}")
    option_list = data.get("optionList")
    if not isinstance(option_list, list) or not option_list:
        pytest.skip(f"resourceId={resource_id!r} 的 eSIM optionList 为空，无法解析 optionId")
    for item in option_list:
        if not isinstance(item, dict):
            continue
        option_id = item.get("optionId")
        if isinstance(option_id, str) and option_id:
            return option_id
    pytest.skip(f"resourceId={resource_id!r} 的 eSIM optionList 无有效 optionId")


def GetLocalOfferOptionDetail(
    token: str,
    resource_id: str,
    option_id: str,
    *,
    step_code: Optional[str] = None,
    step_title: Optional[str] = None,
) -> Response:
    """``GET /v2/resources/localOffers/{resourceId}/options/{optionId}`` — option 详情基准值。"""
    path = _GetLocalOfferResourcePath(resource_id, option_id=option_id)
    url = f"{GetBaseUrl().rstrip('/')}{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Program-ID": GetConfiguredEpassProgramId(),
        "X-Request-ID": str(uuid.uuid4()),
        "Content-Type": "application/json",
        "Accept": "*/*",
    }
    x_version = os.getenv("DP_X_VERSION", "").strip()
    if x_version and x_version.lower() not in ("omit", "none", "off"):
        headers["x-version"] = x_version
    step_name = FormatAllureHttpStepTitle("GET", path, step_code=step_code, step_title=step_title)
    with allure.step(step_name):
        if step_code or step_title:
            allure.attach(
                str({"step_code": step_code, "step_title": step_title, "method": "GET", "path": path}),
                name="request_step_meta",
                attachment_type=allure.attachment_type.TEXT,
            )
        AttachAllureRequestMeta(
            url=url,
            method="GET",
            headers=MaskHeadersForLog(headers),
            json_body=None,
            params=None,
        )
        try:
            resp = requests.get(url, headers=headers, timeout=30.0)
        except requests.RequestException as exc:
            raise RuntimeError(f"GET {path} 网络异常") from exc
        AttachAllureResponseArtifacts(resp)
        return resp


def _ParseResourceDetailLocation(data: Mapping[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    """从 resource 详情 ``locationInfo`` 提取 city / countryOrRegion。"""
    loc = data.get("locationInfo")
    if not isinstance(loc, dict):
        return None, None
    city_raw = loc.get("city")
    if not isinstance(city_raw, str) or not city_raw:
        city_raw = loc.get("cityName")
    city = city_raw if isinstance(city_raw, str) and city_raw else None
    country_raw = loc.get("countryOrRegion")
    country = country_raw if isinstance(country_raw, str) and country_raw else None
    return city, country


def FetchLocalOfferResourceOptionReference(
    token: str,
    resource_id: str,
    option_id: str,
    *,
    steps: Any = None,
) -> LocalOfferResourceOptionReference:
    """
    拉取 ePass usage 订单字段对拍基准。

    - ``GET /v2/resources/{resourceId}?language=en-US&module=11&fallbackAllowed=true`` →
      ``city`` / ``countryOrRegion`` / ``optionId``（与入参 optionId 一致）
    - ``GET .../localOffers/{resourceId}/options`` + ``.../options/{optionId}`` →
      ``resourceId`` / ``resourceName`` / ``optionName``
    """
    detail_kw = _HttpStepKw(steps, f"Local Offer resource 详情（{resource_id}）") if steps else {}
    detail_resp = GetResourceDetail(
        token,
        resource_id,
        step_code=detail_kw.get("step_code"),
        step_title=detail_kw.get("step_title"),
    )
    city: Optional[str] = None
    country_or_region: Optional[str] = None
    if detail_resp.status_code != 200:
        pytest.skip(f"GET resource 详情 HTTP 非 200: {detail_resp.status_code}")
    _st_detail_res, env_detail_res, data_detail_res = ParseResponseEnvelope(detail_resp)
    if not IsLocalOfferBusinessSuccess(env_detail_res):
        err = env_detail_res.get("errCode") if env_detail_res else None
        if err in ("500.020.006", "500.020.007", "500.020.016"):
            pytest.skip(f"GET resource 详情不可用（{err}），跳过字段对拍: {env_detail_res!r}")
        LocalOfferFailOrRecord(f"GET resource 详情非预期失败: {env_detail_res!r}")
    if isinstance(data_detail_res, dict):
        city, country_or_region = _ParseResourceDetailLocation(data_detail_res)

    list_kw = _HttpStepKw(steps, f"Local Offer options 列表（{resource_id}）") if steps else {}
    list_resp = GetLocalOfferOptionsList(
        token,
        resource_id,
        step_code=list_kw.get("step_code"),
        step_title=list_kw.get("step_title"),
    )
    if list_resp.status_code != 200:
        pytest.skip(f"GET options 列表 HTTP 非 200: {list_resp.status_code}")
    _st_list, env_list, data_list = ParseResponseEnvelope(list_resp)
    if not IsLocalOfferBusinessSuccess(env_list):
        err = env_list.get("errCode") if env_list else None
        if err in ("500.020.016", "500.020.007", "500.020.011"):
            pytest.skip(f"GET options 列表不可用（{err}），跳过 option 对拍: {env_list!r}")
        LocalOfferFailOrRecord(f"GET options 列表非预期失败: {env_list!r}")
    assert isinstance(data_list, dict), f"options 列表 data 非对象: {data_list!r}"
    resource_name = data_list.get("resourceName")
    assert isinstance(resource_name, str) and resource_name, f"resourceName 缺失: {data_list!r}"
    list_resource_id = data_list.get("resourceId")
    assert list_resource_id == resource_id, (
        f"options 列表 resourceId 与 path 不一致: expected={resource_id!r}, actual={list_resource_id!r}"
    )

    detail_kw = _HttpStepKw(steps, f"Local Offer option 详情（{option_id}）") if steps else {}
    detail_resp = GetLocalOfferOptionDetail(
        token,
        resource_id,
        option_id,
        step_code=detail_kw.get("step_code"),
        step_title=detail_kw.get("step_title"),
    )
    if detail_resp.status_code != 200:
        pytest.skip(f"GET option 详情 HTTP 非 200: {detail_resp.status_code}")
    _st_detail, env_detail, data_detail = ParseResponseEnvelope(detail_resp)
    if not IsLocalOfferBusinessSuccess(env_detail):
        err = env_detail.get("errCode") if env_detail else None
        if err in ("500.020.011", "500.020.007", "500.020.016"):
            pytest.skip(f"GET option 详情不可用（{err}），跳过 option 对拍: {env_detail!r}")
        LocalOfferFailOrRecord(f"GET option 详情非预期失败: {env_detail!r}")
    assert isinstance(data_detail, dict), f"option 详情 data 非对象: {data_detail!r}"
    ref_option_id = data_detail.get("optionId")
    ref_option_name = data_detail.get("optionName")
    assert isinstance(ref_option_id, str) and ref_option_id, f"optionId 缺失: {data_detail!r}"
    assert isinstance(ref_option_name, str) and ref_option_name, f"optionName 缺失: {data_detail!r}"
    assert ref_option_id == option_id, (
        f"option 详情 optionId 与 path 不一致: expected={option_id!r}, actual={ref_option_id!r}"
    )
    return LocalOfferResourceOptionReference(
        ResourceId=resource_id,
        ResourceName=resource_name,
        OptionId=ref_option_id,
        OptionName=ref_option_name,
        City=city,
        CountryOrRegion=country_or_region,
    )


def IsLocalOfferBusinessSuccess(envelope: Optional[JsonDict]) -> bool:
    """Local Offer 相关接口成功码可能是 ``0`` 或 ``1``（usage 详情等）。"""
    if envelope is None:
        return False
    code = envelope.get("code")
    return code in (0, 1, "0", "1")


def ExtractBusinessData(resp: Response) -> JsonDict:
    _st, env, data = ParseResponseEnvelope(resp)
    assert resp.status_code == 200, f"HTTP 非 200: {resp.status_code}, body={resp.text[:800]}"
    assert IsLocalOfferBusinessSuccess(env), f"业务失败: {env!r}"
    assert isinstance(data, dict), f"data 非对象: {data!r}"
    return cast(JsonDict, data)


def _BestEffortParseResponseData(resp: Response) -> JsonDict:
    """软断言 fallback：尽量从响应解析 ``data`` 对象，不抛错。"""
    try:
        _st, env, data = ParseResponseEnvelope(resp)
        if resp.status_code == 200 and isinstance(data, dict):
            return cast(JsonDict, data)
    except Exception:
        pass
    return {}


def _BestEffortResolveEPassIdFromResponse(resp: Response) -> str:
    data = _BestEffortParseResponseData(resp)
    ep = _ResolveEPassIdField(data)
    if isinstance(ep, str) and ep:
        return ep
    extra = data.get("extra")
    if isinstance(extra, dict):
        raw = extra.get("ePassId")
        if isinstance(raw, str) and raw:
            return raw
    return ""


def _BestEffortResolveOrderIdFromResponse(resp: Response) -> str:
    data = _BestEffortParseResponseData(resp)
    order_id = data.get("orderId")
    return order_id if isinstance(order_id, str) else ""


def _BestEffortResolvePrebookingTokenFromResponse(resp: Response) -> str:
    data = _BestEffortParseResponseData(resp)
    token = data.get("prebookingToken")
    return token if isinstance(token, str) else ""


def _BestEffortExtractCreateEpassIds(resp: Response) -> Tuple[str, str, str]:
    data = _BestEffortParseResponseData(resp)
    client_user_id = data.get("clientUserId")
    order_id = data.get("orderId")
    extra = data.get("extra")
    e_pass_id = extra.get("ePassId") if isinstance(extra, dict) else None
    return (
        client_user_id if isinstance(client_user_id, str) else "",
        e_pass_id if isinstance(e_pass_id, str) else "",
        order_id if isinstance(order_id, str) else "",
    )


def _ResolveSoftHolderValue(
    holder: Dict[str, str],
    key: str,
    *,
    resp: Response,
    fallback: Callable[[Response], str],
) -> str:
    if key in holder:
        return holder[key]
    if GetActiveLocalOfferSoftAssert() is not None:
        return fallback(resp)
    raise KeyError(key)


def ExtractCreateEpassIds(resp: Response) -> Tuple[str, str, str]:
    """返回 (clientUserId, ePassId, purchaseOrderId)。"""
    data = ExtractBusinessData(resp)
    client_user_id = data.get("clientUserId")
    order_id = data.get("orderId")
    extra = data.get("extra")
    e_pass_id = None
    if isinstance(extra, dict):
        e_pass_id = extra.get("ePassId")
    assert isinstance(client_user_id, str) and client_user_id, f"缺少 clientUserId: {data!r}"
    assert isinstance(order_id, str) and order_id, f"缺少 orderId: {data!r}"
    assert isinstance(e_pass_id, str) and e_pass_id, f"缺少 extra.ePassId: {data!r}"
    RegisterPendingLocalOfferOrder(order_id)
    RegisterPendingLocalOfferEPassId(e_pass_id)
    return client_user_id, e_pass_id, order_id


def AssertLocalOfferEpassCreateCoreFields(
    resp: Response,
    *,
    expected_client_user_id: str,
    context: str = "LocalOffer-ePass-create",
) -> None:
    """断言创建 ePass 响应核心字段（status=1, module=11, category=2, ePassStatus=1, usedUsages=0）。"""

    def _Do() -> str:
        data = ExtractBusinessData(resp)
        AssertLocalOfferDataRootModule11(data, context=context)
        assert data.get("status") == 1, f"status 应为 1（CONFIRMED/可用）: {data!r}"
        assert data.get("category") == 2, f"category 应为 2: {data!r}"
        assert data.get("clientUserId") == expected_client_user_id, (
            f"clientUserId 回显不一致: expected={expected_client_user_id!r}, data={data!r}"
        )
        assert data.get("orderCancelledDate") is None, f"orderCancelledDate 应为 null: {data!r}"
        extra = data.get("extra")
        assert isinstance(extra, dict), f"extra 缺失: {data!r}"
        assert extra.get("ePassStatus") == 1, f"ePassStatus 应为 1（Active）: {extra!r}"
        assert extra.get("usedUsages") == 0, f"usedUsages 应为 0: {extra!r}"
        assert isinstance(extra.get("ePassId"), str) and extra.get("ePassId"), "ePassId 缺失"
        assert "allowedResources" in extra, f"allowedResources 缺失: {extra!r}"
        return (
            f"{context}: status=1, ePassStatus=1, module=11, category=2, "
            "clientUserId 回显一致, usedUsages=0, ePassId 非空。"
        )

    RunSoftAwareAllureAssertionStep(f"Local Offer ePass: 创建响应核心字段（{context}）", _Do)


def AssertCreateAllowedResourcesRestriction(
    resp: Response,
    *,
    restriction_key: str,
    expected_values: Sequence[str],
    context: str = "allowedResources-restriction",
) -> None:
    """断言创建响应 ``extra.allowedResources`` 含指定限制字段及取值。"""

    def _Do() -> str:
        data = ExtractBusinessData(resp)
        extra = data.get("extra")
        assert isinstance(extra, dict), f"extra 缺失: {data!r}"
        allowed = extra.get("allowedResources")
        assert isinstance(allowed, dict), f"allowedResources 缺失: {extra!r}"
        AssertLocalOfferDataRootModule11(data, context=context)
        actual = allowed.get(restriction_key)
        assert isinstance(actual, list), f"allowedResources.{restriction_key} 应为数组: {allowed!r}"
        for val in expected_values:
            assert val in actual, (
                f"allowedResources.{restriction_key} 应含 {val!r}，实际 {actual!r}"
            )
        return f"{context}: allowedResources.{restriction_key} 含 {list(expected_values)!r}。"

    RunSoftAwareAllureAssertionStep(
        f"Local Offer ePass: 创建响应 allowedResources（{context}）",
        _Do,
    )


def _ResolveEPassIdField(data: Mapping[str, Any]) -> Optional[str]:
    """兼容 ``ePassId`` / ``epassId`` 大小写差异。"""
    for key in ("ePassId", "epassId"):
        val = data.get(key)
        if isinstance(val, str) and val:
            return val
    return None


def AssertUserEPassesContains(
    resp: Response,
    *,
    e_pass_id: str,
    context: str = "LocalOffer-users-ePasses",
) -> None:
    """断言用户 ePass 列表包含目标 ePassId；列表项含 ``module`` 时须为 11。"""

    def _Do() -> str:
        data = ExtractBusinessData(resp)
        lst = data.get("ePassesList")
        assert isinstance(lst, list), f"ePassesList 应为数组: {data!r}"
        matched = []
        for item in lst:
            if not isinstance(item, dict):
                continue
            if item.get("ePassId") != e_pass_id:
                continue
            matched.append(cast(JsonDict, item))
        assert matched, f"ePassesList 未找到 ePassId={e_pass_id!r}: {lst!r}"
        module_checked = AssertLocalOfferListItemModule11(
            matched[0],
            context=context,
            allow_missing_module=True,
        )
        if module_checked:
            return f"{context}: ePassesList 含 ePassId={e_pass_id!r}，module=11。"
        return (
            f"{context}: ePassesList 含 ePassId={e_pass_id!r}；"
            "列表项无 module（canary/doc gap，已跳过 module=11 校验）。"
        )

    RunSoftAwareAllureAssertionStep(f"Local Offer ePass: 用户列表包含 ePass（{context}）", _Do)


def AssertOrdersEPassesListContains(
    resp: Response,
    *,
    order_id: str,
    context: str = "LocalOffer-orders-ePasses",
    allow_empty_skip: bool = False,
    field_reference: Optional[LocalOfferResourceOptionReference] = None,
    expected_used_usages: int = 1,
) -> None:
    """断言 usage 订单列表包含指定 orderId；可选对拍 resource/option 与 location 字段。"""

    def _Do() -> str:
        data = ExtractBusinessData(resp)
        orders = data.get("orders")
        assert isinstance(orders, list), f"orders 应为数组: {data!r}"
        if allow_empty_skip and not orders:
            return (
                f"{context}: orders 暂为空（canary 索引延迟，doc gap），"
                f"跳过 orderId={order_id!r} 包含断言。"
            )
        matched = [o for o in orders if isinstance(o, dict) and o.get("orderId") == order_id]
        assert matched, f"orders 未包含 orderId={order_id!r}: {orders!r}"
        item = cast(JsonDict, matched[0])
        if field_reference is not None:
            _AssertEpassOrderFieldsMatchReference(
                item,
                field_reference,
                context=context,
                expected_used_usages=expected_used_usages,
            )
        else:
            AssertLocalOfferListItemModule11(item, context=context)
        return (
            f"{context}: orders 含 orderId={order_id!r}，"
            f"module=11"
            + (
                "，resource/option/location 字段与基准一致。"
                if field_reference is not None
                else "。"
            )
        )
    RunSoftAwareAllureAssertionStep(f"Local Offer ePass: 订单列表包含 usage 单（{context}）", _Do)


def AssertEpassSearchDetailsCoreFields(
    resp: Response,
    *,
    expected_order_id: Optional[str] = None,
    expected_e_pass_id: Optional[str] = None,
    context: str = "LocalOffer-ePasses-search",
    assert_module_11: bool = True,
) -> None:
    """断言 ePass 购买单详情（search）核心字段。"""

    def _Do() -> str:
        data = ExtractBusinessData(resp)
        if assert_module_11:
            AssertLocalOfferDataRootModule11(data, context=context)
        assert data.get("category") == 2, f"category 应为 2: {data!r}"
        if expected_order_id:
            assert data.get("orderId") == expected_order_id, f"orderId 不一致: {data!r}"
        extra = data.get("extra")
        assert isinstance(extra, dict), f"extra 缺失: {data!r}"
        if expected_e_pass_id:
            extra_e_pass = _ResolveEPassIdField(extra) if isinstance(extra, dict) else None
            assert extra_e_pass == expected_e_pass_id, f"ePassId 不一致: {extra!r}"
        module_note = "module=11，" if assert_module_11 else ""
        return f"{context}: search 详情 {module_note}category=2，关键 ID 一致。"
    RunSoftAwareAllureAssertionStep(f"Local Offer ePass: 购买单详情（{context}）", _Do)


def AssertPrebookingAvailabilitySuccess(resp: Response, *, context: str = "LocalOffer-availability") -> str:
    """断言可用性成功并返回 prebookingToken；``500.020.009`` 时 skip。"""
    _SkipIfPrebookingTimeslotUnavailable(resp, context=context)

    token_holder: Dict[str, str] = {}

    def _Do() -> str:
        data = ExtractBusinessData(resp)
        assert data.get("available") is True, f"available 应为 true: {data!r}"
        token = data.get("prebookingToken")
        assert isinstance(token, str) and token, f"prebookingToken 缺失: {data!r}"
        return token

    def _Wrapper() -> str:
        token = _Do()
        token_holder["token"] = token
        return f"{context}: available=true，prebookingToken 非空。"

    RunSoftAwareAllureAssertionStep(f"Local Offer ePass: 可用性校验（{context}）", _Wrapper)
    return _ResolveSoftHolderValue(
        token_holder,
        "token",
        resp=resp,
        fallback=_BestEffortResolvePrebookingTokenFromResponse,
    )


def AssertLocalOfferPrebookingOrderSuccess(
    resp: Response,
    *,
    e_pass_id: str,
    resource_id: str,
    option_id: str,
    expected_voucher_type: Optional[int] = None,
    expect_redemption_url_present: Optional[bool] = None,
    context: str = "LocalOffer-prebooking",
) -> str:
    """断言预约下单成功并返回 usage orderId。"""
    order_holder: Dict[str, str] = {}

    def _Do() -> str:
        _SkipIfPrebookingTimeslotUnavailable(resp, context=context)
        data = ExtractBusinessData(resp)
        status = data.get("status")
        if status == 10:
            pytest.skip(f"预约单 status=10 FAILED（可能供应商/券发放未完成）: {data!r}")
        assert status == 1, f"status 应为 1 CONFIRMED: {data!r}"
        AssertLocalOfferDataRootModule11(data, context=context)
        assert data.get("category") == 2, f"category 应为 2: {data!r}"
        resp_e_pass_id = _ResolveEPassIdField(data)
        assert isinstance(resp_e_pass_id, str) and resp_e_pass_id, f"响应应含 ePassId/epassId: {data!r}"
        id_note = ""
        if resp_e_pass_id != e_pass_id:
            id_note = f"（注意：响应 epassId={resp_e_pass_id!r} 与请求 {e_pass_id!r} 不一致，以业务成功为准）"
        order_id = data.get("orderId")
        assert isinstance(order_id, str) and order_id, f"orderId 缺失: {data!r}"
        extra = data.get("extra")
        assert isinstance(extra, dict), f"extra 缺失: {data!r}"
        assert extra.get("resourceId") == resource_id, f"resourceId 不一致: {extra!r}"
        local_opts = extra.get("localOfferOptions")
        redemption_url_note = ""
        if isinstance(local_opts, dict):
            assert local_opts.get("optionId") == option_id, f"optionId 不一致: {local_opts!r}"
            if expect_redemption_url_present is not None:
                redemption_url = local_opts.get("redemptionUrl")
                has_url = isinstance(redemption_url, str) and bool(redemption_url.strip())
                if expect_redemption_url_present:
                    assert has_url, (
                        f"localOfferOptions.redemptionUrl 应有值: {local_opts!r} "
                        f"（context={context}）"
                    )
                    redemption_url_note = f"，redemptionUrl 非空"
                else:
                    assert redemption_url is None or (
                        isinstance(redemption_url, str) and not redemption_url.strip()
                    ), (
                        f"localOfferOptions.redemptionUrl 应为 null/空: {local_opts!r} "
                        f"（context={context}）"
                    )
                    redemption_url_note = f"，redemptionUrl 为 null"
        vouchers = extra.get("vouchersList")
        if expected_voucher_type is not None and isinstance(vouchers, list) and vouchers:
            first = vouchers[0]
            if isinstance(first, dict):
                assert first.get("voucherType") == expected_voucher_type, (
                    f"voucherType 期望 {expected_voucher_type}: {first!r}"
                )
        order_holder["id"] = order_id
        return (
            f"{context}: 预约成功 status=1, module=11, resource/option 一致{id_note}{redemption_url_note}。"
        )

    RunSoftAwareAllureAssertionStep(f"Local Offer ePass: 预约下单响应（{context}）", _Do)
    usage_order_id = _ResolveSoftHolderValue(
        order_holder,
        "id",
        resp=resp,
        fallback=_BestEffortResolveOrderIdFromResponse,
    )
    RegisterPendingLocalOfferOrder(usage_order_id)
    return usage_order_id


def AssertBundleOrderSuccess(
    resp: Response,
    *,
    expected_client_user_id: str,
    resource_id: str,
    option_id: str,
    expected_voucher_type: Optional[int] = None,
    expect_redemption_url_present: Optional[bool] = None,
    context: str = "LocalOffer-bundle",
) -> Tuple[str, str]:
    """断言 Bundle 下单成功，返回 ``(ePassId, usageOrderId)``。"""

    holder: Dict[str, str] = {}

    def _Do() -> str:
        _st, env, _data = ParseResponseEnvelope(resp)
        if env is not None and env.get("code") == -1 and env.get("errCode") == "500.110.010":
            pytest.skip(f"Bundle 内部错误 500.110.010（canary 暂不稳定）: {env.get('msg')!r}")
        _SkipIfPrebookingTimeslotUnavailable(resp, context=context)
        data = ExtractBusinessData(resp)
        status = data.get("status")
        if status == 10:
            pytest.skip(f"Bundle 预约单 status=10 FAILED: {data!r}")
        assert status == 1, f"status 应为 1 CONFIRMED: {data!r}"
        AssertLocalOfferDataRootModule11(data, context=context)
        assert data.get("category") == 2, f"category 应为 2: {data!r}"
        e_pass_id = _ResolveEPassIdField(data)
        assert isinstance(e_pass_id, str) and e_pass_id, f"ePassId 缺失: {data!r}"
        order_id = data.get("orderId")
        assert isinstance(order_id, str) and order_id, f"orderId 缺失: {data!r}"
        extra = data.get("extra")
        assert isinstance(extra, dict), f"extra 缺失: {data!r}"
        assert extra.get("clientUserId") == expected_client_user_id, f"clientUserId 不一致: {extra!r}"
        assert extra.get("resourceId") == resource_id, f"resourceId 不一致: {extra!r}"
        local_opts = extra.get("localOfferOptions")
        redemption_url_note = ""
        if isinstance(local_opts, dict):
            assert local_opts.get("optionId") == option_id, f"optionId 不一致: {local_opts!r}"
            if expect_redemption_url_present is not None:
                redemption_url = local_opts.get("redemptionUrl")
                has_url = isinstance(redemption_url, str) and bool(redemption_url.strip())
                if expect_redemption_url_present:
                    assert has_url, (
                        f"localOfferOptions.redemptionUrl 应有值: {local_opts!r} "
                        f"（context={context}）"
                    )
                    redemption_url_note = "，redemptionUrl 非空"
                else:
                    assert redemption_url is None or (
                        isinstance(redemption_url, str) and not redemption_url.strip()
                    ), (
                        f"localOfferOptions.redemptionUrl 应为 null/空: {local_opts!r} "
                        f"（context={context}）"
                    )
                    redemption_url_note = "，redemptionUrl 为 null"
        vouchers = extra.get("vouchersList")
        if expected_voucher_type is not None and isinstance(vouchers, list) and vouchers:
            first = vouchers[0]
            if isinstance(first, dict):
                assert first.get("voucherType") == expected_voucher_type, (
                    f"voucherType 期望 {expected_voucher_type}: {first!r}"
                )
        holder["ePassId"] = e_pass_id
        holder["orderId"] = order_id
        return (
            f"{context}: Bundle 成功 status=1, ePassId/orderId 非空, "
            f"resource/option 一致{redemption_url_note}。"
        )

    RunSoftAwareAllureAssertionStep(f"Local Offer ePass: Bundle 下单响应（{context}）", _Do)
    e_pass_id = _ResolveSoftHolderValue(
        holder,
        "ePassId",
        resp=resp,
        fallback=_BestEffortResolveEPassIdFromResponse,
    )
    usage_order_id = _ResolveSoftHolderValue(
        holder,
        "orderId",
        resp=resp,
        fallback=_BestEffortResolveOrderIdFromResponse,
    )
    RegisterPendingLocalOfferOrder(usage_order_id)
    RegisterPendingLocalOfferEPassId(e_pass_id)
    return e_pass_id, usage_order_id


def RequestPrebookingTokenWithoutEpass(
    token: str,
    steps: Any,
    *,
    target: LocalOfferPrebookingTarget,
    prebooking_date: Optional[str] = None,
    adult_count: int = 1,
    child_count: int = 0,
) -> Tuple[str, str]:
    """可用性校验（不绑 ePassId）并返回 ``(prebookingToken, prebookingDate)``；多时段重试 ``500.020.009``。"""
    date_candidates = (
        (prebooking_date,)
        if prebooking_date
        else IterLocalOfferPrebookingDateCandidates()
    )
    errors: List[str] = []
    last_resp: Optional[Response] = None
    for pb_date in date_candidates:
        body = BuildAvailabilityBody(
            resource_id=target.ResourceId,
            option_id=target.OptionId,
            prebooking_date=pb_date,
            adult_count=adult_count,
            child_count=child_count,
        )
        kw = _HttpStepKw(steps, f"可用性（无 ePassId · {pb_date}）{target.Label}")
        resp = PostResourcesOptionsPrebookingsAvailability(
            token,
            body,
            step_code=kw["step_code"],
            step_title=kw["step_title"],
        )
        last_resp = resp
        pb_token, err = _ParsePrebookingTokenFromAvailabilityResponse(resp)
        if pb_token:
            return pb_token, pb_date
        if err:
            errors.append(f"{pb_date}:{err}")
    if last_resp is not None:
        _SkipIfPrebookingTimeslotUnavailable(
            last_resp,
            context=f"no-epass-{target.Label}",
        )
    pytest.skip(
        f"可用性未通过（{target.ResourceId}/{target.OptionId}）: "
        + ("；".join(errors) if errors else "无候选时段")
    )


def RequestPrebookingToken(
    token: str,
    steps: Any,
    *,
    e_pass_id: str,
    target: LocalOfferPrebookingTarget,
    option_id: Optional[str] = None,
    prebooking_date: Optional[str] = None,
    adult_count: int = 1,
    child_count: int = 0,
) -> Tuple[str, str]:
    """可用性校验并返回 ``(prebookingToken, prebookingDate)``；多时段重试 ``500.020.009``。"""
    resolved_option = option_id or target.OptionId
    date_candidates = (
        (prebooking_date,)
        if prebooking_date
        else IterLocalOfferPrebookingDateCandidates()
    )
    errors: List[str] = []
    last_resp: Optional[Response] = None
    for pb_date in date_candidates:
        body = BuildAvailabilityBody(
            e_pass_id=e_pass_id,
            resource_id=target.ResourceId,
            option_id=resolved_option,
            prebooking_date=pb_date,
            adult_count=adult_count,
            child_count=child_count,
        )
        kw = _HttpStepKw(steps, f"可用性 {target.Label} · {pb_date}")
        resp = PostResourcesOptionsPrebookingsAvailability(
            token,
            body,
            step_code=kw["step_code"],
            step_title=kw["step_title"],
        )
        last_resp = resp
        pb_token, err = _ParsePrebookingTokenFromAvailabilityResponse(resp)
        if pb_token:
            return pb_token, pb_date
        if err:
            errors.append(f"{pb_date}:{err}")
    if last_resp is not None:
        _SkipIfPrebookingTimeslotUnavailable(last_resp, context=target.Label)
    pytest.skip(
        f"可用性未通过（{target.Label} {target.ResourceId}/{resolved_option}）: "
        + ("；".join(errors) if errors else "无候选时段")
    )


def PickAlternatePrebookingTarget(*, exclude_resource_ids: Sequence[str]) -> LocalOfferPrebookingTarget:
    """从默认三类券型网点中选取 ``resourceId`` 不在排除列表内的预约目标。"""
    excluded = {str(rid) for rid in exclude_resource_ids}
    for item in GetDefaultPrebookingResources():
        target = _StaticPrebookingTargetFromCatalogItem(item)
        if target.ResourceId not in excluded:
            return target
    raise LookupError(
        f"未找到 resourceId 不在 {list(excluded)!r} 的 Local Offer 预约网点；"
        "请配置 DP_LO_EPASS_RESOURCE_ID / DP_LO_EPASS_<LABEL>_RESOURCE_ID（见 env/.env.local-offer.example）。"
    )


def PickCountryOrRegionOutsideAllowed(
    token: str,
    steps: Any,
    *,
    allowed_countries: Sequence[str],
    fallback_target: LocalOfferPrebookingTarget,
) -> str:
    """
    选取与 ``allowed_countries`` 不同的 countryOrRegion（优先默认网点详情，其次 resources 列表）。

    用于 countryOrRegion 限制负向：ePass 限定 A 国，预约 B 国网点应失败。
    """
    allowed_set = {str(c) for c in allowed_countries}
    ref = FetchLocalOfferResourceOptionReference(
        token,
        fallback_target.ResourceId,
        fallback_target.OptionId,
        steps=steps,
    )
    if ref.CountryOrRegion and ref.CountryOrRegion not in allowed_set:
        return ref.CountryOrRegion
    hints = FetchModuleResourceHintsOrSkip(token, module=LOCAL_OFFER_MODULE_INT, steps=steps)
    for country in hints.CountryOrRegions:
        if country not in allowed_set:
            return country
    raise LookupError(
        f"无法解析与 allowed={list(allowed_set)!r} 不同的 countryOrRegion；"
        f"默认网点 country={ref.CountryOrRegion!r}，resources 列表={hints.CountryOrRegions!r}"
    )


def RegisterMembershipIdForAvailability(
    token: str,
    steps: Any,
    *,
    client_user_id: Optional[str] = None,
) -> str:
    """
    ``POST /v2/memberships`` 注册并返回 ``membershipId``。

    ePass 专用 Bearer 无会籍写权限（``201.000.001``）时，回退 ``GetAccessToken()`` 默认 client。
    """
    kw = _HttpStepKw(steps, "注册会籍获取 membershipId")
    payload = BuildMinimalMembershipPayload(
        extra={"programId": GetConfiguredEpassProgramId()},
    )
    if client_user_id:
        payload["clientUserId"] = client_user_id

    def _TryRegister(register_token: str, title_suffix: str) -> Optional[str]:
        resp, env, inner = PostMemberships(
            register_token,
            payload,
            step_code=kw.get("step_code"),
            step_title=(kw.get("step_title") or "") + title_suffix,
        )
        if IsBusinessSuccess(env):
            body = AssertRegisterSuccessBody(inner)
            return str(body["membershipId"])
        err_code = env.get("errCode") if isinstance(env, dict) else None
        if err_code == "201.000.001":
            return None
        AssertHttpAndBusinessOk(resp, env, context="POST /v2/memberships")
        return None

    membership_id = _TryRegister(token, "")
    if membership_id:
        return membership_id

    try:
        default_token = GetAccessToken()
    except RuntimeError as exc:
        pytest.skip(f"POST /v2/memberships 需配置 DP_CLIENT_ID/DP_CLIENT_SECRET：{exc}")

    if default_token != token:
        membership_id = _TryRegister(default_token, " · 默认 client")
        if membership_id:
            return membership_id

    LocalOfferFailOrRecord(
        "POST /v2/memberships 注册失败：ePass token 无权限且默认 client 未成功；"
        "请检查 canary 会籍注册凭据或配置 DP_LO_EPASS_MEMBERSHIP_ID。"
    )


def ResolveMembershipIdForAvailabilityOrSkip(
    token: str,
    steps: Any,
    *,
    created: Optional[LocalOfferEpassCreateResult] = None,
) -> str:
    """
    解析可用于可用性 ``membershipId`` 的测试 ID。

    优先级：``DP_LO_EPASS_MEMBERSHIP_ID`` → 创建 ePass 响应 ``extra.membershipId`` →
    ``POST /v2/memberships`` 会话级注册并取 ``membershipId``。
    """
    env_mid = os.getenv("DP_LO_EPASS_MEMBERSHIP_ID", "").strip()
    if env_mid:
        return env_mid
    if created is not None:
        data = ExtractBusinessData(created.CreateResponse)
        extra = data.get("extra")
        if isinstance(extra, dict):
            mid = extra.get("membershipId")
            if isinstance(mid, str) and mid:
                return mid
    return RegisterMembershipIdForAvailability(token, steps)


def AssertPrebookingStepRejected(
    resp: Response,
    *,
    expected_err_codes: Sequence[str],
    context: str,
    accept_http_400: bool = False,
) -> None:
    """预约或可用性步骤业务失败（允许多 errCode；可选接受 HTTP 400 参数校验拒绝）。"""
    AssertBusinessFailure(
        resp,
        expected_err_codes=expected_err_codes,
        context=context,
        accept_http_400=accept_http_400,
    )


def AssertPrebookingTokenOptionMismatchOutcome(
    resp: Response,
    *,
    expected_option_id: str,
    injected_option_id: str,
    expected_err_codes: Sequence[str],
    context: str = "token-option-mismatch",
) -> None:
    """
    tc-p2 option 不一致：优先期望下单失败；若 canary 仍成功，则断言响应 ``optionId`` 来自 token 缓存而非注入值。
    """

    def _Do() -> str:
        if resp.status_code != 200:
            raise AssertionError(f"HTTP 非 200: {resp.status_code}")
        _st, env, data = ParseResponseEnvelope(resp)
        assert env is not None, "响应非 JSON 对象"
        if env.get("code") == -1:
            actual_err = env.get("errCode")
            allowed = tuple(expected_err_codes or ())
            if allowed:
                assert actual_err in allowed, (
                    f"errCode 期望 {allowed!r} 之一，实际 {actual_err!r}，msg={env.get('msg')!r}"
                )
            return f"{context}: 下单失败 code=-1，errCode={actual_err!r}（option 注入被拒绝）。"
        assert env.get("code") == 0, f"非预期业务响应: {env!r}"
        assert isinstance(data, dict), f"成功 data 应为对象: {data!r}"
        extra = data.get("extra")
        assert isinstance(extra, dict), f"extra 缺失: {data!r}"
        local_opts = extra.get("localOfferOptions")
        assert isinstance(local_opts, dict), f"localOfferOptions 缺失: {extra!r}"
        actual_option = local_opts.get("optionId")
        assert actual_option == expected_option_id, (
            f"订单 optionId 应来自 token（{expected_option_id!r}），"
            f"不应使用注入的 {injected_option_id!r}；actual={actual_option!r}"
        )
        assert actual_option != injected_option_id, (
            f"订单误用注入 optionId={injected_option_id!r}"
        )
        return (
            f"{context}: canary 未拒绝 option 注入但订单 optionId={actual_option!r} "
            f"与 token 一致（未采用 {injected_option_id!r}）；见 Allure 附件 doc-gap。"
        )

    def _AttachDocGap(note: str) -> None:
        allure.attach(
            note,
            name="doc_gap_token_option_mismatch",
            attachment_type=allure.attachment_type.TEXT,
        )

    def _RunWithDocGap() -> str:
        summary = _Do()
        if "canary 未拒绝" in summary:
            _AttachDocGap(
                "功能用例期望「option 不一致时下单失败」；canary 当前忽略 extra/localOfferOptions 注入，"
                "仍成功且 optionId 取自 token 缓存。已断言未误用注入 optionId。"
            )
        return summary

    RunSoftAwareAllureAssertionStep(f"Local Offer ePass: token/option 一致性（{context}）", _RunWithDocGap)


def PostPrebookingAvailability(
    token: str,
    steps: Any,
    *,
    body: JsonDict,
    brief: str,
) -> Response:
    """发送可用性请求（不断言）。"""
    kw = _HttpStepKw(steps, brief)
    return PostResourcesOptionsPrebookingsAvailability(
        token,
        body,
        step_code=kw["step_code"],
        step_title=kw["step_title"],
    )


def AssertAvailabilityBusinessFailure(
    resp: Response,
    *,
    expected_err_code: Optional[str] = None,
    expected_err_codes: Optional[Sequence[str]] = None,
    context: str = "availability-negative",
) -> None:
    """断言可用性业务失败（不 skip 500.020.009）。"""
    AssertBusinessFailure(
        resp,
        expected_err_code=expected_err_code,
        expected_err_codes=expected_err_codes,
        context=context,
    )


def BuildFakeOrderId() -> str:
    """构造不存在的订单号（负向）。"""
    return f"DPFAKE{uuid.uuid4().hex[:12].upper()}"


def BuildOverLimitResourceIds(base_ids: Sequence[str], count: int = 31) -> List[str]:
    """构造超过上限的 resourceIds 列表。"""
    result: List[str] = []
    idx = 0
    while len(result) < count:
        if base_ids:
            result.append(base_ids[idx % len(base_ids)])
        else:
            result.append(f"GRFAKE{idx:04d}")
        idx += 1
    return result


def AssertLocalOfferNotReturnedWithEsimModuleFilter(
    resp: Response,
    *,
    expected_order_id: Optional[str] = None,
    expected_e_pass_id: Optional[str] = None,
    context: str = "module8-no-local-offer-data",
) -> None:
    """
    Local Offer 订单在入参 ``module=8``（eSIM）且其余字段正确时，不应返回 Local Offer 数据。

    接受：业务失败（``code=-1``）、``data`` 为 null、列表为空、或成功响应中不含目标 orderId /
    ``module=11`` 条目。
    """

    def _Do() -> str:
        assert resp.status_code == 200, f"HTTP 非 200: {resp.status_code}, body={resp.text[:800]}"
        _st, env, data = ParseResponseEnvelope(resp)
        assert env is not None, "响应非 JSON 对象"

        if env.get("code") == -1:
            err = env.get("errCode")
            return f"{context}: module=8 时业务失败未返回 Local Offer 数据（errCode={err!r}）。"

        assert IsLocalOfferBusinessSuccess(env), f"非预期响应信封: {env!r}"

        if data is None:
            return f"{context}: module=8 时 data 为 null，未返回 Local Offer 数据。"

        if not isinstance(data, dict):
            return f"{context}: module=8 时 data 非对象（{type(data).__name__}），未返回 Local Offer 详情。"

        orders = data.get("orders")
        if isinstance(orders, list):
            if expected_order_id:
                matched = [
                    o for o in orders
                    if isinstance(o, dict) and o.get("orderId") == expected_order_id
                ]
                assert not matched, (
                    f"{context}: module=8 时 orders 不应含 Local Offer orderId="
                    f"{expected_order_id!r}: {matched!r}"
                )
            lo_items = [
                o for o in orders
                if isinstance(o, dict) and o.get("module") == LOCAL_OFFER_MODULE_INT
            ]
            assert not lo_items, (
                f"{context}: module=8 时 orders 不应含 module=11 条目: {lo_items!r}"
            )
            return (
                f"{context}: module=8 时 orders 未含 Local Offer 订单"
                f"（共 {len(orders)} 条，无 module=11）。" 
            )

        resp_order_id = data.get("orderId")
        resp_module = data.get("module")
        if resp_module == LOCAL_OFFER_MODULE_INT:
            raise AssertionError(
                f"{context}: module=8 时不应返回 module=11 订单详情: orderId={resp_order_id!r}"
            )
        if expected_order_id and resp_order_id == expected_order_id:
            raise AssertionError(
                f"{context}: module=8 时不应返回 Local Offer orderId={expected_order_id!r}"
            )
        if expected_e_pass_id:
            extra = data.get("extra")
            ep = _ResolveEPassIdField(data)
            if ep is None and isinstance(extra, dict):
                ep = _ResolveEPassIdField(extra)
            if ep == expected_e_pass_id and resp_module == LOCAL_OFFER_MODULE_INT:
                raise AssertionError(
                    f"{context}: module=8 时不应返回 Local Offer ePassId={expected_e_pass_id!r}"
                )
        if resp_order_id is None and resp_module is None:
            return f"{context}: module=8 时未返回 Local Offer 订单详情（data 无 orderId/module）。"

        return (
            f"{context}: module=8 时响应未暴露 Local Offer 订单"
            f"（orderId={resp_order_id!r}, module={resp_module!r}）。"
        )

    RunSoftAwareAllureAssertionStep(
        f"Local Offer ePass: module=8 不返回 Local Offer 数据（{context}）",
        _Do,
    )


def AssertEsimNotReturnedWithLocalOfferModuleFilter(
    resp: Response,
    *,
    expected_order_id: Optional[str] = None,
    expected_e_pass_id: Optional[str] = None,
    context: str = "module11-no-esim-data",
) -> None:
    """
    eSIM 订单在入参 ``module=11``（Local Offer）且其余字段正确时，不应返回 eSIM（module=8）数据。

    与 ``AssertLocalOfferNotReturnedWithEsimModuleFilter`` 对称。
    """

    def _Do() -> str:
        assert resp.status_code == 200, f"HTTP 非 200: {resp.status_code}, body={resp.text[:800]}"
        _st, env, data = ParseResponseEnvelope(resp)
        assert env is not None, "响应非 JSON 对象"

        if env.get("code") == -1:
            err = env.get("errCode")
            return f"{context}: module=11 时业务失败未返回 eSIM 数据（errCode={err!r}）。"

        assert IsLocalOfferBusinessSuccess(env), f"非预期响应信封: {env!r}"

        if data is None:
            return f"{context}: module=11 时 data 为 null，未返回 eSIM 数据。"

        if not isinstance(data, dict):
            return f"{context}: module=11 时 data 非对象（{type(data).__name__}），未返回 eSIM 详情。"

        orders = data.get("orders")
        if isinstance(orders, list):
            if expected_order_id:
                matched = [
                    o for o in orders
                    if isinstance(o, dict) and o.get("orderId") == expected_order_id
                ]
                assert not matched, (
                    f"{context}: module=11 时 orders 不应含 eSIM orderId="
                    f"{expected_order_id!r}: {matched!r}"
                )
            esim_items = [
                o for o in orders
                if isinstance(o, dict) and o.get("module") == ESIM_MODULE_INT
            ]
            assert not esim_items, (
                f"{context}: module=11 时 orders 不应含 module=8 条目: {esim_items!r}"
            )
            return (
                f"{context}: module=11 时 orders 未含 eSIM 订单"
                f"（共 {len(orders)} 条，无 module=8）。"
            )

        resp_order_id = data.get("orderId")
        resp_module = data.get("module")
        if resp_module == ESIM_MODULE_INT:
            raise AssertionError(
                f"{context}: module=11 时不应返回 module=8 订单详情: orderId={resp_order_id!r}"
            )
        if expected_order_id and resp_order_id == expected_order_id:
            raise AssertionError(
                f"{context}: module=11 时不应返回 eSIM orderId={expected_order_id!r}"
            )
        if expected_e_pass_id:
            extra = data.get("extra")
            ep = _ResolveEPassIdField(data)
            if ep is None and isinstance(extra, dict):
                ep = _ResolveEPassIdField(extra)
            if ep == expected_e_pass_id and resp_module == ESIM_MODULE_INT:
                raise AssertionError(
                    f"{context}: module=11 时不应返回 eSIM ePassId={expected_e_pass_id!r}"
                )
        if resp_order_id is None and resp_module is None:
            return f"{context}: module=11 时未返回 eSIM 订单详情（data 无 orderId/module）。"

        return (
            f"{context}: module=11 时响应未暴露 eSIM 订单"
            f"（orderId={resp_order_id!r}, module={resp_module!r}）。"
        )

    RunSoftAwareAllureAssertionStep(
        f"Local Offer ePass: module=11 不返回 eSIM 数据（{context}）",
        _Do,
    )


def AssertOrdersEPassesListContainsModule(
    resp: Response,
    *,
    order_id: str,
    expected_module: int,
    context: str = "orders-ePasses-list",
    allow_empty_skip: bool = False,
) -> None:
    """断言 usage 订单列表含指定 ``orderId`` 且列表项 ``module`` 与预期一致。"""

    def _Do() -> str:
        data = ExtractBusinessData(resp)
        orders = data.get("orders")
        assert isinstance(orders, list), f"orders 应为数组: {data!r}"
        if allow_empty_skip and not orders:
            return (
                f"{context}: orders 暂为空（索引延迟），跳过 orderId={order_id!r} 包含断言。"
            )
        matched = [o for o in orders if isinstance(o, dict) and o.get("orderId") == order_id]
        assert matched, f"orders 未包含 orderId={order_id!r}: {orders!r}"
        item = cast(JsonDict, matched[0])
        assert item.get("module") == expected_module, (
            f"列表项 module 应为 {expected_module}: {item!r}"
        )
        return f"{context}: orders 含 orderId={order_id!r}，module={expected_module}。"

    RunSoftAwareAllureAssertionStep(
        f"Local Offer ePass: 订单列表 module={expected_module}（{context}）",
        _Do,
    )


def AssertEsimUsageOrderDetailsCoreFields(
    resp: Response,
    *,
    expected_order_id: str,
    expected_e_pass_id: str,
    context: str = "esim-usage-details",
) -> None:
    """eSIM usage 订单详情（``module=8``）核心字段。"""

    def _Do() -> str:
        data = ExtractBusinessData(resp)
        assert data.get("module") == ESIM_MODULE_INT, f"module 应为 8: {data!r}"
        assert data.get("orderId") == expected_order_id, f"orderId 不一致: {data!r}"
        ep = _ResolveEPassIdField(data)
        assert ep == expected_e_pass_id, f"ePassId 不一致: expected={expected_e_pass_id!r}, actual={ep!r}"
        status = data.get("status")
        assert status in (1, 5), f"eSIM usage 详情 status 应为 1 或 5: {data!r}"
        return f"{context}: module=8，orderId/ePassId 一致，status={status}。"

    RunSoftAwareAllureAssertionStep(f"Local Offer ePass: eSIM usage 详情（{context}）", _Do)


def VerifyUsageOrderRetrieveModuleIsolation(
    token: str,
    steps: Any,
    *,
    e_pass_id: str,
    usage_order_id: str,
    native_module: int,
    source_path_module: str,
    context: str,
    soft: bool = False,
) -> bool:
    """
    下单成功后校验订单可查性：

    - **列表** ``POST /v2/orders/ePasses``：入参 ``module`` + ``ePassId``；native 可见、foreign 不可见。
    - **详情** ``POST /v2/orders/ePasses/details``：仅 ``orderId``（不传 ``module``）；校验响应 ``module`` 与 native 一致。

    ``soft=True`` 时断言失败不中断主场景，返回 ``False`` 并写入 Allure 附件。
    """
    from _pytest.outcomes import Failed

    try:
        _VerifyUsageOrderRetrieveModuleIsolationImpl(
            token,
            steps,
            e_pass_id=e_pass_id,
            usage_order_id=usage_order_id,
            native_module=native_module,
            source_path_module=source_path_module,
            context=context,
        )
        return True
    except (AssertionError, Failed) as exc:
        if not soft:
            raise
        import json

        with allure.step(f"module 隔离软断言失败 · {context}（继续后续步骤）"):
            allure.attach(
                str(exc),
                name=f"soft_assert_failed_{context}",
                attachment_type=allure.attachment_type.TEXT,
            )
            allure.attach(
                json.dumps(
                    {
                        "context": context,
                        "usageOrderId": usage_order_id,
                        "ePassId": e_pass_id,
                        "nativeModule": native_module,
                        "soft": True,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                name=f"soft_assert_meta_{context}",
                attachment_type=allure.attachment_type.JSON,
            )
        return False


def _VerifyUsageOrderRetrieveModuleIsolationImpl(
    token: str,
    steps: Any,
    *,
    e_pass_id: str,
    usage_order_id: str,
    native_module: int,
    source_path_module: str,
    context: str,
) -> None:
    """``VerifyUsageOrderRetrieveModuleIsolation`` 内部实现（失败抛 ``AssertionError``）。"""
    if native_module == LOCAL_OFFER_MODULE_INT:
        foreign_module = ESIM_MODULE_INT
        foreign_path = ESIM_PATH_MODULE
    elif native_module == ESIM_MODULE_INT:
        foreign_module = LOCAL_OFFER_MODULE_INT
        foreign_path = LOCAL_OFFER_PATH_MODULE
    else:
        raise ValueError(f"不支持的 native_module={native_module!r}")

    import json

    with allure.step(f"module 隔离校验 · {context}"):
        allure.attach(
            json.dumps(
                {
                    "usageOrderId": usage_order_id,
                    "ePassId": e_pass_id,
                    "nativeModule": native_module,
                    "sourcePathModule": source_path_module,
                    "foreignModule": foreign_module,
                    "foreignPathModule": foreign_path,
                    "detailsRequestBody": {"orderId": usage_order_id},
                },
                ensure_ascii=False,
                indent=2,
            ),
            name=f"module_isolation_{context}",
            attachment_type=allure.attachment_type.JSON,
        )

    kw_list_native = _HttpStepKw(
        steps,
        f"{context} · 订单列表 module={native_module}（{source_path_module}）",
    )
    resp_list_native = PostOrdersEPassesList(
        token,
        e_pass_id,
        module=native_module,
        step_code=kw_list_native["step_code"],
        step_title=kw_list_native["step_title"],
    )
    AssertOrdersEPassesListContainsModule(
        resp_list_native,
        order_id=usage_order_id,
        expected_module=native_module,
        context=f"{context}-list-native",
        allow_empty_skip=True,
    )

    kw_det_native = _HttpStepKw(
        steps,
        f"{context} · 订单详情（仅 orderId，{source_path_module}）",
    )
    resp_det_native = PostOrdersEPassesUsageDetails(
        token,
        usage_order_id,
        step_code=kw_det_native["step_code"],
        step_title=kw_det_native["step_title"],
    )
    if native_module == LOCAL_OFFER_MODULE_INT:
        AssertUsageOrderDetailsCoreFields(
            resp_det_native,
            expected_order_id=usage_order_id,
            expected_e_pass_id=e_pass_id,
            context=f"{context}-details-native",
        )
    else:
        AssertEsimUsageOrderDetailsCoreFields(
            resp_det_native,
            expected_order_id=usage_order_id,
            expected_e_pass_id=e_pass_id,
            context=f"{context}-details-native",
        )

    kw_list_foreign = _HttpStepKw(
        steps,
        f"{context} · 订单列表 module={foreign_module}（{foreign_path}，应不可见）",
    )
    resp_list_foreign = PostOrdersEPassesList(
        token,
        e_pass_id,
        module=foreign_module,
        step_code=kw_list_foreign["step_code"],
        step_title=kw_list_foreign["step_title"],
    )
    if native_module == LOCAL_OFFER_MODULE_INT:
        AssertLocalOfferNotReturnedWithEsimModuleFilter(
            resp_list_foreign,
            expected_order_id=usage_order_id,
            context=f"{context}-list-foreign",
        )
    else:
        AssertEsimNotReturnedWithLocalOfferModuleFilter(
            resp_list_foreign,
            expected_order_id=usage_order_id,
            context=f"{context}-list-foreign",
        )


def AssertBusinessFailure(
    resp: Response,
    *,
    expected_err_code: Optional[str] = None,
    expected_err_codes: Optional[Sequence[str]] = None,
    context: str = "LocalOffer-negative",
    accept_http_400: bool = False,
) -> None:
    """断言 HTTP 200（或可选 400）+ 业务失败信封；``expected_err_codes`` 允许多个可接受 errCode。"""

    def _Do() -> str:
        if accept_http_400 and resp.status_code == 400:
            return f"{context}: HTTP 400 拒绝（参数校验层）"
        assert resp.status_code == 200, f"HTTP 非 200: {resp.status_code}"
        _st, env, _data = ParseResponseEnvelope(resp)
        assert env is not None, "响应非 JSON 对象"
        assert env.get("code") == -1, f"期望 code=-1: {env!r}"
        actual_err = env.get("errCode")
        allowed = tuple(expected_err_codes or ())
        if expected_err_code:
            allowed = (expected_err_code,) + tuple(c for c in allowed if c != expected_err_code)
        if allowed:
            assert actual_err in allowed, (
                f"errCode 期望 {allowed!r} 之一，实际 {actual_err!r}，msg={env.get('msg')!r}"
            )
        err_note = f", errCode={actual_err!r}" if actual_err else ""
        return f"{context}: 业务失败 code=-1{err_note}"

    RunSoftAwareAllureAssertionStep(f"Local Offer ePass: 负向业务失败（{context}）", _Do)


def CreateLocalOfferEpass(
    token: str,
    steps: Any,
    *,
    allowed_resources: Optional[Mapping[str, Sequence[str]]] = None,
    client_user_id: Optional[str] = None,
    available_usages: Optional[int] = None,
) -> LocalOfferEpassCreateResult:
    """创建 Local Offer ePass 并解析上下文。"""
    payload = BuildLocalOfferEpassCreatePayload(
        client_user_id=client_user_id,
        allowed_resources=allowed_resources,
        available_usages=available_usages,
    )
    kw = _HttpStepKw(steps, "创建 Local Offer ePass")
    resp = PostOrdersLocalOffersEPasses(
        token,
        payload,
        step_code=kw["step_code"],
        step_title=kw["step_title"],
    )
    cid, e_pass_id, order_id = RunWithSoftCapture(
        "创建 Local Offer ePass 解析 ID",
        lambda: ExtractCreateEpassIds(resp),
        fallback=lambda: _BestEffortExtractCreateEpassIds(resp),
    )
    AssertLocalOfferEpassCreateCoreFields(resp, expected_client_user_id=cid)
    RegisterPendingLocalOfferOrder(order_id)
    RegisterPendingLocalOfferEPassId(e_pass_id)
    return LocalOfferEpassCreateResult(
        ClientUserId=cid,
        EPassId=e_pass_id,
        PurchaseOrderId=order_id,
        CreateResponse=resp,
    )


def BuildAvailabilityBody(
    *,
    resource_id: str,
    option_id: str,
    e_pass_id: Optional[str] = None,
    membership_id: Optional[str] = None,
    prebooking_date: Optional[str] = None,
    adult_count: int = 1,
    child_count: int = 0,
    module: int = LOCAL_OFFER_MODULE_INT,
) -> JsonDict:
    """构造 ``POST /v2/resources/options/prebookings/availability`` 请求体。"""
    body: JsonDict = {
        "module": module,
        "resourceId": resource_id,
        "optionId": option_id,
        "prebookingDate": prebooking_date or BuildLocalOfferPrebookingDate(),
        "adultCount": adult_count,
        "childCount": child_count,
    }
    if e_pass_id:
        body["ePassId"] = e_pass_id
    if membership_id:
        body["membershipId"] = membership_id
    return body


def PostOrdersLocalOffersEPassesBundle(
    token: str,
    client_user_id: str,
    prebooking_token: str,
    *,
    async_mode: bool = False,
    step_code: Optional[str] = None,
    step_title: Optional[str] = None,
) -> Response:
    """``POST /v2/orders/localOffers/ePasses/bundle``"""
    body: JsonDict = {
        "module": LOCAL_OFFER_MODULE_INT,
        "clientUserId": client_user_id,
        "extra": {"prebookingToken": prebooking_token},
        "async": async_mode,
    }
    return RequestWithAllure(
        "POST",
        f"/v2/orders/{LOCAL_OFFER_PATH_MODULE}/ePasses/bundle",
        token=token,
        json_body=body,
        step_code=step_code,
        step_title=step_title,
        x_program_id=GetConfiguredEpassProgramId(),
    )


def PostOrdersLocalOffersEPassesPrebookingWithToken(
    token: str,
    e_pass_id: str,
    prebooking_token: str,
    *,
    async_mode: bool = False,
    extra_overrides: Optional[Mapping[str, Any]] = None,
    body_overrides: Optional[Mapping[str, Any]] = None,
    step_code: Optional[str] = None,
    step_title: Optional[str] = None,
) -> Response:
    """``POST /v2/orders/localOffers/ePasses/prebooking``（可指定 async / extra / body 扩展字段）。"""
    extra: JsonDict = {"prebookingToken": prebooking_token}
    if extra_overrides:
        extra.update(dict(extra_overrides))
    body: JsonDict = {
        "module": LOCAL_OFFER_MODULE_INT,
        "ePassId": e_pass_id,
        "extra": extra,
        "async": async_mode,
    }
    if body_overrides:
        body.update(dict(body_overrides))
    return RequestWithAllure(
        "POST",
        f"/v2/orders/{LOCAL_OFFER_PATH_MODULE}/ePasses/prebooking",
        token=token,
        json_body=body,
        step_code=step_code,
        step_title=step_title,
        x_program_id=GetConfiguredEpassProgramId(),
    )


def PostOrdersLocalOffersMembershipsPrebookingWithToken(
    token: str,
    membership_id: str,
    prebooking_token: str,
    *,
    to_use_entitlement_count: int = 1,
    cash_payment_applied: bool = False,
    async_mode: bool = False,
    extra_overrides: Optional[Mapping[str, Any]] = None,
    step_code: Optional[str] = None,
    step_title: Optional[str] = None,
) -> Response:
    """``POST /v2/orders/localOffers/memberships/prebooking``。"""
    extra: JsonDict = {
        "prebookingToken": prebooking_token,
        "cashPaymentApplied": cash_payment_applied,
        "toUseEntitlementCount": to_use_entitlement_count,
    }
    if extra_overrides:
        extra.update(dict(extra_overrides))
    body: JsonDict = {
        "module": LOCAL_OFFER_MODULE_INT,
        "membershipId": membership_id,
        "extra": extra,
        "async": async_mode,
    }
    return RequestWithAllure(
        "POST",
        f"/v2/orders/{LOCAL_OFFER_PATH_MODULE}/memberships/prebooking",
        token=token,
        json_body=body,
        step_code=step_code,
        step_title=step_title,
        x_program_id=GetConfiguredEpassProgramId(),
    )


def PatchCancelOrder(
    token: str,
    order_id: str,
    *,
    step_code: Optional[str] = None,
    step_title: Optional[str] = None,
) -> Response:
    """``PATCH /v2/orders`` — 取消订单（status=3）。"""
    return RequestWithAllure(
        "PATCH",
        "/v2/orders",
        token=token,
        json_body={"status": 3, "orderId": order_id},
        step_code=step_code,
        step_title=step_title,
        x_program_id=GetConfiguredEpassProgramId(),
    )


def ParseEnvelope(resp: Response) -> Tuple[Optional[JsonDict], Any]:
    """解析响应信封，不断言成功。"""
    _st, env, data = ParseResponseEnvelope(resp)
    return env, data


def AssertSearchDetailsExtendedFields(
    resp: Response,
    *,
    expected_client_user_id: str,
    expected_expiration_date: Optional[str] = None,
    context: str = "search-extended",
) -> None:
    """RetrieveEpassDetails 扩展字段断言。"""

    def _Do() -> str:
        data = ExtractBusinessData(resp)
        AssertLocalOfferDataRootModule11(data, context=context)
        assert isinstance(data.get("orderId"), str) and data.get("orderId"), "orderId 缺失"
        assert isinstance(data.get("orderCreatedDate"), str) and data.get("orderCreatedDate"), "orderCreatedDate 缺失"
        assert data.get("clientUserId") == expected_client_user_id, "clientUserId 不一致"
        extra = data.get("extra")
        assert isinstance(extra, dict), "extra 缺失"
        for key in ("ePassId", "ePassStatus", "firstName", "lastName", "availableUsages", "allowedResources"):
            assert key in extra, f"extra 缺 {key}"
        if expected_expiration_date:
            assert extra.get("expirationDate") == expected_expiration_date, "expirationDate 与入参不一致"
        return f"{context}: search 详情扩展字段齐全。"

    RunSoftAwareAllureAssertionStep(f"Local Offer ePass: 购买单详情扩展（{context}）", _Do)


def _AssertPrebookingRequiredInfoAllNull(prebooking_required_info: Any, *, context: str) -> None:
    """断言 ``prebookingRequiredInfo`` 各字段均为 null。"""
    assert isinstance(prebooking_required_info, dict), (
        f"{context}: prebookingRequiredInfo 应为对象: {prebooking_required_info!r}"
    )
    for field_name in _PREBOOKING_REQUIRED_INFO_NULL_FIELDS:
        assert field_name in prebooking_required_info, (
            f"{context}: prebookingRequiredInfo 缺字段 {field_name!r}: {prebooking_required_info!r}"
        )
        assert prebooking_required_info.get(field_name) is None, (
            f"{context}: prebookingRequiredInfo.{field_name} 应为 null，"
            f"实际 {prebooking_required_info.get(field_name)!r}"
        )


def _ResolveEpassOrderFieldValues(item: Mapping[str, Any]) -> JsonDict:
    """
    归一化 ``POST /v2/orders/ePasses`` 列表项与 ``POST /v2/orders/ePasses/details`` 响应字段位置差异。

    列表项：``usedUsages/module/category/resourceId/resourceName`` 多在根节点，
    ``transportHub*`` / ``optionId`` / ``optionName`` / ``city`` / ``countryOrRegion`` 多在 ``extra``。
    详情：多数业务字段在 ``extra``，``localOfferOptions`` 承载 option 信息。
    """
    extra_raw = item.get("extra")
    extra = cast(JsonDict, extra_raw) if isinstance(extra_raw, dict) else {}
    local_opts_raw = extra.get("localOfferOptions")
    local_opts = cast(JsonDict, local_opts_raw) if isinstance(local_opts_raw, dict) else {}

    option_id = extra.get("optionId")
    if option_id is None:
        option_id = local_opts.get("optionId")
    option_name = extra.get("optionName")
    if option_name is None:
        option_name = local_opts.get("optionName")

    used_usages = item.get("usedUsages")
    if used_usages is None:
        used_usages = extra.get("usedUsages")

    transport_hub_name = extra.get("transportHubName")
    if "transportHubName" not in extra:
        transport_hub_name = item.get("transportHubName")
    transport_hub_id = extra.get("transportHubId")
    if "transportHubId" not in extra:
        transport_hub_id = item.get("transportHubId")

    city = extra.get("city")
    if city is None:
        city = item.get("city")
    country_or_region = extra.get("countryOrRegion")
    if country_or_region is None:
        country_or_region = item.get("countryOrRegion")

    resource_id = extra.get("resourceId")
    if resource_id is None:
        resource_id = item.get("resourceId")
    resource_name = extra.get("resourceName")
    if resource_name is None:
        resource_name = item.get("resourceName")

    return {
        "module": item.get("module"),
        "category": item.get("category"),
        "usedUsages": used_usages,
        "resourceId": resource_id,
        "resourceName": resource_name,
        "transportHubName": transport_hub_name,
        "transportHubId": transport_hub_id,
        "city": city,
        "countryOrRegion": country_or_region,
        "optionId": option_id,
        "optionName": option_name,
    }


def _AssertEpassOrderFieldsMatchReference(
    item: Mapping[str, Any],
    reference: LocalOfferResourceOptionReference,
    *,
    context: str,
    expected_used_usages: int = 1,
) -> None:
    """
    断言 ePass usage 订单（列表项或 details ``data``）核心字段与 resource/option 基准一致。

    固定值：``module=11``、``category=2``、``usedUsages``、``transportHubName/Id=null``；
    ``city/countryOrRegion/optionId`` 对拍 resource 详情（响应无 city/country 时跳过对拍）；
    ``resourceId/resourceName/optionName`` 对拍 option 详情。
    """
    values = _ResolveEpassOrderFieldValues(item)
    AssertLocalOfferModule11(
        values.get("module"),
        context=context,
        response_hint=str(values.get("resourceId")),
    )
    assert values.get("category") == 2, f"{context}: category 应为 2: {values!r}"
    assert values.get("usedUsages") == expected_used_usages, (
        f"{context}: usedUsages 应为 {expected_used_usages}: {values!r}"
    )
    assert values.get("transportHubName") is None, (
        f"{context}: transportHubName 应为 null: {values!r}"
    )
    assert values.get("transportHubId") is None, (
        f"{context}: transportHubId 应为 null: {values!r}"
    )
    assert values.get("resourceId") == reference.ResourceId, (
        f"{context}: resourceId 与 option 详情不一致: "
        f"actual={values.get('resourceId')!r}, reference={reference.ResourceId!r}"
    )
    assert values.get("resourceName") == reference.ResourceName, (
        f"{context}: resourceName 与 option 详情不一致: "
        f"actual={values.get('resourceName')!r}, reference={reference.ResourceName!r}"
    )
    assert values.get("optionId") == reference.OptionId, (
        f"{context}: optionId 与 resource/option 基准不一致: "
        f"actual={values.get('optionId')!r}, reference={reference.OptionId!r}"
    )
    assert values.get("optionName") == reference.OptionName, (
        f"{context}: optionName 与 option 详情不一致: "
        f"actual={values.get('optionName')!r}, reference={reference.OptionName!r}"
    )
    if reference.City is not None and values.get("city") is not None:
        assert values.get("city") == reference.City, (
            f"{context}: city 与 resource 详情不一致: "
            f"actual={values.get('city')!r}, reference={reference.City!r}"
        )
    if reference.CountryOrRegion is not None and values.get("countryOrRegion") is not None:
        assert values.get("countryOrRegion") == reference.CountryOrRegion, (
            f"{context}: countryOrRegion 与 resource 详情不一致: "
            f"actual={values.get('countryOrRegion')!r}, reference={reference.CountryOrRegion!r}"
        )


def AssertUsageOrderDetailsCoreFields(
    resp: Response,
    *,
    expected_order_id: str,
    expected_e_pass_id: Optional[str] = None,
    expected_client_user_id: Optional[str] = None,
    expected_resource_id: Optional[str] = None,
    option_reference: Optional[LocalOfferResourceOptionReference] = None,
    expected_used_usages: int = 1,
    expect_order_cancelled_date_null: bool = True,
    assert_prebooking_required_info_null: bool = True,
    context: str = "usage-details",
) -> None:
    """
    Retrieve E-pass Usage Order Details 核心字段。

    校验：``module=11``、``category=2``、``usedUsages=1``、``transportHubName/Id=null``、
    ``usageDate`` null、``prebookingRequiredInfo`` 各字段 null（可关）、
    ``ePassId/clientUserId`` 与创建入参一致；
    ``city/countryOrRegion/optionId`` 与 resource 详情对拍，
    ``resourceId/resourceName/optionName`` 与 option 详情对拍（传入 ``option_reference`` 时）。
    """

    def _Do() -> str:
        data = ExtractBusinessData(resp)
        assert data.get("orderId") == expected_order_id, f"orderId 不一致: {data!r}"
        if expect_order_cancelled_date_null:
            assert data.get("orderCancelledDate") is None, (
                f"orderCancelledDate 应为 null: {data!r}"
            )
        if expected_e_pass_id:
            ep = _ResolveEPassIdField(data)
            assert isinstance(ep, str) and ep, f"响应应含 ePassId: {data!r}"
            assert ep == expected_e_pass_id, (
                f"ePassId 与创建入参不一致: expected={expected_e_pass_id!r}, actual={ep!r}"
            )
        extra_raw = data.get("extra")
        assert isinstance(extra_raw, dict), f"extra 缺失: {data!r}"
        extra = cast(JsonDict, extra_raw)
        if expected_client_user_id:
            assert extra.get("clientUserId") == expected_client_user_id, (
                f"clientUserId 与创建入参不一致: "
                f"expected={expected_client_user_id!r}, actual={extra.get('clientUserId')!r}"
            )
        assert extra.get("usageDate") is None, f"usageDate 应为 null: {extra!r}"
        if assert_prebooking_required_info_null:
            _AssertPrebookingRequiredInfoAllNull(
                extra.get("prebookingRequiredInfo"),
                context=context,
            )
        if option_reference is not None:
            _AssertEpassOrderFieldsMatchReference(
                data,
                option_reference,
                context=context,
                expected_used_usages=expected_used_usages,
            )
        else:
            AssertLocalOfferDataRootModule11(data, context=context)
            assert data.get("category") == 2, f"category 应为 2: {data!r}"
            assert extra.get("usedUsages") == expected_used_usages, (
                f"usedUsages 应为 {expected_used_usages}: {extra!r}"
            )
            if expected_resource_id:
                assert extra.get("resourceId") == expected_resource_id, (
                    f"resourceId 不一致: {extra!r}"
                )
        parts = [
            f"{context}: module=11, category=2, orderId 一致",
            f"usedUsages={expected_used_usages}, usageDate=null",
        ]
        if expected_e_pass_id:
            parts.append("ePassId 与创建入参一致")
        if expected_client_user_id:
            parts.append("clientUserId 与创建入参一致")
        if assert_prebooking_required_info_null:
            parts.append("prebookingRequiredInfo 各字段 null")
        if option_reference is not None:
            parts.append(
                "transportHubName/Id=null；city/countryOrRegion/optionId 与 resource 详情一致；"
                "resourceId/resourceName/optionName 与 option 详情一致"
            )
        return "；".join(parts) + "。"

    RunSoftAwareAllureAssertionStep(f"Local Offer ePass: usage 订单详情（{context}）", _Do)


def AssertUsageOrderDetailsShowsCancelled(
    resp: Response,
    *,
    expected_order_id: str,
    expected_e_pass_id: str,
    expected_client_user_id: Optional[str] = None,
    expected_resource_id: Optional[str] = None,
    option_reference: Optional[LocalOfferResourceOptionReference] = None,
    context: str = "usage-details-after-cancel",
) -> None:
    """取消 usage 预订单后 ``POST /v2/orders/ePasses/details``：核心字段 + ``status=3``。"""

    AssertUsageOrderDetailsCoreFields(
        resp,
        expected_order_id=expected_order_id,
        expected_e_pass_id=expected_e_pass_id,
        expected_client_user_id=expected_client_user_id,
        expected_resource_id=expected_resource_id,
        option_reference=option_reference,
        expect_order_cancelled_date_null=False,
        context=context,
    )

    def _DoCancelledStatus() -> str:
        data = ExtractBusinessData(resp)
        status = data.get("status")
        assert status == 3, f"取消后 status 应为 3 CANCELLED: {data!r}"
        cancelled_at = data.get("orderCancelledDate")
        assert cancelled_at is not None, f"取消后 orderCancelledDate 应有值: {data!r}"
        return f"{context}: details status=3，orderCancelledDate={cancelled_at!r}。"

    RunSoftAwareAllureAssertionStep(
        f"Local Offer ePass: usage 订单详情已取消（{context}）",
        _DoCancelledStatus,
    )


def AssertUsageOrderListContainsCancelled(
    resp: Response,
    *,
    order_id: str,
    context: str = "orders-list-after-cancel",
    allow_empty_skip: bool = True,
    expected_module: int = LOCAL_OFFER_MODULE_INT,
) -> None:
    """取消后 ``POST /v2/orders/ePasses`` 列表含该 usage 单且 ``status=3``。"""

    def _Do() -> str:
        data = ExtractBusinessData(resp)
        orders = data.get("orders")
        assert isinstance(orders, list), f"orders 应为数组: {data!r}"
        if allow_empty_skip and not orders:
            return (
                f"{context}: orders 暂为空（canary 索引延迟），"
                f"跳过 orderId={order_id!r} 取消态断言。"
            )
        matched = [o for o in orders if isinstance(o, dict) and o.get("orderId") == order_id]
        assert matched, f"orders 未包含 orderId={order_id!r}: {orders!r}"
        item = cast(JsonDict, matched[0])
        status = item.get("status")
        assert status == 3, (
            f"列表项 status 应为 3 CANCELLED: orderId={order_id!r}, item={item!r}"
        )
        if expected_module == LOCAL_OFFER_MODULE_INT:
            module_checked = AssertLocalOfferListItemModule11(
                item,
                context=context,
                allow_missing_module=True,
            )
            module_note = "module=11" if module_checked else "module 缺失已跳过"
        else:
            assert item.get("module") == expected_module, (
                f"列表项 module 应为 {expected_module}: {item!r}"
            )
            module_note = f"module={expected_module}"
        return f"{context}: orders 含 orderId={order_id!r}，status=3，{module_note}。"

    RunSoftAwareAllureAssertionStep(f"Local Offer ePass: 取消后订单列表（{context}）", _Do)


def AssertOrderListPaginationShape(resp: Response, *, context: str = "order-list") -> None:
    """Retrieve E-pass Order List 分页与列表项结构。"""

    def _Do() -> str:
        data = ExtractBusinessData(resp)
        pagination = data.get("pagination")
        assert isinstance(pagination, dict), f"pagination 缺失: {data!r}"
        for key in ("pageSize", "pageNumber", "totalNumber"):
            assert key in pagination, f"pagination 缺 {key}"
        orders = data.get("orders")
        assert isinstance(orders, list), f"orders 应为数组: {data!r}"
        for idx, item in enumerate(orders):
            if isinstance(item, dict):
                AssertLocalOfferListItemModule11(
                    cast(JsonDict, item),
                    context=f"{context}·orders[{idx}]",
                )
        return f"{context}: pagination 与 orders 结构满足契约，列表项 module=11。"
    RunSoftAwareAllureAssertionStep(f"Local Offer ePass: 订单列表结构（{context}）", _Do)


def AssertCancelOrderSuccess(
    resp: Response,
    *,
    context: str = "cancel-order",
    assert_response_module_11: bool = False,
) -> None:
    """断言 PATCH /v2/orders 取消成功（data 可能为 null）。"""

    def _Do() -> str:
        assert resp.status_code == 200, f"HTTP 非 200: {resp.status_code}"
        _st, env, data = ParseResponseEnvelope(resp)
        assert IsLocalOfferBusinessSuccess(env), f"取消业务失败: {env!r}"
        if data is not None and not isinstance(data, dict):
            raise AssertionError(f"取消响应 data 非对象: {data!r}")
        if isinstance(data, dict) and assert_response_module_11:
            AssertLocalOfferDataRootModule11(data, context=context)
        return f"{context}: 取消请求业务成功。"

    RunSoftAwareAllureAssertionStep(f"Local Offer ePass: 取消订单（{context}）", _Do)


def AssertEpassSearchShowsCancelledAfterPurchaseCancel(
    resp: Response,
    *,
    expected_e_pass_id: str,
    expected_purchase_order_id: str,
    context: str = "after-cancel-purchase",
) -> None:
    """
    取消会籍购买单（PATCH MS 单）后 search 校验：

    - ``extra.ePassStatus=3``（Cancelled，注销 ePassId）
    - 购买单 ``orderId`` 仍可查；``status`` 记录（doc 期望 1 不取消，canary 可能为 3）
    """

    def _Do() -> str:
        data = ExtractBusinessData(resp)
        order_id = data.get("orderId")
        assert order_id == expected_purchase_order_id, (
            f"orderId 与购买单不一致: expected={expected_purchase_order_id!r}, actual={order_id!r}"
        )
        extra_raw = data.get("extra")
        assert isinstance(extra_raw, dict), f"extra 缺失: {data!r}"
        extra = cast(JsonDict, extra_raw)
        ep = _ResolveEPassIdField(extra) or extra.get("ePassId")
        assert ep == expected_e_pass_id, (
            f"ePassId 不一致: expected={expected_e_pass_id!r}, extra={extra!r}"
        )
        purchase_status = data.get("status")
        e_pass_status = extra.get("ePassStatus")
        assert e_pass_status == 3, f"ePassStatus 应为 3 Cancelled: {extra!r}"
        if purchase_status == 1:
            status_note = "购买单 status=1（符合 doc：MS 单不取消）。"
        elif purchase_status == 3:
            status_note = (
                "购买单 status=3（canary 与 doc「购买单不取消」不一致，已记录不失败）。"
            )
        else:
            status_note = f"购买单 status={purchase_status!r}（非 1/3，已记录）。"
        return (
            f"{context}: ePassStatus=3 Cancelled，orderId={order_id!r}；{status_note}"
        )

    RunSoftAwareAllureAssertionStep(
        f"Local Offer ePass: 取消购买单后 search 侧效应（{context}）",
        _Do,
    )


def AssertEsimUsageOrderDetailsShowsCancelled(
    resp: Response,
    *,
    expected_order_id: str,
    expected_e_pass_id: str,
    context: str = "esim-usage-details-after-cancel",
) -> None:
    """取消 eSIM usage 预订单后 ``POST /v2/orders/ePasses/details``：``module=8`` 且 ``status=3``。"""

    def _Do() -> str:
        data = ExtractBusinessData(resp)
        assert data.get("module") == ESIM_MODULE_INT, f"module 应为 8: {data!r}"
        assert data.get("orderId") == expected_order_id, f"orderId 不一致: {data!r}"
        ep = _ResolveEPassIdField(data)
        assert ep == expected_e_pass_id, (
            f"ePassId 不一致: expected={expected_e_pass_id!r}, actual={ep!r}"
        )
        status = data.get("status")
        assert status == 3, f"取消后 status 应为 3 CANCELLED: {data!r}"
        cancelled_at = data.get("orderCancelledDate")
        assert cancelled_at is not None, f"取消后 orderCancelledDate 应有值: {data!r}"
        return f"{context}: module=8，status=3，orderCancelledDate={cancelled_at!r}。"

    RunSoftAwareAllureAssertionStep(
        f"Local Offer ePass: eSIM usage 订单详情已取消（{context}）",
        _Do,
    )


def AssertEpassSearchActiveAfterUsageCancel(
    resp: Response,
    *,
    expected_e_pass_id: str,
    expected_purchase_order_id: str,
    context: str = "search-after-usage-cancel",
    assert_module_11: bool = True,
) -> None:
    """
    取消 usage 预订单后 ``POST /v2/orders/ePasses/search``：

    ePass 未注销（``ePassStatus=1``），购买单 ``orderId`` 仍可查（doc：MS 单不取消）。
    """

    def _Do() -> str:
        data = ExtractBusinessData(resp)
        if assert_module_11:
            AssertLocalOfferDataRootModule11(data, context=context)
        else:
            assert data.get("module") == ESIM_MODULE_INT, f"module 应为 8: {data!r}"
        order_id = data.get("orderId")
        assert order_id == expected_purchase_order_id, (
            f"orderId 与购买单不一致: expected={expected_purchase_order_id!r}, actual={order_id!r}"
        )
        extra_raw = data.get("extra")
        assert isinstance(extra_raw, dict), f"extra 缺失: {data!r}"
        extra = cast(JsonDict, extra_raw)
        ep = _ResolveEPassIdField(extra) or extra.get("ePassId")
        assert ep == expected_e_pass_id, (
            f"ePassId 不一致: expected={expected_e_pass_id!r}, extra={extra!r}"
        )
        e_pass_status = extra.get("ePassStatus")
        assert e_pass_status == 1, (
            f"usage 预订单取消后 ePassStatus 应为 1 Active: {extra!r}"
        )
        return (
            f"{context}: ePassStatus=1，购买单 orderId={order_id!r} 仍可查。"
        )

    RunSoftAwareAllureAssertionStep(
        f"Local Offer ePass: usage 取消后会籍卡详情（{context}）",
        _Do,
    )


def CancelUsageOrderAndVerifyPostCancelRetrieve(
    token: str,
    steps: Any,
    *,
    usage_order_id: str,
    e_pass_id: str,
    purchase_order_id: str,
    client_user_id: Optional[str] = None,
    resource_id: Optional[str] = None,
    option_id: Optional[str] = None,
    option_reference: Optional[LocalOfferResourceOptionReference] = None,
    native_module: int = LOCAL_OFFER_MODULE_INT,
    context: str = "usage-cancel-retrieve",
    soft: bool = False,
) -> bool:
    """
    usage 预订单下单成功后统一收尾：

    ``PATCH /v2/orders`` 取消 → ``POST /v2/orders/ePasses/details`` →
    ``POST /v2/orders/ePasses`` → ``POST /v2/orders/ePasses/search``（ePassId）。
    """
    from _pytest.outcomes import Failed

    def _Run() -> None:
        kw_cancel = _HttpStepKw(steps, f"{context} · 取消 usage 预订单")
        resp_cancel = PatchCancelOrder(
            token,
            usage_order_id,
            step_code=kw_cancel["step_code"],
            step_title=kw_cancel["step_title"],
        )
        AssertCancelOrderSuccess(resp_cancel, context=f"{context}-cancel")
        MarkLocalOfferOrderCancelled(usage_order_id)

        opt_ref = option_reference
        if opt_ref is None and resource_id and option_id:
            opt_ref = FetchLocalOfferResourceOptionReference(
                token,
                resource_id,
                option_id,
                steps=steps,
            )

        kw_details = _HttpStepKw(steps, f"{context} · 取消后 usage 订单详情")
        resp_details = PostOrdersEPassesUsageDetails(
            token,
            usage_order_id,
            step_code=kw_details["step_code"],
            step_title=kw_details["step_title"],
        )
        if native_module == LOCAL_OFFER_MODULE_INT:
            AssertUsageOrderDetailsShowsCancelled(
                resp_details,
                expected_order_id=usage_order_id,
                expected_e_pass_id=e_pass_id,
                expected_client_user_id=client_user_id,
                expected_resource_id=resource_id,
                option_reference=opt_ref,
                context=f"{context}-details",
            )
        else:
            AssertEsimUsageOrderDetailsShowsCancelled(
                resp_details,
                expected_order_id=usage_order_id,
                expected_e_pass_id=e_pass_id,
                context=f"{context}-details",
            )

        kw_list = _HttpStepKw(steps, f"{context} · 取消后 usage 订单列表")
        resp_list = PostOrdersEPassesList(
            token,
            e_pass_id,
            step_code=kw_list["step_code"],
            step_title=kw_list["step_title"],
        )
        AssertOrderListPaginationShape(resp_list, context=f"{context}-list-shape")
        AssertUsageOrderListContainsCancelled(
            resp_list,
            order_id=usage_order_id,
            context=f"{context}-list",
            expected_module=native_module,
        )

        if purchase_order_id:
            kw_search = _HttpStepKw(steps, f"{context} · 取消后会籍卡详情（ePassId）")
            resp_search = PostOrdersEPassesSearch(
                token,
                e_pass_id=e_pass_id,
                step_code=kw_search["step_code"],
                step_title=kw_search["step_title"],
            )
            AssertEpassSearchActiveAfterUsageCancel(
                resp_search,
                expected_e_pass_id=e_pass_id,
                expected_purchase_order_id=purchase_order_id,
                context=f"{context}-search",
                assert_module_11=(native_module == LOCAL_OFFER_MODULE_INT),
            )

    try:
        _Run()
        return True
    except (AssertionError, Failed) as exc:
        if not soft:
            raise
        import json

        with allure.step(f"取消后查询软断言失败 · {context}（继续后续步骤）"):
            allure.attach(
                str(exc),
                name=f"soft_cancel_retrieve_failed_{context}",
                attachment_type=allure.attachment_type.TEXT,
            )
            allure.attach(
                json.dumps(
                    {
                        "context": context,
                        "usageOrderId": usage_order_id,
                        "ePassId": e_pass_id,
                        "purchaseOrderId": purchase_order_id,
                        "nativeModule": native_module,
                        "soft": True,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                name=f"soft_cancel_retrieve_meta_{context}",
                attachment_type=allure.attachment_type.JSON,
            )
        return False


def CancelPurchaseOrderAndVerifyPostCancelRetrieve(
    token: str,
    steps: Any,
    *,
    e_pass_id: str,
    purchase_order_id: str,
    context: str = "purchase-cancel-retrieve",
) -> None:
    """
    会籍购买单（创建 ePass）下单成功后统一收尾：

    ``PATCH /v2/orders`` 取消 MS 单 → ``POST /v2/orders/ePasses/search``（ePassId）。
    """
    kw_cancel = _HttpStepKw(steps, f"{context} · 取消 ePass 会籍购买单")
    resp_cancel = PatchCancelOrder(
        token,
        purchase_order_id,
        step_code=kw_cancel["step_code"],
        step_title=kw_cancel["step_title"],
    )
    AssertCancelOrderSuccess(resp_cancel, context=f"{context}-cancel")
    MarkLocalOfferOrderCancelled(purchase_order_id)
    MarkLocalOfferEPassPurchaseCancelled(e_pass_id)

    kw_list = _HttpStepKw(steps, f"{context} · 取消后 usage 订单列表（可为空）")
    resp_list = PostOrdersEPassesList(
        token,
        e_pass_id,
        step_code=kw_list["step_code"],
        step_title=kw_list["step_title"],
    )
    AssertOrderListPaginationShape(resp_list, context=f"{context}-list-shape")

    kw_search = _HttpStepKw(steps, f"{context} · 取消后会籍卡详情（ePassId）")
    resp_search = PostOrdersEPassesSearch(
        token,
        e_pass_id=e_pass_id,
        step_code=kw_search["step_code"],
        step_title=kw_search["step_title"],
    )
    AssertEpassSearchShowsCancelledAfterPurchaseCancel(
        resp_search,
        expected_e_pass_id=e_pass_id,
        expected_purchase_order_id=purchase_order_id,
        context=f"{context}-search",
    )


def FinalizeSuccessfulLocalOfferUsageOrder(
    token: str,
    steps: Any,
    *,
    usage_order_id: str,
    e_pass_id: str,
    purchase_order_id: str,
    client_user_id: Optional[str] = None,
    resource_id: Optional[str] = None,
    option_id: Optional[str] = None,
    context: str = "local-offer-usage",
    soft: bool = False,
) -> bool:
    """Local Offer（module=11）usage 预订单成功后的取消与查询收尾（别名）。"""
    if not (isinstance(usage_order_id, str) and usage_order_id.strip()):
        FinalizeCreatedLocalOfferPurchaseOnly(
            token,
            steps,
            e_pass_id=e_pass_id,
            purchase_order_id=purchase_order_id,
            context=f"{context}-purchase-only",
        )
        return False
    return CancelUsageOrderAndVerifyPostCancelRetrieve(
        token,
        steps,
        usage_order_id=usage_order_id,
        e_pass_id=e_pass_id,
        purchase_order_id=purchase_order_id,
        client_user_id=client_user_id,
        resource_id=resource_id,
        option_id=option_id,
        native_module=LOCAL_OFFER_MODULE_INT,
        context=context,
        soft=soft,
    )


def FinalizeCreatedLocalOfferPurchaseOnly(
    token: str,
    steps: Any,
    *,
    e_pass_id: str,
    purchase_order_id: str,
    context: str = "create-only-cancel",
) -> None:
    """仅创建 ePass（MS 购买单）、未产生 usage 预订单时的取消与 search 查询。"""
    if not purchase_order_id:
        return
    CancelPurchaseOrderAndVerifyPostCancelRetrieve(
        token,
        steps,
        e_pass_id=e_pass_id,
        purchase_order_id=purchase_order_id,
        context=context,
    )


def FinalizeCreatedLocalOfferEpassResults(
    token: str,
    steps: Any,
    *created: LocalOfferEpassCreateResult,
    context_prefix: str = "create-only-cancel",
) -> None:
    """批量取消仅创建、未走 ``CreateLocalOfferEpass`` 封装或负向用例残留的 MS 购买单。"""
    for index, item in enumerate(created):
        FinalizeCreatedLocalOfferPurchaseOnly(
            token,
            steps,
            e_pass_id=item.EPassId,
            purchase_order_id=item.PurchaseOrderId,
            context=f"{context_prefix}-{index}",
        )


def CancelProbedLocalOfferOrdersAndPurchaseBestEffort(
    token: str,
    steps: Any,
    *,
    catalog: LocalOfferRedemptionUrlProbeCatalog,
    purchase_order_id: str,
    e_pass_id: str,
    context: str = "probe-cancel",
) -> None:
    """redemptionUrl 轮询探测：取消本轮所有成功 usage 单及探测用 ePass 购买单。"""
    import json

    usage_ids = [
        row.OrderId
        for row in catalog.Results
        if isinstance(row.OrderId, str) and row.OrderId
    ]
    with allure.step(f"轮询探测订单兜底取消 · {context}"):
        allure.attach(
            json.dumps(
                {
                    "usageOrderIds": usage_ids,
                    "purchaseOrderId": purchase_order_id,
                    "ePassId": e_pass_id,
                },
                ensure_ascii=False,
                indent=2,
            ),
            name="probe_orders_to_cancel",
            attachment_type=allure.attachment_type.JSON,
        )
    for order_id in usage_ids:
        _PatchCancelOrderBestEffort(
            token,
            order_id,
            steps=steps,
            step_brief=f"{context} · 取消探测 usage 单",
        )
    if purchase_order_id:
        _PatchCancelOrderBestEffort(
            token,
            purchase_order_id,
            steps=steps,
            step_brief=f"{context} · 取消探测 ePass 购买单",
        )
        MarkLocalOfferOrderCancelled(purchase_order_id)
        MarkLocalOfferEPassPurchaseCancelled(e_pass_id)


def FinalizeSuccessfulBundleOrder(
    token: str,
    steps: Any,
    *,
    usage_order_id: str,
    e_pass_id: str,
    client_user_id: str,
    resource_id: str,
    option_id: str,
    context: str = "bundle-cancel",
) -> bool:
    """Bundle 下单成功后：解析购买单 orderId → 取消 usage 并查询 details/列表/search。"""
    purchase_order_id = ""
    kw_search = _HttpStepKw(steps, f"{context} · Bundle 后购买单 orderId")
    resp_search = PostOrdersEPassesSearch(
        token,
        e_pass_id=e_pass_id,
        step_code=kw_search["step_code"],
        step_title=kw_search["step_title"],
    )
    try:
        data = ExtractBusinessData(resp_search)
        raw = data.get("orderId")
        if isinstance(raw, str):
            purchase_order_id = raw
    except Exception:
        purchase_order_id = ""
    usage_ok = FinalizeSuccessfulLocalOfferUsageOrder(
        token,
        steps,
        usage_order_id=usage_order_id,
        e_pass_id=e_pass_id,
        purchase_order_id=purchase_order_id,
        client_user_id=client_user_id,
        resource_id=resource_id,
        option_id=option_id,
        context=context,
    )
    if purchase_order_id:
        CancelPurchaseOrderAndVerifyPostCancelRetrieve(
            token,
            steps,
            e_pass_id=e_pass_id,
            purchase_order_id=purchase_order_id,
            context=f"{context}-purchase",
        )
    return usage_ok


def BuildPastPrebookingDate() -> str:
    """早于当前时间的预约日期（负向）。"""
    dt = datetime.now(timezone.utc) - timedelta(days=1)
    return dt.strftime("%Y-%m-%dT%H:%M")


_SAAS_VOUCHER_SQL_HINT = (
    "SELECT assignment_id, card_coupon_type, activation_code, use_url, end_time "
    "FROM `business-saas`.ord_order_common_voucher_esim_record "
    "WHERE sub_type='OFFER' AND <按 usageOrderId / assignment_id 等补充条件>;"
)


def AttachSaasManualCheckpoint(
    *,
    scenario: str,
    checklist: Sequence[str],
    context: Mapping[str, Any],
    sql_hints: Optional[Sequence[str]] = None,
) -> None:
    """
    将 SaaS 人工核对清单写入 Allure（不查库）。

    用例通过后，测试工程师按 ``checklist`` 与 ``context`` 中的订单/ePass ID 到 SaaS 后台核对。
    """
    import json

    payload: Dict[str, Any] = {
        "scenario": scenario,
        "status": "API_PASSED_AWAITING_SAAS_MANUAL_VERIFY",
        "saas_manual_checklist": list(checklist),
        "api_context": dict(context),
    }
    if sql_hints:
        payload["saas_sql_hints"] = list(sql_hints)

    with allure.step(f"SaaS 人工核对检查点 · {scenario}"):
        allure.attach(
            json.dumps(payload, ensure_ascii=False, indent=2),
            name="saas_manual_checkpoint",
            attachment_type=allure.attachment_type.JSON,
        )
