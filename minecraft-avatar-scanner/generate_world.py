#!/usr/bin/env python3
"""
Minecraft Bedrock Edition .mcworld Generator v3
Matches exact binary format from amulet-core reference output.
"""
import struct, os, shutil, zipfile, math
import amulet_nbt as nbt
from leveldb import LevelDB

WORLD_NAME = "Avatar Scanner - Extremely Hard Build"
WORLD_DIR = "/home/ubuntu/minecraft-avatar-scanner/world_final"
MCWORLD_PATH = "/home/ubuntu/minecraft-avatar-scanner/AvatarScanner.mcworld"
SPAWN_X, SPAWN_Y, SPAWN_Z = 0, 8, -20
PLATFORM_CENTER = (0, 5, -10)
CAMERA_BASE = (-5, 5, 2)
DISPLAY_ORIGIN = (14, 5, -12)
COMMAND_Y = 1
BLOCK_VERSION = 18087969  # 1.20.1.1

AVATAR = [
    [0,1,1,1,1,1,1,0],[1,1,1,1,1,1,1,1],[1,2,2,2,2,2,2,1],[2,3,4,2,2,4,3,2],
    [2,2,2,2,2,2,2,2],[2,2,8,8,8,8,2,2],[0,2,5,5,5,5,2,0],[0,2,5,5,5,5,2,0],
    [0,2,5,5,5,5,2,0],[0,2,5,5,5,5,2,0],[0,0,5,5,5,5,0,0],[0,0,6,6,6,6,0,0],
    [0,0,6,6,6,6,0,0],[0,0,6,0,0,6,0,0],[0,0,6,0,0,6,0,0],[0,0,7,0,0,7,0,0],
]
COLOR_NAMES = {1:"brown_concrete",2:"orange_concrete",3:"white_concrete",
    4:"light_blue_concrete",5:"cyan_concrete",6:"blue_concrete",7:"gray_concrete",8:"pink_concrete"}

# Block definitions: name -> (minecraft_name, {states})
BLOCKS = {
    "air": ("minecraft:air", {}),
    "bedrock": ("minecraft:bedrock", {}),
    "stone": ("minecraft:stone", {"stone_type": "stone"}),
    "grass_block": ("minecraft:grass_block", {}),
    "dirt": ("minecraft:dirt", {"dirt_type": "normal"}),
    "deepslate_tiles": ("minecraft:deepslate_tiles", {}),
    "polished_blackstone": ("minecraft:polished_blackstone", {}),
    "black_concrete": ("minecraft:concrete", {"color": "black"}),
    "white_concrete": ("minecraft:concrete", {"color": "white"}),
    "gray_concrete": ("minecraft:concrete", {"color": "gray"}),
    "brown_concrete": ("minecraft:concrete", {"color": "brown"}),
    "orange_concrete": ("minecraft:concrete", {"color": "orange"}),
    "cyan_concrete": ("minecraft:concrete", {"color": "cyan"}),
    "blue_concrete": ("minecraft:concrete", {"color": "blue"}),
    "light_blue_concrete": ("minecraft:concrete", {"color": "light_blue"}),
    "pink_concrete": ("minecraft:concrete", {"color": "pink"}),
    "red_concrete": ("minecraft:concrete", {"color": "red"}),
    "yellow_concrete": ("minecraft:concrete", {"color": "yellow"}),
    "quartz_block": ("minecraft:quartz_block", {"chisel_type": "default", "pillar_axis": "y"}),
    "smooth_quartz": ("minecraft:quartz_block", {"chisel_type": "smooth", "pillar_axis": "y"}),
    "iron_block": ("minecraft:iron_block", {}),
    "diamond_block": ("minecraft:diamond_block", {}),
    "gold_block": ("minecraft:gold_block", {}),
    "sea_lantern": ("minecraft:sea_lantern", {}),
    "glowstone": ("minecraft:glowstone", {}),
    "glass": ("minecraft:glass", {}),
    "stained_glass_black": ("minecraft:stained_glass", {"color": "black"}),
    "stained_glass_gray": ("minecraft:stained_glass", {"color": "gray"}),
    "stained_glass_light_blue": ("minecraft:stained_glass", {"color": "light_blue"}),
    "stained_glass_cyan": ("minecraft:stained_glass", {"color": "cyan"}),
    "obsidian": ("minecraft:obsidian", {}),
    "iron_bars": ("minecraft:iron_bars", {}),
}

