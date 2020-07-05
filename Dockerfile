FROM python:3.8.3-alpine as img

ENV PIP_DISABLE_PIP_VERSION_CHECK=1
# false is new true:
# > To enable the boolean options --no-compile, --no-warn-script-location
# > and --no-cache-dir, falsy values have to be used
# (c) https://pip.pypa.io/en/stable/user_guide/#config-file
ENV PIP_NO_CACHE_DIR=false
ENV PATH="/opt/venv/bin:$PATH"


FROM img as build

RUN apk add gcc musl-dev libffi-dev libressl-dev

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
