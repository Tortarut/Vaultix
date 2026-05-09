# Vaultix (backend)

Vaultix — серверная часть учебного проекта «онлайн‑банк», реализованная на **Django** и **Django REST Framework**.
Система предоставляет REST API для выполнения банковских операций и ведения учёта по счетам.

### Развёртывание

- **Сервер**: `http://vaultix123.duckdns.org`
- **Интерактивная документация (Swagger UI)**: `http://vaultix123.duckdns.org/api/docs/`

### Стек

- **Python 3.12**
- **Django 5.2**, **DRF**
- **JWT** (`djangorestframework-simplejwt`)
- **OpenAPI/Swagger** (`drf-spectacular`)
- **PostgreSQL 16** (в Docker); также поддерживается SQLite (при отсутствии настроек PostgreSQL)

## Быстрый старт (Docker)

### 1) Подготовка переменных окружения

Перед запуском необходимо подготовить файл переменных окружения. В репозитории предоставлен пример `.env.example`.

```bash
cp .env.example .env
```

Файл `.env` используется для конфигурации параметров приложения и подключения к базе данных.

### 2) Сборка и запуск

```bash
docker compose up -d --build
```

Проверка статуса контейнеров:

```bash
docker compose ps
```

### 3) Миграции

При старте контейнер `web` выполняет миграции автоматически. При необходимости миграции можно выполнить вручную:

```bash
docker compose exec web python manage.py migrate
```

## Полезные адреса

- OpenAPI schema: `/api/schema/`
- Swagger UI: `/api/docs/`

## Тесты и покрытие

Запуск тестов:

```bash
python manage.py test
```
