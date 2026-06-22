"""各 API 端点专属检查点与预期结果（供 export_api_main_testcase_xlsx 使用）。

键为 ``(path, method)``，method 为大写 HTTP 动词。
"""

from __future__ import annotations

import re
from typing import Dict, Tuple

EndpointKey = Tuple[str, str]
HintPair = Tuple[str, str]

_PATH_SLUG_TO_TEMPLATE_RE = re.compile(
    r"^/v2/orders/(?:lounges|fastTrack|setMeals|coupons|fitness|esims|localOffers)(?=/|$)"
)

ENDPOINT_HINTS: Dict[EndpointKey, HintPair] = {
    ("POST", "/v2/auth/token"): (
        "使用有效 clientId、clientSecret 及 grantType=client_credentials 请求 Token",
        "返回 HTTP 200，code=0；data 含 accessToken、tokenType、expiresIn，Token 可用于后续接口 Bearer 鉴权",
    ),
    ("POST", "/v2/search"): (
        "携带有效 Token，按 keyword 及 location 等条件发起聚合搜索",
        "返回 HTTP 200，code=0；results 按 module 分组返回匹配资源/枢纽，字段与 Apifox 定义一致",
    ),
    ("GET", "/v2/search/modules"): (
        "携带有效 Token，传入 location（如 IATA/坐标）查询可用 module 列表",
        "返回 HTTP 200，code=0；data 列出当前位置可用的 module 枚举及说明",
    ),
    ("GET", "/v2/transportHubs"): (
        "携带有效 Token，按 iata/countryOrRegion 等条件查询交通枢纽列表",
        "返回 HTTP 200，code=0；返回 transportHubs 列表，每条含 transportHubId、名称及位置信息",
    ),
    ("GET", "/v2/transportHubs/{transportHubId}"): (
        "携带有效 Token，使用有效 transportHubId 查询枢纽详情",
        "返回 HTTP 200，code=0；data 含枢纽完整详情，transportHubId 与入参一致",
    ),
    ("GET", "/v2/resources"): (
        "携带有效 Token，按 module、iata、language 等筛选条件查询资源列表",
        "返回 HTTP 200，code=0；resources 数组中每条含 resourceId、module、名称等核心字段，符合筛选条件",
    ),
    ("GET", "/v2/resources/{resourceId}"): (
        "携带有效 Token，使用有效 resourceId 查询单个资源详情",
        "返回 HTTP 200，code=0；data 含资源完整信息，resourceId 与入参一致",
    ),
    ("POST", "/v2/resources/prebookings/availability"): (
        "携带有效 Token，传入 resourceId、module、预约日期时段等查询资源可预约库存",
        "返回 HTTP 200，code=0；返回指定时段 availability 状态及可预约数量/时段列表",
    ),
    ("POST", "/v2/resources/options/prebookings/availability"): (
        "携带有效 Token，传入 resourceId、optionId 及预约时段查询 Option 级可预约库存",
        "返回 HTTP 200，code=0；返回 option 维度 availability，可区分不同 option 的库存差异",
    ),
    ("GET", "/v2/resources/fitness/{resourceId}/options/{optionId}"): (
        "携带有效 Token，查询指定 Fitness 资源的 Option 详情",
        "返回 HTTP 200，code=0；data 含 optionId、课程/场次信息及预约相关字段",
    ),
    ("GET", "/v2/resources/fitness/{resourceId}/schedule"): (
        "携带有效 Token，查询指定 Fitness 资源的排期/课表",
        "返回 HTTP 200，code=0；返回 schedule 列表，含可预约时段及 option 关联信息",
    ),
    ("GET", "/v2/resources/esims/{resourceId}/options"): (
        "携带有效 Token，查询 eSIM 资源下全部套餐 Option 列表",
        "返回 HTTP 200，code=0；options 列表含 optionId、流量/有效期等套餐描述字段",
    ),
    ("GET", "/v2/resources/esims/{resourceId}/options/{optionId}"): (
        "携带有效 Token，查询 eSIM 资源单个 Option 详情",
        "返回 HTTP 200，code=0；data 含 optionId 及套餐明细，与列表接口字段一致",
    ),
    ("GET", "/v2/resources/localOffers/{resourceId}/options"): (
        "携带有效 Token，查询 Local Offer 资源下 Option 列表",
        "返回 HTTP 200，code=0；options 含 optionId、local offer 品类及可用性相关字段",
    ),
    ("GET", "/v2/resources/localOffers/{resourceId}/options/{optionId}"): (
        "携带有效 Token，查询 Local Offer 单个 Option 详情",
        "返回 HTTP 200，code=0；data 含 optionId、预约规则及价格相关字段",
    ),
    ("POST", "/v2/resources/prices"): (
        "携带有效 Token，传入 resourceId、module、usage 场景查询资源 Walk-in 价格",
        "返回 HTTP 200，code=0；返回 pricing 信息，含币种、单价/扣点等计费字段",
    ),
    ("POST", "/v2/resources/options/prices"): (
        "携带有效 Token，传入 resourceId、optionId 及预约场景查询 Option 预约价格",
        "返回 HTTP 200，code=0；返回 prebooking 价格明细，与所选 option 匹配",
    ),
    ("GET", "/v2/resources/updates"): (
        "携带有效 Token，按 since/时间戳查询自某时间点以来有变更的资源列表",
        "返回 HTTP 200，code=0；仅返回变更过的 resourceId 及变更类型/时间，便于增量同步",
    ),
    ("POST", "/v2/users"): (
        "携带有效 Token 及 X-Request-ID，传入 clientUserId 等必填字段创建用户",
        "返回 HTTP 200，code=0；成功创建用户，clientUserId 与入参一致且可后续查询",
    ),
    ("POST", "/v2/users/update"): (
        "携带有效 Token，对已存在 clientUserId 更新用户信息",
        "返回 HTTP 200，code=0；更新字段生效，再次 search 可查到最新信息",
    ),
    ("POST", "/v2/users/delete"): (
        "携带有效 Token，对有效 clientUserId 发起删除",
        "返回 HTTP 200，code=0；用户标记删除/不可再用，后续 search 符合删除后状态",
    ),
    ("POST", "/v2/users/search"): (
        "携带有效 Token，按 clientUserId 查询用户信息",
        "返回 HTTP 200，code=0；data 含 clientUserId 及用户 profile 字段，与注册/更新一致",
    ),
    ("POST", "/v2/users/memberships"): (
        "携带有效 Token，按 clientUserId 查询其名下会籍列表",
        "返回 HTTP 200，code=0；memberships 列表含 membershipId、program、状态等字段",
    ),
    ("POST", "/v2/users/ePasses"): (
        "携带有效 Token，按 clientUserId 查询其名下 E-pass 列表",
        "返回 HTTP 200，code=0；ePasses 列表含 ePassId、module、availableUsages、ePassStatus 等",
    ),
    ("POST", "/v2/memberships"): (
        "携带有效 Token 及 X-Request-ID，传入 clientUserId、programId、姓名等注册会籍",
        "返回 HTTP 200，code=0；data 含 membershipId、activationDate/expirationDate，会籍状态为有效",
    ),
    ("POST", "/v2/memberships/update"): (
        "携带有效 Token，对有效 membershipId 更新会籍信息（姓名、有效期等）",
        "返回 HTTP 200，code=0；更新字段生效，search 会籍可验证变更",
    ),
    ("POST", "/v2/memberships/search"): (
        "携带有效 Token，按 membershipId 或 clientUserId 查询会籍详情",
        "返回 HTTP 200，code=0；data 含 membershipId、program、状态、有效期等完整会籍信息",
    ),
    ("POST", "/v2/memberships/qrCodes"): (
        "携带有效 Token，对有效 membershipId 生成动态 QR Code",
        "返回 HTTP 200，code=0；返回 QR 内容/图片数据，可用于核销场景且有时效性",
    ),
    ("POST", "/v2/memberships/programChange"): (
        "携带有效 Token，对已注册会籍发起升/降级 programChange",
        "返回 HTTP 200，code=0；会籍 program/权益模板切换成功，search 可见新 program 信息",
    ),
    ("POST", "/v2/entitlements/update"): (
        "携带有效 Token，对指定会籍更新权益配额（如可用次数、有效期）",
        "返回 HTTP 200，code=0；权益变更生效，search/details 可验证更新后 entitlement 值",
    ),
    ("POST", "/v2/entitlements/search"): (
        "携带有效 Token，按 membershipId 查询权益概览 Summary",
        "返回 HTTP 200，code=0；返回各 module 权益汇总，含 remaining/total 等汇总字段",
    ),
    ("POST", "/v2/entitlements/details"): (
        "携带有效 Token，按 membershipId 查询权益明细 Details",
        "返回 HTTP 200，code=0；返回 entitlement 明细列表，含 entitlementPoolId、用量及规则字段",
    ),
    ("POST", "/v2/entitlements/{entitlementPoolId}/update"): (
        "携带有效 Token，按 entitlementPoolId 精确更新单条权益池",
        "返回 HTTP 200，code=0；指定 pool 权益变更成功，details 中该 pool 数据已更新",
    ),
    ("POST", "/v2/orders/{modules}/memberships/prebooking/preview"): (
        "携带有效 Token，传入 module、resourceId、预约时段等预览 Membership 预约订单",
        "返回 HTTP 200，code=0；返回预览价、扣点/支付金额及订单摘要，未实际落单",
    ),
    ("POST", "/v2/orders/lounges/memberships/prebooking"): (
        "携带有效 Token 及 X-Request-ID，用有效会籍创建 Lounge 预约订单",
        "返回 HTTP 200，code=0；data 含 orderId、status=Confirmed，module=1，category=Prebooking",
    ),
    ("POST", "/v2/orders/fastTrack/memberships/prebooking"): (
        "携带有效 Token 及 X-Request-ID，用有效会籍创建 Fast Track 预约订单",
        "返回 HTTP 200，code=0；data 含 orderId、voucher/预约凭证字段，module=2",
    ),
    ("POST", "/v2/orders/fitness/memberships/prebooking"): (
        "携带有效 Token 及 X-Request-ID，用有效会籍创建 Fitness 预约订单",
        "返回 HTTP 200，code=0；data 含 orderId 及 fitness 预约时段/option 信息",
    ),
    ("POST", "/v2/orders/esims/memberships/prebooking"): (
        "携带有效 Token 及 X-Request-ID，用有效会籍创建 eSIM/LO 预约类订单",
        "返回 HTTP 200，code=0；data 含 orderId 及 eSIM 套餐/激活相关 extra 字段",
    ),
    ("POST", "/v2/orders/localOffers/memberships/prebooking"): (
        "携带有效 Token 及 X-Request-ID，用有效会籍创建 Local Offer 预约订单",
        "返回 HTTP 200，code=0；data 含 orderId，module=11，category 为预约类型",
    ),
    ("POST", "/v2/orders/esims/memberships/topup"): (
        "携带有效 Token，对已购 eSIM 会籍订单发起流量包 Top-up",
        "返回 HTTP 200，code=0；topup 订单创建成功，原 eSIM 订单流量/套餐信息更新",
    ),
    ("PATCH", "/v2/orders"): (
        "携带有效 Token，对有效 orderId 发起取消（Cancel）",
        "返回 HTTP 200，code=0；订单 status 变为 Cancelled，orderCancelledDate 非空",
    ),
    ("POST", "/v2/orders/memberships"): (
        "携带有效 Token，按 membershipId/时间范围查询 Membership 订单列表",
        "返回 HTTP 200，code=0；orders 列表含 orderId、module、status、创建时间等",
    ),
    ("POST", "/v2/orders/memberships/details"): (
        "携带有效 Token，按 orderId 查询 Membership 使用/预约订单详情",
        "返回 HTTP 200，code=0；data 含完整订单字段、extra 及核销/预约状态",
    ),
    ("POST", "/v2/internal/orders/memberships"): (
        "携带内部鉴权，按条件查询 Membership 订单列表（Internal 口径）",
        "返回 HTTP 200，code=0；返回内部可见字段更全的订单列表，与普通列表接口字段范围一致或扩展",
    ),
    ("POST", "/v2/orders/fitness/checkin"): (
        "携带有效 Token，对已预约 Fitness 订单执行 Check-In",
        "返回 HTTP 200，code=0；订单状态更新为已签到/已使用，checkin 时间写入",
    ),
    ("POST", "/v2/orders/esims/details"): (
        "携带有效 Token，按 orderId 查询 eSIM 订单实时扩展详情（Live Extended）",
        "返回 HTTP 200，code=0；data 含 ICCID、流量用量、套餐状态等 live 字段",
    ),
    ("POST", "/v2/orders/esims/topup/availability"): (
        "携带有效 Token，查询指定 eSIM 订单是否可 Top-up 及可选套餐",
        "返回 HTTP 200，code=0；返回 available 标志及可购 topup packages 列表",
    ),
    ("POST", "/v2/orders/esims/packages/query"): (
        "携带有效 Token，查询 eSIM 可购流量包/Data Packages 列表",
        "返回 HTTP 200，code=0；packages 含 packageId、流量、价格等字段",
    ),
    ("POST", "/v2/orders/{module}/ePasses"): (
        "携带有效 Token 及 X-Request-ID，path module 与 body module 一致，创建 E-pass 订单",
        "返回 HTTP 200，code=0；data 含 orderId、ePassId、availableUsages、usedUsages=0，module/category 与入参一致",
    ),
    ("POST", "/v2/orders/ePasses/search"): (
        "携带有效 Token，按 ePassId 或 clientUserId 查询 E-pass 详情",
        "返回 HTTP 200，code=0；data 含 ePassId、状态、可用次数及 allowedResources",
    ),
    ("POST", "/v2/orders/{module}/ePasses/prebooking"): (
        "携带有效 Token 及 X-Request-ID，用 E-pass 创建预约订单（Local Offer/eSIM 等 module）",
        "返回 HTTP 200，code=0；data 含 orderId、预约凭证字段，E-pass availableUsages 相应扣减",
    ),
    ("POST", "/v2/orders/{module}/ePasses/bundle"): (
        "携带有效 Token 及 X-Request-ID，E-pass 下单同时绑定预约（Bundle）",
        "返回 HTTP 200，code=0；同时返回 E-pass 与 prebooking 订单关联信息，两笔业务一次完成",
    ),
    ("POST", "/v2/orders/esims/ePasses/topup"): (
        "携带有效 Token，对已发 E-pass 关联 eSIM 发起流量 Top-up",
        "返回 HTTP 200，code=0；topup 成功，ePass/eSIM 流量或套餐字段更新",
    ),
    ("POST", "/v2/orders/ePasses"): (
        "携带有效 Token，按 clientUserId/条件查询 E-pass 订单列表",
        "返回 HTTP 200，code=0；orders 列表含 orderId、module、ePassId、status 等",
    ),
    ("POST", "/v2/orders/ePasses/details"): (
        "携带有效 Token，按 orderId 查询 E-pass 使用/核销订单详情",
        "返回 HTTP 200，code=0；data 含订单状态、核销时间、ePass 扣次等 usage 明细",
    ),
    ("POST", "/v2/internal/orders/ePasses"): (
        "携带内部鉴权，按条件查询 E-pass 订单列表（Internal 口径）",
        "返回 HTTP 200，code=0；返回内部可见字段更全的 E-pass 订单列表",
    ),
    ("GET", "/v2/event"): (
        "携带有效 Token，按 eventId/恢复参数拉取 Push Event 补偿数据",
        "返回 HTTP 200，code=0；返回待恢复的事件 payload，可用于 webhook 漏推补偿",
    ),
    ("POST", "/v2/simulations/lounges/redemptions"): (
        "测试环境模拟 Lounge Walk-in 核销",
        "返回 HTTP 200，code=0；模拟核销成功，关联订单 status 变为 Used",
    ),
    ("POST", "/v2/simulations/lounges/prebookings/redemptions"): (
        "测试环境模拟 Lounge 预约单核销",
        "返回 HTTP 200，code=0；预约订单核销成功，voucher 状态更新",
    ),
    ("POST", "/v2/simulations/lounges/cancellation"): (
        "测试环境模拟 Lounge 订单取消",
        "返回 HTTP 200，code=0；订单变为 Cancelled，释放库存/权益",
    ),
    ("POST", "/v2/simulations/setMeals/redemptions"): (
        "测试环境模拟 Set Meal Walk-in 核销",
        "返回 HTTP 200，code=0；模拟核销成功，订单 status 变为 Used",
    ),
    ("POST", "/v2/simulations/setMeals/cancellation"): (
        "测试环境模拟 Set Meal 订单取消",
        "返回 HTTP 200，code=0；订单变为 Cancelled",
    ),
    ("POST", "/v2/simulations/coupons/redemptions"): (
        "测试环境模拟 Dining Coupon Walk-in 核销",
        "返回 HTTP 200，code=0；模拟核销成功，优惠券订单 status 变为 Used",
    ),
    ("POST", "/v2/simulations/coupons/cancellation"): (
        "测试环境模拟 Dining Coupon 订单取消",
        "返回 HTTP 200，code=0；订单变为 Cancelled",
    ),
    ("POST", "/v2/simulations/fastTrack/prebookings/redemptions"): (
        "测试环境模拟 Fast Track 预约单核销",
        "返回 HTTP 200，code=0；预约订单核销成功，status 变为 Used",
    ),
    ("POST", "/v2/simulations/fastTrack/cancellation"): (
        "测试环境模拟 Fast Track 订单取消",
        "返回 HTTP 200，code=0；订单变为 Cancelled",
    ),
}


