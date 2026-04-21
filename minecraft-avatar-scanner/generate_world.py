#!/usr/bin/env python3
"""
Minecraft Bedrock Edition .mcworld Generator
=============================================
Creates an "Avatar Scanner" world with:
- A large decorative camera structure
- A scanning platform with a button trigger
- A display wall where a pixel-art avatar is rebuilt block-by-block
- Command block circuits that animate scanning + building effects
"""

import struct
import os
import shutil
import zipfile
import io
import math
import amulet_nbt as nbt
from leveldb import LevelDB

# ============================================================
# CONFIGURATION
# ============================================================
WORLD_NAME = "Avatar Scanner - Extremely Hard Build"
WORLD_DIR = "/home/ubuntu/minecraft-avatar-scanner/world"
MCWORLD_PATH = "/home/ubuntu/minecraft-avatar-scanner/AvatarScanner.mcworld"

SPAWN_X, SPAWN_Y, SPAWN_Z = 0, 8, -20

# Structure positions
PLATFORM_CENTER = (0, 5, -10)  # Where player stands
CAMERA_BASE = (-5, 5, 2)       # Camera structure origin
DISPLAY_ORIGIN = (14, 5, -12)  # Bottom-left of display wall (on X-Z plane, wall faces west)
COMMAND_Y = 1                   # Y level for command blocks

# Avatar: 8 wide x 16 tall pixel art of Steve
# 0=air, 1=brown(hair), 2=skin, 3=white(eye), 4=light_blue(pupil),
# 5=cyan(shirt), 6=blue(pants), 7=gray(shoes), 8=pink(mouth)
AVATAR = [
    [0,1,1,1,1,1,1,0],  # 15 top - hair
    [1,1,1,1,1,1,1,1],  # 14
    [1,2,2,2,2,2,2,1],  # 13
    [2,3,4,2,2,4,3,2],  # 12 eyes
    [2,2,2,2,2,2,2,2],  # 11
    [2,2,8,8,8,8,2,2],  # 10 mouth
    [0,2,5,5,5,5,2,0],  # 9  shirt top + arms
    [0,2,5,5,5,5,2,0],  # 8
    [0,2,5,5,5,5,2,0],  # 7
    [0,2,5,5,5,5,2,0],  # 6
    [0,0,5,5,5,5,0,0],  # 5  shirt bottom
    [0,0,6,6,6,6,0,0],  # 4  pants
    [0,0,6,6,6,6,0,0],  # 3
    [0,0,6,0,0,6,0,0],  # 2  legs
    [0,0,6,0,0,6,0,0],  # 1
    [0,0,7,0,0,7,0,0],  # 0 bottom - shoes
]

# Map avatar color IDs to Bedrock block names
COLOR_BLOCKS = {
    1: "minecraft:concrete",    # brown  -> data 12
    2: "minecraft:concrete",    # skin   -> data 1 (orange)
    3: "minecraft:concrete",    # white  -> data 0
    4: "minecraft:concrete",    # blue   -> data 3 (light blue)
    5: "minecraft:concrete",    # cyan   -> data 9
    6: "minecraft:concrete",    # pants  -> data 11 (blue)
    7: "minecraft:concrete",    # gray   -> data 7
    8: "minecraft:concrete",    # pink   -> data 6
}

# Concrete color data values
COLOR_DATA = {
    1: 12,  # brown
    2: 1,   # orange (skin)
    3: 0,   # white
    4: 3,   # light blue
    5: 9,   # cyan
    6: 11,  # blue
    7: 7,   # gray
    8: 6,   # pink
}

# Concrete color names for /setblock commands (Bedrock 1.20+)
COLOR_NAMES = {
    1: "brown_concrete",
    2: "orange_concrete",
    3: "white_concrete",
    4: "light_blue_concrete",
    5: "cyan_concrete",
    6: "blue_concrete",
    7: "gray_concrete",
    8: "pink_concrete",
}

