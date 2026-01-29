import os
from pathlib import Path
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, ReplyKeyboardMarkup, \
    KeyboardButton
from database.db_manager import DBManager
import logging
import pytz


BASE_DIR = Path(__file__).resolve().parent.parent
SCREENSHOT_DIR = BASE_DIR / "screenshots"


class ParserBot:
    def __init__(self, token: str):
        self.bot = Bot(token=token)
        self.dp = Dispatcher()
        self.db = DBManager()
        self.logger = logging.getLogger("bot")

        self.dp.message(Command("start"))(self.cmd_start)
        self.dp.message(F.text == "📊 Получить данные")(self.get_message_data)
        self.dp.callback_query(F.data == "get_data")(self.get_data)
        self.dp.callback_query(F.data.startswith("show_screenshot:"))(self.show_screenshot)
        self.dp.callback_query(F.data.startswith("hide_screenshot:"))(self.hide_screenshot)

    async def cmd_start(self, message: types.Message):
        # keyboard = InlineKeyboardMarkup(inline_keyboard=[
        #     [InlineKeyboardButton(text="📊 Получить данные", callback_data="get_data")]
        # ])
        keyboard = self._create_get_data_keyborad()

        await message.answer(
            "👋 Привет! Я бот для мониторинга данных о пополнении сайтов.\n\n"
            "Нажми кнопку ниже, чтобы получить актуальные данные.",
            reply_markup=keyboard
        )

    async def get_data(self, callback: types.CallbackQuery | None):
        await callback.answer("⏳ Загружаю данные...")

        results = await self.db.get_latest_results()

        if not results:
            await callback.message.answer(
                "⚠️ Нет доступных данных.\nПарсер еще не запускался или все сайты недоступны."
            )
            return

        for result in results:
            await self.send_site_data(callback.message, result)

    async def get_message_data(self, message: types.Message):
        await message.answer("⏳ Загружаю данные...")

        results = await self.db.get_latest_results()

        if not results:
            await message.answer(
                "⚠️ Нет доступных данных.\nПарсер еще не запускался или все сайты недоступны."
            )
            return

        for result in results:
            await self.send_site_data(message, result)

    async def send_site_data(self, message: types.Message, result: dict):
        text = self._format_result_text(result)
        site_id= result.get("site_id")
        keyboard = self._create_show_screenshot_keyboard(site_id)

        await message.answer(
            text,
            parse_mode="HTML",
            reply_markup=keyboard,
            disable_web_page_preview=True
        )

    async def show_screenshot(self, callback: types.CallbackQuery):
        site_id = callback.data.split(":")[1]

        if not site_id:
            await callback.answer("❌ Данные не найдены", show_alert=True)
            return

        screenshot_path = f"{SCREENSHOT_DIR}/{site_id}/{site_id}.png"

        if not screenshot_path or not os.path.exists(screenshot_path):
            await callback.answer("❌ Скриншот не найден", show_alert=True)
            return

        try:
            keyboard = self._create_hide_screenshot_keyboard(site_id)

            await callback.message.edit_media(
                media=InputMediaPhoto(
                    media=FSInputFile(screenshot_path),
                    parse_mode="HTML"
                ),
                reply_markup=keyboard,
            )

            await callback.answer()

        except Exception as e:
            self.logger.error(f"Error showing screenshot: {e}")
            await callback.answer("❌ Ошибка при загрузке скриншота", show_alert=True)

    async def hide_screenshot(self, callback: types.CallbackQuery):
        site_id = callback.data.split(":")[1]

        result = await self.db.get_result_by_site_id(site_id)

        if not result:
            await callback.answer("❌ Данные не найдены", show_alert=True)
            return

        try:
            await callback.message.delete()
            await self.send_site_data(callback.message, result)
            await callback.answer()

        except Exception as e:
            self.logger.error(f"Error hiding screenshot: {e}")
            await callback.answer("❌ Ошибка", show_alert=True)

    def _format_result_text(self, result: dict) -> str:
        site_name = result['site_id'].capitalize()
        site_url = result['site_url']
        parsed_at = result['parsed_at'].astimezone(pytz.timezone('Europe/Moscow')).strftime('%H:%M')

        text = f"<b><a href='{site_url}'>{site_name}</a></b> "
        text += f"({parsed_at} МСК)\n"

        payment_methods = result.get('payment_methods', [])

        if payment_methods:
            for method in payment_methods:
                text += f"{method['method_name']}: от {method['min_amount']}₽\n"
        else:
            text += "⚠️ Методы пополнения не найдены\n\n"

        return text

    def _create_show_screenshot_keyboard(self, site_id: str) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="📄 Показать подтверждение",
                callback_data=f"show_screenshot:{site_id}"
            )]
        ])

    def _create_hide_screenshot_keyboard(self, site_id: str) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="◀️ Назад",
                callback_data=f"hide_screenshot:{site_id}"
            )]
        ])

    def _create_get_data_keyborad(self):
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📊 Получить данные")]
            ],
            is_persistent=True,
            resize_keyboard=True
        )

    async def start_polling(self):
        await self.bot.delete_webhook(drop_pending_updates=True)
        self.logger.info("🤖 Bot started polling")
        await self.dp.start_polling(self.bot)

    async def stop(self):
        await self.bot.session.close()
        self.logger.info("🤖 Bot stopped")