# tests/test_services.py
import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta
from bot.services import WeatherService
from bot.config import THUNDERSTORM_CODES


@pytest.fixture
def weather_service():
    return WeatherService("test_api_key")


@pytest.mark.asyncio
async def test_get_weather_data_success(weather_service):
    mock_response = {"current": {"temp_c": 20}, "forecast": {}}

    with patch('aiohttp.ClientSession.get', new_callable=AsyncMock) as mock_get:
        mock_get.return_value.__aenter__.return_value.status = 200
        mock_get.return_value.__aenter__.return_value.json = AsyncMock(return_value=mock_response)

        result = await weather_service.get_weather_data("test_location")
        assert result == mock_response


@pytest.mark.asyncio
async def test_check_thunderstorm(weather_service):
    test_data = {
        "forecast": {
            "forecastday": [{
                "hour": [{
                    "time": (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M"),
                    "condition": {"code": THUNDERSTORM_CODES[0], "text": "Thunderstorm"},
                    "chance_of_thunder": 90,
                    "precip_mm": 5.0,
                    "wind_kph": 30
                }]
            }]
        }
    }

    alerts = weather_service.check_thunderstorm(test_data)
    assert len(alerts) == 1
    assert alerts[0]["chance"] == 90