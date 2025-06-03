# main.py
import asyncio
import logging
import os
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder

from bot.services import WeatherService
from bot.handlers import BotHandlers

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def main():
    load_dotenv()

    weather_service = WeatherService(os.getenv("WEATHER_API_KEY"))
    handlers = BotHandlers(weather_service)

    application = (
        ApplicationBuilder()
        .token(os.getenv("TELEGRAM_BOT_TOKEN"))
        .concurrent_updates(True)
        .build()
    )

    application.add_handler(handlers.get_conversation_handler())

    logger.info("Бот запущен")
    await application.run_polling()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен")