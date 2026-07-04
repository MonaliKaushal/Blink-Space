"""
hud.py – PUBG / Free Fire Style HUD for Blink Space FPS
=========================================================
Visual elements:
  • Circle + dot crosshair  (expands on shoot, turns red on lock)
  • Hit marker  ✕  (fades 0.4 s after each enemy hit)
  • "ELIMINATED" kill banner  (slides in, fades)
  • Segmented health bar  (bottom-left, PUBG style)
  • Floating damage text  (drifts upward from crosshair area)
  • Corner vignette panels  (extra dark corners)
  • Wave / zone indicator  (top-right, zone-ring style)
  • Kills / score  (top-left under health)
  • Animated gun  (bottom-centre, recoil on shoot)
  • Webcam feed  (bottom-right corner)
"""

import math
import random
import pygame
import numpy as np

# ---------------------------------------------------------------------------
# Colour palette  (Free Fire / PUBG palette)
# ---------------------------------------------------------------------------
C_ORANGE  = (255, 140,  30)
C_GOLD    = (255, 210,  50)
C_CYAN    = (  0, 210, 220)
C_RED     = (220,  40,  40)
C_GREEN   = ( 60, 220, 100)
C_WHITE   = (230, 235, 240)
C_DARK    = ( 10,  12,  10)
C_HEALTH  = ( 30, 160, 255)
C_ARMOR   = (  0, 200, 255)
C_PANEL   = (  8,  10,   8, 180)

# ---------------------------------------------------------------------------
# Floating damage number
# ---------------------------------------------------------------------------
class FloatingNumber:
    def __init__(self, text: str, x: float, y: float,
                 color=C_ORANGE):
        self.text  = text
        self.x     = x
        self.y     = y
        self.vel_y = -55.0
        self.life  = 1.1
        self.age   = 0.0
        self.color = color

    @property
    def alive(self) -> bool:
        return self.age < self.life

    def update(self, dt: float) -> None:
        self.age   += dt
        self.y     += self.vel_y * dt
        self.vel_y *= 0.92

    @property
    def alpha(self) -> int:
        return int(255 * max(0.0, 1.0 - self.age / self.life))


# ---------------------------------------------------------------------------
# Kill banner
# ---------------------------------------------------------------------------
class KillBanner:
    def __init__(self, wave_kill_count: int = 1):
        self.life  = 2.4
        self.age   = 0.0
        self.slide = 0.0    # 0 = off-screen, 1 = fully in
        words = ["ELIMINATED!", "HEADSHOT!", "DOWN!", "NICE SHOT!"]
        self.text = words[min(wave_kill_count - 1, len(words) - 1)]

    @property
    def alive(self) -> bool:
        return self.age < self.life

    def update(self, dt: float) -> None:
        self.age  += dt
        # Slide in fast, slide out near end
        if self.age < 0.25:
            self.slide = self.age / 0.25
        elif self.age > self.life - 0.5:
            self.slide = max(0.0, (self.life - self.age) / 0.5)
        else:
            self.slide = 1.0

    @property
    def alpha(self) -> int:
        return int(255 * self.slide)


# ---------------------------------------------------------------------------
# Font helpers
# ---------------------------------------------------------------------------
_fonts: dict = {}

def _font(size: int, bold: bool = False) -> pygame.font.Font:
    key = (size, bold)
    if key not in _fonts:
        for name in ("segoeui", "calibri", "arial", "consolas"):
            try:
                _fonts[key] = pygame.font.SysFont(name, size, bold=bold)
                break
            except Exception:
                continue
        else:
            _fonts[key] = pygame.font.Font(None, size)
    return _fonts[key]

def _lbl(text: str, size: int, color, bold: bool = False) -> pygame.Surface:
    return _font(size, bold).render(text, True, color)


# ---------------------------------------------------------------------------
# Gun sprites cache and dynamic drawer
# ---------------------------------------------------------------------------
_GUN_SURFS: dict = {}

