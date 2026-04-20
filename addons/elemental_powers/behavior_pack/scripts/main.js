/*
 * Elemental Powers - Minecraft Bedrock Script API entry point.
 *
 * Triggers that open the element GUI:
 *   - Tap / right-click the "GUI Tool" item while holding it.
 *   - Type "!getmygui" or "getmygui" in chat (Bedrock eats "/"-prefixed text as
 *     slash commands before scripts can see them).
 *   - Run "/scriptevent elempower:gui" (works on any platform, all versions).
 *   - Run the custom slash command "/elempower:getmygui" (MC >= 1.21.80 only).
 *
 * Selecting an element grants its full scripted skill kit (no potion effects).
 * Seven elements (Fire, Water, Earth, Air, Lightning, Light, Dark) + Dark Scythe weapon.
 *
 * Description: uekermjheh on rblx
 */

import * as mc from "@minecraft/server";
import { ActionFormData } from "@minecraft/server-ui";

const { world, system, EntityDamageCause, EquipmentSlot, ItemStack } = mc;

const NS = "elempower";

const ELEMENTS = [
  {
    id: "fire",
    label: "Fire",
    color: "c",
    subtitle: "Fireball - Flame Nova",
    icon: "textures/items/elem_fire_orb",
    items: [`${NS}:fire_staff`, `${NS}:fire_orb`],
  },
  {
    id: "water",
    label: "Water",
    color: "b",
    subtitle: "Tidal Lance - Aqua Restore",
    icon: "textures/items/elem_water_orb",
    items: [`${NS}:water_staff`, `${NS}:water_orb`],
  },
  {
    id: "earth",
    label: "Earth",
    color: "2",
    subtitle: "Stone Spike - Quake Stomp",
    icon: "textures/items/elem_earth_orb",
    items: [`${NS}:earth_staff`, `${NS}:earth_orb`],
  },
  {
    id: "air",
    label: "Air",
    color: "f",
    subtitle: "Gust Dash - Sky Leap",
    icon: "textures/items/elem_air_orb",
    items: [`${NS}:air_staff`, `${NS}:air_orb`],
  },
  {
    id: "lightning",
    label: "Lightning",
    color: "e",
    subtitle: "Thunder Strike - Chain Lightning",
    icon: "textures/items/elem_lightning_orb",
    items: [`${NS}:lightning_staff`, `${NS}:lightning_orb`],
  },
  {
    id: "light",
    label: "Light",
    color: "g",
    subtitle: "Solar Beam - Radiant Pulse",
    icon: "textures/items/elem_light_orb",
    items: [`${NS}:light_staff`, `${NS}:light_orb`],
  },
  {
    id: "dark",
    label: "Dark",
    color: "5",
    subtitle: "Void Grasp - Shadow Step - Dark Scythe",
    icon: "textures/items/elem_dark_orb",
    items: [`${NS}:dark_staff`, `${NS}:dark_orb`, `${NS}:dark_scythe`],
  },
];

// ---------------------------------------------------------------------------
// cooldowns (in-memory)
// ---------------------------------------------------------------------------
const COOLDOWN_TICKS = {
  [`${NS}:fire_staff`]: 20,
  [`${NS}:water_staff`]: 30,
  [`${NS}:earth_staff`]: 30,
  [`${NS}:air_staff`]: 15,
  [`${NS}:lightning_staff`]: 40,
  [`${NS}:light_staff`]: 30,
  [`${NS}:dark_staff`]: 35,
  [`${NS}:dark_scythe`]: 25,
  [`${NS}:gui_tool`]: 6,
};

/** @type {Map<string, Map<string, number>>} */
const COOLDOWNS = new Map();

function checkCooldown(player, item) {
  const now = system.currentTick;
  const ticks = COOLDOWN_TICKS[item] ?? 20;
  let perPlayer = COOLDOWNS.get(player.id);
  if (!perPlayer) {
    perPlayer = new Map();
    COOLDOWNS.set(player.id, perPlayer);
  }
  const last = perPlayer.get(item);
  if (typeof last === "number" && now - last < ticks) {
    const remaining = ((ticks - (now - last)) / 20).toFixed(1);
    tryActionBar(player, `§c§lCooldown §7${remaining}s`);
    return false;
  }
  perPlayer.set(item, now);
  return true;
}

