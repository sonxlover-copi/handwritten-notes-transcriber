# Local RAG Assistant

Локальный RAG-сервис для ответов по внутренней документации. FastAPI принимает вопрос, LangChain ищет релевантные фрагменты в Chroma, а Ollama генерирует ответ локальной LLM. Документы и модель не отправляются во внешние AI API.

## Что демонстрирует проект

- Python: REST API, CLI-индексация документов, настройки через переменные окружения.
- Linux и Docker: запуск API и локальной модели через Docker Compose.
- Локальные LLM и embeddings: Ollama (`qwen2.5:3b`, `nomic-embed-text`).
- LangChain: text splitters, Ollama integrations, Chroma vector store.
- RAG: загрузка Markdown/TXT, разбиение на чанки, векторный поиск, ответы с источниками.

## Архитектура

```text
Markdown / TXT ──> ingest CLI ──> chunking ──> Ollama embeddings ──> Chroma
                                                                       │
Client ──HTTP──> FastAPI ──> retriever ────────────────────────────────┤
                         └──> grounded prompt ──> Ollama chat model <──┘
```

## Быстрый запуск (Linux + Docker Compose)

Нужны Docker Engine и Docker Compose plugin. Первый запуск скачает образы контейнеров и модели.

```bash
cp .env.example .env
docker compose up -d ollama
docker compose exec ollama ollama pull qwen2.5:3b
docker compose exec ollama ollama pull nomic-embed-text
docker compose up --build -d api
docker compose run --rm api python -m app.ingest
```

Проверить API:

```bash
curl http://localhost:8000/health
curl -X POST http://localhost:8000/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"Как добавить документы в индекс?"}'
```

Swagger UI: <http://localhost:8000/docs>

Добавьте свои `.md` и `.txt` файлы в `data/docs/`, затем повторно запустите команду индексации. Для локальной разработки без Docker установите зависимости из `requirements.txt`, запустите Ollama на Linux и выполните `python -m app.ingest` и `uvicorn app.main:app --reload`.

## API

`POST /ask`

```json
{
  "question": "Как добавить документы в индекс?",
  "top_k": 4
}
```

Ответ содержит сгенерированный текст и список найденных источников с оценками релевантности. Если подходящих фрагментов нет, сервис не вызывает LLM и сообщает, что данных недостаточно.

`GET /health` возвращает статус сервиса и выбранные модели.

## Настройки

Скопируйте `.env.example` в `.env`. Доступны `OLLAMA_BASE_URL`, `CHAT_MODEL`, `EMBEDDING_MODEL`, `CHROMA_DIR`, `DOCS_DIR`, `TOP_K` и `MIN_RELEVANCE`. Значения по умолчанию подходят для Compose.

## Структура

```text
app/
  config.py       # конфигурация из окружения
  ingest.py       # загрузка, чанкинг и индексация документов
  main.py         # FastAPI endpoints и grounded RAG цепочка
data/docs/        # документы для индексации
```

## Ограничения демо

- Поддерживаются Markdown и обычный текст; PDF-парсер можно добавить отдельным loader.
- Chroma хранится на локальном volume и подходит для одного экземпляра сервиса.
- Доступ к API в демо не защищён аутентификацией; не публикуйте порт в интернет без защиты.
- Качество ответа зависит от выбранных моделей, чанкинга и содержания документов.

## Остановка

```bash
docker compose down
```

Чтобы также удалить локальную модель и векторный индекс: `docker compose down -v`.
