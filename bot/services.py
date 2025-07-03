import aiohttp
import logging
from typing import Dict, Optional
from datetime import datetime, timedelta
from bot.config import THUNDERSTORM_CODES, ALERT_WINDOW

logger = logging.getLogger(__name__)



class WeatherService:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.weatherapi.com/v1"
        self.session = None

    async def _ensure_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()

    async def get_weather_data(self, location: str) -> Optional[Dict]:
        """Получает данные о погоде для указанной локации"""
        try:
            await self._ensure_session()
            params = {
                "key": self.api_key,
                "q": location,
                "days": 2,
                "alerts": "yes"
            }
            async with self.session.get(f"{self.base_url}/forecast.json", params=params) as resp:
                if resp.status == 200:
                    return await resp.json()
                return None
        except Exception as e:
            logger.error(f"API error: {e}")
            return None

    async def check_thunder(self) -> bool:
        """Проверяет наличие грозы через API"""
        try:
            data = await self.get_weather_data("Minsk")
            if not data:
                return False

            alerts = data.get("alerts", {}).get("alert", [])
            # Ищем русское слово "гроза" в описании событий
            return any("гроза" in alert.get("event", "").lower() for alert in alerts)
        except Exception as e:
            logger.error(f"Ошибка при проверке грозы: {e}")
            return False

    def check_thunderstorm(self, weather_data: Dict) -> list[dict]:
        """Проверка приближения грозы"""
        alerts = []
        try:
            if not weather_data or 'forecast' not in weather_data:
                return alerts

            now = datetime.now()
            time_window = now + timedelta(hours=ALERT_WINDOW)

            for day in weather_data['forecast']['forecastday']:
                for hour in day.get('hour', []):
                    if hour.get('condition', {}).get('code') in THUNDERSTORM_CODES:
                        alert_time = datetime.strptime(hour['time'], "%Y-%m-%d %H:%M")
                        if now < alert_time <= time_window:
                            alerts.append({
                                "time": alert_time.strftime('%H:%M %d.%m'),
                                "condition": hour['condition']['text'],
                                "chance": hour['chance_of_thunder'],
                                "precip": hour['precip_mm'],
                                "wind": hour['wind_kph']
                            })
        except Exception as e:
            logger.error(f"Ошибка при обработке данных: {str(e)}")

        return alerts


# services.py (добавить в класс WeatherService)
async def check_thunder_for_point(self, location: str) -> bool:
    """Проверяет наличие грозы для конкретной точки"""
    try:
        data = await self.get_weather_data(location)
        if not data:
            return False

        alerts = data.get("alerts", {}).get("alert", [])
        return any("гроза" in alert.get("event", "").lower() for alert in alerts)
    except Exception as e:
        logger.error(f"Ошибка при проверке грозы: {e}")
        return False