return {
  "stevearc/conform.nvim",
  opts = {
    formatters_by_ft = {
      ["markdown"] = { "prettier_md" },
    },
    formatters = {
      prettier_md = {
        command = "prettier",
        -- Need --prose-wrap for markdown. See: https://github.com/prettier/prettier/issues/5123
        args = { "--prose-wrap", "always", "--stdin-filepath", "$FILENAME" },
      },
    },
  },
}
