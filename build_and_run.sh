#!/bin/bash

docker build -t wtb:latest . && TELEGRAM_TOKEN=`cat token` docker-compose up
