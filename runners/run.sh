#!/bin/bash
# This is a parent script to manage worlds and lone wolves.

# detect all world folders (directories containing run.sh)
WORLD_DIRS=()
for d in */; do
    if [[ -f "$d/run.sh" ]]; then
        WORLD_DIRS+=("${d%/}")
    fi
done

if [[ ${#WORLD_DIRS[@]} -eq 0 ]]; then
    echo "No worlds/lone-wolves found (no run.sh in subfolders)."
    exit 1
fi

echo "=== World/Lone-wolf Manager ==="
echo

# list running screen sessions
RUNNING_SESSIONS=$(screen -ls | grep -o '[0-9]*\.\S*' | cut -d. -f2-)

echo "Currently open sessions:"
ANY_RUNNING=false
for world in "${WORLD_DIRS[@]}"; do
    MATCH=$(echo "$RUNNING_SESSIONS" | grep "^${world}-" || true)
    if [[ -n "$MATCH" ]]; then
        echo "  -> $world (running sessions: $(echo "$MATCH" | xargs))"
        ANY_RUNNING=true
    fi
done
if ! $ANY_RUNNING; then
    echo "  (none)"
fi

echo
echo "Available worlds to run (select 'lonewolves' to trigger an additional menu):"
for i in "${!WORLD_DIRS[@]}"; do
    num=$((i+1))
    echo "  $num) ${WORLD_DIRS[$i]}"
done
echo
read -p "Select what to run (number): " choice

# validate input
if ! [[ "$choice" =~ ^[0-9]+$ ]]; then
    echo "Invalid input. Must be a number."
    exit 1
fi

if (( choice < 1 || choice > ${#WORLD_DIRS[@]} )); then
    echo "Choice out of range."
    exit 1
fi

# run the selected world
WORLD="${WORLD_DIRS[$((choice-1))]}"
echo "Launching '$WORLD'..."
cd "$WORLD" || { echo "Failed to cd into $WORLD"; exit 1; }
./run.sh
