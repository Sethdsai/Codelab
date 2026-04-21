#!/usr/bin/env python3
"""
Minecraft Bedrock Edition .mcworld Generator v2
Uses amulet-core for correct world format handling.
"""

import os
import shutil
import zipfile
import math
import numpy as np
import amulet
from amulet.api.block import Block
from amulet.api.level import World
from amulet.api.chunk import Chunk
from amulet.utils.world_utils import block_coords_to_chunk_coords
import amulet_nbt as nbt

WORLD_NAME = "Avatar Scanner - Extremely Hard Build"
WORLD_DIR = "/home/ubuntu/minecraft-avatar-scanner/world_v2"
MCWORLD_PATH = "/home/ubuntu/minecraft-avatar-scanner/AvatarScanner.mcworld"

SPAWN_X, SPAWN_Y, SPAWN_Z = 0, 8, -20
PLATFORM_CENTER = (0, 5, -10)
CAMERA_BASE = (-5, 5, 2)
DISPLAY_ORIGIN = (14, 5, -12)
COMMAND_Y = 1

# 8x16 pixel Steve avatar (top to bottom)
# 0=air, 1=brown, 2=skin(orange), 3=white, 4=light_blue, 5=cyan, 6=blue, 7=gray, 8=pink
AVATAR = [
    [0,1,1,1,1,1,1,0],
    [1,1,1,1,1,1,1,1],
    [1,2,2,2,2,2,2,1],
    [2,3,4,2,2,4,3,2],
    [2,2,2,2,2,2,2,2],
    [2,2,8,8,8,8,2,2],
    [0,2,5,5,5,5,2,0],
    [0,2,5,5,5,5,2,0],
    [0,2,5,5,5,5,2,0],
    [0,2,5,5,5,5,2,0],
    [0,0,5,5,5,5,0,0],
    [0,0,6,6,6,6,0,0],
    [0,0,6,6,6,6,0,0],
    [0,0,6,0,0,6,0,0],
    [0,0,6,0,0,6,0,0],
    [0,0,7,0,0,7,0,0],
]

COLOR_NAMES = {
    1: "brown_concrete", 2: "orange_concrete", 3: "white_concrete",
    4: "light_blue_concrete", 5: "cyan_concrete", 6: "blue_concrete",
    7: "gray_concrete", 8: "pink_concrete",
}

# ============================================================
# Block placement buffer
# ============================================================
blocks_to_place = {}  # (x,y,z) -> (platform, namespace, base_name, properties)
command_blocks_data = []  # list of dicts with position + NBT data

PLATFORM = "bedrock"
NAMESPACE = "minecraft"

def place(x, y, z, base_name, properties=None):
    blocks_to_place[(x, y, z)] = (PLATFORM, NAMESPACE, base_name, properties or {})

def place_cmd(x, y, z, block_type, command, auto=True, tick_delay=0, conditional=False, facing=5):
    props = {"facing_direction": str(facing), "conditional_bit": "1" if conditional else "0"}
    blocks_to_place[(x, y, z)] = (PLATFORM, NAMESPACE, block_type, props)
    
    if block_type == "repeating_command_block":
        lp_mode = 1
    elif block_type == "chain_command_block":
        lp_mode = 2
    else:
        lp_mode = 0
    
    command_blocks_data.append({
        "x": x, "y": y, "z": z,
        "command": command, "auto": auto,
        "tick_delay": tick_delay, "conditional": conditional,
        "lp_mode": lp_mode,
    })

# ============================================================
# STRUCTURES
# ============================================================

def build_ground():
    for x in range(-35, 45):
        for z in range(-35, 25):
            place(x, 0, z, "bedrock")
            for y in range(1, 4):
                place(x, y, z, "stone")
            place(x, 4, z, "deepslate_tiles")
    for x in range(-30, 40):
        for z in range(-30, 20):
            if (x + z) % 8 == 0 or (x - z) % 8 == 0:
                place(x, 4, z, "polished_blackstone")

