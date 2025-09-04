#!/bin/bash

# config (working dir is the one where this script is stored)
SCRIPT="run_demo_b.py"
GET_ADDRESSES="scp mela@multaiverse.diism.unisi.it:/home/mela/unaiverse_private/runners/info_extraction/addresses.txt ."
LOG="off"
PROC_DEVICE="cpu"
WORKING_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# setup
cd "$WORKING_DIR" || exit 1

# handle logging flag
if [ "$LOG" = "on" ]; then
    NODE_PRINT=2
    NODE_LIBP2PLOG=1
else
    NODE_PRINT=0
    NODE_LIBP2PLOG=0
fi

# running
bash -c "$GET_ADDRESSES"
export PROC_DEVICE="$PROC_DEVICE"
export NODE_PRINT="$NODE_PRINT"
export NODE_LIBP2PLOG="$NODE_LIBP2PLOG"
python3 "$SCRIPT"
