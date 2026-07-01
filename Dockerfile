# Используем стабильную версию Python
FROM python:3.11-slim

# Устанавливаем FFmpeg (обязательно для работы звука Craig-системы) и необходимые кодеки
RUN apt-get update && apt-get install -y \
    ffmpeg \
    build-essential \
    libffi-dev \
    libnacl-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Создаем рабочую директорию в контейнере
WORKDIR /app

# Копируем список зависимостей и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь остальной код проекта
COPY . .

# Команда для запуска бота
CMD ["python", "main.py"]
