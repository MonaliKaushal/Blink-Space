"""
weapons.py – Cursed Arsenal System
====================================
Defines the 8 cursed weapons, their stats and drawbacks, plus
the WeaponPickup class that spawns on the arena floor between waves.

Rules:
  • Player holds ONE weapon at a time.
  • Picking up a new weapon auto-drops the old one (no menu).
  • Every weapon has a chaotic curse / drawback.
"""

from dataclasses import dataclass, field
from typing import Optional
import math
import random


# ---------------------------------------------------------------------------
# Weapon definition
# ---------------------------------------------------------------------------
@dataclass
class Weapon:
    id:            str
    name:          str
    damage:        int            # hit-points removed per shot
    curse_name:    str
    curse_desc:    str            # short HUD reminder
    color:         tuple          # RGB tint for HUD / gun sprite
    fire_delay:    float = 0.3    # unified rate of fire / cooldown (seconds)
    automatic:     bool  = False  # can be fired continuously by holding fire
    max_range:     float = 100.0  # max map units for hit detection
    splash_radius: float = 0.0    # splash damage radius
    # Curse / weapon specific parameters
    self_damage:   int   = 0      # HP drained per swing / shot
    wide_arc:      bool  = False  # hits all enemies in forward arc
    knockback:     float = 0.0    # extra camera shake magnitude
    reload_time:   float = 0.0    # if > 0, shows reload bar on HUD


# ---------------------------------------------------------------------------
# The 8 Weapons across 5 Categories
# ---------------------------------------------------------------------------
WEAPONS = {
    # --- Starting Weapon ---
    "pistol": Weapon(
        id          = "pistol",
        name        = "🔫 Pistol",
        damage      = 1,
        curse_name  = "No Curse",
        curse_desc  = "Standard starting sidearm. Steady aim.",
        color       = (200, 200, 200),
        fire_delay  = 0.4,
        max_range   = 100.0,
    ),

    # --- Melee Weapons ---
    "cutlass": Weapon(
        id          = "cutlass",
        name        = "⚔  Cutlass",
        damage      = 1,
        curse_name  = "No Curse",
        curse_desc  = "Standard blade. Short melee range.",
        color       = (200, 200, 200),
        fire_delay  = 0.3,
        max_range   = 2.2,
    ),
    "crowbar": Weapon(
        id          = "crowbar",
        name        = "⚓ Crowbar",
        damage      = 5,
        curse_name  = "HEAVY WEIGHT",
        curse_desc  = "Slows down camera movement speed by 40%!",
        color       = (230, 70, 70),
        fire_delay  = 0.7,
        max_range   = 2.2,
    ),
    "cursed_cutlass": Weapon(
        id          = "cursed_cutlass",
        name        = "☠  Cursed Cutlass",
        damage      = 2,
        curse_name  = "LIFE DRAIN",
        curse_desc  = "Swings drain 3 HP, but hits life-steal 6 HP!",
        color       = (160, 40, 200),
        fire_delay  = 0.25,
        max_range   = 2.2,
        self_damage = 3,
    ),

    # --- Pistols & Revolvers ---
    "flintlock": Weapon(
        id          = "flintlock",
        name        = "🔫 Flintlock Pistol",
        damage      = 3,
        curse_name  = "SLOW RELOAD",
        curse_desc  = "3-sec reload after every shot!",
        color       = (255, 190, 60),
        fire_delay  = 3.0,
        reload_time = 3.0,
        max_range   = 100.0,
    ),
    "revolver": Weapon(
        id          = "revolver",
        name        = "🤠 Golden Revolver",
        damage      = 4,
        curse_name  = "GREED'S BLEED",
        curse_desc  = "Drains 12 score points per second while held!",
        color       = (255, 215, 0),
        fire_delay  = 0.5,
        max_range   = 100.0,
    ),

    # --- Shotguns ---
    "blunderbuss": Weapon(
        id          = "blunderbuss",
        name        = "💣 Blunderbuss",
        damage      = 6,
        curse_name  = "KNOCKBACK BLAST",
        curse_desc  = "Hits ALL pirates – but jolts your aim!",
        color       = (255, 100, 40),
        fire_delay  = 0.8,
        wide_arc    = True,
        knockback   = 18.0,
        max_range   = 16.0,
    ),

    # --- Automatic Weapons ---
    "machine_gun": Weapon(
        id          = "machine_gun",
        name        = "🔥 Gatling Gun",
        damage      = 1,
        curse_name  = "OVERHEAT BURN",
        curse_desc  = "Continuous fire. Firing >1.2s burns you (5 HP/s)!",
        color       = (0, 230, 230),
        fire_delay  = 0.1,
        automatic   = True,
        max_range   = 15.0,
    ),

    # --- Heavy / Specialized Weapons ---
    "grenade_launcher": Weapon(
        id          = "grenade_launcher",
        name        = "🧨 Grenade Launcher",
        damage      = 3,
        curse_name  = "BLAST ZONE",
        curse_desc  = "Explosive splash! Self-dmg if enemies are close (3u).",
        color       = (230, 100, 255),
        fire_delay  = 1.4,
        reload_time = 1.4,
        max_range   = 100.0,
        splash_radius = 3.0,
    ),
    "rubber_duck": Weapon(
        id          = "rubber_duck",
        name        = "🦆 Cursed Rubber Duck",
        damage      = 5,
        curse_name  = "SQUEAKY DECOY",
        curse_desc  = "Draws enemies with squeaks, then detonates in a quack-blast!",
        color       = (255, 215, 0),
        fire_delay  = 1.5,
        reload_time = 1.5,
        max_range   = 100.0,
        splash_radius = 3.5,
    ),
}

# Cursed weapons that can drop
PICKUP_WEAPONS = [
    "cutlass",
    "crowbar",
    "cursed_cutlass",
    "flintlock",
    "revolver",
    "blunderbuss",
    "machine_gun",
    "grenade_launcher",
    "rubber_duck"
]


# ---------------------------------------------------------------------------
# Floor pickup
# ---------------------------------------------------------------------------
class WeaponPickup:
    PICKUP_RADIUS = 0.9   # map units

    def __init__(self, x: float, y: float, weapon: Weapon):
        self.x       = x
        self.y       = y
        self.weapon  = weapon
        self.alive   = True
        self._bob    = 0.0   # animation timer

    def update(self, dt: float) -> None:
        self._bob += dt * 2.5

    @property
    def bob_offset(self) -> float:
        """Sinusoidal bob value for HUD minimap dot or 3-D icon."""
        return math.sin(self._bob) * 0.12

    def check_pickup(self, px: float, py: float) -> Optional[Weapon]:
        """Returns the weapon if player is close enough, else None."""
        if not self.alive:
            return None
        dist = math.hypot(px - self.x, py - self.y)
        if dist <= self.PICKUP_RADIUS:
            self.alive = False
            return self.weapon
        return None


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def random_pickup_weapon() -> Weapon:
    return WEAPONS[random.choice(PICKUP_WEAPONS)]
