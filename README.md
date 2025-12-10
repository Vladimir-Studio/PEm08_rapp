# Анализатор (мониторинг конкурентов — текст, изображения, парсинг сайтов)

Полноценный MVP на FastAPI + ванильный фронтенд для анализа конкурентов по тексту, изображениям и страницам сайтов (через Playwright). Есть история запросов и fallback-логика для пустых ответов модели.

## Возможности
- Анализ текста конкурента → сильные/слабые стороны, УТП, рекомендации, summary.
- Анализ изображения (баннер/сайт/упаковка) → описание, инсайты, оценка стиля, разбор стиля, рекомендации.
- Парсинг сайта через Playwright → скриншот, извлечение контента, анализ (с дизайн-метриками и идеями анимаций).
- История последних запросов (тип, краткое описание, резюме ответа) с очисткой.
- Одностраничный UI с меню и серой цветовой схемой.

## Стек
- Backend: Python 3.10+, FastAPI, OpenAI API (или Proxy совместимые), Playwright (Chromium), BeautifulSoup4, httpx.
- Frontend: HTML + CSS + JS (vanilla).

## Структура
```
backend/
  config.py
  main.py
  models/schemas.py
  services/
    openai_service.py
    parser_service.py   # Playwright, скриншот + контент
    history_service.py
frontend/
  index.html
  styles.css
  app.js
.env.example
requirements.txt
run.py
README.md
```

## Установка и запуск
```bash
python -m venv .venv
.venv\Scripts\activate         # Windows
# source .venv/bin/activate    # Linux/macOS

pip install -r requirements.txt
python -m playwright install chromium
```

Создайте `.env` на основе `.env.example`:
```
OPENAI_API_KEY=sk-...           # или PROXY_API_KEY с совместимым API
PROXY_API_KEY=
PROXY_API_BASE_URL=https://api.proxyapi.ru/openai/v1
OPENAI_MODEL=gpt-4o-mini
OPENAI_VISION_MODEL=gpt-4o-mini
API_HOST=0.0.0.0
API_PORT=8000
```

Запуск:
```bash
python run.py
```
Фронтенд: http://localhost:8000
Документация Swagger: http://localhost:8000/docs

## Использование API (кратко)
- `POST /analyze_text` `{ "text": "..." }`
- `POST /analyze_image` multipart `file=@image.jpg`
- `POST /parse_demo` `{ "url": "https://example.com" }`
- `GET /history` — история, `DELETE /history` — очистка.

## UI
- Левое меню: Анализ текста / Анализ изображения / Парсинг сайта / История.
- Цветовая схема: серая; карточки с читабельным форматированием результатов (не JSON).
- История с иконками по типу запроса.

## Особенности
- Парсинг через Playwright (Chromium headless) с ожиданием загрузки и скриншотом.
- Fallback: если модель вернёт пустые списки при парсинге/визионе, используется детерминированный анализ.
- Дизайн-поля (design_score, animation_potential) добавляются для парсинга и визион анализа; для текстового анализа не возвращаются.

## Тестовые шаги
- Текст: `curl -X POST http://localhost:8000/analyze_text -H "Content-Type: application/json" -d "{\"text\":\"Наши окна...\"}"`
- Изображение: `curl -X POST http://localhost:8000/analyze_image -F "file=@banner.jpg"`
- Парсинг: `curl -X POST http://localhost:8000/parse_demo -H "Content-Type: application/json" -d "{\"url\":\"https://example.com\"}"`

## Очистка истории
```bash
curl -X DELETE http://localhost:8000/history
```

## Требования
- Python 3.10+
- Установленный Chromium через `python -m playwright install chromium`
- Доступ к OpenAI-совместимому API и интернет для парсинга

## Лицензия
MIT

