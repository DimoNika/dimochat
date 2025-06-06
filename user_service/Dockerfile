# Используем официальный базовый образ Python
FROM python:3.12

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

# Копируем зависимости
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Указываем команду по умолчанию (пример — запуск FastAPI через uvicorn)
# CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--reload"]
CMD ["python3", "main.py"]
