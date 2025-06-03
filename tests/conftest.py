import pytest
from unittest.mock import AsyncMock
from bot.services import WeatherService

@pytest.fixture
def mock_weather_service():
    service = WeatherService("test_key")
    service.get_weather_data = AsyncMock()
    return service