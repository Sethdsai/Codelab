// Build a Bedrock .mcworld file from scratch with a small airport + airplane.
// Uses bedrock-provider (PrismarineJS) to write LevelDB chunks and
// prismarine-nbt to produce a valid level.dat.
//
// Output: ./Airport.mcworld
//
// Run: node build_airport.js

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');
const { LevelDB } = require('leveldb-zlib');
const { WorldProvider } = require('bedrock-provider');
const { KeyBuilder } = require('bedrock-provider/js/disk/databaseKeys');
const BinaryStream = require('@jsprismarine/jsbinaryutils').default || require('@jsprismarine/jsbinaryutils');

// Monkey-patch prismarine-chunk's byte-stream writeUInt8 to accept signed
// bytes (-128..255) — Bedrock subchunk y uses signed int8 for negative CYs.
const CStream = require('prismarine-chunk/src/bedrock/common/Stream');
const origWrite = CStream.prototype.writeUInt8;
CStream.prototype.writeUInt8 = function (v) {
  return origWrite.call(this, v < 0 ? v & 0xff : v);
};

const registry = require('prismarine-registry')('bedrock_1.18.0');
const Block = require('prismarine-block')(registry);
const ChunkColumn = require('prismarine-chunk')(registry);
const nbt = require('prismarine-nbt');
const { Vec3 } = require('vec3');

// ---------- Block palette -----------------------------------------------
const byName = n => {
  const b = registry.blocksByName[n];
  if (!b) throw new Error(`Unknown block: ${n}`);
  return b.defaultState;
};

const AIR       = byName('air');
const BEDROCK   = byName('bedrock');
const STONE     = byName('stone');
const DIRT      = byName('dirt');
const GRASS     = byName('grass');
const QUARTZ    = byName('quartz_block');
const IRON      = byName('iron_block');
const GLASS     = byName('glass');
const GLOWSTONE = byName('glowstone');
const STAINED_GLASS_BLUE = (() => {
  // stained_glass range: colors 0..15; we want light_blue (color=3)
  const bl = registry.blocksByName.stained_glass;
  return bl.minStateId + 3;
})();

// Concrete colors come from a single 'concrete' block with state offset per color.
// Order (from earlier inspection): white, orange, magenta, light_blue, yellow,
// lime, pink, gray, silver(light_gray), cyan, purple, blue, brown, green, red, black.
const concreteBase = registry.blocksByName.concrete.minStateId;
const C = {
  white:     concreteBase + 0,
  orange:    concreteBase + 1,
  magenta:   concreteBase + 2,
  lightBlue: concreteBase + 3,
  yellow:    concreteBase + 4,
  lime:      concreteBase + 5,
  pink:      concreteBase + 6,
  gray:      concreteBase + 7,
  silver:    concreteBase + 8,
  cyan:      concreteBase + 9,
  purple:    concreteBase + 10,
  blue:      concreteBase + 11,
  brown:     concreteBase + 12,
  green:     concreteBase + 13,
  red:       concreteBase + 14,
  black:     concreteBase + 15,
};

// ---------- World dictionary --------------------------------------------
// We stage all edits in a Map keyed by "x,y,z" then flush to chunks.
const edits = new Map();
const key = (x, y, z) => `${x}|${y}|${z}`;

function setBlock(x, y, z, state) {
  edits.set(key(x, y, z), state);
}

function fill(x1, y1, z1, x2, y2, z2, state) {
  const xmin = Math.min(x1, x2), xmax = Math.max(x1, x2);
  const ymin = Math.min(y1, y2), ymax = Math.max(y1, y2);
  const zmin = Math.min(z1, z2), zmax = Math.max(z1, z2);
  for (let x = xmin; x <= xmax; x++)
    for (let y = ymin; y <= ymax; y++)
      for (let z = zmin; z <= zmax; z++)
        setBlock(x, y, z, state);
}

