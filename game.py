"""
game.py – FPS Game World: Player, Enemies, Waves, Weapons
==========================================================
Turret-mode FPS: the player stands at the map centre and rotates 360°
via head tracking.  Enemies spawn at the edges and advance to attack.
"""

import math
import random
import time
from dataclasses import dataclass, field
from typing import List, Optional

import pygame

from weapons import WEAPONS, WeaponPickup, random_pickup_weapon


# ---------------------------------------------------------------------------
# Map definition  (0 = open, 1-4 = wall textures)
# ---------------------------------------------------------------------------
WORLD_MAP = [
    [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,2,0,0,0,0,0,0,0,0,0,0,0,0,3,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,2,0,0,0,0,0,0,4,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,4,0,0,0,0,0,0,2,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,3,0,0,0,0,0,0,0,0,0,0,0,0,2,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
]
MAP_W = len(WORLD_MAP[0])
MAP_H = len(WORLD_MAP)

PLAYER_START_X = 9.5
PLAYER_START_Y = 9.5

# Valid open spawn positions (pre-computed)
_OPEN_CELLS = [
    (cx + 0.5, cy + 0.5)
    for cy in range(MAP_H)
    for cx in range(MAP_W)
    if WORLD_MAP[cy][cx] == 0
]

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
ROTATION_SPEED  = 2.8    # rad/s  (how fast head yaw rotates camera)
PITCH_SCALE     = 0.45   # direct pitch mapping coefficient

ENEMY_SPEED_BASE = 1.1   # map units / second (wave 1)
ENEMY_SPEED_STEP = 0.12  # extra speed per wave
ENEMY_HP_BASE    = 3     # hit points
ENEMY_MELEE_DIST = 0.85  # map units – contact damage range
ENEMY_DAMAGE     = 8     # HP per melee hit
ENEMY_ATTACK_CD  = 1.2   # seconds between melee attacks

PLAYER_MAX_HP    = 100
PLAYER_REGEN_HP  = 2.0   # HP per second (slow auto-regen between waves)

WAVE_SPAWN_DELAY = 4.0   # seconds of calm between waves
KILL_SCORE       = 100
COMBO_WINDOW     = 2.5   # seconds – kills within this time add to combo

COLLISION_MARGIN = 0.28  # wall collision radius


# ---------------------------------------------------------------------------
# Kill-feed entry
# ---------------------------------------------------------------------------
@dataclass
class KillEntry:
    text:  str
    timer: float = 2.2    # seconds before fade-out
    alpha: int   = 255


# ---------------------------------------------------------------------------
# Enemy
# ---------------------------------------------------------------------------
class Enemy:
    ANIM_INTERVAL = 0.28   # seconds between walk frames

    def __init__(self, x: float, y: float, hp: int, speed: float,
                 sprites: dict):
        self.x = x
        self.y = y
        self.hp = hp
        self.max_hp = hp
        self.speed = speed
        self.sprites = sprites

        self.state: str = "walk1"   # walk1 | walk2 | hurt | dead
        self.alive = True  # tracking alive
        self.stun_timer: float = 0.0  # seconds remaining for stun effect
        self.dead_timer: float = 0.0  # countdown after death
        self.anim_timer: float = 0.0
        self.attack_cd: float = 0.0       # cooldown between melee hits
        self.hurt_flash: float = 0.0       # brief red flash on hit
        self.y      = y
        self.hp     = hp
        self.max_hp = hp
        self.speed  = speed
        self.sprites = sprites

        self.state        : str   = "walk1"   # walk1 | walk2 | hurt | dead
        self.alive = True  # added for alive tracking
        self.stun_timer: float = 0.0  # seconds remaining for stun effect
        self.dead_timer   : float = 0.0       # countdown after death
        self.anim_timer   : float = 0.0
        self.attack_cd    : float = 0.0       # cooldown between melee hits
        self.hurt_flash   : float = 0.0       # brief red flash on hit


    # ------------------------------------------------------------------

    def update(self, dt: float, player_x: float, player_y: float,
               world_map: list) -> int:
        """
        Update enemy AI.  Returns damage dealt to player this frame.
        """
        if not self.alive:
            return 0

        dx = player_x - self.x
        dy = player_y - self.y
        self.dist = math.hypot(dx, dy)

        self.attack_cd  = max(0.0, self.attack_cd - dt)
        self.stun_timer = max(0.0, self.stun_timer - dt)

        # If stunned, skip movement, attack, and animation
        if self.stun_timer > 0:
            return 0

        if self.state == "hurt" and self.hurt_flash <= 0:
            self.state = "walk1"

        damage_dealt = 0

        if self.state == "dead":
            self.dead_timer -= dt
            if self.dead_timer <= 0:
                self.alive = False
            return 0

        # ── Move toward player ─────────────────────────────────────
        if self.dist > ENEMY_MELEE_DIST:
            length = max(self.dist, 0.001)
            vx = (dx / length) * self.speed * dt
            vy = (dy / length) * self.speed * dt
            _try_move(self, vx, vy, world_map)

        # ── Melee attack when in range ─────────────────────────────
        elif self.attack_cd <= 0:
            damage_dealt   = ENEMY_DAMAGE
            self.attack_cd = ENEMY_ATTACK_CD

        # ── Walk animation ─────────────────────────────────────────
        self.anim_timer += dt
        if self.anim_timer >= self.ANIM_INTERVAL:
            self.anim_timer = 0.0
            if self.state in ("walk1", "walk2"):
                self.state = "walk2" if self.state == "walk1" else "walk1"

        return damage_dealt

    def take_hit(self) -> bool:
        """Apply one bullet hit.  Returns True if enemy just died."""
        self.hp -= 1
        self.hurt_flash = 0.18
        self.state = "hurt"
        if self.hp <= 0:
            self.state      = "dead"
            self.dead_timer = 1.5
            return True
        return False

    @property
    def current_sprite(self) -> pygame.Surface:
        if self.hurt_flash > 0:
            return self.sprites["hurt"]
        return self.sprites.get(self.state, self.sprites["walk1"])
        return self.sprites.get(self.state, self.sprites["walk1"])


# ---------------------------------------------------------------------------
# Bullet / muzzle-flash effect
# ---------------------------------------------------------------------------
@dataclass
class MuzzleFlash:
    timer: float = 0.10   # seconds


# ---------------------------------------------------------------------------
# Hit marker
# ---------------------------------------------------------------------------
@dataclass
class HitMarker:
    timer: float = 0.35


# ---------------------------------------------------------------------------
# Duck Projectile
# ---------------------------------------------------------------------------
class DuckProjectile:
    def __init__(self, x: float, y: float, angle: float, speed: float, damage: int, splash_radius: float, sprite: pygame.Surface):
        self.x = x
        self.y = y
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.damage = damage
        self.splash_radius = splash_radius
        self.sprite = sprite
        self.timer = 2.0  # 2.0 second fuse
        self.alive = True
        self.squeak_timer = 0.0

    def update(self, dt: float, world_map: list, sound_manager) -> bool:
        if not self.alive:
            return False

        self.timer -= dt
        self.squeak_timer -= dt

        # Squeak periodically
        if self.squeak_timer <= 0:
            if sound_manager:
                sound_manager.play("duck_squeak")
            self.squeak_timer = 0.45

        # Check path collision
        nx = self.x + self.vx * dt
        if _is_solid(nx + 0.12, self.y) or _is_solid(nx - 0.12, self.y):
            self.vx = -self.vx * 0.65
            if sound_manager:
                sound_manager.play("duck_squeak")
        else:
            self.x = nx

        ny = self.y + self.vy * dt
        if _is_solid(self.x, ny + 0.12) or _is_solid(self.x, ny - 0.12):
            self.vy = -self.vy * 0.65
            if sound_manager:
                sound_manager.play("duck_squeak")
        else:
            self.y = ny

        self.vx *= 0.97
        self.vy *= 0.97

        if self.timer <= 0:
            self.alive = False
            return True
        return False


# ---------------------------------------------------------------------------
# Game World
# ---------------------------------------------------------------------------
class GameWorld:
    """
    Central game state for the FPS mode.

    Call every frame:
      damage = world.update(dt, head_yaw, head_pitch, blink_fired)
      sprites = world.get_sprites()
      world.draw_minimap(surface, rect)
    """

    def __init__(self, enemy_sprites: dict, sound_manager=None):
        self._enemy_sprites = enemy_sprites
        self.sound_manager = sound_manager
        
        # Load duck.png
        try:
            import os
            path = os.path.join("Blink Space", "duck.png")
            if not os.path.exists(path):
                path = "duck.png"
            self.duck_sprite = pygame.image.load(path).convert_alpha()
            self.duck_sprite = pygame.transform.scale(self.duck_sprite, (128, 128))
        except Exception as e:
            print(f"Error loading duck.png: {e}")
            self.duck_sprite = pygame.Surface((128, 128), pygame.SRCALPHA)
            pygame.draw.circle(self.duck_sprite, (255, 220, 0), (64, 64), 48)
            pygame.draw.circle(self.duck_sprite, (230, 100, 0), (96, 64), 16)
            pygame.draw.circle(self.duck_sprite, (0, 0, 0), (64, 48), 8)

        # Blood splash particle sprite
        self.blood_sprite = pygame.Surface((8, 8), pygame.SRCALPHA)
        pygame.draw.circle(self.blood_sprite, (200, 0, 0), (4, 4), 4)
        self.blood_particles: List[object] = []  # will hold BloodParticle instances

        self.restart()
        try:
            import os
            path = os.path.join("Blink Space", "duck.png")
            if not os.path.exists(path):
                path = "duck.png"
            self.duck_sprite = pygame.image.load(path).convert_alpha()
            self.duck_sprite = pygame.transform.scale(self.duck_sprite, (128, 128))
        except Exception as e:
            print(f"Error loading duck.png: {e}")
            self.duck_sprite = pygame.Surface((128, 128), pygame.SRCALPHA)
            pygame.draw.circle(self.duck_sprite, (255, 220, 0), (64, 64), 48)
            pygame.draw.circle(self.duck_sprite, (230, 100, 0), (96, 64), 16)
            pygame.draw.circle(self.duck_sprite, (0, 0, 0), (64, 48), 8)

        self.restart()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def restart(self) -> None:
        self.state      : str   = "WAVE_INTRO"   # WAVE_INTRO | PLAYING | GAME_OVER
        self.score      : int   = 0
        self.kills      : int   = 0
        self.wave       : int   = 0

        self.player_x   : float = PLAYER_START_X
        self.player_y   : float = PLAYER_START_Y
        self.cam_angle  : float = 0.0
        self.cam_pitch  : float = 0.0
        self.player_hp  : int   = PLAYER_MAX_HP

        self.enemies        : List[Enemy]        = []
        self.kill_feed      : List[KillEntry]    = []
        self.weapon_pickups : List[WeaponPickup] = []
        self.muzzle         : Optional[MuzzleFlash] = None
        self.hit_marker     : Optional[HitMarker]   = None
        self.projectiles    : List[DuckProjectile]  = []
        self.explosion_events: List[tuple]           = [] # (wx, wy, is_duck)

        # ── Weapon inventory ──────────────────────────────────────────
        self.current_weapon        = WEAPONS["pistol"]   # default
        self._reload_cooldown      : float = 0.0           # Flintlock curse
        self.weapon_notification   : str   = ""            # pickup banner text
        self._notif_timer          : float = 0.0
        self.weapon_knockback      : float = 0.0           # consumed by main.py
        self.duck_grenades         : int   = 3
        self.grenade_cooldown      : float = 0.0

        self._score_drain_accumulator: float = 0.0
        self._continuous_fire_time   : float = 0.0
        self._overheat_hp_accumulator: float = 0.0

        self._wave_timer    : float = 0.0
        self._combo_kills   : int   = 0
        self._combo_timer   : float = 0.0
        self._intro_timer   : float = 3.0
        self._screen_flash  : float = 0.0   # seconds of white overlay
        self._damage_flash  : float = 0.0   # seconds of red overlay (player hurt)
        self._wave_incoming_played : bool = False

        self._start_wave()

    def update(self, dt: float,
               head_yaw: float, head_pitch: float,
               blink_fired: bool = False,
               trigger_held: bool = False) -> None:
        """Main update.  Call once per frame."""

        if self.state == "GAME_OVER":
            return

        # ── Camera rotation from head yaw (Crowbar sluggish curse) ─────
        rot_scale = 0.6 if self.current_weapon.id == "crowbar" else 1.0
        self.cam_angle += head_yaw * ROTATION_SPEED * dt * rot_scale
        self.cam_pitch  = -head_pitch * PITCH_SCALE   # inverted: look up = negative

        # ── Revolver Score Drain Curse ────────────────────────────────
        if self.current_weapon.id == "revolver" and self.state == "PLAYING":
            self._score_drain_accumulator += dt * 12.0
            if self._score_drain_accumulator >= 1.0:
                drain = int(self._score_drain_accumulator)
                self.score = max(0, self.score - drain)
                self._score_drain_accumulator -= drain

        # ── Gatling Gun Overheat Curse ────────────────────────────────
        if self.current_weapon.id == "machine_gun" and trigger_held and self.state == "PLAYING":
            self._continuous_fire_time += dt
            if self._continuous_fire_time > 1.2:
                burn_damage = 5.0 * dt
                self._overheat_hp_accumulator += burn_damage
                if self._overheat_hp_accumulator >= 1.0:
                    hp_deduct = int(self._overheat_hp_accumulator)
                    self.player_hp = max(1, self.player_hp - hp_deduct)
                    self._overheat_hp_accumulator -= hp_deduct
                    self._damage_flash = 0.15
        else:
            self._continuous_fire_time = max(0.0, self._continuous_fire_time - dt * 2.0)
            self._overheat_hp_accumulator = 0.0

        # ── Muzzle flash countdown ────────────────────────────────────
        if self.muzzle:
            self.muzzle.timer -= dt
            if self.muzzle.timer <= 0:
                self.muzzle = None

        # ── Hit marker countdown ──────────────────────────────────────
        if self.hit_marker:
            self.hit_marker.timer -= dt
            if self.hit_marker.timer <= 0:
                self.hit_marker = None

        # ── Screen flashes ────────────────────────────────────────────
        self._screen_flash = max(0.0, self._screen_flash - dt)
        self._damage_flash = max(0.0, self._damage_flash - dt)

        # ── Weapon reload cooldown (Flintlock curse) ──────────────────
        was_reloading = self._reload_cooldown > 0
        self._reload_cooldown = max(0.0, self._reload_cooldown - dt)
        if was_reloading and self._reload_cooldown == 0:
            if self.sound_manager and self.current_weapon.reload_time > 0:
                self.sound_manager.play("reload_done")

        # ── Grenade throw cooldown ────────────────────────────────────
        self.grenade_cooldown = max(0.0, self.grenade_cooldown - dt)

        # ── Weapon notification timer ─────────────────────────────────
        if self._notif_timer > 0:
            self._notif_timer = max(0.0, self._notif_timer - dt)
            if self._notif_timer <= 0:
                self.weapon_notification = ""

        # ── Weapon pickup check (auto-equip; pickups consumed immediately) ──
        for pickup in self.weapon_pickups:
            new_weapon = pickup.weapon
            pickup.alive = False
            self.current_weapon    = new_weapon
            self._reload_cooldown  = 0.0
            self.weapon_notification = (
                f"{new_weapon.name}  |  CURSE: {new_weapon.curse_name}  —  "
                f"{new_weapon.curse_desc}"
            )
            self._notif_timer = 4.0
        self.weapon_pickups = [p for p in self.weapon_pickups if p.alive]

        # ── Fire on blink ─────────────────────────────────────────
        if blink_fired:
            self._fire_result = self._shoot()
        else:
            self._fire_result = (None, False)

        # ── Wave intro pause ──────────────────────────────────────────
        if self.state == "WAVE_INTRO":
            self._intro_timer -= dt
            if self._intro_timer <= 0:
                self.state = "PLAYING"

        # ── Enemy AI + damage ─────────────────────────────────────────
        if self.state == "PLAYING":
            # Update projectiles first
            active_projs = []
            for proj in self.projectiles:
                exploded = proj.update(dt, WORLD_MAP, self.sound_manager)
                if not exploded:
                    # Check enemy collision
                    for enemy in self.enemies:
                        if not enemy.alive or enemy.state == "dead":
                            continue
                        edist = math.hypot(enemy.x - proj.x, enemy.y - proj.y)
                        if edist <= 0.6:
                            # Apply damage to enemy
                            for _ in range(proj.damage):
                                k = enemy.take_hit()
                                if self.sound_manager:
                                    self.sound_manager.play("enemy_hit")
                                if k:
                                    self._on_kill(enemy)
                                    # Spawn blood splash on death
                                    self._spawn_blood(enemy.x, enemy.y)
                                    break
                            exploded = True
                            proj.alive = False
                            break
                if exploded:
                    self._detonate_duck(proj)
                else:
                    active_projs.append(proj)
            self.projectiles = active_projs

            total_dmg = 0
            for enemy in self.enemies:
                target_x, target_y = self.player_x, self.player_y
                # Decoy attraction logic
                if self.projectiles:
                    closest_proj = min(self.projectiles, key=lambda p: math.hypot(enemy.x - p.x, enemy.y - p.y))
                    if math.hypot(enemy.x - closest_proj.x, enemy.y - closest_proj.y) <= 8.0:
                        target_x, target_y = closest_proj.x, closest_proj.y

                dmg = enemy.update(dt, target_x, target_y, WORLD_MAP)
                if enemy.alive and enemy.state != "dead":
                    if random.random() < 0.003:  # Random creepy chuckle as they approach
                        if self.sound_manager:
                            self.sound_manager.play("enemy_laugh")
                if dmg > 0:
                    # Only damage player if actually close to the player
                    dist_to_player = math.hypot(self.player_x - enemy.x, self.player_y - enemy.y)
                    if dist_to_player <= ENEMY_MELEE_DIST:
                        total_dmg += dmg

            if total_dmg > 0:
                self.player_hp = max(0, self.player_hp - total_dmg)
                self._damage_flash = 0.25
                if self.sound_manager and self.player_hp > 0:
                    self.sound_manager.play("player_hurt")
                    self.sound_manager.play("enemy_hit")
                if self.player_hp == 0:
                    self.state = "GAME_OVER"
                    if self.sound_manager:
                        self.sound_manager.play("game_over")
                    return

            # Update blood particles
        new_particles = []
        for p in self.blood_particles:
            p.update(dt)
            if p.timer > 0:
                new_particles.append(p)
        self.blood_particles = new_particles
        self.enemies = [e for e in self.enemies if e.alive]

        # All enemies dead → next wave
        if not self.enemies:
            if not self._wave_incoming_played:
                if self.sound_manager:
                    self.sound_manager.play("wave_incoming")
                self._wave_incoming_played = True
            self._wave_timer -= dt
            if self._wave_timer <= 0:
                self._start_wave()

                # ── Kill-feed entries ─────────────────────────────────────────
                for kf in self.kill_feed:
                    kf.timer -= dt
                self.kill_feed = [kf for kf in self.kill_feed if kf.timer > 0]

                # ── Combo timer ───────────────────────────────────────────────
                if self._combo_timer > 0:
                    self._combo_timer -= dt
                    if self._combo_timer <= 0:
                        self._combo_kills = 0

    def fire(self) -> tuple:
        """External fire trigger (keyboard fallback). Returns (enemy|None, killed:bool)."""
        return self._shoot()

    def throw_grenade(self) -> bool:
        """Throws a Cursed Decoy Duck Grenade if available. Returns True if thrown."""
        if self.state != "PLAYING":
            return False
        if self.duck_grenades <= 0:
            return False
        if self.grenade_cooldown > 0:
            return False

        self.duck_grenades -= 1
        self.grenade_cooldown = 1.0  # 1.0s cooldown between grenade throws

        # Throw speed
        speed = 10.5
        proj = DuckProjectile(
            self.player_x, self.player_y,
            self.cam_angle, speed,
            damage=5, splash_radius=3.5,
            sprite=self.duck_sprite
        )
        self.projectiles.append(proj)

        if self.sound_manager:
            self.sound_manager.play("duck_squeak")

        return True

    def get_sprites(self) -> list:
        """Return sprite list for the raycaster (sorted by dist inside raycaster)."""
        sprites = []
        for enemy in self.enemies:
            if not enemy.alive:
                continue
            dx   = enemy.x - self.player_x
            dy   = enemy.y - self.player_y
            dist = math.hypot(dx, dy)
            sprites.append({
                'x':    enemy.x,
                'y':    enemy.y,
                'surf': enemy.current_sprite,
                'dist': dist,
            })
        # Add duck projectiles as billboard sprites
        for proj in self.projectiles:
            dx   = proj.x - self.player_x
            dy   = proj.y - self.player_y
            dist = math.hypot(dx, dy)
            sprites.append({
                'x':    proj.x,
                'y':    proj.y,
                'surf': proj.sprite,
                'dist': dist,
            })
        # Add blood particles as sprites (small red circles)
        for p in self.blood_particles:
            sprites.append({
                'x': p.x,
                'y': p.y,
                'surf': self.blood_sprite,
                'dist': math.hypot(p.x - self.player_x, p.y - self.player_y),
            })
        return sprites

    def draw_minimap(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        """Draw a top-down minimap into the given rect."""
        mw, mh = rect.width, rect.height
        cell_w = mw / MAP_W
        cell_h = mh / MAP_H

        # Map background
        pygame.draw.rect(surface, (10, 14, 10), rect)

        # Walls
        for my in range(MAP_H):
            for mx in range(MAP_W):
                if WORLD_MAP[my][mx] > 0:
                    r = pygame.Rect(
                        rect.x + int(mx * cell_w),
                        rect.y + int(my * cell_h),
                        max(1, int(cell_w)),
                        max(1, int(cell_h)),
                    )
                    colors = [(80, 55, 45), (50, 60, 70), (55, 55, 55), (45, 30, 25)]
                    c = colors[(WORLD_MAP[my][mx] - 1) % 4]
                    pygame.draw.rect(surface, c, r)

        # Enemies (red dots)
        for enemy in self.enemies:
            if not enemy.alive:
                continue
            ex = rect.x + int(enemy.x * cell_w)
            ey = rect.y + int(enemy.y * cell_h)
            pygame.draw.circle(surface, (220, 50, 50), (ex, ey), max(2, int(cell_w * 0.4)))

        # Player (bright arrow)
        px = rect.x + int(self.player_x * cell_w)
        py = rect.y + int(self.player_y * cell_h)
        arrow_len = int(cell_w * 1.6)
        ax = px + int(math.cos(self.cam_angle) * arrow_len)
        ay = py + int(math.sin(self.cam_angle) * arrow_len)
        pygame.draw.circle(surface, (0, 230, 120), (px, py), max(2, int(cell_w * 0.5)))
        pygame.draw.line(surface, (0, 230, 120), (px, py), (ax, ay), 2)

        # Border
        pygame.draw.rect(surface, (0, 180, 90), rect, 1)

    # ------------------------------------------------------------------
    # Properties for HUD
    # ------------------------------------------------------------------

    @property
    def screen_flash(self) -> float:
        return self._screen_flash

    @property
    def damage_flash(self) -> float:
        return self._damage_flash

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    class BloodParticle:
        def __init__(self, x: float, y: float, vx: float, vy: float):
            self.x = x
            self.y = y
            self.vx = vx
            self.vy = vy
            import random
            self.timer = random.uniform(0.3, 0.7)
            
        def update(self, dt: float):
            self.x += self.vx * dt
            self.y += self.vy * dt
            self.timer -= dt

    def _spawn_blood(self, x: float, y: float) -> None:
        """Create a burst of blood particles at (x, y)."""
        for _ in range(6):
            angle = random.random() * 2 * math.pi
            speed = random.uniform(1.0, 2.0)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            self.blood_particles.append(self.BloodParticle(x, y, vx, vy))
    # Note: using the nested BloodParticle class defined above
    def _shoot(self) -> tuple:
        """Shoot with current weapon, applying its curse. Returns (hit_enemy | None, killed: bool)."""
        w = self.current_weapon
        self._lifesteal_triggered = False

        # ── Block shooting during reload/cooldown ─────────────────────
        if self._reload_cooldown > 0:
            return (None, False)   # can't fire

        self.muzzle        = MuzzleFlash()
        self._screen_flash = 0.06
        self.weapon_knockback = 0.0

        # Set rate of fire cooldown / reload time
        self._reload_cooldown = w.fire_delay

        # Play fire sound
        if self.sound_manager:
            if w.id == "pistol":
                self.sound_manager.play("pistol_fire")
            elif w.id == "revolver":
                self.sound_manager.play("revolver_fire")
            elif w.id == "flintlock":
                self.sound_manager.play("flintlock_fire")
            elif w.id == "machine_gun":
                self.sound_manager.play("gatling_fire")
            elif w.id == "blunderbuss":
                self.sound_manager.play("blunderbuss_fire")
            elif w.id == "grenade_launcher":
                self.sound_manager.play("grenade_fire")
            elif w.id == "rubber_duck":
                self.sound_manager.play("duck_squeak")
            elif w.id == "crowbar":
                self.sound_manager.play("crowbar_swing")
            elif w.id == "cutlass":
                self.sound_manager.play("cutlass_swing")
            elif w.id == "cursed_cutlass":
                self.sound_manager.play("cursed_cutlass_swing")

            # Play reload start sound for reloadable weapons
            if w.reload_time > 0:
                self.sound_manager.play("reload_start")

        # Spawn projectile if it is the rubber duck
        if w.id == "rubber_duck":
            speed = 10.5
            proj = DuckProjectile(
                self.player_x, self.player_y,
                self.cam_angle, speed,
                w.damage, w.splash_radius,
                self.duck_sprite
            )
            self.projectiles.append(proj)
            return (None, False)

        # ── Apply self-damage curse ───────────────────────────────────
        if w.self_damage > 0:
            self.player_hp = max(1, self.player_hp - w.self_damage)  # min 1 so not instant death
            self._damage_flash = 0.15
            if self.sound_manager:
                self.sound_manager.play("player_hurt")
                self.sound_manager.play("enemy_hit")

        # ── Apply knockback curse ─────────────────────────────────────
        if w.knockback > 0:
            self.weapon_knockback = w.knockback

        # ── Wide-arc weapons (Blunderbuss) ────────────────────────────
        if w.wide_arc:
            best_hit = None
            best_dist = float('inf')
            closest_killed = False
            for enemy in self.enemies:
                if not enemy.alive or enemy.state == "dead":
                    continue
                dx = enemy.x - self.player_x
                dy = enemy.y - self.player_y
                dist = math.hypot(dx, dy)
                if dist > w.max_range:
                    continue

                # Pure geometric angle-based check relative to player camera view direction
                enemy_angle = math.atan2(dy, dx)
                diff = enemy_angle - self.cam_angle
                # Normalize difference to [-pi, pi]
                diff = (diff + math.pi) % (2 * math.pi) - math.pi

                # If within ~55 degrees of player center view (110 degree total cone)
                if abs(diff) <= 0.96:
                    enemy_died = False
                    # Apply damage
                    for _ in range(w.damage):
                        k = enemy.take_hit()
                        if k:
                            self._on_kill(enemy)
                            enemy_died = True
                            break

                    if dist < best_dist:
                        best_dist = dist
                        best_hit = enemy
                        closest_killed = enemy_died
            return (best_hit, closest_killed)

        # ── Standard single-target shot with Max Range check ──────────
        hit    = self._raycast_hit()
        killed = False
        if hit:
            # Check maximum range limit
            dx = hit.x - self.player_x
            dy = hit.y - self.player_y
            dist = math.hypot(dx, dy)
            if dist <= w.max_range:
                # ── Grenade Launcher Splash Damage ─────────────────────
                if w.splash_radius > 0:
                    primary_hit = hit
                    if self.sound_manager:
                        self.sound_manager.play("grenade_explosion")
                    for enemy in self.enemies:
                        if not enemy.alive or enemy.state == "dead":
                            continue
                        # Distance from primary target
                        edx = enemy.x - primary_hit.x
                        edy = enemy.y - primary_hit.y
                        edist = math.hypot(edx, edy)
                        if edist <= w.splash_radius:
                            # Apply damage
                            for _ in range(w.damage):
                                k = enemy.take_hit()
                                if k:
                                    self._on_kill(enemy)
                                    if enemy == primary_hit:
                                        killed = True
                                    break
                    # Blast Zone Curse self-damage: if primary target is within 3.0 units of player
                    if dist <= 3.0:
                        self.player_hp = max(1, self.player_hp - 25)
                        self._damage_flash = 0.25
                        if self.sound_manager:
                            self.sound_manager.play("player_hurt")
                else:
                    # Normal single target damage
                    if w.id == "cursed_cutlass":
                        self.player_hp = min(PLAYER_MAX_HP, self.player_hp + 6)
                        self._lifestealth_triggered = True
                        if self.sound_manager:
                            self.sound_manager.play("lifestealth")
                    elif self.sound_manager and w.id in ("cutlass", "crowbar"):
                        self.sound_manager.play("melee_hit")

                    for _ in range(w.damage):
                        killed = hit.take_hit()
                        if killed:
                            self._on_kill(hit)
                            # Spawn blood particles on death
                            self._spawn_blood(hit.x, hit.y)
                            break
                        killed = hit.take_hit()
                        if killed:
                            self._on_kill(hit)
                            break
            else:
                # Target out of range
                hit = None

        return (hit, killed)

    def _detonate_duck(self, proj) -> None:
        if self.sound_manager:
            self.sound_manager.play("duck_explosion")

        self._screen_flash = 0.12
        self.explosion_events.append((proj.x, proj.y, True))

        # Splash damage to enemies
        for enemy in self.enemies:
            if not enemy.alive or enemy.state == "dead":
                continue
            edist = math.hypot(enemy.x - proj.x, enemy.y - proj.y)
            if edist <= proj.splash_radius:
                # Apply damage
                for _ in range(proj.damage):
                    k = enemy.take_hit()
                    if k:
                        self._on_kill(enemy)
                        break
                # Apply stun effect (Exploding Quack)
                enemy.stun_timer = 0.5

        # Damage player if close
        pdist = math.hypot(self.player_x - proj.x, self.player_y - proj.y)
        if pdist <= proj.splash_radius:
            scaled_dmg = int(35 * (1.0 - pdist / proj.splash_radius))
            if scaled_dmg > 0:
                self.player_hp = max(1, self.player_hp - scaled_dmg)
                self._damage_flash = 0.25
                if self.sound_manager:
                    self.sound_manager.play("player_hurt")
                    self.sound_manager.play("enemy_hit")

    def _raycast_hit(self) -> Optional['Enemy']:
        """
        Find the enemy (if any) whose screen-centre projection overlaps
        the screen centre column AND is closer than the wall at that column.

        Uses the z_buffer stored after the last render call.
        (Injected via GameWorld.set_zbuffer after each frame.)
        """
        z_buf = getattr(self, '_z_buffer', None)

        dir_x   =  math.cos(self.cam_angle)
        dir_y   =  math.sin(self.cam_angle)
        plane_x = -dir_y   * math.tan(math.pi / 2.2 / 2)
        plane_y =  dir_x   * math.tan(math.pi / 2.2 / 2)
        det = plane_x * dir_y - dir_x * plane_y
        if abs(det) < 1e-9:
            det = 1e-9 if det >= 0 else -1e-9
        inv_det = 1.0 / det

        # Pretend ray_w = 480 for projection (matches Raycaster's default)
        ray_w   = getattr(self, '_ray_w', 480)
        center  = ray_w // 2

        best: Optional[Enemy] = None
        best_tz = float('inf')

        for enemy in self.enemies:
            if not enemy.alive or enemy.state == "dead":
                continue
            sx = enemy.x - self.player_x
            sy = enemy.y - self.player_y
            tx =  inv_det * ( dir_y  * sx - dir_x  * sy)
            tz =  inv_det * (-plane_y * sx + plane_x * sy)
            if tz < 0.1:
                continue

            screen_x = int((ray_w / 2) * (1.0 + tx / tz))
            sprite_w = abs(int(480 / tz))    # approximate sprite width
            half_w   = max(sprite_w // 2, 8)

            if abs(screen_x - center) <= half_w:
                # Check z_buffer occlusion if available
                if z_buf is not None:
                    buf_val = z_buf[min(center, len(z_buf) - 1)]
                    if tz >= buf_val:
                        continue
                if tz < best_tz:
                    best_tz = tz
                    best    = enemy

        return best

    def set_zbuffer(self, z_buffer, ray_w: int) -> None:
        """Called from main loop after each render to supply hit-detection data."""
        self._z_buffer = z_buffer
        self._ray_w    = ray_w

    def _on_kill(self, enemy: Enemy) -> None:
        self.kills += 1
        self._combo_kills += 1
        self._combo_timer  = COMBO_WINDOW

        if self.sound_manager:
            self.sound_manager.play("enemy_death")

        bonus = self._combo_kills
        pts   = KILL_SCORE * bonus
        self.score += pts

        # 20% chance to drop a duck grenade on enemy kill (cap at 5)
        if random.random() < 0.20:
            if self.duck_grenades < 5:
                self.duck_grenades += 1
                if self.sound_manager:
                    self.sound_manager.play("duck_squeak")

    def _start_wave(self) -> None:
        self.wave += 1
        self._wave_incoming_played = False
        n_enemies = 1 + self.wave
        spd = ENEMY_SPEED_BASE + (self.wave - 1) * ENEMY_SPEED_STEP
        hp  = ENEMY_HP_BASE + (self.wave - 1)

        # Reset player health to full on each new wave
        self.player_hp = PLAYER_MAX_HP

        # Refill grenades on start of wave (cap at 5)
        if self.wave > 1:
            self.duck_grenades = min(5, self.duck_grenades + 2)

        self.enemies = []
        spawns = _pick_spawn_positions(n_enemies, self.player_x, self.player_y)
        for sx, sy in spawns:
            self.enemies.append(Enemy(sx, sy, hp, spd, self._enemy_sprites))

        # ── Grant a new weapon automatically each wave (after wave 1) ────────
        if self.wave > 1:
            progression = {
                2: "rubber_duck",
                3: "machine_gun",
                4: "crowbar",
                5: "flintlock",
                6: "revolver",
                7: "cursed_cutlass",
                8: "grenade_launcher",
                9: "blunderbuss"
            }
            if self.wave in progression:
                weapon = WEAPONS[progression[self.wave]]
            else:
                weapon = random_pickup_weapon()
            # Queue it up; it will be auto-consumed in update() this frame
            self.weapon_pickups = [WeaponPickup(self.player_x, self.player_y, weapon)]

        self.state        = "WAVE_INTRO"
        self._intro_timer = 3.0
        self._wave_timer  = WAVE_SPAWN_DELAY
        if self.sound_manager:
            self.sound_manager.play("wave_intro")


# ---------------------------------------------------------------------------
# Movement helpers
# ---------------------------------------------------------------------------

def _is_solid(x: float, y: float) -> bool:
    mx, my = int(x), int(y)
    if 0 <= mx < MAP_W and 0 <= my < MAP_H:
        return WORLD_MAP[my][mx] > 0
    return True


def _try_move(entity, dx: float, dy: float, world_map: list) -> None:
    """Slide-based movement – try X, then Y independently."""
    m = COLLISION_MARGIN
    nx = entity.x + dx
    ny = entity.y + dy
    if not (_is_solid(nx + m, entity.y) or _is_solid(nx - m, entity.y)
            or _is_solid(nx, entity.y + m) or _is_solid(nx, entity.y - m)):
        entity.x = nx
    if not (_is_solid(entity.x + m, ny) or _is_solid(entity.x - m, ny)
            or _is_solid(entity.x, ny + m) or _is_solid(entity.x, ny - m)):
        entity.y = ny


def _pick_spawn_positions(n: int, px: float, py: float,
                          min_dist: float = 5.0) -> list:
    """Choose n open map positions far from the player."""
    candidates = [(x, y) for x, y in _OPEN_CELLS
                  if math.hypot(x - px, y - py) >= min_dist]
    if len(candidates) < n:
        candidates = _OPEN_CELLS   # fallback
    return random.sample(candidates, min(n, len(candidates)))
