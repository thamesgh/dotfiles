-- Keymaps are automatically loaded on the VeryLazy event
-- Default keymaps that are always set: https://github.com/LazyVim/LazyVim/blob/main/lua/lazyvim/config/keymaps.lua
-- Add any additional keymaps here

local map = LazyVim.safe_keymap_set

-- The default <C-[> seems to collide with some move line command,
-- so disambiguate with <C-[[>.
map("i", "<C-[[>", "<esc><esc>", { desc = "Switch from insert to normal mode" })
