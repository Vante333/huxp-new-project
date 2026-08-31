"""
生成 lounge ePass **P0 E2E 核心** Postman Collection v2.1 JSON（**API v1 路径**）。

这是有意保留的入口包装：复用 P0 编排入口 ``BuildCollection(api_version="v1")``，
仅将网关路径 ``/v2/`` 换为 ``/v1/``，且 **不断言** ``extra.ePassStatus``（v1 无该字段）。
公共 runtime / payload / 断言位于 ``lounge_epass_common.py``，本文件不承载复用实现。

用法（仓库根目录）::

    python api-testcases/api_tests/apifox-cli/generators/GeneratePostmanCollectionLoungeEpassV1.py
"""
from __future__ import annotations

import os
from typing import Final

from GeneratePostmanCollectionLoungeEpass import BuildCollection
from collection_builder_common import CollectionPath, WriteCollectionJson

OUT_NAME: Final[str] = "Lounge-ePass-P0-e2e-core-v1.postman_collection.json"
API_VERSION: Final[str] = "v1"


def Main() -> None:
    out_path = str(CollectionPath(OUT_NAME))
    WriteCollectionJson(out_path, BuildCollection(api_version=API_VERSION))
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    Main()
