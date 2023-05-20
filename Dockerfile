FROM python:3.11.3-slim as img

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PATH="/opt/venv/bin:$PATH"

FROM img as build

RUN python -m venv /opt/venv

COPY requirements.txt /requirements.txt
RUN pip install -r /requirements.txt

COPY . /wtb
WORKDIR /wtb

RUN pip install .


FROM img

COPY --from=build /opt/venv /opt/venv

ENV PYTHONUNBUFFERED 1

# runtime arg
ENV TELEGRAM_API_TOKEN=not-set

CMD wtb-bot
