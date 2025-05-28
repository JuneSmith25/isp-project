#!/bin/env bash

path=$(realpath $(dirname $0))
test -z $VIRTUAL_ENV && source $path/renderer/.venv/bin/activate

cargo build --manifest-path $path/simulation/Cargo.toml
# cargo build --release --manifest-path $path/simulation/Cargo.toml
python $path/renderer/main.py
