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

if [ ! -f "$NVIM_CONFIG/init.lua" ]; then
  if [ -d "$NVIM_CONFIG" ] && [ -n "$(find "$NVIM_CONFIG" -mindepth 1 -maxdepth 1 -print -quit)" ]; then
    echo "$NVIM_CONFIG is not empty and does not contain init.lua; refusing to overwrite it." >&2
    exit 1
  fi

  echo "Installing LazyVim starter..."
  rmdir "$NVIM_CONFIG" 2>/dev/null || true
  git clone https://github.com/LazyVim/starter "$NVIM_CONFIG"
  rm -rf "$NVIM_CONFIG/.git"
else
  echo "Neovim configuration already installed, skipping LazyVim starter."
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

echo "Linking customized Hyprland config files..."
HYPR_CONFIG="$HOME/.config/hypr"
mkdir -p "$HYPR_CONFIG"

for source in "$DOTFILES"/hypr/*; do
  [ -f "$source" ] || continue

  name="$(basename "$source")"
  target="$HYPR_CONFIG/$name"

  if [ -e "$target" ] && [ ! -L "$target" ]; then
    backup="$target.bak.$(date +%Y%m%d%H%M%S)"
    echo "Backing up $target to $backup"
    mv "$target" "$backup"
  fi

  ln -sfn "$source" "$target"
done

echo "Installing TPM (tmux plugin manager)..."
if [ ! -d "$HOME/.tmux/plugins/tpm" ]; then
  git clone https://github.com/tmux-plugins/tpm "$HOME/.tmux/plugins/tpm"
else
  echo "TPM already installed, skipping."
fi

echo "Done."
