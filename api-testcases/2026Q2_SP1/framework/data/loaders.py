"""
CSV 测试数据加载器：在 ``DP_PROFILE`` 选环境的基础上，用 ``DP_TEST_DATASET`` 选择该环境下的一行业务数据。
"""
from __future__ import annotations

import csv
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Final, Mapping, Optional, Sequence

JsonDict = Dict[str, Any]

_DEFAULT_DATASET_KEY: Final[str] = "default"


@dataclass(frozen=True)
class MembershipRegisterCsvRow:
    dataset_key: str = _DEFAULT_DATASET_KEY
    first_name: str = ""
    last_name: str = ""
    phone_number: str = ""
    calling_code: str = ""
    email_prefix: str = ""
    expiration_date: str = ""
    program_id_override: str = ""
    register_extra_json: Optional[JsonDict] = None


@dataclass(frozen=True)
class P2515DatasetCsvRow:
    dataset_key: str = _DEFAULT_DATASET_KEY
    probe_membership_id: str = ""
    register_extra_json: Optional[JsonDict] = None
    module_update_json: Optional[JsonDict] = None
    update_module: str = ""
    update_tier: Optional[int] = None
    update_usage_restriction: Optional[int] = None
    update_quantity: Optional[int] = None
    pool_quantity: Optional[int] = None
    pool_purchased_quantity: Optional[int] = None
    summary_guest_key_allowed: str = ""
    summary_guest_key_max: str = ""


@dataclass(frozen=True)
class P2424DatasetCsvRow:
    dataset_key: str = _DEFAULT_DATASET_KEY
    usage_order_id: str = ""
    v1_path: str = ""
    v2_path: str = ""
    ms_prefix_case_insensitive: Optional[bool] = None


def SuiteRoot() -> Path:
    return Path(__file__).resolve().parents[2]


def TestDataRoot() -> Path:
    return SuiteRoot() / "testdata"


def CurrentProfile() -> str:
    profile = os.environ.get("DP_PROFILE", "").strip()
    return profile if profile else "default"


def CurrentDatasetKey() -> str:
    key = os.environ.get("DP_TEST_DATASET", "").strip()
    return key if key else _DEFAULT_DATASET_KEY


def DatasetExplicitlySelected() -> bool:
    return bool(os.environ.get("DP_TEST_DATASET", "").strip())


def ProfileCsvPath(csv_name: str) -> Path:
    return TestDataRoot() / CurrentProfile() / csv_name


