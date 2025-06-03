# tests/test_utils.py
from datetime import datetime, timedelta
from bot.utils import format_weather_data, check_thunderstorm
from bot.config import THUNDERSTORM_CODES


def test_format_weather_data():
    test_data = {
        "current": {
            "temp_c": 20,
            "condition": {"text": "Sunny"},
            "feelslike_c": 22,
            "wind_kph": 10,
            "wind_dir": "N",
            "humidity": 50,
            "precip_mm": 0
        },
        "forecast": {
            "forecastday": [{
                "day": {
                    "maxtemp_c": 25,
                    "mintemp_c": 15,
                    "daily_chance_of_rain": 0,
                    "uv": 5
                }
            }]
        }
    }

    result = format_weather_data(test_data, "Тестовая точка")
    assert "🌤️ **Погода на Тестовая точка**" in result
    assert "• **Сейчас:** 20°C, Sunny" in result