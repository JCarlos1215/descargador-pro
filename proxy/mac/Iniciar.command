#!/bin/zsh
cd "${0:A:h}/../.." || exit 1
export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/local/sbin:$PATH"
exec /usr/bin/caffeinate -i python3 proxy/mac/run.py
