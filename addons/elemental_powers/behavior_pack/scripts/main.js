/*
 * Elemental Powers - Minecraft Bedrock Script API entry point.
 *
 * Features:
 *  - /getmygui chat command and "gui_tool" item both open the elemental selection form.
 *  - Selecting an element grants the player that element's full skill set
 *    (custom items whose use triggers scripted abilities — no potion effects).
 *  - Seven elements (Fire, Water, Earth, Air, Lightning, Light, Dark) + Dark Scythe weapon.
 *  - Per-skill cooldowns tracked via tick timestamps, no dangling state.
 *
 * Description: uekermjheh on rblx
 */

import {
  world,
  system,
  EntityDamageCause,
  EquipmentSlot,
  ItemStack,
  GameMode,
} from "@minecraft/server";
import { ActionFormData } from "@minecraft/server-ui";

const NS = "elempower";

/** @type {ReadonlyArray<{id: string, label: string, color: string, subtitle: string, icon: string, items: string[]}>} */
const ELEMENTS = [
  {
    id: "fire",
    label: "Fire",
    color: "c",
    subtitle: "Fireball · Flame Nova",
    icon: "textures/items/elem_fire_orb",
    items: [`${NS}:fire_staff`, `${NS}:fire_orb`],
  },
  {
    id: "water",
    label: "Water",
    color: "b",
    subtitle: "Tidal Lance · Aqua Restore",
    icon: "textures/items/elem_water_orb",
    items: [`${NS}:water_staff`, `${NS}:water_orb`],
  },
  {
    id: "earth",
    label: "Earth",
    color: "2",
    subtitle: "Stone Spike · Quake Stomp",
    icon: "textures/items/elem_earth_orb",
    items: [`${NS}:earth_staff`, `${NS}:earth_orb`],
  },
  {
    id: "air",
    label: "Air",
    color: "f",
    subtitle: "Gust Dash · Sky Leap",
    icon: "textures/items/elem_air_orb",
    items: [`${NS}:air_staff`, `${NS}:air_orb`],
  },
  {
    id: "lightning",
    label: "Lightning",
    color: "e",
    subtitle: "Thunder Strike · Chain Lightning",
    icon: "textures/items/elem_lightning_orb",
    items: [`${NS}:lightning_staff`, `${NS}:lightning_orb`],
  },
  {
    id: "light",
    label: "Light",
    color: "g",
    subtitle: "Solar Beam · Radiant Pulse",
    icon: "textures/items/elem_light_orb",
    items: [`${NS}:light_staff`, `${NS}:light_orb`],
  },
  {
    id: "dark",
    label: "Dark",
    color: "5",
    subtitle: "Void Grasp · Shadow Step · Dark Scythe",
    icon: "textures/items/elem_dark_orb",
    items: [`${NS}:dark_staff`, `${NS}:dark_orb`, `${NS}:dark_scythe`],
  },
];

// ----------------------------------------------------------------------------
// cooldown helpers
// ----------------------------------------------------------------------------
const COOLDOWN_TICKS = {
  [`${NS}:fire_staff`]: 20,
  [`${NS}:water_staff`]: 30,
  [`${NS}:earth_staff`]: 30,
  [`${NS}:air_staff`]: 15,
  [`${NS}:lightning_staff`]: 40,
  [`${NS}:light_staff`]: 30,
  [`${NS}:dark_staff`]: 35,
  [`${NS}:dark_scythe`]: 25,
};

/** @type {Map<string, Map<string, number>>} playerId -> itemTypeId -> lastTick */
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
    try { player.onScreenDisplay.setActionBar(`§c§lCooldown §7${remaining}s`); } catch (e) { /* */ }
    return false;
  }
  perPlayer.set(item, now);
  return true;
}

world.afterEvents.playerLeave.subscribe((ev) => {
  COOLDOWNS.delete(ev.playerId);
});

// ----------------------------------------------------------------------------
// vector helpers
// ----------------------------------------------------------------------------
const vAdd = (a, b) => ({ x: a.x + b.x, y: a.y + b.y, z: a.z + b.z });
const vScale = (v, s) => ({ x: v.x * s, y: v.y * s, z: v.z * s });
const vLen = (v) => Math.hypot(v.x, v.y, v.z);

