FROM python:3.6.3

ENV PYTHONUNBUFFERED 1

# try to cut some edges... just to speedup container rebuild
RUN pip3 install --no-cache-dir pymongo==3.5.1 python-telegram-bot==9.0.0 ipython debug

ADD . /wtb
WORKDIR /wtb

RUN python3 setup.py install

ENTRYPOINT wtb-bot
