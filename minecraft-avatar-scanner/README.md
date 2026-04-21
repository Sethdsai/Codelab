# Minecraft Bedrock Edition - Avatar Scanner World

An extremely hard and complex Minecraft Bedrock Edition `.mcworld` map featuring a camera that captures the player and rebuilds their avatar using colored blocks.

## Features

- **Giant Camera Structure** — A detailed decorative camera made of black/gray concrete, diamond blocks, and stained glass lens
- **Scanning Platform** — Sea lantern platform with iron frame, diamond accents, and glowstone arch where the player stands
- **Display Wall** — Large black concrete wall with quartz frame where the pixel-art avatar is reconstructed block-by-block
- **202 Command Blocks** — Underground command block circuit that orchestrates the entire scanning and building animation
- **Automated Animation** — When triggered, the system displays scanning effects (titles, particles, sounds) then rebuilds a 8×16 pixel Steve avatar one block at a time

## How It Works

1. Player spawns facing the camera structure
2. Walk onto the scanning platform (sea lantern area)
3. The repeating command block detects you automatically
4. **SCANNING** title appears with particle effects and sounds
5. **COMPUTING** title appears as the system begins reconstruction
6. Colored concrete blocks are placed one-by-one on the display wall, building the avatar from feet to head
7. Sound effects play every 8 blocks during construction
8. **COMPLETE** title appears with celebration effects
9. After a delay, the display resets for the next scan

## Avatar Color Mapping

| Body Part | Block Used |
|-----------|-----------|
| Hair | Brown Concrete |
| Skin | Orange Concrete |
| Eyes (white) | White Concrete |
| Eyes (pupils) | Light Blue Concrete |
| Shirt | Cyan Concrete |
| Mouth | Pink Concrete |
| Pants | Blue Concrete |
| Shoes | Gray Concrete |

## Technical Details

- **World Type:** Flat (Creative Mode)
- **Target Version:** Minecraft Bedrock Edition 1.20.80+
- **Mob Spawning:** Disabled
- **Weather/Day Cycle:** Disabled
- **Command Blocks:** Enabled, always active
- **Coordinates:** Shown
- **Fall/Fire/Drowning Damage:** Disabled

## Installation

1. Download `AvatarScanner.mcworld`
2. Open the file — Minecraft Bedrock Edition will import it automatically
3. Select the world "Avatar Scanner - Extremely Hard Build" from your worlds list
4. Walk to the scanning platform and watch the magic happen!

## Regenerating the World

If you want to modify the world, edit `generate_world.py` and run:

```bash
pip install amulet-nbt amulet-leveldb numpy
python generate_world.py
```

This generates a fresh `AvatarScanner.mcworld` file.

## Build Stats

- ~27,600 blocks placed
- 202 command blocks in sequence
- 50 chunks generated
- 8×16 pixel avatar (96 colored blocks)
