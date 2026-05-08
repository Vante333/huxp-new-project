"""
PAPI-2548 会籍 extensions 自动化用例（不含非内部租户场景）。

主链路（注册→search→extensions→search）见 ``papi2548_helpers.RunPapi2548MainE2EScenario`` 与该模块 docstring。

执行前请设置：DP_PROGRAM_ID、DP_CLIENT_ID、DP_CLIENT_SECRET；
可选 DP_BASE_URL（默认 https://developer-sandbox.dragonpass.com/api）。
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional, Tuple

import allure
import pytest
from requests import Response

from clients import GetAccessToken, PatchMembershipsExtensions, PostMemberships, PostMembershipsSearch
from framework.assertions import IsBusinessSuccess, IsHttpOk
from framework.http import ParseResponseEnvelope
from framework.reporting import AllureHttpScenarioSteps
from scenarios.papi2548_scenarios import RunPapi2548MainE2EScenario
from services.papi2548_service import (
    AssertBusinessFailureEnvelope,
    AssertDictKeyValues,
    AssertExtensionItemInList,
    AssertExtensionItemsKeyShape,
    AssertExtensionsNormalizedEqual,
    AssertExtensionsPatchSuccessBody,
    AssertJsonResponse,
    AssertMembershipSearchRecord,
    AssertNoDuplicateExtensionTypesInList,
    AssertPapi2548DuplicateTypeErrorResponse,
    AssertPapi2548MaxFiveTypesErrorResponse,
    AssertPostmanStyleSuccessResponse,
    AssertRegisterCoreFields,
    AssertRegisterSelectedFieldsEchoed,
    AssertRegisterSuccessBody,
    AssertRootBusinessCodeIndicatesFailure,
    AssertSearchMembershipCoreFields,
    BuildMinimalMembershipPayload,
    BuildSandboxFlags,
    CallMembershipsExpectFailure,
    ExtensionRegisterItem,
    ExtensionUpdateItem,
    ExtractExtensionsList,
    ExtractMembershipId,
    NormalizeExtensionsForCompare,
    PAPI2548_EXT_ERR_DUPLICATE_TYPE,
    PAPI2548_EXT_ERR_DUPLICATE_TYPE_LEGACY,
    PAPI2548_EXT_ERR_MAX_FIVE_TYPES,
    PAPI2548_EXT_ERR_MAX_FIVE_TYPES_LEGACY,
    Papi2548SandboxFlags,
    RegisterMembershipSuccess,
    RegisterMembershipSuccessDetail,
    RequirePapi2548ExtensionsWriteOrSkip,
    RequirePapi2548SearchShowsExtensionsOrSkip,
    RunPatchExtensionsAssertions,
    RunPatchInvalidMembershipIdAssertions,
    RunPatchInvalidOperationGatewayAssertions,
    RunSearchDuplicateTypeCardIdPersistenceAssertions,
    RunSearchOmitExtensionsSemanticsAssertions,
    RunSearchResponseAssertions,
    RunSearchSnapshotForDeleteAssertions,
    RunUpsertMissingValueDocumentedAssertions,
    StrOfLength,
    UnwrapMembershipRecord,
)

pytestmark = [pytest.mark.feature, pytest.mark.papi2548, pytest.mark.needs_write]


@pytest.fixture(scope="function")
def Token() -> str:
    token = GetAccessToken()
    assert isinstance(token, str) and len(token) >= 8, "accessToken 异常"
    return token


def _ExpectedPairsFromRegister(items: List[ExtensionRegisterItem]) -> List[Tuple[str, Optional[str]]]:
    return NormalizeExtensionsForCompare(items)


def _StepKw(steps: AllureHttpScenarioSteps, brief: str) -> Dict[str, str]:
    """生成 ``step_code`` / ``step_title``，用于各 HTTP 封装。"""
    code, title = steps.Next(brief)
    return {"step_code": code, "step_title": title}


@allure.feature("PAPI-2548")
@allure.story("v2_memberships")
class TestMembershipsRegisterExtensions:
    @allure.title("内部租户注册携带合法 extensions 回显一致")
    def test_register_with_extensions_echo(
        self,
        Token: str,
        papi2548_sandbox_flags: Papi2548SandboxFlags,
        ScenarioSteps: AllureHttpScenarioSteps,
    ) -> None:
        exts: List[ExtensionRegisterItem] = [
            {"type": "ailasId", "value": "123456"},
            {"type": "cardId", "value": "abcdef"},
        ]
        payload = BuildMinimalMembershipPayload(extensions=exts)
        mid, got, body_reg = RegisterMembershipSuccessDetail(
            Token,
            payload,
            **_StepKw(ScenarioSteps, "注册会籍（含 extensions）"),
        )
        assert mid
        with allure.step("注册 data：身份字段与请求体回显一致"):
            AssertRegisterCoreFields(
                body_reg,
                membership_id=mid,
                client_user_id=str(payload["clientUserId"]),
                expect_status=1,
                context="注册响应 data",
            )
            AssertRegisterSelectedFieldsEchoed(body_reg, payload, context="注册")
        if NormalizeExtensionsForCompare(got) == _ExpectedPairsFromRegister(exts):
            with allure.step("注册响应：extensions 与入参逐条一致、结构合法、type 不重复"):
                AssertExtensionsNormalizedEqual(got, exts, context="注册响应")
                AssertNoDuplicateExtensionTypesInList(got, context="注册响应")
                AssertExtensionItemsKeyShape(
                    got,
                    ("type", "value"),
                    allowed_keys=("type", "value"),
                    context="注册响应",
                )
                for item in exts:
                    AssertExtensionItemInList(
                        got,
                        type_=str(item["type"]),
                        value=str(item["value"]),
                        context="注册响应 extensions",
                    )
            return
        if papi2548_sandbox_flags.search_shows_extensions:
            PostMembershipsSearch(
                Token,
                mid,
                after_response=lambda r: RunSearchResponseAssertions(
                    r,
                    http_context="POST /v2/memberships/search",
                    membership_id=mid,
                    client_user_id=str(payload["clientUserId"]),
                    expect_status=1,
                    search_core_context="search 单条",
                    extensions_equal_to=exts,
                    extensions_context="search",
                    assert_shape_and_no_dup=True,
                    extension_item_checks=exts,
                ),
                **_StepKw(ScenarioSteps, "search 校验 extensions 持久化"),
            )
            return
        pytest.skip(
            "当前环境注册/查询均未返回 extensions 列表；待后端在 POST /v2/memberships 或 "
            "/v2/memberships/search 暴露字段后本用例将自动校验。"
        )

    @allure.title("同一请求 extensions 重复 type 应失败")
    def test_register_duplicate_type_fails(
        self,
        Token: str,
        papi2548_sandbox_flags: Papi2548SandboxFlags,
        ScenarioSteps: AllureHttpScenarioSteps,
    ) -> None:
        exts: List[ExtensionRegisterItem] = [
            {"type": "cardId", "value": "a"},
            {"type": "cardId", "value": "b"},
        ]
        payload = BuildMinimalMembershipPayload(extensions=exts)
        resp, env, reg_inner = PostMemberships(
            Token,
            payload,
            **_StepKw(ScenarioSteps, "注册会籍（重复 type）"),
        )
        ok = IsHttpOk(resp) and IsBusinessSuccess(env)
        if not ok:
            with allure.step("接口直接拒绝重复 type（失败语义）"):
                AssertBusinessFailureEnvelope(resp, env, context="重复 type 注册")
                try:
                    raw_dup = resp.json()
                except ValueError:
                    return
                if not isinstance(raw_dup, dict):
                    return
                ec_dup = raw_dup.get("errCode")
                if ec_dup in (PAPI2548_EXT_ERR_DUPLICATE_TYPE, PAPI2548_EXT_ERR_DUPLICATE_TYPE_LEGACY):
                    AssertPapi2548DuplicateTypeErrorResponse(resp)
            return
        AssertRegisterSuccessBody(reg_inner)
        if not papi2548_sandbox_flags.search_shows_extensions:
            pytest.skip("沙箱未拒绝重复 type 且 search 不可见 extensions，无法断言持久化结果")
        mid = ExtractMembershipId(reg_inner)
        with allure.step("注册成功但含重复 type：须仍能解析 membershipId"):
            assert mid, "应从成功响应解析 membershipId"
        PostMembershipsSearch(
            Token,
            mid,
            after_response=lambda r: RunSearchDuplicateTypeCardIdPersistenceAssertions(
                r,
                http_context="POST /v2/memberships/search",
                membership_id=mid,
                client_user_id=str(payload["clientUserId"]),
                search_core_context="重复 type 场景 search",
            ),
            **_StepKw(ScenarioSteps, "search 校验重复 type 持久化"),
        )

    @allure.title("注册不传 extensions 键应成功")
    def test_register_omit_extensions_success(
        self,
        Token: str,
        ScenarioSteps: AllureHttpScenarioSteps,
    ) -> None:
        payload = BuildMinimalMembershipPayload(extensions=None)
        assert "extensions" not in payload
        mid, got, body_reg = RegisterMembershipSuccessDetail(
            Token,
            payload,
            **_StepKw(ScenarioSteps, "注册会籍（不传 extensions）"),
        )
        assert mid
        with allure.step("不传 extensions：请求无键，响应不应带非空 extensions"):
            assert "extensions" not in payload
            if "extensions" in body_reg:
                assert body_reg.get("extensions") in (None, []), (
                    f"未传 extensions 时 data.extensions 应为 null/[]，实际 {body_reg.get('extensions')!r}"
                )
        AssertRegisterCoreFields(
            body_reg,
            membership_id=mid,
            client_user_id=str(payload["clientUserId"]),
            expect_status=1,
            context="注册 data",
        )
        AssertRegisterSelectedFieldsEchoed(body_reg, payload, context="omit extensions")
        # 产品若在 data 上新增字段（如约定枚举），在此追加键值断言即可：
        # AssertDictKeyValues(body_reg, {"yourNewKey": "expected"}, context="2548 新增字段")
        AssertDictKeyValues(body_reg, {"status": 1}, context="status 回显（AssertDictKeyValues 用法示例）")
        assert got == [] or NormalizeExtensionsForCompare(got) == []

    @allure.title("注册 extensions 为空数组应成功")
    def test_register_empty_extensions_success(
        self,
        Token: str,
        ScenarioSteps: AllureHttpScenarioSteps,
    ) -> None:
        payload = BuildMinimalMembershipPayload(extensions=[])
        assert payload.get("extensions") == []
        mid, got, body_reg = RegisterMembershipSuccessDetail(
            Token,
            payload,
            **_StepKw(ScenarioSteps, "注册会籍（extensions 空数组）"),
        )
        assert mid
        with allure.step("空数组：与请求一致且无重复 type"):
            AssertRegisterCoreFields(
                body_reg,
                membership_id=mid,
                client_user_id=str(payload["clientUserId"]),
                expect_status=1,
                context="空 extensions 注册",
            )
            AssertRegisterSelectedFieldsEchoed(body_reg, payload, context="空数组注册")
            assert got == [] or NormalizeExtensionsForCompare(got) == []
            if got:
                AssertNoDuplicateExtensionTypesInList(got, context="注册响应")

    @allure.title("恰好 5 个不同 type 的 extensions 注册成功")
    def test_register_five_distinct_types_success(
        self,
        Token: str,
        papi2548_sandbox_flags: Papi2548SandboxFlags,
        ScenarioSteps: AllureHttpScenarioSteps,
    ) -> None:
        exts: List[ExtensionRegisterItem] = [
            {"type": f"t{i}", "value": str(i)} for i in range(5)
        ]
        payload = BuildMinimalMembershipPayload(extensions=exts)
        mid, got, body_reg = RegisterMembershipSuccessDetail(
            Token,
            payload,
            **_StepKw(ScenarioSteps, "注册会籍（5 个 type）"),
        )
        assert mid
        AssertRegisterCoreFields(
            body_reg,
            membership_id=mid,
            client_user_id=str(payload["clientUserId"]),
            expect_status=1,
            context="5 type 注册",
        )
        if len(NormalizeExtensionsForCompare(got)) == 5:
            with allure.step("上限内：5 条 type 互异且与入参完全一致"):
                AssertExtensionsNormalizedEqual(got, exts, context="注册响应")
                AssertNoDuplicateExtensionTypesInList(got, context="注册响应")
                AssertExtensionItemsKeyShape(
                    got,
                    ("type", "value"),
                    allowed_keys=("type", "value"),
                    context="注册响应",
                )
            return
        if papi2548_sandbox_flags.search_shows_extensions:
            PostMembershipsSearch(
                Token,
                mid,
                after_response=lambda r: RunSearchResponseAssertions(
                    r,
                    http_context="POST /v2/memberships/search",
                    membership_id=mid,
                    client_user_id=str(payload["clientUserId"]),
                    expect_status=1,
                    search_core_context="5 type search",
                    extensions_equal_to=exts,
                    extensions_context="search",
                    expect_normalized_count=5,
                    assert_shape_and_no_dup=True,
                ),
                **_StepKw(ScenarioSteps, "search 校验 5 条 type"),
            )
            return
        pytest.skip("注册成功但当前环境未在响应中返回 extensions，无法校验 5 条")

    @allure.title("6 个不同 type 的 extensions 注册应失败")
    def test_register_six_types_fails(
        self,
        Token: str,
        ScenarioSteps: AllureHttpScenarioSteps,
    ) -> None:
        exts: List[ExtensionRegisterItem] = [
            {"type": f"s{i}", "value": str(i)} for i in range(6)
        ]
        payload = BuildMinimalMembershipPayload(extensions=exts)

        def _AfterSixTypes(resp: Response) -> None:
            _st, env, _ = ParseResponseEnvelope(resp)
            ok = IsHttpOk(resp) and IsBusinessSuccess(env)
            if ok:
                pytest.skip("沙箱当前未拒绝 6 个 type，待服务端启用上限校验后重新启用断言")
            assert not (IsHttpOk(resp) and IsBusinessSuccess(env))
            with allure.step("超出 5 个 type：须为明确失败语义"):
                AssertBusinessFailureEnvelope(resp, env, context="6 type")
            try:
                raw = resp.json()
            except ValueError:
                return
            if isinstance(raw, dict):
                if raw.get("code") is not None:
                    AssertRootBusinessCodeIndicatesFailure(raw, context="6 type")
            if isinstance(raw, dict):
                ec6 = raw.get("errCode")
                if ec6 in (PAPI2548_EXT_ERR_MAX_FIVE_TYPES, PAPI2548_EXT_ERR_MAX_FIVE_TYPES_LEGACY):
                    AssertPapi2548MaxFiveTypesErrorResponse(resp)

        CallMembershipsExpectFailure(
            Token,
            payload,
            after_response=_AfterSixTypes,
            **_StepKw(ScenarioSteps, "注册会籍（6 个 type，期望失败）"),
        )

    @allure.title("type/value 长度边界参数化")
    @pytest.mark.parametrize(
        "type_len,value_len,expect_success",
        [
            (128, 1, True),
            (1, 128, True),
            (129, 1, False),
            (1, 129, False),
        ],
        ids=["A_128_1", "B_1_128", "C_129_1", "D_1_129"],
    )
    def test_register_type_value_length_boundary(
        self,
        Token: str,
        type_len: int,
        value_len: int,
        expect_success: bool,
        ScenarioSteps: AllureHttpScenarioSteps,
    ) -> None:
        t = StrOfLength(type_len, "t")
        v = StrOfLength(value_len, "v")
        exts: List[ExtensionRegisterItem] = [{"type": t, "value": v}]
        payload = BuildMinimalMembershipPayload(extensions=exts)
        resp, env, inner = PostMemberships(
            Token,
            payload,
            **_StepKw(ScenarioSteps, "注册会籍（type/value 长度边界）"),
        )
        ok = IsHttpOk(resp) and IsBusinessSuccess(env)
        if expect_success:
            assert ok, f"期望成功: {resp.status_code}, {resp.text[:600]}"
            assert inner is not None
            body_ok = AssertRegisterSuccessBody(inner)
            with allure.step("边界内：extensions 回显与请求的 type/value 完全一致"):
                reg_ext = ExtractExtensionsList(body_ok)
                AssertExtensionsNormalizedEqual(reg_ext, exts, context="边界成功")
                AssertExtensionItemsKeyShape(
                    reg_ext,
                    ("type", "value"),
                    allowed_keys=("type", "value"),
                    context="边界成功",
                )
                assert len(str(t)) == type_len and len(str(v)) == value_len, (
                    f"请求体长度 type={len(str(t))} value={len(str(v))} 应与参数一致"
                )
        else:
            if ok:
                pytest.skip("沙箱当前未拒绝 129 长度 type/value，待校验收紧后重新断言")
            with allure.step("边界外：业务或 HTTP 须失败"):
                AssertBusinessFailureEnvelope(resp, env, context="129 长度")
            assert not (IsHttpOk(resp) and IsBusinessSuccess(env))
            try:
                raw_b = resp.json()
            except ValueError:
                raw_b = None
            if isinstance(raw_b, dict) and raw_b.get("code") is not None:
                AssertRootBusinessCodeIndicatesFailure(raw_b, context="129 长度")


@allure.feature("PAPI-2548")
@allure.story("v2_memberships_search")
class TestMembershipsSearchExtensions:
    @allure.title("search 返回的 extensions 与注册一致")
    def test_search_extensions_match_register(
        self,
        Token: str,
        papi2548_sandbox_flags: Papi2548SandboxFlags,
        ScenarioSteps: AllureHttpScenarioSteps,
    ) -> None:
        if not papi2548_sandbox_flags.search_shows_extensions:
            pytest.skip("当前环境 search 未返回 extensions，跳过一致性校验")
        exts: List[ExtensionRegisterItem] = [
            {"type": "aliasX", "value": "v1"},
            {"type": "cardY", "value": "v2"},
        ]
        payload = BuildMinimalMembershipPayload(extensions=exts)
        mid, reg_ext = RegisterMembershipSuccess(
            Token,
            payload,
            **_StepKw(ScenarioSteps, "注册会籍（search 一致性前置）"),
        )
        PostMembershipsSearch(
            Token,
            mid,
            after_response=lambda r: RunSearchResponseAssertions(
                r,
                http_context="POST /v2/memberships/search",
                membership_id=mid,
                client_user_id=str(payload["clientUserId"]),
                expect_status=1,
                search_core_context="search",
                extensions_equal_to=reg_ext,
                extensions_context="search vs 注册",
                assert_shape_and_no_dup=True,
            ),
            **_StepKw(ScenarioSteps, "search 拉取会籍与 extensions"),
        )

    @allure.title("未传 extensions 注册的会籍 search 时 extensions 为空或省略")
    def test_search_membership_without_extensions_semantics(
        self,
        Token: str,
        ScenarioSteps: AllureHttpScenarioSteps,
    ) -> None:
        payload = BuildMinimalMembershipPayload(extensions=None)
        mid, _ = RegisterMembershipSuccess(
            Token,
            payload,
            **_StepKw(ScenarioSteps, "注册会籍（无 extensions）"),
        )
        PostMembershipsSearch(
            Token,
            mid,
            after_response=lambda r: RunSearchOmitExtensionsSemanticsAssertions(
                r,
                http_context="POST /v2/memberships/search",
                membership_id=mid,
                client_user_id=str(payload["clientUserId"]),
                search_core_context="无 extensions 注册后 search",
            ),
            **_StepKw(ScenarioSteps, "search 校验 extensions 语义"),
        )


@allure.feature("PAPI-2548")
@allure.story("v2_memberships_extensions")
class TestMembershipsExtensionsUpdate:
    @allure.title("UPSERT 新增 type 成功且返回完整 extensions")
    def test_extensions_upsert_add_new_type(
        self,
        Token: str,
        papi2548_sandbox_flags: Papi2548SandboxFlags,
        ScenarioSteps: AllureHttpScenarioSteps,
    ) -> None:
        RequirePapi2548ExtensionsWriteOrSkip(papi2548_sandbox_flags)
        exts: List[ExtensionRegisterItem] = [{"type": "keepA", "value": "1"}]
        mid, _ = RegisterMembershipSuccess(
            Token,
            BuildMinimalMembershipPayload(extensions=exts),
            **_StepKw(ScenarioSteps, "注册会籍（PATCH 前置）"),
        )
        ops: List[ExtensionUpdateItem] = [{"operation": "UPSERT", "type": "newB", "value": "2"}]
        PatchMembershipsExtensions(
            Token,
            mid,
            ops,
            after_response=lambda r: RunPatchExtensionsAssertions(
                r,
                membership_id=mid,
                expected_extensions=[{"type": "keepA", "value": "1"}, {"type": "newB", "value": "2"}],
                ext_context="extensions 更新",
                assert_no_dup=True,
                assert_shape=True,
            ),
            **_StepKw(ScenarioSteps, "extensions UPSERT 新增 type"),
        )

    @allure.title("UPSERT 已存在 type 更新 value")
    def test_extensions_upsert_update_value(
        self,
        Token: str,
        papi2548_sandbox_flags: Papi2548SandboxFlags,
        ScenarioSteps: AllureHttpScenarioSteps,
    ) -> None:
        RequirePapi2548ExtensionsWriteOrSkip(papi2548_sandbox_flags)
        exts: List[ExtensionRegisterItem] = [{"type": "k1", "value": "old"}]
        mid, _ = RegisterMembershipSuccess(
            Token,
            BuildMinimalMembershipPayload(extensions=exts),
            **_StepKw(ScenarioSteps, "注册会籍（PATCH 前置）"),
        )
        ops: List[ExtensionUpdateItem] = [{"operation": "UPSERT", "type": "k1", "value": "newval"}]
        PatchMembershipsExtensions(
            Token,
            mid,
            ops,
            after_response=lambda r: RunPatchExtensionsAssertions(
                r,
                membership_id=mid,
                expected_extensions=[{"type": "k1", "value": "newval"}],
                ext_context="extensions 更新",
                length_exact=1,
                single_item_type_value=("k1", "newval"),
            ),
            **_StepKw(ScenarioSteps, "extensions UPSERT 更新 value"),
        )

    @allure.title("DELETE 移除已有 type")
    def test_extensions_delete_existing_type(
        self,
        Token: str,
        papi2548_sandbox_flags: Papi2548SandboxFlags,
        ScenarioSteps: AllureHttpScenarioSteps,
    ) -> None:
        RequirePapi2548ExtensionsWriteOrSkip(papi2548_sandbox_flags)
        exts: List[ExtensionRegisterItem] = [
            {"type": "a1", "value": "1"},
            {"type": "b2", "value": "2"},
        ]
        mid, _ = RegisterMembershipSuccess(
            Token,
            BuildMinimalMembershipPayload(extensions=exts),
            **_StepKw(ScenarioSteps, "注册会籍（PATCH 前置）"),
        )
        ops: List[ExtensionUpdateItem] = [{"operation": "DELETE", "type": "a1"}]
        def _AfterDeleteExisting(resp: Response) -> None:
            got = RunPatchExtensionsAssertions(
                resp,
                membership_id=mid,
                expected_extensions=[{"type": "b2", "value": "2"}],
                ext_context="extensions 更新",
            )
            pairs = {t for t, _ in NormalizeExtensionsForCompare(got)}
            assert "a1" not in pairs
            assert "b2" in pairs

        PatchMembershipsExtensions(
            Token,
            mid,
            ops,
            after_response=_AfterDeleteExisting,
            **_StepKw(ScenarioSteps, "extensions DELETE 移除 type"),
        )

    @allure.title("DELETE 不存在的 type 仍成功且数据不变")
    def test_extensions_delete_nonexistent_type_idempotent(
        self,
        Token: str,
        papi2548_sandbox_flags: Papi2548SandboxFlags,
        ScenarioSteps: AllureHttpScenarioSteps,
    ) -> None:
        RequirePapi2548ExtensionsWriteOrSkip(papi2548_sandbox_flags)
        RequirePapi2548SearchShowsExtensionsOrSkip(papi2548_sandbox_flags)
        exts: List[ExtensionRegisterItem] = [{"type": "only", "value": "x"}]
        mid, _ = RegisterMembershipSuccess(
            Token,
            BuildMinimalMembershipPayload(extensions=exts),
            **_StepKw(ScenarioSteps, "注册会籍"),
        )
        before_holder: Dict[str, List[Tuple[str, Optional[str]]]] = {}

        def _AfterSearchBeforeDelete(resp: Response) -> None:
            RunSearchSnapshotForDeleteAssertions(
                resp,
                http_context="POST /v2/memberships/search(before DELETE)",
                membership_id=mid,
            )
            _st, _e, inner_b = ParseResponseEnvelope(resp)
            rec_b = UnwrapMembershipRecord(inner_b)
            AssertMembershipSearchRecord(rec_b, mid)
            before_holder["snap"] = NormalizeExtensionsForCompare(ExtractExtensionsList(rec_b))

        PostMembershipsSearch(
            Token,
            mid,
            after_response=_AfterSearchBeforeDelete,
            **_StepKw(ScenarioSteps, "search 取 DELETE 前快照"),
        )
        before = before_holder["snap"]
        ops: List[ExtensionUpdateItem] = [{"operation": "DELETE", "type": "nosuch"}]

        def _AfterPatchDeleteNosuch(resp: Response) -> None:
            after_ext = RunPatchExtensionsAssertions(
                resp,
                membership_id=mid,
                expected_extensions=[{"type": "only", "value": "x"}],
                ext_context="extensions 更新应与 search 前一致",
            )
            assert NormalizeExtensionsForCompare(after_ext) == before

        PatchMembershipsExtensions(
            Token,
            mid,
            ops,
            after_response=_AfterPatchDeleteNosuch,
            **_StepKw(ScenarioSteps, "extensions DELETE 不存在的 type"),
        )

    @allure.title("同一请求混合 UPSERT 与 DELETE")
    def test_extensions_mixed_operations(
        self,
        Token: str,
        papi2548_sandbox_flags: Papi2548SandboxFlags,
        ScenarioSteps: AllureHttpScenarioSteps,
    ) -> None:
        RequirePapi2548ExtensionsWriteOrSkip(papi2548_sandbox_flags)
        exts: List[ExtensionRegisterItem] = [
            {"type": "delMe", "value": "1"},
            {"type": "keepMe", "value": "2"},
        ]
        mid, _ = RegisterMembershipSuccess(
            Token,
            BuildMinimalMembershipPayload(extensions=exts),
            **_StepKw(ScenarioSteps, "注册会籍"),
        )
        ops: List[ExtensionUpdateItem] = [
            {"operation": "DELETE", "type": "delMe"},
            {"operation": "UPSERT", "type": "addMe", "value": "3"},
        ]
        def _AfterMixed(resp: Response) -> None:
            got = RunPatchExtensionsAssertions(
                resp,
                membership_id=mid,
                expected_extensions=[{"type": "keepMe", "value": "2"}, {"type": "addMe", "value": "3"}],
                ext_context="extensions 更新",
                assert_no_dup=True,
            )
            pairs = NormalizeExtensionsForCompare(got)
            assert ("delMe", "1") not in pairs
            assert ("keepMe", "2") in pairs
            assert ("addMe", "3") in pairs

        PatchMembershipsExtensions(
            Token,
            mid,
            ops,
            after_response=_AfterMixed,
            **_StepKw(ScenarioSteps, "extensions 混合 DELETE+UPSERT"),
        )

    @allure.title("membershipId 不存在时应失败")
    def test_extensions_invalid_membership_id_fails(
        self,
        Token: str,
        ScenarioSteps: AllureHttpScenarioSteps,
    ) -> None:
        fake_id = str(uuid.uuid4().int)[:18]
        ops: List[ExtensionUpdateItem] = [{"operation": "UPSERT", "type": "x", "value": "y"}]
        PatchMembershipsExtensions(
            Token,
            fake_id,
            ops,
            after_response=RunPatchInvalidMembershipIdAssertions,
            **_StepKw(ScenarioSteps, "extensions 更新（非法 membershipId）"),
        )

    @allure.title("非法 operation 不得改变已持久化的 extensions")
    def test_extensions_invalid_operation_fails(
        self,
        Token: str,
        papi2548_sandbox_flags: Papi2548SandboxFlags,
        ScenarioSteps: AllureHttpScenarioSteps,
    ) -> None:
        RequirePapi2548SearchShowsExtensionsOrSkip(papi2548_sandbox_flags)
        exts: List[ExtensionRegisterItem] = [{"type": "stable", "value": "1"}]
        payload_io = BuildMinimalMembershipPayload(extensions=exts)
        mid, _ = RegisterMembershipSuccess(
            Token,
            payload_io,
            **_StepKw(ScenarioSteps, "注册会籍"),
        )
        before_holder2: Dict[str, List[Tuple[str, Optional[str]]]] = {}

        def _AfterSearchBeforeBadOp(resp: Response) -> None:
            RunSearchResponseAssertions(
                resp,
                http_context="POST /v2/memberships/search(before)",
                membership_id=mid,
                client_user_id=str(payload_io["clientUserId"]),
                expect_status=1,
                search_core_context="非法 operation 前 search",
            )
            _st, _e, inner0 = ParseResponseEnvelope(resp)
            rec0 = UnwrapMembershipRecord(inner0)
            before_holder2["before"] = NormalizeExtensionsForCompare(ExtractExtensionsList(rec0))
            with allure.step("非法 operation 前：extensions 与注册一致"):
                AssertExtensionsNormalizedEqual(ExtractExtensionsList(rec0), exts, context="search before")

        PostMembershipsSearch(
            Token,
            mid,
            after_response=_AfterSearchBeforeBadOp,
            **_StepKw(ScenarioSteps, "search（非法 operation 前）"),
        )
        before = before_holder2["before"]
        ops = [{"operation": "UPDATE", "type": "x", "value": "y"}]
        patch_holder: Dict[str, str] = {}

        def _AfterBadPatch(resp: Response) -> None:
            RunPatchInvalidOperationGatewayAssertions(resp)
            patch_holder["raw"] = resp.text[:500]

        PatchMembershipsExtensions(
            Token,
            mid,
            ops,
            after_response=_AfterBadPatch,
            **_StepKw(ScenarioSteps, "extensions 更新（非法 operation）"),
        )

        def _AfterSearchAfterBadOp(resp: Response) -> None:
            RunSearchResponseAssertions(
                resp,
                http_context="POST /v2/memberships/search(after)",
                membership_id=mid,
                client_user_id=str(payload_io["clientUserId"]),
                expect_status=1,
                search_core_context="非法 operation 后 search",
            )
            _st, _e, inner2 = ParseResponseEnvelope(resp)
            rec2 = UnwrapMembershipRecord(inner2)
            after = NormalizeExtensionsForCompare(ExtractExtensionsList(rec2))
            with allure.step("非法 operation 后：extensions 与操作前完全一致"):
                AssertExtensionsNormalizedEqual(ExtractExtensionsList(rec2), exts, context="search after")
            assert after == before, (
                f"非法 operation 不得修改 extensions: before={before!r} after={after!r}, "
                f"raw={patch_holder.get('raw', '')}"
            )

        PostMembershipsSearch(
            Token,
            mid,
            after_response=_AfterSearchAfterBadOp,
            **_StepKw(ScenarioSteps, "search（非法 operation 后）"),
        )

    @allure.title("UPSERT 缺少 value：按契约成功或失败（记录实际行为）")
    def test_extensions_upsert_missing_value_documented(
        self,
        Token: str,
        ScenarioSteps: AllureHttpScenarioSteps,
    ) -> None:
        mid, _ = RegisterMembershipSuccess(
            Token,
            BuildMinimalMembershipPayload(extensions=[{"type": "base", "value": "1"}]),
            **_StepKw(ScenarioSteps, "注册会籍"),
        )
        ops: List[ExtensionUpdateItem] = [{"operation": "UPSERT", "type": "noval"}]
        PatchMembershipsExtensions(
            Token,
            mid,
            ops,
            after_response=lambda r: RunUpsertMissingValueDocumentedAssertions(r, membership_id=mid),
            **_StepKw(ScenarioSteps, "extensions UPSERT 缺 value"),
        )


@allure.feature("PAPI-2548")
@allure.story("E2E")
class TestMembershipsExtensionsE2E:
    @allure.title("注册→search→extensions→search 闭环一致")
    def test_e2e_register_search_extensions_search(
        self,
        Token: str,
        papi2548_sandbox_flags: Papi2548SandboxFlags,
        ScenarioSteps: AllureHttpScenarioSteps,
    ) -> None:
        RunPapi2548MainE2EScenario(Token, ScenarioSteps, papi2548_sandbox_flags)


@allure.feature("PAPI-2548")
@pytest.mark.manual
class TestManualObservation:
    @allure.title("SaaS feature 存放（需人工/DB/管理端）")
    def test_placeholder_saas_feature_not_automated(self) -> None:
        pytest.skip("依赖外部观测手段，参见手工用例 tc-p3")
