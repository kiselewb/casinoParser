from parser.base_parser import BaseParser


class Site1Parser(BaseParser):
    async def navigate_to_topup(self, page):
        pass
        # topup_config = self.config['topup']
        # await page.click(topup_config['cashbox_selector'])

    async def parse_topup_data(self, page) -> dict:
        topup_config = self.config["topup"]

        # await page.wait_for_selector(topup_config['success_indicator'])

        async with page.expect_request(
            lambda req: "cashbox/deposit/methods" in req.url
        ) as request_info:
            await page.click(topup_config["cashbox_selector"])

        request = await request_info.value
        response = await request.response()

        data = await response.json()
        methods = data.get("methods")

        payment_methods = []
        for method in methods:
            group_id = method.get("groups", [])[0].get("id", None)
            aggregate_type = method.get("name")
            if (
                group_id != 51
                and group_id != 49
                and aggregate_type not in topup_config["invalid_methods"]
            ):
                method_name = method.get("popUpName").strip().capitalize()
                min_amount = method.get("limit", {}).get("RUB", {}).get("min")

                payment_methods.append(
                    {
                        "method_name": method_name,
                        "min_amount": min_amount,
                    }
                )

        return {"site_id": self.config["id"], "payment_methods": payment_methods}
