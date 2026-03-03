# dotfiles

Personal configuration files for Neovim and tmux.

## Structure

```
dotfiles/
├── nvim/          # Neovim config (LazyVim)
├── tmux.conf      # tmux config
├── install.sh     # Symlink setup script
└── copy.sh        # Copy setup script
```

## Install

### Symlinks (recommended for personal machines)

```sh
./install.sh
```

Symlinks configs to their canonical locations so edits here are reflected immediately.

### Copy (for remote/shared machines)

```sh
./copy.sh
```

Copies configs directly — useful on remote servers or machines where you don't want to clone this repo permanently. Changes made to the live config won't be reflected back here.

Both scripts will:
- Set up `~/.config/nvim`
- Set up `~/.tmux.conf`
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
