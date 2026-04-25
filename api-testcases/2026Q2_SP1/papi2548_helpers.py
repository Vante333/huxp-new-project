"""
兼容壳：PAPI-2548 会籍 extensions 业务实现已迁至
``services.papi2548_memberships_extensions_impl``。

新代码请 ``from services.papi2548_memberships_extensions_impl import …`` 或经
``services.papi2548_service`` 引用，勿在本文件追加逻辑。
"""
from __future__ import annotations

from services.papi2548_memberships_extensions_impl import *  # noqa: F401,F403,F405
