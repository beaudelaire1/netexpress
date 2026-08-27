FROM node:22-bookworm-slim AS assets
WORKDIR /assets
COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts
COPY tailwind.config.js ./
COPY templates/ templates/
COPY static/ static/
RUN npm run build-css-prod

FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DJANGO_SETTINGS_MODULE=netexpress.settings.prod PORT=8000
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0 libjpeg62-turbo libopenjp2-7 fonts-dejavu-core ca-certificates && rm -rf /var/lib/apt/lists/*
COPY requirements/ requirements/
RUN pip install --no-cache-dir -r requirements/prod.txt
COPY . .
COPY --from=assets /assets/static/css/tailwind.css /app/static/css/tailwind.css
RUN python manage.py collectstatic --noinput --settings=netexpress.settings.build &&     useradd --uid 10001 --create-home app &&     mkdir -p /app/private_media /app/media && chown app:app /app/private_media /app/media &&     chmod +x /app/start.sh
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/readyz/', timeout=4)" || exit 1
CMD ["./start.sh"]