function normalize(v) {
  const l = vLen(v) || 1;
  return { x: v.x / l, y: v.y / l, z: v.z / l };
}

function horizontal(v) {
  const h = { x: v.x, y: 0, z: v.z };
  return normalize(h);
}

// ----------------------------------------------------------------------------
// targeting utilities
// ----------------------------------------------------------------------------
function raycastEntity(player, maxDistance = 32) {
  try {
    const hit = player.getEntitiesFromViewDirection({ maxDistance });
    if (hit && hit.length > 0) {
      for (const h of hit) {
        if (h.entity && h.entity.id !== player.id) return h.entity;
      }
    }
  } catch (e) {
    // older 1.14 might throw if nothing is found
  }
  return undefined;
}

function raycastBlockLocation(player, maxDistance = 32) {
  try {
    const hit = player.getBlockFromViewDirection({ maxDistance });
    if (hit) return hit.block.location;
  } catch (e) {
    /* noop */
  }
  // fallback: project from head
  const head = player.getHeadLocation();
  return vAdd(head, vScale(player.getViewDirection(), maxDistance));
}

function entitiesNear(dimension, origin, radius, excludeId) {
  return dimension.getEntities({
    location: origin,
    maxDistance: radius,
    excludeTypes: ["minecraft:item", "minecraft:xp_orb"],
  }).filter((e) => e.id !== excludeId);
}

function entitiesInCone(player, origin, forward, maxDistance, cosAngle) {
  const candidates = player.dimension.getEntities({
    location: origin,
    maxDistance,
    excludeTypes: ["minecraft:item", "minecraft:xp_orb"],
  });
  const results = [];
  for (const e of candidates) {
    if (e.id === player.id) continue;
    const to = { x: e.location.x - origin.x, y: e.location.y - origin.y, z: e.location.z - origin.z };
    if (vLen(to) < 0.01) continue;
    const n = normalize(to);
    const dot = n.x * forward.x + n.y * forward.y + n.z * forward.z;
    if (dot >= cosAngle) results.push(e);
  }
  return results;
}

function safeParticle(dimension, id, loc, variables) {
  try {
    dimension.spawnParticle(id, loc, variables);
  } catch (e) {
    /* particle may not exist on that platform */
  }
}

// ----------------------------------------------------------------------------
// skills - each returns true if the skill fired
// ----------------------------------------------------------------------------
function castFire(player) {
  const dim = player.dimension;
  const head = player.getHeadLocation();
  const view = player.getViewDirection();
  if (player.isSneaking) {
    // Flame Nova - damage + knockback ring
    for (let a = 0; a < Math.PI * 2; a += Math.PI / 24) {
      const p = vAdd(player.location, { x: Math.cos(a) * 3, y: 0.6, z: Math.sin(a) * 3 });
      safeParticle(dim, "minecraft:basic_flame_particle", p);
      safeParticle(dim, "minecraft:huge_explosion_emitter", p);
    }
    const victims = entitiesNear(dim, player.location, 5, player.id);
    for (const v of victims) {
      if (!v || v.id === player.id) continue;
      try {
        v.applyDamage(10, { cause: EntityDamageCause.fire, damagingEntity: player });
        const dir = normalize({ x: v.location.x - player.location.x, y: 0, z: v.location.z - player.location.z });
        v.applyKnockback(dir.x, dir.z, 1.6, 0.6);
      } catch (e) { /* skip invincible entities */ }
    }
    player.playSound("mob.blaze.shoot", { location: player.location });
    player.onScreenDisplay.setActionBar("§c§lFlame Nova§r §7unleashed");
  } else {
    // Fireball projectile
    const spawnPos = vAdd(head, vScale(view, 1.2));
    try {
      const fb = dim.spawnEntity("minecraft:fireball", spawnPos);
      fb.applyImpulse(vScale(view, 2.5));
      if (fb.getComponent) {
        const proj = fb.getComponent("minecraft:projectile");
        if (proj) proj.owner = player;
      }
    } catch (e) {
      // fallback: trace a line of fire damage
      for (let i = 1; i <= 20; i++) {
        const step = vAdd(head, vScale(view, i));
        safeParticle(dim, "minecraft:basic_flame_particle", step);
      }
      const target = raycastEntity(player, 32);
      if (target) target.applyDamage(8, { cause: EntityDamageCause.fire, damagingEntity: player });
    }
    player.playSound("mob.ghast.fireball", { location: player.location });
    player.onScreenDisplay.setActionBar("§c§lFireball§r §7launched");
  }
}