def build_camera():
    bx, by, bz = CAMERA_BASE
    for x in range(bx, bx+10):
        for y in range(by, by+10):
            for z in range(bz, bz+8):
                ex = (x==bx or x==bx+9)
                ey = (y==by or y==by+9)
                ez = (z==bz or z==bz+7)
                if ex or ey or ez:
                    place(x, y, z, "black_concrete")
                else:
                    place(x, y, z, "gray_concrete")
    lcx, lcy = bx+5, by+5
    for x in range(bx+1, bx+9):
        for y in range(by+1, by+9):
            dx, dy = x-lcx+0.5, y-lcy+0.5
            dist = math.sqrt(dx*dx+dy*dy)
            if dist < 2.0:
                place(x, y, bz, "diamond_block")
            elif dist < 3.0:
                place(x, y, bz, "stained_glass", {"color": "light_blue"})
            elif dist < 3.8:
                place(x, y, bz, "stained_glass", {"color": "cyan"})
            if 3.5 < dist < 4.2:
                place(x, y, bz, "iron_block")
    # Flash
    for dx in [3,4,5,6]:
        place(bx+dx, by+10, bz+2, "iron_block")
    for dx in [4,5]:
        place(bx+dx, by+11, bz+2, "sea_lantern")
        place(bx+dx, by+10, bz+2, "glowstone")
    # Viewfinder
    place(bx+4, by+10, bz+5, "black_concrete")
    place(bx+5, by+10, bz+5, "black_concrete")
    place(bx+5, by+11, bz+5, "stained_glass", {"color": "gray"})
    # Red accents
    for y in range(by+3, by+7):
        place(bx+9, y, bz+3, "red_concrete")
        place(bx+9, y, bz+4, "red_concrete")

def build_scanning_platform():
    px, py, pz = PLATFORM_CENTER
    for x in range(px-2, px+3):
        for z in range(pz-2, pz+3):
            place(x, py-1, z, "sea_lantern")
    for x in range(px-3, px+4):
        for z in range(pz-3, pz+4):
            if x==px-3 or x==px+3 or z==pz-3 or z==pz+3:
                place(x, py-1, z, "iron_block")
    for cx, cz in [(px-3,pz-3),(px+3,pz-3),(px-3,pz+3),(px+3,pz+3)]:
        for y in range(py, py+4):
            place(cx, y, cz, "quartz_block", {"chisel_type": "default", "pillar_axis": "y"})
        place(cx, py+4, cz, "sea_lantern")
    for cx, cz in [(px-2,pz-2),(px+2,pz-2),(px-2,pz+2),(px+2,pz+2)]:
        place(cx, py-1, cz, "diamond_block")
    place(px, py, pz-3, "quartz_block", {"chisel_type": "default", "pillar_axis": "y"})
    place(px, py+1, pz-3, "quartz_block", {"chisel_type": "default", "pillar_axis": "y"})
    # Arch
    for x in range(px-3, px+4):
        place(x, py+6, pz-2, "iron_block")
        place(x, py+6, pz+2, "iron_block")
    for z in range(pz-2, pz+3):
        place(px-3, py+6, z, "iron_block")
        place(px+3, py+6, z, "iron_block")
    for x in range(px-2, px+3):
        for z in range(pz-1, pz+2):
            place(x, py+6, z, "glowstone")

