"""一次性脚本：从 lounge 生成器派生 fastTrack 生成器。"""
from __future__ import annotations

import re
from pathlib import Path

SRC = Path(__file__).with_name("GeneratePostmanCollectionLoungeEpass.py")
OUT = Path(__file__).with_name("GeneratePostmanCollectionFastTrackEpass.py")


def Main() -> None:
    src = SRC.read_text(encoding="utf-8")
    pairs = [
        ("GeneratePostmanCollectionLoungeEpassV1.py", "GeneratePostmanCollectionFastTrackEpass.py"),
        ("GeneratePostmanCollectionLoungeEpass.py", "GeneratePostmanCollectionFastTrackEpass.py"),
        ("Lounge-ePass-P0-e2e-core.postman_collection.json", "FastTrack-ePass-P0-e2e-core.postman_collection.json"),
        ("BuildLoungeJsHelpersLines", "BuildFastTrackJsHelpersLines"),
        ("LoungePrebookingExtraDict", "FastTrackPrebookingExtraDict"),
        ("lpAssertNoLoungeReturnedWithOtherModuleFilter", "ftAssertNoFastTrackReturnedWithOtherModuleFilter"),
        ("loungeAvailabilityResourceId", "fastTrackAvailabilityResourceId"),
        ("loungeCancelMaxAttempts", "fastTrackCancelMaxAttempts"),
        ("lounge_resource_var", "fast_track_resource_var"),
        ("LOUNGE_RESOURCE_ID_VAR", "FASTTRACK_RESOURCE_ID_VAR"),
        ("ENV_LOUNGE_RESOURCE_ID", "ENV_FASTTRACK_RESOURCE_ID"),
        ("DP_HIST_EPASS_LOUNGE_RESOURCE_ID", "DP_HIST_EPASS_FASTTRACK_RESOURCE_ID"),
        ("DEFAULT_LOUNGE_RESOURCE_ID", "DEFAULT_FASTTRACK_RESOURCE_ID"),
        ("/v2/orders/lounges/", "/v2/orders/fastTrack/"),
        ("catalog_label='lounge'", "catalog_label='fastTrack'"),
        ("lounge ePass", "fastTrack ePass"),
        ("lounge 经典", "fastTrack 经典"),
        ("lounge 预约", "fastTrack 预约"),
        ("lounge 网点", "fastTrack 网点"),
        ("lounge 订单", "fastTrack 订单"),
        ("创建 lounge", "创建 fastTrack"),
        ("不含 lounge", "不含 fastTrack"),
        ("lounge 列表", "fastTrack 列表"),
        ("lounge 数据", "fastTrack 数据"),
        ("loungeMod", "fastTrackMod"),
        ("N00012", "C10826"),
        ("EPASS_MODULE_DEFAULT: Final[int] = 1", "EPASS_MODULE_DEFAULT: Final[int] = 2"),
        ("module=1", "module=2"),
        ("function lp", "function ft"),
        ("lpCancelDone_", "ftCancelDone_"),
        ("lpCancelDoneVar", "ftCancelDoneVar"),
        ("lpCancelOrderAttempt", "ftCancelOrderAttempt"),
        ("lpAssert", "ftAssert"),
        ("lpResolve", "ftResolve"),
        ("lpSave", "ftSave"),
        ("lpSync", "ftSync"),
        ("lpExpect", "ftExpect"),
        ("lpOther", "ftOther"),
        ("lpIs", "ftIs"),
        ("lpGet", "ftGet"),
        ("lpResponse", "ftResponse"),
        ("lpClear", "ftClear"),
        ("lpMark", "ftMark"),
        ("lpSet", "ftSet"),
        ("lpPrerequest", "ftPrerequest"),
        ("lpOrder", "ftOrder"),
        ("lpFail", "ftFail"),
        ("var lp", "var ft"),
        ("``lp*", "``ft*"),
        ("{{loungeResourceId}}", "{{fastTrackResourceId}}"),
        ("loungeResourceId", "fastTrackResourceId"),
    ]
    for old, new in pairs:
        src = src.replace(old, new)

    # 避免 ``module=1`` → ``module=2`` 误伤 ``module=11``（otherModule 隔离）
    src = src.replace("module=21", "module=11")
    # fastTrack MS 购买单 category=2（lounge 为 3）
    src = src.replace(
        "pm.test(label + ': category=3', function () {{\n    pm.expect(dataFn().category).to.eql(3);",
        "pm.test(label + ': category=2', function () {{\n    pm.expect(dataFn().category).to.eql(2);",
    )
    src = src.replace(
        "``category``：MS 创建/search=3，usage 单=2。",
        "``category``：MS 创建/search=2，usage 预约单=2。",
    )

    extra_old = '''def FastTrackPrebookingExtraDict() -> JsonObject:
    """fastTrack 经典预约 / Bundle ``extra``（含 prebookingRequiredInfo，无 optionId）。"""
    return {
        "prebookingToken": "{{prebookingToken}}",
        "prebookingRequiredInfo": {
            "firstName": CREATE_FIRST_NAME,
            "lastName": CREATE_LAST_NAME,
            "email": "auto.test@dragonpass.com",
            "phoneNumber": "8081966002",
            "callingCode": "44",
        },
    }'''

    extra_new = '''def BuildFastTrackPassengers(*, adult_count: int, child_count: int) -> List[JsonObject]:
    """按预约人数生成 fastTrack ``passengers``；仅首位为 leadPassenger，姓名唯一且仅拉丁字母。"""
    if adult_count < 0 or child_count < 0:
        raise ValueError("adult_count and child_count must be non-negative")
    if adult_count > len(FASTTRACK_ADULT_FIRST_NAMES):
        raise ValueError(
            f"adult_count={adult_count} exceeds configured names ({len(FASTTRACK_ADULT_FIRST_NAMES)})"
        )
    if child_count > len(FASTTRACK_CHILD_FIRST_NAMES):
        raise ValueError(
            f"child_count={child_count} exceeds configured names ({len(FASTTRACK_CHILD_FIRST_NAMES)})"
        )
    passenger_count = adult_count + child_count
    if passenger_count <= 0:
        raise ValueError("fastTrack passengers require at least one adult or child")

    passengers: List[JsonObject] = []
    for adult_index in range(adult_count):
        passengers.append(
            {
                "firstName": FASTTRACK_ADULT_FIRST_NAMES[adult_index],
                "lastName": "Adult",
                "passengersType": 1,
                "leadPassenger": adult_index == 0,
            }
        )
    for child_index in range(child_count):
        passengers.append(
            {
                "firstName": FASTTRACK_CHILD_FIRST_NAMES[child_index],
                "lastName": "Child",
                "passengersType": 2,
                "leadPassenger": False,
            }
        )
    return passengers


def FastTrackPrebookingExtraDict(
    *,
    adult_count: int = DEFAULT_FASTTRACK_ADULT_COUNT,
    child_count: int = DEFAULT_FASTTRACK_CHILD_COUNT,
) -> JsonObject:
    """fastTrack 经典预约 / Bundle ``extra``（含 prebookingRequiredInfo、passengers、transportNumber，无 optionId）。"""
    return {
        "prebookingToken": "{{prebookingToken}}",
        "prebookingRequiredInfo": {
            "firstName": CREATE_FIRST_NAME,
            "lastName": CREATE_LAST_NAME,
            "email": "auto.test@dragonpass.com",
            "phoneNumber": "8081966002",
            "callingCode": "44",
            "transportNumber": "BA123",
        },
        "passengers": BuildFastTrackPassengers(adult_count=adult_count, child_count=child_count),
    }'''
    src = src.replace(extra_old, extra_new)
    src = src.replace(
        'CREATE_AVAILABLE_USAGES: Final[int] = 2\n',
        'CREATE_AVAILABLE_USAGES: Final[int] = 2\n'
        'DEFAULT_FASTTRACK_ADULT_COUNT: Final[int] = 2\n'
        'DEFAULT_FASTTRACK_CHILD_COUNT: Final[int] = 0\n'
        'FASTTRACK_ADULT_FIRST_NAMES: Final[List[str]] = ["Auto", "Alex", "Anna", "Alan"]\n'
        'FASTTRACK_CHILD_FIRST_NAMES: Final[List[str]] = ["Amy", "Ben", "Cyra", "Dora"]\n',
    )
    src = src.replace(
        '        "adultCount": 1,\n        "childCount": 0,\n',
        '        "adultCount": DEFAULT_FASTTRACK_ADULT_COUNT,\n'
        '        "childCount": DEFAULT_FASTTRACK_CHILD_COUNT,\n',
    )
    src = src.replace(
        "function ftIsBusinessSuccess(env) {{",
        "function ftParseNonNegativeInt(value, fallbackValue) {{\n"
        "  var n = parseInt(String(value), 10);\n"
        "  if (isNaN(n) || n < 0) return fallbackValue;\n"
        "  return n;\n"
        "}}\n"
        "function ftExpectedUsageCount() {{\n"
        "  var raw = pm.collectionVariables.get('fastTrackExpectedUsageCount');\n"
        "  var n = ftParseNonNegativeInt(raw, 1);\n"
        "  return n <= 0 ? 1 : n;\n"
        "}}\n"
        "function ftIsBusinessSuccess(env) {{",
    )
    src = src.replace(
        "    if (reqBody && reqBody.resourceId) {{\n"
        "      pm.collectionVariables.set('fastTrackAvailabilityResourceId', String(reqBody.resourceId));\n"
        "    }}",
        "    if (reqBody && reqBody.resourceId) {{\n"
        "      pm.collectionVariables.set('fastTrackAvailabilityResourceId', String(reqBody.resourceId));\n"
        "    }}\n"
        "    var adultCount = ftParseNonNegativeInt(reqBody && reqBody.adultCount, 0);\n"
        "    var childCount = ftParseNonNegativeInt(reqBody && reqBody.childCount, 0);\n"
        "    pm.collectionVariables.set('fastTrackAdultCount', String(adultCount));\n"
        "    pm.collectionVariables.set('fastTrackChildCount', String(childCount));\n"
        "    pm.collectionVariables.set('fastTrackExpectedUsageCount', String(Math.max(1, adultCount + childCount)));",
    )
    src = src.replace(
        "pm.test(label + ': extra.usedUsages=1', function () {{\n"
        "    pm.expect(data().extra.usedUsages).to.eql(1);\n"
        "  }});",
        "pm.test(label + ': extra.usedUsages 与预约人数一致', function () {{\n"
        "    pm.expect(data().extra.usedUsages).to.eql(ftExpectedUsageCount());\n"
        "  }});",
    )
    src = src.replace(
        "pm.test(label + ': extra.usedUsages=1', function () {{ pm.expect(data().extra.usedUsages).to.eql(1); }});",
        "pm.test(label + ': extra.usedUsages 与预约人数一致', function () {{\n"
        "    pm.expect(data().extra.usedUsages).to.eql(ftExpectedUsageCount());\n"
        "  }});",
    )
    src = src.replace(
        "pm.expect(used, label + ' usedUsages').to.eql(1);",
        "pm.expect(used, label + ' usedUsages').to.eql(ftExpectedUsageCount());",
    )
    src = src.replace(
        'CollectionVariable("fastTrackCancelMaxAttempts", str(GENERATED_CANCEL_ATTEMPTS)),',
        'CollectionVariable("fastTrackAdultCount", str(DEFAULT_FASTTRACK_ADULT_COUNT)),\n'
        '        CollectionVariable("fastTrackChildCount", str(DEFAULT_FASTTRACK_CHILD_COUNT)),\n'
        '        CollectionVariable("fastTrackExpectedUsageCount", str(DEFAULT_FASTTRACK_ADULT_COUNT + DEFAULT_FASTTRACK_CHILD_COUNT)),\n'
        '        CollectionVariable("fastTrackCancelMaxAttempts", str(GENERATED_CANCEL_ATTEMPTS)),',
    )
    src = src.replace(
        "生成 fastTrack ePass **P0 E2E 核心**",
        "生成 fastTrack（快速通道）ePass **P0 E2E 核心**",
        1,
    )

    remaining = sorted(set(re.findall(r"\blp[A-Za-z_]+", src)))
    if remaining:
        raise RuntimeError(f"仍有 lp 前缀残留: {remaining}")

    OUT.write_text(src, encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    Main()
