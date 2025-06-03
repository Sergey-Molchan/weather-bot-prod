from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler
from telegram.ext import ConversationHandler

from bot.keyboards import (
    get_main_menu_keyboard,
    get_points_keyboard,
    get_weather_details_keyboard
)
from bot.services import WeatherService
from bot.config import LOCATIONS_C_SECTOR, LOCATION_EAST_SECTOR, ALL_LOCATIONS
from bot.utils import format_weather_data


# Состояния для ConversationHandler
SELECTING_SECTOR, SELECTING_POINT, SHOWING_WEATHER = range(3)


class BotHandlers:
    def __init__(self, weather_service: WeatherService):
        self.weather_service = weather_service

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        keyboard = get_main_menu_keyboard()
        reply_markup = InlineKeyboardMarkup(keyboard)

        if update.message:
            await update.message.reply_text(
                "🏔️ Выберите сектор для просмотра погоды:",
                reply_markup=reply_markup
            )
        else:
            await update.callback_query.edit_message_text(
                text="🏔️ Выберите сектор для просмотра погоды:",
                reply_markup=reply_markup
            )
        return SELECTING_SECTOR

    async def sector_selected(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора сектора"""
        query = update.callback_query
        await query.answer()

        sector = query.data.split(":")[1]
        context.user_data['sector'] = sector

        if sector == "central":
            locations = LOCATIONS_C_SECTOR
        elif sector == "east":
            locations = LOCATION_EAST_SECTOR
        else:
            locations = ALL_LOCATIONS

        keyboard = get_points_keyboard(locations)
        await query.edit_message_text(
            text="📍 Выберите точку для просмотра погоды:",
            reply_markup=keyboard
        )
        return SELECTING_POINT

    # ... остальные обработчики

    def get_conversation_handler(self):
        return ConversationHandler(
            entry_points=[CommandHandler('start', self.start)],
            states={
                SELECTING_SECTOR: [
                    CallbackQueryHandler(self.sector_selected, pattern=r"^sector:"),
                    CallbackQueryHandler(self.check_thunder, pattern=r"^check_thunder$"),
                ],
                SELECTING_POINT: [
                    CallbackQueryHandler(self.point_selected, pattern=r"^point:"),
                    CallbackQueryHandler(self.back_to_main, pattern=r"^back_to_main$")
                ],
                SHOWING_WEATHER: [
                    CallbackQueryHandler(self.tomorrow_forecast, pattern=r"^tomorrow_forecast$"),
                    CallbackQueryHandler(self.weather_alerts, pattern=r"^weather_alerts$"),
                    CallbackQueryHandler(self.back_to_points, pattern=r"^back_to_points$"),
                    CallbackQueryHandler(self.back_to_main, pattern=r"^back_to_main$")
                ]
            },
            fallbacks=[CommandHandler('cancel', self.cancel)],
            allow_reentry=True
        )