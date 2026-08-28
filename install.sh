#!/bin/bash

set -e

DOTFILES="$(cd "$(dirname "$0")" && pwd)"

echo "Linking nvim config and plugin files..."
NVIM_CONFIG="$HOME/.config/nvim"

if [ -L "$NVIM_CONFIG" ]; then
  echo "$NVIM_CONFIG is a symlink; expected an existing Neovim config directory." >&2
  echo "Restore the Omarchy Neovim config, then run this script again." >&2
  exit 1
fi

for section in config plugins; do
  mkdir -p "$NVIM_CONFIG/lua/$section"

  for source in "$DOTFILES/nvim/lua/$section"/*.lua; do
    [ -e "$source" ] || continue
    ln -sfn "$source" "$NVIM_CONFIG/lua/$section/$(basename "$source")"
  done
done

echo "Linking tmux.conf..."
ln -sf "$DOTFILES/tmux.conf" "$HOME/.tmux.conf"

echo "Installing TPM (tmux plugin manager)..."
if [ ! -d "$HOME/.tmux/plugins/tpm" ]; then
  git clone https://github.com/tmux-plugins/tpm "$HOME/.tmux/plugins/tpm"
else
  echo "TPM already installed, skipping."
fi

echo "Done."
