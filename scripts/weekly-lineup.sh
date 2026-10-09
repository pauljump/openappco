#!/bin/sh
# Weekly lineup re-rank (PM2 scheduled job `openappco-lineup`, Mini only).
# Exports fresh opportunities from OpenX Miner outside the openforx repo, then
# opens or refreshes the "Lineup review" issue if the severity order changed.
set -eu
DATA="$HOME/.local/share/openappco"
mkdir -p "$DATA"
OPPORTUNITIES_OUT="$DATA/opportunities.json" /opt/homebrew/bin/node --no-warnings /Users/mini-home/projects/openforx/scripts/export-opportunities.mjs
cd /Users/mini-home/projects/openappco
GH_BIN=/opt/homebrew/bin/gh OPPORTUNITIES="$DATA/opportunities.json" /opt/homebrew/bin/node scripts/lineup.mjs propose --publish
