FROM python:3.7.4 as img

FROM img as build

COPY requirements.txt /requirements.txt
RUN pip3 install --no-warn-script-location --prefix=/pip-install -r /requirements.txt

COPY . /wtb
WORKDIR /wtb

#RUN python3 setup.py install --prefix
RUN pip3 install --no-warn-script-location --prefix=/pip-install .


FROM img

COPY --from=build /pip-install /usr/local

ENV PYTHONUNBUFFERED 1

ENTRYPOINT wtb-bot
