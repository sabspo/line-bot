from __future__ import annotations

import logging
import sys

from reply_service import generate_reply


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )

    if len(sys.argv) < 2:
        print('Usage: python main.py "つくしヤングラガーズ小学部です。商品の価格を教えてください。"')
        return 1

    print(generate_reply(sys.argv[1]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
