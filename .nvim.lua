vim.keymap.set("n", "<leader>fd", function()
  require("telescope.builtin").find_files({
    cwd = "derivatives",
    hidden = true,
    no_ignore = true,
  })
end, { desc = "Find derivative files" })
