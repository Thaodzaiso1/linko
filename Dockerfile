# Linko V8: React + FastAPI in one Render service
FROM node:22-alpine AS frontend
WORKDIR /web
COPY Linko_V2/linko-web/package*.json ./
RUN npm ci
COPY Linko_V2/linko-web/ ./
RUN npm run build

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=10000
WORKDIR /app/backend
COPY Linko_V2/linko-fastapi/linko-fastapi/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY Linko_V2/linko-fastapi/linko-fastapi/ ./
COPY --from=frontend /web/dist /app/linko-static
EXPOSE 10000
CMD ["sh","-c","uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000} --proxy-headers"]