function fillHollow(x1, y1, z1, x2, y2, z2, wall, inside = AIR) {
  const xmin = Math.min(x1, x2), xmax = Math.max(x1, x2);
  const ymin = Math.min(y1, y2), ymax = Math.max(y1, y2);
  const zmin = Math.min(z1, z2), zmax = Math.max(z1, z2);
  for (let x = xmin; x <= xmax; x++) {
    for (let y = ymin; y <= ymax; y++) {
      for (let z = zmin; z <= zmax; z++) {
        const edge = x === xmin || x === xmax || y === ymin || y === ymax ||
                     z === zmin || z === zmax;
        setBlock(x, y, z, edge ? wall : inside);
      }
    }
  }
}

// ---------- World layout -------------------------------------------------
// Build a 5x5 chunk area centred on (0,0). Area: x=-40..39, z=-40..39.
const CHUNK_MIN_X = -3, CHUNK_MAX_X = 2;
const CHUNK_MIN_Z = -3, CHUNK_MAX_Z = 2;
const X_MIN = CHUNK_MIN_X * 16,      X_MAX = (CHUNK_MAX_X + 1) * 16 - 1;
const Z_MIN = CHUNK_MIN_Z * 16,      Z_MAX = (CHUNK_MAX_Z + 1) * 16 - 1;

// Flat world layering: bedrock at y=-64, stone -63..-62, dirt -61..-60, grass -59.
const Y_BEDROCK = -64;
const Y_STONE_T = -62;
const Y_DIRT_T  = -60;
const Y_GRASS   = -59;
const Y_GROUND  = Y_GRASS + 1;   // first y-level of air above grass

// --- Ground ---
fill(X_MIN, Y_BEDROCK, Z_MIN, X_MAX, Y_BEDROCK, Z_MAX, BEDROCK);
fill(X_MIN, Y_BEDROCK + 1, Z_MIN, X_MAX, Y_STONE_T, Z_MAX, STONE);
fill(X_MIN, Y_STONE_T + 1, Z_MIN, X_MAX, Y_DIRT_T, Z_MAX, DIRT);
fill(X_MIN, Y_GRASS,    Z_MIN, X_MAX, Y_GRASS,    Z_MAX, GRASS);

// --- Runway (gray concrete) with centerline stripes ---
// Runway runs west-east along x, centered at z=0. Length 48, width 8.
const RUNWAY_X1 = -24, RUNWAY_X2 = 23;
const RUNWAY_Z1 = -4,  RUNWAY_Z2 = 3;
fill(RUNWAY_X1, Y_GRASS, RUNWAY_Z1, RUNWAY_X2, Y_GRASS, RUNWAY_Z2, C.gray);
// Threshold markings (white) at both ends
fill(RUNWAY_X1, Y_GRASS, RUNWAY_Z1 + 1, RUNWAY_X1 + 1, Y_GRASS, RUNWAY_Z2 - 1, C.white);
fill(RUNWAY_X2 - 1, Y_GRASS, RUNWAY_Z1 + 1, RUNWAY_X2, Y_GRASS, RUNWAY_Z2 - 1, C.white);
// Centerline dashes
for (let x = RUNWAY_X1 + 4; x <= RUNWAY_X2 - 4; x += 4) {
  fill(x, Y_GRASS, 0, x + 1, Y_GRASS, 0, C.white);
}

// --- Taxiway from runway to apron (yellow edged) ---
// A short strip running north (negative z) from runway to apron at z=-12.
fill(-6, Y_GRASS, -11, -3, Y_GRASS, -5, C.silver);
fill(-6, Y_GRASS, -11, -6, Y_GRASS, -5, C.yellow);
fill(-3, Y_GRASS, -11, -3, Y_GRASS, -5, C.yellow);

// --- Apron (parking area) north of runway ---
fill(-14, Y_GRASS, -20, 5, Y_GRASS, -12, C.silver);