def build_display_wall():
    ox, oy, oz = DISPLAY_ORIGIN
    wall_w, wall_h = 12, 20
    for dz in range(-2, wall_w+2):
        for dy in range(-2, wall_h+2):
            place(ox, oy+dy, oz+dz, "black_concrete")
            place(ox+1, oy+dy, oz+dz, "black_concrete")
    for dz in range(-1, wall_w+1):
        for dy in range(-1, wall_h+1):
            if dz==-1 or dz==wall_w or dy==-1 or dy==wall_h:
                place(ox-1, oy+dy, oz+dz, "quartz_block", {"chisel_type": "default", "pillar_axis": "y"})
    for dz, dy in [(-1,-1),(-1,wall_h),(wall_w,-1),(wall_w,wall_h)]:
        place(ox-1, oy+dy, oz+dz, "gold_block")
    for dz in range(0, wall_w):
        place(ox-1, oy+wall_h+1, oz+dz, "iron_block")
        place(ox-2, oy+wall_h, oz+dz, "sea_lantern")
        place(ox-2, oy-1, oz+dz, "sea_lantern")
    for dz in range(wall_w):
        for dy in range(wall_h):
            az, ay = dz-2, dy-2
            if 0<=az<8 and 0<=ay<16:
                place(ox-1, oy+dy, oz+dz, "stained_glass", {"color": "black"})
            else:
                place(ox-1, oy+dy, oz+dz, "stained_glass", {"color": "gray"})
    for dz in range(-2, wall_w+2):
        place(ox-1, oy-2, oz+dz, "obsidian")
        place(ox, oy-2, oz+dz, "obsidian")
    for dy in range(-2, wall_h+3):
        place(ox-1, oy+dy, oz-2, "quartz_block", {"chisel_type": "default", "pillar_axis": "y"})
        place(ox-1, oy+dy, oz+wall_w+1, "quartz_block", {"chisel_type": "default", "pillar_axis": "y"})
        if dy % 3 == 0:
            place(ox-2, oy+dy, oz-2, "sea_lantern")
            place(ox-2, oy+dy, oz+wall_w+1, "sea_lantern")

def build_command_blocks():
    sx, sy, sz = -5, COMMAND_Y, 0
    cx = sx
    px, py, pz = PLATFORM_CENTER
    ox, oy, oz = DISPLAY_ORIGIN
    flag_x, flag_y, flag_z = sx+1, sy+1, sz

    # 0: Repeating - detect player on platform
    place_cmd(cx, sy, sz, "repeating_command_block",
        f"execute @p[x={px-2},y={py-2},z={pz-2},dx=4,dy=4,dz=4] ~~~ testforblock {flag_x} {flag_y} {flag_z} air",
        auto=True, tick_delay=0)
    cx += 1

    # 1: Set flag (conditional)
    place_cmd(cx, sy, sz, "chain_command_block",
        f"setblock {flag_x} {flag_y} {flag_z} stone", auto=True, tick_delay=0, conditional=True)
    cx += 1

    # 2-9: Animation
    for cmd, delay in [
        ('title @a title §l§c⚡ SCANNING ⚡', 5),
        (f'playsound note.pling @a {px} {py} {pz}', 10),
        ('title @a subtitle §7Analyzing player data...', 20),
        (f'particle minecraft:villager_happy {px} {py+1} {pz}', 10),
        (f'particle minecraft:totem_particle {px} {py+2} {pz}', 20),
        ('title @a title §l§a◆ COMPUTING ◆', 30),
        ('title @a subtitle §7Rebuilding avatar with blocks...', 10),
        (f'playsound random.levelup @a {px} {py} {pz}', 20),
    ]:
        place_cmd(cx, sy, sz, "chain_command_block", cmd, auto=True, tick_delay=delay)
        cx += 1

    # Avatar building
    count = 0
    for row_bot in range(16):
        arow = 15 - row_bot
        for col in range(8):
            cid = AVATAR[arow][col]
            if cid == 0:
                continue
            bname = COLOR_NAMES[cid]
            bx = ox - 1
            by = oy + row_bot + 2
            bz = oz + col + 2
            tick = 2 if count > 0 else 30
            place_cmd(cx, sy, sz, "chain_command_block",
                f"setblock {bx} {by} {bz} {bname}", auto=True, tick_delay=tick)
            cx += 1
            if count % 8 == 0:
                place_cmd(cx, sy, sz, "chain_command_block",
                    f"playsound note.hat @a {bx} {by} {bz}", auto=True, tick_delay=0)
                cx += 1
            count += 1

    # Completion
    for cmd, delay in [
        ('title @a title §l§b★ COMPLETE ★', 20),
        ('title @a subtitle §7Avatar successfully reconstructed!', 5),
        (f'playsound random.totem @a {px} {py} {pz}', 20),
        (f'particle minecraft:totem_particle {ox-2} {oy+12} {oz+6}', 10),
        (f'setblock {flag_x} {flag_y} {flag_z} air', 100),
    ]:
        place_cmd(cx, sy, sz, "chain_command_block", cmd, auto=True, tick_delay=delay)
        cx += 1

    # Reset display
    for row_bot in range(16):
        arow = 15 - row_bot
        for col in range(8):
            if AVATAR[arow][col] == 0:
                continue
            bx_d, by_d, bz_d = ox-1, oy+row_bot+2, oz+col+2
            place_cmd(cx, sy, sz, "chain_command_block",
                f"setblock {bx_d} {by_d} {bz_d} black_stained_glass", auto=True, tick_delay=0)
            cx += 1

    print(f"  Total command blocks: {cx - sx}")
    # Cover them
    for x in range(sx-1, cx+2):
        for z in range(sz-1, sz+2):
            place(x, sy-1, z, "bedrock")
            place(x, sy+2, z, "stone")
            if z != sz:
                place(x, sy, z, "stone")
                place(x, sy+1, z, "stone")

