FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production \
    HOST=0.0.0.0 \
    PORT=8000 \
    DATABASE_PATH=/data/bpip.sqlite3
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && groupadd --gid 10001 bpip \
    && useradd --uid 10001 --gid bpip --no-create-home bpip \
    && mkdir /data && chown bpip:bpip /data
COPY server.py wsgi.py gunicorn.conf.py ./
COPY web ./web
USER bpip
EXPOSE 8000
VOLUME ["/data"]
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.getenv('PORT','8000')+'/api/config',timeout=3)"
CMD ["gunicorn", "--config", "gunicorn.conf.py", "wsgi:application"]
