-- Rotate the panes in the active tab, like tmux's rotate-window.
-- Panes are ordered by layout (depth-first through the split tree).
-- Forward:  [A, B, C] -> [C, A, B]
-- Backward: [A, B, C] -> [B, C, A]
local function rotate(ctx, forward)
  local view, err = rex.session.view{}
  if err ~= nil then error(err, 0) end

  local win
  for _, w in ipairs(view.windows or {}) do
    if w.window_id == view.active_window_id then win = w end
  end
  if not win or not win.layers or not win.layers[1] then return end

  local blocks = win.layers[1].blocks or {}
  local n = #blocks
  if n < 2 then return end

  local function swap(a, b)
    local _, e = rex.session.swap_blocks{ block_id = a, other_block_id = b }
    if e ~= nil then error(e, 0) end
  end

  if forward then
    local last = blocks[n].block_id
    for i = n - 1, 1, -1 do swap(last, blocks[i].block_id) end
  else
    local first = blocks[1].block_id
    for i = 2, n do swap(first, blocks[i].block_id) end
  end
end

rex.action{
  name     = "rotate_panes_forward",
  title    = "Rotate Panes Forward",
  category = "Pane",
  keywords = "cycle rotate swap panes",
  run      = function(ctx) rotate(ctx, true) end,
}

rex.action{
  name     = "rotate_panes_backward",
  title    = "Rotate Panes Backward",
  category = "Pane",
  keywords = "cycle rotate swap panes",
  run      = function(ctx) rotate(ctx, false) end,
}

rex.bind("ctrl+cmd+]", "rotate_panes_forward")
rex.bind("ctrl+cmd+[", "rotate_panes_backward")

-- Navigate panes with vim motions.
rex.bind("ctrl+cmd+h", "pane.focus.left")
rex.bind("ctrl+cmd+j", "pane.focus.down")
rex.bind("ctrl+cmd+k", "pane.focus.up")
rex.bind("ctrl+cmd+l", "pane.focus.right")

-- Split panes with vim motions.
rex.bind("ctrl+cmd+shift+h", "pane.split.left")
rex.bind("ctrl+cmd+shift+j", "pane.split.down")
rex.bind("ctrl+cmd+shift+k", "pane.split.up")
rex.bind("ctrl+cmd+shift+l", "pane.split.right")
