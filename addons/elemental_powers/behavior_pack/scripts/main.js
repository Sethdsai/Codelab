/*
 * Elemental Powers v3 - Minecraft Bedrock Script API entry point.
 *
 * Flow:
 *   1. Open the GUI (/getmygui chat fallback, !getmygui, /scriptevent, or GUI Tool item).
 *   2. Pick an element -> receive ONE element orb.
 *   3. Eat the orb -> dizzy awakening (nausea + slowness + blindness + shake) for a few
 *      seconds, then the full element staff kit is granted.
 *   4. The staff has EIGHT unique skills dispatched by stance/look/environment:
 *        tap / sneak / look-up / look-down / airborne / in-water / sneak+up / sneak+down
 *
 * Description: uekermjheh on rblx
 */

import * as mc from "@minecraft/server";
import { ActionFormData } from "@minecraft/server-ui";

const { world, system, EntityDamageCause, EquipmentSlot, ItemStack } = mc;
const NS = "elempower";

// ---------------------------------------------------------------------------
// element metadata
// ---------------------------------------------------------------------------
const ELEMENTS = [
  { id: "fire", label: "Fire", color: "c", subtitle: "8 flame arts", icon: "textures/items/elem_fire_orb" },
  { id: "water", label: "Water", color: "b", subtitle: "8 tide arts", icon: "textures/items/elem_water_orb" },
  { id: "earth", label: "Earth", color: "2", subtitle: "8 stone arts", icon: "textures/items/elem_earth_orb" },
  { id: "air", label: "Air", color: "f", subtitle: "8 gale arts", icon: "textures/items/elem_air_orb" },
  { id: "lightning", label: "Lightning", color: "e", subtitle: "8 storm arts", icon: "textures/items/elem_lightning_orb" },
  { id: "light", label: "Light", color: "g", subtitle: "8 radiant arts", icon: "textures/items/elem_light_orb" },
  { id: "dark", label: "Dark", color: "5", subtitle: "8 shadow arts + Dark Scythe", icon: "textures/items/elem_dark_orb" },
];

const ELEMENT_BY_ID = Object.fromEntries(ELEMENTS.map((e) => [e.id, e]));

const ORB_TO_ELEMENT = Object.fromEntries(ELEMENTS.map((e) => [`${NS}:${e.id}_orb`, e.id]));
const ELEMENT_TO_STAFF = Object.fromEntries(ELEMENTS.map((e) => [e.id, `${NS}:${e.id}_staff`]));

// ---------------------------------------------------------------------------
// cooldowns (in-memory)
// ---------------------------------------------------------------------------
/** @type {Map<string, Map<string, number>>} */
const COOLDOWNS = new Map();

function getCooldown(player, key) {
  const perPlayer = COOLDOWNS.get(player.id);
  return perPlayer ? perPlayer.get(key) : undefined;
}

function setCooldown(player, key) {
  let perPlayer = COOLDOWNS.get(player.id);
  if (!perPlayer) { perPlayer = new Map(); COOLDOWNS.set(player.id, perPlayer); }
  perPlayer.set(key, system.currentTick);
}

function checkCooldownTicks(player, key, ticks) {
  const last = getCooldown(player, key);
  const now = system.currentTick;
  if (typeof last === "number" && now - last < ticks) {
    const remaining = ((ticks - (now - last)) / 20).toFixed(1);
    tryActionBar(player, `§c§lCooldown §7${remaining}s`);
    return false;
  }
  setCooldown(player, key);
  return true;
}

function tryActionBar(player, text) { try { player.onScreenDisplay.setActionBar(text); } catch (e) { /* */ } }

try { world.afterEvents.playerLeave.subscribe((ev) => { COOLDOWNS.delete(ev.playerId); }); } catch (e) { /* */ }

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
    for (const h of hits || []) if (h && h.entity && h.entity.id !== player.id) return h.entity;
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
  } catch (e) { return []; }
}

function entitiesInCone(player, origin, forward, maxDistance, cosAngle) {
  const out = [];
  for (const e of entitiesNear(player.dimension, origin, maxDistance, player.id)) {
    const to = { x: e.location.x - origin.x, y: e.location.y - origin.y, z: e.location.z - origin.z };
    if (vLen(to) < 0.01) continue;
    const n = vNorm(to);
    if (n.x * forward.x + n.y * forward.y + n.z * forward.z >= cosAngle) out.push(e);
  }
  return out;
}

function safeParticle(dimension, id, loc) { try { dimension.spawnParticle(id, loc); } catch (e) { /* */ } }

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

function applyKnock(entity, dirX, dirZ, hStrength, vStrength) {
  try { entity.applyKnockback(dirX, dirZ, hStrength, vStrength); } catch (e) { /* */ }
}

function tryImpulse(entity, v) { try { entity.applyImpulse(v); } catch (e) { /* */ } }

function addFx(player, effect, ticks, amp) {
  try { player.addEffect(effect, ticks, { amplifier: amp ?? 0, showParticles: false }); } catch (e) { /* */ }
}

function removeFx(player, effect) {
  try { player.removeEffect(effect); } catch (e) { /* */ }
}

function runCmd(source, cmd) {
  try { source.runCommand(cmd); } catch (e) { /* */ }
}

function isInWater(player) {
  try { if (typeof player.isInWater === "boolean") return player.isInWater; } catch (e) { /* */ }
  return false;
}

function isOnGround(player) {
  try { if (typeof player.isOnGround === "boolean") return player.isOnGround; } catch (e) { /* */ }
  return true;
}

// ---------------------------------------------------------------------------
// input classification -> 8 skill slots per element
// ---------------------------------------------------------------------------
function classifyInput(player) {
  const view = player.getViewDirection();
  const sneak = player.isSneaking;
  const up = view.y > 0.7;
  const down = view.y < -0.7;
  if (sneak && up) return "sneak_up";
  if (sneak && down) return "sneak_down";
  if (sneak) return "sneak";
  if (up) return "up";
  if (isInWater(player)) return "water";
  if (!isOnGround(player)) return "air";
  if (down) return "down";
  return "tap";
}

const SKILL_COOLDOWNS = {
  tap: 14, sneak: 28, up: 45, down: 30, air: 25, water: 30, sneak_up: 120, sneak_down: 70,
};

function dispatchStaff(player, itemId, handlers) {
  const mode = classifyInput(player);
  const cdKey = `${itemId}:${mode}`;
  const ticks = SKILL_COOLDOWNS[mode] ?? 20;
  if (!checkCooldownTicks(player, cdKey, ticks)) return;
  const fn = handlers[mode] || handlers.tap;
  try { fn(player); } catch (e) {
    try { console.warn(`skill error ${itemId}/${mode}: ${e}`); } catch (_) { /* */ }
  }
}

