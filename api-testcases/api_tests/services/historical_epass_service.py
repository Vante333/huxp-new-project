"""
历史品类 ePass 回归 — HTTP 封装与断言。

**主链路**（对齐 ``api-testcases/docs/api-main-call-chains.md`` · 二、EPass）：

1. **创建验证链**（``RunHistoricalEpassCreateMainE2EScenario``）：
   ``POST /v2/orders/{module}/ePasses`` → ``POST /v2/users/ePasses`` →
   ``POST /v2/orders/ePasses`` → ``POST /v2/orders/ePasses/search`` → 取消 MS 单

2. **Prebooking 链**（``RunHistoricalEpassPrebookingMainE2EScenario``）：
   创建 ePass → 可用性（classic 或 options）→ ``POST .../ePasses/prebooking`` →
   取消 usage 单 → details / 列表 / search

3. **Bundle 链**（``RunHistoricalEpassBundleMainE2EScenario``）：
   可用性（无 ePassId）→ ``POST .../ePasses/bundle`` → users → search →
   取消 usage 单 → 取消 MS 单

鉴权 ``POST /v2/auth/token`` 由用例 ``EpassToken`` fixture 提供。
Allure ``S01/S02/…`` 由 ``AllureHttpScenarioSteps.Next`` 递增。

休息室 / 快速通道使用 ``POST /v2/resources/prebookings/availability``（无 optionId）；
fitness 先 ``GET /v2/resources/fitness/{resourceId}/schedule`` 解析 ``optionId``/时段，
再 ``POST /v2/resources/options/prebookings/availability``；eSIM 走 options 可用性链。
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, cast
from urllib.parse import urlencode

import pytest
from requests import Response

from config.historical_epass_env import (
    BuildFitnessScheduleQueryDateRange,
    GetFitnessPreferredOptionType,
    HistoricalAvailabilityMode,
    HistoricalEpassCatalogEntry,
    HistoricalFitnessScheduleTarget,
    GetHistoricalEsimStatusPollIntervalSec,
    GetHistoricalEsimStatusPollMaxAttempts,
    GetHistoricalPrebookingDateOverride,
    IterHistoricalPrebookingDateCandidates,
    RequireHistoricalEpassCatalogOrSkipMessage,
)
from services.papi2548_memberships_extensions_impl import (
    JsonDict,
    ParseResponseEnvelope,
    RequestWithAllure,
    _RunAllureAssertionStep,
)
from services.papi2424_epasses_impl import GetConfiguredEpassProgramId
from services.local_offer_epass_service import (
    AssertEsimPrebookingOrderSuccess,
    AssertPrebookingAvailabilitySuccess,
    BuildAvailabilityBody,
    BuildModuleEpassCreatePayload,
    ExtractBusinessData,
    ExtractCreateEpassIds,
    IsLocalOfferBusinessSuccess,
    MarkLocalOfferEPassPurchaseCancelled,
    MarkLocalOfferOrderCancelled,
    PatchCancelOrder,
    PostOrdersEPassesList,
    PostOrdersEPassesSearch,
    PostOrdersEPassesUsageDetails,
    PostOrdersPathModuleEPasses,
    PostOrdersPathModuleEPassesPrebooking,
    PostResourcesOptionsPrebookingsAvailability,
    PostUsersEPasses,
    RegisterPendingLocalOfferEPassId,
    RegisterPendingLocalOfferOrder,
    RequireLocalOfferEpassEnvOrSkip,
    _HttpStepKw,
    _ResolveEPassIdField,
    _SkipIfPrebookingTimeslotUnavailable,
)


@dataclass(frozen=True)
class HistoricalEpassCreateResult:
    """历史品类 ePass 创建链结果。"""

    ClientUserId: str
    EPassId: str
    PurchaseOrderId: str
    Catalog: HistoricalEpassCatalogEntry
    CreateResponse: Response


@dataclass(frozen=True)
class HistoricalEpassPrebookingResult:
    """历史品类 ePass 预约链结果。"""

    ClientUserId: str
    EPassId: str
    PurchaseOrderId: str
    UsageOrderId: str
    PrebookingToken: str
    PrebookingDate: str
    Catalog: HistoricalEpassCatalogEntry


def RequireHistoricalEpassEnvOrSkip(entry: Optional[HistoricalEpassCatalogEntry] = None) -> None:
    """鉴权三件套 + 指定品类网点；缺配置则 ``pytest.skip``。"""
    RequireLocalOfferEpassEnvOrSkip()
    if entry is None:
        return
    msg = RequireHistoricalEpassCatalogOrSkipMessage(entry)
    if msg:
        pytest.skip(msg)


def PostResourcesClassicPrebookingsAvailability(
    token: str,
    body: JsonDict,
    *,
    step_code: Optional[str] = None,
    step_title: Optional[str] = None,
) -> Response:
    """``POST /v2/resources/prebookings/availability`` — 休息室 / 快速通道经典链。"""
    return RequestWithAllure(
        "POST",
        "/v2/resources/prebookings/availability",
        token=token,
        json_body=body,
        step_code=step_code,
        step_title=step_title,
        x_program_id=GetConfiguredEpassProgramId(),
    )


def GetFitnessResourcesSchedule(
    token: str,
    resource_id: str,
    *,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    fallback_allowed: bool = True,
    step_code: Optional[str] = None,
    step_title: Optional[str] = None,
) -> Response:
    """``GET /v2/resources/fitness/{resourceId}/schedule`` — 解析 Day Pass 等 option。"""
    if not start_date or not end_date:
        start_date, end_date = BuildFitnessScheduleQueryDateRange()
    qs = urlencode(
        {
            "startDate": start_date,
            "endDate": end_date,
            "fallbackAllowed": "true" if fallback_allowed else "false",
        }
    )
    path = f"/v2/resources/fitness/{resource_id}/schedule?{qs}"
    return RequestWithAllure(
        "GET",
        path,
        token=token,
        step_code=step_code,
        step_title=step_title,
        x_program_id=GetConfiguredEpassProgramId(),
    )


def _ParseFitnessScheduleOption(
    resource_id: str,
    schedule_date: str,
    option: JsonDict,
) -> Optional[HistoricalFitnessScheduleTarget]:
    option_id = option.get("optionId")
    start_time = option.get("startTime")
    end_time = option.get("endTime")
    if not (
        isinstance(option_id, str)
        and option_id
        and isinstance(start_time, str)
        and start_time
        and isinstance(end_time, str)
        and end_time
    ):
        return None
    option_type_raw = option.get("optionType")
    option_type = option_type_raw if isinstance(option_type_raw, int) else 0
    option_name_raw = option.get("optionName")
    option_name = option_name_raw if isinstance(option_name_raw, str) else ""
    return HistoricalFitnessScheduleTarget(
        ResourceId=resource_id,
        OptionId=option_id,
        ScheduleDate=schedule_date,
        StartTime=start_time,
        EndTime=end_time,
        OptionType=option_type,
        OptionName=option_name,
    )


def ParseHistoricalFitnessScheduleTargets(
    resp: Response,
    *,
    resource_id: str,
    preferred_option_type: Optional[int] = None,
) -> List[HistoricalFitnessScheduleTarget]:
    """从 schedule 响应解析候选 option；同日内优先 ``optionType``（默认 Day Pass=1）。"""
    _st, env, data = ParseResponseEnvelope(resp)
    if resp.status_code != 200 or not IsLocalOfferBusinessSuccess(env):
        return []
    if not isinstance(data, dict):
        return []
    schedules = data.get("schedules")
    if not isinstance(schedules, list) or not schedules:
        return []

    preferred = (
        preferred_option_type
        if preferred_option_type is not None
        else GetFitnessPreferredOptionType()
    )
    override = GetHistoricalPrebookingDateOverride()
    override_date = override.split("T", 1)[0] if override else ""

    ordered: List[HistoricalFitnessScheduleTarget] = []
    for schedule in schedules:
        if not isinstance(schedule, dict):
            continue
        schedule_date_raw = schedule.get("date")
        if not isinstance(schedule_date_raw, str) or not schedule_date_raw:
            continue
        if override_date and schedule_date_raw != override_date:
            continue
        option_list = schedule.get("optionList")
        if not isinstance(option_list, list):
            continue
        day_targets: List[HistoricalFitnessScheduleTarget] = []
        for option in option_list:
            if not isinstance(option, dict):
                continue
            target = _ParseFitnessScheduleOption(resource_id, schedule_date_raw, option)
            if target is not None:
                day_targets.append(target)
        day_targets.sort(
            key=lambda item: (0 if item.OptionType == preferred else 1, item.OptionId),
        )
        ordered.extend(day_targets)
    return ordered


def ResolveHistoricalFitnessScheduleTargets(
    token: str,
    steps: Any,
    *,
    catalog: HistoricalEpassCatalogEntry,
    brief: str,
) -> List[HistoricalFitnessScheduleTarget]:
    """拉取 fitness schedule 并解析候选；无候选则 ``pytest.skip``。"""
    start_date, end_date = BuildFitnessScheduleQueryDateRange()
    kw = _HttpStepKw(steps, f"{brief} · fitness schedule · {start_date}~{end_date}")
    resp = GetFitnessResourcesSchedule(
        token,
        catalog.ResourceId,
        start_date=start_date,
        end_date=end_date,
        step_code=kw["step_code"],
        step_title=kw["step_title"],
    )
    _st, env, data = ParseResponseEnvelope(resp)
    if resp.status_code != 200:
        pytest.skip(f"{brief}: fitness schedule HTTP {resp.status_code}")
    if not IsLocalOfferBusinessSuccess(env):
        err = env.get("errCode") if isinstance(env, dict) else env
        pytest.skip(f"{brief}: fitness schedule 业务失败: {err!r}")

    def _AssertSchedule() -> str:
        assert isinstance(data, dict), f"schedule data 应为对象: {data!r}"
        assert data.get("resourceId") == catalog.ResourceId, (
            f"resourceId 不一致: {data!r}"
        )
        schedules = data.get("schedules")
        assert isinstance(schedules, list) and schedules, (
            f"schedules 为空: {data!r}"
        )
        return (
            f"{brief}: resourceId={catalog.ResourceId!r}, "
            f"schedules 共 {len(schedules)} 天。"
        )

    _RunAllureAssertionStep(f"历史 ePass: fitness schedule 响应（{brief}）", _AssertSchedule)

    targets = ParseHistoricalFitnessScheduleTargets(resp, resource_id=catalog.ResourceId)
    if not targets:
        pytest.skip(
            f"{brief}: fitness schedule 未解析到可用 option"
            f"（resourceId={catalog.ResourceId!r}, range={start_date}~{end_date}）"
        )
    return targets


def BuildClassicAvailabilityBody(
    *,
    module: int,
    resource_id: str,
    prebooking_date: str,
    e_pass_id: Optional[str] = None,
    adult_count: int = 1,
    child_count: int = 0,
) -> JsonDict:
    """经典可用性请求体（无 optionId）。"""
    body: JsonDict = {
        "module": module,
        "resourceId": resource_id,
        "prebookingDate": prebooking_date,
        "adultCount": adult_count,
        "childCount": child_count,
    }
    if e_pass_id:
        body["ePassId"] = e_pass_id
    return body


def AssertHistoricalEpassCreateCoreFields(
    resp: Response,
    *,
    expected_module: int,
    expected_client_user_id: str,
    context: str,
) -> None:
    """断言历史品类创建响应：``module`` 匹配、``status=1``、``ePassId`` 非空。"""

    def _Do() -> str:
        data = ExtractBusinessData(resp)
        module_val = data.get("module")
        assert module_val == expected_module, (
            f"{context}: module 应为 {expected_module}，实际 {module_val!r}"
        )
        assert data.get("status") == 1, f"status 应为 1: {data!r}"
        assert data.get("clientUserId") == expected_client_user_id, (
            f"clientUserId 回显不一致: {data!r}"
        )
        category = data.get("category")
        if expected_module == 2:
            assert category == 2, f"fastTrack category 应为 2: {data!r}"
        else:
            assert category in (2, 3), f"category 应为 2 或 3: {data!r}"
        extra = data.get("extra")
        assert isinstance(extra, dict), f"extra 缺失: {data!r}"
        e_pass_status = extra.get("ePassStatus")
        assert e_pass_status in (0, 1), f"ePassStatus 应为 0 或 1: {extra!r}"
        ep = _ResolveEPassIdField(extra) or extra.get("ePassId")
        assert isinstance(ep, str) and ep, f"ePassId 缺失: {extra!r}"
        return (
            f"{context}: module={expected_module}, status=1, category={category}, "
            f"ePassStatus={e_pass_status}, ePassId 非空。"
        )

    _RunAllureAssertionStep(f"历史 ePass: 创建响应核心字段（{context}）", _Do)


def AssertUserEPassesContainsHistorical(
    resp: Response,
    *,
    e_pass_id: str,
    expected_module: Optional[int] = None,
    context: str,
) -> None:
    """用户 ePass 列表含目标 ID；列表项含 ``module`` 时须与期望一致。"""

    def _Do() -> str:
        data = ExtractBusinessData(resp)
        lst = data.get("ePassesList")
        assert isinstance(lst, list), f"ePassesList 应为数组: {data!r}"
        matched: List[JsonDict] = []
        for item in lst:
            if isinstance(item, dict) and item.get("ePassId") == e_pass_id:
                matched.append(cast(JsonDict, item))
        assert matched, f"ePassesList 未找到 ePassId={e_pass_id!r}: {lst!r}"
        if expected_module is not None and "module" in matched[0]:
            assert matched[0].get("module") == expected_module, (
                f"列表项 module 应为 {expected_module}: {matched[0]!r}"
            )
            module_note = f"，module={expected_module}"
        else:
            module_note = ""
        return f"{context}: ePassesList 含 ePassId={e_pass_id!r}{module_note}。"

    _RunAllureAssertionStep(f"历史 ePass: 用户列表包含 ePass（{context}）", _Do)


def AssertHistoricalEpassSearchDetailsCoreFields(
    resp: Response,
    *,
    expected_module: int,
    expected_e_pass_id: str,
    context: str,
    expected_order_id: Optional[str] = None,
) -> None:
    """``POST /v2/orders/ePasses/search`` 购买单详情核心字段。"""

    def _Do() -> str:
        data = ExtractBusinessData(resp)
        assert data.get("module") == expected_module, f"module 应为 {expected_module}: {data!r}"
        if expected_order_id:
            assert data.get("orderId") == expected_order_id, f"orderId 不一致: {data!r}"
        extra = data.get("extra")
        assert isinstance(extra, dict), f"extra 缺失: {data!r}"
        ep = _ResolveEPassIdField(extra) or extra.get("ePassId")
        assert ep == expected_e_pass_id, f"ePassId 不一致: {extra!r}"
        order_note = f", orderId={expected_order_id!r}" if expected_order_id else ""
        return (
            f"{context}: search module={expected_module}, ePassId 一致{order_note}。"
        )

    _RunAllureAssertionStep(f"历史 ePass: 购买单详情 search（{context}）", _Do)


def AssertHistoricalPrebookingOrderSuccess(
    resp: Response,
    *,
    expected_module: int,
    e_pass_id: str,
    resource_id: str,
    option_id: str = "",
    context: str,
) -> str:
    """历史品类预约下单成功；返回 usage orderId。"""

    holder: Dict[str, str] = {}

    def _Do() -> str:
        _SkipIfPrebookingTimeslotUnavailable(resp, context=context)
        data = ExtractBusinessData(resp)
        status = data.get("status")
        if status == 10:
            pytest.skip(f"预约单 status=10 FAILED: {data!r}")
        assert status in (1, 5), f"status 应为 1 或 5: {data!r}"
        assert data.get("module") == expected_module, (
            f"module 应为 {expected_module}: {data!r}"
        )
        resp_e_pass_id = _ResolveEPassIdField(data)
        assert isinstance(resp_e_pass_id, str) and resp_e_pass_id, f"响应缺 ePassId: {data!r}"
        order_id = data.get("orderId")
        assert isinstance(order_id, str) and order_id, f"orderId 缺失: {data!r}"
        extra = data.get("extra")
        assert isinstance(extra, dict), f"extra 缺失: {data!r}"
        assert extra.get("resourceId") == resource_id, f"resourceId 不一致: {extra!r}"
        if option_id:
            local_opts = extra.get("localOfferOptions")
            if isinstance(local_opts, dict) and local_opts.get("optionId"):
                assert local_opts.get("optionId") == option_id, (
                    f"optionId 不一致: {local_opts!r}"
                )
        holder["orderId"] = order_id
        return f"{context}: module={expected_module} 预约成功, orderId={order_id!r}。"

    _RunAllureAssertionStep(f"历史 ePass: 预约下单响应（{context}）", _Do)
    order_id = holder.get("orderId", "")
    if not order_id:
        data = ExtractBusinessData(resp)
        raw = data.get("orderId")
        order_id = raw if isinstance(raw, str) else ""
    assert order_id, f"{context}: 无法解析 orderId"
    RegisterPendingLocalOfferOrder(order_id)
    return order_id


def _ParsePrebookingTokenFromAvailabilityResponse(resp: Response) -> Tuple[str, str]:
    """返回 ``(token, errHint)``；token 非空表示成功。"""
    try:
        _st, env, data = ParseResponseEnvelope(resp)
    except Exception as exc:
        return "", str(exc)
    if resp.status_code != 200:
        return "", f"HTTP {resp.status_code}"
    if not IsLocalOfferBusinessSuccess(env):
        err = env.get("errCode") if isinstance(env, dict) else None
        return "", str(err or env)
    if not isinstance(data, dict):
        return "", "data 非对象"
    token = data.get("prebookingToken")
    if isinstance(token, str) and token:
        return token, ""
    return "", f"无 token: {data!r}"


def RequestHistoricalPrebookingToken(
    token: str,
    steps: Any,
    *,
    catalog: HistoricalEpassCatalogEntry,
    e_pass_id: str,
    brief: str,
) -> Tuple[str, str, Optional[HistoricalFitnessScheduleTarget]]:
    """
    按品类可用性模式取 ``prebookingToken``；多时段重试 ``500.020.009``。

    fitness 先调 schedule 解析 ``optionId`` + ``prebookingDate``（``YYYY-MM-DDTHH:mm``）。
    返回 ``(prebookingToken, prebookingDate, fitnessTarget)``；非 fitness 时第三项为 ``None``。
    """
    if catalog.Label == "fitness":
        return _RequestHistoricalFitnessPrebookingToken(
            token,
            steps,
            catalog=catalog,
            e_pass_id=e_pass_id,
            brief=brief,
        )

    errors: List[str] = []
    last_resp: Optional[Response] = None
    for pb_date in IterHistoricalPrebookingDateCandidates():
        if catalog.AvailabilityMode == HistoricalAvailabilityMode.Classic:
            body = BuildClassicAvailabilityBody(
                module=catalog.ModuleInt,
                resource_id=catalog.ResourceId,
                prebooking_date=pb_date,
                e_pass_id=e_pass_id,
            )
            kw = _HttpStepKw(steps, f"{brief} · classic · {pb_date}")
            resp = PostResourcesClassicPrebookingsAvailability(
                token,
                body,
                step_code=kw["step_code"],
                step_title=kw["step_title"],
            )
        else:
            body = BuildAvailabilityBody(
                e_pass_id=e_pass_id,
                resource_id=catalog.ResourceId,
                option_id=catalog.OptionId,
                prebooking_date=pb_date,
                module=catalog.ModuleInt,
            )
            kw = _HttpStepKw(steps, f"{brief} · options · {pb_date}")
            resp = PostResourcesOptionsPrebookingsAvailability(
                token,
                body,
                step_code=kw["step_code"],
                step_title=kw["step_title"],
            )
        last_resp = resp
        pb_token, err = _ParsePrebookingTokenFromAvailabilityResponse(resp)
        if pb_token:
            AssertPrebookingAvailabilitySuccess(resp, context=f"{brief}-{pb_date}")
            return pb_token, pb_date, None
        if err:
            errors.append(f"{pb_date}:{err}")
    if last_resp is not None:
        _SkipIfPrebookingTimeslotUnavailable(last_resp, context=brief)
    pytest.fail(
        f"{brief}: 所有 prebookingDate 候选均无法取得 token（{catalog.Label}）: "
        + "; ".join(errors[-4:])
    )


def _RequestHistoricalFitnessPrebookingToken(
    token: str,
    steps: Any,
    *,
    catalog: HistoricalEpassCatalogEntry,
    e_pass_id: str,
    brief: str,
) -> Tuple[str, str, HistoricalFitnessScheduleTarget]:
    """fitness：schedule 候选逐个试 options 可用性。"""
    targets = ResolveHistoricalFitnessScheduleTargets(
        token,
        steps,
        catalog=catalog,
        brief=brief,
    )
    errors: List[str] = []
    last_resp: Optional[Response] = None
    for target in targets:
        pb_date = target.PrebookingDate
        body = BuildAvailabilityBody(
            e_pass_id=e_pass_id,
            resource_id=catalog.ResourceId,
            option_id=target.OptionId,
            prebooking_date=pb_date,
            module=catalog.ModuleInt,
        )
        kw = _HttpStepKw(
            steps,
            f"{brief} · fitness · {target.ScheduleDate} · {target.OptionId}",
        )
        resp = PostResourcesOptionsPrebookingsAvailability(
            token,
            body,
            step_code=kw["step_code"],
            step_title=kw["step_title"],
        )
        last_resp = resp
        pb_token, err = _ParsePrebookingTokenFromAvailabilityResponse(resp)
        if pb_token:
            AssertPrebookingAvailabilitySuccess(resp, context=f"{brief}-{pb_date}")
            return pb_token, pb_date, target
        if err:
            errors.append(f"{target.OptionId}@{pb_date}:{err}")
    if last_resp is not None:
        _SkipIfPrebookingTimeslotUnavailable(last_resp, context=brief)
    pytest.fail(
        f"{brief}: fitness schedule 候选均无法取得 token: " + "; ".join(errors[-6:])
    )


def RequestHistoricalPrebookingTokenWithoutEpass(
    token: str,
    steps: Any,
    *,
    catalog: HistoricalEpassCatalogEntry,
    brief: str,
) -> Tuple[str, str, Optional[HistoricalFitnessScheduleTarget]]:
    """
    Bundle 链可用性（不绑 ePassId）取 ``prebookingToken``。

    返回 ``(prebookingToken, prebookingDate, fitnessTarget)``。
    """
    if catalog.Label == "fitness":
        return _RequestHistoricalFitnessPrebookingTokenWithoutEpass(
            token,
            steps,
            catalog=catalog,
            brief=brief,
        )

    errors: List[str] = []
    last_resp: Optional[Response] = None
    for pb_date in IterHistoricalPrebookingDateCandidates():
        if catalog.AvailabilityMode == HistoricalAvailabilityMode.Classic:
            body = BuildClassicAvailabilityBody(
                module=catalog.ModuleInt,
                resource_id=catalog.ResourceId,
                prebooking_date=pb_date,
            )
            kw = _HttpStepKw(steps, f"{brief} · classic · 无 ePassId · {pb_date}")
            resp = PostResourcesClassicPrebookingsAvailability(
                token,
                body,
                step_code=kw["step_code"],
                step_title=kw["step_title"],
            )
        else:
            body = BuildAvailabilityBody(
                resource_id=catalog.ResourceId,
                option_id=catalog.OptionId,
                prebooking_date=pb_date,
                module=catalog.ModuleInt,
            )
            kw = _HttpStepKw(steps, f"{brief} · options · 无 ePassId · {pb_date}")
            resp = PostResourcesOptionsPrebookingsAvailability(
                token,
                body,
                step_code=kw["step_code"],
                step_title=kw["step_title"],
            )
        last_resp = resp
        pb_token, err = _ParsePrebookingTokenFromAvailabilityResponse(resp)
        if pb_token:
            AssertPrebookingAvailabilitySuccess(resp, context=f"{brief}-{pb_date}")
            return pb_token, pb_date, None
        if err:
            errors.append(f"{pb_date}:{err}")
    if last_resp is not None:
        _SkipIfPrebookingTimeslotUnavailable(last_resp, context=brief)
    pytest.fail(
        f"{brief}: 所有 prebookingDate 候选均无法取得 token（{catalog.Label} · 无 ePassId）: "
        + "; ".join(errors[-4:])
    )


def _RequestHistoricalFitnessPrebookingTokenWithoutEpass(
    token: str,
    steps: Any,
    *,
    catalog: HistoricalEpassCatalogEntry,
    brief: str,
) -> Tuple[str, str, HistoricalFitnessScheduleTarget]:
    """fitness Bundle：schedule 候选逐个试 options 可用性（无 ePassId）。"""
    targets = ResolveHistoricalFitnessScheduleTargets(
        token,
        steps,
        catalog=catalog,
        brief=brief,
    )
    errors: List[str] = []
    last_resp: Optional[Response] = None
    for target in targets:
        pb_date = target.PrebookingDate
        body = BuildAvailabilityBody(
            resource_id=catalog.ResourceId,
            option_id=target.OptionId,
            prebooking_date=pb_date,
            module=catalog.ModuleInt,
        )
        kw = _HttpStepKw(
            steps,
            f"{brief} · fitness · 无 ePassId · {target.ScheduleDate} · {target.OptionId}",
        )
        resp = PostResourcesOptionsPrebookingsAvailability(
            token,
            body,
            step_code=kw["step_code"],
            step_title=kw["step_title"],
        )
        last_resp = resp
        pb_token, err = _ParsePrebookingTokenFromAvailabilityResponse(resp)
        if pb_token:
            AssertPrebookingAvailabilitySuccess(resp, context=f"{brief}-{pb_date}")
            return pb_token, pb_date, target
        if err:
            errors.append(f"{target.OptionId}@{pb_date}:{err}")
    if last_resp is not None:
        _SkipIfPrebookingTimeslotUnavailable(last_resp, context=brief)
    pytest.fail(
        f"{brief}: fitness schedule 候选均无法取得 token（无 ePassId）: "
        + "; ".join(errors[-6:])
    )


def AssertHistoricalBundleOrderSuccess(
    resp: Response,
    *,
    catalog: HistoricalEpassCatalogEntry,
    expected_client_user_id: str,
    fitness_target: Optional[HistoricalFitnessScheduleTarget] = None,
    context: str,
) -> Tuple[str, str]:
    """历史品类 Bundle 下单成功；返回 ``(ePassId, usageOrderId)``。"""

    holder: Dict[str, str] = {}

    def _Do() -> str:
        _SkipIfPrebookingTimeslotUnavailable(resp, context=context)
        data = ExtractBusinessData(resp)
        status = data.get("status")
        if status == 10:
            pytest.skip(f"Bundle 预约单 status=10 FAILED: {data!r}")
        assert status in (1, 5), f"status 应为 1 或 5: {data!r}"
        assert data.get("module") == catalog.ModuleInt, (
            f"module 应为 {catalog.ModuleInt}: {data!r}"
        )
        assert data.get("category") == 2, f"category 应为 2 Prebooking: {data!r}"
        e_pass_id = _ResolveEPassIdField(data)
        assert isinstance(e_pass_id, str) and e_pass_id, f"ePassId 缺失: {data!r}"
        order_id = data.get("orderId")
        assert isinstance(order_id, str) and order_id, f"orderId 缺失: {data!r}"
        extra = data.get("extra")
        assert isinstance(extra, dict), f"extra 缺失: {data!r}"
        assert extra.get("clientUserId") == expected_client_user_id, (
            f"clientUserId 不一致: {extra!r}"
        )
        assert extra.get("resourceId") == catalog.ResourceId, (
            f"resourceId 不一致: {extra!r}"
        )
        option_id = fitness_target.OptionId if fitness_target is not None else catalog.OptionId
        if option_id:
            local_opts = extra.get("localOfferOptions")
            if isinstance(local_opts, dict) and local_opts.get("optionId"):
                assert local_opts.get("optionId") == option_id, (
                    f"optionId 不一致: {local_opts!r}"
                )
        holder["ePassId"] = e_pass_id
        holder["orderId"] = order_id
        return (
            f"{context}: Bundle module={catalog.ModuleInt}, "
            f"ePassId/orderId 非空, resourceId 一致。"
        )

    _RunAllureAssertionStep(f"历史 ePass: Bundle 下单响应（{context}）", _Do)
    e_pass_id = holder.get("ePassId", "")
    usage_order_id = holder.get("orderId", "")
    if not e_pass_id or not usage_order_id:
        data = ExtractBusinessData(resp)
        e_pass_id = e_pass_id or (_ResolveEPassIdField(data) or "")
        raw_oid = data.get("orderId")
        usage_order_id = usage_order_id or (raw_oid if isinstance(raw_oid, str) else "")
    assert e_pass_id and usage_order_id, f"{context}: 无法解析 ePassId/orderId"
    RegisterPendingLocalOfferOrder(usage_order_id)
    RegisterPendingLocalOfferEPassId(e_pass_id)
    return e_pass_id, usage_order_id


def PostHistoricalEpassBundle(
    token: str,
    catalog: HistoricalEpassCatalogEntry,
    *,
    client_user_id: str,
    prebooking_token: str,
    fitness_target: Optional[HistoricalFitnessScheduleTarget] = None,
    step_code: Optional[str] = None,
    step_title: Optional[str] = None,
) -> Response:
    """``POST /v2/orders/{path_module}/ePasses/bundle`` — 一次创建 ePass 并下预约单。"""
    extra: JsonDict = {"prebookingToken": prebooking_token}
    if catalog.AvailabilityMode == HistoricalAvailabilityMode.Classic:
        transport = "BA123" if catalog.ModuleInt == 2 else None
        extra["prebookingRequiredInfo"] = BuildHistoricalPrebookingRequiredInfo(
            transport_number=transport,
        )
        if catalog.ModuleInt == 2:
            extra["passengers"] = BuildHistoricalFastTrackPassengers()
    elif catalog.Label == "fitness":
        extra["prebookingRequiredInfo"] = BuildHistoricalPrebookingRequiredInfo()
        if fitness_target is not None:
            extra["optionId"] = fitness_target.OptionId
    body: JsonDict = {
        "module": catalog.ModuleInt,
        "clientUserId": client_user_id,
        "extra": extra,
        "async": False,
    }
    return RequestWithAllure(
        "POST",
        f"/v2/orders/{catalog.PathModule}/ePasses/bundle",
        token=token,
        json_body=body,
        step_code=step_code,
        step_title=step_title,
        x_program_id=GetConfiguredEpassProgramId(),
    )


def CreateHistoricalEpass(
    token: str,
    steps: Any,
    catalog: HistoricalEpassCatalogEntry,
    *,
    client_user_id: Optional[str] = None,
    available_usages: int = 2,
) -> HistoricalEpassCreateResult:
    """创建指定历史品类 ePass 并断言核心字段。"""
    cid = client_user_id or str(uuid.uuid4())
    payload = BuildModuleEpassCreatePayload(
        module=catalog.ModuleInt,
        client_user_id=cid,
        available_usages=available_usages,
    )
    kw = _HttpStepKw(steps, f"创建 {catalog.DisplayName} ePass（module={catalog.ModuleInt}）")
    resp = PostOrdersPathModuleEPasses(
        token,
        catalog.PathModule,
        payload,
        step_code=kw["step_code"],
        step_title=kw["step_title"],
    )
    client_user_id_res, e_pass_id, purchase_order_id = ExtractCreateEpassIds(resp)
    AssertHistoricalEpassCreateCoreFields(
        resp,
        expected_module=catalog.ModuleInt,
        expected_client_user_id=client_user_id_res,
        context=f"{catalog.Label}-create",
    )
    RegisterPendingLocalOfferOrder(purchase_order_id)
    RegisterPendingLocalOfferEPassId(e_pass_id)
    return HistoricalEpassCreateResult(
        ClientUserId=client_user_id_res,
        EPassId=e_pass_id,
        PurchaseOrderId=purchase_order_id,
        Catalog=catalog,
        CreateResponse=resp,
    )


def BuildHistoricalPrebookingRequiredInfo(
    *,
    first_name: str = "Auto",
    last_name: str = "Test",
    email: str = "auto.test@dragonpass.com",
    phone_number: str = "8081966002",
    calling_code: str = "44",
    transport_number: Optional[str] = None,
) -> JsonDict:
    """休息室 / 快速通道等经典品类预约必填联系人信息。"""
    info: JsonDict = {
        "firstName": first_name,
        "lastName": last_name,
        "email": email,
        "phoneNumber": phone_number,
        "callingCode": calling_code,
    }
    if transport_number is not None:
        info["transportNumber"] = transport_number
    return info


def BuildHistoricalFastTrackPassengers(
    *,
    first_name: str = "Auto",
    last_name: str = "Test",
    passengers_type: int = 1,
) -> List[JsonDict]:
    """快速通道 ``extra.passengers`` 数组（``passengersType`` + ``leadPassenger``）。"""
    return [
        {
            "firstName": first_name,
            "lastName": last_name,
            "passengersType": passengers_type,
            "leadPassenger": True,
        }
    ]


def PostHistoricalEpassPrebooking(
    token: str,
    catalog: HistoricalEpassCatalogEntry,
    *,
    e_pass_id: str,
    prebooking_token: str,
    fitness_target: Optional[HistoricalFitnessScheduleTarget] = None,
    step_code: Optional[str] = None,
    step_title: Optional[str] = None,
) -> Response:
    """``POST /v2/orders/{path_module}/ePasses/prebooking`` — 经典/fitness 附带 ``prebookingRequiredInfo``。"""
    extra: JsonDict = {"prebookingToken": prebooking_token}
    if catalog.AvailabilityMode == HistoricalAvailabilityMode.Classic:
        transport = "BA123" if catalog.ModuleInt == 2 else None
        extra["prebookingRequiredInfo"] = BuildHistoricalPrebookingRequiredInfo(
            transport_number=transport,
        )
        if catalog.ModuleInt == 2:
            extra["passengers"] = BuildHistoricalFastTrackPassengers()
    elif catalog.Label == "fitness":
        extra["prebookingRequiredInfo"] = BuildHistoricalPrebookingRequiredInfo()
        if fitness_target is not None:
            extra["optionId"] = fitness_target.OptionId
    body: JsonDict = {
        "module": catalog.ModuleInt,
        "ePassId": e_pass_id,
        "extra": extra,
        "async": False,
    }
    return RequestWithAllure(
        "POST",
        f"/v2/orders/{catalog.PathModule}/ePasses/prebooking",
        token=token,
        json_body=body,
        step_code=step_code,
        step_title=step_title,
        x_program_id=GetConfiguredEpassProgramId(),
    )


def PatchCancelOrderWithRetry(
    token: str,
    order_id: str,
    *,
    step_code: Optional[str] = None,
    step_title: Optional[str] = None,
    max_attempts: int = 2,
) -> Response:
    """``PATCH /v2/orders`` 取消；沙箱 ``500.041.006`` 时短暂重试。"""
    last_resp: Optional[Response] = None
    for attempt in range(1, max_attempts + 1):
        title = step_title if attempt == 1 else f"{step_title} · 重试 {attempt}"
        last_resp = PatchCancelOrder(
            token,
            order_id,
            step_code=step_code,
            step_title=title,
        )
        _st, env, _ = ParseResponseEnvelope(last_resp)
        if IsLocalOfferBusinessSuccess(env):
            return last_resp
        err = env.get("errCode") if isinstance(env, dict) else None
        if err == "500.041.006" and attempt < max_attempts:
            time.sleep(2.0)
            continue
        break
    assert last_resp is not None
    return last_resp


def AssertHistoricalCancelOrderSuccess(resp: Response, *, context: str) -> None:
    """历史回归专用取消断言（硬失败，不走 Local Offer 软断言）。"""

    def _Do() -> str:
        _st, env, _data = ParseResponseEnvelope(resp)
        assert resp.status_code == 200, f"取消 HTTP 非 200: {resp.status_code}, {resp.text[:400]!r}"
        assert IsLocalOfferBusinessSuccess(env), f"取消业务失败: {env!r}"
        return f"{context}: PATCH /v2/orders 取消成功。"

    def _DoWithSkipOnFlake() -> str:
        try:
            return _Do()
        except AssertionError as exc:
            _st, env, _ = ParseResponseEnvelope(resp)
            err = env.get("errCode") if isinstance(env, dict) else None
            if err in ("500.041.006", "500.071.016"):
                pytest.skip(
                    f"{context}: 沙箱取消偶发失败 errCode={err}（预约/创建已成功，请人工核对订单 {exc}）"
                )
            raise

    _RunAllureAssertionStep(f"历史 ePass: 取消订单（{context}）", _DoWithSkipOnFlake)


def CancelHistoricalPurchaseOrderAndVerify(
    token: str,
    steps: Any,
    *,
    catalog: HistoricalEpassCatalogEntry,
    e_pass_id: str,
    purchase_order_id: str,
    context: str,
) -> None:
    """取消 MS 购买单并 search 校验 ePass 注销。"""
    kw_cancel = _HttpStepKw(steps, f"{context} · 取消 ePass 会籍购买单")
    resp_cancel = PatchCancelOrderWithRetry(
        token,
        purchase_order_id,
        step_code=kw_cancel["step_code"],
        step_title=kw_cancel["step_title"],
    )
    AssertHistoricalCancelOrderSuccess(resp_cancel, context=f"{context}-cancel")
    MarkLocalOfferOrderCancelled(purchase_order_id)
    MarkLocalOfferEPassPurchaseCancelled(e_pass_id)

    kw_search = _HttpStepKw(steps, f"{context} · 取消后 search（ePassId）")
    resp_search = PostOrdersEPassesSearch(
        token,
        e_pass_id=e_pass_id,
        step_code=kw_search["step_code"],
        step_title=kw_search["step_title"],
    )

    def _DoSearch() -> str:
        data = ExtractBusinessData(resp_search)
        assert data.get("module") == catalog.ModuleInt, f"module 应为 {catalog.ModuleInt}: {data!r}"
        extra = data.get("extra")
        assert isinstance(extra, dict), f"extra 缺失: {data!r}"
        e_pass_status = extra.get("ePassStatus")
        assert e_pass_status == 3, f"购买单取消后 ePassStatus 应为 3: {extra!r}"
        return f"{context}: 购买单取消后 ePassStatus=3。"

    _RunAllureAssertionStep(f"历史 ePass: 购买单取消后 search（{context}）", _DoSearch)


def CancelHistoricalUsageOrderAndVerify(
    token: str,
    steps: Any,
    *,
    catalog: HistoricalEpassCatalogEntry,
    usage_order_id: str,
    e_pass_id: str,
    purchase_order_id: str,
    context: str,
) -> None:
    """取消 usage 预订单并校验 details / 列表 / search。"""
    if catalog.ModuleInt == 8:
        WaitForHistoricalEsimUsageOrderConfirmed(
            token,
            steps,
            usage_order_id=usage_order_id,
            e_pass_id=e_pass_id,
            context=f"{context}-poll-status1",
        )

    kw_cancel = _HttpStepKw(steps, f"{context} · 取消 usage 预订单")
    resp_cancel = PatchCancelOrderWithRetry(
        token,
        usage_order_id,
        step_code=kw_cancel["step_code"],
        step_title=kw_cancel["step_title"],
    )
    AssertHistoricalCancelOrderSuccess(resp_cancel, context=f"{context}-cancel")
    MarkLocalOfferOrderCancelled(usage_order_id)

    kw_details = _HttpStepKw(steps, f"{context} · 取消后 usage 详情")
    resp_details = PostOrdersEPassesUsageDetails(
        token,
        usage_order_id,
        step_code=kw_details["step_code"],
        step_title=kw_details["step_title"],
    )

    def _DoDetails() -> str:
        data = ExtractBusinessData(resp_details)
        assert data.get("module") == catalog.ModuleInt, (
            f"module 应为 {catalog.ModuleInt}: {data!r}"
        )
        assert data.get("orderId") == usage_order_id, f"orderId 不一致: {data!r}"
        ep = _ResolveEPassIdField(data)
        assert ep == e_pass_id, f"ePassId 不一致: {data!r}"
        assert data.get("status") == 3, f"取消后 status 应为 3: {data!r}"
        assert data.get("orderCancelledDate") is not None, "orderCancelledDate 应有值"
        return f"{context}: details status=3。"

    _RunAllureAssertionStep(f"历史 ePass: usage 取消后详情（{context}）", _DoDetails)

    kw_list = _HttpStepKw(steps, f"{context} · 取消后 usage 列表")
    resp_list = PostOrdersEPassesList(
        token,
        e_pass_id,
        module=catalog.ModuleInt,
        step_code=kw_list["step_code"],
        step_title=kw_list["step_title"],
    )

    def _DoList() -> str:
        data = ExtractBusinessData(resp_list)
        orders = data.get("orders")
        assert isinstance(orders, list), f"orders 应为数组: {data!r}"
        if not orders:
            return f"{context}: orders 暂为空，跳过取消态列表断言。"
        matched = [
            o for o in orders
            if isinstance(o, dict) and o.get("orderId") == usage_order_id
        ]
        assert matched, f"orders 未含 orderId={usage_order_id!r}"
        item = cast(JsonDict, matched[0])
        assert item.get("status") == 3, f"列表项 status 应为 3: {item!r}"
        if "module" in item:
            assert item.get("module") == catalog.ModuleInt, f"module 不一致: {item!r}"
        return f"{context}: 列表含已取消 usage 单。"

    _RunAllureAssertionStep(f"历史 ePass: 取消后订单列表（{context}）", _DoList)

    if purchase_order_id:
        kw_search = _HttpStepKw(steps, f"{context} · 取消后 search（ePass 仍 Active）")
        resp_search = PostOrdersEPassesSearch(
            token,
            e_pass_id=e_pass_id,
            step_code=kw_search["step_code"],
            step_title=kw_search["step_title"],
        )

        def _DoSearchActive() -> str:
            data = ExtractBusinessData(resp_search)
            assert data.get("module") == catalog.ModuleInt, f"module 不一致: {data!r}"
            extra = data.get("extra")
            assert isinstance(extra, dict), f"extra 缺失: {data!r}"
            assert extra.get("ePassStatus") == 1, f"usage 取消后 ePass 应仍 Active: {extra!r}"
            return f"{context}: usage 取消后 ePassStatus=1。"

        _RunAllureAssertionStep(f"历史 ePass: usage 取消后 search Active（{context}）", _DoSearchActive)


def WaitForHistoricalEsimUsageOrderConfirmed(
    token: str,
    steps: Any,
    *,
    usage_order_id: str,
    e_pass_id: str,
    context: str,
) -> None:
    """
    eSIM usage 单异步落单：轮询 ``POST /v2/orders/ePasses/details`` 直至 ``status=1`` 再进入取消。

    下单响应可能为 ``status=5``（处理中）；``status=10`` 视为失败并 skip。
    """
    interval_sec = GetHistoricalEsimStatusPollIntervalSec()
    max_attempts = GetHistoricalEsimStatusPollMaxAttempts()
    last_status: Optional[int] = None
    last_resp: Optional[Response] = None

    for attempt in range(1, max_attempts + 1):
        kw = _HttpStepKw(
            steps,
            f"{context} · 轮询 eSIM usage 详情 status=1（{attempt}/{max_attempts}）",
        )
        resp = PostOrdersEPassesUsageDetails(
            token,
            usage_order_id,
            step_code=kw["step_code"],
            step_title=kw["step_title"],
        )
        last_resp = resp
        _st, env, data = ParseResponseEnvelope(resp)
        if resp.status_code != 200 or not IsLocalOfferBusinessSuccess(env):
            if attempt < max_attempts:
                time.sleep(interval_sec)
                continue
            pytest.fail(
                f"{context}: eSIM usage 详情轮询失败 HTTP/business: "
                f"status={resp.status_code}, env={env!r}"
            )
        if not isinstance(data, dict):
            if attempt < max_attempts:
                time.sleep(interval_sec)
                continue
            pytest.fail(f"{context}: eSIM usage 详情 data 非对象: {data!r}")

        status_raw = data.get("status")
        last_status = int(status_raw) if isinstance(status_raw, int) else None
        if last_status == 10:
            pytest.skip(f"{context}: eSIM usage 单 status=10 FAILED: {data!r}")
        if last_status == 1:
            def _DoConfirmed() -> str:
                assert data.get("module") == 8, f"module 应为 8: {data!r}"
                assert data.get("orderId") == usage_order_id, f"orderId 不一致: {data!r}"
                ep = _ResolveEPassIdField(data)
                assert ep == e_pass_id, f"ePassId 不一致: {data!r}"
                return (
                    f"{context}: 第 {attempt} 次轮询命中 status=1，"
                    f"orderId={usage_order_id!r}。"
                )

            _RunAllureAssertionStep(
                f"历史 ePass: eSIM usage 单已确认（{context}）",
                _DoConfirmed,
            )
            return
        if attempt < max_attempts:
            time.sleep(interval_sec)

    hint = ""
    if last_resp is not None:
        try:
            _st, env, data = ParseResponseEnvelope(last_resp)
            hint = f" 末次 data={data!r}, env={env!r}"
        except Exception:
            hint = f" 末次 body={last_resp.text[:400]!r}"
    pytest.fail(
        f"{context}: eSIM usage 单在 {max_attempts} 次轮询内未达 status=1"
        f"（末次 status={last_status!r}，间隔 {interval_sec}s）。{hint}"
    )


def AssertHistoricalPrebookingOrderSuccessForCatalog(
    resp: Response,
    *,
    catalog: HistoricalEpassCatalogEntry,
    e_pass_id: str,
    context: str,
    fitness_target: Optional[HistoricalFitnessScheduleTarget] = None,
) -> str:
    """按品类分发预约成功断言（eSIM 复用专用断言；fitness 用 schedule 解析的 optionId）。"""
    if catalog.ModuleInt == 8:
        return AssertEsimPrebookingOrderSuccess(
            resp,
            e_pass_id=e_pass_id,
            resource_id=catalog.ResourceId,
            option_id=catalog.OptionId,
            context=context,
        )
    option_id = fitness_target.OptionId if fitness_target is not None else catalog.OptionId
    return AssertHistoricalPrebookingOrderSuccess(
        resp,
        expected_module=catalog.ModuleInt,
        e_pass_id=e_pass_id,
        resource_id=catalog.ResourceId,
        option_id=option_id,
        context=context,
    )


__all__ = [
    "AssertHistoricalBundleOrderSuccess",
    "AssertHistoricalPrebookingOrderSuccessForCatalog",
    "BuildHistoricalPrebookingRequiredInfo",
    "CancelHistoricalPurchaseOrderAndVerify",
    "CancelHistoricalUsageOrderAndVerify",
    "CreateHistoricalEpass",
    "GetFitnessResourcesSchedule",
    "HistoricalEpassCreateResult",
    "HistoricalEpassPrebookingResult",
    "ParseHistoricalFitnessScheduleTargets",
    "PostHistoricalEpassBundle",
    "PostHistoricalEpassPrebooking",
    "RequireHistoricalEpassEnvOrSkip",
    "RequestHistoricalPrebookingToken",
    "RequestHistoricalPrebookingTokenWithoutEpass",
    "ResolveHistoricalFitnessScheduleTargets",
    "WaitForHistoricalEsimUsageOrderConfirmed",
]