# Block name -> palette tuple (name, states_dict)
BLOCK_PALETTE = {
    "air": ("minecraft:air", {}),
    "bedrock": ("minecraft:bedrock", {}),
    "stone": ("minecraft:stone", {"stone_type": nbt.StringTag("stone")}),
    "grass": ("minecraft:grass_block", {}),
    "dirt": ("minecraft:dirt", {"dirt_type": nbt.StringTag("normal")}),
    "black_concrete": ("minecraft:concrete", {"color": nbt.StringTag("black")}),
    "white_concrete": ("minecraft:concrete", {"color": nbt.StringTag("white")}),
    "gray_concrete": ("minecraft:concrete", {"color": nbt.StringTag("gray")}),
    "light_gray_concrete": ("minecraft:concrete", {"color": nbt.StringTag("silver")}),
    "brown_concrete": ("minecraft:concrete", {"color": nbt.StringTag("brown")}),
    "orange_concrete": ("minecraft:concrete", {"color": nbt.StringTag("orange")}),
    "cyan_concrete": ("minecraft:concrete", {"color": nbt.StringTag("cyan")}),
    "blue_concrete": ("minecraft:concrete", {"color": nbt.StringTag("blue")}),
    "light_blue_concrete": ("minecraft:concrete", {"color": nbt.StringTag("light_blue")}),
    "pink_concrete": ("minecraft:concrete", {"color": nbt.StringTag("pink")}),
    "yellow_concrete": ("minecraft:concrete", {"color": nbt.StringTag("yellow")}),
    "red_concrete": ("minecraft:concrete", {"color": nbt.StringTag("red")}),
    "quartz_block": ("minecraft:quartz_block", {"chisel_type": nbt.StringTag("default"), "pillar_axis": nbt.StringTag("y")}),
    "smooth_quartz": ("minecraft:quartz_block", {"chisel_type": nbt.StringTag("smooth"), "pillar_axis": nbt.StringTag("y")}),
    "iron_block": ("minecraft:iron_block", {}),
    "sea_lantern": ("minecraft:sea_lantern", {}),
    "glowstone": ("minecraft:glowstone", {}),
    "glass": ("minecraft:glass", {}),
    "black_glass": ("minecraft:stained_glass", {"color": nbt.StringTag("black")}),
    "gray_glass": ("minecraft:stained_glass", {"color": nbt.StringTag("gray")}),
    "light_blue_glass": ("minecraft:stained_glass", {"color": nbt.StringTag("light_blue")}),
    "cyan_glass": ("minecraft:stained_glass", {"color": nbt.StringTag("cyan")}),
    "redstone_lamp": ("minecraft:redstone_lamp", {}),
    "redstone_block": ("minecraft:redstone_block", {}),
    "obsidian": ("minecraft:obsidian", {}),
    "diamond_block": ("minecraft:diamond_block", {}),
    "gold_block": ("minecraft:gold_block", {}),
    "emerald_block": ("minecraft:emerald_block", {}),
    "lapis_block": ("minecraft:lapis_block", {}),
    "netherite_block": ("minecraft:netherite_block", {}),
    "crying_obsidian": ("minecraft:crying_obsidian", {}),
    "prismarine": ("minecraft:prismarine", {"prismarine_block_type": nbt.StringTag("default")}),
    "dark_prismarine": ("minecraft:prismarine", {"prismarine_block_type": nbt.StringTag("dark")}),
    "command_block": ("minecraft:command_block", {"facing_direction": nbt.IntTag(5), "conditional_bit": nbt.ByteTag(0)}),
    "chain_command_block": ("minecraft:chain_command_block", {"facing_direction": nbt.IntTag(5), "conditional_bit": nbt.ByteTag(0)}),
    "repeating_command_block": ("minecraft:repeating_command_block", {"facing_direction": nbt.IntTag(5), "conditional_bit": nbt.ByteTag(0)}),
    "stone_button": ("minecraft:stone_button", {"facing_direction": nbt.IntTag(2), "button_pressed_bit": nbt.ByteTag(0)}),
    "iron_bars": ("minecraft:iron_bars", {}),
    "stone_slab": ("minecraft:stone_block_slab", {"stone_slab_type": nbt.StringTag("smooth_stone"), "minecraft:vertical_half": nbt.StringTag("bottom")}),
    "polished_blackstone": ("minecraft:polished_blackstone", {}),
    "polished_deepslate": ("minecraft:polished_deepslate", {}),
    "barrier": ("minecraft:barrier", {}),
}

# ============================================================
# WORLD DATA - Block placement buffer
# ============================================================
# We store blocks as {(x,y,z): "block_key"} and command block entities separately
placed_blocks = {}
command_block_entities = []

def place_block(x, y, z, block_key):
    placed_blocks[(x, y, z)] = block_key

def place_command_block(x, y, z, block_type, command, auto=True, tick_delay=0, 
                         conditional=False, facing=5, custom_name=""):
    """Place a command block with NBT data.
    block_type: 'command_block', 'chain_command_block', 'repeating_command_block'
    facing: 0=down,1=up,2=north,3=south,4=west,5=east
    """
    # Determine block key with correct facing
    bkey = f"cb_{x}_{y}_{z}"
    BLOCK_PALETTE[bkey] = (
        f"minecraft:{block_type}",
        {
            "facing_direction": nbt.IntTag(facing),
            "conditional_bit": nbt.ByteTag(1 if conditional else 0),
        }
    )
    placed_blocks[(x, y, z)] = bkey
    
    # LPCommandMode: 0=impulse, 1=repeat, 2=chain
    if block_type == "repeating_command_block":
        lp_mode = 1
    elif block_type == "chain_command_block":
        lp_mode = 2
    else:
        lp_mode = 0
    
    command_block_entities.append({
        "x": x, "y": y, "z": z,
        "command": command,
        "block_type": block_type,
        "auto": auto,
        "tick_delay": tick_delay,
        "conditional": conditional,
        "lp_mode": lp_mode,
        "custom_name": custom_name,
    })


# ============================================================
# BUILD STRUCTURES
# ============================================================

def build_ground():
    """Build the ground platform."""
    for x in range(-35, 45):
        for z in range(-35, 25):
            place_block(x, 0, z, "bedrock")
            for y in range(1, 4):
                place_block(x, y, z, "stone")
            place_block(x, 4, z, "polished_deepslate")
    
    # Decorative pattern on ground
    for x in range(-30, 40):
        for z in range(-30, 20):
            if (x + z) % 8 == 0 or (x - z) % 8 == 0:
                place_block(x, 4, z, "polished_blackstone")


