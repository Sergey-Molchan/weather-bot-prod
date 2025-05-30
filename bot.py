import os
import requests
import asyncio
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from datetime import datetime, timedelta
from dotenv import load_dotenv
import config

# Загрузка переменных окружения
load_dotenv()

# Конфигурация
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

# Коды погоды для грозы
THUNDERSTORM_CODES = [1087, 1273, 1276, 1279, 1282]


async def get_weather_alerts(location: str):
    """Получение данных о погоде для конкретной локации"""
    url = f"http://api.weatherapi.com/v1/forecast.json?key={WEATHER_API_KEY}&q={location}&days=2&alerts=yes"
    response = requests.get(url)
    return response.json()


def check_thunderstorm(weather_data: dict):
    """Проверка приближения грозы"""
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
    except KeyError:
        pass
    return alerts


async def send_alert(context: ContextTypes.DEFAULT_TYPE, location_name: str, alerts: list):
    """Отправка уведомления в канал"""
    message = (
        f"⚡️ **ПРЕДУПРЕЖДЕНИЕ О ГРОЗЕ: {location_name.upper()}** ⚡️\n"
        f"*Период предупреждения:* {config.ALERT_WINDOW} ч\n"
    )

    for alert in alerts:
        message += (
            f"\n▫️ *{alert['time']}*: {alert['condition']}\n"
            f"  - Вероятность: {alert['chance']}%\n"
            f"  - Осадки: {alert['precip']} мм/ч\n"
            f"  - Ветер: {alert['wind']} км/ч\n"
        )

    await context.bot.send_message(
        chat_id=CHANNEL_ID,
        text=message,
        parse_mode="Markdown"
    )


async def auto_check(context: ContextTypes.DEFAULT_TYPE):
    """Автоматическая проверка всех локаций"""
    for name, coords in config.ALL_LOCATIONS.items():
        try:
            data = await get_weather_alerts(coords)
            alerts = check_thunderstorm(data)

            if alerts:
                await send_alert(context, name, alerts)
                # Пауза между отправками, чтобы не перегружать API
                await asyncio.sleep(2)

        except Exception as e:
            print(f"Ошибка для {name}: {str(e)}")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    keyboard = []
    for sector_name in config.SECTORS:
        keyboard.append([InlineKeyboardButton(sector_name, callback_data=f"sector:{sector_name}")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🌩️ Бот мониторинга гроз\nВыберите сектор для проверки:",
        reply_markup=reply_markup
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопок"""
    query = update.callback_query
    await query.answer()

    if query.data.startswith("sector:"):
        sector_name = query.data.split(":")[1]
        locations = config.SECTORS[sector_name]

        await query.edit_message_text(f"⏳ Проверяю {sector_name}...")

        results = []
        for name, coords in locations.items():
            try:
                data = await get_weather_alerts(coords)
                alerts = check_thunderstorm(data)

                if alerts:
                    result = f"⚡️ *{name}:*"
                    for alert in alerts:
                        result += f"\n▫️ {alert['time']} - {alert['condition']} ({alert['chance']}%)"
                    results.append(result)
                else:
                    results.append(f"✅ *{name}:* Грозы не ожидается")

                # Пауза для соблюдения лимитов API
                await asyncio.sleep(1)

            except Exception as e:
                results.append(f"❌ *{name}:* Ошибка ({str(e)})")

        # Формируем итоговое сообщение
        message = f"*Результаты проверки ({sector_name}):*\n\n" + "\n\n".join(results)
        await query.message.reply_text(
            text=message,
            parse_mode="Markdown",
            disable_web_page_preview=True
        )


def main():
    """Запуск бота"""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))

    # Периодическая проверка
    job_queue = application.job_queue
    job_queue.run_repeating(
        auto_check,
        interval=config.CHECK_INTERVAL,
        first=10
    )

    # Запуск бота
    application.run_polling()


if __name__ == "__main__":
    main()