def build_decorations():
    for z in range(SPAWN_Z, PLATFORM_CENTER[2]-3):
        for x in range(-2, 3):
            place(x, 4, z, "quartz_block", {"chisel_type": "smooth", "pillar_axis": "y"})
    for x in range(3, DISPLAY_ORIGIN[0]-1):
        for z in range(-2, 3):
            place(x, 4, PLATFORM_CENTER[2]+z, "quartz_block", {"chisel_type": "smooth", "pillar_axis": "y"})
    for z in range(SPAWN_Z, PLATFORM_CENTER[2]-3, 5):
        for side_x in [-3, 3]:
            place(side_x, 5, z, "quartz_block", {"chisel_type": "default", "pillar_axis": "y"})
            place(side_x, 6, z, "quartz_block", {"chisel_type": "default", "pillar_axis": "y"})
            place(side_x, 7, z, "sea_lantern")

# ============================================================
# WORLD WRITING using amulet-core
# ============================================================

def create_level_dat():
    """Write level.dat manually (amulet doesn't create new worlds easily)."""
    root = nbt.CompoundTag({
        "BiomeOverride": nbt.StringTag(""),
        "CenterMapsToOrigin": nbt.ByteTag(0),
        "ConfirmedPlatformLockedContent": nbt.ByteTag(0),
        "Difficulty": nbt.IntTag(1),
        "FlatWorldLayers": nbt.StringTag('{"biome_id":1,"block_layers":[{"block_name":"minecraft:bedrock","count":1},{"block_name":"minecraft:stone","count":3},{"block_name":"minecraft:grass_block","count":1}],"encoding_version":6,"structure_options":null,"world_version":"version.post_1_18"}'),
        "ForceGameType": nbt.ByteTag(0),
        "GameType": nbt.IntTag(1),
        "Generator": nbt.IntTag(2),
        "InventoryVersion": nbt.StringTag("1.20.80"),
        "LANBroadcast": nbt.ByteTag(1),
        "LANBroadcastIntent": nbt.ByteTag(1),
        "LastPlayed": nbt.LongTag(0),
        "LevelName": nbt.StringTag(WORLD_NAME),
        "LimitedWorldOriginX": nbt.IntTag(0),
        "LimitedWorldOriginY": nbt.IntTag(32767),
        "LimitedWorldOriginZ": nbt.IntTag(0),
        "MinimumCompatibleClientVersion": nbt.ListTag([nbt.IntTag(1),nbt.IntTag(20),nbt.IntTag(80),nbt.IntTag(0),nbt.IntTag(0)]),
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
        "baseGameVersion": nbt.StringTag("1.20.80"),
        "bonusChestEnabled": nbt.ByteTag(0),
        "bonusChestSpawned": nbt.ByteTag(0),
        "cheatsEnabled": nbt.ByteTag(1),
        "commandblockoutput": nbt.ByteTag(0),
        "commandblocksenabled": nbt.ByteTag(1),
        "commandsEnabled": nbt.ByteTag(1),
        "currentTick": nbt.LongTag(0),
        "daylightCycle": nbt.IntTag(0),
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
        "educationFeaturesEnabled": nbt.ByteTag(0),
        "experimentalgameplay": nbt.ByteTag(0),
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
        "lastOpenedWithVersion": nbt.ListTag([nbt.IntTag(1),nbt.IntTag(20),nbt.IntTag(80),nbt.IntTag(0),nbt.IntTag(0)]),
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
            "attackmobs": nbt.ByteTag(1), "attackplayers": nbt.ByteTag(1),
            "build": nbt.ByteTag(1), "doorsandswitches": nbt.ByteTag(1),
            "flySpeed": nbt.FloatTag(0.05), "flying": nbt.ByteTag(0),
            "instabuild": nbt.ByteTag(0), "invulnerable": nbt.ByteTag(0),
            "lightning": nbt.ByteTag(0), "mayfly": nbt.ByteTag(1),
            "mine": nbt.ByteTag(1), "op": nbt.ByteTag(1),
            "opencontainers": nbt.ByteTag(1), "permissionsLevel": nbt.IntTag(1),
            "playerPermissionsLevel": nbt.IntTag(1), "teleport": nbt.ByteTag(1),
            "walkSpeed": nbt.FloatTag(0.1),
        }),
    })
    import struct
    named = nbt.NamedTag(root, "")
    nbt_data = named.to_nbt(compressed=False, little_endian=True)
    header = struct.pack('<II', 10, len(nbt_data))
    return header + nbt_data