function castWater(player) {
  const dim = player.dimension;
  const head = player.getHeadLocation();
  const view = player.getViewDirection();
  if (player.isSneaking) {
    // Aqua Restore - heal to full
    const health = player.getComponent("minecraft:health");
    if (health) {
      const max = health.effectiveMax ?? health.defaultValue ?? 20;
      health.setCurrentValue(max);
    }
    for (let i = 0; i < 24; i++) {
      const a = (Math.PI * 2 * i) / 24;
      const p = vAdd(player.location, { x: Math.cos(a) * 2, y: 1 + Math.sin(a) * 0.5, z: Math.sin(a) * 2 });
      safeParticle(dim, "minecraft:water_splash_particle", p);
    }
    player.playSound("random.splash", { location: player.location });
    player.onScreenDisplay.setActionBar("§b§lAqua Restore§r §7full HP");
  } else {
    // Tidal Lance - line AoE
    for (let i = 1; i <= 18; i++) {
      const step = vAdd(head, vScale(view, i));
      safeParticle(dim, "minecraft:water_splash_particle", step);
    }
    const victims = entitiesInCone(
      player,
      head,
      normalize(view),
      18,
      Math.cos(Math.PI / 14),
    );
    for (const v of victims) {
      try {
        v.applyDamage(9, { cause: EntityDamageCause.drowning, damagingEntity: player });
        v.applyKnockback(view.x, view.z, 1.2, 0.2);
      } catch (e) { /* ignore */ }
    }
    player.playSound("liquid.water", { location: player.location });
    player.onScreenDisplay.setActionBar("§b§lTidal Lance§r §7pierces forward");
  }
}

function castEarth(player) {
  const dim = player.dimension;
  const head = player.getHeadLocation();
  const view = player.getViewDirection();
  if (player.isSneaking) {
    // Quake Stomp - AoE damage + upward launch
    for (let a = 0; a < Math.PI * 2; a += Math.PI / 18) {
      const p = vAdd(player.location, { x: Math.cos(a) * 4, y: 0.1, z: Math.sin(a) * 4 });
      safeParticle(dim, "minecraft:basic_crit_particle", p);
    }
    const victims = entitiesNear(dim, player.location, 6, player.id);
    for (const v of victims) {
      try {
        v.applyDamage(11, { cause: EntityDamageCause.stalagmite, damagingEntity: player });
        v.applyKnockback(0, 0, 0, 1.2);
      } catch (e) { /* */ }
    }
    player.playSound("dig.stone", { location: player.location });
    player.onScreenDisplay.setActionBar("§2§lQuake Stomp§r §7shakes the earth");
  } else {
    // Stone Spike line
    for (let i = 1; i <= 8; i++) {
      const step = vAdd(player.location, vScale(horizontal(view), i));
      try {
        const loc = { x: Math.floor(step.x), y: Math.floor(step.y), z: Math.floor(step.z) };
        safeParticle(dim, "minecraft:basic_crit_particle", { x: loc.x + 0.5, y: loc.y + 1, z: loc.z + 0.5 });
      } catch (e) { /* */ }
      const victims = entitiesNear(dim, step, 1.6, player.id);
      for (const v of victims) {
        try {
          v.applyDamage(7, { cause: EntityDamageCause.stalagmite, damagingEntity: player });
          v.applyKnockback(0, 0, 0, 0.9);
        } catch (e) { /* */ }
      }
    }
    player.playSound("use.stone", { location: player.location });
    player.onScreenDisplay.setActionBar("§2§lStone Spike§r §7erupts forward");
  }
}