placed = {}  # (x,y,z) -> block_key
cmd_entities = []  # command block NBT data

def place(x, y, z, bkey):
    placed[(x,y,z)] = bkey

def place_cmd(x, y, z, btype, command, auto=True, tick_delay=0, conditional=False, facing=5):
    bkey = f"_cb_{x}_{y}_{z}"
    BLOCKS[bkey] = (f"minecraft:{btype}", {
        "facing_direction": facing, "conditional_bit": 1 if conditional else 0
    })
    placed[(x,y,z)] = bkey
    lp = 1 if btype=="repeating_command_block" else (2 if btype=="chain_command_block" else 0)
    cmd_entities.append({"x":x,"y":y,"z":z,"command":command,"auto":auto,
        "tick_delay":tick_delay,"conditional":conditional,"lp_mode":lp})

# ---- STRUCTURES ----
def build_ground():
    for x in range(-35, 45):
        for z in range(-35, 25):
            place(x,0,z,"bedrock")
            for y in range(1,4): place(x,y,z,"stone")
            place(x,4,z,"deepslate_tiles")
    for x in range(-30,40):
        for z in range(-30,20):
            if (x+z)%8==0 or (x-z)%8==0: place(x,4,z,"polished_blackstone")

def build_camera():
    bx,by,bz = CAMERA_BASE
    for x in range(bx,bx+10):
        for y in range(by,by+10):
            for z in range(bz,bz+8):
                ex,ey,ez = x==bx or x==bx+9, y==by or y==by+9, z==bz or z==bz+7
                if ex or ey or ez: place(x,y,z,"black_concrete")
                else: place(x,y,z,"gray_concrete")
    lcx,lcy = bx+5,by+5
    for x in range(bx+1,bx+9):
        for y in range(by+1,by+9):
            dx,dy = x-lcx+0.5,y-lcy+0.5
            dist = math.sqrt(dx*dx+dy*dy)
            if dist<2: place(x,y,bz,"diamond_block")
            elif dist<3: place(x,y,bz,"stained_glass_light_blue")
            elif dist<3.8: place(x,y,bz,"stained_glass_cyan")
            if 3.5<dist<4.2: place(x,y,bz,"iron_block")
    for dx in [3,4,5,6]: place(bx+dx,by+10,bz+2,"iron_block")
    for dx in [4,5]:
        place(bx+dx,by+11,bz+2,"sea_lantern")
        place(bx+dx,by+10,bz+2,"glowstone")
    place(bx+4,by+10,bz+5,"black_concrete"); place(bx+5,by+10,bz+5,"black_concrete")
    place(bx+5,by+11,bz+5,"stained_glass_gray")
    for y in range(by+3,by+7):
        place(bx+9,y,bz+3,"red_concrete"); place(bx+9,y,bz+4,"red_concrete")

def build_platform():
    px,py,pz = PLATFORM_CENTER
    for x in range(px-2,px+3):
        for z in range(pz-2,pz+3): place(x,py-1,z,"sea_lantern")
    for x in range(px-3,px+4):
        for z in range(pz-3,pz+4):
            if x==px-3 or x==px+3 or z==pz-3 or z==pz+3: place(x,py-1,z,"iron_block")
    for cx,cz in [(px-3,pz-3),(px+3,pz-3),(px-3,pz+3),(px+3,pz+3)]:
        for y in range(py,py+4): place(cx,y,cz,"quartz_block")
        place(cx,py+4,cz,"sea_lantern")
    for cx,cz in [(px-2,pz-2),(px+2,pz-2),(px-2,pz+2),(px+2,pz+2)]:
        place(cx,py-1,cz,"diamond_block")
    for x in range(px-3,px+4):
        place(x,py+6,pz-2,"iron_block"); place(x,py+6,pz+2,"iron_block")
    for z in range(pz-2,pz+3):
        place(px-3,py+6,z,"iron_block"); place(px+3,py+6,z,"iron_block")
    for x in range(px-2,px+3):
        for z in range(pz-1,pz+2): place(x,py+6,z,"glowstone")