def write_world_leveldb():
    """Write all chunk data to LevelDB with correct Bedrock format."""
    import struct
    from leveldb import LevelDB
    
    if os.path.exists(WORLD_DIR):
        shutil.rmtree(WORLD_DIR)
    os.makedirs(os.path.join(WORLD_DIR, "db"), exist_ok=True)
    
    # Write level.dat
    with open(os.path.join(WORLD_DIR, "level.dat"), "wb") as f:
        f.write(create_level_dat())
    with open(os.path.join(WORLD_DIR, "level.dat_old"), "wb") as f:
        f.write(create_level_dat())
    with open(os.path.join(WORLD_DIR, "levelname.txt"), "w") as f:
        f.write(WORLD_NAME)
    with open(os.path.join(WORLD_DIR, "world_behavior_packs.json"), "w") as f:
        f.write("[]")
    with open(os.path.join(WORLD_DIR, "world_resource_packs.json"), "w") as f:
        f.write("[]")
    # Empty but valid JPEG (actually just skip it - not required)
    
    # Group blocks by chunk
    chunks = {}
    for (bx, by, bz), block_data in blocks_to_place.items():
        cx = math.floor(bx / 16)
        cz = math.floor(bz / 16)
        if (cx, cz) not in chunks:
            chunks[(cx, cz)] = {}
        lx = bx - cx * 16
        lz = bz - cz * 16
        chunks[(cx, cz)][(lx, by, lz)] = block_data
    
    # Group command block entities by chunk
    cb_by_chunk = {}
    for cb in command_blocks_data:
        cx = math.floor(cb["x"] / 16)
        cz = math.floor(cb["z"] / 16)
        if (cx, cz) not in cb_by_chunk:
            cb_by_chunk[(cx, cz)] = []
        cb_by_chunk[(cx, cz)].append(cb)
    
    print(f"  Writing {len(chunks)} chunks...")
    
    db = LevelDB(os.path.join(WORLD_DIR, "db"), create_if_missing=True)
    
    for (cx, cz), chunk_blocks in chunks.items():
        key_prefix = struct.pack('<ii', cx, cz)
        
        # Chunk version: tag 0x2C (44) for Bedrock 1.16.100+, value 40 for 1.18+
        db.put(key_prefix + b'\x2c', b'\x28')
        
        # Data2D (tag 0x2D = 45): heightmap (256 x int16 LE) + biomes (256 bytes)
        # Compute per-column heightmap
        col_heights = {}
        for (lx, by, lz) in chunk_blocks:
            col = lx * 16 + lz
            col_heights[col] = max(col_heights.get(col, 0), by + 1)
        heightmap = bytearray()
        for xz in range(256):
            h = col_heights.get(xz, 0)
            heightmap.extend(struct.pack('<h', min(h, 32767)))  # signed int16
        biomes = bytearray(b'\x01' * 256)  # plains
        db.put(key_prefix + b'\x2d', bytes(heightmap + biomes))
        
        # FinalizedState (tag 0x36 = 54): value 2 = fully generated
        db.put(key_prefix + b'\x36', struct.pack('<i', 2))
        
        # Determine subchunk y range
        ys = [by for (_, by, _) in chunk_blocks]
        min_sy = min(ys) >> 4
        max_sy = max(ys) >> 4
        
        for sy in range(min_sy, max_sy + 1):
            write_subchunk(db, key_prefix, sy, cx, cz, chunk_blocks)
        
        # Block entities (tag 0x31 = 49)
        if (cx, cz) in cb_by_chunk:
            entity_nbt_data = bytearray()
            for cb in cb_by_chunk[(cx, cz)]:
                entity_nbt_data.extend(make_cb_nbt(cb))
            db.put(key_prefix + b'\x31', bytes(entity_nbt_data))
    
    db.close()
    print("  LevelDB written!")


