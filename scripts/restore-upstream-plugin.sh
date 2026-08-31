#!/usr/bin/env bash
set -euo pipefail

plugin_id="${PLUGIN_ID:-io.github.tyrichards.orthodox-daily}"
target="${OMARCHY_PLUGIN_DIR:-$HOME/.config/omarchy/plugins/$plugin_id}"
backup="${target}.upstream-backup"

if [[ -L "$target" ]]; then
  rm "$target"
  echo "Removed local plugin symlink: $target"
elif [[ -e "$target" ]]; then
  echo "Refusing to remove non-symlink target: $target" >&2
  exit 1
fi

if [[ -e "$backup" || -L "$backup" ]]; then
  mv "$backup" "$target"
  echo "Restored upstream plugin: $target"
else
  echo "No backup found at: $backup" >&2
  exit 1
fi

echo "Reload/restart Omarchy shell to pick up QML changes."
