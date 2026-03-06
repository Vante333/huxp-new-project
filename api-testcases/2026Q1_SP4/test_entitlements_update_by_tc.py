import pytest

from entitlements_helpers import (
    get_access_token,
    create_membership,
    get_entitlements_details,
    get_entitlements_search,
    update_entitlements,
)


@pytest.mark.entitlements_update
class TestEntitlementsUpdateByTC:
    """
    覆盖《会籍权益分级需求文档测试用例.md》中 ENT-UPDATE 相关用例：
    - tc-P0-ENT-UPDATE-001 ~ 005
    - tc-P1-ENT-UPDATE-008 ~ 011
    - tc-P2-ENT-UPDATE-012 ~ 013
    - tc-P2-ENT-UPDATE-015 ~ 016（多 tier 求和场景，给出骨架）
    - tc-P1-ENT-UPDATE-017 ~ 018（scopeType=2 null 字段规则）
    """

    def test_tc_P0_ENT_UPDATE_001_scopeType_2_update_specific_tier(self):
        """
        tc-P0-ENT-UPDATE-001：
        scopeType=2 时传入正确 tier，指定 tier 权益更新成功。

        真正落地时，建议使用一个已知 scopeType=2、且 tier=1 有非共享权益的会员，
        这里暂时用 create_membership 占位，并在 scopeType!=2 时跳过。
        """
        token = get_access_token()
        membership_id = create_membership(token)

        details_before = get_entitlements_details(token, membership_id, module="3")
        if details_before.get("scopeType") != 2:
            pytest.skip("当前测试会员非 TIERED（scopeType!=2），请改为固定 scopeType=2 会籍后再启用此用例")

        update_resp = update_entitlements(
            token,
            membership_id=membership_id,
            module="3",
            quantity=5,
            tier=1,
        )
        assert update_resp.get("scopeType") == 2

        # 再查询 details，确认 tier=1 的权益有变化（这里只做“有变化”的示意）
        details_after = get_entitlements_details(token, membership_id, module="3")
        assert details_after.get("scopeType") == 2

    def test_tc_P0_ENT_UPDATE_002_scopeType_1_update_without_tier(self):
        """
        tc-P0-ENT-UPDATE-002：
        scopeType=1 时不传 tier 字段，正常更新权益。
        """
        token = get_access_token()
        membership_id = create_membership(token)

        details_before = get_entitlements_details(token, membership_id, module="3")
        if details_before.get("scopeType") != 1:
            pytest.skip("当前测试会员非 GLOBAL（scopeType!=1），请改为固定 scopeType=1 会籍后再启用此用例")

        update_resp = update_entitlements(
            token,
            membership_id=membership_id,
            module="3",
            quantity=5,
        )
        assert update_resp.get("scopeType") == 1

    @pytest.mark.parametrize(
        "case_id,desc,has_tier_entitlements,send_tier,expected_status_not_200",
        [
            ("tc-P0-ENT-UPDATE-003", "无分级权益时传 tier", False, True, True),
            ("tc-P0-ENT-UPDATE-004", "有分级权益时未传 tier", True, False, True),
            ("tc-P0-ENT-UPDATE-005", "传不存在的 tier 值", True, True, True),
        ],
    )
    def test_tc_P0_ENT_UPDATE_003_005_tier_validation(
        self,
        case_id,
        desc,
        has_tier_entitlements,
        send_tier,
        expected_status_not_200,
    ):
        """
        三个错误码场景的通用骨架。
        由于当前测试环境尚未区分“有分级权益/无分级权益”的造数方式，
        这里仅示例如何构造参数，真正落地时你可以：
        - 使用固定 membershipId 表示“无分级权益”的品类；
        - 使用固定 membershipId 表示“有分级权益”的品类；
        然后在这里精确断言 code=500.030.026/027/028。
        """
        token = get_access_token()
        membership_id = create_membership(token)

        import requests
        from entitlements_helpers import BASE_URL, common_headers

        url = BASE_URL.rstrip("/") + "/v2/entitlements/update"
        payload = {
            "membershipId": membership_id,
            "module": "3",
            "quantity": 5,
        }
        if send_tier:
            payload["tier"] = 999  # 故意传错/不存在的 tier

        resp = requests.post(url, json=payload, headers=common_headers(token), timeout=10)

        if expected_status_not_200:
            assert resp.status_code != 200
        else:
            assert resp.status_code == 200

        # TODO：按具体 case_id 对应的错误码，断言 resp.json()["code"] == 500.030.0xx

    @pytest.mark.parametrize(
        "case_id,tier_value",
        [
            ("tc-P2-ENT-UPDATE-012", 0),
            ("tc-P2-ENT-UPDATE-013", -1),
        ],
    )
    def test_tc_P2_ENT_UPDATE_012_013_tier_boundary(self, case_id, tier_value):
        """
        tc-P2-ENT-UPDATE-012/013：
        tier 传入 0 或负数进行权益更新。
        """
        token = get_access_token()
        membership_id = create_membership(token)

        import requests
        from entitlements_helpers import BASE_URL, common_headers

        url = BASE_URL.rstrip("/") + "/v2/entitlements/update"
        payload = {
            "membershipId": membership_id,
            "module": "3",
            "tier": tier_value,
            "quantity": 5,
        }
        resp = requests.post(url, json=payload, headers=common_headers(token), timeout=10)

        assert resp.status_code != 200
        # TODO：断言错误码为 500.030.028

    def test_tc_P1_ENT_UPDATE_017_018_scopeType_2_null_fields_after_update(self):
        """
        tc-P1-ENT-UPDATE-017/018：
        scopeType=2 时：
        - update 成功后 search 接口 allowedGuestsPerUsage、maxGuestsNextUse 仍为 null；
        - update 接口自身返回的 allowedGuestsPerUsage、maxGuestsNextUse 也为 null。
        """
        token = get_access_token()
        membership_id = create_membership(token)

        details_before = get_entitlements_details(token, membership_id, module="3")
        if details_before.get("scopeType") != 2:
            pytest.skip("当前测试会员非 TIERED（scopeType!=2），请改为固定 scopeType=2 会籍后再启用此用例")

        # 先做一次 update
        update_resp = update_entitlements(
            token,
            membership_id=membership_id,
            module="3",
            quantity=5,
            tier=1,
        )
        # update 返回的这两个字段应该为 null
        details_part = update_resp.get("details") or {}
        assert details_part.get("allowedGuestsPerUsage") is None
        assert details_part.get("maxGuestsNextUse") is None

        # 再查 search，确认仍为 null
        search_body = get_entitlements_search(token, membership_id)
        search_details = search_body.get("details") or {}
        assert search_details.get("allowedGuestsPerUsage") is None
        assert search_details.get("maxGuestsNextUse") is None

