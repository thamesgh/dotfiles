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

-- URL hints: mark each URL on the focused pane's screen with a lettered pill, then
-- type a label to open that URL in the default browser. The labels are drawn
-- by url-hints.py in a floating pane laid over the one being searched.
local config_dir = (debug.getinfo(1, "S").source:match("^@(.*)/[^/]*$"))
  or ((os.getenv("XDG_CONFIG_HOME") or (os.getenv("HOME") .. "/.config")) .. "/rex")
local terminal = "com.superlogical.terminal"

local function find_rect(node, block_id)
  if type(node) ~= "table" then return nil end
  if node.block_id == block_id and node.rect then return node.rect end
  for _, child in pairs(node) do
    local rect = find_rect(child, block_id)
    if rect then return rect end
  end
end

-- The pane's palette, scrollback and screen as VT sequences. Only the end
-- matters, so a long scrollback is read from its tail; the palette comes first
-- and is always in the first part.
local function read_screen(block_id)
  local limit = 900000
  local r, err = rex.block.call(terminal, "format", {
    block_id = block_id, format = "vt", extra_palette = true, max_bytes = limit,
  })
  if err ~= nil then error(err, 0) end
  local out = r.content or ""
  if r.id and r.total and #out < r.total then
    local parts, offset = { out, "\r\n" }, math.max(#out, r.total - limit)
    while offset < r.total do
      local b, berr = rex.block.call(terminal, "blob_read", {
        block_id = block_id, id = r.id, offset = offset, max_bytes = limit,
      })
      if berr ~= nil then error(berr, 0) end
      local data = b.data or ""
      if data == "" then break end
      parts[#parts + 1] = data
      offset = offset + #data
      if b.eof then break end
    end
    out = table.concat(parts)
  end
  return out
end

local overlay_label = "url-hints"

local function url_hints(ctx)
  local view, err = rex.session.view{}
  if err ~= nil then error(err, 0) end

  -- Pressed again while the hints are up: ask them to fade out and close.
  -- Escape is what the helper takes as "cancel".
  local dismissed = false
  for _, w in ipairs(view.windows or {}) do
    for _, layer in ipairs(w.layers or {}) do
      for _, b in ipairs(layer.blocks or {}) do
        if b.label == overlay_label then
          rex.block.call(terminal, "write", { block_id = b.block_id, data = "\27" })
          dismissed = true
        end
      end
    end
  end
  if dismissed then return end

  local block_id, window_id, rect = ctx.block_id, nil, nil
  for _, w in ipairs(view.windows or {}) do
    if not block_id and w.window_id == view.active_window_id then
      block_id = w.focused_block_id
    end
  end
  if not block_id then return end
  for _, w in ipairs(view.windows or {}) do
    rect = find_rect(w.layers, block_id)
    if rect then window_id = w.window_id break end
  end

  local size, serr = rex.block.call(terminal, "size", { block_id = block_id })
  if serr ~= nil then error(serr, 0) end

  local path = os.tmpname()
  local f = assert(io.open(path, "w"))
  f:write(read_screen(block_id))
  f:close()

  local _, lerr = rex.session.new_layer{
    window_id = window_id,
    bounds    = rect or { 0, 0, 1, 1 },
    focus     = true,
    layout    = rex.layout.block{
      flavor  = terminal .. ".shell",
      label   = overlay_label,
      options = {
        shell   = "none",
        command = { "/usr/bin/python3", config_dir .. "/url-hints.py",
                    path, tostring(size.columns), tostring(size.rows) },
      },
    },
  }
  if lerr ~= nil then os.remove(path) error(lerr, 0) end
end

rex.action{
  name     = "url_hints",
  title    = "Open URL with Hints",
  category = "Pane",
  keywords = "url link hint open browser",
  run      = url_hints,
}

rex.bind("ctrl+cmd+u", "url_hints")

-- Split panes with vim motions.
rex.bind("ctrl+cmd+shift+h", "pane.split.left")
rex.bind("ctrl+cmd+shift+j", "pane.split.down")
rex.bind("ctrl+cmd+shift+k", "pane.split.up")
rex.bind("ctrl+cmd+shift+l", "pane.split.right")
