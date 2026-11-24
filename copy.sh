#!/bin/bash

set -e

DOTFILES="$(cd "$(dirname "$0")" && pwd)"

# Copy a file, replacing any existing file or symlink (e.g. one created by install.sh).
copy_file() {
  rm -f "$2"
  cp "$1" "$2"
}

echo "Copying nvim config and plugin files..."
NVIM_CONFIG="$HOME/.config/nvim"

if [ ! -f "$NVIM_CONFIG/init.lua" ]; then
  echo "$NVIM_CONFIG/init.lua not found; run install.sh first to set up LazyVim." >&2
  exit 1
fi

for section in config plugins; do
  mkdir -p "$NVIM_CONFIG/lua/$section"

  for source in "$DOTFILES/nvim/lua/$section"/*.lua; do
    [ -e "$source" ] || continue
    copy_file "$source" "$NVIM_CONFIG/lua/$section/$(basename "$source")"
  done
done

echo "Copying tmux.conf..."
copy_file "$DOTFILES/tmux.conf" "$HOME/.tmux.conf"

echo "Copying rex config..."
mkdir -p "$HOME/.config/rex"
for source in "$DOTFILES/rex"/*; do
  [ -e "$source" ] || continue
  copy_file "$source" "$HOME/.config/rex/$(basename "$source")"
done

echo "Installing TPM (tmux plugin manager)..."
if [ ! -d "$HOME/.tmux/plugins/tpm" ]; then
  git clone https://github.com/tmux-plugins/tpm "$HOME/.tmux/plugins/tpm"
else
  echo "TPM already installed, skipping."
fi

echo "Done."
