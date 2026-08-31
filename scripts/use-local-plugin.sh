#!/usr/bin/env bash
set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
plugin_id="${PLUGIN_ID:-io.github.tyrichards.orthodox-daily}"
target="${OMARCHY_PLUGIN_DIR:-$HOME/.config/omarchy/plugins/$plugin_id}"
backup="${target}.upstream-backup"

if [[ -L "$target" && "$(readlink "$target")" == "$repo" ]]; then
  echo "Already using local plugin: $target -> $repo"
  exit 0
fi

if [[ -e "$target" || -L "$target" ]]; then
  if [[ -e "$backup" || -L "$backup" ]]; then
    echo "Refusing to overwrite existing backup: $backup" >&2
    echo "Restore/remove it first, or set PLUGIN_ID/OMARCHY_PLUGIN_DIR explicitly." >&2
    exit 1
  fi
  mv "$target" "$backup"
  echo "Moved existing plugin to: $backup"
fi

ln -s "$repo" "$target"
echo "Using local plugin: $target -> $repo"
echo "Reload/restart Omarchy shell to pick up QML changes."
