#!/bin/bash

# config (working dir is the one where this script is stored)
SCRIPTS=("run_w.py" "run_1.py" "run_2_smolvlm.py")
LOG="on"
DEFAULT_VENV_DIR="$HOME/python_env"
declare -A VENV_DIR_MAP
VENV_DIR_MAP=(
    ["run_w.py"]=$DEFAULT_VENV_DIR
    ["run_1.py"]=$DEFAULT_VENV_DIR
    ["run_2_smolvlm.py"]=$DEFAULT_VENV_DIR
)
DEFAULT_PROC_DEVICE="cpu"
declare -A PROC_DEVICE_MAP
PROC_DEVICE_MAP=(
    ["run_w.py"]=$DEFAULT_PROC_DEVICE
    ["run_1.py"]="cuda:0"
    ["run_2_smolvlm.py"]="cuda:0"
)
WORKING_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# setup
cd "$WORKING_DIR" || exit 1
SESSION_NAME=$(basename "$WORKING_DIR")

# kill existing screen sessions
for SCRIPT in "${SCRIPTS[@]}"; do
    echo "Killing screen '${SESSION_NAME}-${SCRIPT}' (if existing), that was running $SCRIPT..."
    for session in $(screen -ls | grep "${SESSION_NAME}-${SCRIPT}" | awk '{print $1}'); do
        screen -S "$session" -X quit 2>/dev/null
    done
done

# wait for the processes to die
echo "Wait a moment (5 seconds)..."
sleep 5

# run the python scripts
for i in "${!SCRIPTS[@]}"; do
    SCRIPT="${SCRIPTS[$i]}"
    VENV_DIR="${VENV_DIR_MAP[$SCRIPT]:-$DEFAULT_VENV_DIR}"

    # set the device
    PROC_DEVICE="${PROC_DEVICE_MAP[$SCRIPT]:-$DEFAULT_PROC_DEVICE}"

    # handle logging flag
    rm -f "${SCRIPT}.log"
    if [ "$LOG" = "on" ]; then
        LOG_OPTS=(-L -Logfile "${SCRIPT}.log")
        NODE_PRINT=2
        NODE_LIBP2PLOG=1
    else
        LOG_OPTS=(-Logfile "${SCRIPT}.log")
        NODE_PRINT=0
        NODE_LIBP2PLOG=0
    fi

    echo "Starting '$SCRIPT' in screen '${SESSION_NAME}-${SCRIPT}' with 'PROC_DEVICE=$PROC_DEVICE'..."
    screen -dmS "${SESSION_NAME}-${SCRIPT}" "${LOG_OPTS[@]}" bash -c "
        source '$VENV_DIR/bin/activate' && \
        export PROC_DEVICE='$PROC_DEVICE' && \
        export NODE_PRINT='$NODE_PRINT' && \
        export NODE_LIBP2PLOG='$NODE_LIBP2PLOG' && \
        python3 '$SCRIPT';
        exec bash
    "
    echo "Done! You can attach with: screen -r ${SESSION_NAME}-${SCRIPT}"
    if [ "$i" -lt $((${#SCRIPTS[@]} - 1)) ]; then
        echo "Now wait a moment (10 seconds)..."
        sleep 10
    fi
done
