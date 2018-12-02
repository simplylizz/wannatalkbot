#!/bin/bash

if [ ! -f token ]; then
    echo "No token file in current dir was found"
    exit 1
fi

docker build -t wtb:latest . && TELEGRAM_API_TOKEN=`cat token` docker-compose up
