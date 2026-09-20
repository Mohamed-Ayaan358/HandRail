#!/bin/sh
# Use installed tooling, or the existing Codex bundled runtime on this Mac.
set -eu
cd "$(dirname "$0")/.."
HANDRAIL_RUNTIME="${HANDRAIL_RUNTIME:-/Users/ayaan/.cache/codex-runtimes/codex-primary-runtime/dependencies}"
if command -v node >/dev/null 2>&1; then HANDRAIL_NODE=node
elif [ -x "$HANDRAIL_RUNTIME/node/bin/node" ]; then HANDRAIL_NODE="$HANDRAIL_RUNTIME/node/bin/node"
else echo 'Node.js 20+ is required.' >&2; exit 1; fi
case "${1:-help}" in
  test) "$HANDRAIL_NODE" --test pilot/tests/*.test.mjs; exec python3 -m unittest discover -s pilot/tests -p 'test_*.py';;
  collect) shift; exec "$HANDRAIL_NODE" pilot/collect.mjs "$@";;
  run|review) exec python3 pilot/evaluate.py "$@";;
  *) echo 'Usage: ./pilot/run.sh test | collect [options] | run [options] | review [options]';;
esac