// --- Terminal building ---
// Footprint: 14 wide (x) x 7 deep (z) x 5 tall, at z ~ -28..-22
const T_X1 = -10, T_X2 = 3;
const T_Z1 = -28, T_Z2 = -22;
const T_Y1 = Y_GROUND, T_Y2 = Y_GROUND + 4;
fillHollow(T_X1, T_Y1, T_Z1, T_X2, T_Y2, T_Z2, QUARTZ);
// Roof (solid quartz)
fill(T_X1, T_Y2, T_Z1, T_X2, T_Y2, T_Z2, QUARTZ);
// Floor
fill(T_X1, T_Y1 - 1, T_Z1, T_X2, T_Y1 - 1, T_Z2, C.white);
// Glass windows along front (south-facing, z = T_Z2) and back
for (let x = T_X1 + 1; x <= T_X2 - 1; x++) {
  setBlock(x, T_Y1 + 1, T_Z2, GLASS);
  setBlock(x, T_Y1 + 2, T_Z2, GLASS);
  setBlock(x, T_Y1 + 1, T_Z1, GLASS);
  setBlock(x, T_Y1 + 2, T_Z1, GLASS);
}
// Doors (open space) on the south side
setBlock(T_X1 + 3, T_Y1, T_Z2, AIR);
setBlock(T_X1 + 3, T_Y1 + 1, T_Z2, AIR);
setBlock(T_X1 + 4, T_Y1, T_Z2, AIR);
setBlock(T_X1 + 4, T_Y1 + 1, T_Z2, AIR);
// Interior lights
for (let x = T_X1 + 2; x <= T_X2 - 2; x += 3) {
  for (let z = T_Z1 + 2; z <= T_Z2 - 2; z += 3) {
    setBlock(x, T_Y2 - 1, z, GLOWSTONE);
  }
}
// "TERMINAL" sign strip in blue concrete
fill(T_X1 + 1, T_Y2 + 1, T_Z2, T_X2 - 1, T_Y2 + 1, T_Z2, C.blue);

// --- Control tower ---
// 5x5 base, 12 tall, glass cab on top.
const TW_X = -20, TW_Z = -24;
const TW_BOT = Y_GROUND, TW_TOP = Y_GROUND + 11;
// Shaft (hollow quartz, 5x5 outer)
for (let y = TW_BOT; y <= TW_BOT + 8; y++) {
  for (let x = TW_X; x < TW_X + 5; x++) {
    for (let z = TW_Z; z < TW_Z + 5; z++) {
      const edge = x === TW_X || x === TW_X + 4 || z === TW_Z || z === TW_Z + 4;
      setBlock(x, y, z, edge ? QUARTZ : AIR);
    }
  }
}
// Cab base (slightly wider feel): solid quartz floor
fill(TW_X - 1, TW_BOT + 9, TW_Z - 1, TW_X + 5, TW_BOT + 9, TW_Z + 5, QUARTZ);
// Cab walls of glass, 2 blocks tall
for (let y = TW_BOT + 10; y <= TW_TOP; y++) {
  for (let x = TW_X - 1; x <= TW_X + 5; x++) {
    for (let z = TW_Z - 1; z <= TW_Z + 5; z++) {
      const edge = x === TW_X - 1 || x === TW_X + 5 || z === TW_Z - 1 || z === TW_Z + 5;
      if (edge) setBlock(x, y, z, GLASS);
    }
  }
}
// Cab roof (quartz)
fill(TW_X - 1, TW_TOP + 1, TW_Z - 1, TW_X + 5, TW_TOP + 1, TW_Z + 5, QUARTZ);
// Beacon on top
setBlock(TW_X + 2, TW_TOP + 2, TW_Z + 2, GLOWSTONE);

// --- Airplane parked on the apron, nose pointing +x ---
// Reference origin (tail) at (ax, ay, az); length along +x.
const ax = -8, az = -15;
const ay = Y_GROUND; // sits on the apron (y = ay)
const ayFus = ay + 1; // fuselage center height

