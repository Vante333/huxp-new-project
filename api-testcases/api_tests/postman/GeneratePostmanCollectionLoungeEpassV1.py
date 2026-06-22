"""
生成 lounge ePass **P0 E2E 核心** Postman Collection v2.1 JSON（**API v1 路径**）。

与 ``GeneratePostmanCollectionLoungeEpass.py`` 步骤一致；网关路径 ``/v2/`` 换为 ``/v1/``，且 **不断言** ``extra.ePassStatus``（v1 无该字段）。

用法（仓库根目录）::

    python api-testcases/api_tests/postman/GeneratePostmanCollectionLoungeEpassV1.py
"""
from __future__ import annotations

import os
from typing import Final

from GeneratePostmanCollectionLoungeEpass import BuildCollection
from collection_builder_common import WriteCollectionJson

OUT_NAME: Final[str] = "Lounge-ePass-P0-e2e-core-v1.postman_collection.json"
API_VERSION: Final[str] = "v1"


def Main() -> None:
    script_dir = os.path.dirname(__file__)
    out_path = os.path.join(script_dir, OUT_NAME)
    WriteCollectionJson(out_path, BuildCollection(api_version=API_VERSION))
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    Main()
