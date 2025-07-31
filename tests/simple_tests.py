#!/usr/bin/env python3
"""
Простые и быстрые тесты для Telegram YouTube Subtitles Bot
Запуск: python simple_tests.py
"""

import sys
import os
import re
from io import StringIO

# Добавляем текущую директорию в путь для импортов
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Импортируем функции для тестирования
try:
    from bot import extract_video_id, format_subtitles, MIN_REQUEST_INTERVAL
    from summarizer import TextSummarizer
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    print("Убедитесь, что bot.py и summarizer.py находятся в той же папке")
    sys.exit(1)


class SimpleTestRunner:
    """Простой класс для запуска тестов без pytest"""
    
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failed_tests = []
    
    def test(self, name, test_func):
        """Запускает один тест"""
        self.tests_run += 1
        print(f"🧪 Тест: {name}")
        
        try:
            test_func()
            print("   ✅ ПРОЙДЕН")
            self.tests_passed += 1
        except Exception as e:
            print(f"   ❌ ОШИБКА: {e}")
            self.tests_failed += 1
            self.failed_tests.append(name)
    
    def assert_equal(self, actual, expected, message=""):
        """Проверяет равенство значений"""
        if actual != expected:
            raise AssertionError(f"Ожидалось {expected}, получено {actual}. {message}")
    
    def assert_true(self, condition, message=""):
        """Проверяет истинность условия"""
        if not condition:
            raise AssertionError(f"Условие должно быть True. {message}")
    
    def assert_false(self, condition, message=""):
        """Проверяет ложность условия"""
        if condition:
            raise AssertionError(f"Условие должно быть False. {message}")
    
    def assert_not_none(self, value, message=""):
        """Проверяет, что значение не None"""
        if value is None:
            raise AssertionError(f"Значение не должно быть None. {message}")
    
    def summary(self):
        """Выводит итоги тестирования"""
        print("\n" + "="*50)
        print(f"📊 ИТОГИ ТЕСТИРОВАНИЯ:")
        print(f"   Всего тестов: {self.tests_run}")
        print(f"   ✅ Пройдено: {self.tests_passed}")
        print(f"   ❌ Ошибок: {self.tests_failed}")
        
        if self.tests_failed == 0:
            print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
            return True
        else:
            print(f"\n💥 Неудачные тесты: {', '.join(self.failed_tests)}")
            return False


# Создаем экземпляр тестера
runner = SimpleTestRunner()


def test_extract_video_id_youtube_watch():
    """Тест извлечения ID из обычной ссылки YouTube"""
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    video_id = extract_video_id(url)
    runner.assert_equal(video_id, "dQw4w9WgXcQ")


def test_extract_video_id_youtu_be():
    """Тест извлечения ID из короткой ссылки youtu.be"""
    url = "https://youtu.be/dQw4w9WgXcQ"
    video_id = extract_video_id(url)
    runner.assert_equal(video_id, "dQw4w9WgXcQ")


def test_extract_video_id_embed():
    """Тест извлечения ID из embed ссылки"""
    url = "https://www.youtube.com/embed/dQw4w9WgXcQ"
    video_id = extract_video_id(url)
    runner.assert_equal(video_id, "dQw4w9WgXcQ")


def test_extract_video_id_direct():
    """Тест извлечения ID из прямого ID"""
    video_id = extract_video_id("dQw4w9WgXcQ")
    runner.assert_equal(video_id, "dQw4w9WgXcQ")


def test_extract_video_id_invalid():
    """Тест с невалидными ссылками"""
    invalid_urls = [
        "https://www.google.com",
        "not a url",
        "https://youtube.com/invalid",
        "shortid"
    ]
    
    for url in invalid_urls:
        video_id = extract_video_id(url)
        runner.assert_equal(video_id, None, f"URL: {url}")


def test_format_subtitles_with_time():
    """Тест форматирования субтитров с временными метками"""
    transcript = [
        {'start': 0.0, 'text': 'Первая строка'},
        {'start': 65.5, 'text': 'Вторая строка'}
    ]
    
    result = format_subtitles(transcript, with_time=True)
    expected = "[00:00] Первая строка\n[01:05] Вторая строка"
    runner.assert_equal(result, expected)


def test_format_subtitles_plain():
    """Тест форматирования субтитров без временных меток"""
    transcript = [
        {'start': 0.0, 'text': 'Первая строка'},
        {'start': 65.5, 'text': 'Вторая строка'}
    ]
    
    result = format_subtitles(transcript, with_time=False)
    expected = "Первая строка\nВторая строка"
    runner.assert_equal(result, expected)


