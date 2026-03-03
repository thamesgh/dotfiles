#!/bin/bash

set -e

DOTFILES="$(cd "$(dirname "$0")" && pwd)"

echo "Copying nvim..."
rm -rf "$HOME/.config/nvim"
cp -r "$DOTFILES/nvim" "$HOME/.config/nvim"

echo "Copying tmux.conf..."
cp "$DOTFILES/tmux.conf" "$HOME/.tmux.conf"

echo "Installing TPM (tmux plugin manager)..."
if [ ! -d "$HOME/.tmux/plugins/tpm" ]; then
  git clone https://github.com/tmux-plugins/tpm "$HOME/.tmux/plugins/tpm"
else
  echo "TPM already installed, skipping."
fi

echo "Done."