def NormalizeRow(row: Mapping[str, Any]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for key, value in row.items():
        clean_key = str(key).strip()
        if not clean_key:
            continue
        out[clean_key] = "" if value is None else str(value).strip()
    return out


def ReadCsvRows(path: Path) -> Sequence[Dict[str, str]]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                raise RuntimeError(f"CSV 缺少表头: {path}")
            if "datasetKey" not in reader.fieldnames:
                raise RuntimeError(f"CSV 缺少必填列 datasetKey: {path}")
            return [NormalizeRow(row) for row in reader]
    except OSError as exc:
        raise RuntimeError(f"读取 CSV 失败: {path} ({exc})") from exc
    except csv.Error as exc:
        raise RuntimeError(f"解析 CSV 失败: {path} ({exc})") from exc


def LocateCsvRow(csv_name: str) -> Mapping[str, str]:
    path = ProfileCsvPath(csv_name)
    if not path.is_file():
        if DatasetExplicitlySelected():
            raise RuntimeError(
                f"未找到测试数据文件: {path}。当前 DP_PROFILE={CurrentProfile()!r}, "
                f"DP_TEST_DATASET={CurrentDatasetKey()!r}"
            )
        return {}
    rows = ReadCsvRows(path)
    dataset_key = CurrentDatasetKey()
    default_row: Optional[Mapping[str, str]] = None
    for row in rows:
        row_key = row.get("datasetKey", "").strip()
        if row_key == dataset_key:
            return row
        if row_key == _DEFAULT_DATASET_KEY:
            default_row = row
    if default_row is not None:
        return default_row
    if DatasetExplicitlySelected():
        raise RuntimeError(
            f"CSV {path} 中未找到 datasetKey={dataset_key!r}，且也没有 default 行。"
        )
    return {}


def ParseOptionalJsonObject(
    row: Mapping[str, str],
    *,
    field_name: str,
    csv_name: str,
) -> Optional[JsonDict]:
    raw = row.get(field_name, "").strip()
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{csv_name}.{field_name} 不是合法 JSON 对象: {exc}") from exc
    if not isinstance(parsed, dict):
        raise RuntimeError(f"{csv_name}.{field_name} 必须为 JSON 对象，实际={type(parsed).__name__}")
    return dict(parsed)


def ParseOptionalInt(
    row: Mapping[str, str],
    *,
    field_name: str,
    csv_name: str,
) -> Optional[int]:
    raw = row.get(field_name, "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{csv_name}.{field_name} 不是合法整数: {raw!r}") from exc


def ParseOptionalBool(
    row: Mapping[str, str],
    *,
    field_name: str,
    csv_name: str,
) -> Optional[bool]:
    raw = row.get(field_name, "").strip().lower()
    if not raw:
        return None
    if raw in ("1", "true", "yes", "on"):
        return True
    if raw in ("0", "false", "no", "off"):
        return False
    raise RuntimeError(f"{csv_name}.{field_name} 不是合法布尔值: {raw!r}")


def LoadMembershipRegisterCsvRow() -> MembershipRegisterCsvRow:
    csv_name = "membership_register.csv"
    row = LocateCsvRow(csv_name)
    if not row:
        return MembershipRegisterCsvRow()
    return MembershipRegisterCsvRow(
        dataset_key=row.get("datasetKey", _DEFAULT_DATASET_KEY) or _DEFAULT_DATASET_KEY,
        first_name=row.get("firstName", "").strip(),
        last_name=row.get("lastName", "").strip(),
        phone_number=row.get("phoneNumber", "").strip(),
        calling_code=row.get("callingCode", "").strip(),
        email_prefix=row.get("emailPrefix", "").strip(),
        expiration_date=row.get("expirationDate", "").strip(),
        program_id_override=row.get("programIdOverride", "").strip(),
        register_extra_json=ParseOptionalJsonObject(row, field_name="registerExtraJson", csv_name=csv_name),
    )


def LoadP2515DatasetCsvRow() -> P2515DatasetCsvRow:
    csv_name = "p2515_dataset.csv"
    row = LocateCsvRow(csv_name)
    if not row:
        return P2515DatasetCsvRow()
    return P2515DatasetCsvRow(
        dataset_key=row.get("datasetKey", _DEFAULT_DATASET_KEY) or _DEFAULT_DATASET_KEY,
        probe_membership_id=row.get("probeMembershipId", "").strip(),
        register_extra_json=ParseOptionalJsonObject(row, field_name="registerExtraJson", csv_name=csv_name),
        module_update_json=ParseOptionalJsonObject(row, field_name="moduleUpdateJson", csv_name=csv_name),
        update_module=row.get("updateModule", "").strip(),
        update_tier=ParseOptionalInt(row, field_name="updateTier", csv_name=csv_name),
        update_usage_restriction=ParseOptionalInt(row, field_name="updateUsageRestriction", csv_name=csv_name),
        update_quantity=ParseOptionalInt(row, field_name="updateQuantity", csv_name=csv_name),
        pool_quantity=ParseOptionalInt(row, field_name="poolQuantity", csv_name=csv_name),
        pool_purchased_quantity=ParseOptionalInt(row, field_name="poolPurchasedQuantity", csv_name=csv_name),
        summary_guest_key_allowed=row.get("summaryGuestKeyAllowed", "").strip(),
        summary_guest_key_max=row.get("summaryGuestKeyMax", "").strip(),
    )


def LoadP2424DatasetCsvRow() -> P2424DatasetCsvRow:
    csv_name = "p2424_dataset.csv"
    row = LocateCsvRow(csv_name)
    if not row:
        return P2424DatasetCsvRow()
    return P2424DatasetCsvRow(
        dataset_key=row.get("datasetKey", _DEFAULT_DATASET_KEY) or _DEFAULT_DATASET_KEY,
        usage_order_id=row.get("usageOrderId", "").strip(),
        v1_path=row.get("v1Path", "").strip(),
        v2_path=row.get("v2Path", "").strip(),
        ms_prefix_case_insensitive=ParseOptionalBool(
            row,
            field_name="msPrefixCaseInsensitive",
            csv_name=csv_name,
        ),
    )


def ResolveMembershipProgramIdOverride() -> str:
    row = LoadMembershipRegisterCsvRow()
    return row.program_id_override.strip()
