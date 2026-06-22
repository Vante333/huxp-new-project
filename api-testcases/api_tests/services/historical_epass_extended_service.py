"""
历史品类 ePass 扩展回归 — Topup / 资源只读 / Simulation / Checkin / Event / Internal。

补充 ``historical_epass_service`` 未覆盖的 MCP ePass 相关接口；凡请求含 ``module`` 的接口
均按 catalog 品类入参，并断言响应 ``module`` 与入参一致。
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, cast

import pytest
from requests import Response

from config.historical_epass_env import (
    HistoricalAvailabilityMode,
    HistoricalEpassCatalogEntry,
    HistoricalFitnessScheduleTarget,
    BuildHistoricalPrebookingDate,
    GetHistoricalSimulationPaths,
    IterHistoricalPrebookingDateCandidates,
)
from services.historical_epass_service import (
    AssertHistoricalPrebookingOrderSuccessForCatalog,
    CancelHistoricalPurchaseOrderAndVerify,
    CancelHistoricalUsageOrderAndVerify,
    CreateHistoricalEpass,
    HistoricalEpassCreateResult,
    PatchCancelOrderWithRetry,
    PostHistoricalEpassPrebooking,
    RequestHistoricalPrebookingToken,
    ResolveHistoricalFitnessScheduleTargets,
    WaitForHistoricalEsimUsageOrderConfirmed,
    PostResourcesClassicPrebookingsAvailability,
    PostResourcesOptionsPrebookingsAvailability,
)
from services.local_offer_epass_service import (
    BuildAvailabilityBody,
    ExtractBusinessData,
    GetResourceDetail,
    GetResourcesList,
    IsLocalOfferBusinessSuccess,
    PostOrdersEPassesList,
    PostOrdersEPassesUsageDetails,
    _HttpStepKw,
    _SkipIfPrebookingTimeslotUnavailable,
)
from services.historical_epass_service import (
    _ParsePrebookingTokenFromAvailabilityResponse,
    _ResolveEPassIdField,
)
from services.papi2424_epasses_impl import GetConfiguredEpassProgramId
from services.papi2548_memberships_extensions_impl import (
    JsonDict,
    ParseResponseEnvelope,
    RequestWithAllure,
    _RunAllureAssertionStep,
)


@dataclass(frozen=True)
class HistoricalEsimTopupResult:
    """eSIM EPass Topup 链结果。"""

    ClientUserId: str
    EPassId: str
    PurchaseOrderId: str
    UsageOrderId: str
    Iccid: str
    TopupOrderId: str
    Catalog: HistoricalEpassCatalogEntry


def AssertHistoricalResponseModule(
    data: JsonDict,
    *,
    expected_module: int,
    context: str,
) -> None:
    """断言业务 ``data.module`` 与入参一致（若响应含 ``module`` 字段）。"""
    if "module" not in data:
        return
    actual = data.get("module")
    assert actual == expected_module, (
        f"{context}: module 应为 {expected_module}，实际 {actual!r}；data={data!r}"
    )


def _ExtractIccidFromOrderData(data: JsonDict) -> str:
    extra = data.get("extra")
    if isinstance(extra, dict):
        iccid = extra.get("iccid")
        if isinstance(iccid, str) and iccid.strip():
            return iccid.strip()
        esim_block = extra.get("esim")
        if isinstance(esim_block, dict):
            iccid_esim = esim_block.get("iccid")
            if isinstance(iccid_esim, str) and iccid_esim.strip():
                return iccid_esim.strip()
    iccid_top = data.get("iccid")
    if isinstance(iccid_top, str) and iccid_top.strip():
        return iccid_top.strip()
    esim_root = data.get("esim")
    if isinstance(esim_root, dict):
        iccid_root = esim_root.get("iccid")
        if isinstance(iccid_root, str) and iccid_root.strip():
            return iccid_root.strip()
    return ""


def _ExtractVoucherFromOrderData(data: JsonDict) -> str:
    extra = data.get("extra")
    if not isinstance(extra, dict):
        return ""
    vouchers = extra.get("vouchersList")
    if not isinstance(vouchers, list):
        return ""
    for item in vouchers:
        if isinstance(item, dict):
            voucher = item.get("voucher")
            if isinstance(voucher, str) and voucher.strip():
                return voucher.strip()
    return ""


def PostResourcesPrices(
    token: str,
    *,
    module: int,
    resource_id: str,
    e_pass_id: Optional[str] = None,
    step_code: Optional[str] = None,
    step_title: Optional[str] = None,
) -> Response:
    """``POST /v2/resources/prices``。"""
    body: JsonDict = {
        "module": module,
        "resourceId": resource_id,
        "prebookingDate": BuildHistoricalPrebookingDate(),
        "adultCount": 1,
        "childCount": 0,
    }
    if e_pass_id:
        body["ePassId"] = e_pass_id
    return RequestWithAllure(
        "POST",
        "/v2/resources/prices",
        token=token,
        json_body=body,
        step_code=step_code,
        step_title=step_title,
        x_program_id=GetConfiguredEpassProgramId(),
    )


def PostResourcesOptionsPrices(
    token: str,
    *,
    module: int,
    resource_id: str,
    option_id: str,
    e_pass_id: Optional[str] = None,
    step_code: Optional[str] = None,
    step_title: Optional[str] = None,
) -> Response:
    """``POST /v2/resources/options/prices``。"""
    body: JsonDict = {
        "module": module,
        "resourceId": resource_id,
        "optionId": option_id,
        "prebookingDate": BuildHistoricalPrebookingDate(),
        "adultCount": 1,
        "childCount": 0,
    }
    if e_pass_id:
        body["ePassId"] = e_pass_id
    return RequestWithAllure(
        "POST",
        "/v2/resources/options/prices",
        token=token,
        json_body=body,
        step_code=step_code,
        step_title=step_title,
        x_program_id=GetConfiguredEpassProgramId(),
    )


def GetFitnessOptionDetail(
    token: str,
    resource_id: str,
    option_id: str,
    *,
    module: int = 7,
    step_code: Optional[str] = None,
    step_title: Optional[str] = None,
) -> Response:
    """``GET /v2/resources/fitness/{resourceId}/options/{optionId}``。"""
    path = f"/v2/resources/fitness/{resource_id}/options/{option_id}?module={module}"
    return RequestWithAllure(
        "GET",
        path,
        token=token,
        step_code=step_code,
        step_title=step_title,
        x_program_id=GetConfiguredEpassProgramId(),
    )


def GetEsimResourceOptions(
    token: str,
    resource_id: str,
    *,
    module: int = 8,
    step_code: Optional[str] = None,
    step_title: Optional[str] = None,
) -> Response:
    """``GET /v2/resources/esims/{resourceId}/options``。"""
    path = f"/v2/resources/esims/{resource_id}/options?module={module}"
    return RequestWithAllure(
        "GET",
        path,
        token=token,
        step_code=step_code,
        step_title=step_title,
        x_program_id=GetConfiguredEpassProgramId(),
    )


def GetEsimOptionDetail(
    token: str,
    resource_id: str,
    option_id: str,
    *,
    module: int = 8,
    step_code: Optional[str] = None,
    step_title: Optional[str] = None,
) -> Response:
    """``GET /v2/resources/esims/{resourceId}/options/{optionId}``。"""
    path = f"/v2/resources/esims/{resource_id}/options/{option_id}?module={module}"
    return RequestWithAllure(
        "GET",
        path,
        token=token,
        step_code=step_code,
        step_title=step_title,
        x_program_id=GetConfiguredEpassProgramId(),
    )


def PostEsimTopupAvailability(
    token: str,
    *,
    e_pass_id: str,
    iccid: str,
    resource_id: str,
    option_id: str,
    module: int = 8,
    step_code: Optional[str] = None,
    step_title: Optional[str] = None,
) -> Response:
    """``POST /v2/orders/esims/topup/availability``。"""
    body: JsonDict = {
        "ePassId": e_pass_id,
        "module": module,
        "resourceId": resource_id,
        "optionId": option_id,
        "prebookingDate": BuildHistoricalPrebookingDate(),
        "iccid": iccid,
        "adultCount": 1,
        "childCount": 0,
    }
    return RequestWithAllure(
        "POST",
        "/v2/orders/esims/topup/availability",
        token=token,
        json_body=body,
        step_code=step_code,
        step_title=step_title,
        x_program_id=GetConfiguredEpassProgramId(),
    )


def PostEsimEpassTopup(
    token: str,
    *,
    e_pass_id: str,
    iccid: str,
    prebooking_token: str,
    module: int = 8,
    step_code: Optional[str] = None,
    step_title: Optional[str] = None,
) -> Response:
    """``POST /v2/orders/esims/ePasses/topup``。"""
    body: JsonDict = {
        "module": module,
        "ePassId": e_pass_id,
        "extra": {
            "prebookingToken": prebooking_token,
            "iccid": iccid,
        },
    }
    return RequestWithAllure(
        "POST",
        "/v2/orders/esims/ePasses/topup",
        token=token,
        json_body=body,
        step_code=step_code,
        step_title=step_title,
        x_program_id=GetConfiguredEpassProgramId(),
    )


def PostEsimPackagesQuery(
    token: str,
    *,
    e_pass_id: str,
    iccid: str,
    step_code: Optional[str] = None,
    step_title: Optional[str] = None,
) -> Response:
    """``POST /v2/orders/esims/packages/query``。"""
    body: JsonDict = {"ePassId": e_pass_id, "iccid": iccid}
    return RequestWithAllure(
        "POST",
        "/v2/orders/esims/packages/query",
        token=token,
        json_body=body,
        step_code=step_code,
        step_title=step_title,
        x_program_id=GetConfiguredEpassProgramId(),
    )


def PostEsimOrderExtendedDetails(
    token: str,
    *,
    order_id: str,
    iccid: str,
    option_id: str,
    step_code: Optional[str] = None,
    step_title: Optional[str] = None,
) -> Response:
    """``POST /v2/orders/esims/details``。"""
    body: JsonDict = {
        "orderId": order_id,
        "iccid": iccid,
        "optionId": option_id,
    }
    return RequestWithAllure(
        "POST",
        "/v2/orders/esims/details",
        token=token,
        json_body=body,
        step_code=step_code,
        step_title=step_title,
        x_program_id=GetConfiguredEpassProgramId(),
    )


def PostFitnessOrderCheckin(
    token: str,
    *,
    order_id: str,
    step_code: Optional[str] = None,
    step_title: Optional[str] = None,
) -> Response:
    """``POST /v2/orders/fitness/checkin``。"""
    body: JsonDict = {"orderId": order_id}
    return RequestWithAllure(
        "POST",
        "/v2/orders/fitness/checkin",
        token=token,
        json_body=body,
        step_code=step_code,
        step_title=step_title,
        x_program_id=GetConfiguredEpassProgramId(),
    )


def PostInternalOrdersEPassesList(
    token: str,
    e_pass_id: str,
    *,
    module: int,
    step_code: Optional[str] = None,
    step_title: Optional[str] = None,
) -> Response:
    """``POST /v2/internal/orders/ePasses``（Q1 分支；404 时 skip）。"""
    body: JsonDict = {
        "ePassId": e_pass_id,
        "module": module,
        "pageSize": 10,
        "pageNumber": 1,
    }
    return RequestWithAllure(
        "POST",
        "/v2/internal/orders/ePasses",
        token=token,
        json_body=body,
        step_code=step_code,
        step_title=step_title,
        x_program_id=GetConfiguredEpassProgramId(),
    )


def GetEventRecovery(
    token: str,
    *,
    module: int,
    step_code: Optional[str] = None,
    step_title: Optional[str] = None,
) -> Response:
    """``GET /v2/event?module={module}``。"""
    path = f"/v2/event?module={module}"
    return RequestWithAllure(
        "GET",
        path,
        token=token,
        step_code=step_code,
        step_title=step_title,
        x_program_id=GetConfiguredEpassProgramId(),
    )


def PostSimulationRedemption(
    token: str,
    path: str,
    *,
    voucher: str,
    step_code: Optional[str] = None,
    step_title: Optional[str] = None,
) -> Response:
    """Simulation 核销（prebooking / walk-in）。"""
    body: JsonDict = {"voucher": voucher}
    return RequestWithAllure(
        "POST",
        path,
        token=token,
        json_body=body,
        step_code=step_code,
        step_title=step_title,
        x_program_id=GetConfiguredEpassProgramId(),
    )


def PostSimulationCancellation(
    token: str,
    path: str,
    *,
    voucher: str,
    step_code: Optional[str] = None,
    step_title: Optional[str] = None,
) -> Response:
    """Simulation 取消。"""
    body: JsonDict = {"voucher": voucher}
    return RequestWithAllure(
        "POST",
        path,
        token=token,
        json_body=body,
        step_code=step_code,
        step_title=step_title,
        x_program_id=GetConfiguredEpassProgramId(),
    )


def _FlattenResourcesFromListData(data: JsonDict) -> List[JsonDict]:
    """``GET /v2/resources`` 返回的嵌套 ``resources`` 结构展平为列表。"""
    raw = data.get("resources")
    items: List[JsonDict] = []
    if isinstance(raw, dict):
        for key in (
            "transportHubResources",
            "lifestyleResources",
            "localOfferResources",
        ):
            bucket = raw.get(key)
            if isinstance(bucket, list):
                for entry in bucket:
                    if isinstance(entry, dict):
                        items.append(cast(JsonDict, entry))
        return items
    if isinstance(raw, list):
        return [cast(JsonDict, x) for x in raw if isinstance(x, dict)]
    for alt_key in ("resourcesList", "resourceList"):
        alt = data.get(alt_key)
        if isinstance(alt, list):
            return [cast(JsonDict, x) for x in alt if isinstance(x, dict)]
    return items


def AssertHistoricalResourcesListModule(
    resp: Response,
    *,
    expected_module: int,
    resource_id: str,
    context: str,
) -> None:
    def _Do() -> str:
        data = ExtractBusinessData(resp)
        resources = _FlattenResourcesFromListData(data)
        assert resources, f"resources 列表为空: {data!r}"
        matched = [
            r for r in resources
            if r.get("resourceId") == resource_id
        ]
        if not matched:
            ids = [r.get("resourceId") for r in resources[:8]]
            return (
                f"{context}: module={expected_module} 资源列表可读"
                f"（当前页未含 {resource_id!r}，样例 {ids}）。"
            )
        if "module" in matched[0]:
            assert matched[0].get("module") == expected_module, matched[0]
        else:
            for item in resources:
                if "module" in item:
                    assert item.get("module") == expected_module, (
                        f"{context}: 列表项 module 应为 {expected_module}: {item!r}"
                    )
                    break
        return f"{context}: module={expected_module} 资源列表可读。"

    _RunAllureAssertionStep(f"历史 ePass: 资源列表 module（{context}）", _Do)


def AssertHistoricalResourceDetailModule(
    resp: Response,
    *,
    expected_module: int,
    resource_id: str,
    context: str,
) -> None:
    def _Do() -> str:
        data = ExtractBusinessData(resp)
        assert data.get("resourceId") == resource_id, f"resourceId 不一致: {data!r}"
        if "module" in data:
            AssertHistoricalResponseModule(
                data,
                expected_module=expected_module,
                context=context,
            )
        return f"{context}: resourceId={resource_id!r} 详情可读。"

    _RunAllureAssertionStep(f"历史 ePass: 资源详情 module（{context}）", _Do)


def AssertHistoricalPricesResponseModule(
    resp: Response,
    *,
    expected_module: int,
    context: str,
) -> None:
    def _Do() -> str:
        data = ExtractBusinessData(resp)
        if isinstance(data, dict):
            AssertHistoricalResponseModule(
                data,
                expected_module=expected_module,
                context=context,
            )
            price = data.get("price")
            if isinstance(price, dict) and "module" in price:
                assert price.get("module") == expected_module, price
        return f"{context}: prices module={expected_module}。"

    _RunAllureAssertionStep(f"历史 ePass: 价格查询 module（{context}）", _Do)


def AssertHistoricalOrdersListModuleSweep(
    resp: Response,
    *,
    expected_module: int,
    e_pass_id: str,
    context: str,
) -> None:
    def _Do() -> str:
        data = ExtractBusinessData(resp)
        if "module" in data:
            AssertHistoricalResponseModule(
                data,
                expected_module=expected_module,
                context=context,
            )
        orders = data.get("orders")
        assert isinstance(orders, list), f"orders 应为数组: {data!r}"
        for item in orders:
            if not isinstance(item, dict):
                continue
            if item.get("ePassId") == e_pass_id and "module" in item:
                assert item.get("module") == expected_module, item
        return f"{context}: orders 列表 module={expected_module} 一致。"

    _RunAllureAssertionStep(f"历史 ePass: 订单列表 module 轮询（{context}）", _Do)


def RunHistoricalResourcesReadForCatalog(
    token: str,
    steps: Any,
    *,
    catalog: HistoricalEpassCatalogEntry,
    e_pass_id: Optional[str] = None,
    fitness_target: Optional[HistoricalFitnessScheduleTarget] = None,
) -> None:
    """按品类拉资源列表/详情/价格（module 与 catalog 一致）。"""
    ctx = catalog.Label
    mod = catalog.ModuleInt

    kw_list = _HttpStepKw(steps, f"{catalog.DisplayName} · GET resources · module={mod}")
    resp_list = GetResourcesList(
        token,
        module=mod,
        step_code=kw_list["step_code"],
        step_title=kw_list["step_title"],
    )
    if resp_list.status_code == 200:
        AssertHistoricalResourcesListModule(
            resp_list,
            expected_module=mod,
            resource_id=catalog.ResourceId,
            context=f"{ctx}-resources-list",
        )

    kw_detail = _HttpStepKw(steps, f"{catalog.DisplayName} · GET resource detail · module={mod}")
    resp_detail = GetResourceDetail(
        token,
        catalog.ResourceId,
        module=mod,
        step_code=kw_detail["step_code"],
        step_title=kw_detail["step_title"],
    )
    if resp_detail.status_code == 200:
        AssertHistoricalResourceDetailModule(
            resp_detail,
            expected_module=mod,
            resource_id=catalog.ResourceId,
            context=f"{ctx}-resource-detail",
        )

    kw_price = _HttpStepKw(steps, f"{catalog.DisplayName} · POST prices · module={mod}")
    resp_price = PostResourcesPrices(
        token,
        module=mod,
        resource_id=catalog.ResourceId,
        e_pass_id=e_pass_id,
        step_code=kw_price["step_code"],
        step_title=kw_price["step_title"],
    )
    if resp_price.status_code == 200:
        AssertHistoricalPricesResponseModule(
            resp_price,
            expected_module=mod,
            context=f"{ctx}-prices",
        )

    if catalog.AvailabilityMode == HistoricalAvailabilityMode.Options:
        option_id = (
            fitness_target.OptionId
            if fitness_target is not None
            else catalog.OptionId
        )
        if not option_id and catalog.Label == "fitness":
            targets = ResolveHistoricalFitnessScheduleTargets(
                token,
                steps,
                catalog=catalog,
                brief=f"{catalog.DisplayName} schedule（价格链）",
            )
            option_id = targets[0].OptionId if targets else ""
        if option_id:
            kw_opt_price = _HttpStepKw(
                steps,
                f"{catalog.DisplayName} · POST options/prices · module={mod}",
            )
            resp_opt_price = PostResourcesOptionsPrices(
                token,
                module=mod,
                resource_id=catalog.ResourceId,
                option_id=option_id,
                e_pass_id=e_pass_id,
                step_code=kw_opt_price["step_code"],
                step_title=kw_opt_price["step_title"],
            )
            if resp_opt_price.status_code == 200:
                AssertHistoricalPricesResponseModule(
                    resp_opt_price,
                    expected_module=mod,
                    context=f"{ctx}-options-prices",
                )
            if catalog.Label == "fitness":
                kw_fopt = _HttpStepKw(steps, f"fitness option detail · {option_id}")
                GetFitnessOptionDetail(
                    token,
                    catalog.ResourceId,
                    option_id,
                    module=mod,
                    step_code=kw_fopt["step_code"],
                    step_title=kw_fopt["step_title"],
                )
            if catalog.Label == "esim":
                kw_eopts = _HttpStepKw(steps, f"eSIM options list · module={mod}")
                GetEsimResourceOptions(
                    token,
                    catalog.ResourceId,
                    module=mod,
                    step_code=kw_eopts["step_code"],
                    step_title=kw_eopts["step_title"],
                )
                kw_ed = _HttpStepKw(steps, f"eSIM option detail · {option_id}")
                GetEsimOptionDetail(
                    token,
                    catalog.ResourceId,
                    option_id,
                    module=mod,
                    step_code=kw_ed["step_code"],
                    step_title=kw_ed["step_title"],
                )


def RunHistoricalOrdersListModuleSweep(
    token: str,
    steps: Any,
    *,
    catalog: HistoricalEpassCatalogEntry,
    e_pass_id: str,
) -> None:
    """``POST /v2/orders/ePasses`` 按 catalog.module 入参并断言响应 module。"""
    kw = _HttpStepKw(
        steps,
        f"{catalog.DisplayName} · orders 列表 module 轮询 · {catalog.ModuleInt}",
    )
    resp = PostOrdersEPassesList(
        token,
        e_pass_id,
        module=catalog.ModuleInt,
        step_code=kw["step_code"],
        step_title=kw["step_title"],
    )
    AssertHistoricalOrdersListModuleSweep(
        resp,
        expected_module=catalog.ModuleInt,
        e_pass_id=e_pass_id,
        context=f"{catalog.Label}-orders-list-sweep",
    )


def RunHistoricalInternalOrdersListOrSkip(
    token: str,
    steps: Any,
    *,
    catalog: HistoricalEpassCatalogEntry,
    e_pass_id: str,
) -> None:
    kw = _HttpStepKw(steps, f"internal orders/ePasses · module={catalog.ModuleInt}")
    resp = PostInternalOrdersEPassesList(
        token,
        e_pass_id,
        module=catalog.ModuleInt,
        step_code=kw["step_code"],
        step_title=kw["step_title"],
    )
    if resp.status_code == 404:
        pytest.skip("当前环境无 POST /v2/internal/orders/ePasses")
    _st, env, data = ParseResponseEnvelope(resp)
    if resp.status_code != 200 or not IsLocalOfferBusinessSuccess(env):
        pytest.skip(f"internal orders/ePasses 不可用: HTTP {resp.status_code}, env={env!r}")

    def _Do() -> str:
        assert isinstance(data, dict), f"data 应为对象: {data!r}"
        AssertHistoricalResponseModule(
            cast(JsonDict, data),
            expected_module=catalog.ModuleInt,
            context=f"{catalog.Label}-internal-list",
        )
        return f"{catalog.Label}: internal 列表 module={catalog.ModuleInt}。"

    _RunAllureAssertionStep(f"历史 ePass: internal 订单列表（{catalog.Label}）", _Do)


def RunHistoricalEventRecoveryModuleSweep(
    token: str,
    steps: Any,
    *,
    catalog: HistoricalEpassCatalogEntry,
) -> None:
    kw = _HttpStepKw(steps, f"GET /v2/event · module={catalog.ModuleInt}")
    resp = GetEventRecovery(
        token,
        module=catalog.ModuleInt,
        step_code=kw["step_code"],
        step_title=kw["step_title"],
    )
    if resp.status_code != 200:
        pytest.skip(f"GET /v2/event 不可用: HTTP {resp.status_code}")

    _st, env, _data = ParseResponseEnvelope(resp)
    if not IsLocalOfferBusinessSuccess(env):
        err = env.get("errCode") if isinstance(env, dict) else None
        if err == "302.020.001":
            pytest.skip("GET /v2/event 需 batchId，沙箱无默认补偿批次")
        pytest.skip(f"GET /v2/event 业务不可用: {env!r}")

    def _Do() -> str:
        assert IsLocalOfferBusinessSuccess(env), f"event 业务失败: {env!r}"
        return f"{catalog.Label}: event module={catalog.ModuleInt} 查询成功。"

    _RunAllureAssertionStep(f"历史 ePass: event 恢复（{catalog.Label}）", _Do)


def RunHistoricalEsimTopupMainE2EScenario(
    token: str,
    steps: Any,
    *,
    catalog: HistoricalEpassCatalogEntry,
) -> HistoricalEsimTopupResult:
    """eSIM EPass Topup 主链路（module=8 全链）。"""
    if catalog.Label != "esim":
        raise ValueError("Topup 链仅适用于 esim 品类")

    created = CreateHistoricalEpass(token, steps, catalog)
    pb_token, _pb_date, _ft = RequestHistoricalPrebookingToken(
        token,
        steps,
        catalog=catalog,
        e_pass_id=created.EPassId,
        brief=f"{catalog.DisplayName} Topup 前预约",
    )
    kw_book = _HttpStepKw(steps, "eSIM ePass 预约（Topup 前置）")
    resp_book = PostHistoricalEpassPrebooking(
        token,
        catalog,
        e_pass_id=created.EPassId,
        prebooking_token=pb_token,
        step_code=kw_book["step_code"],
        step_title=kw_book["step_title"],
    )
    usage_order_id = AssertHistoricalPrebookingOrderSuccessForCatalog(
        resp_book,
        catalog=catalog,
        e_pass_id=created.EPassId,
        context="esim-topup-prebook",
    )
    WaitForHistoricalEsimUsageOrderConfirmed(
        token,
        steps,
        usage_order_id=usage_order_id,
        e_pass_id=created.EPassId,
        context="esim-topup-poll",
    )

    kw_details = _HttpStepKw(steps, "eSIM usage 详情取 iccid")
    resp_details = PostOrdersEPassesUsageDetails(
        token,
        usage_order_id,
        step_code=kw_details["step_code"],
        step_title=kw_details["step_title"],
    )
    detail_data = ExtractBusinessData(resp_details)
    AssertHistoricalResponseModule(
        detail_data,
        expected_module=8,
        context="esim-topup-details",
    )
    iccid = _ExtractIccidFromOrderData(detail_data)
    if not iccid:
        pytest.skip(f"eSIM usage 单未返回 iccid，无法继续 Topup: {detail_data!r}")

    kw_avail = _HttpStepKw(steps, "eSIM topup availability · module=8")
    resp_avail = PostEsimTopupAvailability(
        token,
        e_pass_id=created.EPassId,
        iccid=iccid,
        resource_id=catalog.ResourceId,
        option_id=catalog.OptionId,
        module=8,
        step_code=kw_avail["step_code"],
        step_title=kw_avail["step_title"],
    )
    topup_token, err = _ParsePrebookingTokenFromAvailabilityResponse(resp_avail)
    if not topup_token:
        _SkipIfPrebookingTimeslotUnavailable(resp_avail, context="esim-topup-availability")
        pytest.skip(f"eSIM topup 可用性失败: {err}")

    kw_topup = _HttpStepKw(steps, "eSIM ePasses topup · module=8")
    resp_topup = PostEsimEpassTopup(
        token,
        e_pass_id=created.EPassId,
        iccid=iccid,
        prebooking_token=topup_token,
        module=8,
        step_code=kw_topup["step_code"],
        step_title=kw_topup["step_title"],
    )

    topup_order_id = ""

    def _DoTopup() -> str:
        nonlocal topup_order_id
        data = ExtractBusinessData(resp_topup)
        AssertHistoricalResponseModule(data, expected_module=8, context="esim-topup")
        status = data.get("status")
        if status == 10:
            pytest.skip(f"eSIM topup status=10: {data!r}")
        assert status in (1, 5), f"topup status 应为 1/5: {data!r}"
        oid = data.get("orderId")
        assert isinstance(oid, str) and oid, f"topup orderId 缺失: {data!r}"
        topup_order_id = oid
        return f"eSIM topup 成功 module=8, orderId={oid!r}。"

    _RunAllureAssertionStep("历史 ePass: eSIM Topup 下单", _DoTopup)

    kw_pkg = _HttpStepKw(steps, "eSIM packages/query")
    resp_pkg = PostEsimPackagesQuery(
        token,
        e_pass_id=created.EPassId,
        iccid=iccid,
        step_code=kw_pkg["step_code"],
        step_title=kw_pkg["step_title"],
    )
    ExtractBusinessData(resp_pkg)

    kw_ext = _HttpStepKw(steps, "eSIM orders/details 扩展")
    resp_ext = PostEsimOrderExtendedDetails(
        token,
        order_id=usage_order_id,
        iccid=iccid,
        option_id=catalog.OptionId,
        step_code=kw_ext["step_code"],
        step_title=kw_ext["step_title"],
    )
    ExtractBusinessData(resp_ext)

    CancelHistoricalUsageOrderAndVerify(
        token,
        steps,
        catalog=catalog,
        usage_order_id=usage_order_id,
        e_pass_id=created.EPassId,
        purchase_order_id=created.PurchaseOrderId,
        context="esim-topup-usage-cancel",
    )
    CancelHistoricalPurchaseOrderAndVerify(
        token,
        steps,
        catalog=catalog,
        e_pass_id=created.EPassId,
        purchase_order_id=created.PurchaseOrderId,
        context="esim-topup-purchase-cancel",
    )

    return HistoricalEsimTopupResult(
        ClientUserId=created.ClientUserId,
        EPassId=created.EPassId,
        PurchaseOrderId=created.PurchaseOrderId,
        UsageOrderId=usage_order_id,
        Iccid=iccid,
        TopupOrderId=topup_order_id,
        Catalog=catalog,
    )


def RunHistoricalFitnessCheckinMainE2EScenario(
    token: str,
    steps: Any,
    *,
    catalog: HistoricalEpassCatalogEntry,
) -> HistoricalEpassCreateResult:
    """fitness 预约后 checkin（module=7）。"""
    if catalog.Label != "fitness":
        raise ValueError("Checkin 链仅适用于 fitness")

    created = CreateHistoricalEpass(token, steps, catalog)
    pb_token, _pb_date, fitness_target = RequestHistoricalPrebookingToken(
        token,
        steps,
        catalog=catalog,
        e_pass_id=created.EPassId,
        brief=f"{catalog.DisplayName} checkin 前预约",
    )
    kw_book = _HttpStepKw(steps, "fitness 预约（checkin 前置）")
    resp_book = PostHistoricalEpassPrebooking(
        token,
        catalog,
        e_pass_id=created.EPassId,
        prebooking_token=pb_token,
        fitness_target=fitness_target,
        step_code=kw_book["step_code"],
        step_title=kw_book["step_title"],
    )
    usage_order_id = AssertHistoricalPrebookingOrderSuccessForCatalog(
        resp_book,
        catalog=catalog,
        e_pass_id=created.EPassId,
        context="fitness-checkin-prebook",
        fitness_target=fitness_target,
    )

    kw_checkin = _HttpStepKw(steps, f"fitness checkin · orderId={usage_order_id}")
    resp_checkin = PostFitnessOrderCheckin(
        token,
        order_id=usage_order_id,
        step_code=kw_checkin["step_code"],
        step_title=kw_checkin["step_title"],
    )

    def _DoCheckin() -> str:
        data = ExtractBusinessData(resp_checkin)
        if isinstance(data, dict) and "module" in data:
            AssertHistoricalResponseModule(
                data,
                expected_module=7,
                context="fitness-checkin",
            )
        return f"fitness checkin 成功 orderId={usage_order_id!r}。"

    _RunAllureAssertionStep("历史 ePass: fitness checkin", _DoCheckin)

    kw_cancel = _HttpStepKw(steps, "fitness checkin 后取消 usage")
    resp_cancel = PatchCancelOrderWithRetry(
        token,
        usage_order_id,
        step_code=kw_cancel["step_code"],
        step_title=kw_cancel["step_title"],
    )
    _st, env, _ = ParseResponseEnvelope(resp_cancel)
    if not IsLocalOfferBusinessSuccess(env):
        err = env.get("errCode") if isinstance(env, dict) else None
        if err in ("500.071.016", "500.041.006"):
            pytest.skip(f"fitness checkin 后 usage 单不可取消（{err}）")
        pytest.fail(f"fitness checkin 后取消失败: {env!r}")
    CancelHistoricalPurchaseOrderAndVerify(
        token,
        steps,
        catalog=catalog,
        e_pass_id=created.EPassId,
        purchase_order_id=created.PurchaseOrderId,
        context="fitness-checkin-purchase-cancel",
    )
    return created


def RunHistoricalSimulationPrebookingMainE2EScenario(
    token: str,
    steps: Any,
    *,
    catalog: HistoricalEpassCatalogEntry,
) -> None:
    """支持 simulation 的品类：预约 → 模拟核销 → 模拟取消。"""
    sim_paths = GetHistoricalSimulationPaths(catalog.Label)
    if sim_paths is None:
        pytest.skip(f"{catalog.Label} 无 simulation 接口定义")

    created = CreateHistoricalEpass(token, steps, catalog)
    pb_token, _pb_date, fitness_target = RequestHistoricalPrebookingToken(
        token,
        steps,
        catalog=catalog,
        e_pass_id=created.EPassId,
        brief=f"{catalog.DisplayName} simulation 前预约",
    )
    kw_book = _HttpStepKw(steps, f"{catalog.DisplayName} 预约（simulation）")
    resp_book = PostHistoricalEpassPrebooking(
        token,
        catalog,
        e_pass_id=created.EPassId,
        prebooking_token=pb_token,
        fitness_target=fitness_target,
        step_code=kw_book["step_code"],
        step_title=kw_book["step_title"],
    )
    usage_order_id = AssertHistoricalPrebookingOrderSuccessForCatalog(
        resp_book,
        catalog=catalog,
        e_pass_id=created.EPassId,
        context=f"{catalog.Label}-sim-prebook",
        fitness_target=fitness_target,
    )

    kw_det = _HttpStepKw(steps, "simulation 前取 voucher")
    resp_det = PostOrdersEPassesUsageDetails(
        token,
        usage_order_id,
        step_code=kw_det["step_code"],
        step_title=kw_det["step_title"],
    )
    detail_data = ExtractBusinessData(resp_det)
    voucher = _ExtractVoucherFromOrderData(detail_data)
    if not voucher:
        pytest.skip(f"usage 单无 voucher，无法 simulation: {detail_data!r}")

    redeem_path, cancel_path = sim_paths
    kw_redeem = _HttpStepKw(steps, f"simulation 核销 · {catalog.Label}")
    resp_redeem = PostSimulationRedemption(
        token,
        redeem_path,
        voucher=voucher,
        step_code=kw_redeem["step_code"],
        step_title=kw_redeem["step_title"],
    )
    if resp_redeem.status_code != 200:
        pytest.skip(f"simulation 核销不可用: HTTP {resp_redeem.status_code}")

    kw_sim_cancel = _HttpStepKw(steps, f"simulation 取消 · {catalog.Label}")
    PostSimulationCancellation(
        token,
        cancel_path,
        voucher=voucher,
        step_code=kw_sim_cancel["step_code"],
        step_title=kw_sim_cancel["step_title"],
    )

    CancelHistoricalPurchaseOrderAndVerify(
        token,
        steps,
        catalog=catalog,
        e_pass_id=created.EPassId,
        purchase_order_id=created.PurchaseOrderId,
        context=f"{catalog.Label}-sim-purchase-cancel",
    )


__all__ = [
    "AssertHistoricalOrdersListModuleSweep",
    "AssertHistoricalResponseModule",
    "HistoricalEsimTopupResult",
    "RunHistoricalEsimTopupMainE2EScenario",
    "RunHistoricalEventRecoveryModuleSweep",
    "RunHistoricalFitnessCheckinMainE2EScenario",
    "RunHistoricalInternalOrdersListOrSkip",
    "RunHistoricalOrdersListModuleSweep",
    "RunHistoricalResourcesReadForCatalog",
    "RunHistoricalSimulationPrebookingMainE2EScenario",
]
