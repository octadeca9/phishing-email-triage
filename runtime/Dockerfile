FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=7681

# ttyd serves the locked-down shell over HTTP so the participant workspace is
# reachable in a browser on the deploy platform. It is not in the Debian slim
# repos, so fetch the official static binary matching the target architecture.
ARG TTYD_VERSION=1.7.7
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && arch="$(dpkg --print-architecture)" \
    && case "$arch" in \
         amd64) t=x86_64 ;; \
         arm64) t=aarch64 ;; \
         armhf) t=arm ;; \
         *) echo "unsupported architecture: $arch" >&2; exit 1 ;; \
       esac \
    && curl -fsSL -o /usr/local/bin/ttyd \
         "https://github.com/tsl0922/ttyd/releases/download/${TTYD_VERSION}/ttyd.${t}" \
    && chmod 0555 /usr/local/bin/ttyd \
    && apt-get purge -y curl \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --system lab && useradd --system --gid lab --home-dir /home/lab lab \
    && mkdir -p /workspace /data /home/lab \
    && chown -R lab:lab /workspace /home/lab

WORKDIR /workspace
COPY --chown=lab:lab tools/ /opt/lab-tools/
COPY --chown=lab:lab entrypoint.sh /usr/local/bin/lab-entrypoint
COPY --chown=lab:lab lab-shell /usr/local/bin/lab-shell
COPY --chown=lab:lab lab-web /usr/local/bin/lab-web
RUN chmod 0555 /usr/local/bin/lab-entrypoint /usr/local/bin/lab-shell \
        /usr/local/bin/lab-web \
    && chmod -R 0555 /opt/lab-tools
USER lab
ENV PATH="/opt/lab-tools:${PATH}"
EXPOSE 7681
ENTRYPOINT ["/usr/local/bin/lab-entrypoint"]
# Default: serve the web terminal. Override for a direct CLI, e.g.
#   docker compose run --rm lab sh
CMD ["lab-web"]