def _NormalizePathForHint(path: str) -> str:
    """将展开后的 concrete path 还原为 OAS 模板 path 以便命中 hints。"""
    if not _PATH_SLUG_TO_TEMPLATE_RE.match(path):
        return path
    parts = path.split("/")
    if len(parts) < 4:
        return path
    placeholder = "{modules}" if path.endswith("/memberships/prebooking/preview") else "{module}"
    parts[3] = placeholder
    return "/".join(parts)


def GetCheckpointAndExpected(path: str, method: str, summary: str) -> HintPair:
    """按 path+method 取专属文案；未命中时基于 summary 生成兜底（仍尽量具体）。"""
    template_path = _NormalizePathForHint(path)
    key: EndpointKey = (method.upper(), template_path)
    hint = ENDPOINT_HINTS.get(key)
    if hint is not None:
        return hint
    key_raw: EndpointKey = (method.upper(), path)
    hint = ENDPOINT_HINTS.get(key_raw)
    if hint is not None:
        return hint
    action = summary.strip() if summary else f"{method} {path}"
    checkpoint = f"携带有效 Token 及必填参数，执行 {action}"
    expected = f"返回 HTTP 200，code=0；响应满足 {action} 业务语义，核心字段与 Apifox 一致"
    return checkpoint, expected
