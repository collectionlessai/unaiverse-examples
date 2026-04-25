#!/bin/bash

# Class Incremental Learning - launcher
# Usage: ./run.sh
#
# Two modes:
#   GUI      — tmux dashboard showing only user-facing messages
#   Terminal — screen sessions, attach individually
#
# Screen commands (Terminal mode):
#   screen -r cil-world          -> attach to world
#   screen -r cil-teacher        -> attach to teacher
#   screen -r cil-student        -> attach to student
#   Ctrl+A then D                -> detach from a screen
#   screen -ls                   -> list all sessions
#
# Tmux commands (GUI mode):
#   Ctrl+B then D                -> detach
#   tmux attach -t cil           -> reattach
#   tmux kill-session -t cil     -> stop everything

SCRIPT_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

SCRIPTS=("run_w.py" "run_teacher.py" "run_student_cnn.py")
LABELS=("World" "Teacher" "Student")
SCREEN_SESSIONS=("cil-world" "cil-teacher" "cil-student")
TMUX_SESSION="cil"

# --- Mode selection ---
echo ""
echo "=== Class Incremental Learning ==="
echo ""
echo "  1) GUI         (tmux dashboard, user messages only)"
echo "  2) Terminal    (screen sessions, full control)"
echo ""
read -rp "Select mode [1/2]: " RUN_MODE
RUN_MODE=${RUN_MODE:-1}