// Fuselage (13 long x 1 wide x 2 tall), iron_block body with white nose.
fill(ax,     ayFus, az,     ax + 12, ayFus, az,     IRON);
fill(ax,     ayFus + 1, az, ax + 11, ayFus + 1, az, IRON);
// Rounded nose
setBlock(ax + 12, ayFus + 1, az, C.white);
setBlock(ax + 13, ayFus,     az, C.white);
// Cockpit windows (blue stained glass on top)
setBlock(ax + 9,  ayFus + 1, az, STAINED_GLASS_BLUE);
setBlock(ax + 10, ayFus + 1, az, STAINED_GLASS_BLUE);
// Wings (light_blue concrete) — span across z, at fuselage-bottom height
fill(ax + 4, ayFus, az - 4, ax + 6, ayFus, az + 4, C.lightBlue);
// Wing tips (red) for visibility
setBlock(ax + 5, ayFus, az - 4, C.red);
setBlock(ax + 5, ayFus, az + 4, C.red);
// Horizontal stabilizers at the tail
fill(ax, ayFus, az - 2, ax + 1, ayFus, az + 2, C.lightBlue);
// Vertical stabilizer (tail fin)
fill(ax, ayFus + 2, az, ax, ayFus + 3, az, C.lightBlue);
setBlock(ax, ayFus + 3, az, C.red);
// Landing gear (iron blocks)
setBlock(ax + 2, ay, az, IRON);
setBlock(ax + 10, ay, az, IRON);
setBlock(ax + 5, ay, az - 4, IRON);
setBlock(ax + 5, ay, az + 4, IRON);
// Propeller (crossed glow for fun) in front of nose
setBlock(ax + 14, ayFus,     az,     GLOWSTONE);
setBlock(ax + 14, ayFus + 1, az,     GLOWSTONE);
setBlock(ax + 14, ayFus,     az - 1, GLOWSTONE);
setBlock(ax + 14, ayFus,     az + 1, GLOWSTONE);

// --- Windsock pole near runway end ---
fill(22, Y_GROUND, -8, 22, Y_GROUND + 4, -8, IRON);
setBlock(22, Y_GROUND + 5, -8, C.orange);
setBlock(22, Y_GROUND + 5, -7, C.orange);
setBlock(22, Y_GROUND + 5, -6, C.white);

// --- Runway edge lights (glowstone every 4 blocks) ---
for (let x = RUNWAY_X1; x <= RUNWAY_X2; x += 4) {
  setBlock(x, Y_GROUND, RUNWAY_Z1 - 1, GLOWSTONE);
  setBlock(x, Y_GROUND, RUNWAY_Z2 + 1, GLOWSTONE);
}

// --- Apron perimeter markings (yellow) ---
fill(-14, Y_GRASS, -20, 5, Y_GRASS, -20, C.yellow);
fill(-14, Y_GRASS, -12, 5, Y_GRASS, -12, C.yellow);
fill(-14, Y_GRASS, -20, -14, Y_GRASS, -12, C.yellow);
fill(5, Y_GRASS, -20, 5, Y_GRASS, -12, C.yellow);

console.log(`Staged ${edits.size} block edits.`);

// ---------- Flush edits to chunks ---------------------------------------
// bedrock-provider 0.3.7's WorldProvider.save has a bug where it calls
// column.getSection(y) with a raw int (the method expects `{y}`), so it always
// returns undefined and no subchunks get written. We write chunks manually.
async function saveColumn(db, column, dim = 0) {
  // 1. version key (single byte)
  const verKey = KeyBuilder.buildVersionKey(column.x, column.z, dim);
  await db.put(verKey, Buffer.from([column.chunkVersion]));

  // 2. subchunks via section.encode(0 = LocalPersistence)
  for (let cy = column.minCY; cy < column.maxCY; cy++) {
    const sec = column.getSectionAtIndex(cy);
    if (!sec) continue;
    const key = KeyBuilder.buildChunkKey(column.x, cy, column.z, dim);
    const buf = await sec.encode(0);
    await db.put(key, buf);
  }

  // 3. heightmap + 3D biomes (Data3D) — use prismarine-chunk's own Stream
  const hbKey = KeyBuilder.buildHeightmapAnd3DBiomeKey(column.x, column.z, dim);
  const stream = new CStream();
  column.writeHeightMap(stream);
  column.writeBiomes(stream);
  await db.put(hbKey, stream.getBuffer());

  // 4. Finalized state = 2 (populated) so Bedrock treats the chunk as generated
  const fsKey = KeyBuilder.buildFinalizedState(column.x, column.z, dim);
  const fsBuf = Buffer.alloc(4);
  fsBuf.writeInt32LE(2, 0);
  await db.put(fsKey, fsBuf);
}

