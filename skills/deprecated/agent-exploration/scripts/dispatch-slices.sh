#!/usr/bin/env bash
# dispatch-slices.sh — run N explorer slices in parallel through an official
# harness CLI (claude | codex | cursor-agent), wait for all, and report
# per-slice exit codes. Bundled with the agent-exploration skill; used only on
# the external-CLI dispatch route (native subagents need no script).
# Zero external dependencies (native bash + the chosen CLI binary).
#
# Usage:
#   dispatch-slices.sh \
#     --cli <claude|codex|cursor-agent> [--model <model>] [--reasoning <effort>] \
#     [--add-dir <dir>] [--logs <dir>] \
#     -- <prompt-file> [<prompt-file>...]
#
# Required:
#   --cli        Harness CLI: claude (Claude models), codex (gpt-*),
#                cursor-agent (Grok).
#
# Optional:
#   --model      Model to pin. Required for claude and cursor-agent; codex
#                falls back to the ~/.codex/config.toml default when omitted.
#                Examples: fable | opus | gpt-5.3-codex | cursor-grok-4.5-high-fast
#   --reasoning  Reasoning effort: low | medium | high | xhigh. Default xhigh.
#                claude → --effort; codex → -c model_reasoning_effort=…;
#                cursor-agent → ignored (effort/fast live in the model id).
#   --add-dir    Extra workspace root forwarded to the CLI. Pass the analysis
#                <path> whenever it lies outside the CLI's working tree.
#   --logs       Directory for per-slice .out/.err/.exit files. Default ./dispatch-logs.
#
# Positional (after --): 1 to 8 prompt files. Each file's basename
# (without .txt/.md) becomes the slice id used for log file naming.
#
# Behaviour:
#   - claude:       claude -p --model … --effort … --permission-mode dontAsk
#                     --allowedTools "<scoped-write allowlist>" < prompt-file
#   - codex:        codex exec [-m …] -c model_reasoning_effort=… -s workspace-write
#                     -c sandbox_workspace_write.network_access=true
#                     --skip-git-repo-check - < prompt-file
#   - cursor-agent: cursor-agent -p --output-format text --force --model … "$(cat prompt-file)"
#   - All slices run in parallel via shell job control (& + wait $pid).
#   - Per-slice stdout/stderr/exit are captured under --logs.
#   - The script blocks until every slice has exited, then prints a summary.
#   - Exits 0 only when every slice exited 0; otherwise exits 1.
#   - SIGINT/SIGTERM kills running child processes before exiting.
set -uo pipefail

CLI=""
MODEL=""
REASONING="xhigh"
ADD_DIR=""
LOGS_DIR="./dispatch-logs"

# Mirrors the Tool Restrictions list in references/dispatch-rules.md: read-only
# helpers plus exactly one Write. --permission-mode dontAsk auto-denies the rest.
CLAUDE_ALLOWED_TOOLS="Read Glob Grep WebFetch WebSearch Write Bash(rg *) Bash(ls *) Bash(cat *) Bash(head *) Bash(wc *) Bash(file *) Bash(find *)"

print_help() {
  sed -n '2,45p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

while [ $# -gt 0 ]; do
  case "$1" in
    --cli)         CLI="${2:-}"; shift 2 ;;
    --cli=*)       CLI="${1#--cli=}"; shift ;;
    --model)       MODEL="${2:-}"; shift 2 ;;
    --model=*)     MODEL="${1#--model=}"; shift ;;
    --reasoning)   REASONING="${2:-}"; shift 2 ;;
    --reasoning=*) REASONING="${1#--reasoning=}"; shift ;;
    --add-dir)     ADD_DIR="${2:-}"; shift 2 ;;
    --add-dir=*)   ADD_DIR="${1#--add-dir=}"; shift ;;
    --logs)        LOGS_DIR="${2:-}"; shift 2 ;;
    --logs=*)      LOGS_DIR="${1#--logs=}"; shift ;;
    --)            shift; break ;;
    -h|--help)     print_help; exit 0 ;;
    *)             echo "ERROR: unknown argument: $1" >&2; exit 2 ;;
  esac
done

case "$CLI" in
  claude|codex|cursor-agent) ;;
  "") echo "ERROR: --cli is required (claude | codex | cursor-agent)" >&2; exit 2 ;;
  *)  echo "ERROR: unsupported --cli '$CLI' (claude | codex | cursor-agent)" >&2; exit 2 ;;
esac

