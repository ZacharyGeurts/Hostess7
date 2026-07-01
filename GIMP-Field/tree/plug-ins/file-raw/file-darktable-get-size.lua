--[[
  This file is part of AmmoOS Image,
  copyright (c) 2016 Tobias Ellinghaus

  AmmoOS Image is free software: you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation, either version 3 of the License, or
  (at your option) any later version.

  AmmoOS Image is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License
  along with AmmoOS Image.  If not, see <https://www.gnu.org/licenses/>.
]]

local dt = require "darktable"

print("[dt4gimp] " .. (dt.database[1].width) .. " " .. (dt.database[1].height))