// ---------------------------------------------------------------------------
// FIRE - 8 skills
// ---------------------------------------------------------------------------
const fireSkills = {
  tap(player) {
    const dim = player.dimension;
    const head = player.getHeadLocation();
    const view = player.getViewDirection();
    let ok = false;
    try {
      const fb = dim.spawnEntity("minecraft:fireball", vAdd(head, vScale(view, 1.2)));
      fb.applyImpulse(vScale(view, 2.5));
      ok = true;
    } catch (e) { /* */ }
    if (!ok) {
      for (let i = 1; i <= 24; i++) safeParticle(dim, "minecraft:basic_flame_particle", vAdd(head, vScale(view, i)));
      const t = raycastEntity(player, 40);
      if (t) damage(t, 10, player, EntityDamageCause.fire);
    }
    try { player.playSound("mob.ghast.fireball"); } catch (e) { /* */ }
    tryActionBar(player, "§c§lFireball");
  },
  sneak(player) {
    const dim = player.dimension;
    for (let r = 1; r <= 4; r++) {
      for (let a = 0; a < Math.PI * 2; a += Math.PI / (6 * r)) {
        safeParticle(dim, "minecraft:basic_flame_particle",
          vAdd(player.location, { x: Math.cos(a) * r, y: 0.4, z: Math.sin(a) * r }));
      }
    }
    for (const v of entitiesNear(dim, player.location, 5, player.id)) {
      damage(v, 12, player, EntityDamageCause.fire);
      const d = vNorm({ x: v.location.x - player.location.x, y: 0, z: v.location.z - player.location.z });
      applyKnock(v, d.x, d.z, 1.6, 0.6);
    }
    try { player.playSound("mob.blaze.shoot"); } catch (e) { /* */ }
    tryActionBar(player, "§c§lFlame Nova");
  },
  up(player) {
    const dim = player.dimension;
    const aim = raycastBlockLocation(player, 35);
    for (let i = 0; i < 5; i++) {
      const spot = vAdd(aim, { x: (Math.random() - 0.5) * 6, y: 10 + i * 2, z: (Math.random() - 0.5) * 6 });
      for (let k = 0; k < 10; k++) {
        safeParticle(dim, "minecraft:basic_flame_particle",
          vAdd(spot, { x: 0, y: -k, z: 0 }));
      }
      const impact = vAdd(aim, { x: (Math.random() - 0.5) * 6, y: 0, z: (Math.random() - 0.5) * 6 });
      for (const v of entitiesNear(dim, impact, 3, player.id)) {
        damage(v, 7, player, EntityDamageCause.fire);
      }
    }
    try { player.playSound("random.explode"); } catch (e) { /* */ }
    tryActionBar(player, "§c§lMeteor Rain");
  },
  down(player) {
    const dim = player.dimension;
    for (let a = 0; a < Math.PI * 2; a += Math.PI / 12) {
      const p = vAdd(player.location, { x: Math.cos(a) * 3, y: 0.1, z: Math.sin(a) * 3 });
      safeParticle(dim, "minecraft:basic_flame_particle", p);
    }
    for (const v of entitiesNear(dim, player.location, 4, player.id)) {
      damage(v, 8, player, EntityDamageCause.fire);
      applyKnock(v, 0, 0, 0, 0.8);
    }
    runCmd(player, `fill ~-1 ~-1 ~-1 ~1 ~-1 ~1 fire 0 replace air`);
    tryActionBar(player, "§c§lLava Pool");
  },
  air(player) {
    const view = player.getViewDirection();
    tryImpulse(player, { x: view.x * 3, y: 0.2, z: view.z * 3 });
    for (let i = 1; i <= 14; i++) safeParticle(player.dimension, "minecraft:basic_flame_particle", vAdd(player.location, vScale(view, i)));
    const t = raycastEntity(player, 8);
    if (t) damage(t, 9, player, EntityDamageCause.fire);
    try { player.playSound("mob.ghast.fireball"); } catch (e) { /* */ }
    tryActionBar(player, "§c§lFire Dash");
  },
  water(player) {
    const dim = player.dimension;
    for (let a = 0; a < Math.PI * 2; a += Math.PI / 16) {
      safeParticle(dim, "minecraft:water_splash_particle",
        vAdd(player.location, { x: Math.cos(a) * 4, y: 1, z: Math.sin(a) * 4 }));
    }
    for (const v of entitiesNear(dim, player.location, 5, player.id)) {
      damage(v, 11, player, EntityDamageCause.magic);
      const d = vNorm({ x: v.location.x - player.location.x, y: 0.4, z: v.location.z - player.location.z });
      applyKnock(v, d.x, d.z, 1.8, 0.8);
    }
    tryActionBar(player, "§c§lSteam Burst");
  },
  sneak_up(player) {
    const dim = player.dimension;
    const base = player.location;
    for (let a = 0; a < Math.PI * 2; a += Math.PI / 4) {
      const column = vAdd(base, { x: Math.cos(a) * 4, y: 0, z: Math.sin(a) * 4 });
      for (let y = 0; y < 6; y++) {
        safeParticle(dim, "minecraft:basic_flame_particle", vAdd(column, { x: 0, y, z: 0 }));
      }
      for (const v of entitiesNear(dim, column, 2, player.id)) {
        damage(v, 14, player, EntityDamageCause.fire);
      }
    }
    try { player.playSound("mob.ghast.scream"); } catch (e) { /* */ }
    tryActionBar(player, "§c§l§nInferno");
  },
  sneak_down(player) {
    const dim = player.dimension;
    tryImpulse(player, { x: 0, y: 1.6, z: 0 });
    system.runTimeout(() => {
      for (let a = 0; a < Math.PI * 2; a += Math.PI / 18) {
        safeParticle(dim, "minecraft:basic_flame_particle",
          vAdd(player.location, { x: Math.cos(a) * 5, y: 0.2, z: Math.sin(a) * 5 }));
      }
      for (const v of entitiesNear(dim, player.location, 6, player.id)) {
        damage(v, 18, player, EntityDamageCause.fire);
        applyKnock(v, 0, 0, 0, 1.2);
      }
      try { player.playSound("random.explode"); } catch (e) { /* */ }
    }, 20);
    tryActionBar(player, "§c§l§nPhoenix Dive");
  },
};

// ---------------------------------------------------------------------------
// WATER - 8 skills
// ---------------------------------------------------------------------------
const waterSkills = {
  tap(player) {
    const dim = player.dimension;
    const head = player.getHeadLocation();
    const view = player.getViewDirection();
    for (let i = 1; i <= 20; i++) safeParticle(dim, "minecraft:water_splash_particle", vAdd(head, vScale(view, i)));
    for (const v of entitiesInCone(player, head, vNorm(view), 20, Math.cos(Math.PI / 14))) {
      damage(v, 10, player, EntityDamageCause.magic);
      applyKnock(v, view.x, view.z, 1.3, 0.3);
    }
    tryActionBar(player, "§b§lTidal Lance");
  },
  sneak(player) {
    healPlayer(player, 20);
    for (let i = 0; i < 24; i++) {
      const a = (Math.PI * 2 * i) / 24;
      safeParticle(player.dimension, "minecraft:water_splash_particle",
        vAdd(player.location, { x: Math.cos(a) * 2, y: 1 + Math.sin(a) * 0.5, z: Math.sin(a) * 2 }));
    }
    try { player.playSound("random.splash"); } catch (e) { /* */ }
    tryActionBar(player, "§b§lAqua Restore");
  },
  up(player) {
    const dim = player.dimension;
    for (const v of entitiesNear(dim, player.location, 10, player.id)) {
      if (v.typeId === "minecraft:player") { healPlayer(v, 8); continue; }
      damage(v, 6, player, EntityDamageCause.magic);
    }
    for (let i = 0; i < 20; i++) {
      const a = Math.random() * Math.PI * 2;
      safeParticle(dim, "minecraft:water_splash_particle",
        vAdd(player.location, { x: Math.cos(a) * 5, y: 4 + Math.random() * 2, z: Math.sin(a) * 5 }));
    }
    tryActionBar(player, "§b§lRain Heal");
  },
  down(player) {
    const dim = player.dimension;
    for (const v of entitiesNear(dim, player.location, 6, player.id)) {
      const pullPos = vAdd(player.location, { x: 0, y: 0.5, z: 0 });
      try { v.teleport(pullPos, { dimension: dim }); } catch (e) { /* */ }
      damage(v, 9, player, EntityDamageCause.drowning || EntityDamageCause.magic);
    }
    for (let a = 0; a < Math.PI * 2; a += Math.PI / 16) {
      safeParticle(dim, "minecraft:water_splash_particle",
        vAdd(player.location, { x: Math.cos(a) * 3, y: 0.5, z: Math.sin(a) * 3 }));
    }
    tryActionBar(player, "§b§lWhirlpool");
  },
  air(player) {
    const view = player.getViewDirection();
    tryImpulse(player, { x: view.x * 2, y: -0.6, z: view.z * 2 });
    for (let i = 1; i <= 10; i++) safeParticle(player.dimension, "minecraft:water_splash_particle", vAdd(player.location, vScale(view, i)));
    tryActionBar(player, "§b§lWater Slide");
  },
  water(player) {
    const dim = player.dimension;
    healPlayer(player, 6);
    addFx(player, "speed", 80, 2);
    addFx(player, "water_breathing", 200, 0);
    for (let i = 0; i < 12; i++) {
      safeParticle(dim, "minecraft:water_splash_particle",
        vAdd(player.location, { x: (Math.random() - 0.5) * 2, y: Math.random() * 2, z: (Math.random() - 0.5) * 2 }));
    }
    tryActionBar(player, "§b§lTide Blessing");
  },
  sneak_up(player) {
    const dim = player.dimension;
    for (let r = 1; r <= 9; r++) {
      for (let a = 0; a < Math.PI * 2; a += Math.PI / (4 * r)) {
        safeParticle(dim, "minecraft:water_splash_particle",
          vAdd(player.location, { x: Math.cos(a) * r, y: 1, z: Math.sin(a) * r }));
      }
    }
    for (const v of entitiesNear(dim, player.location, 11, player.id)) {
      damage(v, 18, player, EntityDamageCause.magic);
      const d = vNorm({ x: v.location.x - player.location.x, y: 0, z: v.location.z - player.location.z });
      applyKnock(v, d.x, d.z, 2.8, 0.8);
    }
    healPlayer(player, 10);
    try { player.playSound("ambient.weather.rain"); } catch (e) { /* */ }
    tryActionBar(player, "§b§l§nTsunami");
  },
  sneak_down(player) {
    const dim = player.dimension;
    for (const v of entitiesNear(dim, player.location, 7, player.id)) {
      damage(v, 10, player, EntityDamageCause.magic);
      addFx(v, "slowness", 100, 3);
    }
    for (let a = 0; a < Math.PI * 2; a += Math.PI / 16) {
      safeParticle(dim, "minecraft:snowflake",
        vAdd(player.location, { x: Math.cos(a) * 4, y: 0.8, z: Math.sin(a) * 4 }));
    }
    tryActionBar(player, "§b§l§nFrost Nova");
  },
};

