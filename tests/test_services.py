import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime
from bot.services import WeatherService
from bot.config import THUNDERSTORM_CODES
from bot.config import THUNDERSTORM_CODES, ALERT_WINDOW

@pytest.mark.asyncio
async def test_get_weather_data_success(weather_service):
    mock_data = {"current": {"temp_c": 20}}

    # Исправленное мокирование асинхронных вызовов
    with patch('bot.services.aiohttp.ClientSession.get', new_callable=AsyncMock) as mock_get:
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value=mock_data)
        mock_get.return_value.__aenter__.return_value = mock_resp

        result = await weather_service.get_weather_data("test_location")
        assert result == mock_data


@pytest.mark.asyncio
async def test_check_thunder(weather_service):
    # Используем русский текст
    mock_data = {
        "alerts": {
            "alert": [{"event": "Гроза"}]
        }
    }

    # Мокируем get_weather_data напрямую
    with patch.object(WeatherService, 'get_weather_data', AsyncMock(return_value=mock_data)):
        result = await weather_service.check_thunder()
        assert result is True


def test_check_thunderstorm(weather_service):
    test_data = {
        "forecast": {
            "forecastday": [{
                "hour": [
                    {
                        "time": "2023-01-01 10:00",
                        "condition": {"text": "Ясно", "code": 1000},
                        "chance_of_thunder": 0,
                        "wind_kph": 10,
                        "precip_mm": 0
                    },
                    {
                        "time": "2023-01-01 12:00",
                        "condition": {"text": "Гроза", "code": THUNDERSTORM_CODES[0]},
                        "chance_of_thunder": 60,
                        "wind_kph": 30,
                        "precip_mm": 5
                    }
                ]
            }]
        }
    }

    # Исправленное мокирование времени
    with patch('bot.services.datetime') as mock_datetime:
        # Фиксируем текущее время
        mock_datetime.now.return_value = datetime(2023, 1, 1, 9, 0)

        # Мокируем timedelta
        mock_datetime.timedelta = lambda **kw: datetime.timedelta(**kw)

        alerts = weather_service.check_thunderstorm(test_data)
        assert len(alerts) == 1
        assert alerts[0]["time"] == "12:00 01.01"