def build_camera():
    """Build a large decorative camera structure."""
    bx, by, bz = CAMERA_BASE  # (-5, 5, 2)
    
    # Camera body: 10 wide (x), 10 tall (y), 8 deep (z)
    # Made of black concrete with details
    for x in range(bx, bx + 10):
        for y in range(by, by + 10):
            for z in range(bz, bz + 8):
                # Outer shell
                is_edge_x = (x == bx or x == bx + 9)
                is_edge_y = (y == by or y == by + 9)
                is_edge_z = (z == bz or z == bz + 7)
                
                if is_edge_x or is_edge_y or is_edge_z:
                    place_block(x, y, z, "black_concrete")
                else:
                    place_block(x, y, z, "gray_concrete")
    
    # Lens (south face z=bz, centered) - circular pattern
    lens_cx, lens_cy = bx + 5, by + 5
    for x in range(bx + 1, bx + 9):
        for y in range(by + 1, by + 9):
            dx = x - lens_cx + 0.5
            dy = y - lens_cy + 0.5
            dist = math.sqrt(dx*dx + dy*dy)
            if dist < 2.0:
                place_block(x, y, bz, "diamond_block")
            elif dist < 3.0:
                place_block(x, y, bz, "light_blue_glass")
            elif dist < 3.8:
                place_block(x, y, bz, "cyan_glass")
    
    # Lens ring
    for x in range(bx + 1, bx + 9):
        for y in range(by + 1, by + 9):
            dx = x - lens_cx + 0.5
            dy = y - lens_cy + 0.5
            dist = math.sqrt(dx*dx + dy*dy)
            if 3.5 < dist < 4.2:
                place_block(x, y, bz, "iron_block")
    
    # Flash on top
    place_block(bx + 3, by + 10, bz + 2, "iron_block")
    place_block(bx + 4, by + 10, bz + 2, "glowstone")
    place_block(bx + 5, by + 10, bz + 2, "glowstone")
    place_block(bx + 6, by + 10, bz + 2, "iron_block")
    place_block(bx + 3, by + 11, bz + 2, "iron_block")
    place_block(bx + 4, by + 11, bz + 2, "sea_lantern")
    place_block(bx + 5, by + 11, bz + 2, "sea_lantern")
    place_block(bx + 6, by + 11, bz + 2, "iron_block")
    
    # Tripod legs
    for leg_x in [bx + 2, bx + 7]:
        for y in range(by - 1, by + 5):
            place_block(leg_x, by - (by - y), bz + 4, "iron_bars")
    # Center leg
    for y_off in range(5):
        place_block(bx + 5, by - 1 + y_off, bz + 6, "iron_bars") if y_off < 2 else None
    
    # Viewfinder on top
    place_block(bx + 4, by + 10, bz + 5, "black_concrete")
    place_block(bx + 5, by + 10, bz + 5, "black_concrete")
    place_block(bx + 4, by + 11, bz + 5, "black_concrete")
    place_block(bx + 5, by + 11, bz + 5, "gray_glass")
    
    # "SCAN" label on camera side
    # Small text using colored blocks on the east side (x = bx+9)
    for y in range(by + 3, by + 7):
        place_block(bx + 9, y, bz + 3, "red_concrete")
        place_block(bx + 9, y, bz + 4, "red_concrete")


def build_scanning_platform():
    """Build the scanning platform with button."""
    px, py, pz = PLATFORM_CENTER  # (0, 5, -10)
    
    # Main platform 5x5 of sea lanterns
    for x in range(px - 2, px + 3):
        for z in range(pz - 2, pz + 3):
            place_block(x, py - 1, z, "sea_lantern")
    
    # Iron frame around it
    for x in range(px - 3, px + 4):
        for z in range(pz - 3, pz + 4):
            is_edge = (x == px - 3 or x == px + 3 or z == pz - 3 or z == pz + 3)
            if is_edge:
                place_block(x, py - 1, z, "iron_block")
    
    # Corner pillars with redstone lamps
    for cx, cz in [(px-3, pz-3), (px+3, pz-3), (px-3, pz+3), (px+3, pz+3)]:
        for y in range(py, py + 4):
            place_block(cx, y, cz, "quartz_block")
        place_block(cx, py + 4, cz, "sea_lantern")
    
    # Diamond accent blocks
    for cx, cz in [(px-2, pz-2), (px+2, pz-2), (px-2, pz+2), (px+2, pz+2)]:
        place_block(cx, py - 1, cz, "diamond_block")
    
    # Button pillar in front of platform
    place_block(px, py, pz - 3, "quartz_block")
    place_block(px, py + 1, pz - 3, "quartz_block")
    # Button on the south face of the pillar (facing player approaching from south)
    btn_key = "btn_trigger"
    BLOCK_PALETTE[btn_key] = ("minecraft:stone_button", {
        "facing_direction": nbt.IntTag(3),  # south face
        "button_pressed_bit": nbt.ByteTag(0),
    })
    place_block(px, py + 1, pz - 4, btn_key)
    
    # Signs/indicators - gold blocks spelling "STAND HERE"
    for x in range(px - 1, px + 2):
        place_block(x, py - 1, pz - 4, "gold_block")
    
    # Arch over platform
    for x in range(px - 3, px + 4):
        place_block(x, py + 6, pz - 2, "iron_block")
        place_block(x, py + 6, pz + 2, "iron_block")
    for z in range(pz - 2, pz + 3):
        place_block(px - 3, py + 6, z, "iron_block")
        place_block(px + 3, py + 6, z, "iron_block")
    # Glowstone in arch
    for x in range(px - 2, px + 3):
        for z in range(pz - 1, pz + 2):
            place_block(x, py + 6, z, "glowstone")


