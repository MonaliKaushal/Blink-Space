"""
ui.py – Right Panel UI: Webcam Feed, EAR Diagnostics, Instructions
===================================================================
Renders the 400×800 control tower panel using only Pygame surfaces.
"""

import math
import pygame
import cv2
import numpy as np

# ---------------------------------------------------------------------------
# Colours
# ---------------------------------------------------------------------------
C_BG        = (10,  10,  18)
C_PANEL_BG  = (12,  12,  24)
C_BORDER    = (30,  35,  60)
C_PLAYER    = (0,   255, 200)
C_RETICLE   = (255, 230, 0)
C_ASTEROID  = (240, 80,  80)
C_ACCENT    = (120, 80,  255)
C_TEXT      = (200, 200, 220)
C_DIM       = (100, 105, 130)
C_OPEN      = (0,   230, 130)
C_BLINK     = (240, 80,  80)
C_GAUGE_BG  = (25,  28,  50)
C_GAUGE_FG  = (0,   255, 200)

PANEL_W = 400
PANEL_H = 800

CAM_W   = 380
CAM_H   = 285          # 4:3 display area for webcam


# ---------------------------------------------------------------------------
# Utility: OpenCV frame → Pygame surface
# ---------------------------------------------------------------------------
def cv_frame_to_pygame(frame: np.ndarray, target_w: int, target_h: int) -> pygame.Surface:
    """Resize & convert a BGR OpenCV frame to a Pygame surface (RGB)."""
    resized = cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_LINEAR)
    rgb     = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
    # numpy array is already contiguous after resize; transpose to (W,H,3) for pygame
    surf    = pygame.surfarray.make_surface(rgb.swapaxes(0, 1))
    return surf


# ---------------------------------------------------------------------------
# EAR Gauge bar
# ---------------------------------------------------------------------------
def _draw_ear_gauge(surface: pygame.Surface, x: int, y: int,
                    width: int, height: int,
                    ear: float, threshold: float) -> None:
    """Horizontal bar showing current EAR vs threshold."""
    max_ear = 0.08
    ratio   = min(ear / max_ear, 1.0)
    filled  = int(width * ratio)

    # Background
    pygame.draw.rect(surface, C_GAUGE_BG, (x, y, width, height), border_radius=4)

    # Fill colour: green when open, red near blink
    if ear < threshold:
        colour = C_BLINK
    elif ear < threshold * 1.4:
        colour = C_RETICLE    # warning yellow
    else:
        colour = C_GAUGE_FG

    if filled > 0:
        pygame.draw.rect(surface, colour, (x, y, filled, height), border_radius=4)

    # Threshold marker
    thresh_x = x + int(width * (threshold / max_ear))
    thresh_x = min(thresh_x, x + width - 2)
    pygame.draw.line(surface, C_RETICLE, (thresh_x, y - 2), (thresh_x, y + height + 2), 2)