function tryActionBar(player, text) {
  try { player.onScreenDisplay.setActionBar(text); } catch (e) { /* */ }
}

try {
  world.afterEvents.playerLeave.subscribe((ev) => {
    COOLDOWNS.delete(ev.playerId);
  });
} catch (e) { /* old API */ }

// ---------------------------------------------------------------------------
// vec helpers
// ---------------------------------------------------------------------------
const vAdd = (a, b) => ({ x: a.x + b.x, y: a.y + b.y, z: a.z + b.z });
const vScale = (v, s) => ({ x: v.x * s, y: v.y * s, z: v.z * s });
const vLen = (v) => Math.hypot(v.x, v.y, v.z);
const vNorm = (v) => { const l = vLen(v) || 1; return { x: v.x / l, y: v.y / l, z: v.z / l }; };
const vHoriz = (v) => vNorm({ x: v.x, y: 0, z: v.z });

function raycastEntity(player, maxDistance) {
  try {
    const hits = player.getEntitiesFromViewDirection({ maxDistance });
    for (const h of hits || []) {
      if (h && h.entity && h.entity.id !== player.id) return h.entity;
    }
  } catch (e) { /* */ }
  return undefined;
}

function raycastBlockLocation(player, maxDistance) {
  try {
    const hit = player.getBlockFromViewDirection({ maxDistance });
    if (hit && hit.block) return hit.block.location;
  } catch (e) { /* */ }
  const head = player.getHeadLocation();
  return vAdd(head, vScale(player.getViewDirection(), maxDistance));
}

function entitiesNear(dimension, origin, radius, excludeId) {
  try {
    return dimension.getEntities({
      location: origin,
      maxDistance: radius,
      excludeTypes: ["minecraft:item", "minecraft:xp_orb"],
    }).filter((e) => e && e.id !== excludeId);
  } catch (e) {
    return [];
  }
}

function entitiesInCone(player, origin, forward, maxDistance, cosAngle) {
  const candidates = entitiesNear(player.dimension, origin, maxDistance, player.id);
  const results = [];
  for (const e of candidates) {
    const to = { x: e.location.x - origin.x, y: e.location.y - origin.y, z: e.location.z - origin.z };
    if (vLen(to) < 0.01) continue;
    const n = vNorm(to);
    const dot = n.x * forward.x + n.y * forward.y + n.z * forward.z;
    if (dot >= cosAngle) results.push(e);
  }
  return results;
}

function safeParticle(dimension, id, loc) {
  try { dimension.spawnParticle(id, loc); } catch (e) { /* */ }
}

function healPlayer(player, amount) {
  try {
    const h = player.getComponent("minecraft:health");
    if (!h) return;
    const cur = h.currentValue;
    const max = h.effectiveMax ?? h.defaultValue ?? 20;
    h.setCurrentValue(Math.min(max, cur + amount));
  } catch (e) { /* */ }
}

function damage(entity, amount, player, cause) {
  try {
    entity.applyDamage(amount, {
      cause: cause || EntityDamageCause.entityAttack,
      damagingEntity: player,
    });
  } catch (e) { /* */ }
}

// ---------------------------------------------------------------------------
// skills
// ---------------------------------------------------------------------------
function castFire(player) {
  const dim = player.dimension;
  const head = player.getHeadLocation();
  const view = player.getViewDirection();
  if (player.isSneaking) {
    for (let a = 0; a < Math.PI * 2; a += Math.PI / 24) {
      const p = vAdd(player.location, { x: Math.cos(a) * 3, y: 0.6, z: Math.sin(a) * 3 });
      safeParticle(dim, "minecraft:basic_flame_particle", p);
    }
    for (const v of entitiesNear(dim, player.location, 5, player.id)) {
      damage(v, 10, player, EntityDamageCause.fire);
      try {
        const dir = vNorm({ x: v.location.x - player.location.x, y: 0, z: v.location.z - player.location.z });
        v.applyKnockback(dir.x, dir.z, 1.6, 0.6);
      } catch (e) { /* */ }
    }
    try { player.playSound("mob.blaze.shoot"); } catch (e) { /* */ }
    tryActionBar(player, "§c§lFlame Nova §7unleashed");
  } else {
    const spawnPos = vAdd(head, vScale(view, 1.2));
    let ok = false;
    try {
      const fb = dim.spawnEntity("minecraft:fireball", spawnPos);
      fb.applyImpulse(vScale(view, 2.5));
      ok = true;
    } catch (e) { /* */ }
    if (!ok) {
      for (let i = 1; i <= 20; i++) {
        safeParticle(dim, "minecraft:basic_flame_particle", vAdd(head, vScale(view, i)));
      }
      const t = raycastEntity(player, 32);
      if (t) damage(t, 8, player, EntityDamageCause.fire);
    }
    try { player.playSound("mob.ghast.fireball"); } catch (e) { /* */ }
    tryActionBar(player, "§c§lFireball §7launched");
  }
}

