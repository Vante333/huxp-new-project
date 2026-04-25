"""
兼容壳：PAPI-2424 ePasses details 业务实现已迁至 ``services.papi2424_epasses_impl``。

新代码请 ``from services.papi2424_epasses_impl import …`` 或经 ``services.papi2424_service`` 引用。
"""
from __future__ import annotations

from services.papi2424_epasses_impl import *  # noqa: F401,F403,F405
