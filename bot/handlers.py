from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler
from telegram.ext import ConversationHandler
from datetime import datetime, timedelta
import logging
from telegram import InlineKeyboardMarkup
from bot.keyboards import (
    get_main_menu_keyboard,
    get_points_keyboard,
    get_weather_details_keyboard,
    get_back_to_weather_keyboard,
    get_thunder_check_keyboard
)
from bot.services import WeatherService
from bot.config import LOCATIONS_C_SECTOR, LOCATION_EAST_SECTOR, ALL_LOCATIONS
from bot.utils import format_weather_data

logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
SELECTING_SECTOR, SELECTING_POINT, SHOWING_WEATHER = range(3)


class BotHandlers:
    def __init__(self, weather_service: WeatherService):
        self.weather_service = weather_service
        self.thunder_cache = {"status": None, "expires": None}

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

    async def point_selected(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка выбора точки"""
        query = update.callback_query
        await query.answer()

        point_name = query.data.split(":")[1]
        context.user_data['point'] = point_name

        # Получаем координаты точки
        location = ALL_LOCATIONS.get(point_name)
        if not location:
            await query.edit_message_text(text="Ошибка: точка не найдена")
            return SELECTING_SECTOR

        # Получаем данные о погоде
        data = await self.weather_service.get_weather_data(location)
        if not data:
            await query.edit_message_text(text="Не удалось получить данные о погоде")
            return SELECTING_SECTOR

        # Форматируем данные
        message = format_weather_data(data, point_name)

        keyboard = get_weather_details_keyboard()
        await query.edit_message_text(
            text=message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return SHOWING_WEATHER

    async def tomorrow_forecast(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показ прогноза на завтра для выбранной точки"""
        query = update.callback_query
        await query.answer()

        point_name = context.user_data.get('point')
        location = ALL_LOCATIONS.get(point_name)

        if not location:
            await query.edit_message_text(text="Ошибка: точка не найдена")
            return SHOWING_WEATHER

        data = await self.weather_service.get_weather_data(location)
        if not data or 'forecast' not in data:
            await query.edit_message_text(text="Не удалось получить прогноз")
            return SHOWING_WEATHER

        # Берем прогноз на завтра (второй день)
        if len(data['forecast']['forecastday']) < 2:
            await query.edit_message_text(text="Прогноз на завтра недоступен")
            return SHOWING_WEATHER

        forecast = data['forecast']['forecastday'][1]['day']

        message = (
            f"📅 **Прогноз на завтра для {point_name}**\n"
            f"• Макс: {forecast['maxtemp_c']}°C\n"
            f"• Мин: {forecast['mintemp_c']}°C\n"
            f"• Состояние: {forecast['condition']['text']}\n"
            f"• Вероятность дождя: {forecast['daily_chance_of_rain']}%\n"
            f"• УФ-индекс: {forecast['uv']}"
        )

        keyboard = get_back_to_weather_keyboard()
        await query.edit_message_text(
            text=message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return SHOWING_WEATHER

    async def weather_alerts(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показ опасных явлений для выбранной точки"""
        query = update.callback_query
        await query.answer()

        point_name = context.user_data.get('point')
        location = ALL_LOCATIONS.get(point_name)

        if not location:
            await query.edit_message_text(text="Ошибка: точка не найдена")
            return SHOWING_WEATHER

        # Проверяем грозу для конкретной точки
        has_thunder = await self.weather_service.check_thunder_for_point(location)
        data = await self.weather_service.get_weather_data(location)
        alerts = self.weather_service.check_thunderstorm(data) if data else []

        message = f"⚠️ **Опасные явления для {point_name}**\n"

        if has_thunder:
            message += "⛈️ Обнаружена гроза!\n\n"

        if alerts:
            message += "🛑 Приближение грозового фронта:\n"
            for alert in alerts[:3]:
                message += (
                    f"• {alert['time']}: {alert['condition']}\n"
                    f"  Вероятность: {alert['chance']}%, "
                    f"Ветер: {alert['wind']} км/ч\n"
                )
        else:
            message += "✅ Опасных явлений не обнаружено"

        keyboard = get_back_to_weather_keyboard()
        await query.edit_message_text(
            text=message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return SHOWING_WEATHER

    async def back_to_weather(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Возврат к просмотру погоды для точки"""
        query = update.callback_query
        await query.answer()

        point_name = context.user_data.get('point')
        if not point_name:
            return await self.start(update, context)

        location = ALL_LOCATIONS.get(point_name)
        if not location:
            return await self.start(update, context)

        data = await self.weather_service.get_weather_data(location)
        if not data:
            return await self.start(update, context)

        message = format_weather_data(data, point_name)
        keyboard = get_weather_details_keyboard()
        await query.edit_message_text(
            text=message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return SHOWING_WEATHER

    async def back_to_points(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Возврат к выбору точек"""
        query = update.callback_query
        await query.answer()

        sector = context.user_data.get('sector', 'central')
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

    async def back_to_main(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Возврат в главное меню"""
        return await self.start(update, context)

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отмена диалога"""
        await update.message.reply_text("Диалог отменен")
        return ConversationHandler.END

    async def check_thunder(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик кнопки 'Проверить грозы'"""
        query = update.callback_query
        await query.answer()

        try:
            if self.thunder_cache["expires"] and datetime.now() < self.thunder_cache["expires"]:
                thunder_status = self.thunder_cache["status"]
            else:
                has_thunder = await self.weather_service.check_thunder()
                thunder_status = "⛈️ Грозы обнаружены!" if has_thunder else "🌤️ Без гроз"
                self.thunder_cache = {
                    "status": thunder_status,
                    "expires": datetime.now() + timedelta(minutes=15)
                }
        except Exception as e:
            logger.error(f"Ошибка при проверке гроз: {e}")
            thunder_status = "⚠️ Ошибка при проверке"

        await query.edit_message_text(
            text=f"Статус гроз: {thunder_status}",
            reply_markup=InlineKeyboardMarkup(get_thunder_check_keyboard())
        )
        return SELECTING_SECTOR

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
                    CallbackQueryHandler(self.back_to_main, pattern=r"^back_to_main$"),
                    CallbackQueryHandler(self.back_to_weather, pattern=r"^back_to_weather$")
                ]
            },
            fallbacks=[CommandHandler('cancel', self.cancel)],
            allow_reentry=True
        )