function castWater(player) {
  const dim = player.dimension;
  const head = player.getHeadLocation();
  const view = player.getViewDirection();
  if (player.isSneaking) {
    healPlayer(player, 20);
    for (let i = 0; i < 24; i++) {
      const a = (Math.PI * 2 * i) / 24;
      const p = vAdd(player.location, { x: Math.cos(a) * 2, y: 1 + Math.sin(a) * 0.5, z: Math.sin(a) * 2 });
      safeParticle(dim, "minecraft:water_splash_particle", p);
    }
    try { player.playSound("random.splash"); } catch (e) { /* */ }
    tryActionBar(player, "§b§lAqua Restore §7full HP");
  } else {
    for (let i = 1; i <= 18; i++) {
      safeParticle(dim, "minecraft:water_splash_particle", vAdd(head, vScale(view, i)));
    }
    const victims = entitiesInCone(player, head, vNorm(view), 18, Math.cos(Math.PI / 14));
    for (const v of victims) {
      damage(v, 9, player, EntityDamageCause.magic);
      try { v.applyKnockback(view.x, view.z, 1.2, 0.2); } catch (e) { /* */ }
    }
    tryActionBar(player, "§b§lTidal Lance");
  }
}

function castEarth(player) {
  const dim = player.dimension;
  const view = player.getViewDirection();
  if (player.isSneaking) {
    for (let a = 0; a < Math.PI * 2; a += Math.PI / 18) {
      const p = vAdd(player.location, { x: Math.cos(a) * 4, y: 0.1, z: Math.sin(a) * 4 });
      safeParticle(dim, "minecraft:basic_crit_particle", p);
    }
    for (const v of entitiesNear(dim, player.location, 6, player.id)) {
      damage(v, 11, player, EntityDamageCause.entityAttack);
      try { v.applyKnockback(0, 0, 0, 1.2); } catch (e) { /* */ }
    }
    try { player.playSound("dig.stone"); } catch (e) { /* */ }
    tryActionBar(player, "§2§lQuake Stomp");
  } else {
    for (let i = 1; i <= 8; i++) {
      const step = vAdd(player.location, vScale(vHoriz(view), i));
      safeParticle(dim, "minecraft:basic_crit_particle", { x: step.x, y: step.y + 1, z: step.z });
      for (const v of entitiesNear(dim, step, 1.6, player.id)) {
        damage(v, 7, player, EntityDamageCause.entityAttack);
        try { v.applyKnockback(0, 0, 0, 0.9); } catch (e) { /* */ }
      }
    }
    tryActionBar(player, "§2§lStone Spike");
  }
}

function castAir(player) {
  const view = player.getViewDirection();
  if (player.isSneaking) {
    try { player.applyImpulse({ x: view.x * 0.8, y: 1.6, z: view.z * 0.8 }); } catch (e) { /* */ }
    for (let i = 0; i < 12; i++) {
      const p = vAdd(player.location, { x: (Math.random() - 0.5) * 2, y: i * 0.3, z: (Math.random() - 0.5) * 2 });
      safeParticle(player.dimension, "minecraft:cloud", p);
    }
    tryActionBar(player, "§f§lSky Leap");
  } else {
    try { player.applyImpulse({ x: view.x * 2.4, y: Math.max(0.3, view.y * 1.2), z: view.z * 2.4 }); } catch (e) { /* */ }
    for (let i = 1; i <= 12; i++) {
      safeParticle(player.dimension, "minecraft:cloud", vAdd(player.location, vScale(view, i)));
    }
    tryActionBar(player, "§f§lGust Dash");
  }
}

