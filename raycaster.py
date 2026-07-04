"""
raycaster.py – Pseudo-3D Raycasting Renderer  (Visual Polish Edition)
======================================================================
• DDA raycasting with 4 procedural wall textures
• Fully-vectorised textured floor / ceiling casting (numpy)
• PUBG-style sunset sky gradient
• Distance fog
• Pre-computed screen-space vignette
• Billboard enemy sprite rendering
"""

import math
from typing import List, Dict, Any

import numpy as np
import pygame

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TEX_SIZE    = 64
SPRITE_SIZE = 128
FOV         = math.pi / 2.2   # ~82° horizontal


# ---------------------------------------------------------------------------
# Procedural texture generators
# ---------------------------------------------------------------------------
def _make_wood_texture(base=(100, 65, 45), lines=(50, 30, 20)):
    np.random.seed(1)
    tex = np.full((TEX_SIZE, TEX_SIZE, 3), base, dtype=np.uint8)
    plank_w = 16
    for x in range(0, TEX_SIZE, plank_w):
        tex[:, x:x+2] = lines
    for x in range(0, TEX_SIZE, plank_w):
        cut_y = np.random.randint(10, TEX_SIZE-10)
        tex[cut_y:cut_y+2, x:x+plank_w] = lines
    noise = np.random.randint(-15, 15, tex.shape, dtype=np.int16)
    return np.clip(tex.astype(np.int16) + noise, 0, 255).astype(np.uint8)


def _make_brick_texture(base=(92, 60, 46), mortar=(52, 38, 34)):
    return _make_wood_texture((80, 50, 35), (40, 25, 15))


def _make_metal_texture():
    return _make_wood_texture((120, 85, 60), (60, 40, 25))


def _make_concrete_texture():
    return _make_wood_texture((70, 45, 30), (35, 20, 15))


def _make_dark_brick():
    return _make_wood_texture((60, 35, 25), (30, 15, 10))


def _make_floor_texture():
    """Wooden ship deck floor."""
    return _make_wood_texture((90, 60, 40), (45, 28, 18))


def _make_ceiling_texture():
    """Night sky / sails."""
    np.random.seed(8)
    base = np.zeros((TEX_SIZE, TEX_SIZE, 3), dtype=np.uint8)
    for _ in range(40):
        x = np.random.randint(0, TEX_SIZE)
        y = np.random.randint(0, TEX_SIZE)
        base[y, x] = [200, 220, 255]
    return base


# ---------------------------------------------------------------------------
# Enemy sprites
# ---------------------------------------------------------------------------
def make_enemy_sprites() -> Dict[str, pygame.Surface]:
    frames = {}
    for state in ("idle", "walk1", "walk2", "hurt", "dead"):
        surf = pygame.Surface((SPRITE_SIZE, SPRITE_SIZE), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 0))
        _draw_soldier(surf, state)
        frames[state] = surf
    return frames


