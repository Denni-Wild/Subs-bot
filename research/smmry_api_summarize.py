import requests
import time
import re

API_KEY = "sk-smmry-0ae058216cceb199035f102b9c999e707d47389de29efdfa7ecc5a4b6bae08b9"
INPUT_FILE = "subtitles_DpQtKCcTMnQ_ru.txt"
CHUNK_SIZE = 7000  # Можно увеличить, если уверены в лимите
SUMMARY_FILE = "summary_smmry_full.txt"
FINAL_FILE = "summary_smmry_final.txt"


def split_text(text, max_len):
    words = re.findall(r'\S+|\n', text)
    chunks = []
    current = ''
    for word in words:
        if len(current) + len(word) + 1 > max_len:
            chunks.append(current.strip())
            current = word if word != '\n' else ''
        else:
            current += (' ' if current and word != '\n' and not current.endswith('\n') else '') + word
    if current.strip():
        chunks.append(current.strip())
    return chunks


def smmry_summarize(text):
    # Step 1: POST to process-summarize
    resp = requests.post(
        "https://smmry.com/api/process-summarize",
        headers={
            "Content-Type": "application/json",
            "x-api-key": API_KEY
        },
        json={"raw_text": text}
    )
    resp.raise_for_status()
    request_id = resp.json()["request_id"]
    # Step 2: GET the summary
    for _ in range(10):
        time.sleep(1)
        resp2 = requests.get(
            f"https://smmry.com/api/get-summary?request_id={request_id}",
            headers={"x-api-key": API_KEY}
        )
        if resp2.status_code == 200 and "summary" in resp2.json():
            return resp2.json()["summary"]
    return "[No summary returned]"


with open(INPUT_FILE, encoding="utf-8") as f:
    text = f.read()

chunks = split_text(text, CHUNK_SIZE)
print(f"Text split into {len(chunks)} chunks of up to {CHUNK_SIZE} characters.")

all_summaries = []
for i, chunk in enumerate(chunks):
    print(f"Processing chunk {i+1}/{len(chunks)}...")
    try:
        summary = smmry_summarize(chunk)
    except Exception as e:
        summary = f"Error: {e}"
    all_summaries.append(f"--- Chunk {i+1} ---\n{summary}\n")
    time.sleep(2)  # чтобы не перегружать API

with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
    f.write("\n".join(all_summaries))
print(f"Saved full summary to {SUMMARY_FILE}")

# Финальный шаг: суммировать все chunk-резюме в один общий итог
final_prompt = "Суммируй эти пересказы в один общий итог."
final_text = final_prompt + "\n" + "\n".join(all_summaries)
try:
    final_summary = smmry_summarize(final_text)
except Exception as e:
    final_summary = f"Error: {e}"

with open(FINAL_FILE, "w", encoding="utf-8") as f:
    f.write(final_summary)
print(f"Saved FINAL summary to {FINAL_FILE}") 