function castLightning(player) {
  const dim = player.dimension;
  if (player.isSneaking) {
    const near = entitiesNear(dim, player.location, 18, player.id).slice(0, 5);
    for (const t of near) {
      try { dim.spawnEntity("minecraft:lightning_bolt", t.location); } catch (e) { /* */ }
      damage(t, 8, player, EntityDamageCause.lightning);
    }
    tryActionBar(player, `§e§lChain Lightning §7 ${near.length}`);
  } else {
    const target = raycastEntity(player, 32);
    const loc = target ? target.location : raycastBlockLocation(player, 32);
    if (target) damage(target, 12, player, EntityDamageCause.lightning);
    try { dim.spawnEntity("minecraft:lightning_bolt", loc); } catch (e) { /* */ }
    tryActionBar(player, "§e§lThunder Strike");
  }
}

function castLight(player) {
  const dim = player.dimension;
  if (player.isSneaking) {
    for (let a = 0; a < Math.PI * 2; a += Math.PI / 12) {
      const p = vAdd(player.location, { x: Math.cos(a) * 4, y: 1, z: Math.sin(a) * 4 });
      safeParticle(dim, "minecraft:villager_happy", p);
    }
    let hit = 0;
    for (const v of entitiesNear(dim, player.location, 8, player.id)) {
      if (v.typeId === "minecraft:player") continue;
      damage(v, 8, player, EntityDamageCause.magic);
      hit++;
    }
    healPlayer(player, 3 + hit);
    try { player.playSound("beacon.power"); } catch (e) { /* */ }
    tryActionBar(player, "§e§lRadiant Pulse");
  } else {
    const target = raycastEntity(player, 32);
    const head = player.getHeadLocation();
    const view = player.getViewDirection();
    for (let i = 1; i <= 22; i++) {
      safeParticle(dim, "minecraft:villager_happy", vAdd(head, vScale(view, i)));
    }
    if (target) {
      damage(target, 14, player, EntityDamageCause.magic);
      healPlayer(player, 4);
    }
    try { player.playSound("beacon.activate"); } catch (e) { /* */ }
    tryActionBar(player, "§e§lSolar Beam");
  }
}

function castDark(player) {
  const dim = player.dimension;
  const head = player.getHeadLocation();
  const view = player.getViewDirection();
  if (player.isSneaking) {
    const dest = vAdd(player.location, vScale(view, 20));
    try { player.teleport(dest, { dimension: dim }); } catch (e) { /* */ }
    for (let i = 0; i < 20; i++) {
      safeParticle(dim, "minecraft:mobspell_emitter", vAdd(player.location, vScale(view, -i)));
    }
    try { player.playSound("mob.endermen.portal"); } catch (e) { /* */ }
    tryActionBar(player, "§5§lShadow Step");
  } else {
    const target = raycastEntity(player, 24);
    if (target) {
      damage(target, 10, player, EntityDamageCause.magic);
      const back = vNorm({ x: player.location.x - target.location.x, y: 0, z: player.location.z - target.location.z });
      const pullPos = vAdd(target.location, vScale(back, 1.5));
      try { player.teleport(pullPos, { dimension: dim }); } catch (e) { /* */ }
      for (let i = 1; i <= 10; i++) {
        safeParticle(dim, "minecraft:mobspell_emitter", vAdd(head, vScale(view, i)));
      }
      try { player.playSound("mob.wither.shoot"); } catch (e) { /* */ }
      tryActionBar(player, "§5§lVoid Grasp");
    } else {
      tryActionBar(player, "§5§lVoid Grasp §7(no target)");
    }
  }
}

function castDarkScythe(player) {
  const dim = player.dimension;
  const head = player.getHeadLocation();
  const view = player.getViewDirection();
  if (player.isSneaking) {
    const victims = entitiesNear(dim, player.location, 4.5, player.id)
      .filter((e) => e.typeId !== "minecraft:player");
    let drained = 0;
    for (const v of victims) {
      damage(v, 9, player, EntityDamageCause.magic);
      drained++;
    }
    healPlayer(player, drained * 2);
    for (let i = 0; i < 16; i++) {
      const a = (Math.PI * 2 * i) / 16;
      safeParticle(dim, "minecraft:mobspell_emitter",
        vAdd(player.location, { x: Math.cos(a) * 3, y: 1, z: Math.sin(a) * 3 }));
    }
    try { player.playSound("mob.wither.ambient"); } catch (e) { /* */ }
    tryActionBar(player, `§5§lSoul Reap §7 ${drained}`);
  } else {
    const forward = vNorm(view);
    const victims = entitiesInCone(player, head, forward, 6, Math.cos(Math.PI / 4));
    for (const v of victims) {
      damage(v, 12, player, EntityDamageCause.entityAttack);
      try { v.applyKnockback(view.x, view.z, 1.4, 0.4); } catch (e) { /* */ }
    }
    for (let i = 1; i <= 6; i++) {
      safeParticle(dim, "minecraft:mobspell_emitter", vAdd(head, vScale(view, i)));
    }
    try { player.playSound("mob.wither.shoot"); } catch (e) { /* */ }
    tryActionBar(player, `§5§lShadow Slash §7 ${victims.length}`);
  }
}

