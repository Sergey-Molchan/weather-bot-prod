import os
import logging
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Загрузка переменных окружения
load_dotenv()

# Настройка
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
LOCATION = {
    "name": "Горный курорт",
    "lat": 43.68,
    "lon": 40.28,
    "elevation": 1500
}

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Клавиатура
keyboard = [["Погода сейчас", "Прогноз"], ["Оповещения"]]
reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"⛰️ Погодный бот для {LOCATION['name']} (высота: {LOCATION['elevation']}м)\n"
        "Выберите действие:",
        reply_markup=reply_markup
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "Погода сейчас":
        await update.message.reply_text("🌡️ Сейчас: -5°C, ☁️ облачно")
    elif text == "Прогноз":
        await update.message.reply_text("❄️ Завтра: -3°C днем, -8°C ночью")
    elif text == "Оповещения":
        await update.message.reply_text("⚠️ Возможен снегопад в 18:00")


def main():
    if not TELEGRAM_TOKEN:
        logger.error("Токен Telegram не найден! Проверьте файл .env")
        return

    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Бот запущен...")
    application.run_polling()


if __name__ == "__main__":
    main()