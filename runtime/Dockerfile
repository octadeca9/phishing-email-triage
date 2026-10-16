FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN groupadd --system lab && useradd --system --gid lab --home-dir /home/lab lab \
    && mkdir -p /workspace /data /home/lab \
    && chown -R lab:lab /workspace /home/lab

WORKDIR /workspace
COPY --chown=lab:lab tools/ /opt/lab-tools/
COPY --chown=lab:lab entrypoint.sh /usr/local/bin/lab-entrypoint
RUN chmod 0555 /usr/local/bin/lab-entrypoint && chmod -R 0555 /opt/lab-tools
USER lab
ENV PATH="/opt/lab-tools:${PATH}"
ENTRYPOINT ["/usr/local/bin/lab-entrypoint"]
CMD ["sh"]
