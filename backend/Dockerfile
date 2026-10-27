FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
RUN groupadd --system linko && useradd --system --gid linko --home-dir /app linko
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN chown -R linko:linko /app
USER linko
EXPOSE 8000
# Single worker by default; scale via replicas behind reverse proxy after pool sizing.
CMD ["uvicorn","main:app","--host","0.0.0.0","--port","8000","--proxy-headers","--forwarded-allow-ips","127.0.0.1"]
