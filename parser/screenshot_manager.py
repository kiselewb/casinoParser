from pathlib import Path
import logging
from config.settings import SCREENSHOT_PATH


class ScreenshotManager:
    def __init__(self, retention_days: int = None):
        from config.settings import SCREENSHOT_RETENTION_DAYS

        self.base_path = Path(SCREENSHOT_PATH)
        self.retention_days = retention_days or SCREENSHOT_RETENTION_DAYS
        self.logger = logging.getLogger("screenshot_manager")

    def get_screenshot_path(self, site_id: str) -> str:
        site_dir = self.base_path / site_id
        site_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{site_id}.png"

        return str(site_dir / filename)