function castAir(player) {
  const view = player.getViewDirection();
  if (player.isSneaking) {
    // Sky Leap - big upward launch
    try { player.applyImpulse({ x: view.x * 0.8, y: 1.6, z: view.z * 0.8 }); } catch (e) { /* */ }
    for (let i = 0; i < 12; i++) {
      const p = vAdd(player.location, { x: (Math.random() - 0.5) * 2, y: i * 0.3, z: (Math.random() - 0.5) * 2 });
      safeParticle(player.dimension, "minecraft:mobflame_emitter", p);
    }
    player.playSound("mob.enderdragon.flap", { location: player.location });
    player.onScreenDisplay.setActionBar("§f§lSky Leap§r §7to the heavens");
  } else {
    // Gust dash
    try { player.applyImpulse({ x: view.x * 2.4, y: Math.max(0.3, view.y * 1.2), z: view.z * 2.4 }); } catch (e) { /* */ }
    for (let i = 1; i <= 12; i++) {
      const step = vAdd(player.location, vScale(view, i));
      safeParticle(player.dimension, "minecraft:cloud", step);
    }
    player.playSound("mob.phantom.swoop", { location: player.location });
    player.onScreenDisplay.setActionBar("§f§lGust Dash§r §7rides the wind");
  }
}

function castLightning(player) {
  const dim = player.dimension;
  if (player.isSneaking) {
    // Chain Lightning - strike up to 5 nearest
    const near = entitiesNear(dim, player.location, 18, player.id)
      .filter((e) => e.typeId !== "minecraft:player" || e.id !== player.id)
      .slice(0, 5);
    for (const t of near) {
      try {
        dim.spawnEntity("minecraft:lightning_bolt", t.location);
        t.applyDamage(8, { cause: EntityDamageCause.lightning, damagingEntity: player });
      } catch (e) { /* */ }
    }
    player.onScreenDisplay.setActionBar(`§e§lChain Lightning§r §7 ${near.length} arcs`);
  } else {
    // Thunder Strike - at aimed location
    const target = raycastEntity(player, 32);
    let loc;
    if (target) {
      loc = target.location;
      try { target.applyDamage(12, { cause: EntityDamageCause.lightning, damagingEntity: player }); } catch (e) { /* */ }
    } else {
      loc = raycastBlockLocation(player, 32);
    }
    try { dim.spawnEntity("minecraft:lightning_bolt", loc); } catch (e) { /* */ }
    player.onScreenDisplay.setActionBar("§e§lThunder Strike§r §7called");
  }
}

function castLight(player) {
  const dim = player.dimension;
  if (player.isSneaking) {
    // Radiant Pulse - damage hostile near, heal self
    for (let a = 0; a < Math.PI * 2; a += Math.PI / 12) {
      const p = vAdd(player.location, { x: Math.cos(a) * 4, y: 1, z: Math.sin(a) * 4 });
      safeParticle(dim, "minecraft:villager_happy", p);
    }
    const victims = entitiesNear(dim, player.location, 8, player.id);
    let healed = 0;
    for (const v of victims) {
      if (v.typeId === "minecraft:player") continue;
      try {
        v.applyDamage(8, { cause: EntityDamageCause.magic, damagingEntity: player });
        healed++;
      } catch (e) { /* */ }
    }
    const health = player.getComponent("minecraft:health");
    if (health) {
      const cur = health.currentValue;
      const max = health.effectiveMax ?? 20;
      health.setCurrentValue(Math.min(max, cur + 3 + healed));
    }
    player.playSound("beacon.power", { location: player.location });
    player.onScreenDisplay.setActionBar("§e§lRadiant Pulse§r §7 purifies the area");
  } else {
    // Solar Beam - single target beam
    const target = raycastEntity(player, 32);
    const head = player.getHeadLocation();
    const view = player.getViewDirection();
    for (let i = 1; i <= 22; i++) {
      const step = vAdd(head, vScale(view, i));
      safeParticle(dim, "minecraft:end_chest", step);
      safeParticle(dim, "minecraft:villager_happy", step);
    }
    if (target) {
      try {
        target.applyDamage(14, { cause: EntityDamageCause.magic, damagingEntity: player });
      } catch (e) { /* */ }
      const health = player.getComponent("minecraft:health");
      if (health) {
        const cur = health.currentValue;
        const max = health.effectiveMax ?? 20;
        health.setCurrentValue(Math.min(max, cur + 4));
      }
    }
    player.playSound("beacon.activate", { location: player.location });
    player.onScreenDisplay.setActionBar("§e§lSolar Beam§r §7pierces the dark");
  }
}

