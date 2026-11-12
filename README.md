# Рукописный конспект → LaTeX и PDF

Локальное приложение, которое превращает фото или скан конспекта в структурированный документ. Модель распознаёт заголовки, абзацы, пункты и формулы; приложение создаёт из структуры LaTeX и собирает PDF. Из браузера можно скачать PDF и исходный `.tex` для ручной правки.

## Возможности

- Загрузка изображений (`.png`, `.jpg`, `.jpeg`, `.webp`) и PDF.
- Структурирование текста на заголовки, абзацы, элементы списка и формулы.
- Генерация LaTeX по шаблону и сборка PDF локальным движком Tectonic.
- Пометки `⟦неразборчиво⟧` и `[формула требует проверки]` вместо догадок.
- FastAPI endpoints и интерактивная документация `/docs`.

## Как это работает

```text
Фото / PDF → Python готовит страницы → Qwen3-VL через Ollama → структура документа → LaTeX → PDF
```

Модель просят дословно переносить содержание, не решать задания с листа и отмечать сомнительные места. LaTeX генерируется приложением по шаблону: произвольный исходник от модели не исполняется. Рукописный текст всё равно нужно сверять с оригиналом.

## Запуск на Linux через Docker Compose

Нужны Docker Engine и Docker Compose plugin. Команды ниже включают GPU через NVIDIA Container Toolkit. Если toolkit не установлен, уберите `-f compose.gpu.yaml`; Ollama будет считать на CPU, но медленнее. Для Qwen3-VL нужен Ollama 0.12.7 или новее.

```bash
cp .env.example .env
docker compose -f compose.yaml -f compose.gpu.yaml up -d ollama
docker compose -f compose.yaml -f compose.gpu.yaml exec ollama ollama pull qwen3-vl:8b
docker compose -f compose.yaml -f compose.gpu.yaml up --build -d app
```

Откройте <http://localhost:8000>, загрузите фото или PDF и нажмите **«Распознать и скачать PDF»**. При первой сборке Docker загружает Tectonic и необходимые пакеты LaTeX; первый запуск отдельно скачивает веса модели. Тег `qwen3-vl:8b` занимает около 6,2 ГБ по каталогу Ollama. [Каталог Qwen3-VL](https://ollama.com/library/qwen3-vl)

Если модели не хватает видеопамяти, задайте `VISION_MODEL=qwen3-vl:4b` в `.env` и перезапустите приложение.

Чтобы остановить сервисы:

```bash
docker compose down
```

Чтобы удалить также модель и кэш LaTeX: `docker compose down -v`.

## HTTP API

`POST /transcribe` принимает файл как `multipart/form-data` и возвращает распознанные страницы, структуру документа и исходник `.tex`:

```bash
curl -X POST http://localhost:8000/transcribe \
  -F "file=@my_notes.pdf"
```

`POST /pdf` принимает поле `document` из ответа `/transcribe` и возвращает PDF:

```bash
curl -s -X POST http://localhost:8000/transcribe -F "file=@my_notes.pdf" \
  | jq '.document' > document.json
curl -X POST http://localhost:8000/pdf \
  -H 'Content-Type: application/json' \
  --data-binary @document.json \
  --output my_notes.pdf
```

Веб-интерфейс вызывает оба endpoint и скачивает PDF автоматически. Ограничение входа: 20 МБ и 20 страниц PDF. `/health` показывает состояние API и выбранную модель; Swagger UI доступен на <http://localhost:8000/docs>.

## Настройки

`VISION_MODEL` задаёт модель Ollama, `OLLAMA_BASE_URL` — адрес сервера моделей, `MAX_PDF_PAGES` — максимальное число страниц, `LATEX_COMPILER` — исполняемый файл Tectonic. По умолчанию используется `qwen3-vl:8b`.

## Структура проекта

```text
app/
  main.py          # HTTP API
  transcriber.py   # подготовка страниц и распознавание в JSON
  latex.py         # шаблон LaTeX и сборка PDF
  documents.py     # структуры данных для API
static/index.html  # браузерный интерфейс
tests/             # проверки API, преобразования страниц и LaTeX
evaluation/        # CER-скрипт и план оценки качества
```

## Проверка качества

В `evaluation/` описано, как собрать проверочный набор страниц. `evaluation/cer.py` сравнивает результат с ручной расшифровкой по Character Error Rate (CER): значение ближе к нулю означает меньше ошибок. Не включайте личные конспекты в публичный репозиторий.

```bash
python -m pip install -r requirements-dev.txt
pytest -q
```

## GitHub-проект, который послужил ориентиром

Ориентиром послужил ноутбук [handwriting-ocr-vlm](https://github.com/Slavaxexe/handwriting-ocr-vlm): там Qwen2.5-VL распознаёт русские рукописные страницы, а качество оценивается по CER. Автор сообщает о среднем CER около 0,173 на шести примерах. Лицензия в репозитории не указана, поэтому его код и изображения не копировались; это приложение написано самостоятельно.

## Ограничения

- Почерк и качество фото влияют на точность; тест на собственных конспектах пока не выполнен.
- Таблицы, схемы, мелкие подписи, формулы и имена могут распознаться неверно.
- Страницы обрабатываются локально; загрузка весов модели и пакетов LaTeX требует интернета.
- Перепроверьте PDF по оригиналу, особенно числа и формулы.