def _get_gun(weapon_id: str) -> pygame.Surface:
    global _GUN_SURFS
    if weapon_id in _GUN_SURFS:
        return _GUN_SURFS[weapon_id]

    w, h = 320, 200
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    s.fill((0, 0, 0, 0))

    if weapon_id in ("cutlass", "cursed_cutlass"):
        # Blade tint color
        color = (160, 40, 200) if weapon_id == "cursed_cutlass" else (200, 200, 200)
        # Guard/Hilt
        pygame.draw.circle(s, (218, 165, 32), (180, 140), 24)
        pygame.draw.circle(s, (0, 0, 0, 0), (180, 140), 16)
        pygame.draw.rect(s, (218, 165, 32), (174, 110, 12, 60), border_radius=4)
        # Grip
        pygame.draw.rect(s, (70, 40, 20), (175, 125, 10, 30), border_radius=2)
        # Curved blade polygon
        points = [
            (180, 115), (140, 95), (100, 70), (60, 40), (40, 20),
            (48, 18), (72, 38), (110, 65), (148, 90), (182, 110)
        ]
        pygame.draw.polygon(s, color, points)
        # Blade reflection
        pygame.draw.polygon(s, (255, 255, 255, 120), [
            (178, 112), (138, 92), (98, 67), (58, 37), (41, 19),
            (43, 19), (61, 38), (101, 68), (141, 93), (179, 113)
        ])

    elif weapon_id == "crowbar":
        # Main red shaft with metal highlights
        pygame.draw.line(s, (180, 30, 30), (200, 160), (90, 70), 14)
        pygame.draw.line(s, (80, 80, 80), (200, 160), (90, 70), 8)
        # Curved hook
        curve_pts = [(90, 70), (70, 55), (55, 45), (45, 45), (40, 55), (45, 70), (55, 78)]
        for i in range(len(curve_pts) - 1):
            pygame.draw.line(s, (80, 80, 80), curve_pts[i], curve_pts[i+1], 10)
        # Claw tip
        pygame.draw.polygon(s, (50, 50, 50), [(50, 72), (62, 84), (45, 88), (35, 76)])

    elif weapon_id == "flintlock":
        # Brass barrel (tapered)
        pygame.draw.polygon(s, (180, 150, 80), [(50, 85), (170, 85), (170, 103), (50, 95)])
        pygame.draw.circle(s, (60, 60, 60), (50, 90), 5)
        # Wooden stock
        pygame.draw.polygon(s, (100, 60, 30), [(120, 95), (200, 95), (220, 150), (180, 160), (140, 120)])
        # Trigger guard
        pygame.draw.circle(s, (180, 150, 80), (160, 115), 12, 2)
        pygame.draw.line(s, (60, 60, 60), (160, 105), (155, 115), 3)
        # Flint cock/hammer
        pygame.draw.rect(s, (90, 90, 90), (140, 75, 25, 12), border_radius=2)
        pygame.draw.line(s, (70, 70, 70), (150, 75), (145, 62), 6)

    elif weapon_id == "revolver":
        # Golden barrel
        pygame.draw.rect(s, (240, 190, 40), (40, 80, 100, 16), border_radius=2)
        pygame.draw.rect(s, (210, 160, 20), (40, 96, 100, 6))
        # Cylinder
        pygame.draw.rect(s, (230, 180, 30), (140, 76, 42, 28), border_radius=3)
        for offset_y in (80, 88, 96):
            pygame.draw.line(s, (160, 120, 10), (142, offset_y), (178, offset_y), 2)
        # Frame
        pygame.draw.rect(s, (240, 190, 40), (130, 70, 65, 45), border_radius=4)
        # Dark wood grip
        pygame.draw.polygon(s, (80, 45, 20), [(180, 105), (210, 115), (200, 170), (165, 160)])
        # Trigger guard
        pygame.draw.circle(s, (240, 190, 40), (165, 120), 12, 2)

    elif weapon_id == "blunderbuss":
        # Flared brass muzzle
        pygame.draw.polygon(s, (200, 160, 40), [(30, 70), (120, 85), (120, 105), (30, 120)])
        pygame.draw.ellipse(s, (80, 60, 20), (24, 70, 12, 50))
        # Wooden stock
        pygame.draw.polygon(s, (110, 70, 40), [(120, 90), (210, 90), (230, 160), (180, 160)])
        # Lock plate
        pygame.draw.rect(s, (80, 80, 85), (140, 88, 35, 15), border_radius=2)

    elif weapon_id == "machine_gun":
        # Gatling gun multi-barrel rotary assembly
        pygame.draw.rect(s, (40, 40, 45), (30, 76, 120, 6))
        pygame.draw.rect(s, (30, 30, 35), (30, 84, 120, 6))
        pygame.draw.rect(s, (40, 40, 45), (30, 92, 120, 6))
        # Rotary rings
        pygame.draw.rect(s, (70, 70, 75), (50, 74, 8, 26))
        pygame.draw.rect(s, (70, 70, 75), (100, 74, 8, 26))
        pygame.draw.rect(s, (70, 70, 75), (140, 74, 8, 26))
        # Body
        pygame.draw.rect(s, (50, 50, 55), (148, 70, 65, 45), border_radius=4)
        # Ammo drum
        pygame.draw.ellipse(s, (35, 35, 40), (150, 45, 55, 30))
        # Grip
        pygame.draw.polygon(s, (20, 20, 20), [(195, 105), (215, 115), (205, 165), (185, 155)])

    elif weapon_id == "grenade_launcher":
        # Thick launcher barrel
        pygame.draw.rect(s, (55, 60, 65), (35, 78, 90, 24), border_radius=2)
        # Grenade cylinder drum
        pygame.draw.rect(s, (45, 50, 55), (125, 70, 50, 40), border_radius=4)
        pygame.draw.circle(s, (10, 10, 10), (140, 80), 6)
        pygame.draw.circle(s, (10, 10, 10), (140, 100), 6)
        pygame.draw.circle(s, (10, 10, 10), (160, 90), 6)
        # Receiver & stock
        pygame.draw.rect(s, (55, 60, 65), (175, 76, 40, 30))
        pygame.draw.rect(s, (30, 25, 20), (215, 80, 25, 45), border_radius=2)
        # Grips
        pygame.draw.rect(s, (30, 25, 20), (70, 102, 35, 14), border_radius=2)

    elif weapon_id == "rubber_duck":
        # Load duck image to hold in hand
        try:
            import os
            path = os.path.join("Blink Space", "duck.png")
            if not os.path.exists(path):
                path = "duck.png"
            img = pygame.image.load(path).convert_alpha()
            img = pygame.transform.scale(img, (110, 110))
            # Sleeve
            pygame.draw.rect(s, (80, 40, 40), (140, 110, 50, 90), border_radius=4)
            # Hand
            pygame.draw.circle(s, (210, 160, 120), (165, 110), 18)
            # Blit duck
            s.blit(img, (110, 40))
        except Exception as e:
            # Fallback yellow duck shape
            pygame.draw.circle(s, (255, 220, 0), (160, 100), 30)
            pygame.draw.circle(s, (230, 100, 0), (185, 100), 10)
            pygame.draw.circle(s, (0, 0, 0), (165, 90), 4)

    elif weapon_id == "pistol":
        # Standard pistol: slide, barrel, grip
        # Slide
        pygame.draw.rect(s, (70, 70, 75), (50, 75, 110, 22), border_radius=2)
        # Barrel tip
        pygame.draw.circle(s, (30, 30, 30), (50, 86), 4)
        # Frame
        pygame.draw.rect(s, (50, 50, 55), (90, 95, 60, 18))
        # Grip
        pygame.draw.polygon(s, (30, 30, 35), [(120, 110), (145, 110), (155, 168), (125, 168)])
        # Trigger guard
        pygame.draw.circle(s, (50, 50, 55), (115, 120), 10, 2)

    else:
        # Fallback rifle (original generic gun)
        pygame.draw.rect(s, (32, 32, 36), (28, 70, 90, 18))
        pygame.draw.rect(s, (22, 22, 26), (18, 75, 12, 8))
        pygame.draw.rect(s, (26, 26, 30), (120, 68, 28, 22))
        pygame.draw.rect(s, (44, 44, 50), (80, 60, 80, 8))
        pygame.draw.rect(s, (52, 52, 60), (60, 68, 120, 30))
        pygame.draw.rect(s, (44, 44, 52), (60, 98, 100, 28))
        pygame.draw.ellipse(s, (42, 42, 48), (80, 112, 44, 28))
        pygame.draw.ellipse(s, (0, 0, 0, 0), (86, 117, 32, 18))
        pygame.draw.rect(s, (38, 38, 44), (100, 126, 28, 58))
        pygame.draw.rect(s, (50, 50, 58), (102, 128, 24, 54))
        pygame.draw.polygon(s, (36, 26, 18), [(130, 120), (158, 120), (165, 178), (128, 178)])
        for i in range(5):
            y = 126 + i * 10
            pygame.draw.line(s, (50, 38, 26), (133, y), (158, y + 3), 1)
        pygame.draw.rect(s, (60, 60, 68), (172, 72, 14, 12))
        for i in range(5):
            x = 140 + i * 8
            pygame.draw.line(s, (65, 65, 72), (x, 70), (x, 96), 2)
        pygame.draw.rect(s, (180, 180, 195), (158, 60, 18, 10))
        pygame.draw.rect(s, (0, 0, 0, 0),   (164, 60, 6, 8))
        pygame.draw.rect(s, (180, 180, 195), (66, 60, 6, 10))
        pygame.draw.rect(s, (30, 30, 34), (82, 42, 76, 24))
        pygame.draw.rect(s, (20, 20, 24), (84, 44, 72, 20))
        pygame.draw.circle(s, (0, 200, 60, 160), (122, 54), 4)
        pygame.draw.rect(s, (34, 24, 16), (178, 90, 20, 36))

    _GUN_SURFS[weapon_id] = s
    return s


