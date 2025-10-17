import os
import logging
from typing import Optional


class BackgroundManager:
    def __init__(self, videos_dir: str = "videos"):
        """
        Менеджер для управления видео-фонами погодного бота

        Args:
            videos_dir: Папка с видео файлами
        """
        self.videos_dir = videos_dir
        self.weather_videos = {
            'clear': 'sunny.mp4',
            'sunny': 'sunny.mp4',
            'clouds': 'default.mp4',  # Используем default для облаков
            'cloudy': 'default.mp4',
            'rain': 'storm.mp4',
            'storm': 'storm.mp4',
            'thunderstorm': 'storm.mp4',
            'snow': 'default.mp4',  # Используем default для снега
            'fog': 'default.mp4',  # Используем default для тумана
            'mist': 'default.mp4',
            'default': 'default.mp4'
        }

        # Проверяем существование файлов
        self._check_video_files()

        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def _check_video_files(self):
        """Проверяет наличие всех видео файлов"""
        missing_files = []

        for video_file in set(self.weather_videos.values()):
            video_path = os.path.join(self.videos_dir, video_file)
            if not os.path.exists(video_path):
                missing_files.append(video_file)

        if missing_files:
            self.logger.warning(f"Отсутствуют видео файлы: {missing_files}")

    def get_video_for_weather(self, weather_condition: str) -> Optional[str]:
        """
        Возвращает путь к видео файлу для указанного погодного условия

        Args:
            weather_condition: строка с описанием погоды

        Returns:
            Путь к видео файлу или None если файл не найден
        """
        if not weather_condition:
            return self._get_video_path('default')

        condition = weather_condition.lower().strip()

        # Поиск подходящего видео
        for weather_key, video_file in self.weather_videos.items():
            if weather_key in condition:
                video_path = self._get_video_path(video_file)
                if os.path.exists(video_path):
                    self.logger.info(f"Найдено видео для '{condition}': {video_file}")
                    return video_path
                else:
                    self.logger.warning(f"Файл не найден: {video_path}")

        # Возвращаем default если ничего не нашли
        default_path = self._get_video_path('default.mp4')
        self.logger.info(f"Используется default видео для: {condition}")
        return default_path if os.path.exists(default_path) else None

    def _get_video_path(self, filename: str) -> str:
        """Возвращает полный путь к видео файлу"""
        return os.path.join(self.videos_dir, filename)

    def get_available_weather_conditions(self) -> list:
        """Возвращает список поддерживаемых погодных условий"""
        return list(self.weather_videos.keys())

    def list_available_videos(self) -> dict:
        """Возвращает информацию о доступных видео файлах"""
        available_videos = {}

        for weather_type, video_file in self.weather_videos.items():
            video_path = self._get_video_path(video_file)
            exists = os.path.exists(video_path)
            available_videos[weather_type] = {
                'video_file': video_file,
                'full_path': video_path,
                'exists': exists
            }

        return available_videos


# Пример использования
if __name__ == "__main__":
    # Тестирование менеджера
    bg_manager = BackgroundManager()

    # Проверяем доступные видео
    print("📹 Доступные видео:")
    videos_info = bg_manager.list_available_videos()
    for weather_type, info in videos_info.items():
        status = "✅" if info['exists'] else "❌"
        print(f"{status} {weather_type}: {info['video_file']}")

    # Тестируем поиск видео для разных условий
    test_conditions = ['sunny', 'rain', 'storm', 'cloudy', 'snow', 'fog', 'unknown']

    print("\n🧪 Тестирование поиска видео:")
    for condition in test_conditions:
        video_path = bg_manager.get_video_for_weather(condition)
        if video_path:
            print(f"🌤️ '{condition}' -> {os.path.basename(video_path)}")
        else:
            print(f"❌ '{condition}' -> видео не найдено")