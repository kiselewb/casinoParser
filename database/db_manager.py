from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import update, select, and_
from database.models import Base, ParseResult
from config.settings import DATABASE_URL
import logging


class DBManager:
    def __init__(self):
        self.engine = create_async_engine(DATABASE_URL, echo=False)
        self.async_session = async_sessionmaker(self.engine, expire_on_commit=False)
        self.logger = logging.getLogger("db_manager")

    async def init_db(self):
        async with self.engine.begin() as conn:
            # await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        self.logger.info("Database initialized")

    async def save_parse_result(self, result: dict):
        async with self.async_session() as session:
            try:
                site_id = result['site_id']

                stmt = (
                    update(ParseResult)
                    .where(and_(
                        ParseResult.site_id == site_id,
                        ParseResult.is_latest == True
                    ))
                    .values(is_latest=False)
                )
                await session.execute(stmt)

                parse_result = ParseResult(
                    site_id=site_id,
                    status=result.get('status'),
                    payment_methods=result.get('payment_methods'),
                    site_url=result.get('site_url'),
                    screenshot_path=result.get('screenshot_path'),
                    is_latest=True,
                    parsed_at=result.get('parsed_at'),
                    error_message=result.get('error_message'),
                )
                session.add(parse_result)
                await session.commit()

                self.logger.info(f"✅ Saved result for {site_id} (ID: {parse_result.id})")

            except Exception as e:
                await session.rollback()
                self.logger.error(f"❌ Error saving result: {e}")
                raise

    async def get_latest_results(self):
        async with self.async_session() as session:
            query = select(
                ParseResult.id,
                ParseResult.site_id,
                ParseResult.payment_methods,
                ParseResult.site_url,
                ParseResult.parsed_at,
                ParseResult.screenshot_path
            ).where(ParseResult.is_latest == True)
            result = await session.execute(query)

            return result.mappings().all()

    async def get_result_by_site_id(self, site_id: str):
        async with self.async_session() as session:
            query = select(
                ParseResult.id,
                ParseResult.site_id,
                ParseResult.payment_methods,
                ParseResult.site_url,
                ParseResult.parsed_at,
                ParseResult.screenshot_path
            ).where(and_(
                ParseResult.is_latest == True,
                ParseResult.site_id == site_id,
            ))
            result = await session.execute(query)

            return result.mappings().one_or_none()