# ---------------------------------------------------------------------------
# Main UI renderer
# ---------------------------------------------------------------------------
class UIPanel:
    """
    Renders everything on the right 400×800 panel.
    Call `draw(surface, vision_result, threshold)` each frame.
    """

    def __init__(self):
        self._font_title  = pygame.font.SysFont("monospace", 17, bold=True)
        self._font_body   = pygame.font.SysFont("monospace", 13)
        self._font_small  = pygame.font.SysFont("monospace", 11)
        self._font_large  = pygame.font.SysFont("monospace", 28, bold=True)
        self._font_badge  = pygame.font.SysFont("monospace", 20, bold=True)

        self._ear_history : list[float] = []   # rolling buffer for sparkline

    # -----------------------------------------------------------------------
    def draw(self, surface: pygame.Surface,
             frame: np.ndarray,
             annotated_frame: np.ndarray,
             ear: float,
             state: str,
             threshold: float,
             score: int,
             game_state: str) -> None:

        surface.fill(C_PANEL_BG)

        # ── Section 1: Header bar ──────────────────────────────────────────
        self._draw_header(surface)

        # ── Section 2: Webcam feed ─────────────────────────────────────────
        cam_y = 44
        self._draw_cam_feed(surface, annotated_frame, cam_y)

        # ── Section 3: EAR / State diagnostics ────────────────────────────
        diag_y = cam_y + CAM_H + 10
        self._draw_diagnostics(surface, ear, state, threshold, diag_y)

        # ── Section 4: Instructions ────────────────────────────────────────
        instr_y = diag_y + 195
        self._draw_instructions(surface, instr_y, score, game_state)

        # Vertical separator line on left edge of panel
        pygame.draw.line(surface, C_BORDER, (0, 0), (0, PANEL_H), 2)

    # -----------------------------------------------------------------------
    # Section renderers
    # -----------------------------------------------------------------------

    def _draw_header(self, surface: pygame.Surface) -> None:
        pygame.draw.rect(surface, (15, 15, 32), (0, 0, PANEL_W, 40))
        pygame.draw.line(surface, C_BORDER, (0, 40), (PANEL_W, 40), 1)

        title = self._font_title.render("◈  CONTROL  TOWER", True, C_ACCENT)
        surface.blit(title, (PANEL_W // 2 - title.get_width() // 2, 10))

    def _draw_cam_feed(self, surface: pygame.Surface,
                       annotated_frame: np.ndarray, y: int) -> None:
        # Border
        border_rect = pygame.Rect(8, y - 2, CAM_W + 4, CAM_H + 4)
        pygame.draw.rect(surface, C_BORDER, border_rect, 1, border_radius=4)

        # Camera frame
        cam_surf = cv_frame_to_pygame(annotated_frame, CAM_W, CAM_H)
        surface.blit(cam_surf, (10, y))

        # Corner accent brackets
        blen = 12
        for bx, by, xd, yd in [
            (10, y, 1, 1), (10 + CAM_W, y, -1, 1),
            (10, y + CAM_H, 1, -1), (10 + CAM_W, y + CAM_H, -1, -1)
        ]:
            pygame.draw.line(surface, C_PLAYER, (bx, by), (bx + blen * xd, by), 2)
            pygame.draw.line(surface, C_PLAYER, (bx, by), (bx, by + blen * yd), 2)

        # Label
        lbl = self._font_small.render("LIVE EYE FEED", True, C_DIM)
        surface.blit(lbl, (10, y + CAM_H + 4))

    def _draw_diagnostics(self, surface: pygame.Surface,
                           ear: float, state: str,
                           threshold: float, y: int) -> None:
        pad = 10
        sect_w = PANEL_W - pad * 2

        # Section title
        t = self._font_body.render("EYE TRACKING DIAGNOSTICS", True, C_ACCENT)
        surface.blit(t, (pad, y))
        pygame.draw.line(surface, C_BORDER, (pad, y + 18), (PANEL_W - pad, y + 18), 1)
        y += 26

        # State badge ● OPEN / ● BLINKING
        badge_colour = C_OPEN if state == "OPEN" else C_BLINK
        badge_text   = f"●  {state}"
        badge_surf   = self._font_badge.render(badge_text, True, badge_colour)

        # Animated glow behind badge
        glow_r = 34
        gs = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
        pygame.draw.circle(gs, (*badge_colour, 25), (glow_r, glow_r), glow_r)
        surface.blit(gs, (PANEL_W - glow_r * 2 - pad, y - 6))

        surface.blit(badge_surf, (pad, y))
        y += 34

        # EAR value
        ear_label = self._font_body.render(
            f"EAR  {ear:.4f}   THRESH {threshold:.4f}", True, C_TEXT
        )
        surface.blit(ear_label, (pad, y))
        y += 22

        # Gauge bar
        _draw_ear_gauge(surface, pad, y, sect_w, 14, ear, threshold)
        y += 22

        # Threshold hint
        hint = self._font_small.render("[+] raise threshold    [-] lower threshold", True, C_DIM)
        surface.blit(hint, (pad, y))
        y += 20

        # Sparkline (rolling EAR history)
        self._ear_history.append(ear)
        if len(self._ear_history) > sect_w:
            self._ear_history.pop(0)

        self._draw_sparkline(surface, pad, y, sect_w, 40, threshold)
        y += 48

        # Grid lines for sparkline
        spark_label = self._font_small.render("EAR HISTORY", True, C_DIM)
        surface.blit(spark_label, (pad, y))

    def _draw_sparkline(self, surface: pygame.Surface,
                        x: int, y: int, w: int, h: int,
                        threshold: float) -> None:
        max_ear = 0.08
        pygame.draw.rect(surface, C_GAUGE_BG, (x, y, w, h), border_radius=3)

        if len(self._ear_history) < 2:
            return

        # Threshold line
        ty = y + h - int(h * (threshold / max_ear))
        pygame.draw.line(surface, (80, 70, 0), (x, ty), (x + w, ty), 1)

        pts = []
        n   = len(self._ear_history)
        for i, v in enumerate(self._ear_history):
            px = x + int(i * w / max(n - 1, 1))
            py = y + h - int(h * min(v / max_ear, 1.0))
            pts.append((px, py))

        if len(pts) >= 2:
            pygame.draw.lines(surface, C_GAUGE_FG, False, pts, 1)

        # Latest dot
        pygame.draw.circle(surface, C_RETICLE, pts[-1], 3)

    def _draw_instructions(self, surface: pygame.Surface,
                            y: int, score: int, game_state: str) -> None:
        pad = 10

        # Divider
        pygame.draw.line(surface, C_BORDER, (pad, y), (PANEL_W - pad, y), 1)
        y += 10

        # Score display
        sc_label = self._font_small.render("CURRENT SCORE", True, C_DIM)
        surface.blit(sc_label, (pad, y))
        sc_val = self._font_large.render(f"{score:06d}", True, C_RETICLE)
        surface.blit(sc_val, (pad, y + 14))
        y += 56

        pygame.draw.line(surface, C_BORDER, (pad, y), (PANEL_W - pad, y), 1)
        y += 10

        # How to play
        title = self._font_body.render("HOW  TO  PLAY", True, C_ACCENT)
        surface.blit(title, (pad, y))
        y += 22

        steps = [
            ("①", "BLINK  to fire a bullet"),
            ("②", "Aim with the GOLD ORB orbiting"),
            ("  ", "your ship — time your blink!"),
            ("③", "Destroy RED asteroids for"),
            ("  ", "+100 pts each"),
            ("④", "Don't let asteroids reach"),
            ("  ", "your ship core!"),
        ]
        for icon, text in steps:
            ic = self._font_body.render(icon, True, C_RETICLE)
            tx = self._font_body.render(text, True, C_TEXT)
            surface.blit(ic, (pad,      y))
            surface.blit(tx, (pad + 22, y))
            y += 20

        y += 8
        pygame.draw.line(surface, C_BORDER, (pad, y), (PANEL_W - pad, y), 1)
        y += 8

        # Game state hint
        if game_state == "GAME_OVER":
            hint = "Hold BLINK 2s  or  [R] to restart"
            colour = C_ASTEROID
        elif game_state == "MENU":
            hint = "BLINK  or  [SPACE] to start"
            colour = C_OPEN
        else:
            hint = "[SPACE] = manual fire  |  [Q] = quit"
            colour = C_DIM

        ht = self._font_small.render(hint, True, colour)
        surface.blit(ht, (pad, y))