def build_display_wall():
    """Build the display wall where the avatar appears."""
    ox, oy, oz = DISPLAY_ORIGIN  # (14, 5, -12)
    
    # Wall dimensions: avatar is 8 wide (along z) x 16 tall (along y)
    # Frame: 2 blocks extra on each side
    wall_w = 12  # z direction
    wall_h = 20  # y direction
    
    # Back wall (black concrete)
    for dz in range(-2, wall_w + 2):
        for dy in range(-2, wall_h + 2):
            z = oz + dz
            y = oy + dy
            place_block(ox, y, z, "black_concrete")
            place_block(ox + 1, y, z, "black_concrete")
    
    # Quartz frame
    for dz in range(-1, wall_w + 1):
        for dy in range(-1, wall_h + 1):
            z = oz + dz
            y = oy + dy
            is_frame = (dz == -1 or dz == wall_w or dy == -1 or dy == wall_h)
            if is_frame:
                place_block(ox - 1, y, z, "quartz_block")
    
    # Corner accents
    for dz, dy in [(-1, -1), (-1, wall_h), (wall_w, -1), (wall_w, wall_h)]:
        place_block(ox - 1, oy + dy, oz + dz, "gold_block")
    
    # Top label bar
    for dz in range(0, wall_w):
        place_block(ox - 1, oy + wall_h + 1, oz + dz, "iron_block")
    
    # Sea lantern lighting at top and bottom
    for dz in range(0, wall_w):
        place_block(ox - 2, oy + wall_h, oz + dz, "sea_lantern")
        place_block(ox - 2, oy - 1, oz + dz, "sea_lantern")
    
    # Inner display area: initially dark gray glass (will be replaced by avatar blocks)
    for dz in range(wall_w):
        for dy in range(wall_h):
            # Map to avatar pixels (centered, with padding)
            az = dz - 2  # avatar x (0-7)
            ay = dy - 2  # avatar y from bottom (0-15)
            if 0 <= az < 8 and 0 <= ay < 16:
                # Start with dark background that will be replaced
                place_block(ox - 1, oy + dy, oz + dz, "black_glass")
            else:
                place_block(ox - 1, oy + dy, oz + dz, "gray_glass")
    
    # Decorative base
    for dz in range(-2, wall_w + 2):
        place_block(ox - 1, oy - 2, oz + dz, "obsidian")
        place_block(ox, oy - 2, oz + dz, "obsidian")
        place_block(ox + 1, oy - 2, oz + dz, "obsidian")
    
    # Side pillars with sea lanterns
    for dy in range(-2, wall_h + 3):
        place_block(ox - 1, oy + dy, oz - 2, "quartz_block")
        place_block(ox - 1, oy + dy, oz + wall_w + 1, "quartz_block")
        if dy % 3 == 0:
            place_block(ox - 2, oy + dy, oz - 2, "sea_lantern")
            place_block(ox - 2, oy + dy, oz + wall_w + 1, "sea_lantern")


def build_command_blocks():
    """Build the command block circuit underground."""
    # Command blocks run along x axis at y=COMMAND_Y, z=0
    # Starting position
    sx, sy, sz = -5, COMMAND_Y, 0
    cx = sx
    
    # --- Block 0: Repeating command block (always active) ---
    # Detects player on platform and checks cooldown
    px, py, pz = PLATFORM_CENTER
    place_command_block(
        cx, sy, sz,
        "repeating_command_block",
        f"execute @p[x={px-2},y={py-2},z={pz-2},dx=4,dy=4,dz=4] ~~~ testforblock {cx+1} {sy+1} {sz} air",
        auto=True, tick_delay=0
    )
    # Flag block position (used to prevent re-triggering)
    flag_pos = (cx + 1, sy + 1, sz)
    place_block(flag_pos[0], flag_pos[1], flag_pos[2], "air")
    
    cx += 1
    
    # --- Block 1: Chain - Set flag to prevent re-trigger ---
    place_command_block(
        cx, sy, sz,
        "chain_command_block",
        f"setblock {flag_pos[0]} {flag_pos[1]} {flag_pos[2]} stone",
        auto=True, tick_delay=0, conditional=True
    )
    cx += 1
    
    # --- Block 2: Title - SCANNING ---
    place_command_block(
        cx, sy, sz,
        "chain_command_block",
        'title @a title §l§c⚡ SCANNING ⚡',
        auto=True, tick_delay=5
    )
    cx += 1
    
    # --- Block 3: Sound ---
    place_command_block(
        cx, sy, sz,
        "chain_command_block",
        f"playsound note.pling @a {px} {py} {pz}",
        auto=True, tick_delay=10
    )
    cx += 1
    
    # --- Block 4: Subtitle ---
    place_command_block(
        cx, sy, sz,
        "chain_command_block",
        'title @a subtitle §7Analyzing player data...',
        auto=True, tick_delay=20
    )
    cx += 1
    
    # --- Block 5: Particles ---
    place_command_block(
        cx, sy, sz,
        "chain_command_block",
        f"particle minecraft:villager_happy {px} {py+1} {pz}",
        auto=True, tick_delay=10
    )
    cx += 1
    
    # --- Block 6: More particles ---
    place_command_block(
        cx, sy, sz,
        "chain_command_block",
        f"particle minecraft:totem_particle {px} {py+2} {pz}",
        auto=True, tick_delay=20
    )
    cx += 1
    
    # --- Block 7: COMPUTING title ---
    place_command_block(
        cx, sy, sz,
        "chain_command_block",
        'title @a title §l§a◆ COMPUTING ◆',
        auto=True, tick_delay=30
    )
    cx += 1
    
    # --- Block 8: Subtitle ---
    place_command_block(
        cx, sy, sz,
        "chain_command_block",
        'title @a subtitle §7Rebuilding avatar with blocks...',
        auto=True, tick_delay=10
    )
    cx += 1
    
    # --- Block 9: Sound ---
    place_command_block(
        cx, sy, sz,
        "chain_command_block",
        f"playsound random.levelup @a {px} {py} {pz}",
        auto=True, tick_delay=20
    )
    cx += 1
    
    # --- Avatar building blocks ---
    # Place avatar pixels from bottom-left to top-right, row by row
    ox, oy, oz = DISPLAY_ORIGIN
    # Avatar rows are stored top-to-bottom in AVATAR list
    # Row 0 in AVATAR = top of head = highest y
    # We iterate bottom to top for building effect
    
    block_count = 0
    for row_from_bottom in range(16):
        avatar_row = 15 - row_from_bottom  # index in AVATAR list
        for col in range(8):
            color_id = AVATAR[avatar_row][col]
            if color_id == 0:
                continue
            
            block_name = COLOR_NAMES[color_id]
            # Display wall position
            # ox-1 is the display surface X
            # oz + col + 2 is the Z position (2 offset for frame)
            # oy + row_from_bottom + 2 is the Y position (2 offset for frame)
            bx = ox - 1
            by = oy + row_from_bottom + 2
            bz = oz + col + 2
            
            # Calculate tick delay - faster for dramatic effect
            tick = 2 if block_count > 0 else 30
            
            place_command_block(
                cx, sy, sz,
                "chain_command_block",
                f"setblock {bx} {by} {bz} {block_name}",
                auto=True, tick_delay=tick
            )
            cx += 1
            
            # Every 8 blocks, add a sound effect
            if block_count % 8 == 0:
                place_command_block(
                    cx, sy, sz,
                    "chain_command_block",
                    f"playsound note.hat @a {bx} {by} {bz}",
                    auto=True, tick_delay=0
                )
                cx += 1
            
            block_count += 1
    
    # --- Completion effects ---
    place_command_block(
        cx, sy, sz,
        "chain_command_block",
        'title @a title §l§b★ COMPLETE ★',
        auto=True, tick_delay=20
    )
    cx += 1
    
    place_command_block(
        cx, sy, sz,
        "chain_command_block",
        'title @a subtitle §7Avatar successfully reconstructed!',
        auto=True, tick_delay=5
    )
    cx += 1
    
    place_command_block(
        cx, sy, sz,
        "chain_command_block",
        f"playsound random.totem @a {px} {py} {pz}",
        auto=True, tick_delay=20
    )
    cx += 1
    
    # Firework particles
    place_command_block(
        cx, sy, sz,
        "chain_command_block",
        f"particle minecraft:totem_particle {ox-2} {oy+12} {oz+6}",
        auto=True, tick_delay=10
    )
    cx += 1
    
    # Reset: clear the flag after a delay so it can be triggered again
    place_command_block(
        cx, sy, sz,
        "chain_command_block",
        f"setblock {flag_pos[0]} {flag_pos[1]} {flag_pos[2]} air",
        auto=True, tick_delay=100
    )
    cx += 1
    
    # Also clear the display wall for next scan
    for row_from_bottom in range(16):
        avatar_row = 15 - row_from_bottom
        for col in range(8):
            color_id = AVATAR[avatar_row][col]
            if color_id == 0:
                continue
            bx_d = ox - 1
            by_d = oy + row_from_bottom + 2
            bz_d = oz + col + 2
            place_command_block(
                cx, sy, sz,
                "chain_command_block",
                f"setblock {bx_d} {by_d} {bz_d} black_stained_glass",
                auto=True, tick_delay=0
            )
            cx += 1
    
    print(f"  Total command blocks: {cx - sx}")
    
    # Cover command blocks with stone (hide them)
    for x in range(sx - 1, cx + 2):
        for z in range(sz - 1, sz + 2):
            place_block(x, sy - 1, z, "bedrock")
            place_block(x, sy + 2, z, "stone")
            if z != sz:
                place_block(x, sy, z, "stone")
                place_block(x, sy + 1, z, "stone")


