#!/usr/bin/env bash
set -euo pipefail

# AIInSight Skill installer
# Usage:
#   curl -fsSL .../install.sh | bash -s -- --platform <platform>   (explicit)
#   curl -fsSL .../install.sh | bash                                (auto-detect)
#
# Platforms: claude-code, opencode, costrict, vscode-costrict

BASE_URL="https://raw.githubusercontent.com/papysans/AIInSight/main"
SKILLS="ai-insight ai-topic-analyzer"

# --- Auto-detect platform via process-injected env vars ---

detect_platform() {
  if [ "${COSTRICT_CALLER:-}" = "vscode" ]; then
    echo "vscode-costrict"
  elif [ "${COSTRICT_RUNNING:-}" = "1" ]; then
    echo "costrict"
  elif [ "${CLAUDECODE:-}" = "1" ]; then
    echo "claude-code"
  elif [ "${OPENCODE:-}" = "1" ]; then
    echo "opencode"
  else
    echo ""
  fi
}

# --- Parse arguments ---

PLATFORM=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --platform|-p)
      PLATFORM="$2"
      shift 2
      ;;
    claude-code|opencode|costrict|vscode-costrict)
      PLATFORM="$1"
      shift
      ;;
    *)
      echo "Unknown argument: $1" >&2
      echo "" >&2
      echo "Usage: bash install.sh [--platform <platform>]" >&2
      echo "Platforms: claude-code, opencode, costrict, vscode-costrict" >&2
      echo "Omit --platform to auto-detect via environment variables." >&2
      exit 1
      ;;
  esac
done

if [ -z "$PLATFORM" ]; then
  PLATFORM=$(detect_platform)
  if [ -z "$PLATFORM" ]; then
    echo "ERROR: Could not auto-detect platform." >&2
    echo "" >&2
    echo "None of these environment variables were found:" >&2
    echo "  COSTRICT_CALLER=vscode  → vscode-costrict" >&2
    echo "  COSTRICT_RUNNING=1      → costrict" >&2
    echo "  CLAUDECODE=1            → claude-code" >&2
    echo "  OPENCODE=1              → opencode" >&2
    echo "" >&2
    echo "Please specify explicitly:" >&2
    echo "  curl -fsSL .../install.sh | bash -s -- --platform <platform>" >&2
    exit 1
  fi
  echo "Auto-detected platform: $PLATFORM"
else
  echo "Platform: $PLATFORM"
fi

# --- Download helper ---

download() {
  local url="$1" dest="$2"
  if ! curl -fsSL "$url" -o "$dest"; then
    echo "ERROR: Failed to download $url" >&2
    exit 1
  fi
}

# --- Install per platform ---
# Claude Code uses .agents/skills/ (new version)
# Opencode / Costrict / VSCode Costrict use .opencode/skills/ (legacy version)

install_skills() {
  local base_dir="$1"
  local source_prefix="$2"

  for skill in $SKILLS; do
    mkdir -p "$base_dir/$skill"
    echo "Downloading $skill..."
    download "$BASE_URL/$source_prefix/$skill/SKILL.md" "$base_dir/$skill/SKILL.md"
  done

  mkdir -p "$base_dir/shared"
  echo "Downloading shared guidelines..."
  download "$BASE_URL/$source_prefix/shared/GUIDELINES.md" "$base_dir/shared/GUIDELINES.md"
}

install_claude_code() {
  install_skills "$HOME/.claude/skills" ".agents/skills"

  echo ""
  echo "=== AIInSight Skills installed (Claude Code) ==="
  echo ""
  echo "Skills: $HOME/.claude/skills/"
  echo ""
  echo "Next: Configure MCP connection in ~/.claude/.mcp.json"
  echo "Then try: \"今日AI热点\" or \"帮我分析 GPT-5\""
}

install_opencode() {
  install_skills "$HOME/.opencode/skills" ".opencode/skills"

  echo ""
  echo "=== AIInSight Skills installed (Opencode) ==="
  echo ""
  echo "Skills: $HOME/.opencode/skills/"
  echo ""
  echo "Next: Configure MCP connection in project opencode.json"
  echo "Then try: \"今日AI热点\" or \"帮我分析 GPT-5\""
}

install_costrict() {
  install_skills "$HOME/.costrict/skills" ".opencode/skills"

  echo ""
  echo "=== AIInSight Skills installed (Costrict CLI) ==="
  echo ""
  echo "Skills: $HOME/.costrict/skills/"
  echo ""
  echo "Next: Configure MCP connection in ~/.costrict/settings.json"
  echo "Then try: \"今日AI热点\" or \"帮我分析 GPT-5\""
}

install_vscode_costrict() {
  install_skills "$HOME/.roo/skills" ".opencode/skills"

  echo ""
  echo "=== AIInSight Skills installed (VSCode Costrict / Roo Code) ==="
  echo ""
  echo "Skills: $HOME/.roo/skills/"
  echo ""
  echo "Next: Configure MCP connection in ~/.roo/mcp.json"
  echo "Then try: \"今日AI热点\" or \"帮我分析 GPT-5\""
}

# --- Main ---

echo ""

case "$PLATFORM" in
  claude-code)       install_claude_code ;;
  opencode)          install_opencode ;;
  costrict)          install_costrict ;;
  vscode-costrict)   install_vscode_costrict ;;
  *)
    echo "ERROR: Unknown platform '$PLATFORM'" >&2
    echo "Valid platforms: claude-code, opencode, costrict, vscode-costrict" >&2
    exit 1
    ;;
esac
