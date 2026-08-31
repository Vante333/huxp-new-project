"""生成 FT Membership Prebooking Payment · P0 冒烟 Postman Collection。"""
from __future__ import annotations

from ft_prebooking_payment_common import Generate


def Main() -> None:
    out = Generate("membership", "p0")
    print(f"Wrote {out}")


if __name__ == "__main__":
    Main()
