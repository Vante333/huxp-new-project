"""
预预约 Payment · 品类参数（Fast Track / Lounge）。

``ft_prebooking_payment_common`` 在 ``Generate(..., category=...)`` 时 ``SetActiveCategory``，
路径 / 资源变量 / module 枚举 / 权益不足池 / **单一价 Environment 键名与默认值**均读本配置。

定价与 FT **解耦（换变量名）**：同一 Apifox Environment 可同时放 FT 键与 Lounge ``lounge*`` 键，
改 BOSS 价只改对应键，互不覆盖。断言脚本仍读规范键（``prebookingUnitPrice`` 等），
由 ``ftPayEnsurePricingEnv`` 从本品类 Environment 键映射写入。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Final, Literal, Tuple

CategoryKind = Literal["fastTrack", "lounge"]

# 断言 / helpers 使用的规范键（与 tools/apifox_payment_assert_post.js 一致）
PRICING_CANONICAL_KEYS: Final[Tuple[str, ...]] = (
    "paymentSceneId",
    "prebookingFeePayer",
    "prebookingUnitPrice",
    "overageUnitPrice",
    "paymentSceneExpectError",
    "assert_payment_env_price",
)


@dataclass(frozen=True)
class CategoryConfig:
    key: CategoryKind
    label_zh: str
    label_en: str
    """订单 path 段：fastTrack | lounges"""
    path_segment: str
    resource_env_key: str
    default_resource_id: str
    """body.module / epassModule 默认值"""
    epass_module: int
    """注册权益 moduleExclusiveEntitlements 池"""
    insuf_module: int
    """创建 ePass 采购单 category 断言"""
    epass_create_category: int
    """预预约 usage 单 category 断言"""
    usage_order_category: int
    collection_prefix: str
    out_name_prefix: str
    """Environment / 集合变量名（与 FT 解耦时换名即可）"""
    env_payment_scene_id: str
    env_prebooking_fee_payer: str
    env_prebooking_unit_price: str
    env_overage_unit_price: str
    env_payment_scene_expect_error: str
    env_assert_payment_env_price: str
    """单一价默认值"""
    payment_scene_id: str
    prebooking_fee_payer: str
    prebooking_unit_price: str
    overage_unit_price: str
    assert_payment_env_price: str
    payment_scene_expect_error: str = "false"
    pricing_note_zh: str = ""

    def PricingEnvKeyMap(self) -> Dict[str, str]:
        """规范键 → 本品类 Environment 键名。"""
        return {
            "paymentSceneId": self.env_payment_scene_id,
            "prebookingFeePayer": self.env_prebooking_fee_payer,
            "prebookingUnitPrice": self.env_prebooking_unit_price,
            "overageUnitPrice": self.env_overage_unit_price,
            "paymentSceneExpectError": self.env_payment_scene_expect_error,
            "assert_payment_env_price": self.env_assert_payment_env_price,
        }

    def PricingDefaults(self) -> Dict[str, str]:
        return {
            "paymentSceneId": self.payment_scene_id,
            "prebookingFeePayer": self.prebooking_fee_payer,
            "prebookingUnitPrice": self.prebooking_unit_price,
            "overageUnitPrice": self.overage_unit_price,
            "paymentSceneExpectError": self.payment_scene_expect_error,
            "assert_payment_env_price": self.assert_payment_env_price,
        }


CATALOG: Final[Dict[CategoryKind, CategoryConfig]] = {
    "fastTrack": CategoryConfig(
        key="fastTrack",
        label_zh="Fast Track",
        label_en="Fast Track",
        path_segment="fastTrack",
        resource_env_key="fastTrackResourceId",
        # 与 env/.env.canary 的 DP_HIST_EPASS_FASTTRACK_RESOURCE_ID 对齐；N18999 在 UAT 常 301.020.001
        default_resource_id="C10826",
        epass_module=2,
        insuf_module=2,
        epass_create_category=2,
        usage_order_category=2,
        collection_prefix="FT",
        out_name_prefix="FT",
        # FT 沿用规范键名（与历史 Environment 一致）
        env_payment_scene_id="paymentSceneId",
        env_prebooking_fee_payer="prebookingFeePayer",
        env_prebooking_unit_price="prebookingUnitPrice",
        env_overage_unit_price="overageUnitPrice",
        env_payment_scene_expect_error="paymentSceneExpectError",
        env_assert_payment_env_price="assert_payment_env_price",
        payment_scene_id="7",
        prebooking_fee_payer="user",
        prebooking_unit_price="8.99",
        overage_unit_price="23.67",
        assert_payment_env_price="true",
        payment_scene_expect_error="false",
        pricing_note_zh=(
            "FT Environment 键：paymentSceneId / prebookingFeePayer / "
            "prebookingUnitPrice / overageUnitPrice / …；默认 scene=7"
        ),
    ),
    "lounge": CategoryConfig(
        key="lounge",
        label_zh="休息室",
        label_en="Lounge",
        path_segment="lounges",
        resource_env_key="loungeResourceId",
        default_resource_id="N00012",
        epass_module=1,
        insuf_module=1,
        # 创建 ePass 采购单与历史 Lounge 金样例一致 category=3（usage 预约单仍为 2）
        epass_create_category=3,
        usage_order_category=2,
        collection_prefix="Lounge",
        out_name_prefix="Lounge",
        # 与 FT 同 Environment 解耦：换 lounge* 变量名即可并存
        env_payment_scene_id="loungePaymentSceneId",
        env_prebooking_fee_payer="loungePrebookingFeePayer",
        env_prebooking_unit_price="loungePrebookingUnitPrice",
        env_overage_unit_price="loungeOverageUnitPrice",
        env_payment_scene_expect_error="loungePaymentSceneExpectError",
        env_assert_payment_env_price="loungeAssertPaymentEnvPrice",
        # 对齐 Lounge BOSS 单一价（客户预约费=0 + 超人次=17 → 场景 3）
        payment_scene_id="3",
        prebooking_fee_payer="client",
        prebooking_unit_price="0",
        overage_unit_price="17.00",
        assert_payment_env_price="true",
        payment_scene_expect_error="false",
        pricing_note_zh=(
            "Lounge Environment 键（与 FT 解耦）：loungePaymentSceneId / "
            "loungePrebookingFeePayer / loungePrebookingUnitPrice / "
            "loungeOverageUnitPrice / loungePaymentSceneExpectError / "
            "loungeAssertPaymentEnvPrice；默认 scene=3（client/0/17.00）"
        ),
    ),
}

_Active: CategoryConfig = CATALOG["fastTrack"]


def SetActiveCategory(key: CategoryKind) -> CategoryConfig:
    global _Active
    if key not in CATALOG:
        raise ValueError(f"未知品类 category={key!r}；可选 {sorted(CATALOG)}")
    _Active = CATALOG[key]
    return _Active


def ActiveCategory() -> CategoryConfig:
    return _Active
