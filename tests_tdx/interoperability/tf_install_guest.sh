#!/bin/bash
set -x

apt install -y python3-venv
python3 -m venv tensorflow_env
source tensorflow_env/bin/activate
pip install --upgrade pip
pip install tensorflow protobuf
