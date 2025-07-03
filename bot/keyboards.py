# bot/keyboards.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from bot.config import LOCATIONS_C_SECTOR, LOCATION_EAST_SECTOR, ALL_LOCATIONS

def get_main_menu_keyboard() -> list[list[InlineKeyboardButton]]:
    """Клавиатура главного меню"""
    return [
        [InlineKeyboardButton("Центральный сектор", callback_data="sector:central")],
        [InlineKeyboardButton("Восточный сектор", callback_data="sector:east")],
        [InlineKeyboardButton("Все точки", callback_data="sector:all")],
        [InlineKeyboardButton("Проверить грозы", callback_data="check_thunder")]
    ]

def get_points_keyboard(locations: dict[str, str]) -> InlineKeyboardMarkup:
    """Клавиатура выбора точек"""
    keyboard = []
    for name in locations:
        keyboard.append([InlineKeyboardButton(name, callback_data=f"point:{name}")])
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")])
    return InlineKeyboardMarkup(keyboard)

def get_weather_details_keyboard() -> list[list[InlineKeyboardButton]]:
    """Клавиатура деталей погоды"""
    return [
        [InlineKeyboardButton("Прогноз на завтра", callback_data="tomorrow_forecast")],
        [InlineKeyboardButton("Опасные явления", callback_data="weather_alerts")],
        [InlineKeyboardButton("⬅️ Назад к точкам", callback_data="back_to_points")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]
    ]

# Добавьте в конец файла
def get_back_to_weather_keyboard() -> list[list[InlineKeyboardButton]]:
    return [
        [InlineKeyboardButton("⬅️ Назад к погоде", callback_data="back_to_weather")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]
    ]

def get_thunder_check_keyboard() -> list[list[InlineKeyboardButton]]:
    return [
        [InlineKeyboardButton("🔄 Обновить", callback_data="check_thunder")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]
    ]