const SKILL_HANDLERS = {
  [`${NS}:fire_staff`]: castFire,
  [`${NS}:water_staff`]: castWater,
  [`${NS}:earth_staff`]: castEarth,
  [`${NS}:air_staff`]: castAir,
  [`${NS}:lightning_staff`]: castLightning,
  [`${NS}:light_staff`]: castLight,
  [`${NS}:dark_staff`]: castDark,
  [`${NS}:dark_scythe`]: castDarkScythe,
};

// ---------------------------------------------------------------------------
// grant items
// ---------------------------------------------------------------------------
function giveItem(player, typeId, amount) {
  try {
    const inv = player.getComponent("minecraft:inventory");
    if (!inv || !inv.container) return;
    const stack = new ItemStack(typeId, amount || 1);
    const leftover = inv.container.addItem(stack);
    if (leftover) {
      player.dimension.spawnItem(leftover, player.location);
    }
  } catch (e) {
    try { console.warn(`giveItem failed for ${typeId}: ${e}`); } catch (_) { /* */ }
  }
}

function grantElement(player, el) {
  for (const it of el.items) giveItem(player, it, 1);
  player.sendMessage(`§${el.color}§l[Elemental Powers]§r §7Granted §${el.color}${el.label}§7 skills.`);
  try { player.playSound("random.levelup"); } catch (e) { /* */ }
}

function grantAll(player) {
  for (const el of ELEMENTS) for (const it of el.items) giveItem(player, it, 1);
  player.sendMessage("§d§l[Elemental Powers]§r §7All §delemental§7 skills granted.");
  try { player.playSound("random.levelup"); } catch (e) { /* */ }
}

// ---------------------------------------------------------------------------
// GUI
// ---------------------------------------------------------------------------
function openGui(player) {
  const form = new ActionFormData()
    .title("§5§lElemental Powers")
    .body(
      "§7Choose an element to §freceive its full skill kit§7.\n" +
      "§8Tap the staff to cast primary. §8Hold §7SNEAK§8 + tap for secondary.\n" +
      "§5uekermjheh on rblx",
    );
  for (const el of ELEMENTS) {
    form.button(`§${el.color}§l${el.label}§r\n§7${el.subtitle}`, el.icon);
  }
  form.button("§d§lAll Elements§r\n§7Every skill at once", "textures/items/elem_gui_tool");
  form.button("§c§lCancel", "textures/items/elem_dark_orb");

  form.show(player).then((res) => {
    if (!res || res.canceled) return;
    const idx = res.selection;
    if (typeof idx !== "number") return;
    if (idx < ELEMENTS.length) return grantElement(player, ELEMENTS[idx]);
    if (idx === ELEMENTS.length) return grantAll(player);
  }).catch((err) => {
    try { console.warn(`form error: ${err}`); } catch (e) { /* */ }
  });
}

// ---------------------------------------------------------------------------
// listeners
// ---------------------------------------------------------------------------

// 1) Item use (tap/right-click) - fires in before (press) AND after (release)
function handleItemUse(source, itemStack) {
  const id = itemStack && itemStack.typeId;
  if (!id || !source) return;
  if (id === `${NS}:gui_tool`) {
    if (!checkCooldown(source, id)) return;
    system.run(() => openGui(source));
    return;
  }
  const handler = SKILL_HANDLERS[id];
  if (!handler) return;
  if (!checkCooldown(source, id)) return;
  system.run(() => {
    try { handler(source); } catch (e) {
      try { console.warn(`skill error for ${id}: ${e}`); } catch (_) { /* */ }
    }
  });
}