// ---------------------------------------------------------------------------
// EARTH - 8 skills
// ---------------------------------------------------------------------------
const earthSkills = {
  tap(player) {
    const dim = player.dimension;
    const view = player.getViewDirection();
    for (let i = 1; i <= 9; i++) {
      const step = vAdd(player.location, vScale(vHoriz(view), i));
      safeParticle(dim, "minecraft:basic_crit_particle", { x: step.x, y: step.y + 1, z: step.z });
      for (const v of entitiesNear(dim, step, 1.6, player.id)) {
        damage(v, 8, player, EntityDamageCause.entityAttack);
        applyKnock(v, 0, 0, 0, 1.0);
      }
    }
    try { player.playSound("dig.stone"); } catch (e) { /* */ }
    tryActionBar(player, "§2§lStone Spike");
  },
  sneak(player) {
    const dim = player.dimension;
    for (let r = 1; r <= 4; r++) {
      for (let a = 0; a < Math.PI * 2; a += Math.PI / (6 * r)) {
        safeParticle(dim, "minecraft:basic_crit_particle",
          vAdd(player.location, { x: Math.cos(a) * r, y: 0.1, z: Math.sin(a) * r }));
      }
    }
    for (const v of entitiesNear(dim, player.location, 6, player.id)) {
      damage(v, 12, player, EntityDamageCause.entityAttack);
      applyKnock(v, 0, 0, 0, 1.3);
    }
    try { player.playSound("dig.stone"); } catch (e) { /* */ }
    tryActionBar(player, "§2§lQuake Stomp");
  },
  up(player) {
    const dim = player.dimension;
    const target = raycastEntity(player, 32);
    if (target) {
      damage(target, 16, player, EntityDamageCause.entityAttack);
      applyKnock(target, 0, 0, 0, 1.8);
      for (let i = 0; i < 8; i++) safeParticle(dim, "minecraft:basic_crit_particle",
        vAdd(target.location, { x: (Math.random() - 0.5) * 1, y: i * 0.5, z: (Math.random() - 0.5) * 1 }));
    }
    tryActionBar(player, "§2§lBoulder Toss");
  },
  down(player) {
    const dim = player.dimension;
    const view = player.getViewDirection();
    const fwd = vHoriz(view);
    for (let i = 1; i <= 10; i++) {
      const p = vAdd(player.location, vScale(fwd, i));
      safeParticle(dim, "minecraft:basic_crit_particle", p);
      for (const v of entitiesNear(dim, p, 1.2, player.id)) {
        damage(v, 7, player, EntityDamageCause.entityAttack);
        applyKnock(v, 0, 0, 0, 1.2);
      }
    }
    tryActionBar(player, "§2§lFissure");
  },
  air(player) {
    const dim = player.dimension;
    tryImpulse(player, { x: 0, y: -2.2, z: 0 });
    system.runTimeout(() => {
      for (let a = 0; a < Math.PI * 2; a += Math.PI / 12) {
        safeParticle(dim, "minecraft:basic_crit_particle",
          vAdd(player.location, { x: Math.cos(a) * 4, y: 0.2, z: Math.sin(a) * 4 }));
      }
      for (const v of entitiesNear(dim, player.location, 5, player.id)) {
        damage(v, 14, player, EntityDamageCause.entityAttack);
        applyKnock(v, 0, 0, 0, 1.4);
      }
      try { player.playSound("dig.stone"); } catch (e) { /* */ }
    }, 10);
    tryActionBar(player, "§2§lEarth Fall");
  },
  water(player) {
    const dim = player.dimension;
    for (const v of entitiesNear(dim, player.location, 5, player.id)) {
      damage(v, 9, player, EntityDamageCause.entityAttack);
      addFx(v, "slowness", 120, 4);
    }
    for (let a = 0; a < Math.PI * 2; a += Math.PI / 12) {
      safeParticle(dim, "minecraft:basic_crit_particle",
        vAdd(player.location, { x: Math.cos(a) * 3, y: 0.5, z: Math.sin(a) * 3 }));
    }
    tryActionBar(player, "§2§lMud Trap");
  },
  sneak_up(player) {
    const dim = player.dimension;
    const view = player.getViewDirection();
    for (let n = 0; n < 6; n++) {
      const spot = vAdd(player.location, vScale(vHoriz(view), 3 + n * 1.5));
      for (let y = 0; y < 5; y++) {
        safeParticle(dim, "minecraft:basic_crit_particle", vAdd(spot, { x: 0, y, z: 0 }));
      }
      for (const v of entitiesNear(dim, spot, 2, player.id)) {
        damage(v, 10, player, EntityDamageCause.entityAttack);
        applyKnock(v, 0, 0, 0, 1.1);
      }
    }
    try { player.playSound("dig.stone"); } catch (e) { /* */ }
    tryActionBar(player, "§2§l§nMountain Rise");
  },
  sneak_down(player) {
    const dim = player.dimension;
    for (let r = 1; r <= 7; r++) {
      for (let a = 0; a < Math.PI * 2; a += Math.PI / (3 * r)) {
        safeParticle(dim, "minecraft:basic_crit_particle",
          vAdd(player.location, { x: Math.cos(a) * r, y: 0.1, z: Math.sin(a) * r }));
      }
    }
    for (const v of entitiesNear(dim, player.location, 9, player.id)) {
      damage(v, 20, player, EntityDamageCause.entityAttack);
      applyKnock(v, 0, 0, 0, 1.8);
    }
    try { player.playSound("dig.stone"); } catch (e) { /* */ }
    tryActionBar(player, "§2§l§nEarthquake");
  },
};

// ---------------------------------------------------------------------------
// AIR - 8 skills
// ---------------------------------------------------------------------------
const airSkills = {
  tap(player) {
    const view = player.getViewDirection();
    tryImpulse(player, { x: view.x * 2.4, y: Math.max(0.3, view.y * 1.2), z: view.z * 2.4 });
    for (let i = 1; i <= 12; i++) safeParticle(player.dimension, "minecraft:cloud", vAdd(player.location, vScale(view, i)));
    tryActionBar(player, "§f§lGust Dash");
  },
  sneak(player) {
    tryImpulse(player, { x: 0, y: 2.0, z: 0 });
    for (let i = 0; i < 12; i++) {
      safeParticle(player.dimension, "minecraft:cloud",
        vAdd(player.location, { x: (Math.random() - 0.5) * 2, y: i * 0.3, z: (Math.random() - 0.5) * 2 }));
    }
    tryActionBar(player, "§f§lSky Leap");
  },
  up(player) {
    const dim = player.dimension;
    for (const v of entitiesNear(dim, player.location, 8, player.id)) {
      const inDir = vNorm({ x: player.location.x - v.location.x, y: 0, z: player.location.z - v.location.z });
      applyKnock(v, inDir.x, inDir.z, 0.8, 1.6);
      damage(v, 8, player, EntityDamageCause.magic);
    }
    for (let i = 0; i < 24; i++) {
      const a = Math.random() * Math.PI * 2;
      safeParticle(dim, "minecraft:cloud",
        vAdd(player.location, { x: Math.cos(a) * 3, y: i * 0.2, z: Math.sin(a) * 3 }));
    }
    tryActionBar(player, "§f§lTornado");
  },
  down(player) {
    const dim = player.dimension;
    const view = player.getViewDirection();
    const fwd = vHoriz(view);
    for (let i = 1; i <= 10; i++) {
      const p = vAdd(player.location, vScale(fwd, i));
      safeParticle(dim, "minecraft:cloud", p);
      for (const v of entitiesNear(dim, p, 1.3, player.id)) {
        damage(v, 8, player, EntityDamageCause.magic);
        applyKnock(v, fwd.x, fwd.z, 2.2, -0.2);
      }
    }
    tryActionBar(player, "§f§lPressure Wave");
  },
  air(player) {
    tryImpulse(player, { x: 0, y: 0.8, z: 0 });
    for (let i = 0; i < 10; i++) {
      safeParticle(player.dimension, "minecraft:cloud",
        vAdd(player.location, { x: (Math.random() - 0.5) * 1.5, y: (Math.random() - 0.5) * 1.5, z: (Math.random() - 0.5) * 1.5 }));
    }
    tryActionBar(player, "§f§lHover");
  },
  water(player) {
    const dim = player.dimension;
    for (const v of entitiesNear(dim, player.location, 4, player.id)) {
      damage(v, 7, player, EntityDamageCause.magic);
      const d = vNorm({ x: v.location.x - player.location.x, y: 0.5, z: v.location.z - player.location.z });
      applyKnock(v, d.x, d.z, 1.5, 0.8);
    }
    addFx(player, "water_breathing", 200, 0);
    for (let a = 0; a < Math.PI * 2; a += Math.PI / 12) {
      safeParticle(dim, "minecraft:cloud",
        vAdd(player.location, { x: Math.cos(a) * 2, y: 0.8, z: Math.sin(a) * 2 }));
    }
    tryActionBar(player, "§f§lAir Bubble");
  },
  sneak_up(player) {
    const dim = player.dimension;
    for (const v of entitiesNear(dim, player.location, 10, player.id)) {
      const inDir = vNorm({ x: player.location.x - v.location.x, y: 0, z: player.location.z - v.location.z });
      applyKnock(v, inDir.x, inDir.z, 1.8, 2.2);
      damage(v, 14, player, EntityDamageCause.magic);
    }
    for (let i = 0; i < 40; i++) {
      const a = (Math.PI * 2 * i) / 20;
      safeParticle(dim, "minecraft:cloud",
        vAdd(player.location, { x: Math.cos(a) * 4, y: (i / 40) * 8, z: Math.sin(a) * 4 }));
    }
    tryActionBar(player, "§f§l§nHurricane");
  },
  sneak_down(player) {
    const dim = player.dimension;
    const view = player.getViewDirection();
    tryImpulse(player, { x: view.x * 2, y: -2.4, z: view.z * 2 });
    system.runTimeout(() => {
      for (let a = 0; a < Math.PI * 2; a += Math.PI / 10) {
        safeParticle(dim, "minecraft:cloud",
          vAdd(player.location, { x: Math.cos(a) * 5, y: 0.2, z: Math.sin(a) * 5 }));
      }
      for (const v of entitiesNear(dim, player.location, 6, player.id)) {
        damage(v, 16, player, EntityDamageCause.magic);
        const d = vNorm({ x: v.location.x - player.location.x, y: 0, z: v.location.z - player.location.z });
        applyKnock(v, d.x, d.z, 2.2, 0.3);
      }
    }, 10);
    tryActionBar(player, "§f§l§nWind Slam");
  },
};

