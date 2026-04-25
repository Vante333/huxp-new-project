"""
兼容壳：PAPI-2515 crossModule 业务实现已迁至 ``services.papi2515_cross_module_impl``。

新代码请 ``from services.papi2515_cross_module_impl import …`` 或经 ``services.papi2515_service`` 引用。
"""
from __future__ import annotations

from services.papi2515_cross_module_impl import *  # noqa: F401,F403,F405
