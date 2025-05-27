#!/bin/env bash

path=$(realpath $(dirname $0))
test -z $VIRTUAL_ENV && source $path/renderer/.venv/bin/activate

cargo build --release --manifest-path $path/simulation/Cargo.toml
python $path/renderer/main.py