def build_display():
    ox,oy,oz = DISPLAY_ORIGIN
    ww,wh = 12,20
    for dz in range(-2,ww+2):
        for dy in range(-2,wh+2):
            place(ox,oy+dy,oz+dz,"black_concrete"); place(ox+1,oy+dy,oz+dz,"black_concrete")
    for dz in range(-1,ww+1):
        for dy in range(-1,wh+1):
            if dz==-1 or dz==ww or dy==-1 or dy==wh: place(ox-1,oy+dy,oz+dz,"quartz_block")
    for dz,dy in [(-1,-1),(-1,wh),(ww,-1),(ww,wh)]: place(ox-1,oy+dy,oz+dz,"gold_block")
    for dz in range(ww):
        place(ox-1,oy+wh+1,oz+dz,"iron_block")
        place(ox-2,oy+wh,oz+dz,"sea_lantern"); place(ox-2,oy-1,oz+dz,"sea_lantern")
    for dz in range(ww):
        for dy in range(wh):
            az,ay = dz-2,dy-2
            if 0<=az<8 and 0<=ay<16: place(ox-1,oy+dy,oz+dz,"stained_glass_black")
            else: place(ox-1,oy+dy,oz+dz,"stained_glass_gray")
    for dz in range(-2,ww+2): place(ox-1,oy-2,oz+dz,"obsidian"); place(ox,oy-2,oz+dz,"obsidian")
    for dy in range(-2,wh+3):
        place(ox-1,oy+dy,oz-2,"quartz_block"); place(ox-1,oy+dy,oz+ww+1,"quartz_block")
        if dy%3==0: place(ox-2,oy+dy,oz-2,"sea_lantern"); place(ox-2,oy+dy,oz+ww+1,"sea_lantern")

def build_cmds():
    sx,sy,sz = -5,COMMAND_Y,0
    cx = sx
    px,py,pz = PLATFORM_CENTER
    ox,oy,oz = DISPLAY_ORIGIN
    fx,fy,fz = sx+1,sy+1,sz

    place_cmd(cx,sy,sz,"repeating_command_block",
        f"execute @p[x={px-2},y={py-2},z={pz-2},dx=4,dy=4,dz=4] ~~~ testforblock {fx} {fy} {fz} air",
        auto=True); cx+=1
    place_cmd(cx,sy,sz,"chain_command_block",
        f"setblock {fx} {fy} {fz} stone",auto=True,conditional=True); cx+=1

    for cmd,delay in [
        ('title @a title §l§c⚡ SCANNING ⚡',5),
        (f'playsound note.pling @a {px} {py} {pz}',10),
        ('title @a subtitle §7Analyzing player data...',20),
        (f'particle minecraft:villager_happy {px} {py+1} {pz}',10),
        (f'particle minecraft:totem_particle {px} {py+2} {pz}',20),
        ('title @a title §l§a◆ COMPUTING ◆',30),
        ('title @a subtitle §7Rebuilding avatar with blocks...',10),
        (f'playsound random.levelup @a {px} {py} {pz}',20),
    ]:
        place_cmd(cx,sy,sz,"chain_command_block",cmd,auto=True,tick_delay=delay); cx+=1

    count=0
    for rb in range(16):
        ar = 15-rb
        for col in range(8):
            cid = AVATAR[ar][col]
            if cid==0: continue
            bx,by,bz = ox-1,oy+rb+2,oz+col+2
            tick = 2 if count>0 else 30
            place_cmd(cx,sy,sz,"chain_command_block",f"setblock {bx} {by} {bz} {COLOR_NAMES[cid]}",auto=True,tick_delay=tick); cx+=1
            if count%8==0:
                place_cmd(cx,sy,sz,"chain_command_block",f"playsound note.hat @a {bx} {by} {bz}",auto=True); cx+=1
            count+=1

    for cmd,delay in [
        ('title @a title §l§b★ COMPLETE ★',20),
        ('title @a subtitle §7Avatar successfully reconstructed!',5),
        (f'playsound random.totem @a {px} {py} {pz}',20),
        (f'particle minecraft:totem_particle {ox-2} {oy+12} {oz+6}',10),
        (f'setblock {fx} {fy} {fz} air',100),
    ]:
        place_cmd(cx,sy,sz,"chain_command_block",cmd,auto=True,tick_delay=delay); cx+=1

    for rb in range(16):
        ar = 15-rb
        for col in range(8):
            if AVATAR[ar][col]==0: continue
            place_cmd(cx,sy,sz,"chain_command_block",
                f"setblock {ox-1} {oy+rb+2} {oz+col+2} stained_glass color=black",auto=True); cx+=1

    print(f"  Command blocks: {cx-sx}")
    for x in range(sx-1,cx+2):
        for z in range(sz-1,sz+2):
            place(x,sy-1,z,"bedrock"); place(x,sy+2,z,"stone")
            if z!=sz: place(x,sy,z,"stone"); place(x,sy+1,z,"stone")

