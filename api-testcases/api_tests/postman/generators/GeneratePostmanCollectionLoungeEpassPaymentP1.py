"""生成 Lounge E-pass Prebooking Payment · P1 全量 Postman Collection。"""
from __future__ import annotations

from ft_prebooking_payment_common import Generate


def Main() -> None:
    out = Generate("epass", "p1", category="lounge")
    print(f"Wrote {out}")


if __name__ == "__main__":
    Main()