// ---------------------------------------------------------------------------
// LIGHTNING - 8 skills
// ---------------------------------------------------------------------------
// v6 flagship skill: Lightning Chain. Picks the mob you're aiming at, draws
// a trail of custom elempower:chain_link particles between you and it for 4s,
// tags the mob 'elempower_chained'. If the mob dies while chained, a burial
// effect (explosion + dirt fill under feet) fires from the entityDie listener.
// If it survives 4s, the chain fades and the tag is removed.
const CHAIN_DURATION_TICKS = 80;
const CHAIN_RANGE = 14;

function castLightningChain(player) {
  const dim = player.dimension;
  let target;
  try {
    const ray = player.getEntitiesFromViewDirection({ maxDistance: CHAIN_RANGE });
    if (ray && ray.length) {
      for (const hit of ray) {
        const e = hit.entity;
        if (e && e.typeId !== "minecraft:player" && e.isValid && e.isValid()) { target = e; break; }
      }
    }
  } catch (e) { /* */ }
  if (!target) {
    try { player.onScreenDisplay.setActionBar("§e§lLightning Chain §7- §cno target in sight"); } catch (e) { /* */ }
    return;
  }

  try { target.addTag("elempower_chained"); } catch (e) { /* */ }
  try { player.playSound("mob.creeper.say"); } catch (e) { /* */ }
  damage(target, 8, player, EntityDamageCause.lightning);

  let elapsed = 0;
  const handle = system.runInterval(() => {
    elapsed += 2;
    let alive = false;
    try { alive = target && target.isValid && target.isValid(); } catch (e) { alive = false; }
    if (!alive || elapsed >= CHAIN_DURATION_TICKS) {
      try { system.clearRun(handle); } catch (e) { /* */ }
      try { if (target && target.hasTag && target.hasTag("elempower_chained")) target.removeTag("elempower_chained"); } catch (e) { /* */ }
      return;
    }
    const pLoc = player.location;
    const tLoc = target.location;
    const dx = tLoc.x - pLoc.x, dy = (tLoc.y + 1) - (pLoc.y + 1.2), dz = tLoc.z - pLoc.z;
    const steps = 14;
    for (let i = 0; i <= steps; i++) {
      const t = i / steps;
      const jitter = 0.08;
      const loc = {
        x: pLoc.x + dx * t + (Math.random() - 0.5) * jitter,
        y: pLoc.y + 1.2 + dy * t + (Math.random() - 0.5) * jitter,
        z: pLoc.z + dz * t + (Math.random() - 0.5) * jitter,
      };
      safeParticle(dim, "elempower:chain_link", loc);
    }
    if (elapsed % 10 === 0) {
      try { target.applyKnockback(0, 0, 0, -0.1); } catch (e) { /* */ }
    }
  }, 2);
}

const lightningSkills = {
  tap(player) {
    castLightningChain(player);
  },
  sneak(player) {
    const near = entitiesNear(player.dimension, player.location, 20, player.id).slice(0, 5);
    for (const t of near) {
      try { player.dimension.spawnEntity("minecraft:lightning_bolt", t.location); } catch (e) { /* */ }
      damage(t, 9, player, EntityDamageCause.lightning);
    }
    tryActionBar(player, `§e§lChain Lightning §7 ${near.length}`);
  },
  up(player) {
    const dim = player.dimension;
    const hits = entitiesNear(dim, player.location, 15, player.id);
    for (let i = 0; i < 6; i++) {
      const target = hits[Math.floor(Math.random() * Math.max(1, hits.length))] || player;
      const spot = vAdd(target.location, { x: (Math.random() - 0.5) * 4, y: 0, z: (Math.random() - 0.5) * 4 });
      try { dim.spawnEntity("minecraft:lightning_bolt", spot); } catch (e) { /* */ }
      for (const v of entitiesNear(dim, spot, 2.5, player.id)) {
        damage(v, 6, player, EntityDamageCause.lightning);
      }
    }
    tryActionBar(player, "§e§lThunder Cloud");
  },
  down(player) {
    const dim = player.dimension;
    try { dim.spawnEntity("minecraft:lightning_bolt", player.location); } catch (e) { /* */ }
    for (const v of entitiesNear(dim, player.location, 5, player.id)) {
      damage(v, 12, player, EntityDamageCause.lightning);
      applyKnock(v, 0, 0, 0, 0.8);
    }
    tryActionBar(player, "§e§lGround Shock");
  },
  air(player) {
    const view = player.getViewDirection();
    tryImpulse(player, { x: view.x * 3, y: 0.3, z: view.z * 3 });
    const dim = player.dimension;
    for (let i = 1; i <= 8; i++) {
      const p = vAdd(player.location, vScale(view, i));
      try { dim.spawnEntity("minecraft:lightning_bolt", p); } catch (e) { /* */ }
      for (const v of entitiesNear(dim, p, 2, player.id)) damage(v, 8, player, EntityDamageCause.lightning);
    }
    tryActionBar(player, "§e§lLightning Dash");
  },
  water(player) {
    const dim = player.dimension;
    for (const v of entitiesNear(dim, player.location, 6, player.id)) {
      try { dim.spawnEntity("minecraft:lightning_bolt", v.location); } catch (e) { /* */ }
      damage(v, 14, player, EntityDamageCause.lightning);
    }
    tryActionBar(player, "§e§lStatic Discharge");
  },
  sneak_up(player) {
    const dim = player.dimension;
    const near = entitiesNear(dim, player.location, 25, player.id).slice(0, 10);
    for (const t of near) {
      try { dim.spawnEntity("minecraft:lightning_bolt", t.location); } catch (e) { /* */ }
      damage(t, 16, player, EntityDamageCause.lightning);
    }
    for (let i = 0; i < 12; i++) {
      const a = Math.random() * Math.PI * 2;
      const r = Math.random() * 10;
      try { dim.spawnEntity("minecraft:lightning_bolt",
        vAdd(player.location, { x: Math.cos(a) * r, y: 0, z: Math.sin(a) * r })); } catch (e) { /* */ }
    }
    tryActionBar(player, `§e§l§nThunder Storm §7 ${near.length}`);
  },
  sneak_down(player) {
    const dim = player.dimension;
    for (let r = 1; r <= 5; r++) {
      for (let a = 0; a < Math.PI * 2; a += Math.PI / (5 * r)) {
        const p = vAdd(player.location, { x: Math.cos(a) * r, y: 0.1, z: Math.sin(a) * r });
        safeParticle(dim, "minecraft:critical_hit_emitter", p);
      }
    }
    for (const v of entitiesNear(dim, player.location, 6, player.id)) {
      try { dim.spawnEntity("minecraft:lightning_bolt", v.location); } catch (e) { /* */ }
      damage(v, 18, player, EntityDamageCause.lightning);
    }
    tryActionBar(player, "§e§l§nIon Surge");
  },
};

