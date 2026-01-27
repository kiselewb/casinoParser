from apscheduler.schedulers.asyncio import AsyncIOScheduler
from parser.parser_manager import ParserManager
import logging


class ParserScheduler:
    def __init__(self, parser_manager: ParserManager, interval_hours: int = 1):
        self.parser_manager = parser_manager
        self.scheduler = AsyncIOScheduler()
        self.interval_hours = interval_hours
        self.logger = logging.getLogger("scheduler")

    def start(self):
        self.scheduler.add_job(
            self.parser_manager.parse_all_sites,
            'interval',
            hours=self.interval_hours,
            id='parse_sites',
            replace_existing=True
        )

        self.scheduler.add_job(
            self.parser_manager.parse_all_sites,
            'date',
            id='parse_sites_initial'
        )

        self.scheduler.start()
        self.logger.info(f"Scheduler started. Interval: {self.interval_hours} hour(s)")

    def stop(self):
        self.scheduler.shutdown()
        self.logger.info("Scheduler stopped")