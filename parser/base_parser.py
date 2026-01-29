import asyncio
import random
import logging
from playwright.async_api import async_playwright
from abc import ABC, abstractmethod
from datetime import datetime, UTC
from config.settings import BROWSER_TIMEOUT, HEADLESS_MODE, BROWSER_ARGS, CONTEXT_PARAMS
from parser.screenshot_manager import ScreenshotManager


class BaseParser(ABC):
    def __init__(self, config: dict):
        self.config = config
        self.logger = logging.getLogger(f"parser.{config['id']}")
        self.screenshot_manager = ScreenshotManager()

    async def parse(self) -> dict:
        start_time = datetime.now(UTC)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=HEADLESS_MODE, args=BROWSER_ARGS)

            context = await browser.new_context(**CONTEXT_PARAMS)

            context.set_default_timeout(BROWSER_TIMEOUT)

            page = await context.new_page()

            try:
                self.logger.info(f"🚀 Starting parse for {self.config['name']}")

                await self.authenticate(page)
                self.logger.info(f"✅ Authenticated on {self.config['name']}")

                await self.navigate_to_topup(page)
                self.logger.info("✅ Navigated to topup page")

                data = await self.parse_topup_data(page)
                self.logger.info(
                    f"✅ Parsed {len(data.get('payment_methods', []))} payment methods"
                )

                screenshot_path = await self.take_screenshot(page)
                data["screenshot_path"] = screenshot_path

                data["status"] = "success"
                data["parsed_at"] = datetime.now(UTC)
                data["site_url"] = self.config["auth"]["site_url"]

                parse_time = (datetime.now(UTC) - start_time).total_seconds()
                self.logger.info(
                    f"✅ Parse completed in {parse_time:.2f}s for {self.config['name']}"
                )

                return data

            except Exception as e:
                parse_time = (datetime.now(UTC) - start_time).total_seconds()

                self.logger.error(
                    f"❌ Parse failed for {self.config['name']} after {parse_time:.2f}s"
                )
                self.logger.error(f"❌ Error type: {type(e).__name__}")
                self.logger.error(f"❌ Error message: {str(e)}")
                self.logger.exception("Full traceback:")

                try:
                    error_screenshot = f"error_{self.config['id']}_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.png"
                    await page.screenshot(path=f"screenshots/{error_screenshot}")
                    self.logger.info(f"📸 Error screenshot saved: {error_screenshot}")
                except:
                    raise

                return {
                    "site_id": self.config["id"],
                    "status": "error",
                    "error_message": f"{type(e).__name__}: {str(e)}",
                    "parsed_at": datetime.now(UTC),
                }

            finally:
                await browser.close()

    async def authenticate(self, page):
        auth = self.config["auth"]

        await page.goto(auth["site_url"], wait_until="domcontentloaded")

        await page.wait_for_selector(auth["login_selector"])

        await page.click(auth["login_selector"])

        await self._human_like_type(
            page, auth["username_selector"], self.config["credentials"]["username"]
        )
        await self._human_like_type(
            page, auth["password_selector"], self.config["credentials"]["password"]
        )

        await page.click(auth["submit_selector"])

        await page.wait_for_selector(auth["success_indicator"])

    @abstractmethod
    async def navigate_to_topup(self, page):
        pass

    @abstractmethod
    async def parse_topup_data(self, page) -> dict:
        pass

    async def take_screenshot(self, page) -> str:
        topup_config = self.config["topup"]

        filepath = self.screenshot_manager.get_screenshot_path(self.config["id"])
        element = page.locator(topup_config["screenshot_selector"])
        await asyncio.sleep(1)
        await element.screenshot(path=filepath)
        self.logger.info(f"Screenshot saved: {filepath}")
        return filepath

    async def _random_delay(self, min_seconds=1.0, max_seconds=3.0):
        """Случайная задержка для имитации человека"""
        delay = random.uniform(min_seconds, max_seconds)
        self.logger.info(f"⏳ Random delay: {delay:.2f}s")
        await asyncio.sleep(delay)

    async def _human_like_type(self, page, selector: str, text: str):
        """Печатает текст с задержками как человек"""
        await page.click(selector)
        await self._random_delay(0.1, 0.3)

        for char in text:
            await page.keyboard.type(char)
            # Случайная задержка между символами
            await asyncio.sleep(random.uniform(0.05, 0.15))