// ---------------------------------------------------------------------------
// LIGHT - 8 skills
// ---------------------------------------------------------------------------
const lightSkills = {
  tap(player) {
    const dim = player.dimension;
    const head = player.getHeadLocation();
    const view = player.getViewDirection();
    for (let i = 1; i <= 22; i++) safeParticle(dim, "minecraft:villager_happy", vAdd(head, vScale(view, i)));
    const target = raycastEntity(player, 32);
    if (target) { damage(target, 14, player, EntityDamageCause.magic); healPlayer(player, 4); }
    try { player.playSound("beacon.activate"); } catch (e) { /* */ }
    tryActionBar(player, "§e§lSolar Beam");
  },
  sneak(player) {
    const dim = player.dimension;
    for (let a = 0; a < Math.PI * 2; a += Math.PI / 12) {
      safeParticle(dim, "minecraft:villager_happy",
        vAdd(player.location, { x: Math.cos(a) * 4, y: 1, z: Math.sin(a) * 4 }));
    }
    let hit = 0;
    for (const v of entitiesNear(dim, player.location, 8, player.id)) {
      if (v.typeId === "minecraft:player") continue;
      damage(v, 9, player, EntityDamageCause.magic);
      hit++;
    }
    healPlayer(player, 4 + hit);
    try { player.playSound("beacon.power"); } catch (e) { /* */ }
    tryActionBar(player, "§e§lRadiant Pulse");
  },
  up(player) {
    const dim = player.dimension;
    let hit = 0;
    for (const v of entitiesNear(dim, player.location, 18, player.id)) {
      if (v.typeId === "minecraft:player") continue;
      damage(v, 11, player, EntityDamageCause.magic);
      addFx(v, "blindness", 60, 0);
      hit++;
    }
    for (let i = 0; i < 30; i++) {
      const a = Math.random() * Math.PI * 2;
      safeParticle(dim, "minecraft:villager_happy",
        vAdd(player.location, { x: Math.cos(a) * 6, y: 3 + Math.random() * 3, z: Math.sin(a) * 6 }));
    }
    try { player.playSound("beacon.power"); } catch (e) { /* */ }
    tryActionBar(player, `§e§lDivine Judgement §7 ${hit}`);
  },
  down(player) {
    const dim = player.dimension;
    for (let a = 0; a < Math.PI * 2; a += Math.PI / 12) {
      safeParticle(dim, "minecraft:villager_happy",
        vAdd(player.location, { x: Math.cos(a) * 4, y: 0.2, z: Math.sin(a) * 4 }));
    }
    for (const v of entitiesNear(dim, player.location, 4, player.id)) {
      if (v.typeId === "minecraft:player") healPlayer(v, 10);
    }
    addFx(player, "regeneration", 120, 1);
    tryActionBar(player, "§e§lHoly Ground");
  },
  air(player) {
    const view = player.getViewDirection();
    tryImpulse(player, { x: view.x * 2, y: 0.8, z: view.z * 2 });
    addFx(player, "slow_falling", 120, 0);
    for (let i = 0; i < 8; i++) safeParticle(player.dimension, "minecraft:villager_happy", vAdd(player.location, vScale(view, i)));
    tryActionBar(player, "§e§lLight Step");
  },
  water(player) {
    const dim = player.dimension;
    healPlayer(player, 10);
    addFx(player, "water_breathing", 200, 0);
    removeFx(player, "poison");
    removeFx(player, "wither");
    for (let a = 0; a < Math.PI * 2; a += Math.PI / 16) {
      safeParticle(dim, "minecraft:villager_happy",
        vAdd(player.location, { x: Math.cos(a) * 3, y: 1, z: Math.sin(a) * 3 }));
    }
    tryActionBar(player, "§e§lPurify");
  },
  sneak_up(player) {
    const dim = player.dimension;
    let hit = 0;
    for (const v of entitiesNear(dim, player.location, 16, player.id)) {
      if (v.typeId === "minecraft:player") { healPlayer(v, 20); continue; }
      damage(v, 22, player, EntityDamageCause.magic);
      hit++;
    }
    healPlayer(player, 20);
    addFx(player, "resistance", 140, 1);
    for (let a = 0; a < Math.PI * 2; a += Math.PI / 8) {
      for (let r = 1; r <= 6; r++) {
        safeParticle(dim, "minecraft:villager_happy",
          vAdd(player.location, { x: Math.cos(a) * r, y: 1 + r * 0.2, z: Math.sin(a) * r }));
      }
    }
    try { player.playSound("beacon.power"); } catch (e) { /* */ }
    tryActionBar(player, `§e§l§nCelestial §7 ${hit}`);
  },
  sneak_down(player) {
    addFx(player, "resistance", 60, 3);
    addFx(player, "regeneration", 60, 2);
    for (let i = 0; i < 20; i++) {
      const a = Math.random() * Math.PI * 2;
      safeParticle(player.dimension, "minecraft:villager_happy",
        vAdd(player.location, { x: Math.cos(a) * 1.5, y: Math.random() * 2, z: Math.sin(a) * 1.5 }));
    }
    try { player.playSound("beacon.activate"); } catch (e) { /* */ }
    tryActionBar(player, "§e§l§nSanctum");
  },
};

// ---------------------------------------------------------------------------
// DARK - 8 skills
// ---------------------------------------------------------------------------
const darkSkills = {
  tap(player) {
    const dim = player.dimension;
    const head = player.getHeadLocation();
    const view = player.getViewDirection();
    const target = raycastEntity(player, 24);
    if (target) {
      damage(target, 12, player, EntityDamageCause.magic);
      const back = vNorm({ x: player.location.x - target.location.x, y: 0, z: player.location.z - target.location.z });
      try { player.teleport(vAdd(target.location, vScale(back, 1.5)), { dimension: dim }); } catch (e) { /* */ }
      for (let i = 1; i <= 10; i++) safeParticle(dim, "minecraft:mobspell_emitter", vAdd(head, vScale(view, i)));
      try { player.playSound("mob.wither.shoot"); } catch (e) { /* */ }
      tryActionBar(player, "§5§lVoid Grasp");
    } else {
      tryActionBar(player, "§5§lVoid Grasp §7(no target)");
    }
  },
  sneak(player) {
    const dim = player.dimension;
    const view = player.getViewDirection();
    const dest = vAdd(player.location, vScale(view, 20));
    try { player.teleport(dest, { dimension: dim }); } catch (e) { /* */ }
    for (let i = 0; i < 20; i++) safeParticle(dim, "minecraft:mobspell_emitter", vAdd(player.location, vScale(view, -i * 0.5)));
    try { player.playSound("mob.endermen.portal"); } catch (e) { /* */ }
    tryActionBar(player, "§5§lShadow Step");
  },
  up(player) {
    const dim = player.dimension;
    for (const v of entitiesNear(dim, player.location, 15, player.id)) {
      if (v.typeId === "minecraft:player") continue;
      addFx(v, "blindness", 100, 1);
      addFx(v, "slowness", 100, 1);
      damage(v, 6, player, EntityDamageCause.magic);
    }
    for (let i = 0; i < 30; i++) {
      const a = Math.random() * Math.PI * 2;
      safeParticle(dim, "minecraft:mobspell_emitter",
        vAdd(player.location, { x: Math.cos(a) * 6, y: 4 + Math.random() * 3, z: Math.sin(a) * 6 }));
    }
    try { player.playSound("mob.wither.ambient"); } catch (e) { /* */ }
    tryActionBar(player, "§5§lEclipse");
  },
  down(player) {
    const dim = player.dimension;
    for (let a = 0; a < Math.PI * 2; a += Math.PI / 14) {
      safeParticle(dim, "minecraft:mobspell_emitter",
        vAdd(player.location, { x: Math.cos(a) * 4, y: 0.2, z: Math.sin(a) * 4 }));
    }
    for (const v of entitiesNear(dim, player.location, 5, player.id)) {
      damage(v, 10, player, EntityDamageCause.magic);
      addFx(v, "slowness", 80, 2);
    }
    tryActionBar(player, "§5§lShadow Pit");
  },
  air(player) {
    const view = player.getViewDirection();
    tryImpulse(player, { x: view.x * 2.5, y: 0.3, z: view.z * 2.5 });
    addFx(player, "invisibility", 60, 0);
    for (let i = 0; i < 10; i++) safeParticle(player.dimension, "minecraft:mobspell_emitter", vAdd(player.location, vScale(view, i)));
    tryActionBar(player, "§5§lWraith Form");
  },
  water(player) {
    const dim = player.dimension;
    for (const v of entitiesNear(dim, player.location, 6, player.id)) {
      damage(v, 12, player, EntityDamageCause.magic);
      const d = vNorm({ x: v.location.x - player.location.x, y: 0, z: v.location.z - player.location.z });
      applyKnock(v, d.x, d.z, 1.8, 0.4);
    }
    for (let a = 0; a < Math.PI * 2; a += Math.PI / 12) {
      safeParticle(dim, "minecraft:mobspell_emitter",
        vAdd(player.location, { x: Math.cos(a) * 3, y: 0.8, z: Math.sin(a) * 3 }));
    }
    tryActionBar(player, "§5§lAbyssal Wave");
  },
  sneak_up(player) {
    const dim = player.dimension;
    let drained = 0;
    for (const v of entitiesNear(dim, player.location, 14, player.id)) {
      if (v.typeId === "minecraft:player") continue;
      const d = vNorm({ x: player.location.x - v.location.x, y: 0, z: player.location.z - v.location.z });
      applyKnock(v, d.x, d.z, 2.2, -0.2);
      damage(v, 18, player, EntityDamageCause.magic);
      addFx(v, "wither", 80, 1);
      drained++;
    }
    healPlayer(player, drained * 3);
    for (let i = 0; i < 40; i++) {
      const a = Math.random() * Math.PI * 2;
      const r = Math.random() * 7;
      safeParticle(dim, "minecraft:mobspell_emitter",
        vAdd(player.location, { x: Math.cos(a) * r, y: Math.random() * 3, z: Math.sin(a) * r }));
    }
    try { player.playSound("mob.wither.ambient"); } catch (e) { /* */ }
    tryActionBar(player, `§5§l§nDarkness Incarnate §7 ${drained}`);
  },
  sneak_down(player) {
    const dim = player.dimension;
    let absorbed = 0;
    for (const v of entitiesNear(dim, player.location, 6, player.id)) {
      if (v.typeId === "minecraft:player") continue;
      damage(v, 14, player, EntityDamageCause.magic);
      absorbed += 3;
    }
    healPlayer(player, absorbed);
    addFx(player, "absorption", 200, 2);
    for (let a = 0; a < Math.PI * 2; a += Math.PI / 16) {
      safeParticle(dim, "minecraft:mobspell_emitter",
        vAdd(player.location, { x: Math.cos(a) * 3, y: 1, z: Math.sin(a) * 3 }));
    }
    tryActionBar(player, "§5§l§nSoul Siphon");
  },
};