def build_paths():
    for z in range(SPAWN_Z,PLATFORM_CENTER[2]-3):
        for x in range(-2,3): place(x,4,z,"smooth_quartz")
    for x in range(3,DISPLAY_ORIGIN[0]-1):
        for z in range(-2,3): place(x,4,PLATFORM_CENTER[2]+z,"smooth_quartz")
    for z in range(SPAWN_Z,PLATFORM_CENTER[2]-3,5):
        for sx in [-3,3]:
            place(sx,5,z,"quartz_block"); place(sx,6,z,"quartz_block"); place(sx,7,z,"sea_lantern")

# ---- BINARY FORMAT (matching amulet-core output) ----

def make_palette_nbt(mc_name, states_dict):
    states = nbt.CompoundTag()
    for k,v in states_dict.items():
        if isinstance(v,int): states[k] = nbt.IntTag(v)
        elif isinstance(v,str): states[k] = nbt.StringTag(v)
        else: states[k] = nbt.StringTag(str(v))
    tag = nbt.CompoundTag({"name":nbt.StringTag(mc_name),"states":states,"version":nbt.IntTag(BLOCK_VERSION)})
    return tag.to_nbt(compressed=False, little_endian=True)

def make_subchunk_v9(y_index, block_indices, palette_list):
    palette_size = len(palette_list)
    if palette_size <= 1:
        # Single block optimization: 0 bits per block
        data = bytearray([9, 1, y_index & 0xFF, 0x00])  # version=9, layers=1, y_idx, bits=0
        data.extend(struct.pack('<i', max(palette_size, 1)))
        for name, states in (palette_list if palette_list else [("minecraft:air", {})]):
            data.extend(make_palette_nbt(name, states))
        return bytes(data)
    
    if palette_size <= 2: bits = 1
    elif palette_size <= 4: bits = 2
    elif palette_size <= 8: bits = 3
    elif palette_size <= 16: bits = 4
    elif palette_size <= 32: bits = 5
    elif palette_size <= 64: bits = 6
    elif palette_size <= 256: bits = 8
    else: bits = 16
    
    bpw = 32 // bits
    nw = (4096 + bpw - 1) // bpw
    
    words = []
    for wi in range(nw):
        word = 0
        for si in range(bpw):
            bi = wi * bpw + si
            if bi >= 4096: break
            x = (bi >> 8) & 0xF
            z = (bi >> 4) & 0xF
            y = bi & 0xF
            idx = block_indices.get((x,y,z), 0)
            word |= (idx & ((1<<bits)-1)) << (si*bits)
        words.append(word)
    
    data = bytearray()
    data.append(9)  # version
    data.append(1)  # 1 layer
    data.append(y_index & 0xFF)  # y index
    data.append(bits << 1)  # bits_per_block, persistent=0 (matching amulet)
    for w in words: data.extend(struct.pack('<I', w & 0xFFFFFFFF))
    data.extend(struct.pack('<i', palette_size))
    for name, states in palette_list:
        data.extend(make_palette_nbt(name, states))
    return bytes(data)

def make_data3d():
    """541 bytes of 3D biome data (all plains)."""
    # Based on amulet output: 541 zero bytes works for plains biome
    return b'\x00' * 541

