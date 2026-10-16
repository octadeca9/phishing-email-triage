FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN groupadd --system validator && useradd --system --gid validator validator \
    && mkdir -p /app && chown -R validator:validator /app
WORKDIR /app
COPY --chown=validator:validator requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=validator:validator app.py task_definitions.public.json ./
# The answer key is provided via a runtime secret mount (/run/secrets/answer_key),
# never COPY'd into this image.
USER validator
EXPOSE 8080
CMD ["python", "app.py"]
