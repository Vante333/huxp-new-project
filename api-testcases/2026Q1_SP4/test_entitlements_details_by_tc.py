import pytest

from entitlements_helpers import (
    get_access_token,
    create_membership,
    get_entitlements_details,
)


@pytest.mark.entitlements_details
class TestEntitlementsDetailsByTC:
    """
    覆盖《会籍权益分级需求文档测试用例.md》中 ENT-DETAIL 相关用例：
    - tc-P0-ENT-DETAIL-001 ~ 007
    - tc-P1-ENT-DETAIL-008 ~ 009
    - tc-P2-ENT-DETAIL-010 ~ 013

    说明：部分用例依赖特定配置（scopeType=1/2、多个 module 等），
    这里给出通用骨架，真正落地时只需要替换为固定的 membershipId/module 即可。
    """

    def test_tc_P0_ENT_DETAIL_001_basic_structure(self):
        """
        tc-P0-ENT-DETAIL-001：
        调用权益明细接口正常返回基础结构。
        """
        token = get_access_token()
        membership_id = create_membership(token)

        body = get_entitlements_details(token, membership_id, module="3")

        assert body.get("membershipId") == membership_id
        assert "module" in body
        assert "scopeType" in body
        assert "entitlements" in body and isinstance(body["entitlements"], list)

    def test_tc_P0_ENT_DETAIL_003_scopeType_1_details_fields(self):
        """
        tc-P0-ENT-DETAIL-003：
        scopeType=1 时 entitlements[0].details 中 6 个字段均正常返回。

        注意：需要一个 scopeType=1 的会籍，如果默认创建出来不是 1，
        建议改为使用固定的测试 membershipId。
        """
        token = get_access_token()
        membership_id = create_membership(token)

        body = get_entitlements_details(token, membership_id, module="3")

        if body.get("scopeType") != 1:
            pytest.skip("当前测试会员非 GLOBAL（scopeType!=1），请改为固定 scopeType=1 会籍后再启用此用例")

        entitlements = body.get("entitlements") or []
        assert len(entitlements) >= 1
        details = entitlements[0].get("details") or {}

        for field in [
            "cardholderExclusiveEntitlements",
            "guestsExclusiveEntitlements",
            "sharedEntitlements",
            "purchasedEntitlements",
            "allowedGuestsPerUsage",
            "maxGuestsNextUse",
        ]:
            assert field in details, f"{field} missing in details"

    def test_tc_P0_ENT_DETAIL_004_006_scopeType_2_tier_array_and_order(self):
        """
        tc-P0-ENT-DETAIL-004/005/006：
        - scopeType=2（TIERED）时按 tier 返回明细数组；
        - 每个元素包含 tier + details；
        - tier 按升序排列返回。
        """
        token = get_access_token()
        membership_id = create_membership(token)

        body = get_entitlements_details(token, membership_id, module="3")

        if body.get("scopeType") != 2:
            pytest.skip("当前测试会员非 TIERED（scopeType!=2），请改为固定 scopeType=2 会籍后再启用此用例")

        entitlements = body.get("entitlements") or []
        assert len(entitlements) >= 1

        tiers = []
        for ent in entitlements:
            assert "tier" in ent
            assert "details" in ent
            tiers.append(ent["tier"])

        assert tiers == sorted(tiers)

    def test_tc_P0_ENT_DETAIL_007_query_single_module(self):
        """
        tc-P0-ENT-DETAIL-007：
        逐个品类查询返回对应品类的权益明细。

        这里演示调用 module=1 和 module=2：
        实际环境中需要确保该会员在这些 module 下确实有配置。
        """
        token = get_access_token()
        membership_id = create_membership(token)

        body_m1 = get_entitlements_details(token, membership_id, module="1")
        body_m2 = get_entitlements_details(token, membership_id, module="2")

        assert body_m1.get("module") != body_m2.get("module")
        # 各自只应包含对应 module 的权益明细（具体字段断言可按实际结构细化）

    @pytest.mark.parametrize(
        "case_id,module,expected_code",
        [
            ("tc-P1-ENT-DETAIL-008", "9999", "500.030.029"),  # 不存在的 module
            ("tc-P2-ENT-DETAIL-010", "0", "500.030.029"),     # module=0
        ],
    )
    def test_tc_P1_P2_ENT_DETAIL_008_010_module_error_codes(
        self,
        case_id,
        module,
        expected_code,
    ):
        """
        tc-P1-ENT-DETAIL-008/ tc-P2-ENT-DETAIL-010：
        - 查询不存在的 module -> 500.030.029
        - module=0 -> 500.030.029

        由于目前不知道错误响应精确结构，这里仅示意性校验 status_code != 200，
        你可以按实际返回结构把 expected_code 和 message 的断言补上。
        """
        token = get_access_token()
        membership_id = create_membership(token)

        import requests
        from entitlements_helpers import BASE_URL, common_headers

        url = BASE_URL.rstrip("/") + "/v2/entitlements/details"
        payload = {
            "membershipId": membership_id,
            "module": module,
        }
        resp = requests.post(url, json=payload, headers=common_headers(token), timeout=10)

        assert resp.status_code != 200
        # TODO：解析 resp.json()["code"] == expected_code

    @pytest.mark.parametrize(
        "case_id,membership_id",
        [
            ("tc-P2-ENT-DETAIL-011", "0"),                 # 负数 / 0 / 非法字符等都可按需扩展
            ("tc-P2-ENT-DETAIL-012", "NON_EXIST_MEMBER"),  # 格式正确但不存在
        ],
    )
    def test_tc_P2_ENT_DETAIL_011_012_membership_errors(self, case_id, membership_id):
        """
        tc-P2-ENT-DETAIL-011/012：
        - 非法 membershipId / 不存在 membershipId
        返回相应错误码（500.030.007 或非法字符提示）。
        """
        token = get_access_token()

        import requests
        from entitlements_helpers import BASE_URL, common_headers

        url = BASE_URL.rstrip("/") + "/v2/entitlements/details"
        payload = {
            "membershipId": membership_id,
            "module": "1",
        }
        resp = requests.post(url, json=payload, headers=common_headers(token), timeout=10)

        assert resp.status_code != 200
        # TODO：按实际响应结构补充错误码 / 提示语断言

    def test_tc_P2_ENT_DETAIL_013_scopeType_1_and_2_both_work(self):
        """
        tc-P2-ENT-DETAIL-013：
        scopeType=1 和 scopeType=2 均可正常调用 details 接口。

        实际上可以通过两种不同配置的会员来分别验证，
        这里给出一个通用示例：至少保证当前会员能正常调用。
        """
        token = get_access_token()
        membership_id = create_membership(token)

        body = get_entitlements_details(token, membership_id, module="3")
        assert body.get("scopeType") in (1, 2)
        assert isinstance(body.get("entitlements"), list)

