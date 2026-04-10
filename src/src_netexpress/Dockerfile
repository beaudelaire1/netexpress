FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements/ requirements/
RUN pip install --no-cache-dir -r requirements/prod.txt

# Copy project
COPY . .

# Collect static files at build time (no DB or real secret needed)
RUN DJANGO_SECRET_KEY=build-placeholder DJANGO_SETTINGS_MODULE=netexpress.settings.prod \
    python manage.py collectstatic --noinput

# Make start script executable
RUN chmod +x start.sh

# Expose port
EXPOSE 8000

# Run start script
CMD ["./start.sh"]
