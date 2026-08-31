"""对齐 ``api-testcases/docs/api-main-call-chains.md`` 的模块分类、{module} 展开与排序。

用于 Excel 导出：为每条接口分配主链路场景、path module slug 与 body module 整型值。
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Sequence, Tuple

ModuleVariant = Tuple[str, int, str]  # slug, moduleInt, displayName

MODULE_VARIANTS: Dict[str, ModuleVariant] = {
    "lounges": ("lounges", 1, "Lounge"),
    "fastTrack": ("fastTrack", 2, "FastTrack"),
    "setMeals": ("setMeals", 3, "SetMeal"),
    "coupons": ("coupons", 4, "Coupon"),
    "fitness": ("fitness", 5, "Fitness"),
    "esims": ("esims", 6, "eSIM"),
    "localOffers": ("localOffers", 11, "LocalOffer"),
}

EPASS_CREATE_SLUGS: Sequence[str] = (
    "lounges",
    "fastTrack",
    "setMeals",
    "coupons",
    "fitness",
    "esims",
    "localOffers",
)

MEMBERSHIP_PREBOOKING_SLUGS: Sequence[str] = (
    "lounges",
    "fastTrack",
    "fitness",
    "esims",
    "localOffers",
)

EPASS_PREBOOKING_BUNDLE_SLUGS: Sequence[str] = (
    "lounges",
    "fastTrack",
    "fitness",
    "esims",
    "localOffers",
)

SCENARIO_ORDER: Dict[str, int] = {
    "公共能力-Auth鉴权": 100,
    "公共能力-Search搜索": 110,
    "公共能力-TransportHub": 120,
    "公共能力-Resources资源": 130,
    "公共能力-Resources预约库存": 140,
    "公共能力-Users用户": 150,
    "公共能力-Entitlements权益": 160,
    "Membership-创建验证链": 200,
    "Membership-Prebooking链": 210,
    "Membership-订单查询链": 220,
    "EPass-创建验证链": 300,
    "EPass-Prebooking链": 310,
    "EPass-Bundle链": 320,
    "ESIM-EPassTopup链": 400,
    "ESIM-MembershipTopup链": 410,
    "LocalOffers-只读查询链": 500,
    "订单-取消与预览": 600,
    "订单-Fitness签到": 610,
    "订单-Internal内部": 620,
    "Simulations-模拟核销": 700,
    "Event-事件补偿": 800,
    "其他": 900,
}

TOP_GROUP_SHEETS: Dict[str, str] = {
    "公共能力": "公共能力",
    "Membership": "Membership",
    "EPass": "EPass",
    "ESIM": "ESIM",
    "LocalOffers": "LocalOffers",
    "订单与其他": "订单与其他",
}

_PATH_MODULE_SLUG_RE = re.compile(
    r"^/v2/orders/(?P<slug>lounges|fastTrack|setMeals|coupons|fitness|esims|localOffers)/"
)

_TEMPLATE_EXPANSION: Dict[str, Tuple[str, Sequence[str]]] = {
    "/v2/orders/{module}/ePasses": ("EPass-创建验证链", EPASS_CREATE_SLUGS),
    "/v2/orders/{module}/ePasses/prebooking": ("EPass-Prebooking链", EPASS_PREBOOKING_BUNDLE_SLUGS),
    "/v2/orders/{module}/ePasses/bundle": ("EPass-Bundle链", EPASS_PREBOOKING_BUNDLE_SLUGS),
    "/v2/orders/{modules}/memberships/prebooking/preview": (
        "Membership-Prebooking链",
        MEMBERSHIP_PREBOOKING_SLUGS,
    ),
}

_FIXED_SCENARIO: Dict[Tuple[str, str], str] = {
    ("POST", "/v2/auth/token"): "公共能力-Auth鉴权",
    ("POST", "/v2/search"): "公共能力-Search搜索",
    ("GET", "/v2/search/modules"): "公共能力-Search搜索",
    ("GET", "/v2/transportHubs"): "公共能力-TransportHub",
    ("GET", "/v2/transportHubs/{transportHubId}"): "公共能力-TransportHub",
    ("GET", "/v2/resources"): "公共能力-Resources资源",
    ("GET", "/v2/resources/{resourceId}"): "公共能力-Resources资源",
    ("GET", "/v2/resources/updates"): "公共能力-Resources资源",
    ("POST", "/v2/resources/prebookings/availability"): "公共能力-Resources预约库存",
    ("POST", "/v2/resources/options/prebookings/availability"): "公共能力-Resources预约库存",
    ("POST", "/v2/resources/prices"): "公共能力-Resources资源",
    ("POST", "/v2/resources/options/prices"): "公共能力-Resources资源",
    ("GET", "/v2/resources/fitness/{resourceId}/options/{optionId}"): "公共能力-Resources资源",
    ("GET", "/v2/resources/fitness/{resourceId}/schedule"): "公共能力-Resources资源",
    ("GET", "/v2/resources/esims/{resourceId}/options"): "公共能力-Resources资源",
    ("GET", "/v2/resources/esims/{resourceId}/options/{optionId}"): "公共能力-Resources资源",
    ("GET", "/v2/resources/localOffers/{resourceId}/options"): "LocalOffers-只读查询链",
    ("GET", "/v2/resources/localOffers/{resourceId}/options/{optionId}"): "LocalOffers-只读查询链",
    ("POST", "/v2/users"): "公共能力-Users用户",
    ("POST", "/v2/users/update"): "公共能力-Users用户",
    ("POST", "/v2/users/delete"): "公共能力-Users用户",
    ("POST", "/v2/users/search"): "公共能力-Users用户",
    ("POST", "/v2/users/memberships"): "Membership-订单查询链",
    ("POST", "/v2/users/ePasses"): "EPass-创建验证链",
    ("POST", "/v2/memberships"): "Membership-创建验证链",
    ("POST", "/v2/memberships/update"): "Membership-创建验证链",
    ("POST", "/v2/memberships/search"): "Membership-创建验证链",
    ("POST", "/v2/memberships/qrCodes"): "Membership-创建验证链",
    ("POST", "/v2/memberships/programChange"): "Membership-创建验证链",
    ("POST", "/v2/entitlements/update"): "公共能力-Entitlements权益",
    ("POST", "/v2/entitlements/search"): "公共能力-Entitlements权益",
    ("POST", "/v2/entitlements/details"): "公共能力-Entitlements权益",
    ("POST", "/v2/entitlements/{entitlementPoolId}/update"): "公共能力-Entitlements权益",
    ("POST", "/v2/orders/lounges/memberships/prebooking"): "Membership-Prebooking链",
    ("POST", "/v2/orders/fastTrack/memberships/prebooking"): "Membership-Prebooking链",
    ("POST", "/v2/orders/fitness/memberships/prebooking"): "Membership-Prebooking链",
    ("POST", "/v2/orders/esims/memberships/prebooking"): "Membership-Prebooking链",
    ("POST", "/v2/orders/localOffers/memberships/prebooking"): "Membership-Prebooking链",
    ("PATCH", "/v2/orders"): "订单-取消与预览",
    ("POST", "/v2/orders/memberships"): "Membership-订单查询链",
    ("POST", "/v2/orders/memberships/details"): "Membership-订单查询链",
    ("POST", "/v2/orders/fitness/checkin"): "订单-Fitness签到",
    ("POST", "/v2/orders/esims/details"): "ESIM-EPassTopup链",
    ("POST", "/v2/orders/esims/topup/availability"): "ESIM-EPassTopup链",
    ("POST", "/v2/orders/esims/packages/query"): "ESIM-EPassTopup链",
    ("POST", "/v2/orders/esims/memberships/topup"): "ESIM-MembershipTopup链",
    ("POST", "/v2/orders/esims/ePasses/topup"): "ESIM-EPassTopup链",
    ("POST", "/v2/orders/ePasses/search"): "EPass-创建验证链",
    ("POST", "/v2/orders/ePasses"): "EPass-创建验证链",
    ("POST", "/v2/orders/ePasses/details"): "EPass-Prebooking链",
    ("POST", "/v2/internal/orders/ePasses"): "订单-Internal内部",
    ("POST", "/v2/internal/orders/memberships"): "订单-Internal内部",
    ("GET", "/v2/event"): "Event-事件补偿",
    ("POST", "/v2/simulations/lounges/redemptions"): "Simulations-模拟核销",
    ("POST", "/v2/simulations/lounges/prebookings/redemptions"): "Simulations-模拟核销",
    ("POST", "/v2/simulations/lounges/cancellation"): "Simulations-模拟核销",
    ("POST", "/v2/simulations/setMeals/redemptions"): "Simulations-模拟核销",
    ("POST", "/v2/simulations/setMeals/cancellation"): "Simulations-模拟核销",
    ("POST", "/v2/simulations/coupons/redemptions"): "Simulations-模拟核销",
    ("POST", "/v2/simulations/coupons/cancellation"): "Simulations-模拟核销",
    ("POST", "/v2/simulations/fastTrack/prebookings/redemptions"): "Simulations-模拟核销",
    ("POST", "/v2/simulations/fastTrack/cancellation"): "Simulations-模拟核销",
}


class EndpointCatalogEntry:
    """单条导出条目（含展开后的 concrete path 与 module 赋值）。"""

    __slots__ = (
        "template_path",
        "concrete_path",
        "method",
        "summary",
        "scenario",
        "top_group",
        "module_slug",
        "module_int",
        "module_display",
        "sort_key",
    )

    def __init__(
        self,
        template_path: str,
        concrete_path: str,
        method: str,
        summary: str,
        scenario: str,
        module_slug: Optional[str],
        module_int: Optional[int],
        module_display: Optional[str],
    ) -> None:
        self.template_path = template_path
        self.concrete_path = concrete_path
        self.method = method.upper()
        self.summary = summary
        self.scenario = scenario
        self.top_group = _TopGroup(scenario)
        self.module_slug = module_slug
        self.module_int = module_int
        self.module_display = module_display
        slug_order = module_int if module_int is not None else 999
        self.sort_key = (
            SCENARIO_ORDER.get(scenario, 999),
            slug_order,
            concrete_path,
            self.method,
        )

    def BuildModuleColumn(self) -> str:
        if self.module_slug and self.module_int is not None:
            return (
                f"{self.scenario} · {self.module_display}"
                f"（pathModule={self.module_slug}, module={self.module_int}）"
            )
        if self.module_slug:
            return f"{self.scenario} · {self.module_display}（pathModule={self.module_slug}）"
        return self.scenario

    def BuildDetailSuffix(self) -> str:
        if self.module_slug and self.module_int is not None:
            return f" [pathModule={self.module_slug}, body.module={self.module_int}]"
        return ""


def _TopGroup(scenario: str) -> str:
    if scenario.startswith("公共能力"):
        return "公共能力"
    if scenario.startswith("Membership"):
        return "Membership"
    if scenario.startswith("EPass"):
        return "EPass"
    if scenario.startswith("ESIM"):
        return "ESIM"
    if scenario.startswith("LocalOffers"):
        return "LocalOffers"
    return "订单与其他"


def _SlugFromFixedPath(path: str) -> Optional[str]:
    match = _PATH_MODULE_SLUG_RE.match(path)
    if not match:
        return None
    return match.group("slug")


def BuildCatalogEntries(path: str, method: str, summary: str) -> List[EndpointCatalogEntry]:
    """为 OAS 单条 path+method 生成 catalog 条目（含 {module} 展开）。"""
    rule = _TEMPLATE_EXPANSION.get(path)
    if rule is None:
        scenario = _FIXED_SCENARIO.get((method.upper(), path), "其他")
        slug = _SlugFromFixedPath(path)
        variant = MODULE_VARIANTS.get(slug) if slug else None
        return [
            EndpointCatalogEntry(
                template_path=path,
                concrete_path=path,
                method=method,
                summary=summary,
                scenario=scenario,
                module_slug=variant[0] if variant else slug,
                module_int=variant[1] if variant else None,
                module_display=variant[2] if variant else None,
            )
        ]
    scenario, slugs = rule
    entries: List[EndpointCatalogEntry] = []
    for slug in slugs:
        variant = MODULE_VARIANTS[slug]
        concrete = path.replace("{module}", slug).replace("{modules}", slug)
        entries.append(
            EndpointCatalogEntry(
                template_path=path,
                concrete_path=concrete,
                method=method,
                summary=summary,
                scenario=scenario,
                module_slug=variant[0],
                module_int=variant[1],
                module_display=variant[2],
            )
        )
    return entries
