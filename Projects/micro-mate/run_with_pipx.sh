#!/usr/bin/env bash
PIPX_HOME="${PIPX_HOME:-$HOME/.local/pipx}"
VENV_PY="$PIPX_HOME/venvs/micro-mate/bin/python"
if [ -x "$VENV_PY" ]; then
  exec "$VENV_PY" -m src.run_game "$@"
else
  echo "pipx env not found; running with pipx ephemeral run (may re-install packages)"
  python3 -m pipx run --spec 'pygame' --spec 'Pillow' --spec 'cairosvg' python -m src.run_game "$@"
fi