function castDark(player) {
  const dim = player.dimension;
  const head = player.getHeadLocation();
  const view = player.getViewDirection();
  if (player.isSneaking) {
    // Shadow Step - teleport forward 20
    const dest = vAdd(player.location, vScale(view, 20));
    try {
      player.teleport(dest, { dimension: dim, keepVelocity: false });
    } catch (e) { /* */ }
    for (let i = 0; i < 20; i++) {
      const step = vAdd(player.location, vScale(view, -i));
      safeParticle(dim, "minecraft:mobspell_emitter", step);
    }
    player.playSound("mob.endermen.portal", { location: player.location });
    player.onScreenDisplay.setActionBar("§5§lShadow Step§r §7through the void");
  } else {
    // Void Grasp - damage + pull self to target
    const target = raycastEntity(player, 24);
    if (target) {
      try {
        target.applyDamage(10, { cause: EntityDamageCause.magic, damagingEntity: player });
      } catch (e) { /* */ }
      const pullPos = vAdd(target.location, vScale(normalize({ x: player.location.x - target.location.x, y: 0, z: player.location.z - target.location.z }), 1.5));
      try { player.teleport(pullPos, { dimension: dim, keepVelocity: false }); } catch (e) { /* */ }
      for (let i = 1; i <= 10; i++) {
        const step = vAdd(head, vScale(view, i));
        safeParticle(dim, "minecraft:mobspell_emitter", step);
      }
      player.playSound("mob.wither.shoot", { location: player.location });
      player.onScreenDisplay.setActionBar("§5§lVoid Grasp§r §7pulls you in");
    } else {
      player.onScreenDisplay.setActionBar("§5§lVoid Grasp§r §7no target");
    }
  }
}

