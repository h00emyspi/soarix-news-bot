from __future__ import annotations

import asyncio
import logging
import os

from app.bot import NewsBotApp
from app.config import load_config
from app.dashboard import run_dashboard


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    config = load_config()

    mode = os.getenv("APP_MODE", "bot").strip().lower()
    if mode == "dashboard":
        run_dashboard(config, host="0.0.0.0", port=int(os.getenv("DASHBOARD_PORT", "8080")))
        return

    app = NewsBotApp(config)
    asyncio.run(app.run())


if __name__ == "__main__":
    main()
