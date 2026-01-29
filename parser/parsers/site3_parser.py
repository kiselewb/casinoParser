from parser.base_parser import BaseParser
from parser.captcha_manager import CaptchaManager


class Site3Parser(BaseParser):
    async def authenticate(self, page):
        auth = self.config["auth"]

        await page.goto(auth["site_url"], wait_until="load")

        await page.click(auth["cookies_selector"])
        await page.click(auth["login_selector"])
        await page.wait_for_timeout(1000)

        is_captcha = await CaptchaManager().check_captcha(page)

        if is_captcha:
            captcha_sitekey = await CaptchaManager().get_captcha_id(page)
            captcha_token = await CaptchaManager().solve_captcha(page, captcha_sitekey)
            await self.login_with_captcha(page, captcha_token)

            await page.reload(wait_until="commit")
            await page.wait_for_selector(auth["success_indicator"])
        else:
            await self._human_like_type(
                page, auth["username_selector"], self.config["credentials"]["username"]
            )
            await self._human_like_type(
                page, auth["password_selector"], self.config["credentials"]["password"]
            )

            await page.click(auth["submit_selector"])

            await page.wait_for_selector(auth["success_indicator"])

    async def navigate_to_topup(self, page):
        topup_config = self.config["topup"]

        await page.click(topup_config["cashbox_selector"])
        await page.wait_for_selector(topup_config["success_indicator"])

    async def parse_topup_data(self, page) -> dict:
        topup_config = self.config["topup"]

        async with page.expect_request(self._is_payment_system_request) as request:
            await page.reload(wait_until="commit")
            await page.wait_for_selector(topup_config["success_indicator"])
            await page.click(topup_config["button_selector"])

        request = await request.value
        response = await request.response()
        response_data = await response.json()

        methods = response_data.get("details").get("paymentSystems")

        payment_methods = []
        for method in methods:
            aggregate_type = method.get("key")
            if aggregate_type in topup_config["valid_methods"]:
                method_name = method.get("name").capitalize()
                min_amount = int((method.get("min_limit")).split(".")[0])

                payment_methods.append(
                    {
                        "method_name": method_name,
                        "min_amount": min_amount,
                    }
                )

        return {"site_id": self.config["id"], "payment_methods": payment_methods}

    async def login_with_captcha(self, page, token):
        credentials = self.config["credentials"]
        email = credentials["username"]
        password = credentials["password"]
        captcha_token = token

        result = await page.evaluate(
            """
            async ({ email, password, token }) => {
                try {
                    const response = await fetch('https://74on-x.casino/api-gateway/graphql', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'apollographql-client-name': 'react-spa-app',
                            'apollographql-client-version': '31.29.2',
                            'x-locale': 'ru'
                        },
                        body: JSON.stringify({
                            operationName: "Login",
                            variables: {
                                login: email,
                                password: password,
                                gCaptchaResponse: token,
                                code: "",
                                platform: "BROWSER",
                                platformType: "MOB",
                                os: "ANDROID",
                                host: "4on-x62.casino",
                                userUuid: localStorage.getItem('_user_uuid') || ""
                            },
                            extensions: {
                                persistedQuery: {
                                    version: 1,
                                    sha256Hash: "f045d12a2ebf2f78c738edb2171cf507cbf37c6088bbb61838dde131283a8319"
                                }
                            }
                        })
                    });

                    const text = await response.text();
                    console.log('Response status:', response.status);
                    console.log('Response text:', text);

                    return {
                        status: response.status,
                        data: text ? JSON.parse(text) : null
                    };
                } catch (error) {
                    return {
                        error: error.message
                    };
                }
            }
        """,
            {"email": email, "password": password, "token": captcha_token},
        )

        if result["status"] == 200:
            self.logger.info("✅ Login with captcha successful")
            return True
        else:
            self.logger.info("⛔ Login with captcha unsuccessful")
            return False

    def _is_payment_system_request(self, request) -> bool:
        if "billcheckout.com/api/checkout/" not in request.url:
            return False

        if request.method != "GET":
            return False

        return True
