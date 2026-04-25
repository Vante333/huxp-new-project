"""
PAPI-2515 crossModuleEntitlements 返回结构优化 — pytest 自动化。

主场景 HTTP 顺序与软断言语义见 ``papi2515_helpers.RunP2515MainE2EScenario`` 及该模块 docstring **主链路**表；
本文件 E2E 用例仅调用该编排入口以保持单一真相源。

E2E 使用 ``P2515E2ESoftAssert``（在编排函数内）：中间业务断言失败时**仍继续**后续 HTTP，最后一次性 ``pytest.fail`` 汇总。
全文件 PAPI-2515 相关断言均通过 ``after_register_success``、``after_entitlements``、``after_response`` 挂在对应 HTTP Allure 步骤内，与请求同屏。

环境变量见套件 ``README.md`` 与 ``papi2515_helpers`` 模块 docstring。
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple, cast

import allure
import pytest
from requests import Response
from test_data_loader import LoadP2515DatasetCsvRow

from clients import GetAccessToken, PostEntitlementsSearch, PostEntitlementsUpdate
from framework.assertions import AssertHttpAndBusinessOk
from framework.http import ParseResponseEnvelope
from framework.reporting import AllureHttpScenarioSteps
from scenarios.papi2515_scenarios import RunP2515MainE2EScenario
from services.papi2515_service import (
    AssertCrossModuleAtLeastTwoDistinctGroupsOrSkip,
    AssertCrossModuleContract,
    AssertCrossModuleMetricsEqualBetweenDataInners,
    AssertCrossModuleOtherGroupsNormalizedUnchanged,
    AssertCrossModuleSearchVsMembershipsAlign,
    AssertCrossModuleSingleRowPerApplicableModules,
    AssertCrossModuleSummaryGuestAggregateKeys,
    AssertCrossModuleSummaryMatchesExpected,
    AssertFictiveZeroPurchasedPoolInSearch,
    AssertModuleExclusiveMetricDelta,
    AssertNormalizedCrossModuleEqual,
    ApplyPlannedUpdateToExpectedGroupMetrics,
    BuildP2515ModuleExclusiveUpdateBody,
    BuildP2515PoolUpdatePlan,
    BuildP2515RegisterPayload,
    CrossModuleGroupMetricsByKey,
    DetailsOnlyPurchasedEntitlements,
    EntitlementsPoolUpdateSuccessOrSkipIfProgramDenied,
    EntitlementsSearchSuccess,
    ExtractEntitlements,
    GetCrossModuleEntitlements,
    IntDetail,
    MaybeAttach2515SearchDetails,
    MembershipsSearchSuccessEntitlements,
    RequireNonEmptyCrossModule,
    RequireP2515ProgramIdForRegisterOrSkip,
    RunP2515CrossModuleAndModuleExclusiveFromInner,
)
from services.papi2548_service import RegisterMembershipSuccessDetail


def _StepKw(steps: AllureHttpScenarioSteps, brief: str) -> Dict[str, str]:
    code, title = steps.Next(brief)
    return {"step_code": code, "step_title": title}


@pytest.fixture
def Token() -> str:
    token = GetAccessToken()
    assert isinstance(token, str) and len(token) >= 8, "accessToken 异常"
    return token


@allure.feature("PAPI-2515")
@allure.story("v2_entitlements_search")
class TestP2515SearchCrossModuleContract:
    @allure.title("仅 Search：crossModule 结构契约（需探测会籍 ID）")
    @pytest.mark.p2515_probe_membership
    @pytest.mark.needs_cross_module_data
    def test_search_cross_module_contract_with_probe_membership(
        self,
        Token: str,
        ScenarioSteps: AllureHttpScenarioSteps,
    ) -> None:
        mid = os.environ.get("DP_P2515_PROBE_MEMBERSHIP_ID", "").strip()
        if not mid:
            mid = LoadP2515DatasetCsvRow().probe_membership_id.strip()
        if not mid:
            pytest.skip("未设置 DP_P2515_PROBE_MEMBERSHIP_ID，跳过只读探测用例")

        def _AfterProbeSearch(ent: Dict[str, Any]) -> None:
            MaybeAttach2515SearchDetails(ent, label="probe")
            cross = GetCrossModuleEntitlements(ent)
            if not cross:
                pytest.skip("该会籍无 crossModuleEntitlements，换探测 ID 或走注册造数主场景")
            AssertCrossModuleContract(cross, context="PAPI-2515-probe")

        EntitlementsSearchSuccess(
            Token,
            mid,
            after_entitlements=_AfterProbeSearch,
            **_StepKw(ScenarioSteps, "entitlements/search（探测会籍）"),
        )


@allure.feature("PAPI-2515")
@allure.story("cross_module_e2e")
class TestP2515CrossModuleE2E:
    @allure.title("附件链：module 更新隔离 cross + 单池轮询更新 + summary 恒等式（软断言跑完全链路）")
    @pytest.mark.needs_cross_module_write
    def test_e2e_register_search_module_update_pool_updates(
        self,
        Token: str,
        ScenarioSteps: AllureHttpScenarioSteps,
    ) -> None:
        RunP2515MainE2EScenario(Token, ScenarioSteps)


@allure.feature("PAPI-2515")
@allure.story("doc_gap_coverage")
class TestP2515DocGapCoverage:
    """
    补齐 ``testcases/.../PAPI-2515-...测试用例.md`` 中与四接口相关的缺口项（独立用例，不替代 E2E 主链）。
    """

    @allure.title("tc-P1-MBR + tc-P2-MBR-001：memberships/search 上 cross 契约，并与 entitlements/search 对齐")
    @pytest.mark.needs_cross_module_data
    def test_memberships_search_cross_aligns_with_entitlements_search(
        self,
        Token: str,
        ScenarioSteps: AllureHttpScenarioSteps,
    ) -> None:
        RequireP2515ProgramIdForRegisterOrSkip()
        reg_payload = BuildP2515RegisterPayload()
        membership_id, _exts, _reg_body = RegisterMembershipSuccessDetail(
            Token,
            reg_payload,
            **_StepKw(ScenarioSteps, "注册会籍（对齐 doc gap）"),
        )

        def _AfterGapEntitlementsSearch(ent: Dict[str, Any]) -> None:
            cross = GetCrossModuleEntitlements(ent)
            if not cross:
                pytest.skip(
                    "entitlements/search 无 crossModuleEntitlements，无法继续 doc gap 用例；请换 program 模板"
                )
            AssertCrossModuleContract(
                cross,
                context="PAPI-2515-gap-entitlements-search",
            )

        ent_search = EntitlementsSearchSuccess(
            Token,
            membership_id,
            after_entitlements=_AfterGapEntitlementsSearch,
            **_StepKw(ScenarioSteps, "entitlements/search"),
        )

        def _AfterGapMembershipsSearch(ent_m: Dict[str, Any]) -> None:
            cross_m = GetCrossModuleEntitlements(ent_m)
            if not cross_m:
                pytest.skip(
                    "POST /v2/memberships/search 返回的会籍记录未携带 entitlements.crossModuleEntitlements，"
                    "无法做独立 memberships 侧契约；请确认网关是否在会籍查询中下发权益块"
                )
            AssertCrossModuleContract(cross_m, context="PAPI-2515-gap-memberships-search")
            AssertCrossModuleSearchVsMembershipsAlign(
                ent_search,
                ent_m,
                context="PAPI-2515-tc-P2-MBR-001",
            )

        MembershipsSearchSuccessEntitlements(
            Token,
            membership_id,
            after_entitlements=_AfterGapMembershipsSearch,
            **_StepKw(ScenarioSteps, "memberships/search（会籍查询）"),
        )

    @allure.title(
        "tc-P1-GEN-002：summary 携伴字段；tc-P1-GEN-005：applicableModules 唯一；tc-P2-GEN-005：虚构买点池 purchased=0"
    )
    @pytest.mark.needs_cross_module_data
    def test_search_tc_p1_gen_005_and_fictive_purchase_zero(
        self,
        Token: str,
        ScenarioSteps: AllureHttpScenarioSteps,
    ) -> None:
        RequireP2515ProgramIdForRegisterOrSkip()
        membership_id, _e, _b = RegisterMembershipSuccessDetail(
            Token,
            BuildP2515RegisterPayload(),
            **_StepKw(ScenarioSteps, "注册会籍"),
        )

        def _AfterTcP1005Combo(ent: Dict[str, Any]) -> None:
            cross = RequireNonEmptyCrossModule(ent)
            AssertCrossModuleSummaryGuestAggregateKeys(cross, context="PAPI-2515-tc-P1-GEN-002")
            AssertCrossModuleSingleRowPerApplicableModules(cross, context="PAPI-2515-tc-P1-GEN-005")
            AssertFictiveZeroPurchasedPoolInSearch(cross, context="PAPI-2515-tc-P2-GEN-005")

        EntitlementsSearchSuccess(
            Token,
            membership_id,
            after_entitlements=_AfterTcP1005Combo,
            **_StepKw(ScenarioSteps, "entitlements/search"),
        )

    @allure.title("tc-P2-GEN-004：至少两组不同 applicableModules（有则继续，无则 skip）")
    @pytest.mark.needs_cross_module_data
    def test_search_tc_p2_gen_004_at_least_two_cross_groups(
        self,
        Token: str,
        ScenarioSteps: AllureHttpScenarioSteps,
    ) -> None:
        RequireP2515ProgramIdForRegisterOrSkip()
        membership_id, _e, _b = RegisterMembershipSuccessDetail(
            Token,
            BuildP2515RegisterPayload(),
            **_StepKw(ScenarioSteps, "注册会籍"),
        )

        def _AfterTcP204(ent: Dict[str, Any]) -> None:
            cross = RequireNonEmptyCrossModule(ent)
            keys = AssertCrossModuleAtLeastTwoDistinctGroupsOrSkip(cross)
            AssertCrossModuleContract(cross, context="PAPI-2515-tc-P2-GEN-004")
            allure.attach(
                "\n".join(f"组键: {list(k)!r}" for k in keys),
                name="p2515_multi_cross_group_keys",
                attachment_type=allure.attachment_type.TEXT,
            )

        EntitlementsSearchSuccess(
            Token,
            membership_id,
            after_entitlements=_AfterTcP204,
            **_StepKw(ScenarioSteps, "entitlements/search"),
        )

    @allure.title("tc-P2-GEN-001（Update）：update 响应与紧跟的 search 在 cross summary 指标上一致")
    @pytest.mark.needs_cross_module_write
    def test_update_tc_p2_gen_001_metrics_match_followup_search(
        self,
        Token: str,
        ScenarioSteps: AllureHttpScenarioSteps,
    ) -> None:
        RequireP2515ProgramIdForRegisterOrSkip()
        membership_id, _e, _b = RegisterMembershipSuccessDetail(
            Token,
            BuildP2515RegisterPayload(),
            **_StepKw(ScenarioSteps, "注册会籍"),
        )
        EntitlementsSearchSuccess(
            Token,
            membership_id,
            **_StepKw(ScenarioSteps, "entitlements/search（基线）"),
        )
        mod_body = BuildP2515ModuleExclusiveUpdateBody(membership_id)
        holder: Dict[str, object] = {}

        def _AfterUpdateTcP2001(resp: Response) -> None:
            _st, env, inner = ParseResponseEnvelope(resp)
            AssertHttpAndBusinessOk(resp, env, context="POST /v2/entitlements/update")
            holder["inner"] = inner
            if not CrossModuleGroupMetricsByKey(
                GetCrossModuleEntitlements(ExtractEntitlements(inner)),
            ):
                pytest.skip(
                    "update 成功响应未携带可解析的 crossModuleEntitlements，无法做 summary 指标对拍（tc-P2-GEN-001）；"
                    "若产品约定以 search 为准可仅保留 search 断言"
                )

        def _AfterFollowSearch(resp: Response) -> None:
            _st, env, inner = ParseResponseEnvelope(resp)
            AssertHttpAndBusinessOk(resp, env, context="POST /v2/entitlements/search")
            inner_u = holder["inner"]
            AssertCrossModuleMetricsEqualBetweenDataInners(
                inner_u,
                inner,
                context="PAPI-2515-tc-P2-GEN-001-update-vs-search",
            )

        PostEntitlementsUpdate(
            Token,
            mod_body,
            after_response=_AfterUpdateTcP2001,
            **_StepKw(ScenarioSteps, "entitlements/update"),
        )

        PostEntitlementsSearch(
            Token,
            membership_id,
            after_response=_AfterFollowSearch,
            **_StepKw(ScenarioSteps, "entitlements/search（紧跟 update）"),
        )

    @allure.title("tc-P2-GEN-002：按池将买点归零后仍存在买点池且 purchasedEntitlements=0")
    @pytest.mark.needs_cross_module_write
    def test_update_tc_p2_gen_002_purchase_pool_zero_after_pool_update(
        self,
        Token: str,
        ScenarioSteps: AllureHttpScenarioSteps,
    ) -> None:
        RequireP2515ProgramIdForRegisterOrSkip()
        membership_id, _e, _b = RegisterMembershipSuccessDetail(
            Token,
            BuildP2515RegisterPayload(),
            **_StepKw(ScenarioSteps, "注册会籍"),
        )
        pick: Dict[str, Optional[str]] = {"pool_id": None}

        def _AfterPickPurchasePool(ent: Dict[str, Any]) -> None:
            cross = RequireNonEmptyCrossModule(ent)
            target_pool_id: Optional[str] = None
            for g in cross:
                if not isinstance(g, dict):
                    continue
                pools = g.get("pools")
                if not isinstance(pools, list):
                    continue
                for p in pools:
                    if not isinstance(p, dict):
                        continue
                    det = p.get("details")
                    if not isinstance(det, dict):
                        continue
                    d = det
                    if not DetailsOnlyPurchasedEntitlements(d):
                        continue
                    v = IntDetail(d, "purchasedEntitlements")
                    if v is not None and v > 0:
                        pid = p.get("entitlementPoolId")
                        if pid:
                            target_pool_id = str(pid)
                            break
                if target_pool_id:
                    break
            if not target_pool_id:
                pytest.skip("未找到 purchasedEntitlements>0 的买点池，无法执行归零更新")
            pick["pool_id"] = target_pool_id

        EntitlementsSearchSuccess(
            Token,
            membership_id,
            after_entitlements=_AfterPickPurchasePool,
            **_StepKw(ScenarioSteps, "entitlements/search"),
        )
        target_pool_id = pick["pool_id"]
        assert target_pool_id is not None
        EntitlementsPoolUpdateSuccessOrSkipIfProgramDenied(
            Token,
            target_pool_id,
            {"membershipId": membership_id, "purchasedQuantity": 0},
            **_StepKw(ScenarioSteps, "entitlements/{poolId}/update 买点归零"),
        )

        def _AfterVerifyPurchaseZero(ent: Dict[str, Any]) -> None:
            cross2 = GetCrossModuleEntitlements(ent)
            found_zero = False
            for p in _IterCrossPools(cross2):
                det = p.get("details")
                if not isinstance(det, dict):
                    continue
                if not DetailsOnlyPurchasedEntitlements(cast(Mapping[str, Any], det)):
                    continue
                if IntDetail(cast(Mapping[str, Any], det), "purchasedEntitlements") == 0:
                    found_zero = True
                    break
            assert found_zero, "归零后 search 应仍可见买点池且 details.purchasedEntitlements==0"

        EntitlementsSearchSuccess(
            Token,
            membership_id,
            after_entitlements=_AfterVerifyPurchaseZero,
            **_StepKw(ScenarioSteps, "entitlements/search（归零后）"),
        )


@allure.feature("PAPI-2515")
@allure.story("doc_gap_coverage")
class TestP2515PoolUpdateIsolation:
    """tc-P3-GEN-001：单池更新不波及其他 applicableModules 组。"""

    @allure.title("tc-P3-GEN-001：仅更新一个池时其它 cross 组归一化快照不变")
    @pytest.mark.needs_cross_module_write
    def test_pool_update_other_applicable_modules_unchanged(
        self,
        Token: str,
        ScenarioSteps: AllureHttpScenarioSteps,
    ) -> None:
        RequireP2515ProgramIdForRegisterOrSkip()
        membership_id, _e, _b = RegisterMembershipSuccessDetail(
            Token,
            BuildP2515RegisterPayload(),
            **_StepKw(ScenarioSteps, "注册会籍"),
        )
        isolation_state: Dict[str, Any] = {}

        def _AfterSearchBeforePoolUpdate(ent: Dict[str, Any]) -> None:
            cross_before = RequireNonEmptyCrossModule(ent)
            AssertCrossModuleAtLeastTwoDistinctGroupsOrSkip(cross_before)
            isolation_state["cross_before"] = cross_before

        EntitlementsSearchSuccess(
            Token,
            membership_id,
            after_entitlements=_AfterSearchBeforePoolUpdate,
            **_StepKw(ScenarioSteps, "entitlements/search（更新前）"),
        )
        cross_before = isolation_state["cross_before"]
        plan = BuildP2515PoolUpdatePlan(membership_id, cross_before)
        if not plan:
            pytest.skip("BuildP2515PoolUpdatePlan 无项，无法做单池更新隔离断言")
        item = plan[0]
        EntitlementsPoolUpdateSuccessOrSkipIfProgramDenied(
            Token,
            item.entitlement_pool_id,
            item.body,
            **_StepKw(
                ScenarioSteps,
                f"entitlements/{{poolId}}/update（单步 isolation pool={item.entitlement_pool_id}）",
            ),
        )

        def _AfterSearchAfterPoolUpdate(ent: Dict[str, Any]) -> None:
            AssertCrossModuleOtherGroupsNormalizedUnchanged(
                isolation_state["cross_before"],
                GetCrossModuleEntitlements(ent),
                touched_group_key=item.applicable_modules_key,
                context="PAPI-2515-tc-P3-GEN-001",
            )

        EntitlementsSearchSuccess(
            Token,
            membership_id,
            after_entitlements=_AfterSearchAfterPoolUpdate,
            **_StepKw(ScenarioSteps, "entitlements/search（单池更新后）"),
        )


def _IterCrossPools(cross_groups: Sequence[Mapping[str, Any]]) -> List[Mapping[str, Any]]:
    out: List[Mapping[str, Any]] = []
    for g in cross_groups:
        if not isinstance(g, dict):
            continue
        pools = g.get("pools")
        if not isinstance(pools, list):
            continue
        for p in pools:
            if isinstance(p, dict):
                out.append(cast(Mapping[str, Any], p))
    return out
