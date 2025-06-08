#!/usr/bin/env bash

tmux new-session -d -s 'osx-echo'

tmux send-keys -t 'osx-echo.0' 'echo "Starting osx-echo ..." && uv run -m osx_echo' C-m
