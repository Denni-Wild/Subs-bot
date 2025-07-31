import requests
import time
import re

INPUT_FILE = "subtitles_DpQtKCcTMnQ_ru.txt"
CHUNK_SIZE = 7000  # лимит SMMRY
SUMMARY_FILE = "summary_smmry_full.txt"
API_URL = "https://api.smmry.com"

# Функция для деления текста на части по max_len символов, не разрывая слова
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

with open(INPUT_FILE, encoding="utf-8") as f:
    text = f.read()

chunks = split_text(text, CHUNK_SIZE)
print(f"Text split into {len(chunks)} chunks of up to {CHUNK_SIZE} characters.")

all_summaries = []
for i, chunk in enumerate(chunks):
    for attempt in range(1, 4):
        try:
            response = requests.post(
                API_URL,
                data={"sm_api_input": chunk},
                timeout=60
            )
            response.raise_for_status()
            result = response.json()
            summary = result.get("sm_api_content", "[No summary returned]")
            break
        except Exception as e:
            print(f"Chunk {i+1}/{len(chunks)} Attempt {attempt}: {e}")
            if attempt == 3:
                summary = f"Error after 3 attempts: {e}"
            else:
                time.sleep(5)
    all_summaries.append(f"--- Chunk {i+1} ---\n{summary}\n")
    print(f"[PAUSE] Waiting 5 seconds before next chunk...")
    time.sleep(5)

with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
    f.write("\n".join(all_summaries))
print(f"Saved full summary to {SUMMARY_FILE}")

# Финальный шаг: отправить все chunk-резюме в SMMRY для общего итога
final_prompt = "Суммируй эти пересказы в один общий итог."
final_text = final_prompt + "\n" + "\n".join(all_summaries)
final_summary = None
for attempt in range(1, 4):
    try:
        response = requests.post(
            API_URL,
            data={"sm_api_input": final_text},
            timeout=60
        )
        response.raise_for_status()
        result = response.json()
        final_summary = result.get("sm_api_content", "[No summary returned]")
        break
    except Exception as e:
        print(f"FINAL SUMMARY Attempt {attempt}: {e}")
        if attempt == 3:
            final_summary = f"Error after 3 attempts: {e}"
        else:
            time.sleep(5)
with open("summary_smmry_final.txt", "w", encoding="utf-8") as f:
    f.write(final_summary)
print("Saved FINAL summary to summary_smmry_final.txt") 