# ---------------------------------------------------------------------------
# HUD class
# ---------------------------------------------------------------------------
class HUD:
    XHAIR_BASE  = 18
    XHAIR_SHOOT = 42
    XHAIR_DECAY = 80    # px/s

    def __init__(self):
        self._xhair_r    : float = self.XHAIR_BASE
        self._gun_recoil : float = 0.0
        self._hit_timer  : float = 0.0      # hit marker countdown
        self._kill_banner: KillBanner | None = None
        self._combo_count: int = 0
        self.float_nums  : list[FloatingNumber] = []

    # ------------------------------------------------------------------

    def trigger_shoot(self) -> None:
        self._xhair_r    = self.XHAIR_SHOOT
        self._gun_recoil = 22.0

    def trigger_hit(self, kill: bool = False) -> None:
        """Call when a shot connects with an enemy."""
        self._hit_timer = 0.40
        # Floating number near crosshair
        cx = 0   # will be filled at draw time; store offset only
        off_x = random.randint(-40, 40)
        off_y = random.randint(-80, -40)
        label = "KILL!" if kill else "HIT"
        color = C_GOLD if kill else C_ORANGE
        # Store with placeholder coords — resolved in draw()
        self.float_nums.append(FloatingNumber(label, off_x, off_y, color))

        if kill:
            self._combo_count += 1
            self._kill_banner  = KillBanner(self._combo_count)

    def trigger_heal(self, amount: int) -> None:
        """Floating heal text near crosshair."""
        off_x = random.randint(-40, 40)
        off_y = random.randint(-80, -40)
        self.float_nums.append(FloatingNumber(f"+{amount} HP", off_x, off_y, (60, 220, 100)))

    def trigger_grenade_pickup(self, amount: int) -> None:
        """Floating grenade pickup text near crosshair."""
        off_x = random.randint(-40, 40)
        off_y = random.randint(-80, -40)
        self.float_nums.append(FloatingNumber(f"+{amount} DUCK GRENADES", off_x, off_y, C_GOLD))

    def trigger_no_grenades(self) -> None:
        """Floating alert when trying to throw with no grenades left."""
        off_x = random.randint(-20, 20)
        off_y = random.randint(-70, -50)
        self.float_nums.append(FloatingNumber("NO GRENADES!", off_x, off_y, C_RED))

    def reset_combo(self) -> None:
        self._combo_count = 0

    def update(self, dt: float) -> None:
        # Crosshair decay
        diff = self._xhair_r - self.XHAIR_BASE
        if diff > 0:
            self._xhair_r = max(self.XHAIR_BASE,
                                self._xhair_r - self.XHAIR_DECAY * dt)

        # Gun recoil spring-back
        self._gun_recoil = max(0.0, self._gun_recoil - 90 * dt)

        # Hit marker countdown
        self._hit_timer = max(0.0, self._hit_timer - dt)

        # Kill banner
        if self._kill_banner:
            self._kill_banner.update(dt)
            if not self._kill_banner.alive:
                self._kill_banner = None

        # Floating numbers
        for fn in self.float_nums:
            fn.update(dt)
        self.float_nums = [fn for fn in self.float_nums if fn.alive]

    # ------------------------------------------------------------------

    def draw(self, surface: pygame.Surface,
             world, vision_data: dict,
             enemy_locked: bool) -> None:
        sw, sh = surface.get_size()
        cx, cy = sw // 2, sh // 2

        # ── Screen-flash overlays ──────────────────────────────────
        if world.screen_flash > 0:
            t = min(world.screen_flash / 0.06, 1.0)
            _fill_alpha(surface, (255, 240, 160, int(t * 70)))

        if world.damage_flash > 0:
            t = min(world.damage_flash / 0.25, 1.0)
            _fill_alpha(surface, (180, 10, 10, int(t * 120)))

        # ── Extra corner vignette (additional to raycaster vignette) ─
        self._draw_corner_vignette(surface, sw, sh)

        # ── Crosshair ─────────────────────────────────────────────
        self._draw_crosshair(surface, cx, cy, enemy_locked)

        # ── Hit marker ────────────────────────────────────────────
        if self._hit_timer > 0:
            self._draw_hit_marker(surface, cx, cy)

        # ── Health / armor bar  (bottom-left) ─────────────────────
        self._draw_health_panel(surface, world.player_hp, sh)

        # ── Grenade Counter display (bottom-left) ─────────────────
        self._draw_grenade_counter(surface, world, sw, sh)

        # ── Wave / zone indicator  (top-right) ────────────────────
        self._draw_zone_indicator(surface, world, sw)

        # ── Kill banner  (centre-top) ─────────────────────────────
        if self._kill_banner:
            self._draw_kill_banner(surface, world, sw, sh)

        # ── Floating numbers ──────────────────────────────────────
        self._draw_float_nums(surface, cx, cy)

        # ── Gun  (bottom-centre) ──────────────────────────────────
        self._draw_gun(surface, sw, sh, world.current_weapon.id)

        # ── Webcam feed  (bottom-right) ───────────────────────────
        self._draw_webcam(surface, vision_data, sw, sh)

        # ── Wave intro overlay ────────────────────────────────────
        if world.state == "WAVE_INTRO":
            self._draw_wave_intro(surface, world.wave, sw, sh)

        # ── Game-over overlay ─────────────────────────────────────
        if world.state == "GAME_OVER":
            self._draw_game_over(surface, world, sw, sh)

        # ── Weapon pickup banner ─────────────────────────────────────────
        if world.weapon_notification:
            self._draw_weapon_pickup_banner(surface, world, sw, sh)

        # ── Reload indicator (Flintlock curse) ───────────────────────────
        if getattr(world, '_reload_cooldown', 0) > 0:
            self._draw_reload_indicator(surface, world, sw, sh)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _draw_crosshair(self, surface, cx, cy, locked):
        r   = int(self._xhair_r)
        col = C_RED if locked else C_WHITE
        dot_col = C_RED if locked else (200, 200, 200)

        # Thin circle
        xhair_surf = pygame.Surface((r * 2 + 8, r * 2 + 8), pygame.SRCALPHA)
        pygame.draw.circle(xhair_surf, (*col, 200), (r + 4, r + 4), r, 2)
        surface.blit(xhair_surf, (cx - r - 4, cy - r - 4))

        # Centre dot
        pygame.draw.circle(surface, dot_col, (cx, cy), 2)

        # Four tick marks at 90° intervals (inner)
        tick = 6
        gap  = r + 6
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            pygame.draw.line(surface, col,
                             (cx + dx * gap, cy + dy * gap),
                             (cx + dx * (gap + tick), cy + dy * (gap + tick)), 2)

    def _draw_hit_marker(self, surface, cx, cy):
        t     = self._hit_timer / 0.40
        alpha = int(255 * t)
        size  = int(12 + (1 - t) * 4)
        s = pygame.Surface((size * 2 + 4, size * 2 + 4), pygame.SRCALPHA)
        mid = size + 2
        color = (*C_RED, alpha)
        pygame.draw.line(s, color, (mid - size, mid - size), (mid + size, mid + size), 3)
        pygame.draw.line(s, color, (mid + size, mid - size), (mid - size, mid + size), 3)
        surface.blit(s, (cx - mid, cy - mid))

    def _draw_health_panel(self, surface, hp, sh):
        # Panel background
        panel = pygame.Surface((230, 64), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 0))
        pygame.draw.rect(panel, (0, 0, 0, 140), (0, 0, 230, 64), border_radius=4)
        surface.blit(panel, (12, sh - 76))

        # HP label
        hp_lbl = _lbl(f"{hp}", 32, C_WHITE, bold=True)
        surface.blit(hp_lbl, (16, sh - 72))
        hp_tag = _lbl("HP", 14, (160, 180, 160))
        surface.blit(hp_tag, (16 + hp_lbl.get_width() + 4, sh - 58))

        # Segmented health bar  (10 segments)
        seg_w = 17;  seg_h = 12;  gap = 3
        bar_x = 16;  bar_y = sh - 36
        for i in range(10):
            filled = i < int(hp / 10)
            color  = C_HEALTH if filled else (30, 50, 60)
            x = bar_x + i * (seg_w + gap)
            pygame.draw.rect(surface, color,
                             (x, bar_y, seg_w, seg_h), border_radius=2)
            if filled:
                pygame.draw.rect(surface, (100, 210, 255),
                                 (x, bar_y, seg_w, 3), border_radius=2)

        # Armor (fake, always full – visual fluff like Free Fire)
        armor_lbl = _lbl("ARMOR", 10, (100, 160, 200))
        surface.blit(armor_lbl, (16, sh - 20))
        for i in range(10):
            x = 62 + i * (12 + 2)
            pygame.draw.rect(surface, C_ARMOR, (x, sh - 21, 12, 8), border_radius=1)
            pygame.draw.rect(surface, (100, 230, 255), (x, sh - 21, 12, 2), border_radius=1)

    def _draw_zone_indicator(self, surface, world, sw):
        # Panel
        panel = pygame.Surface((210, 70), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 150))
        pygame.draw.rect(panel, (0, 0, 0, 150), (0, 0, 210, 70), border_radius=4)
        surface.blit(panel, (sw - 222, 10))

        wave_lbl  = _lbl(f"WAVE  {world.wave}", 26, C_GOLD, bold=True)
        score_lbl = _lbl(f"SCORE  {world.score}", 14, C_CYAN)
        kills_lbl = _lbl(f"KILLS  {world.kills}", 14, (180, 220, 180))

        surface.blit(wave_lbl,  (sw - 215, 14))
        surface.blit(score_lbl, (sw - 215, 44))
        surface.blit(kills_lbl, (sw - 215 + score_lbl.get_width() + 16, 44))

        # Enemies remaining bar
        n_alive = sum(1 for e in world.enemies if e.alive and e.state != "dead")
        n_total = max(len(world.enemies), 1)
        bar_w = 190
        frac  = n_alive / n_total
        pygame.draw.rect(surface, (30, 30, 30), (sw - 215, 62, bar_w, 6), border_radius=3)
        if frac > 0:
            pygame.draw.rect(surface, C_RED,
                             (sw - 215, 62, int(bar_w * frac), 6), border_radius=3)
        bar_lbl = _lbl(f"{n_alive} enemies remaining", 10, (160, 160, 160))
        surface.blit(bar_lbl, (sw - 215, 70))

        # ── Current weapon ───────────────────────────────────────────
        weapon = getattr(world, 'current_weapon', None)
        if weapon:
            wname_lbl  = _lbl(weapon.name,       12, weapon.color, bold=True)
            curse_lbl  = _lbl(f"☠ {weapon.curse_name}", 10, (220, 80, 80))
            surface.blit(wname_lbl, (sw - 215, 82))
            if weapon.curse_name != "No Curse":
                surface.blit(curse_lbl, (sw - 215, 96))

    def _draw_kill_banner(self, surface, world, sw, sh):
        kb = self._kill_banner
        if not kb:
            return
        alpha = kb.alpha

        big   = _lbl(kb.text, 56, C_GOLD, bold=True)
        small = _lbl(f"WAVE {world.wave} KILL", 18, C_ORANGE)

        # Slide down from top
        y = int((1 - kb.slide) * -80 + 80)

        big.set_alpha(alpha)
        small.set_alpha(alpha)
        surface.blit(big,   (sw // 2 - big.get_width()   // 2, y))
        surface.blit(small, (sw // 2 - small.get_width() // 2, y + 60))

        # Horizontal divider lines
        if alpha > 60:
            line_s = pygame.Surface((300, 2), pygame.SRCALPHA)
            line_s.fill((*C_GOLD, alpha // 2))
            surface.blit(line_s, (sw // 2 - 150, y + 56))

    def _draw_float_nums(self, surface, cx, cy):
        for fn in self.float_nums:
            lbl = _lbl(fn.text, 22, fn.color, bold=True)
            lbl.set_alpha(fn.alpha)
            # Positions are offsets from crosshair centre
            surface.blit(lbl, (cx + fn.x - lbl.get_width() // 2,
                                cy + fn.y - lbl.get_height() // 2))

    def _draw_gun(self, surface, sw, sh, weapon_id: str):
        gun = _get_gun(weapon_id)
        gw, gh = gun.get_size()
        x = sw // 2 - gw // 2 + 60
        y = sh - gh + int(self._gun_recoil)
        surface.blit(gun, (x, y))

        # Muzzle flash
        if self._gun_recoil > 14:
            t     = self._gun_recoil / 22.0
            fsize = int(t * 50)
            flash = pygame.Surface((fsize * 2, fsize * 2), pygame.SRCALPHA)
            pygame.draw.circle(flash, (255, 230, 100, int(t * 200)),
                               (fsize, fsize), fsize)
            pygame.draw.circle(flash, (255, 255, 255, int(t * 180)),
                               (fsize, fsize), fsize // 2)
            # Streaks
            for angle in (0, 30, -30, 15, -15):
                rad = math.radians(angle)
                ex  = fsize + int(math.cos(rad) * fsize * 1.5)
                ey  = fsize + int(math.sin(rad) * fsize * 0.5)
                pygame.draw.line(flash, (255, 200, 80, int(t * 160)),
                                 (fsize, fsize), (ex, ey), 3)
            # Muzzle is roughly at barrel tip position
            mx = x + 40 - fsize
            my = y + 80 - fsize
            surface.blit(flash, (mx, my))

    def _draw_webcam(self, surface, vision_data, sw, sh):
        frame = vision_data.get('frame')
        if frame is None:
            return
        import cv2
        rgb   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        small = cv2.resize(rgb, (150, 112))
        cam_s = pygame.surfarray.make_surface(small.transpose(1, 0, 2))

        x = sw - 160
        y = sh - 122
        surface.blit(cam_s, (x, y))
        pygame.draw.rect(surface, C_CYAN, (x, y, 150, 112), 1)

        ear   = vision_data.get('ear', 0)
        thr   = vision_data.get('threshold', 0.022)
        state = vision_data.get('state', 'OPEN')

        sc = C_GREEN if state == "OPEN" else C_RED
        dot = _lbl(f"● {state}  EAR {ear:.3f}", 10, sc)
        surface.blit(dot, (x, y + 114))

        # Threshold bar
        bw = 150
        pygame.draw.rect(surface, (15, 20, 15), (x, y + 126, bw, 6))
        fill = int(bw * min(ear / 0.04, 1.0))
        if fill > 0:
            pygame.draw.rect(surface, sc, (x, y + 126, fill, 6))
        tx = x + int(bw * min(thr / 0.04, 1.0))
        pygame.draw.line(surface, C_GOLD, (tx, y + 126), (tx, y + 132), 2)

    def _draw_corner_vignette(self, surface, sw, sh):
        """Darker corner triangles for PUBG-feel."""
        size = 220
        for corner_x, corner_y, flip_x, flip_y in [
            (0, 0, False, False),
            (sw, 0, True, False),
            (0, sh, False, True),
            (sw, sh, True, True),
        ]:
            vig = pygame.Surface((size, size), pygame.SRCALPHA)
            for r in range(size, 0, -10):
                alpha = int(120 * (1 - r / size) ** 2)
                pygame.draw.circle(vig, (0, 0, 0, alpha),
                                   (0 if not flip_x else size,
                                    0 if not flip_y else size), r)
            surface.blit(vig, (corner_x - (size if flip_x else 0),
                               corner_y - (size if flip_y else 0)))

    def _draw_wave_intro(self, surface, wave, sw, sh):
        _fill_alpha(surface, (0, 0, 0, 130))
        big   = _lbl(f"WAVE  {wave}", 72, C_GOLD, bold=True)
        sub   = _lbl("ENEMIES INBOUND  ·  BLINK TO SHOOT", 20, C_ORANGE)
        hint  = _lbl("Turn your head to aim", 16, (180, 180, 180))
        surface.blit(big,  (sw // 2 - big.get_width()  // 2, sh // 2 - 70))
        surface.blit(sub,  (sw // 2 - sub.get_width()  // 2, sh // 2 + 20))
        surface.blit(hint, (sw // 2 - hint.get_width() // 2, sh // 2 + 50))

        # Decorative lines
        lw = 400
        pygame.draw.line(surface, C_GOLD,
                         (sw // 2 - lw // 2, sh // 2 - 78),
                         (sw // 2 + lw // 2, sh // 2 - 78), 2)
        pygame.draw.line(surface, C_GOLD,
                         (sw // 2 - lw // 2, sh // 2 + 14),
                         (sw // 2 + lw // 2, sh // 2 + 14), 2)

    def _draw_game_over(self, surface, world, sw, sh):
        _fill_alpha(surface, (0, 0, 0, 175))

        lines = [
            (_lbl("MISSION FAILED", 68, C_RED, True),     sh // 2 - 120),
            (_lbl(f"WAVE  {world.wave}", 32, C_ORANGE),   sh // 2 - 30),
            (_lbl(f"KILLS   {world.kills}", 26, C_GREEN), sh // 2 + 14),
            (_lbl(f"SCORE   {world.score}", 26, C_CYAN),  sh // 2 + 48),
            (_lbl("[ R ] RESTART   [ ESC ] QUIT", 18, (150, 150, 150)),
             sh // 2 + 110),
        ]
        for surf, y in lines:
            surface.blit(surf, (sw // 2 - surf.get_width() // 2, y))

        # Divider
        pygame.draw.line(surface, C_RED,
                         (sw // 2 - 240, sh // 2 - 38),
                         (sw // 2 + 240, sh // 2 - 38), 2)

    def _draw_weapon_pickup_banner(self, surface, world, sw, sh):
        """Slide-in banner at the bottom showing picked-up weapon + curse."""
        t     = world._notif_timer
        total = 4.0
        # Fade in first 0.3s, hold, fade out last 0.5s
        if t > total - 0.3:
            alpha = int(255 * (total - t) / 0.3)
        elif t < 0.5:
            alpha = int(255 * t / 0.5)
        else:
            alpha = 255

        weapon = world.current_weapon
        panel_w, panel_h = 560, 56
        px = sw // 2 - panel_w // 2
        py = sh - 160

        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        pygame.draw.rect(panel, (0, 0, 0, 180), (0, 0, panel_w, panel_h), border_radius=6)

        if "DUCK GRENADE" in world.weapon_notification:
            color = (255, 215, 0) # Gold
            pygame.draw.rect(panel, (*color, 200), (0, 0, panel_w, panel_h), 2, border_radius=6)
            panel.set_alpha(alpha)
            surface.blit(panel, (px, py))
            title = _lbl(world.weapon_notification, 20, color, bold=True)
            curse = _lbl("Decoy decoy! Press [G] or Right-Click to throw!", 13, (220, 220, 220))
        else:
            color = weapon.color
            pygame.draw.rect(panel, (*color, 200), (0, 0, panel_w, panel_h), 2, border_radius=6)
            panel.set_alpha(alpha)
            surface.blit(panel, (px, py))
            title = _lbl(f"PICKED UP  {weapon.name}", 20, color, bold=True)
            curse = _lbl(f"CURSE: {weapon.curse_name}  —  {weapon.curse_desc}", 13, (220, 80, 80))

        title.set_alpha(alpha)
        curse.set_alpha(alpha)
        surface.blit(title, (px + 12, py + 6))
        surface.blit(curse, (px + 12, py + 34))

    def _draw_grenade_counter(self, surface, world, sw, sh):
        # Position next to health panel (px = 250, py = sh - 76, width = 96, height = 64)
        px = 248
        py = sh - 76
        pw, ph = 96, 64

        # Load duck icon once
        if not hasattr(self, '_duck_icon'):
            try:
                import os
                path = os.path.join("Blink Space", "duck.png")
                if not os.path.exists(path):
                    path = "duck.png"
                img = pygame.image.load(path).convert_alpha()
                self._duck_icon = pygame.transform.scale(img, (26, 26))
            except Exception as e:
                # Fallback simple shape
                self._duck_icon = pygame.Surface((26, 26), pygame.SRCALPHA)
                pygame.draw.circle(self._duck_icon, (255, 220, 0), (13, 13), 10)
                pygame.draw.circle(self._duck_icon, (230, 100, 0), (19, 13), 3)

        # Panel background
        panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        pygame.draw.rect(panel, (0, 0, 0, 140), (0, 0, pw, ph), border_radius=4)

        # Border color depending on count
        count = getattr(world, 'duck_grenades', 0)
        border_col = (255, 215, 0) if count > 0 else (100, 100, 100)
        pygame.draw.rect(panel, border_col, (0, 0, pw, ph), 1, border_radius=4)

        surface.blit(panel, (px, py))

        # Blit duck icon
        surface.blit(self._duck_icon, (px + 10, py + (ph - 26) // 2 + 2))

        # Text count
        col = (255, 255, 255) if count > 0 else (150, 150, 150)
        count_lbl = _lbl(f"×{count}", 26, col, bold=True)
        surface.blit(count_lbl, (px + 44, py + (ph - count_lbl.get_height()) // 2 + 4))

        # Label above
        lbl = _lbl("GRENADE [G]", 10, (160, 180, 160))
        surface.blit(lbl, (px + 8, py + 4))

    def _draw_reload_indicator(self, surface, world, sw, sh):
        """Flintlock curse: show RELOADING... bar above health."""
        cd    = world._reload_cooldown
        total = world.current_weapon.reload_time
        frac  = cd / max(total, 0.001)

        bar_w = 200
        bx    = sw // 2 - bar_w // 2
        by    = sh - 100

        panel = pygame.Surface((bar_w + 20, 36), pygame.SRCALPHA)
        pygame.draw.rect(panel, (0, 0, 0, 160), (0, 0, bar_w + 20, 36), border_radius=4)
        surface.blit(panel, (bx - 10, by - 4))

        lbl = _lbl("⟳  RELOADING...", 14, (255, 190, 60), bold=True)
        surface.blit(lbl, (bx, by - 2))

        pygame.draw.rect(surface, (40, 40, 20), (bx, by + 16, bar_w, 8), border_radius=4)
        fill_w = int(bar_w * frac)
        if fill_w > 0:
            pygame.draw.rect(surface, (255, 190, 60), (bx, by + 16, fill_w, 8), border_radius=4)


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------
def _fill_alpha(surface: pygame.Surface, color: tuple) -> None:
    ov = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    ov.fill(color)
    surface.blit(ov, (0, 0))
