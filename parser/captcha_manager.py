import asyncio
import aiohttp
import logging
from config.settings import CAPMONSTER_KEY, CAPMONSTER_URL_CREATE, CAPMONSTER_URL_RESULT


class CaptchaManager:
    def __init__(self):
        self.logger = logging.getLogger("captcha_manager")

    async def solve_captcha(self, page, sitekey) -> str | None:
        task_data = await self._get_task_data(page, sitekey)
        task_id = await self._create_task(task_data)
        token = await self._get_task_result(task_id)

        if token:
            self.logger.info(f"✅ Captcha solved. Token: {token[:50]}...")
            return token
        else:
            self.logger.info("⛔ Failed to get captcha result")
            return None

    async def check_captcha(self, page):
        is_captcha = await page.evaluate("() => Boolean(window.turnstile || window._cf_chl_opt)")

        if is_captcha:
            self.logger.info("⛔ Cloudflare Captcha detected")
            return True

        self.logger.info("✅ Cloudflare Captcha not detected")
        return False

    async def get_captcha_id(self, page):
        async with page.expect_request(self._is_captcha_id_request) as request:
            await page.reload()

        request_data = await request.value
        response = await request_data.response()
        response_data, = await response.json()
        captcha_id = response_data.get('data').get('reCaptcha').get('captchaId')

        return captcha_id

    async def _create_task(self, task_data: dict) -> str:
        payload = {
            "clientKey": CAPMONSTER_KEY,
            "task": task_data,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(CAPMONSTER_URL_CREATE, json=payload) as response:
                response_data = await response.json(content_type=None)

        if response_data["errorId"] == 0:
            return response_data["taskId"]
        else:
            raise RuntimeError(response_data)

    async def _get_task_result(self, task_id, timeout = 120) -> str:
        loop = asyncio.get_running_loop()
        start = loop.time()

        async with aiohttp.ClientSession() as session:
            while True:
                if loop.time() - start > timeout:
                    raise TimeoutError("Captcha solve timeout")

                async with session.post(
                        CAPMONSTER_URL_RESULT,
                        json={
                            "clientKey": CAPMONSTER_KEY,
                            "taskId": task_id
                        }
                ) as response:
                    data = await response.json(content_type=None)

                if data["status"] == "ready":
                    return data["solution"]["token"]

                await asyncio.sleep(2)

    async def _get_task_data(self, page, sitekey) -> dict:
        page_url = page.url

        return {
            "type": "TurnstileTask",
            "websiteURL": page_url,
            "websiteKey": sitekey
        }

    def _is_captcha_id_request(self, request) -> bool:
        if "api-gateway/graphql" not in request.url:
            return False

        if request.method != "POST":
            return False

        payload = request.post_data_json
        if not payload:
            return False

        if not isinstance(payload, list) or not payload:
            return False

        request_payload = payload[0]
        return request_payload.get("operationName") == "Captcha"