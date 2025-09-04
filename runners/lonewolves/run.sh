#!/bin/bash

# config (working dir is the one where this script is stored)
SCRIPTS=(run_*.py)
DEFAULT_VENV_DIR="$HOME/python_env"
declare -A VENV_DIR_MAP
VENV_DIR_MAP=(
    ["run_langsam.py"]="$HOME/python_env_langsam"
    ["run_smolvlm.py"]=$DEFAULT_VENV_DIR
    ["run_siterag.py"]="$HOME/python_env_rag"
    ["run_phi.py"]=$DEFAULT_VENV_DIR
    ["run_tinyllama.py"]=$DEFAULT_VENV_DIR
)
DEFAULT_PROC_DEVICE="cpu"
declare -A PROC_DEVICE_MAP
PROC_DEVICE_MAP=(
    ["run_langsam.py"]="cuda:0"
    ["run_smolvlm.py"]="cuda:0"
    ["run_siterag.py"]="cuda:1"
    ["run_phi.py"]="cuda:1"
    ["run_tinyllama.py"]="cuda:1"
)
WORKING_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# exit if no scripts found
if [ ${#SCRIPTS[@]} -eq 0 ]; then
    echo "No run_*.py scripts found in $WORKING_DIR"
    exit 1
fi

# show menu
echo "Select the lone-wolf script to run:"
for i in "${!SCRIPTS[@]}"; do
    printf "  %d) %s\n" $((i+1)) "${SCRIPTS[$i]}"
done

# ask for user input
read -rp "Enter the number of the script to run: " choice
index=$((choice-1))
if [ -z "${SCRIPTS[$index]}" ]; then
    echo "Invalid selection."
    exit 1
fi

# select the right script
SCRIPT="${SCRIPTS[$index]}"

# setup
cd "$WORKING_DIR" || exit 1
VENV_DIR="${VENV_DIR_MAP[$SCRIPT]:-$DEFAULT_VENV_DIR}"
SESSION_NAME=$(basename "$WORKING_DIR")

# set the device
PROC_DEVICE="${PROC_DEVICE_MAP[$SCRIPT]:-$DEFAULT_PROC_DEVICE}"

# kill existing screen session
echo "Killing screen '${SESSION_NAME}-${SCRIPT}' (if existing)..."
for session in $(screen -ls | grep "${SESSION_NAME}-${SCRIPT}" | awk '{print $1}'); do
    screen -S "$session" -X quit 2>/dev/null
done

# wait for the processes to die
echo "Wait a moment (5 seconds)..."
sleep 5

# run the python script
echo "Starting '$SCRIPT' in screen '${SESSION_NAME}-${SCRIPT}' with 'PROC_DEVICE=$PROC_DEVICE'..."
screen -dmS "${SESSION_NAME}-${SCRIPT}" bash -c "
    source '$VENV_DIR/bin/activate' && \
    export PROC_DEVICE='$PROC_DEVICE' && \
    python3 '$SCRIPT';
    exec bash
"
echo "Done! You can attach with: screen -r ${SESSION_NAME}-${SCRIPT}"