def build_decorations():
    """Add extra decorative elements."""
    # Pathway from spawn to platform
    for z in range(SPAWN_Z, PLATFORM_CENTER[2] - 3):
        for x in range(-2, 3):
            if abs(x) <= 1:
                place_block(x, 4, z, "smooth_quartz")
            else:
                place_block(x, 4, z, "quartz_block")
    
    # Pathway from platform to display wall
    for x in range(3, DISPLAY_ORIGIN[0] - 1):
        for z in range(-2, 3):
            if abs(z) <= 1:
                place_block(x, 4, PLATFORM_CENTER[2] + z, "smooth_quartz")
    
    # Lighting posts along paths
    for z in range(SPAWN_Z, PLATFORM_CENTER[2] - 3, 5):
        for side_x in [-3, 3]:
            place_block(side_x, 5, z, "quartz_block")
            place_block(side_x, 6, z, "quartz_block")
            place_block(side_x, 7, z, "sea_lantern")
    
    # Arrow indicators on ground pointing to platform
    for z in range(SPAWN_Z + 3, PLATFORM_CENTER[2] - 5, 3):
        place_block(0, 4, z, "gold_block")


# ============================================================
# BEDROCK WORLD FORMAT HELPERS
# ============================================================

def make_level_dat():
    """Create the level.dat file for Bedrock Edition."""
    root = nbt.CompoundTag({
        "BiomeOverride": nbt.StringTag(""),
        "CenterMapsToOrigin": nbt.ByteTag(0),
        "ConfirmedPlatformLockedContent": nbt.ByteTag(0),
        "Difficulty": nbt.IntTag(1),
        "FlatWorldLayers": nbt.StringTag('{"biome_id":1,"block_layers":[{"block_name":"minecraft:bedrock","count":1},{"block_name":"minecraft:stone","count":3},{"block_name":"minecraft:grass","count":1}],"encoding_version":6,"structure_options":null,"world_version":"version.post_1_18"}'),
        "ForceGameType": nbt.ByteTag(0),
        "GameType": nbt.IntTag(1),  # Creative
        "Generator": nbt.IntTag(2),  # Flat
        "InventoryVersion": nbt.StringTag("1.20.80"),
        "LANBroadcast": nbt.ByteTag(1),
        "LANBroadcastIntent": nbt.ByteTag(1),
        "LastPlayed": nbt.LongTag(0),
        "LevelName": nbt.StringTag(WORLD_NAME),
        "LimitedWorldOriginX": nbt.IntTag(0),
        "LimitedWorldOriginY": nbt.IntTag(32767),
        "LimitedWorldOriginZ": nbt.IntTag(0),
        "MinimumCompatibleClientVersion": nbt.ListTag([
            nbt.IntTag(1), nbt.IntTag(20), nbt.IntTag(80), nbt.IntTag(0), nbt.IntTag(0)
        ]),
        "MultiplayerGame": nbt.ByteTag(1),
        "MultiplayerGameIntent": nbt.ByteTag(1),
        "NetherScale": nbt.IntTag(8),
        "NetworkVersion": nbt.IntTag(671),
        "Platform": nbt.IntTag(2),
        "PlatformBroadcastIntent": nbt.IntTag(3),
        "RandomSeed": nbt.LongTag(12345),
        "SpawnV1Villagers": nbt.ByteTag(0),
        "SpawnX": nbt.IntTag(SPAWN_X),
        "SpawnY": nbt.IntTag(SPAWN_Y),
        "SpawnZ": nbt.IntTag(SPAWN_Z),
        "StorageVersion": nbt.IntTag(10),
        "Time": nbt.LongTag(6000),
        "WorldVersion": nbt.IntTag(1),
        "XBLBroadcastIntent": nbt.IntTag(3),
        "commandblockoutput": nbt.ByteTag(0),
        "commandblocksenabled": nbt.ByteTag(1),
        "commandsEnabled": nbt.ByteTag(1),
        "currentTick": nbt.LongTag(0),
        "dodaylightcycle": nbt.ByteTag(0),
        "doentitydrops": nbt.ByteTag(1),
        "dofiretick": nbt.ByteTag(0),
        "doimmediaterespawn": nbt.ByteTag(0),
        "domobloot": nbt.ByteTag(1),
        "domobspawning": nbt.ByteTag(0),
        "dotiledrops": nbt.ByteTag(1),
        "doweathercycle": nbt.ByteTag(0),
        "drowningdamage": nbt.ByteTag(0),
        "eduOffer": nbt.IntTag(0),
        "falldamage": nbt.ByteTag(0),
        "firedamage": nbt.ByteTag(0),
        "functioncommandlimit": nbt.IntTag(10000),
        "hasBeenLoadedInCreative": nbt.ByteTag(1),
        "hasLockedBehaviorPack": nbt.ByteTag(0),
        "hasLockedResourcePack": nbt.ByteTag(0),
        "immutableWorld": nbt.ByteTag(0),
        "isCreatedInEditor": nbt.ByteTag(0),
        "isExportedFromEditor": nbt.ByteTag(0),
        "isFromLockedTemplate": nbt.ByteTag(0),
        "isFromWorldTemplate": nbt.ByteTag(0),
        "isSingleUseWorld": nbt.ByteTag(0),
        "isWorldTemplateOptionLocked": nbt.ByteTag(0),
        "keepinventory": nbt.ByteTag(1),
        "lastOpenedWithVersion": nbt.ListTag([
            nbt.IntTag(1), nbt.IntTag(20), nbt.IntTag(80), nbt.IntTag(0), nbt.IntTag(0)
        ]),
        "lightningLevel": nbt.FloatTag(0.0),
        "lightningTime": nbt.IntTag(0),
        "limitedWorldDepth": nbt.IntTag(16),
        "limitedWorldWidth": nbt.IntTag(16),
        "maxcommandchainlength": nbt.IntTag(65535),
        "mobgriefing": nbt.ByteTag(0),
        "naturalregeneration": nbt.ByteTag(1),
        "permissionsLevel": nbt.IntTag(1),
        "playerPermissionsLevel": nbt.IntTag(1),
        "prid": nbt.StringTag(""),
        "pvp": nbt.ByteTag(0),
        "rainLevel": nbt.FloatTag(0.0),
        "rainTime": nbt.IntTag(0),
        "randomtickspeed": nbt.IntTag(0),
        "requiresCopiedPackRemovalCheck": nbt.ByteTag(0),
        "respawnblocksexplode": nbt.ByteTag(0),
        "sendcommandfeedback": nbt.ByteTag(0),
        "serverChunkTickRange": nbt.IntTag(4),
        "showbordereffect": nbt.ByteTag(1),
        "showcoordinates": nbt.ByteTag(1),
        "showdeathmessages": nbt.ByteTag(1),
        "showtags": nbt.ByteTag(1),
        "spawnMobs": nbt.ByteTag(0),
        "spawnradius": nbt.IntTag(0),
        "startWithMapEnabled": nbt.ByteTag(0),
        "texturePacksRequired": nbt.ByteTag(0),
        "tntexplodes": nbt.ByteTag(0),
        "useMsaGamertagsOnly": nbt.ByteTag(0),
        "worldStartCount": nbt.LongTag(0),
        "abilities": nbt.CompoundTag({
            "attackmobs": nbt.ByteTag(1),
            "attackplayers": nbt.ByteTag(1),
            "build": nbt.ByteTag(1),
            "doorsandswitches": nbt.ByteTag(1),
            "flySpeed": nbt.FloatTag(0.05),
            "flying": nbt.ByteTag(0),
            "instabuild": nbt.ByteTag(0),
            "invulnerable": nbt.ByteTag(0),
            "lightning": nbt.ByteTag(0),
            "mayfly": nbt.ByteTag(1),
            "mine": nbt.ByteTag(1),
            "op": nbt.ByteTag(1),
            "opencontainers": nbt.ByteTag(1),
            "permissionsLevel": nbt.IntTag(1),
            "playerPermissionsLevel": nbt.IntTag(1),
            "teleport": nbt.ByteTag(1),
            "walkSpeed": nbt.FloatTag(0.1),
        }),
    })
    
    named = nbt.NamedTag(root, "")
    nbt_data = named.to_nbt(compressed=False, little_endian=True)
    
    # level.dat format: version(4) + length(4) + nbt_data
    header = struct.pack('<II', 10, len(nbt_data))
    return header + nbt_data


