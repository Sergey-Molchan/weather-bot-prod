# tests/test_keyboards.py
from bot.keyboards import (
    get_main_menu_keyboard,
    get_points_keyboard,
    get_weather_details_keyboard
)

def test_main_menu_keyboard():
    keyboard = get_main_menu_keyboard()
    assert len(keyboard) == 4
    assert keyboard[0][0].text == "Центральный сектор"
    assert keyboard[3][0].text == "Проверить грозы"

def test_points_keyboard():
    test_locations = {"Точка 1": "coord1", "Точка 2": "coord2"}
    keyboard = get_points_keyboard(test_locations)
    assert len(keyboard.inline_keyboard) == 3  # 2 точки + кнопка назад