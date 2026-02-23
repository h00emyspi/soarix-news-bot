import os

from .config import load_config
from .dashboard import run_dashboard
from .main import run_bot
from .telethon_collector import main as run_collector


def main():
    cfg = load_config()
    mode = (cfg.app_mode or "bot").strip().lower()

    if mode == "dashboard":
        run_dashboard(cfg, host="0.0.0.0", port=cfg.dashboard_port)
        return

    if mode == "collector":
        # Telethon collector uses cfg from .env
        run_collector()
        return

    run_bot(cfg)


if __name__ == "__main__":
    main()
