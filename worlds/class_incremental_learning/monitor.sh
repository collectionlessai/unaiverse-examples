#!/bin/bash

# Class Incremental Learning - Monitor
# Opens a tmux session with 3 panes attached to the screen sessions.
# Usage: ./monitor.sh
# Exit:  Ctrl+B then type :kill-session  (or just close the terminal)

TMUX_SESSION="cil-monitor"

SESSIONS=("cil-world" "cil-teacher" "cil-student")
LABELS=("World" "Teacher" "Student")

# Check that screen sessions are running
MISSING=()
for i in "${!SESSIONS[@]}"; do
    if ! screen -ls | grep -q "${SESSIONS[$i]}"; then
        MISSING+=("${LABELS[$i]} (${SESSIONS[$i]})")
    fi
done

if [ ${#MISSING[@]} -gt 0 ]; then
    echo "Warning: these screen sessions are not running:"
    for m in "${MISSING[@]}"; do
        echo "  - $m"
    done
    echo ""
    read -rp "Continue anyway? [y/N] " answer
    [[ ! "$answer" =~ ^[Yy]$ ]] && exit 0
fi

# Kill old monitor session if exists
tmux kill-session -t "$TMUX_SESSION" 2>/dev/null

# Build the layout:
#  +-----------+-----------+
#  |           |  Teacher  |
#  |   World   +-----------+
#  |           |  Student  |
#  +-----------+-----------+

tmux new-session -d -s "$TMUX_SESSION" -x "$(tput cols)" -y "$(tput lines)"

# Pane 0: World (left, full height)
tmux send-keys -t "$TMUX_SESSION" "screen -r cil-world 2>/dev/null || echo 'cil-world not running'" Enter

# Split right for Teacher
tmux split-window -h -t "$TMUX_SESSION"
tmux send-keys -t "$TMUX_SESSION" "screen -r cil-teacher 2>/dev/null || echo 'cil-teacher not running'" Enter

# Split bottom-right for Student
tmux split-window -v -t "$TMUX_SESSION"
tmux send-keys -t "$TMUX_SESSION" "screen -r cil-student 2>/dev/null || echo 'cil-student not running'" Enter

# Set pane titles
tmux select-pane -t "$TMUX_SESSION:0.0" -T "World"
tmux select-pane -t "$TMUX_SESSION:0.1" -T "Teacher"
tmux select-pane -t "$TMUX_SESSION:0.2" -T "Student"

# Show pane borders with titles
tmux set-option -t "$TMUX_SESSION" pane-border-status top
tmux set-option -t "$TMUX_SESSION" pane-border-format " #{pane_title} "

# Focus on World pane
tmux select-pane -t "$TMUX_SESSION:0.0"

# Attach
tmux attach-session -t "$TMUX_SESSION"
