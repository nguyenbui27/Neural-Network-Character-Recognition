#!/bin/zsh
set -e
cd "${0:A:h}"
# Prefer the already prepared environment when running from this workspace.
if [[ -x ../../work/cnn-venv/bin/python ]]; then
    exec ../../work/cnn-venv/bin/python app.py
fi
if [[ ! -x .venv/bin/python ]]; then
    chosen_python=""
    for candidate in python3.12 python3.11 /Library/Frameworks/Python.framework/Versions/3.11/bin/python3.11 python3.10; do
        if command -v "$candidate" >/dev/null 2>&1; then
            chosen_python="$candidate"
            break
        fi
    done
    if [[ -z "$chosen_python" ]]; then
        print 'Install Python 3.11 or 3.12 from python.org, then run this launcher again.'
        read '?Press Enter to close.'
        exit 1
    fi
    "$chosen_python" -m venv .venv
    .venv/bin/python -m pip install -r requirements.txt
fi
exec .venv/bin/python app.py
