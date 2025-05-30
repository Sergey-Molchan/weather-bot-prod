import os
import logging
import requests
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Конфигурация
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OWM_API_KEY = os.getenv("OWM_API_KEY")

# Стабильная геопозиция (замените на свою)
STABLE_LOCATION = {
    "name": "Горный курорт 'Высота 1500'",
    "lat": 43.6440174,  # Широта
    "lon": 40.2552175,  # Долгота
    "elevation": 2050  # Высота в метрах
}

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Клавиатура
keyboard = [
    ["🌤️ Текущая погода", "📅 Прогноз на 24 часа"],
    ["⚠️ Грозовые предупреждения", "📊 График температуры"]
]
reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_weather_forecast():
    try:
        # Используем API 2.5
        url = f"https://api.openweathermap.org/data/2.5/onecall?lat={STABLE_LOCATION['lat']}&lon={STABLE_LOCATION['lon']}&exclude=minutely&appid={OWM_API_KEY}&units=metric&lang=ru"

        logger.info(f"Запрос к: {url.split('appid')[0]}...")  # Логируем без ключа

        response = requests.get(url, timeout=10)

        # Обработка HTTP ошибок
        if response.status_code == 401:
            logger.error("Ошибка 401: Неверный API-ключ OpenWeatherMap")
            return None
        elif response.status_code == 404:
            logger.error("Ошибка 404: Неверные координаты")
            return None
        elif response.status_code != 200:
            logger.error(f"Ошибка {response.status_code}: {response.text[:200]}")
            return None

        return response.json()
    except requests.exceptions.Timeout:
        logger.error("Таймаут соединения с OpenWeatherMap")
        return None
    except Exception as e:
        logger.exception("Непредвиденная ошибка:")
        return None



def detect_storm_alerts(forecast):
    """Обнаружение грозовых фронтов"""
    alerts = []
    for hourly in forecast.get("hourly", [])[:24]:  # Проверяем 24 часа
        time = datetime.fromtimestamp(hourly["dt"]).strftime("%H:%M")
        weather_main = hourly["weather"][0]["main"].lower()

        # Проверка на грозу
        if 'thunderstorm' in weather_main:
            alerts.append({
                "time": time,
                "alert": "⛈️ Грозовой фронт",
                "description": hourly["weather"][0]["description"]
            })

        # Проверка на сильный дождь/снег
        elif 'rain' in weather_main or 'snow' in weather_main:
            if hourly.get("pop", 0) > 0.7:  # Вероятность осадков > 70%
                alerts.append({
                    "time": time,
                    "alert": "⚠️ Сильные осадки",
                    "description": hourly["weather"][0]["description"]
                })

    return alerts


def generate_temperature_plot(forecast):
    """Генерация графика температуры на 24 часа"""
    import matplotlib.pyplot as plt
    from datetime import datetime

    hours = []
    temps = []
    for hourly in forecast["hourly"][:24]:
        hours.append(datetime.fromtimestamp(hourly["dt"]))
        temps.append(hourly["temp"])

    plt.figure(figsize=(10, 5))
    plt.plot(hours, temps, 'o-')
    plt.title(f"Температура на {STABLE_LOCATION['elevation']}м")
    plt.xlabel("Время")
    plt.ylabel("°C")
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()

    # Сохраняем график во временный файл
    filename = "temp_plot.png"
    plt.savefig(filename)
    plt.close()
    return filename


def format_weather_response(weather_data):
    """Форматирование данных о погоде в читаемый текст"""
    current = weather_data["current"]
    return (
        f"🌡️ Сейчас: {current['temp']}°C\n"
        f"🧊 Ощущается как: {current['feels_like']}°C\n"
        f"☁️ Погода: {current['weather'][0]['description'].capitalize()}\n"
        f"💧 Влажность: {current['humidity']}%\n"
        f"🌬️ Ветер: {current['wind_speed']} м/с\n"
        f"🌫️ Видимость: {current.get('visibility', 10000) / 1000:.1f} км"
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /start"""
    await update.message.reply_text(
        f"🏔️ Привет! Я бот погоды для {STABLE_LOCATION['name']}.\n"
        f"📏 Высота: {STABLE_LOCATION['elevation']}м\n"
        "Выберите нужную опцию:",
        reply_markup=reply_markup
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора пользователя"""
    text = update.message.text
    forecast = get_weather_forecast()

    if not forecast:
        await update.message.reply_text("❌ Не удалось получить данные о погоде. Попробуйте позже.")
        return

    if "🌤️ Текущая погода" in text:
        response = format_weather_response(forecast)
        await update.message.reply_text(response)

    elif "📅 Прогноз на 24 часа" in text:
        response = "⏱️ Прогноз на 24 часа:\n\n"
        for i in range(0, 24, 3):  # Каждые 3 часа
            hour = forecast["hourly"][i]
            time = datetime.fromtimestamp(hour["dt"]).strftime("%H:%M")
            response += f"🕒 {time}: {hour['temp']}°C, {hour['weather'][0]['description']}\n"
        await update.message.reply_text(response)

    elif "⚠️ Грозовые предупреждения" in text:
        alerts = detect_storm_alerts(forecast)
        if not alerts:
            await update.message.reply_text("✅ Гроз и сильных осадков не ожидается")
        else:
            response = "🚨 Погодные предупреждения:\n\n"
            for alert in alerts:
                response += f"⏰ {alert['time']}: {alert['alert']} ({alert['description']})\n"
            await update.message.reply_text(response)

    elif "📊 График температуры" in text:
        plot_file = generate_temperature_plot(forecast)
        await update.message.reply_photo(
            photo=open(plot_file, 'rb'),
            caption=f"Изменение температуры на 24 часа ({STABLE_LOCATION['name']})"
        )
        # Удаляем временный файл
        import os
        os.remove(plot_file)


def main():
    """Запуск бота"""
    if not TELEGRAM_TOKEN:
        logger.error("Токен Telegram не найден! Проверьте файл .env")
        return
    if not OWM_API_KEY:
        logger.error("API ключ OpenWeather не найден! Проверьте файл .env")
        return

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Регистрация обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Бот запущен в режиме опроса...")
    application.run_polling()


if __name__ == "__main__":
    main()