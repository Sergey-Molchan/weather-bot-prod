import asyncio
import logging
from typing import Optional, Dict
import aiohttp

logger = logging.getLogger(__name__)


class WeatherService:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = None

    async def get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

    async def get_weather_data(self, location: str, days: int = 1) -> Optional[Dict]:
        url = f"http://api.weatherapi.com/v1/forecast.json?key={self.api_key}&q={location}&days={days}&alerts=yes"

        try:
            session = await self.get_session()
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                if response.status == 200:
                    return await response.json()
                logger.error(f"API error: {response.status}")
                return None
        except asyncio.TimeoutError:
            logger.warning("WeatherAPI request timeout")
            return None
        except Exception as e:
            logger.error(f"Connection error: {str(e)}")
            return None