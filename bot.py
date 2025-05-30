import os
import asyncio
import aiohttp
import logging
from telegram import (
    Bot,
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler
)
from datetime import datetime, timedelta
from dotenv import load_dotenv
import config

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG  # Включим DEBUG для диагностики
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()

# Конфигурация
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

# Состояния для ConversationHandler
SELECTING_SECTOR, SELECTING_POINT, SHOWING_WEATHER = range(3)

# Проверка загрузки переменных
if not all([WEATHER_API_KEY, TELEGRAM_BOT_TOKEN, CHANNEL_ID]):
    logger.error("Не все переменные окружения установлены!")
    exit(1)

# Коды погоды для грозы
THUNDERSTORM_CODES = [1087, 1273, 1276, 1279, 1282]


# Создаем единую сессию aiohttp для всех запросов
class HTTPSession:
    session = None

    @classmethod
    async def get_session(cls):
        if cls.session is None or cls.session.closed:
            cls.session = aiohttp.ClientSession()
        return cls.session

    @classmethod
    async def close(cls):
        if cls.session:
            await cls.session.close()


async def get_weather_data(location: str, days: int = 1):
    """Асинхронное получение данных о погоде"""
    url = f"http://api.weatherapi.com/v1/forecast.json?key={WEATHER_API_KEY}&q={location}&days={days}&alerts=yes"

    try:
        session = await HTTPSession.get_session()
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
            if response.status == 200:
                return await response.json()
            logger.error(f"Ошибка API: {response.status}")
            return None
    except asyncio.TimeoutError:
        logger.warning("Таймаут запроса к WeatherAPI")
        return None
    except Exception as e:
        logger.error(f"Ошибка подключения: {str(e)}")
        return None


def check_thunderstorm(weather_data: dict):
    """Проверка приближения грозы"""
    if not weather_data or 'forecast' not in weather_data:
        return []

    alerts = []
    try:
        for day in weather_data['forecast']['forecastday']:
            for hour in day['hour']:
                if hour['condition']['code'] in THUNDERSTORM_CODES:
                    alert_time = datetime.strptime(hour['time'], "%Y-%m-%d %H:%M")
                    time_window = datetime.now() + timedelta(hours=config.ALERT_WINDOW)

                    if datetime.now() < alert_time < time_window:
                        alerts.append({
                            "time": alert_time.strftime('%H:%M %d.%m'),
                            "condition": hour['condition']['text'],
                            "chance": hour['chance_of_thunder'],
                            "precip": hour['precip_mm'],
                            "wind": hour['wind_kph']
                        })
    except Exception as e:
        logger.error(f"Ошибка при обработке данных: {str(e)}")

    return alerts


def format_weather_data(data: dict, point_name: str):
    """Форматирование данных о погоде для вывода"""
    if not data or 'current' not in data:
        return "⚠️ Не удалось получить данные о погоде"

    current = data['current']
    forecast_day = data.get('forecast', {}).get('forecastday', [])
    forecast = forecast_day[0]['day'] if forecast_day else {}

    message = (
        f"🌤️ **Погода на {point_name}**\n"
        f"• **Сейчас:** {current['temp_c']}°C, {current['condition']['text']}\n"
        f"• **Ощущается как:** {current['feelslike_c']}°C\n"
        f"• **Ветер:** {current['wind_kph']} км/ч, {current['wind_dir']}\n"
        f"• **Влажность:** {current['humidity']}%\n"
        f"• **Осадки:** {current['precip_mm']} мм\n"
    )

    if forecast:
        message += (
            f"\n📅 **Прогноз на сегодня:**\n"
            f"• Макс: {forecast.get('maxtemp_c', 'N/A')}°C\n"
            f"• Мин: {forecast.get('mintemp_c', 'N/A')}°C\n"
            f"• Вероятность дождя: {forecast.get('daily_chance_of_rain', 'N/A')}%\n"
            f"• УФ-индекс: {forecast.get('uv', 'N/A')}"
        )

    alerts = check_thunderstorm(data)
    if alerts:
        message += f"\n\n⚠️ **Ожидаются грозы!**"
        for alert in alerts[:3]:
            message += f"\n▫️ {alert['time']} - {alert['condition']} ({alert['chance']}%)"

    return message


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    logger.debug("Вызвана команда /start")
    try:
        keyboard = [
            [InlineKeyboardButton("Центральный сектор", callback_data="sector:central")],
            [InlineKeyboardButton("Восточный сектор", callback_data="sector:east")],
            [InlineKeyboardButton("Все точки", callback_data="sector:all")],
            [InlineKeyboardButton("Проверить грозы", callback_data="check_thunder")]
        ]

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
    except Exception as e:
        logger.error(f"Ошибка в start: {str(e)}")
        return ConversationHandler.END


