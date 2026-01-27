import asyncio
import logging
from config.settings import (
    setup_logging,
    load_config,
    validate_settings
)
from parser.parser_manager import ParserManager
from parser.scheduler import ParserScheduler
from bot.bot import ParserBot
from database.db_manager import DBManager

# Настройка логирования
setup_logging()
logger = logging.getLogger(__name__)


async def main():
    try:
        # Проверка настроек
        validate_settings()

        logger.info("=" * 60)
        logger.info("🚀 Starting Parser Application")
        logger.info("=" * 60)

        # Загрузка конфигурации
        config = load_config()
        logger.info(f"📋 Loaded config for {len(config['sites'])} sites")
        logger.info(f"⏰ Parse interval: {config['parse_interval_hours']} hour(s)")

        # Инициализация БД
        db = DBManager()
        await db.init_db()

        # Создание парсер менеджера
        parser_manager = ParserManager(config['sites'])
        # await parser_manager.parse_all_sites()

        # Запуск планировщика
        scheduler = ParserScheduler(
            parser_manager,
            interval_hours=config['parse_interval_hours'],
        )
        scheduler.start()

        # Запуск бота
        bot = ParserBot(config['telegram_bot_token'])

        # logger.info("✅ All components initialized")
        logger.info("🤖 Starting Telegram bot...")

        await bot.start_polling()

    except KeyboardInterrupt:
        logger.info("\n⚠️  Received shutdown signal")
        logger.info("🛑 Shutting down gracefully...")
        scheduler.stop()
        await bot.stop()
        logger.info("👋 Application stopped")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        logger.exception("Full traceback:")
        raise


if __name__ == '__main__':
    asyncio.run(main())