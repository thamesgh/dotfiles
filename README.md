# dotfiles

Personal configuration files for Neovim and tmux, managed via symlinks.

## Structure

```
dotfiles/
├── nvim/          # Neovim config (LazyVim)
├── tmux.conf      # tmux config
└── install.sh     # Symlink setup script
```

## Install

```sh
./install.sh
```

This will:
- Symlink `nvim/` to `~/.config/nvim`
- Symlink `tmux.conf` to `~/.tmux.conf`
- Clone [TPM](https://github.com/tmux-plugins/tpm) to `~/.tmux/plugins/tpm`

After installing, open tmux and press `ctrl+a I` to install tmux plugins.

## Neovim

Built on [LazyVim](https://lazyvim.org). Customizations live in `nvim/lua/plugins/thames.lua`:

- **Colorscheme**: tokyonight-night (transparent background)
- **Terminal**: floating, rounded border
- **Explorer**: right-side panel
- **vim-tmux-navigator**: seamless pane navigation between nvim and tmux

## tmux

- Prefix: `ctrl+a`
- Splits: `|` (horizontal), `-` (vertical)
- Pane resize: `h/j/k/l`
- Pane zoom: `m`
- Reload config: `r`
- Mouse support enabled
- Vi copy mode: `v` to select, `y` to copy

### Plugins (via TPM)

- [vim-tmux-navigator](https://github.com/christoomey/vim-tmux-navigator) — unified nav with nvim
- [tmux-themepack](https://github.com/jimeh/tmux-themepack) — powerline/cyan theme
