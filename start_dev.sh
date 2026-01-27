#!/bin/bash

# Configuration
BACKEND_DIR="backend"
FRONTEND_DIR="frontend"
SESSION_NAME="feynman-dev"

# ------------------------------------------------------------------
# Step 1: Ensure PostgreSQL is running
# ------------------------------------------------------------------
if service postgresql status | grep -q "down"; then
    echo "🔴 Postgres is down. Starting it now..."
    # 'sudo' might ask for your password here
    sudo service postgresql start
    echo "✅ Postgres started."
else
    echo "✅ Postgres is already running."
fi

# ------------------------------------------------------------------
# Step 2: Start the Development Environment (using tmux)
# ------------------------------------------------------------------

# Check if a session with this name already exists
tmux has-session -t $SESSION_NAME 2>/dev/null

if [ $? != 0 ]; then
    # Create a new session (starts in the current directory)
    tmux new-session -d -s $SESSION_NAME

    # --- Pane 1 (Left): Django ---
    # Rename the window
    tmux rename-window 'Dev Server'
    # Send commands to the first pane
    # Activate the python vitual environment
    tmux send-keys -t $SESSION_NAME "source .venv/bin/activate" C-m
    # Move into backend directory
    tmux send-keys -t $SESSION_NAME "cd $BACKEND_DIR" C-m
    # Activate the django server
    tmux send-keys -t $SESSION_NAME "python manage.py runserver" C-m

    # --- Pane 2 (Right): NPM ---
    # Split the window horizontally
    tmux split-window -h -t $SESSION_NAME
    # Move into frontend directory
    tmux send-keys -t $SESSION_NAME "cd $FRONTEND_DIR" C-m
    # Start npm
    tmux send-keys -t $SESSION_NAME "npm run dev" C-m

    # Select the left pane again
    tmux select-pane -t $SESSION_NAME:0.0
fi

# Attach to the session so you can see it
tmux attach-session -t $SESSION_NAME
