"""
E-pass Collection 域配置与跨品类公共工厂。

本模块不依赖任何 ``GeneratePostmanCollection*.py``，只描述 FT / Lounge /
Fitness / eSIM 的稳定品类参数，并提供创建 ePass payload 与运行时 JS 公共块。
品类生成器可以保留自身差异 hook，但不得反向成为公共模块的依赖。
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Dict, Final, List, Literal, Optional, Tuple

from collection_builder_common import (
    JsRuntimeIdCaptureHelpersBlock,
    JsRuntimeVarScopeHelpersBlock,
)

JsonObject = Dict[str, object]
EpassCategoryKind = Literal["fastTrack", "lounge", "fitness", "esim"]

CREATE_FIRST_NAME: Final[str] = "Auto"
CREATE_LAST_NAME: Final[str] = "Test"
CREATE_EXPIRATION_DATE: Final[str] = "2028-12-31T23:59:59+00:00"
DEFAULT_CREATE_AVAILABLE_USAGES: Final[int] = 2
OTHER_MODULE_DEFAULT: Final[int] = 11


@dataclass(frozen=True)
class EpassCategoryConfig:
    """E-pass 主链路中可参数化且跨生成器稳定的品类配置。"""

    key: EpassCategoryKind
    label: str
    path_segment: str
    module: int
    resource_var: str
    default_resource_id: str
    runtime_prefix: str
    available_usages: int = DEFAULT_CREATE_AVAILABLE_USAGES
    option_var: Optional[str] = None
    supports_passengers: bool = False

    def OrdersBasePath(self) -> str:
        return f"/v2/orders/{self.path_segment}/ePasses"


@dataclass(frozen=True)
class EpassChainPaths:
    """E-pass 创建、预约与 Bundle 主链路路径。"""

    create: str
    prebooking: str
    bundle: str
    users: str = "/v2/users/ePasses"
    orders: str = "/v2/orders/ePasses"
    details: str = "/v2/orders/ePasses/details"


@dataclass(frozen=True)
class EpassRequestSpec:
    """主链路请求的稳定 method/path 规格，不承载品类特有 body 或断言。"""

    method: Literal["POST", "PATCH"]
    path: str


EPASS_CATEGORY_CONFIGS: Final[Dict[EpassCategoryKind, EpassCategoryConfig]] = {
    "fastTrack": EpassCategoryConfig(
        key="fastTrack",
        label="Fast Track",
        path_segment="fastTrack",
        module=2,
        resource_var="fastTrackResourceId",
        default_resource_id="C10826",
        runtime_prefix="ft",
        supports_passengers=True,
    ),
    "lounge": EpassCategoryConfig(
        key="lounge",
        label="Lounge",
        path_segment="lounges",
        module=1,
        resource_var="loungeResourceId",
        default_resource_id="N00012",
        runtime_prefix="lp",
    ),
    "fitness": EpassCategoryConfig(
        key="fitness",
        label="Fitness",
        path_segment="fitness",
        module=7,
        resource_var="fitnessResourceId",
        default_resource_id="GR0000308",
        runtime_prefix="fp",
        option_var="fitnessOptionId",
    ),
    "esim": EpassCategoryConfig(
        key="esim",
        label="eSIM",
        path_segment="esims",
        module=8,
        resource_var="esimResourceId",
        default_resource_id="GR0005901",
        runtime_prefix="ep",
        available_usages=1,
        option_var="esimOptionId",
    ),
}


def GetEpassCategoryConfig(key: EpassCategoryKind) -> EpassCategoryConfig:
    """返回不可变品类配置；未知 key 明确报错。"""
    try:
        return EPASS_CATEGORY_CONFIGS[key]
    except KeyError as exc:
        raise ValueError(
            f"未知 E-pass 品类 key={key!r}；可选 {sorted(EPASS_CATEGORY_CONFIGS)}"
        ) from exc


def BuildEpassCreatePayload(
    config: EpassCategoryConfig,
    *,
    available_usages: Optional[int] = None,
) -> str:
    """构造各品类同构的创建 ePass 请求体。"""
    usages = config.available_usages if available_usages is None else int(available_usages)
    if usages < 1:
        raise ValueError(f"available_usages 须 >= 1，实际={usages}")
    payload: JsonObject = {
        "module": config.module,
        "clientUserId": "{{$string.uuid}}",
        "extra": {
            "firstName": CREATE_FIRST_NAME,
            "lastName": CREATE_LAST_NAME,
            "expirationDate": CREATE_EXPIRATION_DATE,
            "availableUsages": usages,
            "allowedResources": {
                "resourceIds": [],
                "iata": [],
                "countryOrRegion": [],
            },
        },
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def BuildEpassChainPaths(config: EpassCategoryConfig) -> EpassChainPaths:
    """由品类 path 段构造稳定的 E-pass 主链路路径。"""
    base = config.OrdersBasePath()
    return EpassChainPaths(
        create=base,
        prebooking=f"{base}/prebooking",
        bundle=f"{base}/bundle",
    )


def BuildEpassMainChainRequestSpecs(
    config: EpassCategoryConfig,
) -> Dict[str, EpassRequestSpec]:
    """构造 E01/E02/E03 共用请求规格，供 FT 与 Lounge 编排入口消费。"""
    paths = BuildEpassChainPaths(config)
    return {
        "create": EpassRequestSpec("POST", paths.create),
        "users": EpassRequestSpec("POST", paths.users),
        "orders": EpassRequestSpec("POST", paths.orders),
        "details": EpassRequestSpec("POST", paths.details),
        "availability": EpassRequestSpec(
            "POST",
            "/v2/resources/prebookings/availability",
        ),
        "prebooking": EpassRequestSpec("POST", paths.prebooking),
        "bundle": EpassRequestSpec("POST", paths.bundle),
        "cancel": EpassRequestSpec("PATCH", "/v2/orders"),
    }


def JsAssertRuntimeClientUserIdEquals(
    *,
    prefix: str,
    actual_expression: str,
    indent: str = "    ",
) -> str:
    """生成 clientUserId 与 runtime 单一来源比对的 JS 断言行。"""
    if not prefix or not prefix.replace("_", "").isalnum():
        raise ValueError(f"非法 JS helper prefix={prefix!r}")
    if not actual_expression.strip():
        raise ValueError("actual_expression 不能为空")
    return (
        f"{indent}pm.expect({actual_expression}).to.eql("
        f"{prefix}GetVar('clientUserId'));"
    )


def BuildEpassRuntimeHelpersBlock(
    config: EpassCategoryConfig,
    *,
    extra_unset_env_keys: Tuple[str, ...] = (),
) -> str:
    """生成跨品类唯一来源的变量作用域与 runtime ID 捕获 JS。"""
    keys: List[str] = [config.resource_var]
    if config.option_var:
        keys.append(config.option_var)
    keys.extend(extra_unset_env_keys)
    return (
        JsRuntimeVarScopeHelpersBlock(
            prefix=config.runtime_prefix,
            extra_unset_env_keys=tuple(keys),
        )
        + JsRuntimeIdCaptureHelpersBlock(prefix=config.runtime_prefix)
    )


def BuildEpassExpectedModuleHelpersBlock(
    config: EpassCategoryConfig,
    *,
    other_module: int = OTHER_MODULE_DEFAULT,
) -> str:
    """生成 module/otherModule 断言读取函数，保留各品类 JS 前缀。"""
    prefix = config.runtime_prefix
    expected = json.dumps(config.module)
    other = json.dumps(int(other_module))
    return rf"""function {prefix}ExpectedModule() {{
  var raw = pm.collectionVariables.get('epassModule');
  if (raw === undefined || raw === null || String(raw).trim() === '') {{
    return {expected};
  }}
  var n = parseInt(String(raw), 10);
  return isNaN(n) ? {expected} : n;
}}
function {prefix}OtherModule() {{
  var raw = pm.collectionVariables.get('otherModule');
  if (raw === undefined || raw === null || String(raw).trim() === '') {{
    return {other};
  }}
  var n = parseInt(String(raw), 10);
  return isNaN(n) ? {other} : n;
}}
"""