async def sector_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора сектора"""
    query = update.callback_query
    await query.answer()
    logger.debug(f"Выбран сектор: {query.data}")

    try:
        sector = query.data.split(":")[1]
        context.user_data['sector'] = sector

        if sector == "central":
            locations = config.LOCATIONS_C_sector
        elif sector == "east":
            locations = config.LOCATION_East_sector
        else:
            locations = config.ALL_LOCATIONS

        keyboard = []
        for name in locations:
            keyboard.append([InlineKeyboardButton(name, callback_data=f"point:{name}")])

        keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            text="📍 Выберите точку для просмотра погоды:",
            reply_markup=reply_markup
        )
        return SELECTING_POINT
    except Exception as e:
        logger.error(f"Ошибка в sector_selected: {str(e)}")
        await query.edit_message_text("⚠️ Произошла ошибка. Попробуйте позже.")
        return await back_to_main(update, context)


async def point_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора точки"""
    query = update.callback_query
    await query.answer()
    logger.debug(f"Выбрана точка: {query.data}")

    try:
        point_name = query.data.split(":")[1]
        context.user_data['point'] = point_name

        sector = context.user_data.get('sector', 'all')

        if sector == "central":
            locations = config.LOCATIONS_C_sector
        elif sector == "east":
            locations = config.LOCATION_East_sector
        else:
            locations = config.ALL_LOCATIONS

        coords = locations.get(point_name)

        if not coords:
            await query.edit_message_text("❌ Ошибка: точка не найдена")
            return ConversationHandler.END

        # Показать сообщение о загрузке
        await query.edit_message_text("⏳ Загружаю данные о погоде...")

        weather_data = await get_weather_data(coords, days=3)

        if not weather_data:
            await query.edit_message_text("⚠️ Не удалось получить данные о погоде")
            return SELECTING_POINT

        message = format_weather_data(weather_data, point_name)

        keyboard = [
            [InlineKeyboardButton("Прогноз на завтра", callback_data="tomorrow_forecast")],
            [InlineKeyboardButton("Опасные явления", callback_data="weather_alerts")],
            [InlineKeyboardButton("⬅️ Назад к точкам", callback_data="back_to_points")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            text=message,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return SHOWING_WEATHER
    except Exception as e:
        logger.error(f"Ошибка в point_selected: {str(e)}")
        await query.edit_message_text("⚠️ Произошла ошибка при загрузке данных.")
        return await back_to_main(update, context)


async def tomorrow_forecast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать прогноз на завтра"""
    query = update.callback_query
    await query.answer()
    logger.debug("Запрос прогноза на завтра")

    try:
        point_name = context.user_data.get('point')
        sector = context.user_data.get('sector', 'all')

        if sector == "central":
            locations = config.LOCATIONS_C_sector
        elif sector == "east":
            locations = config.LOCATION_East_sector
        else:
            locations = config.ALL_LOCATIONS

        coords = locations.get(point_name)

        if not coords:
            await query.edit_message_text("❌ Ошибка: точка не найдена")
            return ConversationHandler.END

        # Показать сообщение о загрузке
        await query.edit_message_text("⏳ Загружаю прогноз на завтра...")

        weather_data = await get_weather_data(coords, days=3)

        if not weather_data or len(weather_data.get('forecast', {}).get('forecastday', [])) < 2:
            await query.edit_message_text("⚠️ Не удалось получить прогноз на завтра")
            return SHOWING_WEATHER

        tomorrow = weather_data['forecast']['forecastday'][1]['day']
        date = weather_data['forecast']['forecastday'][1]['date']

        message = (
            f"📅 **Прогноз на завтра ({date}) для {point_name}**\n"
            f"• Макс: {tomorrow['maxtemp_c']}°C\n"
            f"• Мин: {tomorrow['mintemp_c']}°C\n"
            f"• Средняя: {tomorrow['avgtemp_c']}°C\n"
            f"• Осадки: {tomorrow['totalprecip_mm']} мм\n"
            f"• Вероятность дождя: {tomorrow['daily_chance_of_rain']}%\n"
            f"• УФ-индекс: {tomorrow['uv']}\n"
            f"• Условия: {tomorrow['condition']['text']}"
        )

        await query.edit_message_text(
            text=message,
            parse_mode="Markdown"
        )
        return SHOWING_WEATHER
    except Exception as e:
        logger.error(f"Ошибка в tomorrow_forecast: {str(e)}")
        await query.edit_message_text("⚠️ Произошла ошибка при загрузке прогноза.")
        return SHOWING_WEATHER


async def weather_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать опасные явления"""
    query = update.callback_query
    await query.answer()
    logger.debug("Запрос опасных явлений")

    try:
        point_name = context.user_data.get('point')
        sector = context.user_data.get('sector', 'all')

        if sector == "central":
            locations = config.LOCATIONS_C_sector
        elif sector == "east":
            locations = config.LOCATION_East_sector
        else:
            locations = config.ALL_LOCATIONS

        coords = locations.get(point_name)

        if not coords:
            await query.edit_message_text("❌ Ошибка: точка не найдена")
            return ConversationHandler.END

        # Показать сообщение о загрузке
        await query.edit_message_text("⏳ Проверяю опасные явления...")

        weather_data = await get_weather_data(coords, days=2)

        if not weather_data:
            await query.edit_message_text("⚠️ Не удалось получить данные о погоде")
            return SHOWING_WEATHER

        alerts = check_thunderstorm(weather_data)

        if alerts:
            message = f"⚡️ **Опасные явления на {point_name}:**\n"
            for alert in alerts:
                message += (
                    f"\n▫️ {alert['time']}: {alert['condition']}\n"
                    f"  - Вероятность грозы: {alert['chance']}%\n"
                    f"  - Осадки: {alert['precip']} мм/ч\n"
                    f"  - Ветер: {alert['wind']} км/ч\n"
                )
        else:
            message = f"✅ На {point_name} опасных явлений не ожидается в ближайшие {config.ALERT_WINDOW} часов"

        await query.edit_message_text(
            text=message,
            parse_mode="Markdown"
        )
        return SHOWING_WEATHER
    except Exception as e:
        logger.error(f"Ошибка в weather_alerts: {str(e)}")
        await query.edit_message_text("⚠️ Произошла ошибка при проверке опасных явлений.")
        return SHOWING_WEATHER


async def back_to_points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Вернуться к выбору точек"""
    query = update.callback_query
    await query.answer()
    logger.debug("Возврат к точкам")

    try:
        sector = context.user_data.get('sector', 'all')

        if sector == "central":
            locations = config.LOCATIONS_C_sector
        elif sector == "east":
            locations = config.LOCATION_East_sector
        else:
            locations = config.ALL_LOCATIONS

        keyboard = []
        for name in locations:
            keyboard.append([InlineKeyboardButton(name, callback_data=f"point:{name}")])

        keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            text="📍 Выберите точку для просмотра погоды:",
            reply_markup=reply_markup
        )
        return SELECTING_POINT
    except Exception as e:
        logger.error(f"Ошибка в back_to_points: {str(e)}")
        await query.edit_message_text("⚠️ Произошла ошибка. Возврат в главное меню.")
        return await back_to_main(update, context)


async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Вернуться в главное меню"""
    logger.debug("Возврат в главное меню")

    try:
        query = update.callback_query
        if query:
            await query.answer()

        context.user_data.clear()

        keyboard = [
            [InlineKeyboardButton("Центральный сектор", callback_data="sector:central")],
            [InlineKeyboardButton("Восточный сектор", callback_data="sector:east")],
            [InlineKeyboardButton("Все точки", callback_data="sector:all")],
            [InlineKeyboardButton("Проверить грозы", callback_data="check_thunder")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        if query:
            await query.edit_message_text(
                text="🏔️ Выберите сектор для просмотра погоды:",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                "🏔️ Выберите сектор для просмотра погоды:",
                reply_markup=reply_markup
            )

        return SELECTING_SECTOR
    except Exception as e:
        logger.error(f"Ошибка в back_to_main: {str(e)}")
        return ConversationHandler.END


async def check_thunder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверка гроз во всех точках"""
    query = update.callback_query
    await query.answer()
    logger.debug("Проверка гроз во всех точках")

    try:
        await query.edit_message_text("⏳ Проверяю все точки на наличие гроз...")

        results = []
        for name, coords in config.ALL_LOCATIONS.items():
            try:
                data = await get_weather_data(coords)
                alerts = check_thunderstorm(data) if data else []

                if alerts:
                    result = f"⚡️ *{name}:*"
                    for alert in alerts:
                        result += f"\n▫️ {alert['time']} - {alert['condition']} ({alert['chance']}%)"
                    results.append(result)
                else:
                    results.append(f"✅ *{name}:* Грозы не ожидается")

                await asyncio.sleep(0.5)  # Небольшая пауза
            except Exception as e:
                results.append(f"❌ *{name}:* Ошибка ({str(e)})")

        message = "*Результаты проверки гроз:*\n\n" + "\n\n".join(results)

        keyboard = [
            [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            text=message,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        return SELECTING_SECTOR
    except Exception as e:
        logger.error(f"Ошибка в check_thunder: {str(e)}")
        await query.edit_message_text("⚠️ Произошла ошибка при проверке гроз.")
        return await back_to_main(update, context)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Завершение диалога"""
    try:
        if update.callback_query:
            query = update.callback_query
            await query.answer()
            await query.edit_message_text("❌ Диалог прерван")
        else:
            await update.message.reply_text("❌ Диалог прерван")

        context.user_data.clear()
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Ошибка в cancel: {str(e)}")
        return ConversationHandler.END


async def shutdown(application: Application) -> None:
    """Очистка ресурсов при завершении"""
    logger.info("Завершение работы приложения...")
    await HTTPSession.close()
    logger.info("Ресурсы освобождены. Приложение завершило работу")


def main():
    """Запуск бота"""
    try:
        logger.info("Запуск бота...")
        application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

        # Настройка ConversationHandler
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', start)],
            states={
                SELECTING_SECTOR: [
                    CallbackQueryHandler(sector_selected, pattern=r"^sector:"),
                    CallbackQueryHandler(check_thunder, pattern=r"^check_thunder$"),
                    CallbackQueryHandler(back_to_main, pattern=r"^back_to_main$")
                ],
                SELECTING_POINT: [
                    CallbackQueryHandler(point_selected, pattern=r"^point:"),
                    CallbackQueryHandler(back_to_main, pattern=r"^back_to_main$")
                ],
                SHOWING_WEATHER: [
                    CallbackQueryHandler(tomorrow_forecast, pattern=r"^tomorrow_forecast$"),
                    CallbackQueryHandler(weather_alerts, pattern=r"^weather_alerts$"),
                    CallbackQueryHandler(back_to_points, pattern=r"^back_to_points$"),
                    CallbackQueryHandler(back_to_main, pattern=r"^back_to_main$")
                ]
            },
            fallbacks=[CommandHandler('cancel', cancel)]
        )

        application.add_handler(conv_handler)

        # Запуск бота
        logger.info("Бот запущен и ожидает сообщений...")
        application.run_polling()
        logger.info("Бот остановлен")
    except Exception as e:
        logger.error(f"Критическая ошибка при запуске: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        # Закрытие ресурсов при завершении
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(HTTPSession.close())
            else:
                loop.run_until_complete(HTTPSession.close())
            logger.info("HTTP сессия закрыта")
        except Exception as e:
            logger.error(f"Ошибка при закрытии ресурсов: {str(e)}")


if __name__ == "__main__":
    main()
