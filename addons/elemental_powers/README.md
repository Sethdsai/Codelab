# Elemental Powers — Minecraft Bedrock Addon

> **Description:** uekermjheh on rblx

A Minecraft **Bedrock Edition** addon that adds seven elemental power sets plus a custom Dark Scythe weapon. Selecting an element grants its full **skill kit** (scripted active abilities — not potion effects).

---

## Install

1. Build the packs:

    ```bash
    ./tools/package.sh
    ```

    This produces, in `dist/`:
    - `elemental_powers.mcaddon` — double-click on a device with Minecraft Bedrock installed to import **both packs at once**.
    - `elemental_powers_BP.mcpack` / `elemental_powers_RP.mcpack` — individual behavior/resource packs.

2. In your world's settings, enable **Holiday Creator Features** and **Beta APIs** (Beta APIs is required for the Script module). Add the behavior pack and resource pack to the world.

3. Minimum game version: **1.21.70**.

---

## Usage

There are two ways to open the element-selection GUI:

- Type `/getmygui` in chat **or**
- Get the **GUI Tool** item (`/give @s elempower:gui_tool`) and hold-tap it (long press on mobile, right-click on PC, `ZL` on console).

A menu opens listing every element with its icon. Picking one instantly grants you that element's full skill set.

### Elements and skills

Every element grants **one Staff** (and the Dark element additionally grants the **Dark Scythe**). Each staff has two skills — **tap** for the primary, **sneak + tap** for the secondary. Cooldowns are displayed on the action bar.

| Element    | Primary (tap)             | Secondary (sneak + tap)       |
| ---------- | ------------------------- | ----------------------------- |
| Fire       | Fireball projectile       | Flame Nova ring AoE           |
| Water      | Tidal Lance line pierce   | Aqua Restore full heal        |
| Earth      | Stone Spike line damage   | Quake Stomp AoE + launch      |
| Air        | Gust Dash                 | Sky Leap                      |
| Lightning  | Thunder Strike at aim     | Chain Lightning (up to 5)     |
| Light      | Solar Beam + self heal    | Radiant Pulse AoE + heal      |
| Dark       | Void Grasp pull + damage  | Shadow Step teleport          |

The **Dark Scythe** (exclusive to the Dark element) adds:
- **Tap:** Shadow Slash — cone AoE damage
- **Sneak + tap:** Soul Reap — drain HP from everything around you
- **Passive:** melee hits deal bonus magic damage and restore your HP

---

## Project layout

```
addons/elemental_powers/
├── behavior_pack/
│   ├── manifest.json
│   ├── pack_icon.png
│   ├── items/                   # 16 custom items (7 staffs + 7 orbs + gui_tool + dark_scythe)
│   ├── scripts/main.js          # Script API entry
│   └── texts/en_US.lang
├── resource_pack/
│   ├── manifest.json
│   ├── pack_icon.png
│   ├── textures/
│   │   ├── item_texture.json
│   │   └── items/               # 16 procedurally-generated 64×64 PNGs
│   └── texts/en_US.lang
├── tools/
│   ├── generate_textures.py     # Pillow texture generator
│   ├── generate_items.py        # Item JSON generator
│   └── package.sh               # Build .mcpack / .mcaddon
└── dist/                        # Build output
```

---

## Regenerating assets

All icons are generated with Pillow (`python3 tools/generate_textures.py`) so they can be tweaked in code rather than hand-drawn. Item JSON can be regenerated with `python3 tools/generate_items.py`.
