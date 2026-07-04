"""
particles.py – Visual Effects: Screen Shake, Explosions, Ring Effects
======================================================================
All pure-pygame drawing, no external assets required.
"""

import math
import random
import pygame


# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------
def _lerp_colour(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


# ---------------------------------------------------------------------------
# Screen Shake
# ---------------------------------------------------------------------------
class ScreenShake:
    """Accumulates shake impulses and returns (dx, dy) each frame."""

    def __init__(self, decay: float = 0.82):
        self._magnitude = 0.0
        self._decay     = decay

    def trigger(self, magnitude: float = 8.0) -> None:
        self._magnitude = max(self._magnitude, magnitude)

    def update(self) -> tuple[int, int]:
        if self._magnitude < 0.5:
            self._magnitude = 0.0
            return (0, 0)
        dx = int(random.uniform(-self._magnitude, self._magnitude))
        dy = int(random.uniform(-self._magnitude, self._magnitude))
        self._magnitude *= self._decay
        return (dx, dy)


# ---------------------------------------------------------------------------
# Individual Particle
# ---------------------------------------------------------------------------
class Particle:
    def __init__(self, x: float, y: float, angle: float, speed: float,
                 colour_start, colour_end, lifespan: float):
        self.x   = x
        self.y   = y
        self.vx  = math.cos(angle) * speed
        self.vy  = math.sin(angle) * speed
        self.cs  = colour_start
        self.ce  = colour_end
        self.life = lifespan   # seconds
        self.age  = 0.0
        self.radius = random.uniform(2, 5)
        self.alive = True

    def update(self, dt: float) -> None:
        self.age += dt
        if self.age >= self.life:
            self.alive = False
            return
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vx *= 0.92     # drag
        self.vy *= 0.92

    def draw(self, surface: pygame.Surface, offset: tuple[int, int] = (0, 0)) -> None:
        if not self.alive:
            return
        t      = min(self.age / self.life, 1.0)
        colour = _lerp_colour(self.cs, self.ce, t)
        alpha  = int(255 * (1.0 - t))
        r      = max(1, int(self.radius * (1.0 - t * 0.5)))

        # Draw with per-pixel alpha using a temporary surface
        s = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*colour, alpha), (r + 1, r + 1), r)
        ox, oy = offset
        surface.blit(s, (int(self.x) - r - 1 + ox, int(self.y) - r - 1 + oy))


# ---------------------------------------------------------------------------
# Ring Effect (expanding transparent circle)
# ---------------------------------------------------------------------------
class RingEffect:
    def __init__(self, x: float, y: float, colour, max_radius: float = 60,
                 lifespan: float = 0.4):
        self.x          = x
        self.y          = y
        self.colour     = colour
        self.max_radius = max_radius
        self.life       = lifespan
        self.age        = 0.0
        self.alive      = True

    def update(self, dt: float) -> None:
        self.age += dt
        if self.age >= self.life:
            self.alive = False

    def draw(self, surface: pygame.Surface, offset: tuple[int, int] = (0, 0)) -> None:
        if not self.alive:
            return
        t      = min(self.age / self.life, 1.0)
        radius = int(self.max_radius * t)
        alpha  = int(220 * (1.0 - t))
        width  = max(1, int(3 * (1.0 - t) + 1))
        if radius < 1:
            return

        s = pygame.Surface((radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.colour, alpha), (radius + 2, radius + 2), radius, width)
        ox, oy = offset
        surface.blit(s, (int(self.x) - radius - 2 + ox, int(self.y) - radius - 2 + oy))


# ---------------------------------------------------------------------------
# Explosion (particle burst + ring)
# ---------------------------------------------------------------------------
class Explosion:
    """
    A complete explosion effect: N radial particles + 2 rings.

    Parameters
    ----------
    x, y        : float  – World position of impact.
    colour_core : tuple  – Bright centre colour (e.g. gold).
    colour_edge : tuple  – Fade-out colour (e.g. coral red).
    n_particles : int    – Number of radial particles.
    """

    def __init__(self, x: float, y: float,
                 colour_core=(255, 230, 0),
                 colour_edge=(240, 80, 80),
                 n_particles: int = 16):
        self.alive      = True
        self.particles  : list[Particle]   = []
        self.rings      : list[RingEffect] = []

        for _ in range(n_particles):
            angle  = random.uniform(0, math.tau)
            speed  = random.uniform(60, 220)
            life   = random.uniform(0.3, 0.55)
            self.particles.append(
                Particle(x, y, angle, speed, colour_core, colour_edge, life)
            )

        # Two concentric rings for more visual weight
        self.rings.append(RingEffect(x, y, colour_core, max_radius=55, lifespan=0.35))
        self.rings.append(RingEffect(x, y, colour_edge, max_radius=80, lifespan=0.45))

    def update(self, dt: float) -> None:
        for p in self.particles:
            p.update(dt)
        for r in self.rings:
            r.update(dt)
        # Mark done when everything is gone
        if all(not p.alive for p in self.particles) and all(not r.alive for r in self.rings):
            self.alive = False

    def draw(self, surface: pygame.Surface, offset: tuple[int, int] = (0, 0)) -> None:
        for r in self.rings:
            r.draw(surface, offset)
        for p in self.particles:
            p.draw(surface, offset)