async function writeWorld(worldDir) {
  const dbDir = path.join(worldDir, 'db');
  fs.mkdirSync(dbDir, { recursive: true });
  const db = new LevelDB(dbDir, { createIfMissing: true });
  await db.open();

  // Group edits by chunk
  const chunks = new Map();
  for (const [k, state] of edits) {
    const [xs, ys, zs] = k.split('|').map(Number);
    const cx = Math.floor(xs / 16);
    const cz = Math.floor(zs / 16);
    const ckey = `${cx},${cz}`;
    if (!chunks.has(ckey)) chunks.set(ckey, []);
    chunks.get(ckey).push([xs, ys, zs, state]);
  }

  console.log(`Writing ${chunks.size} chunks ...`);
  let i = 0;
  for (const [ckey, ops] of chunks) {
    const [cx, cz] = ckey.split(',').map(Number);
    const cc = new ChunkColumn({ x: cx, z: cz });
    // Set biome to plains (id 1) across the whole chunk, all y
    for (let x = 0; x < 16; x++) {
      for (let z = 0; z < 16; z++) {
        cc.setBiomeId(new Vec3(x, 0, z), 1);
      }
    }
    for (const [wx, wy, wz, state] of ops) {
      const lx = ((wx % 16) + 16) % 16;
      const lz = ((wz % 16) + 16) % 16;
      const block = Block.fromStateId(state, 0);
      cc.setBlock({ x: lx, y: wy, z: lz }, block);
    }
    await saveColumn(db, cc, 0);
    i++;
    if (i % 5 === 0) console.log(`  wrote ${i}/${chunks.size}`);
  }
  await db.close();
  console.log('LevelDB written.');
}