try {
  world.afterEvents.itemUse.subscribe((ev) => handleItemUse(ev.source, ev.itemStack));
} catch (e) { /* */ }

try {
  // Some Bedrock versions only deliver itemUse via before-events. Subscribe to
  // both and dedupe via cooldown so we fire exactly once per tap.
  world.beforeEvents.itemUse.subscribe((ev) => handleItemUse(ev.source, ev.itemStack));
} catch (e) { /* */ }

// 2) Chat trigger - Bedrock blocks "/"-prefixed messages; accept !getmygui or getmygui
try {
  world.beforeEvents.chatSend.subscribe((ev) => {
    const raw = (ev.message || "").trim().toLowerCase();
    if (raw === "!getmygui" || raw === "getmygui" || raw === "gui") {
      ev.cancel = true;
      const sender = ev.sender;
      system.run(() => openGui(sender));
    }
  });
} catch (e) { /* */ }

// 3) /scriptevent elempower:gui
try {
  system.afterEvents.scriptEventReceive.subscribe((ev) => {
    if (ev.id !== `${NS}:gui`) return;
    const player = ev.sourceEntity;
    if (!player || player.typeId !== "minecraft:player") return;
    system.run(() => openGui(player));
  });
} catch (e) { /* */ }

// 4) Custom slash command (MC 1.21.80+ @minecraft/server 1.17.0). Best-effort.
try {
  if (system.beforeEvents && system.beforeEvents.startup) {
    system.beforeEvents.startup.subscribe((ev) => {
      try {
        const reg = ev.customCommandRegistry;
        if (!reg || typeof reg.registerCommand !== "function") return;
        reg.registerCommand(
          {
            name: `${NS}:getmygui`,
            description: "Open the Elemental Powers selection GUI",
            permissionLevel: (mc.CommandPermissionLevel && mc.CommandPermissionLevel.Any) ?? 0,
          },
          (origin) => {
            const player = origin && origin.sourceEntity;
            if (player && player.typeId === "minecraft:player") {
              system.run(() => openGui(player));
            }
            return { status: 0, message: "Opening Elemental Powers..." };
          },
        );
      } catch (e) {
        try { console.warn(`custom command register failed: ${e}`); } catch (_) { /* */ }
      }
    });
  }
} catch (e) { /* */ }

// 5) Dark Scythe passive: melee hit -> bonus damage + lifesteal
try {
  world.afterEvents.entityHitEntity.subscribe((ev) => {
    const attacker = ev.damagingEntity;
    const target = ev.hitEntity;
    if (!attacker || !target) return;
    if (attacker.typeId !== "minecraft:player") return;
    let mainhandId;
    try {
      const equip = attacker.getComponent("minecraft:equippable");
      const slot = equip && equip.getEquipment && equip.getEquipment(EquipmentSlot.Mainhand);
      mainhandId = slot && slot.typeId;
    } catch (e) { return; }
    if (mainhandId !== `${NS}:dark_scythe`) return;
    damage(target, 4, attacker, EntityDamageCause.magic);
    healPlayer(attacker, 2);
    safeParticle(attacker.dimension, "minecraft:mobspell_emitter", target.location);
  });
} catch (e) { /* */ }

// 6) Auto-give GUI Tool on first spawn + welcome message
const GIVEN_TAG = "elempower_given_gui";
try {
  world.afterEvents.playerSpawn.subscribe((ev) => {
    if (!ev.initialSpawn) return;
    const player = ev.player;
    if (!player) return;
    system.run(() => {
      try {
        if (!player.hasTag(GIVEN_TAG)) {
          giveItem(player, `${NS}:gui_tool`, 1);
          player.addTag(GIVEN_TAG);
        }
        player.sendMessage("§5§l[Elemental Powers]§r §7Loaded. Tap the §dGUI Tool§7 or type §b!getmygui§7 in chat.");
      } catch (e) { /* */ }
    });
  });
} catch (e) { /* */ }

// 7) Startup broadcast so the player can confirm scripts are running
system.run(() => {
  try {
    world.sendMessage("§5§l[Elemental Powers]§r §7scripts loaded - §5uekermjheh on rblx");
  } catch (e) { /* */ }
  try { console.log("[Elemental Powers] ready"); } catch (e) { /* */ }
});