function castDarkScythe(player) {
  const dim = player.dimension;
  const head = player.getHeadLocation();
  const view = player.getViewDirection();
  if (player.isSneaking) {
    // Soul Reap - 4-block aoe + lifesteal per hit
    const victims = entitiesNear(dim, player.location, 4.5, player.id)
      .filter((e) => e.typeId !== "minecraft:player" || e.id !== player.id);
    let drained = 0;
    for (const v of victims) {
      try {
        v.applyDamage(9, { cause: EntityDamageCause.magic, damagingEntity: player });
        drained++;
      } catch (e) { /* */ }
    }
    const health = player.getComponent("minecraft:health");
    if (health) {
      const cur = health.currentValue;
      const max = health.effectiveMax ?? 20;
      health.setCurrentValue(Math.min(max, cur + drained * 2));
    }
    for (let i = 0; i < 16; i++) {
      const a = (Math.PI * 2 * i) / 16;
      const p = vAdd(player.location, { x: Math.cos(a) * 3, y: 1, z: Math.sin(a) * 3 });
      safeParticle(dim, "minecraft:mobspell_emitter", p);
    }
    player.playSound("mob.wither.ambient", { location: player.location });
    player.onScreenDisplay.setActionBar(`§5§lSoul Reap§r §7drained ${drained}`);
  } else {
    // Shadow Slash - cone in front
    const forward = normalize(view);
    const victims = entitiesInCone(player, head, forward, 6, Math.cos(Math.PI / 4));
    for (const v of victims) {
      try {
        v.applyDamage(12, { cause: EntityDamageCause.entityAttack, damagingEntity: player });
        v.applyKnockback(view.x, view.z, 1.4, 0.4);
      } catch (e) { /* */ }
    }
    for (let i = 1; i <= 6; i++) {
      const step = vAdd(head, vScale(view, i));
      safeParticle(dim, "minecraft:mobspell_emitter", step);
    }
    player.playSound("mob.wither.shoot", { location: player.location });
    player.onScreenDisplay.setActionBar(`§5§lShadow Slash§r §7hit ${victims.length}`);
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

// ----------------------------------------------------------------------------
// grant items
// ----------------------------------------------------------------------------
function giveItem(player, typeId, amount = 1) {
  try {
    const inv = player.getComponent("minecraft:inventory");
    if (!inv || !inv.container) return;
    const stack = new ItemStack(typeId, amount);
    const leftover = inv.container.addItem(stack);
    if (leftover) {
      player.dimension.spawnItem(leftover, player.location);
    }
  } catch (e) {
    console.warn(`giveItem failed for ${typeId}: ${e}`);
  }
}

function grantElement(player, el) {
  for (const it of el.items) giveItem(player, it, 1);
  player.sendMessage(`§${el.color}§l[Elemental Powers]§r §7Granted §${el.color}${el.label}§7 skills.`);
  player.playSound("random.levelup", { location: player.location });
}

function grantAll(player) {
  for (const el of ELEMENTS) {
    for (const it of el.items) giveItem(player, it, 1);
  }
  player.sendMessage("§d§l[Elemental Powers]§r §7All §delemental§7 skills granted.");
  player.playSound("random.levelup", { location: player.location });
}

// ----------------------------------------------------------------------------
// GUI
// ----------------------------------------------------------------------------
function openGui(player) {
  const form = new ActionFormData()
    .title("§5§lElemental Powers")
    .body(
      "§7Choose an element to §freceive its full skill kit§7.\n" +
      "§8Tap the staff to cast the primary skill. Hold §7SNEAK§8 while tapping for the secondary.\n" +
      "§5- uekermjheh on rblx"
    );
  for (const el of ELEMENTS) {
    form.button(`§${el.color}§l${el.label}§r\n§7${el.subtitle}`, el.icon);
  }
  form.button("§d§lAll Elements§r\n§7Every skill at once", "textures/items/elem_gui_tool");
  form.button("§c§lCancel", "textures/items/elem_dark_orb");

  form.show(player).then((res) => {
    if (res.canceled) return;
    const idx = res.selection;
    if (idx === undefined) return;
    if (idx < ELEMENTS.length) return grantElement(player, ELEMENTS[idx]);
    if (idx === ELEMENTS.length) return grantAll(player);
  }).catch((e) => {
    console.warn(`form error: ${e}`);
  });
}

// ----------------------------------------------------------------------------
// listeners
// ----------------------------------------------------------------------------
world.beforeEvents.chatSend.subscribe((ev) => {
  const msg = ev.message.trim().toLowerCase();
  if (msg === "/getmygui" || msg === "!getmygui") {
    ev.cancel = true;
    system.run(() => {
      openGui(ev.sender);
    });
  }
});

world.afterEvents.itemUse.subscribe((ev) => {
  const player = ev.source;
  const id = ev.itemStack?.typeId;
  if (!id || !player) return;

  if (id === `${NS}:gui_tool`) {
    system.run(() => openGui(player));
    return;
  }

  const handler = SKILL_HANDLERS[id];
  if (!handler) return;
  if (!checkCooldown(player, id)) return;
  try {
    handler(player);
  } catch (e) {
    console.warn(`skill handler error for ${id}: ${e}`);
  }
});

// passive: dark scythe melee hit = bonus magic damage + lifesteal
world.afterEvents.entityHitEntity.subscribe((ev) => {
  const attacker = ev.damagingEntity;
  const target = ev.hitEntity;
  if (!attacker || !target) return;
  if (attacker.typeId !== "minecraft:player") return;
  let mainhandId;
  try {
    const equip = attacker.getComponent("minecraft:equippable");
    const slot = equip?.getEquipment?.(EquipmentSlot.Mainhand);
    mainhandId = slot?.typeId;
  } catch (e) {
    return;
  }
  if (mainhandId !== `${NS}:dark_scythe`) return;
  try {
    target.applyDamage(4, { cause: EntityDamageCause.magic, damagingEntity: attacker });
    const health = attacker.getComponent("minecraft:health");
    if (health) {
      const cur = health.currentValue;
      const max = health.effectiveMax ?? 20;
      health.setCurrentValue(Math.min(max, cur + 2));
    }
    safeParticle(attacker.dimension, "minecraft:mobspell_emitter", target.location);
  } catch (e) { /* */ }
});

// onload
system.run(() => {
  console.log("[Elemental Powers] loaded - uekermjheh on rblx");
});