def write_subchunk(db, key_prefix, sy, cx, cz, chunk_blocks):
    """Write a single subchunk (16x16x16) to LevelDB."""
    import struct
    
    # Collect blocks in this subchunk
    sc_blocks = {}
    palette_entries = [("minecraft:air", {})]
    palette_map = {("minecraft:air",): 0}
    
    for (lx, by, lz), (platform, ns, base_name, props) in chunk_blocks.items():
        if by >> 4 != sy:
            continue
        local_y = by & 0xF
        
        full_name = f"{ns}:{base_name}"
        # Create a hashable key for dedup
        props_key = tuple(sorted(props.items())) if props else ()
        pkey = (full_name,) + props_key
        
        if pkey not in palette_map:
            palette_map[pkey] = len(palette_entries)
            palette_entries.append((full_name, props))
        
        sc_blocks[(lx, local_y, lz)] = palette_map[pkey]
    
    if not sc_blocks:
        return
    
    palette_size = len(palette_entries)
    
    # Bits per block
    if palette_size <= 2: bits = 1
    elif palette_size <= 4: bits = 2
    elif palette_size <= 8: bits = 3
    elif palette_size <= 16: bits = 4
    elif palette_size <= 32: bits = 5
    elif palette_size <= 64: bits = 6
    elif palette_size <= 256: bits = 8
    else: bits = 16
    
    blocks_per_word = 32 // bits
    num_words = (4096 + blocks_per_word - 1) // blocks_per_word
    
    # Pack indices - XZY order (y fastest)
    words = []
    for wi in range(num_words):
        word = 0
        for si in range(blocks_per_word):
            bi = wi * blocks_per_word + si
            if bi >= 4096:
                break
            x = (bi >> 8) & 0xF
            z = (bi >> 4) & 0xF
            y = bi & 0xF
            idx = sc_blocks.get((x, y, z), 0)
            word |= (idx & ((1 << bits) - 1)) << (si * bits)
        words.append(word)
    
    # Build subchunk binary
    data = bytearray()
    data.append(8)  # version
    data.append(1)  # 1 layer
    data.append((bits << 1) | 1)  # persistent
    
    for w in words:
        data.extend(struct.pack('<I', w & 0xFFFFFFFF))
    
    data.extend(struct.pack('<i', palette_size))
    
    for name, props in palette_entries:
        states = nbt.CompoundTag()
        for k, v in props.items():
            if isinstance(v, int):
                states[k] = nbt.IntTag(v)
            elif isinstance(v, str):
                states[k] = nbt.StringTag(v)
            elif isinstance(v, bool):
                states[k] = nbt.ByteTag(1 if v else 0)
            else:
                states[k] = nbt.StringTag(str(v))
        
        tag = nbt.CompoundTag({
            "name": nbt.StringTag(name),
            "states": states,
            "version": nbt.IntTag(18100737),
        })
        data.extend(tag.to_nbt(compressed=False, little_endian=True))
    
    sc_key = key_prefix + b'\x2f' + struct.pack('b', sy)
    db.put(sc_key, bytes(data))


