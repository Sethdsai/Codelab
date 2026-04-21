# minecraft-airport-world

A tiny Node.js script that generates a **Minecraft Bedrock Edition `.mcworld`**
file from scratch containing a small airport with a parked airplane.

No Bedrock server, no in-game commands, no world editor — just a script that
writes a LevelDB save + a valid `level.dat` and zips it as `Airport.mcworld`.

## What's inside the world

- **Flat world** (biome: plains) — ~48×48 block area of terrain
- **Runway** (~48×8) in gray concrete with white thresholds and a dashed
  centerline, plus glowstone edge lights every 4 blocks
- **Taxiway** from the runway up to an apron
- **Apron** outlined in yellow concrete
- **Terminal building** (~14×7×5) — quartz walls, glass windows, glowstone
  ceiling lights, a "TERMINAL" strip in blue concrete above the front
- **Control tower** — 5×5 quartz shaft, 12 blocks tall, glass cab on top with
  a glowstone beacon
- **Parked airplane** (~14 long, ~10 wingspan) — iron fuselage, white nose,
  light-blue concrete wings with red wingtips, tail fin, and a glowstone
  propeller
- **Windsock pole** near the runway threshold

The build lives around world coordinates `(0, -58, 0)` (bedrock floor at
`y=-64`, grass at `y=-59`, airport blocks from `y=-58` upward).

## How to import the world

1. Copy `Airport.mcworld` to your Bedrock device.
2. Open it — the platform will auto-import:
   - **Android / iOS / Windows (Minecraft app)**: tap/double-click the file.
   - **Minecraft (any platform)**: Play → Worlds → Import → select the file.
3. The world appears in your worlds list as **"Airport"**.

## Building the file yourself

```bash
cd minecraft-airport-world
npm install
npm run build   # → Airport.mcworld in this folder
```

Requirements: Node.js 18+.

## How it works

1. Stages all block edits in an in-memory `Map<"x|y|z", stateId>`.
2. Groups edits by chunk (16×16 column).
3. For each chunk, creates a `prismarine-chunk` `ChunkColumn` at version
   `bedrock_1.18.0`, sets biomes to plains, applies the edits.
4. Writes LevelDB keys directly (bypassing a known `getSection` bug in
   `bedrock-provider@3.1.0`'s `save`):
   - `...VersionNew` — chunk version byte
   - `...SubChunkPrefix` — one key per subchunk (`section.encode(0)`)
   - `...Data3D` — heightmap + 3D biomes
   - `...FinalizedState` — `2` (populated)
5. Writes a minimal-but-complete Bedrock `level.dat` via `prismarine-nbt`
   (little-endian NBT with the 8-byte Bedrock header), setting
   `Generator=2` (flat) and `GameType=1` (creative).
6. Writes `levelname.txt` + a `level.dat_old` backup.
7. Zips the world folder (files at the archive root) as `Airport.mcworld`.

## Files

- `build_airport.js` — the generator (single file, ~500 LOC)
- `Airport.mcworld` — pre-built world (~8 KB), ready to import
- `package.json` — dependency list

## Credits

Built with [PrismarineJS](https://github.com/PrismarineJS) libraries:
`bedrock-provider`, `prismarine-chunk`, `prismarine-block`,
`prismarine-registry`, `prismarine-nbt`, `leveldb-zlib`.

## License

MIT.
