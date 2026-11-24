return {
	{
		"LazyVim/LazyVim",
		opts = {
			colorscheme = "cyberdream",
		},
	},
	{
		"scottmckendry/cyberdream.nvim",
		lazy = false,
		priority = 1000,
		opts = {
			variant = "auto",
			highlights = {
				CursorLine = { bg = "NONE" },
				Visual = { bg = "#fff3a8", fg = "#16181a" },
				Search = { bg = "#fff3a8", fg = "#16181a" },
				IncSearch = { bg = "#fff3a8", fg = "#16181a" },
				CurSearch = { bg = "#fff3a8", fg = "#16181a", bold = true },
			},
		},
	},
	{ "projekt0n/github-nvim-theme", name = "github-theme" },
	{
		"folke/tokyonight.nvim",
		opts = {
			transparent = true,
			styles = {
				sidebars = "transparent",
				floats = "transparent",
			},
		},
	},
	{
		"folke/snacks.nvim",
		opts = {
			indent = { enabled = false },
			terminal = {
				win = {
					position = "float",
					border = "rounded",
				},
			},
			picker = {
				sources = {
					explorer = {
						layout = {
							layout = {
								position = "right",
							},
						},
					},
				},
			},
		},
	},
	{
		"mfussenegger/nvim-lint",
		opts = {
			linters_by_ft = {
				markdown = {},
			},
		},
	},
	{
		"christoomey/vim-tmux-navigator",
		cmd = {
			"TmuxNavigateLeft",
			"TmuxNavigateDown",
			"TmuxNavigateUp",
			"TmuxNavigateRight",
			"TmuxNavigatePrevious",
			"TmuxNavigatorProcessList",
		},
		keys = {
			{ "<c-h>", "<cmd><C-U>TmuxNavigateLeft<cr>" },
			{ "<c-j>", "<cmd><C-U>TmuxNavigateDown<cr>" },
			{ "<c-k>", "<cmd><C-U>TmuxNavigateUp<cr>" },
			{ "<c-l>", "<cmd><C-U>TmuxNavigateRight<cr>" },
			{ "<c-\\>", "<cmd><C-U>TmuxNavigatePrevious<cr>" },
		},
	},
	{
		"stevearc/conform.nvim",
		opts = {
			formatters_by_ft = {
				typescript = { "prettier" },
				typescriptreact = { "prettier" },
			},
			format_on_save = { timeout_ms = 500, lsp_fallback = true },
		},
	},
}