// ---------------------------------------------------------------------------
// DARK SCYTHE - extra modes (passive is handled by entityHitEntity)
// ---------------------------------------------------------------------------
const darkScytheSkills = {
  tap(player) {
    const dim = player.dimension;
    const head = player.getHeadLocation();
    const view = player.getViewDirection();
    const forward = vNorm(view);
    const victims = entitiesInCone(player, head, forward, 6, Math.cos(Math.PI / 4));
    for (const v of victims) {
      damage(v, 14, player, EntityDamageCause.entityAttack);
      applyKnock(v, view.x, view.z, 1.6, 0.4);
    }
    for (let i = 1; i <= 6; i++) safeParticle(dim, "minecraft:mobspell_emitter", vAdd(head, vScale(view, i)));
    try { player.playSound("mob.wither.shoot"); } catch (e) { /* */ }
    tryActionBar(player, `§5§lShadow Slash §7 ${victims.length}`);
  },
  sneak(player) {
    const dim = player.dimension;
    const victims = entitiesNear(dim, player.location, 5, player.id).filter((e) => e.typeId !== "minecraft:player");
    let drained = 0;
    for (const v of victims) { damage(v, 11, player, EntityDamageCause.magic); drained++; }
    healPlayer(player, drained * 2);
    for (let i = 0; i < 16; i++) {
      const a = (Math.PI * 2 * i) / 16;
      safeParticle(dim, "minecraft:mobspell_emitter",
        vAdd(player.location, { x: Math.cos(a) * 3, y: 1, z: Math.sin(a) * 3 }));
    }
    try { player.playSound("mob.wither.ambient"); } catch (e) { /* */ }
    tryActionBar(player, `§5§lSoul Reap §7 ${drained}`);
  },
  up(player) {
    const dim = player.dimension;
    const target = raycastEntity(player, 30);
    if (target) {
      const to = vAdd(player.location, { x: 0, y: 0, z: 0 });
      try { target.teleport(vAdd(to, { x: 0, y: 1, z: 0 }), { dimension: dim }); } catch (e) { /* */ }
      damage(target, 12, player, EntityDamageCause.magic);
      tryActionBar(player, "§5§lReaper's Call");
    } else {
      tryActionBar(player, "§5§lReaper's Call §7(no target)");
    }
  },
  down(player) {
    const dim = player.dimension;
    for (const v of entitiesNear(dim, player.location, 5, player.id)) {
      if (v.typeId === "minecraft:player") continue;
      damage(v, 8, player, EntityDamageCause.magic);
      addFx(v, "slowness", 140, 3);
      addFx(v, "weakness", 140, 1);
    }
    for (let a = 0; a < Math.PI * 2; a += Math.PI / 14) {
      safeParticle(dim, "minecraft:mobspell_emitter",
        vAdd(player.location, { x: Math.cos(a) * 3.5, y: 0.2, z: Math.sin(a) * 3.5 }));
    }
    tryActionBar(player, "§5§lCemetery");
  },
  air(player) {
    const view = player.getViewDirection();
    tryImpulse(player, { x: view.x * 2, y: 0.4, z: view.z * 2 });
    addFx(player, "slow_falling", 120, 0);
    const dim = player.dimension;
    for (let i = 0; i < 10; i++) safeParticle(dim, "minecraft:mobspell_emitter", vAdd(player.location, vScale(view, i)));
    const t = raycastEntity(player, 8);
    if (t) damage(t, 10, player, EntityDamageCause.entityAttack);
    tryActionBar(player, "§5§lGrim Glide");
  },
  water(player) {
    const dim = player.dimension;
    for (const v of entitiesNear(dim, player.location, 5, player.id)) {
      if (v.typeId === "minecraft:player") continue;
      damage(v, 10, player, EntityDamageCause.magic);
      addFx(v, "slowness", 100, 3);
    }
    addFx(player, "water_breathing", 200, 0);
    tryActionBar(player, "§5§lDrowned Harvest");
  },
  sneak_up(player) {
    const dim = player.dimension;
    let slain = 0;
    for (const v of entitiesNear(dim, player.location, 12, player.id)) {
      if (v.typeId === "minecraft:player") continue;
      damage(v, 22, player, EntityDamageCause.magic);
      addFx(v, "wither", 100, 2);
      slain++;
    }
    healPlayer(player, slain * 3);
    for (let r = 1; r <= 6; r++) {
      for (let a = 0; a < Math.PI * 2; a += Math.PI / (4 * r)) {
        safeParticle(dim, "minecraft:mobspell_emitter",
          vAdd(player.location, { x: Math.cos(a) * r, y: 1, z: Math.sin(a) * r }));
      }
    }
    try { player.playSound("mob.wither.death"); } catch (e) { /* */ }
    tryActionBar(player, `§5§l§nDeath Harvest §7 ${slain}`);
  },
  sneak_down(player) {
    const dim = player.dimension;
    const victims = entitiesNear(dim, player.location, 8, player.id).filter((e) => e.typeId !== "minecraft:player");
    for (const v of victims) {
      damage(v, 16, player, EntityDamageCause.magic);
      addFx(v, "wither", 120, 1);
    }
    addFx(player, "absorption", 200, 2);
    for (let a = 0; a < Math.PI * 2; a += Math.PI / 18) {
      safeParticle(dim, "minecraft:mobspell_emitter",
        vAdd(player.location, { x: Math.cos(a) * 5, y: 0.2, z: Math.sin(a) * 5 }));
    }
    try { player.playSound("mob.wither.ambient"); } catch (e) { /* */ }
    tryActionBar(player, "§5§l§nGraveyard");
  },
};

// ---------------------------------------------------------------------------
// skill dispatch table + v4 metadata (names + per-staff colors/icons)
// ---------------------------------------------------------------------------
const SKILL_SETS = {
  [`${NS}:fire_staff`]: fireSkills,
  [`${NS}:water_staff`]: waterSkills,
  [`${NS}:earth_staff`]: earthSkills,
  [`${NS}:air_staff`]: airSkills,
  [`${NS}:lightning_staff`]: lightningSkills,
  [`${NS}:light_staff`]: lightSkills,
  [`${NS}:dark_staff`]: darkSkills,
  [`${NS}:dark_scythe`]: darkScytheSkills,
};

const MODE_ORDER = ["tap", "sneak", "up", "down", "air", "water", "sneak_up", "sneak_down"];
const MODE_LABEL = {
  tap: "Tap",
  sneak: "Sneak",
  up: "Look Up",
  down: "Look Down",
  air: "Airborne",
  water: "In Water",
  sneak_up: "Sneak + Up",
  sneak_down: "Sneak + Down",
};

const SKILL_NAMES = {
  [`${NS}:fire_staff`]:      { tap: "Fireball",       sneak: "Flame Nova",      up: "Meteor Rain",      down: "Lava Pool",      air: "Fire Dash",      water: "Steam Burst",      sneak_up: "Inferno",            sneak_down: "Phoenix Dive" },
  [`${NS}:water_staff`]:     { tap: "Tidal Lance",    sneak: "Aqua Restore",    up: "Rain Heal",        down: "Whirlpool",      air: "Water Slide",    water: "Tide Blessing",    sneak_up: "Tsunami",            sneak_down: "Frost Nova" },
  [`${NS}:earth_staff`]:     { tap: "Stone Spike",    sneak: "Quake Stomp",     up: "Boulder Toss",     down: "Fissure",        air: "Earth Fall",     water: "Mud Trap",         sneak_up: "Mountain Rise",      sneak_down: "Earthquake" },
  [`${NS}:air_staff`]:       { tap: "Gust Dash",      sneak: "Sky Leap",        up: "Tornado",          down: "Pressure Wave",  air: "Hover",          water: "Air Bubble",       sneak_up: "Hurricane",          sneak_down: "Wind Slam" },
  [`${NS}:lightning_staff`]: { tap: "Thunder Strike", sneak: "Chain Lightning", up: "Thunder Cloud",    down: "Ground Shock",   air: "Lightning Dash", water: "Static Discharge", sneak_up: "Thunder Storm",      sneak_down: "Ion Surge" },
  [`${NS}:light_staff`]:     { tap: "Solar Beam",     sneak: "Radiant Pulse",   up: "Divine Judgement", down: "Holy Ground",    air: "Light Step",     water: "Purify",           sneak_up: "Celestial",          sneak_down: "Sanctum" },
  [`${NS}:dark_staff`]:      { tap: "Void Grasp",     sneak: "Shadow Step",     up: "Eclipse",          down: "Shadow Pit",     air: "Wraith Form",    water: "Abyssal Wave",     sneak_up: "Darkness Incarnate", sneak_down: "Soul Siphon" },
  [`${NS}:dark_scythe`]:     { tap: "Shadow Slash",   sneak: "Soul Reap",       up: "Reaper's Call",    down: "Cemetery",       air: "Grim Glide",     water: "Drowned Harvest",  sneak_up: "Death Harvest",      sneak_down: "Graveyard" },
};

