#!/bin/bash

docker run \
    --rm \
    -it \
    --name flake8 \
    -v "$(pwd):/app" \
    -w /app \
    alpine/flake8 \
    .