def _draw_soldier(surf: pygame.Surface, state: str) -> None:
    s = SPRITE_SIZE
    if state == "dead":
        pygame.draw.ellipse(surf, (50, 75, 50),   (10, s // 2 + 8,  s - 20, 32))
        pygame.draw.circle(surf, (190, 150, 120),  (s // 4, s // 2 + 18), 18)
        pygame.draw.ellipse(surf, (110, 12, 12),   (s // 4 - 22, s // 2 + 22, 55, 20))
        return

    bob  = 6 if state == "walk1" else (-6 if state == "walk2" else 0)
    hurt = (state == "hurt")

    # Legs (Brown pants)
    leg_y = int(s * 0.62) + bob
    ll, rl = s // 2 - 16, s // 2 + 5
    lc = (80, 50, 30)
    if state == "walk1":
        pygame.draw.rect(surf, lc, (ll, leg_y,      12, s // 4))
        pygame.draw.rect(surf, lc, (rl, leg_y + 10, 12, s // 4 - 10))
    elif state == "walk2":
        pygame.draw.rect(surf, lc, (ll, leg_y + 10, 12, s // 4 - 10))
        pygame.draw.rect(surf, lc, (rl, leg_y,      12, s // 4))
    else:
        pygame.draw.rect(surf, lc, (ll, leg_y, 12, s // 4))
        pygame.draw.rect(surf, lc, (rl, leg_y, 12, s // 4))
    
    # Boots
    by = leg_y + s // 4 - 4
    pygame.draw.rect(surf, (20, 20, 20), (ll - 2, by, 16, 10))
    pygame.draw.rect(surf, (20, 20, 20), (rl - 2, by, 16, 10))

    # Torso (Striped shirt)
    body_y = int(s * 0.31) + bob
    bc = (220, 50, 50) if hurt else (220, 220, 220)
    pygame.draw.rect(surf, bc, (s // 2 - 20, body_y, 40, s // 4 + 8))
    if not hurt:
        for i in range(body_y, body_y + s // 4 + 8, 8):
            pygame.draw.rect(surf, (180, 40, 40), (s // 2 - 20, i, 40, 4))
    
    # Large belt
    pygame.draw.rect(surf, (40, 30, 20), (s // 2 - 22, body_y + s // 4 - 2, 44, 12))
    # Golden buckle
    pygame.draw.rect(surf, (210, 180, 40), (s // 2 - 8, body_y + s // 4 - 2, 16, 12), 3)

    # Arms
    arm_y = body_y + 6
    ac = (220, 50, 50) if hurt else (220, 220, 220)
    la_off = 5 if state == "walk1" else (-5 if state == "walk2" else 0)
    pygame.draw.rect(surf, ac, (s // 2 - 33, arm_y + la_off,  14, s // 5))
    pygame.draw.rect(surf, ac, (s // 2 + 19, arm_y - la_off,  14, s // 5))

    # Cutlass (Right side)
    sword_y = arm_y - la_off + 15
    # Handle
    pygame.draw.rect(surf, (100, 70, 40), (s // 2 + 23, sword_y, 6, 12))
    # Guard
    pygame.draw.circle(surf, (180, 150, 50), (s // 2 + 26, sword_y), 6, 2)
    # Blade (curved)
    pygame.draw.arc(surf, (200, 200, 200), (s // 2 + 25, sword_y - 25, 20, 30), math.pi/2, math.pi*1.5, 4)

    # Neck
    pygame.draw.rect(surf, (190, 150, 120), (s // 2 - 7, body_y - 10, 14, 12))

    # Head
    head_y = body_y - 33
    fc = (210, 100, 100) if hurt else (190, 150, 120)
    pygame.draw.circle(surf, fc, (s // 2, head_y + 15), 17)
    
    # Left Eye (Normal)
    pygame.draw.circle(surf, (255, 255, 255), (s // 2 - 6, head_y + 11), 4)
    pygame.draw.circle(surf, (30, 30, 30),    (s // 2 - 6, head_y + 11), 2)
    
    # Right Eye (Eyepatch)
    pygame.draw.circle(surf, (15, 15, 15), (s // 2 + 6, head_y + 11), 5)
    # Eyepatch strap
    pygame.draw.line(surf, (15, 15, 15), (s // 2 - 16, head_y + 6), (s // 2 + 16, head_y + 16), 2)

    # Tricorn Hat
    hat_points = [
        (s // 2 - 28, head_y + 5),
        (s // 2 + 28, head_y + 5),
        (s // 2, head_y - 15)
    ]
    pygame.draw.polygon(surf, (30, 30, 30), hat_points)
    # Gold trim
    pygame.draw.lines(surf, (210, 180, 40), False, hat_points, 2)


# ---------------------------------------------------------------------------
# Raycaster
# ---------------------------------------------------------------------------
class Raycaster:
    """
    Pseudo-3D DDA raycasting renderer with textured floor/ceiling.

    render() returns a pygame.Surface at (ray_w × ray_h).
    Scale it up with pygame.transform.scale before blitting.
    """

    def __init__(self, ray_w: int, ray_h: int, world_map: list):
        self.ray_w    = ray_w
        self.ray_h    = ray_h
        self.half_h   = ray_h // 2
        self.world_map = world_map
        self.map_w    = len(world_map[0])
        self.map_h    = len(world_map)

        half_fov        = FOV * 0.5
        self.plane_mag  = math.tan(half_fov)
        self.col_angles = np.linspace(-half_fov, half_fov, ray_w, dtype=np.float64)

        # Wall textures
        np.random.seed(99)
        self.textures = [
            _make_brick_texture(),
            _make_metal_texture(),
            _make_concrete_texture(),
            _make_dark_brick(),
        ]

        # Floor / ceiling textures  (TEX_SIZE, TEX_SIZE, 3)
        self.floor_tex   = _make_floor_texture().astype(np.float32)
        self.ceil_tex    = _make_ceiling_texture().astype(np.float32)

        # Z-buffer
        self.z_buffer = np.full(ray_w, 1e30, dtype=np.float64)

        # Pre-compute screen-space vignette mask (ray_w, ray_h, 1)
        self._vignette = self._build_vignette()

        # Pre-compute column direction lookup (perf: avoids per-frame trig)
        self._col_cos = np.cos(self.col_angles)
        self._col_sin = np.sin(self.col_angles)

    # ------------------------------------------------------------------

    def render(self,
               cam_x: float, cam_y: float,
               cam_angle: float, cam_pitch: float,
               sprites: List[Dict[str, Any]]) -> pygame.Surface:
        """
        Render one full frame (ray_w × ray_h).

        Parameters
        ----------
        sprites : list of dicts  { 'x', 'y', 'surf', 'dist' }
        """
        frame = np.zeros((self.ray_w, self.ray_h, 3), dtype=np.uint8)
        self.z_buffer[:] = 1e30

        horizon = int(self.half_h + cam_pitch * self.ray_h * 0.40)
        horizon = int(np.clip(horizon, 0, self.ray_h))

        # Camera vectors
        dir_x   =  math.cos(cam_angle)
        dir_y   =  math.sin(cam_angle)
        plane_x = -dir_y * self.plane_mag
        plane_y =  dir_x * self.plane_mag

        # ── 1. Sky gradient ───────────────────────────────────────────
        self._draw_sky(frame, horizon)

        # ── 2. Textured floor + ceiling (fully vectorised) ────────────
        self._cast_floor_ceiling(frame, cam_x, cam_y,
                                 dir_x, dir_y, plane_x, plane_y, horizon)

        # ── 3. DDA wall raycasting ────────────────────────────────────
        for x in range(self.ray_w):
            ray_dx = dir_x * math.cos(self.col_angles[x]) - dir_y * math.sin(self.col_angles[x])
            ray_dy = dir_x * math.sin(self.col_angles[x]) + dir_y * math.cos(self.col_angles[x])

            # Use precomputed sin/cos relative to world axes
            rdx = self._col_cos[x] * dir_x - self._col_sin[x] * dir_y
            rdy = self._col_cos[x] * dir_y + self._col_sin[x] * dir_x

            mx = int(cam_x);  my = int(cam_y)
            ddx = 1e30 if rdx == 0 else abs(1.0 / rdx)
            ddy = 1e30 if rdy == 0 else abs(1.0 / rdy)

            if rdx < 0:
                step_x = -1;  sdx = (cam_x - mx) * ddx
            else:
                step_x =  1;  sdx = (mx + 1.0 - cam_x) * ddx
            if rdy < 0:
                step_y = -1;  sdy = (cam_y - my) * ddy
            else:
                step_y =  1;  sdy = (my + 1.0 - cam_y) * ddy

            hit = False;  side = 0;  wall_val = 1
            for _ in range(80):
                if sdx < sdy:
                    sdx += ddx;  mx += step_x;  side = 0
                else:
                    sdy += ddy;  my += step_y;  side = 1
                if 0 <= mx < self.map_w and 0 <= my < self.map_h:
                    if self.world_map[my][mx] > 0:
                        hit = True;  wall_val = self.world_map[my][mx];  break

            if not hit:
                continue

            perp = (sdx - ddx) if side == 0 else (sdy - ddy)
            if perp < 0.001:
                continue
            self.z_buffer[x] = perp

            line_h = int(self.ray_h / perp)
            draw_s = horizon - line_h // 2
            draw_e = draw_s + line_h

            # Texture X coordinate
            if side == 0:
                wall_x = cam_y + perp * rdy
            else:
                wall_x = cam_x + perp * rdx
            wall_x -= math.floor(wall_x)
            tex_x = int(wall_x * TEX_SIZE)
            if (side == 0 and rdx > 0) or (side == 1 and rdy < 0):
                tex_x = TEX_SIZE - tex_x - 1
            tex_x = max(0, min(TEX_SIZE - 1, tex_x))

            tex_col  = self.textures[(wall_val - 1) % len(self.textures)][:, tex_x]
            y_s      = max(0, draw_s)
            y_e      = min(self.ray_h, draw_e)
            strip_h  = y_e - y_s
            if strip_h <= 0 or line_h <= 0:
                continue

            t_off   = y_s - draw_s
            indices = np.linspace(t_off, t_off + strip_h - 1, strip_h,
                                  dtype=np.float32)
            indices = (indices * TEX_SIZE / max(line_h, 1)).astype(np.int32)
            indices = np.clip(indices, 0, TEX_SIZE - 1)
            colors  = tex_col[indices].astype(np.float32)

            if side == 1:
                colors *= 0.52
            # Distance-based warm fog (slight amber tint in the distance)
            fog      = np.clip(6.0 / max(perp, 0.4), 0.12, 1.0)
            fog_warm = np.array([fog, fog * 0.92, fog * 0.80], dtype=np.float32)
            colors   = np.clip(colors * fog_warm, 0, 255)

            frame[x, y_s:y_e] = colors.astype(np.uint8)

        # ── 4. Sprite rendering ───────────────────────────────────────
        sorted_sp = sorted(sprites, key=lambda s: s['dist'], reverse=True)
        self._render_sprites(frame, sorted_sp,
                             cam_x, cam_y,
                             dir_x, dir_y, plane_x, plane_y, horizon)

        # ── 5. Vignette post-process ──────────────────────────────────
        frame = (frame.astype(np.float32) * self._vignette).astype(np.uint8)

        return pygame.surfarray.make_surface(frame)

    # ------------------------------------------------------------------
    # Sky
    # ------------------------------------------------------------------

    def _draw_sky(self, frame: np.ndarray, horizon: int) -> None:
        """PUBG-style sunset sky: deep navy → blue → warm amber at horizon."""
        if horizon <= 0:
            return
        t = np.linspace(0.0, 1.0, horizon, dtype=np.float32)  # (horizon,)

        # Three-colour gradient: deep navy → mid blue → warm amber/orange
        c0 = np.array([6,  16, 58],  dtype=np.float32)   # top
        c1 = np.array([30, 55, 120], dtype=np.float32)   # middle
        c2 = np.array([190, 100, 35], dtype=np.float32)  # horizon glow

        t1 = np.clip(t / 0.60, 0, 1)[:, np.newaxis]
        t2 = np.clip((t - 0.60) / 0.40, 0, 1)[:, np.newaxis]

        sky = np.where(t[:, np.newaxis] < 0.60,
                       c0 + t1 * (c1 - c0),
                       c1 + t2 * (c2 - c1)).astype(np.uint8)

        # Broadcast to all columns:  sky shape (horizon, 3) → frame shape (ray_w, ray_h, 3)
        frame[:, :horizon] = sky[np.newaxis, :, :]

    # ------------------------------------------------------------------
    # Floor / ceiling casting  (fully vectorised)
    # ------------------------------------------------------------------

    def _cast_floor_ceiling(self, frame, cam_x, cam_y,
                            dir_x, dir_y, plane_x, plane_y, horizon):
        ray_w  = self.ray_w
        ray_h  = self.ray_h
        half_h = ray_h / 2.0

        # Ray directions for leftmost and rightmost screen columns
        left_dx  = dir_x - plane_x;   left_dy  = dir_y - plane_y
        right_dx = dir_x + plane_x;   right_dy = dir_y + plane_y

        # Per-column interpolation factor  [0, 1]
        col_t = np.linspace(0.0, 1.0, ray_w, dtype=np.float32)  # (ray_w,)
        # Per-column ray directions
        ray_dx = left_dx + col_t * (right_dx - left_dx)   # (ray_w,)
        ray_dy = left_dy + col_t * (right_dy - left_dy)   # (ray_w,)

        # ── Floor (rows below horizon) ─────────────────────────────────
        floor_rows = np.arange(max(horizon + 1, 1), ray_h, dtype=np.float32)
        if floor_rows.size:
            p          = floor_rows - half_h                               # (n,)
            row_dist   = np.abs(half_h / np.maximum(np.abs(p), 0.1))      # (n,)

            # World coords for each (row, column)  — shape (n, ray_w)
            fx = cam_x + row_dist[:, None] * ray_dx[None, :]
            fy = cam_y + row_dist[:, None] * ray_dy[None, :]

            tx = (fx * TEX_SIZE).astype(np.int32) & (TEX_SIZE - 1)  # (n, ray_w)
            ty = (fy * TEX_SIZE).astype(np.int32) & (TEX_SIZE - 1)

            # Sample floor texture — shape (n, ray_w, 3)
            colors = self.floor_tex[ty, tx]

            # Per-row distance fog  (warm-tinted)
            fog = np.clip(4.0 / np.maximum(row_dist, 0.4), 0.08, 0.88)   # (n,)
            fog_warm = np.stack([fog, fog * 0.88, fog * 0.72], axis=-1)   # (n, 3)
            colors = np.clip(colors * fog_warm[:, None, :], 0, 255).astype(np.uint8)

            # Assign: frame[:, floor_start:ray_h] = colors.T_perm
            # frame shape (ray_w, ray_h, 3); colors shape (n, ray_w, 3)
            start = int(floor_rows[0])
            frame[:, start:ray_h] = colors.transpose(1, 0, 2)

        # ── Ceiling (rows above horizon) ──────────────────────────────
        ceil_rows = np.arange(0, min(horizon, ray_h), dtype=np.float32)
        if ceil_rows.size:
            p        = ceil_rows - half_h                                  # negative
            row_dist = np.abs(half_h / np.maximum(np.abs(p), 0.1))

            fx = cam_x + row_dist[:, None] * ray_dx[None, :]
            fy = cam_y + row_dist[:, None] * ray_dy[None, :]

            tx = (fx * TEX_SIZE).astype(np.int32) & (TEX_SIZE - 1)
            ty = (fy * TEX_SIZE).astype(np.int32) & (TEX_SIZE - 1)

            colors = self.ceil_tex[ty, tx]

            # Very dark ceiling — only hint of texture
            fog    = np.clip(2.0 / np.maximum(row_dist, 0.4), 0.03, 0.35)
            colors = np.clip(colors * fog[:, None, None], 0, 255).astype(np.uint8)

            end = int(ceil_rows[-1]) + 1
            # Blend over sky (sky already drawn; ceiling is dark, so just overlay)
            frame[:, :end] = np.maximum(frame[:, :end],
                                        colors.transpose(1, 0, 2))

    # ------------------------------------------------------------------
    # Sprite rendering
    # ------------------------------------------------------------------

    def _render_sprites(self, frame, sprites,
                        cam_x, cam_y,
                        dir_x, dir_y, plane_x, plane_y, horizon):
        det = plane_x * dir_y - dir_x * plane_y
        if abs(det) < 1e-9:
            det = 1e-9 if det >= 0 else -1e-9
        inv_det = 1.0 / det

        for sp in sprites:
            sx = sp['x'] - cam_x;  sy = sp['y'] - cam_y
            tx = inv_det * ( dir_y * sx - dir_x * sy)
            tz = inv_det * (-plane_y * sx + plane_x * sy)
            if tz < 0.12:
                continue

            screen_x = int((self.ray_w / 2) * (1.0 + tx / tz))
            sprite_h = abs(int(self.ray_h / tz))
            sprite_w = sprite_h

            draw_xs = screen_x - sprite_w // 2
            draw_xe = screen_x + sprite_w // 2
            draw_ys = horizon  - sprite_h // 2
            draw_ye = draw_ys  + sprite_h

            cxs = max(0, draw_xs);  cxe = min(self.ray_w, draw_xe)
            cys = max(0, draw_ys);  cye = min(self.ray_h, draw_ye)

            if cxs >= cxe or cys >= cye or sprite_h < 1 or sprite_w < 1:
                continue

            surf = sp.get('surf')
            if surf is None:
                continue

            scaled   = pygame.transform.scale(surf, (max(1, sprite_w),
                                                      max(1, sprite_h)))
            sp_rgb   = pygame.surfarray.array3d(scaled)
            sp_alpha = pygame.surfarray.array_alpha(scaled)

            sp_fog   = np.clip(6.0 / max(tz, 0.4), 0.15, 1.0)
            fog_warm = np.array([sp_fog, sp_fog * 0.92, sp_fog * 0.82],
                                dtype=np.float32)

            for col in range(cxs, cxe):
                if self.z_buffer[col] <= tz:
                    continue
                tc = col - draw_xs
                if tc < 0 or tc >= sp_rgb.shape[0]:
                    continue

                col_rgb   = sp_rgb[tc]
                col_alpha = sp_alpha[tc].astype(np.float32) / 255.0

                src_s = max(0, cys - draw_ys)
                src_e = min(sprite_h, src_s + (cye - cys))
                if src_s >= src_e:
                    continue

                rgb   = np.clip(col_rgb[src_s:src_e].astype(np.float32) * fog_warm,
                                0, 255).astype(np.uint8)
                alpha = col_alpha[src_s:src_e, np.newaxis]
                dst   = frame[col, cys:cye].astype(np.float32)
                frame[col, cys:cye] = (rgb * alpha + dst * (1.0 - alpha)).astype(np.uint8)

    # ------------------------------------------------------------------
    # Vignette (pre-computed)
    # ------------------------------------------------------------------

    def _build_vignette(self) -> np.ndarray:
        """Return (ray_w, ray_h, 1) float32 mask: 1.0 centre, ~0.3 corners."""
        cx = self.ray_w / 2.0;  cy = self.ray_h / 2.0
        xs = (np.arange(self.ray_w, dtype=np.float32) - cx) / cx     # -1..1
        ys = (np.arange(self.ray_h, dtype=np.float32) - cy) / cy
        dist = np.sqrt(xs[:, None] ** 2 + ys[None, :] ** 2) / math.sqrt(2)
        mask = np.clip(1.0 - dist ** 2.2 * 0.85, 0.18, 1.0)
        return mask[:, :, np.newaxis].astype(np.float32)