const STAFF_META = {
  [`${NS}:fire_staff`]:      { label: "Fire Staff",      color: "c", icon: "textures/items/elem_fire_orb",      sound: "mob.blaze.shoot" },
  [`${NS}:water_staff`]:     { label: "Water Staff",     color: "b", icon: "textures/items/elem_water_orb",     sound: "random.splash" },
  [`${NS}:earth_staff`]:     { label: "Earth Staff",     color: "2", icon: "textures/items/elem_earth_orb",     sound: "dig.stone" },
  [`${NS}:air_staff`]:       { label: "Air Staff",       color: "f", icon: "textures/items/elem_air_orb",       sound: "mob.bat.takeoff" },
  [`${NS}:lightning_staff`]: { label: "Lightning Staff", color: "e", icon: "textures/items/elem_lightning_orb", sound: "ambient.weather.thunder" },
  [`${NS}:light_staff`]:     { label: "Light Staff",     color: "e", icon: "textures/items/elem_light_orb",     sound: "beacon.activate" },
  [`${NS}:dark_staff`]:      { label: "Dark Staff",      color: "5", icon: "textures/items/elem_dark_orb",      sound: "mob.wither.ambient" },
  [`${NS}:dark_scythe`]:     { label: "Dark Scythe",     color: "5", icon: "textures/items/elem_dark_scythe",   sound: "mob.wither.shoot" },
};

function modeStatus(player, itemId, mode) {
  const ticks = SKILL_COOLDOWNS[mode] ?? 20;
  const last = getCooldown(player, `${itemId}:${mode}`);
  const now = system.currentTick;
  if (typeof last === "number" && now - last < ticks) {
    return { ready: false, remaining: ((ticks - (now - last)) / 20).toFixed(1) };
  }
  return { ready: true, remaining: 0 };
}

// v6 cast wrapper: no huge title card, just camera shake + themed sound +
// themed custom particle halo using the pack's own particle textures.
const STAFF_PARTICLE = {
  [`${NS}:fire_staff`]:      "elempower:ember",
  [`${NS}:water_staff`]:     "elempower:frost_crystal",
  [`${NS}:earth_staff`]:     "elempower:ember",
  [`${NS}:air_staff`]:       "elempower:divine_spark",
  [`${NS}:lightning_staff`]: "elempower:chain_link",
  [`${NS}:light_staff`]:     "elempower:divine_spark",
  [`${NS}:dark_staff`]:      "elempower:shadow_wisp",
  [`${NS}:dark_scythe`]:     "elempower:shadow_wisp",
};

function castSkill(player, itemId, mode) {
  const set = SKILL_SETS[itemId];
  const meta = STAFF_META[itemId];
  const names = SKILL_NAMES[itemId];
  if (!set || !meta || !names) return;
  const fn = set[mode] || set.tap;
  if (!fn) return;
  const cdKey = `${itemId}:${mode}`;
  const ticks = SKILL_COOLDOWNS[mode] ?? 20;
  if (!checkCooldownTicks(player, cdKey, ticks)) return;

  const heavy = mode === "sneak_up" || mode === "sneak_down";
  runCmd(player, `camerashake add @s ${heavy ? 1.6 : 0.55} ${heavy ? 0.6 : 0.28} positional`);
  try { player.playSound(meta.sound); } catch (e) { /* */ }

  const dim = player.dimension;
  const customP = STAFF_PARTICLE[itemId];
  for (let i = 0; i < 18; i++) {
    const a = (Math.PI * 2 * i) / 18;
    const r = 1.25 + Math.random() * 0.3;
    if (customP) {
      safeParticle(dim, customP,
        vAdd(player.location, { x: Math.cos(a) * r, y: 0.6 + Math.random() * 1.4, z: Math.sin(a) * r }));
    }
    safeParticle(dim, heavy ? "minecraft:mobspell_emitter" : "minecraft:critical_hit_emitter",
      vAdd(player.location, { x: Math.cos(a) * 0.6, y: 0.6 + Math.random() * 1.4, z: Math.sin(a) * 0.6 }));
  }

  try { fn(player); } catch (e) {
    try { console.warn(`cast err ${itemId}/${mode}: ${e}`); } catch (_) { /* */ }
  }
}

// v4 skill-picker modal: 8 named skills with live cooldown status.
function openSkillMenu(player, itemId) {
  const meta = STAFF_META[itemId];
  const names = SKILL_NAMES[itemId];
  if (!meta || !names) return;
  const form = new ActionFormData()
    .title(`§${meta.color}§l${meta.label}`)
    .body(
      "§7Tap a skill to cast it.\n" +
      "§8Each skill has its own cooldown.\n" +
      "§5uekermjheh on rblx",
    );

  const ordered = MODE_ORDER;
  for (const mode of ordered) {
    const status = modeStatus(player, itemId, mode);
    const statusText = status.ready ? "§aReady" : `§c${status.remaining}s`;
    form.button(
      `§${meta.color}§l${names[mode]}§r\n§8${MODE_LABEL[mode]} §7| ${statusText}`,
      meta.icon,
    );
  }
  form.button("§c§lClose", meta.icon);

  form.show(player).then((res) => {
    if (!res || res.canceled) return;
    const idx = res.selection;
    if (typeof idx !== "number") return;
    if (idx >= ordered.length) return;
    castSkill(player, itemId, ordered[idx]);
  }).catch((e) => { try { console.warn(`skill menu: ${e}`); } catch (_) { /* */ } });
}

// ---------------------------------------------------------------------------
// grant / awakening
// ---------------------------------------------------------------------------
function giveItem(player, typeId, amount) {
  try {
    const inv = player.getComponent("minecraft:inventory");
    if (!inv || !inv.container) return;
    const stack = new ItemStack(typeId, amount || 1);
    const leftover = inv.container.addItem(stack);
    if (leftover) player.dimension.spawnItem(leftover, player.location);
  } catch (e) { try { console.warn(`giveItem ${typeId}: ${e}`); } catch (_) { /* */ } }
}

// v4: picking in the GUI makes the orb pass INTO the player. No item is
// granted; the awakening runs immediately.
function grantElement(player, el) {
  player.sendMessage(`§${el.color}§l[Elemental Powers]§r §7The §${el.color}${el.label} Orb§7 flows §finto§7 you...`);
  try { player.playSound("random.orb"); } catch (e) { /* */ }
  const dim = player.dimension;
  for (let i = 0; i < 24; i++) {
    const a = Math.random() * Math.PI * 2;
    safeParticle(dim, "minecraft:villager_happy",
      vAdd(player.location, { x: Math.cos(a) * 1.6, y: 1 + Math.random() * 1.5, z: Math.sin(a) * 1.6 }));
  }
  beginAwakening(player, el.id);
}

function grantAll(player) {
  player.sendMessage("§d§l[Elemental Powers]§r §7All §delemental essences§7 surge §finto§7 you.");
  try { player.playSound("random.levelup"); } catch (e) { /* */ }
  let delay = 0;
  for (const el of ELEMENTS) {
    const pickEl = el;
    system.runTimeout(() => beginAwakening(player, pickEl.id), delay);
    delay += AWAKENING_TICKS + 10;
  }
}

const AWAKENING_TICKS = 80; // 4 seconds dizzy

function beginAwakening(player, elementId) {
  const el = ELEMENT_BY_ID[elementId];
  if (!el) return;
  const dim = player.dimension;

  // Dizzy phase
  addFx(player, "nausea", AWAKENING_TICKS + 20, 2);
  addFx(player, "slowness", AWAKENING_TICKS, 3);
  addFx(player, "blindness", AWAKENING_TICKS, 0);
  addFx(player, "weakness", AWAKENING_TICKS, 1);
  try { runCmd(player, `camerashake add @s 2 ${(AWAKENING_TICKS / 20).toFixed(1)} positional`); } catch (e) { /* */ }
  try { player.playSound("mob.endermen.portal"); } catch (e) { /* */ }
  player.sendMessage(`§${el.color}§l[Awakening]§r §7Dizzy... channeling the §${el.color}${el.label}§7 essence.`);

  // Swirling particles around the player during dizziness
  for (let t = 0; t < AWAKENING_TICKS; t += 4) {
    const baseT = t;
    system.runTimeout(() => {
      try {
        const p = player.location;
        for (let i = 0; i < 6; i++) {
          const a = (baseT / 4) * 0.6 + (i * Math.PI) / 3;
          const r = 1.5;
          safeParticle(dim, el.id === "fire" ? "minecraft:basic_flame_particle"
            : el.id === "water" ? "minecraft:water_splash_particle"
            : el.id === "earth" ? "minecraft:basic_crit_particle"
            : el.id === "air" ? "minecraft:cloud"
            : el.id === "lightning" ? "minecraft:critical_hit_emitter"
            : el.id === "light" ? "minecraft:villager_happy"
            : "minecraft:mobspell_emitter",
            vAdd(p, { x: Math.cos(a) * r, y: 1 + Math.sin(a * 0.5) * 0.6, z: Math.sin(a) * r }));
        }
      } catch (e) { /* */ }
    }, t);
  }

  // Awakening completion
  system.runTimeout(() => {
    removeFx(player, "nausea");
    removeFx(player, "slowness");
    removeFx(player, "blindness");
    removeFx(player, "weakness");
    try { player.playSound("random.levelup"); } catch (e) { /* */ }
    giveItem(player, ELEMENT_TO_STAFF[elementId], 1);
    if (elementId === "dark") giveItem(player, `${NS}:dark_scythe`, 1);
    player.sendMessage(
      `§${el.color}§l[Awakened]§r §7You now wield the §${el.color}${el.label} Staff§7. §8Tap it to open the skill menu.`,
    );
    try {
      player.onScreenDisplay.setTitle(`§${el.color}§l${el.label} Awakened`, {
        fadeInDuration: 4, stayDuration: 30, fadeOutDuration: 10, subtitle: "§78 skills unlocked",
      });
    } catch (e) { /* */ }
    tryActionBar(player, `§${el.color}§l${el.label} Awakening complete`);
    // Starburst effect
    for (let i = 0; i < 20; i++) {
      const a = Math.random() * Math.PI * 2;
      safeParticle(dim, "minecraft:villager_happy",
        vAdd(player.location, { x: Math.cos(a) * 2, y: 1 + Math.random() * 2, z: Math.sin(a) * 2 }));
    }
  }, AWAKENING_TICKS);
}