def make_block_nbt(name, states):
    """Create NBT for a block palette entry."""
    states_tag = nbt.CompoundTag({k: v for k, v in states.items()})
    tag = nbt.CompoundTag({
        "name": nbt.StringTag(name),
        "states": states_tag,
        "version": nbt.IntTag(18100737),  # 1.20.80.1
    })
    return tag.to_nbt(compressed=False, little_endian=True)


def make_subchunk_data(blocks_16x16x16, palette_list):
    """
    Create binary subchunk data (version 8).
    blocks_16x16x16: dict of (x,y,z) -> palette_index for blocks within the subchunk
    palette_list: list of (block_name, states_dict) tuples
    """
    if not palette_list:
        palette_list = [("minecraft:air", {})]
    
    # Ensure air is first in palette
    air_entry = ("minecraft:air", {})
    if air_entry not in palette_list:
        palette_list = [air_entry] + list(palette_list)
    
    palette_size = len(palette_list)
    
    # Determine bits per block
    if palette_size <= 2:
        bits = 1
    elif palette_size <= 4:
        bits = 2
    elif palette_size <= 8:
        bits = 3
    elif palette_size <= 16:
        bits = 4
    elif palette_size <= 32:
        bits = 5
    elif palette_size <= 64:
        bits = 6
    elif palette_size <= 256:
        bits = 8
    else:
        bits = 16
    
    blocks_per_word = 32 // bits
    num_words = (4096 + blocks_per_word - 1) // blocks_per_word
    
    # Pack block indices
    # Block order: XZY (y changes fastest)
    words = []
    for word_idx in range(num_words):
        word = 0
        for sub_idx in range(blocks_per_word):
            block_linear = word_idx * blocks_per_word + sub_idx
            if block_linear >= 4096:
                break
            # XZY order: x = block_linear >> 8, z = (block_linear >> 4) & 0xF, y = block_linear & 0xF
            x = (block_linear >> 8) & 0xF
            z = (block_linear >> 4) & 0xF
            y = block_linear & 0xF
            
            palette_idx = blocks_16x16x16.get((x, y, z), 0)
            word |= (palette_idx & ((1 << bits) - 1)) << (sub_idx * bits)
        words.append(word)
    
    # Build binary
    data = bytearray()
    data.append(8)  # version
    data.append(1)  # 1 storage layer
    data.append((bits << 1) | 1)  # bits_per_block with persistence flag
    
    for w in words:
        data.extend(struct.pack('<I', w & 0xFFFFFFFF))
    
    data.extend(struct.pack('<i', palette_size))
    
    for name, states in palette_list:
        nbt_bytes = make_block_nbt(name, states)
        data.extend(nbt_bytes)
    
    return bytes(data)


