FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt requirements.lock ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN python manage.py collectstatic --noinput
RUN useradd -m anma && mkdir -p /data && chown -R anma:anma /app /data
USER anma
EXPOSE 8000
CMD ["gunicorn","anma_cloud.wsgi:application","--bind","0.0.0.0:8000","--workers","2","--timeout","60"]