// ---------------------------------------------------------------------------
// GUI
// ---------------------------------------------------------------------------
function openGui(player) {
  const form = new ActionFormData()
    .title("§5§lElemental Powers v6")
    .body(
      "§7Pick an element. The orb flows §finto§7 you, you get §fdizzy§7 for a\n" +
      "§7few seconds, and then wake up wielding the §fstaff§7 with §f8 unique skills§7.\n" +
      "§8Tap the staff later to open a skill menu with cooldowns.\n" +
      "§5uekermjheh on rblx",
    );
  for (const el of ELEMENTS) form.button(`§${el.color}§l${el.label}§r\n§7${el.subtitle}`, el.icon);
  form.button("§d§lAll Elements§r\n§7Awaken to every element in sequence", "textures/items/elem_gui_tool");
  form.button("§c§lCancel", "textures/items/elem_dark_orb");

  form.show(player).then((res) => {
    if (!res || res.canceled) return;
    const idx = res.selection;
    if (typeof idx !== "number") return;
    if (idx < ELEMENTS.length) return grantElement(player, ELEMENTS[idx]);
    if (idx === ELEMENTS.length) return grantAll(player);
  }).catch((err) => { try { console.warn(`form error: ${err}`); } catch (e) { /* */ } });
}

// v4 welcome shown on first spawn.
function openBetaWelcome(player) {
  const form = new ActionFormData()
    .title("§5§lElemental Powers")
    .body(
      "§7beta v6 version idk if there are bugs now\n\n" +
      "§8The right-side HUD lists all 8 skills.\n" +
      "§8Your stance selects which one fires:\n" +
      "§8tap / sneak / look-up / look-down / airborne / in-water /\n" +
      "§8sneak+look-up / sneak+look-down. No more modal menu.\n\n" +
      "§8Tap the §dGUI Tool§8 or type §b!getmygui§8 to open the element picker.\n" +
      "§8Hold a staff -> your stance auto-picks a skill; tap to fire it.\n" +
      "§5uekermjheh on rblx",
    )
    .button("§c§lClose", "textures/items/elem_gui_tool");
  form.show(player).catch(() => { /* */ });
}

// ---------------------------------------------------------------------------
// listeners
// ---------------------------------------------------------------------------

// v6: tap the GUI tool opens the element picker; tap a staff casts the
// skill matching your current stance directly (no modal menu). The
// right-side HUD shows the full skill list so you always know what stance
// maps to which skill.
function handleItemUse(source, itemStack) {
  const id = itemStack && itemStack.typeId;
  if (!id || !source) return;
  if (id === `${NS}:gui_tool`) {
    if (!checkCooldownTicks(source, `${id}:open`, 6)) return;
    system.run(() => openGui(source));
    return;
  }
  if (SKILL_SETS[id]) {
    const mode = classifyInput(source);
    system.run(() => castSkill(source, id, mode));
  }
}

try { world.afterEvents.itemUse.subscribe((ev) => handleItemUse(ev.source, ev.itemStack)); } catch (e) { /* */ }

// 3) Chat trigger - Bedrock blocks "/"-prefixed messages
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

// 4) /scriptevent elempower:gui
try {
  system.afterEvents.scriptEventReceive.subscribe((ev) => {
    if (ev.id !== `${NS}:gui`) return;
    const player = ev.sourceEntity;
    if (!player || player.typeId !== "minecraft:player") return;
    system.run(() => openGui(player));
  });
} catch (e) { /* */ }

// 5) Custom slash command (MC 1.21.80+). Best-effort.
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
            const p = origin && origin.sourceEntity;
            if (p && p.typeId === "minecraft:player") system.run(() => openGui(p));
            return { status: 0, message: "Opening Elemental Powers..." };
          },
        );
      } catch (e) { try { console.warn(`register cmd: ${e}`); } catch (_) { /* */ } }
    });
  }
} catch (e) { /* */ }

// 6) Dark Scythe melee passive: bonus damage + lifesteal
try {
  world.afterEvents.entityHitEntity.subscribe((ev) => {
    const attacker = ev.damagingEntity;
    const target = ev.hitEntity;
    if (!attacker || !target || attacker.typeId !== "minecraft:player") return;
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

// 7) First-spawn welcome: give GUI Tool + show beta welcome form.
const GIVEN_TAG = "elempower_given_gui_v6";
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
        player.sendMessage("§5§l[Elemental Powers v6]§r §7Tap the §dGUI Tool§7 or type §b!getmygui§7. Pick an element; the orb enters you, you get dizzy, then awaken.");
        system.runTimeout(() => openBetaWelcome(player), 30);
      } catch (e) { /* */ }
    });
  });
} catch (e) { /* */ }

// v6: Chained-mob burial. When a mob tagged by Lightning Chain dies, the
// ground beneath them collapses into a dirt grave and an explosion of custom
// shadow/spark particles fires at the burial site. No-op if the mob was never
// chained.
try {
  world.afterEvents.entityDie.subscribe((ev) => {
    const died = ev.deadEntity;
    if (!died) return;
    let wasChained = false;
    try { wasChained = died.hasTag && died.hasTag("elempower_chained"); } catch (e) { /* */ }
    if (!wasChained) return;
    const loc = died.location;
    const dim = died.dimension;
    const fx = Math.floor(loc.x), fy = Math.floor(loc.y), fz = Math.floor(loc.z);
    try {
      dim.runCommand(`fill ${fx - 1} ${fy - 3} ${fz - 1} ${fx + 1} ${fy - 1} ${fz + 1} dirt 0 replace air`);
    } catch (e) { /* */ }
    for (let y = 0; y > -4; y--) {
      safeParticle(dim, "minecraft:large_explosion", { x: loc.x, y: loc.y + y, z: loc.z });
      for (let k = 0; k < 6; k++) {
        const a = (Math.PI * 2 * k) / 6;
        safeParticle(dim, "elempower:shadow_wisp",
          { x: loc.x + Math.cos(a) * 1.2, y: loc.y + y, z: loc.z + Math.sin(a) * 1.2 });
      }
    }
    try { dim.playSound("random.explode", loc); } catch (e) { /* */ }
    try { dim.playSound("mob.wither.death", loc); } catch (e) { /* */ }
  });
} catch (e) { /* */ }

// 8) Startup broadcast
system.run(() => {
  try { world.sendMessage("§5§l[Elemental Powers v6]§r §7scripts loaded - §5uekermjheh on rblx"); } catch (e) { /* */ }
  try { console.log("[Elemental Powers v6] ready"); } catch (e) { /* */ }
});

// 9) Persistent action-bar readout while holding a staff/scythe. This is as
// close to a pinned side-HUD as Bedrock scripting allows: a live ticker that
// shows the current weapon and its most-constrained cooldown.
function currentMainhandId(player) {
  try {
    const equip = player.getComponent("minecraft:equippable");
    const slot = equip && equip.getEquipment && equip.getEquipment(EquipmentSlot.Mainhand);
    return slot && slot.typeId;
  } catch (e) { return undefined; }
}

// v6: multi-line readout rendered on the right side of the screen via the
// JSON-UI-repositioned hud_actionbar_text. Shows the current stance (which
// picks the skill that will fire on tap) plus every skill with live cooldown.
function buildReadout(player, itemId) {
  const meta = STAFF_META[itemId];
  const names = SKILL_NAMES[itemId];
  if (!meta || !names) return "";
  let currentMode;
  try { currentMode = classifyInput(player); } catch (e) { currentMode = "tap"; }
  const lines = [`§${meta.color}§l${meta.label}`];
  for (const mode of MODE_ORDER) {
    const s = modeStatus(player, itemId, mode);
    const tag = s.ready ? "§a[READY]" : `§c[${s.remaining}s]`;
    const prefix = mode === currentMode ? "§e§l>" : "§8 ";
    lines.push(`${prefix} ${tag} §7${MODE_LABEL[mode]}: §f${names[mode]}`);
  }
  return lines.join("\n");
}

try {
  system.runInterval(() => {
    let players = [];
    try { players = world.getAllPlayers(); } catch (e) { return; }
    for (const p of players) {
      const id = currentMainhandId(p);
      if (!id || !STAFF_META[id]) continue;
      const text = buildReadout(p, id);
      if (text) tryActionBar(p, text);
    }
  }, 10);
} catch (e) { /* */ }
