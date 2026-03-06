import pytest

from entitlements_helpers import (
    get_access_token,
    create_membership,
    get_entitlements_search,
)


@pytest.mark.entitlements_search
class TestEntitlementsSearchByTC:
    """
    覆盖《会籍权益分级需求文档测试用例.md》中 ENT-SEARCH 相关用例：
    - tc-P0-ENT-SEARCH-001 ~ 002
    - tc-P1-ENT-SEARCH-003 ~ 005
    - tc-P0-ENT-SEARCH-006 ~ 008
    """

    def test_tc_P0_ENT_SEARCH_001_scopeType_1_all_fields_present(self):
        """
        tc-P0-ENT-SEARCH-001：
        scopeType=1 时调用权益查询接口，所有 6 个权益字段正常返回。
        这里用一个新建会籍，假设默认场景为 GLOBAL（scopeType=1），
        如果你们环境不是这样，需要在这里改成“先造出 scopeType=1 的会籍”。
        """
        token = get_access_token()
        membership_id = create_membership(token)

        body = get_entitlements_search(token, membership_id)

        assert body.get("scopeType") == 1
        details = body.get("details") or {}
        for field in [
            "cardholderExclusiveEntitlements",
            "guestsExclusiveEntitlements",
            "sharedEntitlements",
            "purchasedEntitlements",
            "allowedGuestsPerUsage",
            "maxGuestsNextUse",
        ]:
            assert field in details, f"{field} missing in details"

    def test_tc_P0_ENT_SEARCH_002_scopeType_2_return_sums_only(self):
        """
        tc-P0-ENT-SEARCH-002：
        scopeType=2 时调用权益查询接口，只返回各同类型权益明细的总和。
        这里先假设你在 BOSS 里已经为某些会籍配置了 tier 分级，
        并能通过外部方式拿到一个 scopeType=2 的 membershipId。
        暂时用 create_membership 占位，真实落地时请替换为固定测试会员。
        """
        token = get_access_token()
        membership_id = create_membership(token)

        body = get_entitlements_search(token, membership_id)

        if body.get("scopeType") != 2:
            pytest.skip("当前测试会员非分级权益（scopeType!=2），请改为固定 scopeType=2 会籍后再启用此用例")

        assert body.get("scopeType") == 2
        # 文档要求只返回各同类型权益明细总和，不返回各等级明细数据
        assert "entitlements" not in body or not isinstance(body.get("entitlements"), list)

    def test_tc_P1_ENT_SEARCH_003_004_005_scopeType_consistency_with_memberships(self):
        """
        tc-P1-ENT-SEARCH-003/004/005：
        - 有 label 的分组 -> scopeType=2
        - 无 label 分组 -> scopeType=1
        - search 与 memberships 接口的 scopeType 判定一致

        这里由于没有 BOSS 配置&会员查询 API 的细节，只做一个“search 内部自洽”的占位断言：
        真正落地时，你可以在这里增加对 /v2/memberships 的调用来比对 scopeType。
        """
        token = get_access_token()
        membership_id = create_membership(token)

        search_body = get_entitlements_search(token, membership_id)

        assert search_body.get("scopeType") in (1, 2)
        # TODO：补充 /v2/memberships 接口调用，对同一 membershipId + module 比较 scopeType 一致性

    def test_tc_P0_ENT_SEARCH_006_007_008_scopeType_2_null_and_sum_rules(self):
        """
        tc-P0-ENT-SEARCH-006/007/008：
        - scopeType=2 时 allowedGuestsPerUsage = null
        - scopeType=2 时 maxGuestsNextUse = null
        - 总计字段为各 tier 权益之和

        由于没有 direct 的 tier 配置接口，这里主要验证“为 null”的规则，
        精确求和值可以和 details 接口联动校验，放在集成场景中完成。
        """
        token = get_access_token()
        membership_id = create_membership(token)

        body = get_entitlements_search(token, membership_id)

        if body.get("scopeType") != 2:
            pytest.skip("当前测试会员非分级权益（scopeType!=2），请改为固定 scopeType=2 会籍后再启用此用例")

        details = body.get("details") or {}
        assert details.get("allowedGuestsPerUsage") is None
        assert details.get("maxGuestsNextUse") is None

        # TODO：如有已知的分级配置，可以在此补充“总计字段 = 各 tier 之和”的精确断言

