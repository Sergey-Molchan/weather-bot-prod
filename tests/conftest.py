import pytest
from bot.services import WeatherService

@pytest.fixture
def weather_service():
    return WeatherService(api_key="test_key")