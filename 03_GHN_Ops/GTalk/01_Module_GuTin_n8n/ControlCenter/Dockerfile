FROM python:3.11-slim

WORKDIR /app

# Tối ưu hóa môi trường Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

# Cài đặt thư viện dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ mã nguồn
COPY . .

EXPOSE 8080

CMD ["python", "control_center.py"]
