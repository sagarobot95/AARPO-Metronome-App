#!/bin/bash
# macOS double-click launcher.
# Double-clicking a ".command" file in Finder automatically opens Terminal.app
# and runs it. This just hands off to run.sh in the same folder.
cd "$(dirname "$0")" || exit 1
exec ./run.sh
