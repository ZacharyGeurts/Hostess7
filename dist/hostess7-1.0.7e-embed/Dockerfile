# Hostess7 embed — minimal sovereign brain container
FROM python:3.12-slim AS builder

WORKDIR /build
COPY requirements.txt pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir --no-deps -e .

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    HOSTESS7_ROOT=/opt/hostess7 \
    HOSTESS7_BRAIN_STATE=/var/lib/hostess7/state \
    HOSTESS7_WEB_PORT=8080 \
    HOSTESS7_LOW_POWER=0 \
    HOSTESS7_LICENSE_MODE=war

WORKDIR /opt/hostess7

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin/hostess7-* /usr/local/bin/
COPY . .

RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir --no-deps -e . \
    && mkdir -p /var/lib/hostess7/state/snapshots \
    && chmod +x Hostess7.sh

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=3)"

CMD ["bash", "-lc", "hostess7-core start && hostess7-daemon"]