#!/usr/bin/env bash
# install.sh — Install the webcapture CLI tool
#
# Run from the cli/ directory:
#   chmod +x install.sh
#   ./install.sh
#
# After installation, 'webcapture' is available in your PATH.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ""
echo "  Installing webcapture CLI..."
echo ""

# Install as an editable package so the 'webcapture' command is registered
pip install -e "$SCRIPT_DIR" --quiet

echo ""
echo "  ✅  Done! The 'webcapture' command is now available."
echo ""
echo "  Usage:"
echo "    webcapture capture example.com"
echo "    webcapture capture example.com --mode crawl --device mobile"
echo "    webcapture capture example.com --mode both --device both --max 50"
echo "    webcapture status  <job_id>"
echo "    webcapture cancel  <job_id>"
echo ""
echo "  The backend must be running first:"
echo "    cd .. && docker-compose up -d"
echo ""