def make_data2d(height=4):
    """Create Data2D binary: heightmap (512 bytes) + biome data (256 bytes)."""
    data = bytearray()
    # Heightmap: 256 entries of int16 LE (one per XZ column)
    for _ in range(256):
        data.extend(struct.pack('<h', height))
    # Biome: 256 bytes (plains = 1)
    for _ in range(256):
        data.append(1)
    return bytes(data)


def make_block_entity_nbt(entity_data):
    """Create NBT for a command block entity."""
    tag = nbt.CompoundTag({
        "id": nbt.StringTag("CommandBlock"),
        "x": nbt.IntTag(entity_data["x"]),
        "y": nbt.IntTag(entity_data["y"]),
        "z": nbt.IntTag(entity_data["z"]),
        "Command": nbt.StringTag(entity_data["command"]),
        "CustomName": nbt.StringTag(entity_data.get("custom_name", "")),
        "ExecuteOnFirstTick": nbt.ByteTag(1),
        "LPCommandMode": nbt.IntTag(entity_data["lp_mode"]),
        "LPCondionalMode": nbt.ByteTag(1 if entity_data.get("conditional") else 0),
        "LPRedstoneMode": nbt.ByteTag(0),
        "LastExecution": nbt.LongTag(0),
        "LastOutput": nbt.StringTag(""),
        "LastOutputParams": nbt.ListTag([]),
        "TickDelay": nbt.IntTag(entity_data.get("tick_delay", 0)),
        "TrackOutput": nbt.ByteTag(1),
        "Version": nbt.IntTag(25),
        "auto": nbt.ByteTag(1 if entity_data.get("auto") else 0),
        "conditionMet": nbt.ByteTag(0),
        "conditionalMode": nbt.ByteTag(1 if entity_data.get("conditional") else 0),
        "isMovable": nbt.ByteTag(1),
        "powered": nbt.ByteTag(0),
        "successCount": nbt.IntTag(0),
    })
    return tag.to_nbt(compressed=False, little_endian=True)


# ============================================================
# CHUNK GENERATION & WORLD WRITING
# ============================================================