def test_summarizer_init():
    """Тест инициализации суммаризатора"""
    # Устанавливаем тестовый API ключ
    os.environ['OPENROUTER_API_KEY'] = 'test_key'
    
    summarizer = TextSummarizer()
    runner.assert_equal(summarizer.api_key, 'test_key')
    runner.assert_equal(summarizer.chunk_size, 1000)
    runner.assert_true(len(summarizer.models) >= 8)


def test_summarizer_split_text_short():
    """Тест разбивки короткого текста"""
    summarizer = TextSummarizer()
    text = "Короткий текст для теста"
    chunks = summarizer.split_text(text, max_len=100)
    
    runner.assert_equal(len(chunks), 1)
    runner.assert_equal(chunks[0], text)


def test_summarizer_split_text_long():
    """Тест разбивки длинного текста"""
    summarizer = TextSummarizer()
    words = ["слово"] * 100
    text = " ".join(words)
    chunks = summarizer.split_text(text, max_len=500)
    
    runner.assert_true(len(chunks) > 1)
    
    # Проверяем, что каждая часть не превышает лимит
    for chunk in chunks:
        runner.assert_true(len(chunk) <= 500)


def test_summarizer_get_models():
    """Тест получения списка моделей"""
    summarizer = TextSummarizer()
    models = summarizer.get_available_models()
    
    runner.assert_true(isinstance(models, list))
    runner.assert_true(len(models) >= 8)
    runner.assert_true(all(isinstance(model, str) for model in models))


def test_constants():
    """Тест констант бота"""
    runner.assert_true(MIN_REQUEST_INTERVAL > 0)
    runner.assert_true(isinstance(MIN_REQUEST_INTERVAL, (int, float)))


def test_regex_patterns():
    """Тест регулярных выражений"""
    from bot import YOUTUBE_REGEX
    
    # Тестируем различные форматы YouTube ссылок
    test_cases = [
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ]
    
    for url, expected_id in test_cases:
        match = re.search(YOUTUBE_REGEX, url)
        if match:
            runner.assert_equal(match.group(1), expected_id, f"URL: {url}")
        else:
            raise AssertionError(f"Не найден ID в URL: {url}")


def test_empty_inputs():
    """Тест обработки пустых входных данных"""
    # Пустая строка для извлечения ID
    video_id = extract_video_id("")
    runner.assert_equal(video_id, None)
    
    # Пустой список субтитров
    result = format_subtitles([], with_time=False)
    runner.assert_equal(result, "")
    
    result = format_subtitles([], with_time=True)
    runner.assert_equal(result, "")


def test_edge_cases():
    """Тест граничных случаев"""
    # Очень короткий ID
    video_id = extract_video_id("short")
    runner.assert_equal(video_id, None)
    
    # Субтитры с нулевым временем
    transcript = [{'start': 0, 'text': 'Тест'}]
    result = format_subtitles(transcript, with_time=True)
    runner.assert_equal(result, "[00:00] Тест")
    
    # Разбивка пустого текста
    summarizer = TextSummarizer()
    chunks = summarizer.split_text("", max_len=100)
    runner.assert_equal(len(chunks), 0)


def run_all_tests():
    """Запускает все тесты"""
    print("🚀 ЗАПУСК ПРОСТЫХ ТЕСТОВ")
    print("=" * 50)
    
    # Список всех тестов
    tests = [
        ("Извлечение ID из youtube.com/watch", test_extract_video_id_youtube_watch),
        ("Извлечение ID из youtu.be", test_extract_video_id_youtu_be),
        ("Извлечение ID из embed", test_extract_video_id_embed),
        ("Извлечение прямого ID", test_extract_video_id_direct),
        ("Обработка невалидных ссылок", test_extract_video_id_invalid),
        ("Форматирование с временными метками", test_format_subtitles_with_time),
        ("Форматирование без меток", test_format_subtitles_plain),
        ("Инициализация суммаризатора", test_summarizer_init),
        ("Разбивка короткого текста", test_summarizer_split_text_short),
        ("Разбивка длинного текста", test_summarizer_split_text_long),
        ("Получение списка моделей", test_summarizer_get_models),
        ("Проверка констант", test_constants),
        ("Регулярные выражения", test_regex_patterns),
        ("Пустые входные данные", test_empty_inputs),
        ("Граничные случаи", test_edge_cases),
    ]
    
    # Запускаем все тесты
    for name, test_func in tests:
        runner.test(name, test_func)
    
    # Выводим итоги
    success = runner.summary()
    
    return success


if __name__ == "__main__":
    print("📋 Простые тесты для Telegram YouTube Subtitles Bot")
    print("Эти тесты проверяют основной функционал без внешних API")
    print()
    
    try:
        success = run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️ Тестирование прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Критическая ошибка: {e}")
        sys.exit(1) 