case "$REASONING" in
  low|medium|high|xhigh) ;;
  *) echo "ERROR: invalid --reasoning '$REASONING' (low | medium | high | xhigh)" >&2; exit 2 ;;
esac

if [ -z "$MODEL" ] && [ "$CLI" != "codex" ]; then
  echo "ERROR: --model is required for --cli $CLI (codex may omit it to use its config default)" >&2
  exit 2
fi

if [ "$#" -lt 1 ] || [ "$#" -gt 8 ]; then
  echo "ERROR: pass between 1 and 8 prompt files after --" >&2
  exit 2
fi

if ! command -v "$CLI" >/dev/null 2>&1; then
  echo "ERROR: '$CLI' not found on PATH — install that harness's official CLI first" >&2
  exit 2
fi

mkdir -p "$LOGS_DIR"

# Builds the per-slice command into the global CMD array. The prompt file is
# fed via stdin for claude/codex; cursor-agent takes it as a positional arg.
build_cmd() {
  local prompt_file="$1"
  case "$CLI" in
    claude)
      CMD=(claude -p --model "$MODEL" --effort "$REASONING"
           --permission-mode dontAsk --allowedTools "$CLAUDE_ALLOWED_TOOLS")
      [ -n "$ADD_DIR" ] && CMD+=(--add-dir "$ADD_DIR")
      ;;
    codex)
      CMD=(codex exec)
      [ -n "$MODEL" ] && CMD+=(-m "$MODEL")
      CMD+=(-c "model_reasoning_effort=$REASONING"
           -s workspace-write -c "sandbox_workspace_write.network_access=true"
           --skip-git-repo-check)
      [ -n "$ADD_DIR" ] && CMD+=(--add-dir "$ADD_DIR")
      CMD+=(-)
      ;;
    cursor-agent)
      CMD=(cursor-agent -p --output-format text --force --model "$MODEL")
      [ -n "$ADD_DIR" ] && CMD+=(--add-dir "$ADD_DIR")
      CMD+=("$(cat "$prompt_file")")
      ;;
  esac
}

PIDS=()
SLUGS=()

cleanup() {
  if [ "${#PIDS[@]}" -gt 0 ]; then
    echo "interrupted; killing ${#PIDS[@]} child process(es)..." >&2
    kill "${PIDS[@]}" 2>/dev/null || true
  fi
  exit 130
}
trap cleanup INT TERM

START_TS=$(date +%s)
echo "dispatch: $# slice(s) via $CLI (model=${MODEL:-config-default} reasoning=$REASONING)"
echo "logs:     $LOGS_DIR"

for PROMPT_FILE in "$@"; do
  if [ ! -f "$PROMPT_FILE" ]; then
    echo "ERROR: prompt file not found: $PROMPT_FILE" >&2
    exit 2
  fi
  SLUG="$(basename "$PROMPT_FILE")"
  SLUG="${SLUG%.txt}"
  SLUG="${SLUG%.md}"
  SLUGS+=("$SLUG")

  OUT="$LOGS_DIR/$SLUG.out"
  ERR="$LOGS_DIR/$SLUG.err"
  rm -f "$LOGS_DIR/$SLUG.exit"

  build_cmd "$PROMPT_FILE"
  if [ "$CLI" = "cursor-agent" ]; then
    "${CMD[@]}" </dev/null >"$OUT" 2>"$ERR" &
  else
    "${CMD[@]}" <"$PROMPT_FILE" >"$OUT" 2>"$ERR" &
  fi

  PID=$!
  PIDS+=("$PID")
  echo "  dispatched: $SLUG  pid=$PID"
done

FAILED=0
TOTAL=${#PIDS[@]}
for i in "${!PIDS[@]}"; do
  PID="${PIDS[$i]}"
  SLUG="${SLUGS[$i]}"
  if wait "$PID"; then
    EXIT_CODE=0
  else
    EXIT_CODE=$?
    FAILED=$((FAILED + 1))
  fi
  echo "$EXIT_CODE" > "$LOGS_DIR/$SLUG.exit"
  echo "  exited:     $SLUG  rc=$EXIT_CODE"
done

ELAPSED=$(( $(date +%s) - START_TS ))
echo "summary: total=${ELAPSED}s  ok=$((TOTAL - FAILED))/${TOTAL}  failed=${FAILED}/${TOTAL}"

# Clear trap so a clean exit does not trigger cleanup.
trap - INT TERM

if [ "$FAILED" -gt 0 ]; then
  exit 1
fi
exit 0