def generate_world():
    """Main world generation function."""
    print("Building structures...")
    build_ground()
    print("  Ground done")
    build_camera()
    print("  Camera done")
    build_scanning_platform()
    print("  Scanning platform done")
    build_display_wall()
    print("  Display wall done")
    build_command_blocks()
    print("  Command blocks done")
    build_decorations()
    print("  Decorations done")
    
    print(f"\nTotal blocks placed: {len(placed_blocks)}")
    print(f"Command block entities: {len(command_block_entities)}")
    
    # Determine which chunks we need
    chunks_needed = set()
    for (x, y, z) in placed_blocks:
        cx = x >> 4 if x >= 0 else -(-x >> 4) - (1 if x % 16 != 0 else 0)
        cz = z >> 4 if z >= 0 else -(-z >> 4) - (1 if z % 16 != 0 else 0)
        # Proper floor division for chunk coords
        cx = math.floor(x / 16)
        cz = math.floor(z / 16)
        chunks_needed.add((cx, cz))
    
    print(f"Chunks needed: {len(chunks_needed)}")
    
    # Create world directory
    if os.path.exists(WORLD_DIR):
        shutil.rmtree(WORLD_DIR)
    os.makedirs(os.path.join(WORLD_DIR, "db"), exist_ok=True)
    
    # Write level.dat
    print("\nWriting level.dat...")
    level_dat = make_level_dat()
    with open(os.path.join(WORLD_DIR, "level.dat"), "wb") as f:
        f.write(level_dat)
    
    # Copy as level.dat_old
    with open(os.path.join(WORLD_DIR, "level.dat_old"), "wb") as f:
        f.write(level_dat)
    
    # Write world metadata files
    with open(os.path.join(WORLD_DIR, "world_icon.jpeg"), "wb") as f:
        f.write(b"")  # empty placeholder
    
    with open(os.path.join(WORLD_DIR, "levelname.txt"), "w") as f:
        f.write(WORLD_NAME)
    
    # Write pack manifests  
    with open(os.path.join(WORLD_DIR, "world_behavior_packs.json"), "w") as f:
        f.write("[]")
    with open(os.path.join(WORLD_DIR, "world_resource_packs.json"), "w") as f:
        f.write("[]")
    
    # Open LevelDB
    print("Writing chunk data to LevelDB...")
    db = LevelDB(os.path.join(WORLD_DIR, "db"), create_if_missing=True)
    
    for chunk_x, chunk_z in sorted(chunks_needed):
        write_chunk(db, chunk_x, chunk_z)
    
    db.close()
    print("LevelDB written successfully!")
    
    # Package as .mcworld
    print(f"\nPackaging as {MCWORLD_PATH}...")
    if os.path.exists(MCWORLD_PATH):
        os.remove(MCWORLD_PATH)
    
    with zipfile.ZipFile(MCWORLD_PATH, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(WORLD_DIR):
            for file in files:
                filepath = os.path.join(root, file)
                arcname = os.path.relpath(filepath, WORLD_DIR)
                zf.write(filepath, arcname)
    
    file_size = os.path.getsize(MCWORLD_PATH)
    print(f"\nDone! Created {MCWORLD_PATH} ({file_size / 1024:.1f} KB)")


def write_chunk(db, chunk_x, chunk_z):
    """Write a complete chunk to LevelDB."""
    # Collect blocks in this chunk
    chunk_blocks = {}
    for (bx, by, bz), block_key in placed_blocks.items():
        bcx = math.floor(bx / 16)
        bcz = math.floor(bz / 16)
        if bcx == chunk_x and bcz == chunk_z:
            local_x = bx - chunk_x * 16
            local_z = bz - chunk_z * 16
            chunk_blocks[(local_x, by, local_z)] = block_key
    
    # Collect block entities in this chunk
    chunk_entities = []
    for ent in command_block_entities:
        ecx = math.floor(ent["x"] / 16)
        ecz = math.floor(ent["z"] / 16)
        if ecx == chunk_x and ecz == chunk_z:
            chunk_entities.append(ent)
    
    # Determine subchunk range
    if not chunk_blocks:
        min_sy, max_sy = 0, 0
    else:
        ys = [by for (_, by, _) in chunk_blocks]
        min_sy = min(ys) >> 4
        max_sy = max(ys) >> 4
    
    # Chunk key prefix
    key_prefix = struct.pack('<ii', chunk_x, chunk_z)
    
    # Write chunk version
    db.put(key_prefix + b'\x76', b'\x28')  # version 40
    
    # Write Data2D
    max_height = 4
    if chunk_blocks:
        max_height = max(by for (_, by, _) in chunk_blocks)
    db.put(key_prefix + b'\x2d', make_data2d(max_height))
    
    # Write FinalizedState (2 = done generating)
    db.put(key_prefix + b'\x36', struct.pack('<i', 2))
    
    # Write subchunks
    for sy in range(min_sy, max_sy + 1):
        # Collect blocks in this subchunk
        sc_blocks = {}
        sc_palette_set = set()
        sc_palette_set.add(("minecraft:air", ()))
        
        for (lx, by, lz), block_key in chunk_blocks.items():
            if by >> 4 == sy:
                local_y = by & 0xF
                
                if block_key in BLOCK_PALETTE:
                    name, states = BLOCK_PALETTE[block_key]
                    states_tuple = tuple(sorted((k, str(v)) for k, v in states.items()))
                else:
                    name = "minecraft:stone"
                    states_tuple = ()
                
                sc_palette_set.add((name, states_tuple))
        
        # Build ordered palette
        palette_list = [("minecraft:air", {})]
        palette_map = {("minecraft:air", ()): 0}
        
        for name, states_tuple in sc_palette_set:
            if (name, states_tuple) not in palette_map:
                states_dict = {}
                for k, v_str in states_tuple:
                    # Reconstruct the NBT tag from the original BLOCK_PALETTE
                    for bk, (bn, bs) in BLOCK_PALETTE.items():
                        if bn == name:
                            s_tuple = tuple(sorted((sk, str(sv)) for sk, sv in bs.items()))
                            if s_tuple == states_tuple:
                                states_dict = bs
                                break
                    if states_dict:
                        break
                
                palette_map[(name, states_tuple)] = len(palette_list)
                palette_list.append((name, states_dict))
        
        # Map blocks to palette indices
        block_indices = {}
        for (lx, by, lz), block_key in chunk_blocks.items():
            if by >> 4 == sy:
                local_y = by & 0xF
                
                if block_key in BLOCK_PALETTE:
                    name, states = BLOCK_PALETTE[block_key]
                    states_tuple = tuple(sorted((k, str(v)) for k, v in states.items()))
                else:
                    name = "minecraft:stone"
                    states_tuple = ()
                
                idx = palette_map.get((name, states_tuple), 0)
                block_indices[(lx, local_y, lz)] = idx
        
        # Create subchunk data
        sc_data = make_subchunk_data(block_indices, palette_list)
        
        # Write to DB
        sc_key = key_prefix + b'\x2f' + struct.pack('b', sy)
        db.put(sc_key, sc_data)
    
    # Write block entities
    if chunk_entities:
        entity_data = bytearray()
        for ent in chunk_entities:
            entity_data.extend(make_block_entity_nbt(ent))
        db.put(key_prefix + b'\x31', bytes(entity_data))


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print("  Minecraft Bedrock Avatar Scanner World Generator")
    print("=" * 60)
    print()
    generate_world()
