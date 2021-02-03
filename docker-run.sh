#!/bin/bash
docker run \
    --mount type=bind,source=$(pwd)/pudl_dir/.,target=/home/jovyan/shared \
    --publish 127.0.0.1:8888:8888 \
    catalystcoop/pilot-hub:latest jupyter lab --ip 0.0.0.0
