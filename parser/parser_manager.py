from parser.parsers.site1_parser import Site1Parser
from parser.parsers.site2_parser import Site2Parser
from parser.parsers.site3_parser import Site3Parser
from database.db_manager import DBManager
import logging


class ParserManager:
    def __init__(self, sites_config: list[dict]):
        self.sites_config = sites_config
        self.db = DBManager()
        self.logger = logging.getLogger("parser_manager")

        self.parsers_map = {
            'pinco': Site1Parser,
            'martin': Site2Parser,
            'onx': Site3Parser,
        }

    async def parse_all_sites(self):
        self.logger.info("Starting parse cycle")

        # tasks = []
        # for site_config in self.sites_config:
        #     if site_config.get('enabled', True):
        #         tasks.append(self.parse_site(site_config))
        #
        # results = await asyncio.gather(*tasks, return_exceptions=True)

        results = []
        for site_config in self.sites_config:
            if site_config.get('enabled', True):
                try:
                    result = await self.parse_site(site_config)
                    results.append(result)
                except Exception as e:
                    results.append(e)

        self.logger.info(f"Parse cycle completed. Results: {len(results)}")
        return results

    async def parse_site(self, site_config: dict):
        site_id = site_config['id']
        self.logger.info(f"Parsing {site_id}")

        try:
            parser_class = self.parsers_map.get(site_id)
            if not parser_class:
                raise ValueError(f"No parser for {site_id}")

            parser = parser_class(site_config)

            result = await parser.parse()

            await self.db.save_parse_result(result)

            return result

        except Exception as e:
            self.logger.error(f"Error parsing {site_id}: {e}")
            return {'site_id': site_id, 'status': 'error', 'error_message': str(e)}