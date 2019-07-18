FROM python:3.7.4 as img

FROM img as build

COPY requirements.txt /requirements.txt
RUN pip3 install \
    --no-cache-dir \
    -r /requirements.txt

COPY . /wtb
WORKDIR /wtb

RUN pip3 install \
    --no-cache-dir \
    .


FROM img

COPY --from=build /usr/local /usr/

ENV PYTHONUNBUFFERED 1

ENTRYPOINT wtb-bot
