return {
  "iamcco/markdown-preview.nvim",
  config = function()
    vim.cmd([[do FileType]])
    vim.g.mkdp_markdown_css = "/Users/thames/.config/nvim/markdown.css"
    vim.g.mkdp_refresh_slow = 1
  end,
}
