# bot/utils.py
from typing import Dict
from bot.config import THUNDERSTORM_CODES, ALERT_WINDOW
from datetime import datetime, timedelta

def format_weather_data(data: Dict, point_name: str) -> str:
    """Форматирование данных о погоде для вывода"""
    if not data or 'current' not in data:
        return "⚠️ Не удалось получить данные о погоде"

    current = data['current']
    forecast_day = data.get('forecast', {}).get('forecastday', [])
    forecast = forecast_day[0]['day'] if forecast_day else {}

    message = (
        f"🌤️ **Погода на {point_name}**\n"
        f"• **Сейчас:** {current['temp_c']}°C, {current['condition']['text']}\n"
        f"• **Ощущается как:** {current['feelslike_c']}°C\n"
        f"• **Ветер:** {current['wind_kph']} км/ч, {current['wind_dir']}\n"
        f"• **Влажность:** {current['humidity']}%\n"
        f"• **Осадки:** {current['precip_mm']} мм\n"
    )

    if forecast:
        message += (
            f"\n📅 **Прогноз на сегодня:**\n"
            f"• Макс: {forecast['maxtemp_c']}°C\n"
            f"• Мин: {forecast['mintemp_c']}°C\n"
            f"• Вероятность дождя: {forecast['daily_chance_of_rain']}%\n"
            f"• УФ-индекс: {forecast['uv']}"
        )

    alerts = check_thunderstorm(data)
    if alerts:
        message += f"\n\n⚠️ **Ожидаются грозы!**"
        for alert in alerts[:3]:
            message += f"\n▫️ {alert['time']} - {alert['condition']} ({alert['chance']}%)"

    return message

def check_thunderstorm(weather_data: Dict) -> list[dict]:
    """Проверка приближения грозы (для использования в utils)"""
    if not weather_data or 'forecast' not in weather_data:
        return []

    alerts = []
    try:
        for day in weather_data['forecast']['forecastday']:
            for hour in day['hour']:
                if hour['condition']['code'] in THUNDERSTORM_CODES:
                    alert_time = datetime.strptime(hour['time'], "%Y-%m-%d %H:%M")
                    time_window = datetime.now() + timedelta(hours=ALERT_WINDOW)

                    if datetime.now() < alert_time < time_window:
                        alerts.append({
                            "time": alert_time.strftime('%H:%M %d.%m'),
                            "condition": hour['condition']['text'],
                            "chance": hour['chance_of_thunder'],
                            "precip": hour['precip_mm'],
                            "wind": hour['wind_kph']
                        })
    except Exception as e:
        from bot.services import logger
        logger.error(f"Ошибка при обработке данных: {str(e)}")

    return alerts