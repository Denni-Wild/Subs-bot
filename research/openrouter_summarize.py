import os
import requests
from dotenv import load_dotenv
import time
import re

# Загрузка API-ключа
load_dotenv()
API_KEY = os.getenv('OPENROUTER_API_KEY')

# Список бесплатных моделей OpenRouter
MODELS = [
    ("venice_uncensored", "venice/uncensored:free"),
    ("google_gemma_3n_2b", "google/gemma-3n-e2b-it:free"),
    ("tencent_hunyuan_a13b", "tencent/hunyuan-a13b-instruct:free"),
    ("tng_deepseek_r1t2_chimera", "tngtech/deepseek-r1t2-chimera:free"),
    ("cypher_alpha", "openrouter/cypher-alpha:free"),
    ("mistral_small_3_2_24b", "mistralai/mistral-small-3.2-24b-instruct:free"),
    ("kimi_dev_72b", "moonshotai/kimi-dev-72b:free"),
    ("deepseek_r1_0528_qwen3_8b", "deepseek/deepseek-r1-0528-qwen3-8b:free"),
    ("deepseek_r1_0528", "deepseek/deepseek-r1-0528:free"),
    ("sarvam_m", "sarvamai/sarvam-m:free"),
    ("mistral_devstral_small", "mistralai/devstral-small:free"),
    ("google_gemma_3n_4b", "google/gemma-3n-e4b-it:free"),
]

INPUT_FILE = "subtitles_DpQtKCcTMnQ_ru.txt"
PROMPT = "Кратко изложи основные мысли этого фрагмента текста."
ERROR_LOG = "errors.log"
CHUNK_SIZE = 1000

with open(INPUT_FILE, encoding="utf-8") as f:
    text = f.read()

def split_text(text, max_len):
    # Разбиваем текст на части по max_len символов, не разрывая слова
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

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
    "HTTP-Referer": "https://openrouter.ai/",
    "X-Title": "Subs-bot summary script"
}

def log_error(model_name, error_text):
    with open(ERROR_LOG, "a", encoding="utf-8") as logf:
        logf.write(f"[{model_name}] {error_text}\n")

chunks = split_text(text, CHUNK_SIZE)
print(f"Text split into {len(chunks)} chunks of up to {CHUNK_SIZE} characters.")

for model_name, model_id in MODELS:
    all_summaries = []
    for i, chunk in enumerate(chunks):
        data = {
            "model": model_id,
            "messages": [
                {"role": "system", "content": PROMPT},
                {"role": "user", "content": chunk}
            ]
        }
        answer = None
        for attempt in range(1, 4):
            try:
                response = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=120
                )
                response.raise_for_status()
                result = response.json()
                answer = result["choices"][0]["message"]["content"]
                break  # успех, выходим из цикла
            except Exception as e:
                err_msg = f"Chunk {i+1}/{len(chunks)} Attempt {attempt}: {e}\nResponse: {getattr(e, 'response', None)}"
                print(f"[{model_name}] {err_msg}")
                if hasattr(e, 'response') and getattr(e.response, 'status_code', None) == 429:
                    print(f"[PAUSE] 429 Too Many Requests. Waiting 60 seconds before retry...")
                    time.sleep(60)
                elif attempt == 3:
                    answer = f"Error after 3 attempts: {e}\nResponse: {getattr(e, 'response', None)}"
                    log_error(model_name, answer)
                else:
                    time.sleep(5)
        all_summaries.append(f"--- Chunk {i+1} ---\n{answer}\n")
        with open(f"summary_{model_name}_chunk_{i+1}.txt", "w", encoding="utf-8") as f:
            f.write(answer)
        print(f"[PAUSE] Waiting 10 seconds before next chunk...")
        time.sleep(10)
    # Собираем все краткие пересказы в один файл
    full_summary_path = f"summary_{model_name}_full.txt"
    with open(full_summary_path, "w", encoding="utf-8") as f:
        f.write("\n".join(all_summaries))
    print(f"Saved full summary from {model_name} to {full_summary_path}")

    # Финальный шаг: отправить все chunk-резюме в модель для общего итога
    final_prompt = "Суммируй эти пересказы в один общий итог."
    final_data = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": final_prompt},
            {"role": "user", "content": "\n".join(all_summaries)}
        ]
    }
    final_answer = None
    for attempt in range(1, 4):
        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=final_data,
                timeout=120
            )
            response.raise_for_status()
            result = response.json()
            final_answer = result["choices"][0]["message"]["content"]
            break
        except Exception as e:
            err_msg = f"FINAL SUMMARY Attempt {attempt}: {e}\nResponse: {getattr(e, 'response', None)}"
            print(f"[{model_name}] {err_msg}")
            if hasattr(e, 'response') and getattr(e.response, 'status_code', None) == 429:
                print(f"[PAUSE] 429 Too Many Requests (final summary). Waiting 60 seconds before retry...")
                time.sleep(60)
            elif attempt == 3:
                final_answer = f"Error after 3 attempts: {e}\nResponse: {getattr(e, 'response', None)}"
                log_error(model_name, final_answer)
            else:
                time.sleep(5)
    with open(f"summary_{model_name}_final.txt", "w", encoding="utf-8") as f:
        f.write(final_answer)
    print(f"Saved FINAL summary from {model_name} to summary_{model_name}_final.txt") 