def make_cb_nbt(cb):
    """Create command block entity NBT."""
    tag = nbt.CompoundTag({
        "id": nbt.StringTag("CommandBlock"),
        "x": nbt.IntTag(cb["x"]),
        "y": nbt.IntTag(cb["y"]),
        "z": nbt.IntTag(cb["z"]),
        "Command": nbt.StringTag(cb["command"]),
        "CustomName": nbt.StringTag(""),
        "ExecuteOnFirstTick": nbt.ByteTag(1),
        "LPCommandMode": nbt.IntTag(cb["lp_mode"]),
        "LPCondionalMode": nbt.ByteTag(1 if cb.get("conditional") else 0),
        "LPRedstoneMode": nbt.ByteTag(0),
        "LastExecution": nbt.LongTag(0),
        "LastOutput": nbt.StringTag(""),
        "LastOutputParams": nbt.ListTag([]),
        "TickDelay": nbt.IntTag(cb.get("tick_delay", 0)),
        "TrackOutput": nbt.ByteTag(1),
        "Version": nbt.IntTag(25),
        "auto": nbt.ByteTag(1 if cb.get("auto") else 0),
        "conditionMet": nbt.ByteTag(0),
        "conditionalMode": nbt.ByteTag(1 if cb.get("conditional") else 0),
        "isMovable": nbt.ByteTag(1),
        "powered": nbt.ByteTag(0),
        "successCount": nbt.IntTag(0),
    })
    return tag.to_nbt(compressed=False, little_endian=True)


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 60)
    print("  Avatar Scanner World Generator v2")
    print("=" * 60)
    
    print("\nBuilding structures...")
    build_ground()
    print("  Ground done")
    build_camera()
    print("  Camera done")
    build_scanning_platform()
    print("  Platform done")
    build_display_wall()
    print("  Display wall done")
    build_command_blocks()
    print("  Command blocks done")
    build_decorations()
    print("  Decorations done")
    
    print(f"\n  Total blocks: {len(blocks_to_place)}")
    print(f"  Command block entities: {len(command_blocks_data)}")
    
    print("\nWriting world...")
    write_world_leveldb()
    
    # Package
    print(f"\nPackaging {MCWORLD_PATH}...")
    if os.path.exists(MCWORLD_PATH):
        os.remove(MCWORLD_PATH)
    with zipfile.ZipFile(MCWORLD_PATH, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(WORLD_DIR):
            for f in files:
                fp = os.path.join(root, f)
                arc = os.path.relpath(fp, WORLD_DIR)
                zf.write(fp, arc)
    
    sz = os.path.getsize(MCWORLD_PATH)
    print(f"\nDone! {MCWORLD_PATH} ({sz/1024:.1f} KB)")


if __name__ == "__main__":
    main()
