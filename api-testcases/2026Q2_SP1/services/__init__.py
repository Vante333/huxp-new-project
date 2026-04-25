"""服务包：请从子模块显式导入，避免包级聚合导入引发循环依赖。"""
from __future__ import annotations

from typing import List

__all__: List[str] = []