# =====================================================================
#  GUI MODE — tmux with USER-only output
# =====================================================================
if [[ "$RUN_MODE" == "1" ]]; then

    # Kill old tmux session if running
    if tmux has-session -t "$TMUX_SESSION" 2>/dev/null; then
        read -rp "Session '$TMUX_SESSION' already running. Kill and restart? [y/N] " answer
        if [[ ! "$answer" =~ ^[Yy]$ ]]; then
            echo "Aborted."
            exit 0
        fi
        tmux kill-session -t "$TMUX_SESSION" 2>/dev/null
        sleep 2
    fi

    # Clean up old log files
    JSONL_COUNT=$(find "$SCRIPT_DIR" -maxdepth 1 -name "*.jsonl" 2>/dev/null | wc -l)
    if [ "$JSONL_COUNT" -gt 0 ]; then
        rm -f "$SCRIPT_DIR"/*.jsonl
    fi

    # Env: show only USER/ERROR/CRITICAL on console, log everything to file
    ENV_EXPORTS="export NODE_LOG=1 NODE_PRINT=1 NODE_SCREEN_BASIC_PRINT=1 NODE_LIBP2PLOG=0 HF_HUB_DISABLE_TELEMETRY=1"

    # Start World in background (no pane)
    echo "Starting World in background..."
    bash -c "${ENV_EXPORTS}; cd \"$SCRIPT_DIR\"; python3 \"${SCRIPTS[0]}\"" &>/dev/null &
    WORLD_PID=$!
    echo "  -> World PID: $WORLD_PID"
    sleep 10

    # Build tmux layout:
    #  +-------------+----------+
    #  |             |          |
    #  |   Teacher   | Student  |
    #  |   (50%)     |  (50%)   |
    #  |             |          |
    #  +-------------+----------+

    # Pane 0: Teacher (left, 50%)
    tmux new-session -d -s "$TMUX_SESSION" -x "$(tput cols)" -y "$(tput lines)" \
        "bash -c '${ENV_EXPORTS}; cd \"$SCRIPT_DIR\"; echo \"=== Teacher ===\"; echo \"\"; python3 \"${SCRIPTS[1]}\"; echo \"\"; echo \">>> Teacher exited <<<\"; exec bash'"

    sleep 10

    # Pane 1: Student (right, 50%)
    tmux split-window -h -t "$TMUX_SESSION" -p 50 \
        "bash -c '${ENV_EXPORTS}; cd \"$SCRIPT_DIR\"; echo \"=== Student ===\"; echo \"\"; python3 \"${SCRIPTS[2]}\"; echo \"\"; echo \">>> Student exited <<<\"; exec bash'"

    # Pane titles and style
    tmux select-pane -t "$TMUX_SESSION:0.0" -T "Teacher"
    tmux select-pane -t "$TMUX_SESSION:0.1" -T "Student"
    tmux set-option -t "$TMUX_SESSION" pane-border-status top
    tmux set-option -t "$TMUX_SESSION" pane-border-format " #{pane_title} "

    # Focus on Teacher
    tmux select-pane -t "$TMUX_SESSION:0.0"

    echo ""
    echo "=== GUI started ==="
    echo "  Detach:    Ctrl+B then D"
    echo "  Reattach:  tmux attach -t $TMUX_SESSION"
    echo "  Stop all:  tmux kill-session -t $TMUX_SESSION"
    echo "  Logs:      $SCRIPT_DIR/*.jsonl"
    echo ""

    tmux attach-session -t "$TMUX_SESSION"

    # After detach/exit: kill background world process
    if kill -0 "$WORLD_PID" 2>/dev/null; then
        echo "Stopping World (PID $WORLD_PID)..."
        kill "$WORLD_PID" 2>/dev/null
    fi
    exit 0
fi

# =====================================================================
#  TERMINAL MODE — screen sessions (original behavior)
# =====================================================================

# --- Log configuration ---
echo ""
echo "--- Log Configuration ---"
echo ""
echo "  1) No logs       (default: console only, minimal output)"
echo "  2) File only      (all channels to file, console minimal)"
echo "  3) Full verbose   (all channels to file AND console)"
echo ""
read -rp "Select log mode [1/2/3]: " LOG_MODE
LOG_MODE=${LOG_MODE:-1}

export NODE_LOG=0
export NODE_PRINT=0
export NODE_SCREEN_BASIC_PRINT=0
export NODE_LIBP2PLOG=0

case "$LOG_MODE" in
    2)
        export NODE_LOG=1
        export NODE_PRINT=1
        export NODE_SCREEN_BASIC_PRINT=1
        echo ""
        echo "  -> File logging ON, console minimal"
        echo "  -> Log files will be in: $SCRIPT_DIR/*.jsonl"
        ;;
    3)
        export NODE_LOG=1
        export NODE_PRINT=1
        echo ""
        echo "  -> File logging ON, console verbose (all channels)"
        echo "  -> Log files will be in: $SCRIPT_DIR/*.jsonl"
        ;;
    *)
        echo ""
        echo "  -> No file logging, console minimal"
        ;;
esac
echo ""

# --- Show running sessions ---
echo "=== Class Incremental Learning Launcher ==="
echo ""
echo "Currently running sessions:"
ANY_RUNNING=false
for sess in "${SCREEN_SESSIONS[@]}"; do
    if screen -ls | grep -q "$sess"; then
        echo "  -> $sess (running)"
        ANY_RUNNING=true
    fi
done
if ! $ANY_RUNNING; then
    echo "  (none)"
fi
echo ""

# --- Ask before killing existing sessions ---
if $ANY_RUNNING; then
    read -rp "Kill existing sessions and restart? [y/N] " answer
    if [[ ! "$answer" =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 0
    fi
    for sess in "${SCREEN_SESSIONS[@]}"; do
        for sid in $(screen -ls | grep "$sess" | awk '{print $1}'); do
            echo "Killing $sid..."
            screen -S "$sid" -X quit 2>/dev/null
        done
    done
    echo "Waiting 5 seconds for processes to die..."
    sleep 5
fi

# --- Clean up old log files ---
JSONL_COUNT=$(find "$SCRIPT_DIR" -maxdepth 1 -name "*.jsonl" 2>/dev/null | wc -l)
if [ "$JSONL_COUNT" -gt 0 ]; then
    echo "Removing $JSONL_COUNT old .jsonl log file(s)..."
    rm -f "$SCRIPT_DIR"/*.jsonl
fi

# --- Launch each script in a screen session ---
for i in "${!SCRIPTS[@]}"; do
    SCRIPT="${SCRIPTS[$i]}"
    SESSION="${SCREEN_SESSIONS[$i]}"
    LABEL="${LABELS[$i]}"

    echo "Starting ${LABEL} (${SCRIPT}) in screen '${SESSION}'..."

    screen -dmS "$SESSION" bash -c "
        export NODE_LOG=$NODE_LOG && \
        export NODE_PRINT=$NODE_PRINT && \
        export NODE_SCREEN_BASIC_PRINT=$NODE_SCREEN_BASIC_PRINT && \
        export NODE_LIBP2PLOG=$NODE_LIBP2PLOG && \
        export HF_HUB_DISABLE_TELEMETRY=1 && \
        cd '$SCRIPT_DIR' && \
        echo '========================================' && \
        echo '  ${LABEL} - ${SCRIPT}' && \
        echo '  Started at: $(date)' && \
        echo '  Log mode: $LOG_MODE (NODE_LOG=$NODE_LOG NODE_PRINT=$NODE_PRINT)' && \
        echo '  Attach: screen -r ${SESSION}' && \
        echo '  Detach: Ctrl+A then D' && \
        echo '========================================' && \
        echo '' && \
        python3 '$SCRIPT'; \
        echo ''; \
        echo '>>> Process exited with code \$? <<<'; \
        exec bash
    "

    echo "  -> Done! Attach with: screen -r ${SESSION}"

    if [ "$i" -lt $((${#SCRIPTS[@]} - 1)) ]; then
        echo "  Waiting 10 seconds before next..."
        sleep 10
    fi
done

echo ""
echo "=== All sessions started! ==="
echo ""
echo "Quick reference:"
echo "  screen -r cil-world      Attach to World"
echo "  screen -r cil-teacher    Attach to Teacher"
echo "  screen -r cil-student    Attach to Student"
echo "  screen -ls               List all sessions"
echo "  Ctrl+A then D            Detach from a screen"
echo ""