// ---------- level.dat ---------------------------------------------------
function buildLevelDat(levelName) {
  const now = BigInt(Math.floor(Date.now() / 1000));
  const flatGenerator = JSON.stringify({
    biome_id: 1,
    block_layers: [
      { block_name: 'minecraft:bedrock', count: 1 },
      { block_name: 'minecraft:stone', count: 2 },
      { block_name: 'minecraft:dirt', count: 2 },
      { block_name: 'minecraft:grass', count: 1 }
    ],
    encoding_version: 6,
    structure_options: null,
    world_version: 'version.post_1_18'
  });

  const tag = {
    type: 'compound',
    name: '',
    value: {
      BiomeOverride:                { type: 'string', value: '' },
      CenterMapsToOrigin:           { type: 'byte',  value: 0 },
      ConfirmedPlatformLockedContent:{ type: 'byte', value: 0 },
      Difficulty:                   { type: 'int',   value: 2 },
      FlatWorldLayers:              { type: 'string',value: flatGenerator },
      ForceGameType:                { type: 'byte',  value: 0 },
      GameType:                     { type: 'int',   value: 1 }, // creative
      Generator:                    { type: 'int',   value: 2 }, // flat
      InventoryVersion:             { type: 'string',value: '1.18.0' },
      LANBroadcast:                 { type: 'byte',  value: 1 },
      LANBroadcastIntent:           { type: 'byte',  value: 1 },
      LastPlayed:                   { type: 'long',  value: [Number(now >> 32n), Number(now & 0xffffffffn)] },
      LevelName:                    { type: 'string',value: levelName },
      LimitedWorldOriginX:          { type: 'int',   value: 0 },
      LimitedWorldOriginY:          { type: 'int',   value: 32767 },
      LimitedWorldOriginZ:          { type: 'int',   value: 0 },
      MinimumCompatibleClientVersion:{ type: 'list',
        value: { type: 'int', value: [1, 18, 0, 0, 0] } },
      MultiplayerGame:              { type: 'byte',  value: 1 },
      MultiplayerGameIntent:        { type: 'byte',  value: 1 },
      NetherScale:                  { type: 'int',   value: 8 },
      NetworkVersion:               { type: 'int',   value: 475 },
      Platform:                     { type: 'int',   value: 2 },
      PlatformBroadcastIntent:      { type: 'int',   value: 3 },
      RandomSeed:                   { type: 'long',  value: [0, 42] },
      SpawnV1Villagers:             { type: 'byte',  value: 0 },
      SpawnX:                       { type: 'int',   value: 0 },
      SpawnY:                       { type: 'int',   value: 32767 },
      SpawnZ:                       { type: 'int',   value: 0 },
      StorageVersion:               { type: 'int',   value: 9 },
      Time:                         { type: 'long',  value: [0, 0] },
      WorldVersion:                 { type: 'int',   value: 1 },
      XBLBroadcastIntent:           { type: 'int',   value: 3 },
      abilities: { type: 'compound', value: {
        attackmobs:       { type: 'byte',  value: 1 },
        attackplayers:    { type: 'byte',  value: 1 },
        build:            { type: 'byte',  value: 1 },
        doorsandswitches: { type: 'byte',  value: 1 },
        flySpeed:         { type: 'float', value: 0.05 },
        flying:           { type: 'byte',  value: 0 },
        instabuild:       { type: 'byte',  value: 1 },
        invulnerable:     { type: 'byte',  value: 1 },
        lightning:        { type: 'byte',  value: 0 },
        mayfly:           { type: 'byte',  value: 1 },
        mine:             { type: 'byte',  value: 1 },
        op:               { type: 'byte',  value: 1 },
        opencontainers:   { type: 'byte',  value: 1 },
        permissionsLevel: { type: 'int',   value: 2 },
        playerPermissionsLevel:{ type: 'int', value: 2 },
        teleport:         { type: 'byte',  value: 1 },
        walkSpeed:        { type: 'float', value: 0.1 },
      } },
      baseGameVersion:              { type: 'string',value: '*' },
      bonusChestEnabled:            { type: 'byte',  value: 0 },
      bonusChestSpawned:            { type: 'byte',  value: 0 },
      commandblockoutput:           { type: 'byte',  value: 1 },
      commandblocksenabled:         { type: 'byte',  value: 1 },
      commandsEnabled:              { type: 'byte',  value: 1 },
      currentTick:                  { type: 'long',  value: [0, 0] },
      daylightCycle:                { type: 'int',   value: 0 },
      dodaylightcycle:              { type: 'byte',  value: 1 },
      doentitydrops:                { type: 'byte',  value: 1 },
      dofiretick:                   { type: 'byte',  value: 1 },
      doimmediaterespawn:           { type: 'byte',  value: 0 },
      doinsomnia:                   { type: 'byte',  value: 1 },
      domobloot:                    { type: 'byte',  value: 1 },
      domobspawning:                { type: 'byte',  value: 1 },
      dotiledrops:                  { type: 'byte',  value: 1 },
      doweathercycle:               { type: 'byte',  value: 1 },
      drowningdamage:               { type: 'byte',  value: 1 },
      eduOffer:                     { type: 'int',   value: 0 },
      educationFeaturesEnabled:     { type: 'byte',  value: 0 },
      experiments: { type: 'compound', value: {
        experiments_ever_used: { type: 'byte', value: 0 },
        saved_with_toggled_experiments: { type: 'byte', value: 0 },
      } },
      falldamage:                   { type: 'byte',  value: 1 },
      firedamage:                   { type: 'byte',  value: 1 },
      functioncommandlimit:         { type: 'int',   value: 10000 },
      hasBeenLoadedInCreative:      { type: 'byte',  value: 1 },
      hasLockedBehaviorPack:        { type: 'byte',  value: 0 },
      hasLockedResourcePack:        { type: 'byte',  value: 0 },
      immutableWorld:               { type: 'byte',  value: 0 },
      isFromLockedTemplate:         { type: 'byte',  value: 0 },
      isFromWorldTemplate:          { type: 'byte',  value: 0 },
      isSingleUseWorld:             { type: 'byte',  value: 0 },
      isWorldTemplateOptionLocked:  { type: 'byte',  value: 0 },
      keepinventory:                { type: 'byte',  value: 0 },
      lastOpenedWithVersion: { type: 'list',
        value: { type: 'int', value: [1, 18, 0, 0, 0] } },
      lightningLevel:               { type: 'float', value: 0.0 },
      lightningTime:                { type: 'int',   value: 0 },
      maxcommandchainlength:        { type: 'int',   value: 65535 },
      mobgriefing:                  { type: 'byte',  value: 1 },
      naturalregeneration:          { type: 'byte',  value: 1 },
      prid:                         { type: 'string',value: '' },
      pvp:                          { type: 'byte',  value: 1 },
      rainLevel:                    { type: 'float', value: 0.0 },
      rainTime:                     { type: 'int',   value: 0 },
      randomtickspeed:              { type: 'int',   value: 1 },
      requiresCopiedPackRemovalCheck:{ type: 'byte', value: 0 },
      sendcommandfeedback:          { type: 'byte',  value: 1 },
      serverChunkTickRange:         { type: 'int',   value: 4 },
      showcoordinates:              { type: 'byte',  value: 1 },
      showdeathmessages:            { type: 'byte',  value: 1 },
      showtags:                     { type: 'byte',  value: 1 },
      spawnMobs:                    { type: 'byte',  value: 1 },
      spawnradius:                  { type: 'int',   value: 5 },
      startWithMapEnabled:          { type: 'byte',  value: 0 },
      texturePacksRequired:         { type: 'byte',  value: 0 },
      tntexplodes:                  { type: 'byte',  value: 1 },
      useMsaGamertagsOnly:          { type: 'byte',  value: 0 },
      worldStartCount:              { type: 'long',  value: [0, 1] },
    }
  };

  const payload = nbt.writeUncompressed(tag, 'little');
  // Bedrock level.dat header: 4-byte version (LE), 4-byte payload length (LE).
  const header = Buffer.alloc(8);
  header.writeUInt32LE(9, 0);                 // storage version
  header.writeUInt32LE(payload.length, 4);
  return Buffer.concat([header, payload]);
}

// ---------- Main --------------------------------------------------------
(async () => {
  const LEVEL_NAME = 'Airport';
  const worldDir = path.resolve('./_world');
  const outFile  = path.resolve('./Airport.mcworld');

  try { fs.rmSync(worldDir, { recursive: true, force: true }); } catch {}
  try { fs.rmSync(outFile, { force: true }); } catch {}
  fs.mkdirSync(worldDir);

  await writeWorld(worldDir);

  // level.dat + _level_name.txt + levelname.txt
  const levelDat = buildLevelDat(LEVEL_NAME);
  fs.writeFileSync(path.join(worldDir, 'level.dat'), levelDat);
  fs.writeFileSync(path.join(worldDir, 'level.dat_old'), levelDat);
  fs.writeFileSync(path.join(worldDir, 'levelname.txt'), LEVEL_NAME);

  // Zip everything at the root of the .mcworld (no top-level folder).
  execSync(`cd "${worldDir}" && zip -rq "${outFile}" .`);
  const stat = fs.statSync(outFile);
  console.log(`\nCreated ${outFile} (${(stat.size / 1024).toFixed(1)} KB)`);
})().catch(e => { console.error(e); process.exit(1); });
