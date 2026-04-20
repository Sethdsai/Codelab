"""Generate the behavior-pack item JSON files for the Elemental Powers addon."""
import json
from pathlib import Path

BP_ITEMS = Path(__file__).resolve().parent.parent / "behavior_pack" / "items"
BP_ITEMS.mkdir(parents=True, exist_ok=True)

NAMESPACE = "elempower"


def staff_item(name: str, texture: str, damage: int = 2):
    return {
        "format_version": "1.20.10",
        "minecraft:item": {
            "description": {
                "identifier": f"{NAMESPACE}:{name}",
                "menu_category": {
                    "category": "equipment",
                    "group": "itemGroup.name.elemental_powers"
                }
            },
            "components": {
                "minecraft:icon": {"texture": texture},
                "minecraft:display_name": {"value": name.replace("_", " ").title()},
                "minecraft:max_stack_size": 1,
                "minecraft:hand_equipped": True,
                "minecraft:damage": damage,
                "minecraft:durability": {"max_durability": 2000},
                "minecraft:use_animation": "eat",
                "minecraft:glint": True
            }
        }
    }


def orb_item(name: str, texture: str):
    # Orbs are consumable unlock keys: eat one, go through the dizzy
    # awakening animation, and awaken with the full elemental staff kit.
    return {
        "format_version": "1.20.10",
        "minecraft:item": {
            "description": {
                "identifier": f"{NAMESPACE}:{name}",
                "menu_category": {
                    "category": "items",
                    "group": "itemGroup.name.elemental_powers"
                }
            },
            "components": {
                "minecraft:icon": {"texture": texture},
                "minecraft:display_name": {"value": name.replace("_", " ").title()},
                "minecraft:max_stack_size": 1,
                "minecraft:hand_equipped": True,
                "minecraft:use_animation": "drink",
                "minecraft:food": {
                    "nutrition": 0,
                    "saturation_modifier": "low",
                    "can_always_eat": True
                },
                "minecraft:glint": True
            }
        }
    }


def scythe_item():
    return {
        "format_version": "1.20.10",
        "minecraft:item": {
            "description": {
                "identifier": f"{NAMESPACE}:dark_scythe",
                "menu_category": {
                    "category": "equipment",
                    "group": "itemGroup.name.elemental_powers"
                }
            },
            "components": {
                "minecraft:icon": {"texture": "elem_dark_scythe"},
                "minecraft:display_name": {"value": "Dark Scythe"},
                "minecraft:max_stack_size": 1,
                "minecraft:hand_equipped": True,
                "minecraft:damage": 9,
                "minecraft:durability": {"max_durability": 3000},
                "minecraft:use_animation": "eat",
                "minecraft:glint": True
            }
        }
    }


def gui_tool_item():
    return {
        "format_version": "1.20.10",
        "minecraft:item": {
            "description": {
                "identifier": f"{NAMESPACE}:gui_tool",
                "menu_category": {
                    "category": "items",
                    "group": "itemGroup.name.elemental_powers"
                }
            },
            "components": {
                "minecraft:icon": {"texture": "elem_gui_tool"},
                "minecraft:display_name": {"value": "GUI Tool"},
                "minecraft:max_stack_size": 1,
                "minecraft:hand_equipped": True,
                "minecraft:use_animation": "eat",
                "minecraft:glint": True
            }
        }
    }


STAFFS = ["fire", "water", "earth", "air", "lightning", "light", "dark"]
STAFF_DAMAGE = {
    "fire": 5, "water": 3, "earth": 7, "air": 3,
    "lightning": 6, "light": 4, "dark": 6,
}


def main() -> None:
    written = []
    for el in STAFFS:
        name = f"{el}_staff"
        data = staff_item(name, f"elem_{name}", damage=STAFF_DAMAGE[el])
        path = BP_ITEMS / f"{name}.json"
        path.write_text(json.dumps(data, indent=2))
        written.append(path)

        orb_name = f"{el}_orb"
        odata = orb_item(orb_name, f"elem_{orb_name}")
        opath = BP_ITEMS / f"{orb_name}.json"
        opath.write_text(json.dumps(odata, indent=2))
        written.append(opath)

    for data, fname in [(scythe_item(), "dark_scythe.json"),
                        (gui_tool_item(), "gui_tool.json")]:
        path = BP_ITEMS / fname
        path.write_text(json.dumps(data, indent=2))
        written.append(path)

    for p in written:
        print(f"wrote {p.relative_to(BP_ITEMS.parent.parent)}")


if __name__ == "__main__":
    main()