def make_cb_entity(cb):
    tag = nbt.CompoundTag({
        "id": nbt.StringTag("CommandBlock"),
        "x": nbt.IntTag(cb["x"]), "y": nbt.IntTag(cb["y"]), "z": nbt.IntTag(cb["z"]),
        "Command": nbt.StringTag(cb["command"]),
        "CustomName": nbt.StringTag(""),
        "ExecuteOnFirstTick": nbt.ByteTag(1),
        "LPCommandMode": nbt.IntTag(cb["lp_mode"]),
        "LPCondionalMode": nbt.ByteTag(1 if cb.get("conditional") else 0),
        "LPRedstoneMode": nbt.ByteTag(0),
        "LastExecution": nbt.LongTag(0),
        "LastOutput": nbt.StringTag(""),
        "LastOutputParams": nbt.ListTag([]),
        "TickDelay": nbt.IntTag(cb.get("tick_delay",0)),
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

def make_level_dat():
    root = nbt.CompoundTag({
        "StorageVersion": nbt.IntTag(10),
        "lastOpenedWithVersion": nbt.ListTag([nbt.IntTag(1),nbt.IntTag(20),nbt.IntTag(0),nbt.IntTag(0),nbt.IntTag(0)]),
        "Generator": nbt.IntTag(2),
        "LastPlayed": nbt.LongTag(0),
        "LevelName": nbt.StringTag(WORLD_NAME),
        "worldStartCount": nbt.LongTag(0),
        "GameType": nbt.IntTag(1),
        "Difficulty": nbt.IntTag(1),
        "SpawnX": nbt.IntTag(SPAWN_X),
        "SpawnY": nbt.IntTag(SPAWN_Y),
        "SpawnZ": nbt.IntTag(SPAWN_Z),
        "RandomSeed": nbt.LongTag(12345),
        "Time": nbt.LongTag(6000),
        "commandblockoutput": nbt.ByteTag(0),
        "commandblocksenabled": nbt.ByteTag(1),
        "commandsEnabled": nbt.ByteTag(1),
        "cheatsEnabled": nbt.ByteTag(1),
        "dodaylightcycle": nbt.ByteTag(0),
        "domobspawning": nbt.ByteTag(0),
        "doweathercycle": nbt.ByteTag(0),
        "dofiretick": nbt.ByteTag(0),
        "falldamage": nbt.ByteTag(0),
        "firedamage": nbt.ByteTag(0),
        "drowningdamage": nbt.ByteTag(0),
        "keepinventory": nbt.ByteTag(1),
        "mobgriefing": nbt.ByteTag(0),
        "showcoordinates": nbt.ByteTag(1),
        "maxcommandchainlength": nbt.IntTag(65535),
        "sendcommandfeedback": nbt.ByteTag(0),
        "pvp": nbt.ByteTag(0),
        "tntexplodes": nbt.ByteTag(0),
        "ForceGameType": nbt.ByteTag(0),
        "hasBeenLoadedInCreative": nbt.ByteTag(1),
        "immutableWorld": nbt.ByteTag(0),
        "LANBroadcast": nbt.ByteTag(1),
        "MultiplayerGame": nbt.ByteTag(1),
        "Platform": nbt.IntTag(2),
        "NetworkVersion": nbt.IntTag(671),
        "WorldVersion": nbt.IntTag(1),
        "baseGameVersion": nbt.StringTag("1.20.0"),
        "InventoryVersion": nbt.StringTag("1.20.0"),
        "MinimumCompatibleClientVersion": nbt.ListTag([nbt.IntTag(1),nbt.IntTag(20),nbt.IntTag(0),nbt.IntTag(0),nbt.IntTag(0)]),
        "spawnradius": nbt.IntTag(0),
        "abilities": nbt.CompoundTag({
            "mayfly": nbt.ByteTag(1), "flying": nbt.ByteTag(0),
            "flySpeed": nbt.FloatTag(0.05), "walkSpeed": nbt.FloatTag(0.1),
            "build": nbt.ByteTag(1), "mine": nbt.ByteTag(1),
            "doorsandswitches": nbt.ByteTag(1), "opencontainers": nbt.ByteTag(1),
            "attackplayers": nbt.ByteTag(1), "attackmobs": nbt.ByteTag(1),
            "op": nbt.ByteTag(1), "teleport": nbt.ByteTag(1),
            "invulnerable": nbt.ByteTag(0), "instabuild": nbt.ByteTag(0),
            "lightning": nbt.ByteTag(0),
            "permissionsLevel": nbt.IntTag(1),
            "playerPermissionsLevel": nbt.IntTag(1),
        }),
    })
    named = nbt.NamedTag(root, "")
    nbt_data = named.to_nbt(compressed=False, little_endian=True)
    return struct.pack('<II', 10, len(nbt_data)) + nbt_data

# ---- WORLD GENERATION ----

def generate():
    print("Building structures...")
    build_ground(); print("  Ground")
    build_camera(); print("  Camera")
    build_platform(); print("  Platform")
    build_display(); print("  Display wall")
    build_cmds(); print("  Commands")
    build_paths(); print("  Paths")
    print(f"  Total blocks: {len(placed)}, Cmd entities: {len(cmd_entities)}")

    # Group by chunk
    chunks = {}
    for (bx,by,bz),bkey in placed.items():
        cx,cz = math.floor(bx/16), math.floor(bz/16)
        chunks.setdefault((cx,cz), {})[(bx-cx*16, by, bz-cz*16)] = bkey
    
    cb_chunks = {}
    for cb in cmd_entities:
        cx,cz = math.floor(cb["x"]/16), math.floor(cb["z"]/16)
        cb_chunks.setdefault((cx,cz), []).append(cb)

    # Setup world dir
    if os.path.exists(WORLD_DIR): shutil.rmtree(WORLD_DIR)
    os.makedirs(os.path.join(WORLD_DIR,"db"))
    
    with open(os.path.join(WORLD_DIR,"level.dat"),"wb") as f: f.write(make_level_dat())
    with open(os.path.join(WORLD_DIR,"level.dat_old"),"wb") as f: f.write(make_level_dat())
    with open(os.path.join(WORLD_DIR,"levelname.txt"),"w") as f: f.write(WORLD_NAME)
    with open(os.path.join(WORLD_DIR,"world_behavior_packs.json"),"w") as f: f.write("[]")
    with open(os.path.join(WORLD_DIR,"world_resource_packs.json"),"w") as f: f.write("[]")

    print(f"\nWriting {len(chunks)} chunks to LevelDB...")
    db = LevelDB(os.path.join(WORLD_DIR,"db"), create_if_missing=True)
    
    for (cx,cz), cblocks in chunks.items():
        kp = struct.pack('<ii', cx, cz)
        
        # Version (tag 0x2C=44), value 40
        db.put(kp + b'\x2c', b'\x28')
        # Data3D (tag 0x2B=43)
        db.put(kp + b'\x2b', make_data3d())
        # FinalizedState (tag 0x36=54), value 2
        db.put(kp + b'\x36', struct.pack('<i', 2))
        
        # SubChunks
        ys = [by for (_,by,_) in cblocks]
        for sy in range(min(ys)>>4, (max(ys)>>4)+1):
            palette = [("minecraft:air", {})]
            pmap = {("minecraft:air",()): 0}
            indices = {}
            
            for (lx,by,lz),bkey in cblocks.items():
                if by>>4 != sy: continue
                if bkey not in BLOCKS: continue
                mc_name, states = BLOCKS[bkey]
                sk = (mc_name, tuple(sorted(states.items())))
                if sk not in pmap:
                    pmap[sk] = len(palette)
                    palette.append((mc_name, states))
                indices[(lx, by&0xF, lz)] = pmap[sk]
            
            if not indices: continue
            db.put(kp + b'\x2f' + struct.pack('b', sy),
                   make_subchunk_v9(sy, indices, palette))
        
        # Block entities (tag 0x31=49)
        if (cx,cz) in cb_chunks:
            edata = bytearray()
            for cb in cb_chunks[(cx,cz)]: edata.extend(make_cb_entity(cb))
            db.put(kp + b'\x31', bytes(edata))
    
    # Compact DB to flush WAL log to SST (.ldb) files - required for Minecraft to read
    db.compact()
    db.close()
    print("  LevelDB compacted and closed!")
    
    # Package .mcworld
    if os.path.exists(MCWORLD_PATH): os.remove(MCWORLD_PATH)
    with zipfile.ZipFile(MCWORLD_PATH,'w',zipfile.ZIP_DEFLATED) as zf:
        for root,_,files in os.walk(WORLD_DIR):
            for f in files:
                fp = os.path.join(root,f)
                zf.write(fp, os.path.relpath(fp, WORLD_DIR))
    
    sz = os.path.getsize(MCWORLD_PATH)
    print(f"\nDone! {MCWORLD_PATH} ({sz/1024:.1f} KB)")

if __name__ == "__main__":
    print("="*50)
    print("  Avatar Scanner World Generator v3")
    print("="*50)
    generate()
