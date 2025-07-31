from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.text_rank import TextRankSummarizer

INPUT_FILE = "subtitles_DpQtKCcTMnQ_ru.txt"
SUMMARY_FILE = "summary_sumy.txt"
SENTENCES_COUNT = 7  # Количество предложений в итоговом резюме

# Чтение исходного текста
with open(INPUT_FILE, encoding="utf-8") as f:
    text = f.read()

# Создание парсера и токенизатора
parser = PlaintextParser.from_string(text, Tokenizer("russian"))
summarizer = TextRankSummarizer()

# Генерация резюме
summary = summarizer(parser.document, SENTENCES_COUNT)

# Сохранение результата
with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
    for sentence in summary:
        f.write(str(sentence) + "\n")

print(f"Saved extractive summary to {SUMMARY_FILE}") 