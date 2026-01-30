from parser.base_parser import BaseParser


class Site2Parser(BaseParser):
    async def navigate_to_topup(self, page):
        await page.reload(wait_until="commit")

    async def parse_topup_data(self, page) -> dict:
        topup_config = self.config["topup"]

        site_url = page.url.replace("ru", "")

        async with page.expect_response(
            lambda response: response.url == f"{site_url}api/v4/cashbox/payment_methods"
        ) as response_info:
            await page.click(topup_config["cashbox_selector"])

        response = await response_info.value

        data = await response.json()

        methods = data.get("payment_methods")

        payment_methods = []
        for method in methods:
            aggregate_type = method.get("aggregate_type")
            if aggregate_type in topup_config["valid_methods"]:
                method_name = method.get("child_system_name")
                if not method_name:
                    method_name = method.get("child_system").capitalize()
                else:
                    method_name = method_name.capitalize()
                min_amount = int(
                    (
                        method.get("limit", {}).get(
                            "min", "Неизвестное минимальное значение"
                        )
                    ).split(".")[0]
                )

                payment_methods.append(
                    {
                        "method_name": method_name,
                        "min_amount": min_amount,
                    }
                )

        return {"site_id": self.config["id"], "payment_methods": payment_methods}
