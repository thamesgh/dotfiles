-- Keep only your personal keybinding overrides here. Add new bindings or
-- unbind defaults before replacing them.

-- See current bindings and descriptions:
--   omarchy menu keybindings --print

-- To disable every Omarchy default binding, set this in
-- ~/.config/hypr/hyprland.lua before require("default.hypr.omarchy"), then add
-- only the bindings you want below:
--   omarchy_default_bindings = false

-- To disable all preinstalled app/webapp bindings, set:
--   omarchy_preinstalled_bindings = false

-- Add a new binding.
-- o.bind("SUPER + SHIFT + R", "SSH", "alacritty -e ssh your-server")

-- Change an existing binding by unbinding it first, then binding the key again.
-- This example changes SUPER+SPACE from the launcher to the Omarchy root menu.
-- hl.unbind("SUPER + SPACE")
-- o.bind("SUPER + SPACE", "Omarchy menu", "omarchy-menu toggle root")

-- Disable a default binding without replacing it.
-- hl.unbind("SUPER + SHIFT + B")

-- Logitech MX Keys examples:
-- o.bind("SUPER + SHIFT + S", nil, "omarchy-capture-screenshot")
-- o.bind("SUPER + H", nil, "voxtype record toggle")
-- o.bind("SUPER + PERIOD", nil, "omarchy-shell shell toggle omarchy.emojis")

-- hl.unbind("SUPER + SHIFT + P")
--
-- hl.bind("SUPER + SHIFT + P", function()
--   local monitor = hl.get_active_monitor()
--
--   if monitor then
--     local padding = 60
--     local logical_height = monitor.height / monitor.scale
--     local height = logical_height - (padding * 2)
--
--     hl.dispatch(hl.dsp.window.float({ action = "toggle" }))
--
--     hl.dispatch(hl.dsp.window.resize({
--       x = 1400,
--       y = height,
--       relative = false
--     }))
--
--     hl.dispatch(hl.dsp.window.center())
--   end
-- end, {
--   description = "Portrait window"
-- })
--
-- local portrait_state = nil

hl.unbind("SUPER + SHIFT + P")

hl.bind("SUPER + SHIFT + P", function()
  local window = hl.get_active_window()
  local monitor = hl.get_active_monitor()

  if not window or not monitor then
    return
  end

  if portrait_state then
    -- Restore exact previous geometry
    hl.dispatch(hl.dsp.window.resize({
      x = portrait_state.width,
      y = portrait_state.height,
      relative = false
    }))

    hl.dispatch(hl.dsp.window.move({
      x = portrait_state.x,
      y = portrait_state.y,
      relative = false
    }))

    -- Restore tiled/floating state
    if not portrait_state.floating then
      hl.dispatch(hl.dsp.window.float({ action = "unset" }))
    end

    portrait_state = nil
  else
    -- Save exact current state
    portrait_state = {
      x = window.at.x,
      y = window.at.y,
      width = window.size.x,
      height = window.size.y,
      floating = window.floating
    }

    local padding = 60
    local logical_height = monitor.height / monitor.scale
    local height = logical_height - (padding * 2)

    hl.dispatch(hl.dsp.window.float({ action = "set" }))

    hl.dispatch(hl.dsp.window.resize({
      x = 1400,
      y = height,
      relative = false
    }))

    hl.dispatch(hl.dsp.window.center())
  end
end, {
  description = "Portrait window"
})

-- Diable middle click

hl.bind("mouse:274", function()
  hl.dispatch(hl.dsp.send_key_state({
    state = "down",
    mods = "",
    key = "mouse:272",
    window = "activewindow"
  }))
end)

hl.bind("mouse:274", function()
  hl.dispatch(hl.dsp.send_key_state({
    state = "up",
    mods = "",
    key = "mouse:272",
    window = "activewindow"
  }))
end, { release = true })

hl.unbind("SUPER + SHIFT + E")
o.bind("SUPER + SHIFT + E", "Gmail", { webapp = "https://mail.google.com/" })

hl.unbind("SUPER + SHIFT + C")
o.bind("SUPER + SHIFT + C", "Google Calendar", { webapp = "https://calendar.google.com/" })
