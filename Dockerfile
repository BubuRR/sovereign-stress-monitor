# Использование легковесного базового образа Python 3.11 на Linux Alpine
FROM python:3.11-slim

# Установка системных зависимостей для сборки C-расширений (необходимы для numpy/scipy)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем и устанавливаем легкие промышленные зависимости одной строкой
RUN pip install --no-cache-dir fastapi uvicorn pandas streamlit plotly ruptures scipy numpy

# Копируем всю структуру репозитория внутрь контейнера
COPY . .

# Открываем порты: 8000 для FastAPI бэкэнда, 8501 для цветного дашборда Streamlit
EXPOSE 8000
EXPOSE 8501

# Команда по умолчанию запускает бэкэнд-сервер автоматизации в фоновом режиме
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
