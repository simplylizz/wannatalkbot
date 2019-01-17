FROM python:3.7.2

ENV PYTHONUNBUFFERED 1

COPY requirements.txt /requirements.txt
RUN pip3 install -r /requirements.txt

COPY . /wtb
WORKDIR /wtb

RUN python3 setup.py install

ENTRYPOINT wtb-bot
