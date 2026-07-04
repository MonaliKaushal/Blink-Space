"""
main.py – Blink Space FPS: Entry Point & Game Loop  (Visual Polish Edition)
=============================================================================
Window:  1280 × 720
  Left   960 × 720  → 3-D raycasted FPS view  (rendered at 480×360, scaled 2×)
  Right  320 × 720  → Webcam feed + diagnostics panel

Controls
--------
  Head left / right   →  Rotate camera
  Blink               →  FIRE
  [SPACE]             →  Manual fire (keyboard fallback)
  [R]                 →  Restart
  [+] / [-]           →  Blink threshold
  [Q] / [ESC]         →  Quit
"""

import sys
import math
import random

import cv2
import pygame
import numpy as np

from vision    import EyeTracker
from raycaster import Raycaster, make_enemy_sprites
from game      import GameWorld, WORLD_MAP
from hud       import HUD
from particles import ScreenShake, Particle, Explosion
from sounds    import SoundManager

# ---------------------------------------------------------------------------
# Window / render config
# ---------------------------------------------------------------------------
WIN_W        = 1280
WIN_H        = 720
GAME_PANEL_W = 960
SIDE_PANEL_W = 320

RAY_W  = 480
RAY_H  = 360

TARGET_FPS   = 60
CAMERA_INDEX = 0


# ---------------------------------------------------------------------------
# Blood burst  (2-D screen-space particles on enemy hit)
# ---------------------------------------------------------------------------
def _spawn_blood(particles: list, screen_x: float, screen_y: float) -> None:
    for _ in range(14):
        angle = random.uniform(0, math.tau)
        speed = random.uniform(80, 280)
        life  = random.uniform(0.25, 0.55)
        particles.append(Particle(screen_x, screen_y, angle, speed,
                                  (220, 20, 20), (80, 10, 10), life))


def _enemy_screen_pos(enemy, world, raycaster: Raycaster) -> tuple[int, int] | None:
    """Project enemy world pos to display-panel screen coords."""
    cam_angle = world.cam_angle
    dir_x  =  math.cos(cam_angle)
    dir_y  =  math.sin(cam_angle)
    plane_x = -dir_y  * raycaster.plane_mag
    plane_y =  dir_x  * raycaster.plane_mag
    det = plane_x * dir_y - dir_x * plane_y
    if abs(det) < 1e-9:
        det = 1e-9 if det >= 0 else -1e-9
    inv_det = 1.0 / det

    sx = enemy.x - world.player_x
    sy = enemy.y - world.player_y
    tx =  inv_det * ( dir_y  * sx - dir_x  * sy)
    tz =  inv_det * (-plane_y * sx + plane_x * sy)
    if tz < 0.1:
        return None

    # Position in render space → scale to display panel
    rx = int((RAY_W / 2) * (1.0 + tx / tz))
    ry = RAY_H // 2
    scale_x = GAME_PANEL_W / RAY_W
    scale_y = WIN_H         / RAY_H
    return (int(rx * scale_x), int(ry * scale_y))


def _world_to_screen_pos(wx: float, wy: float, world, raycaster: Raycaster) -> tuple[int, int] | None:
    """Project generic world coordinates to display-panel screen coordinates."""
    cam_angle = world.cam_angle
    dir_x  =  math.cos(cam_angle)
    dir_y  =  math.sin(cam_angle)
    plane_x = -dir_y  * raycaster.plane_mag
    plane_y =  dir_x  * raycaster.plane_mag
    det = plane_x * dir_y - dir_x * plane_y
    if abs(det) < 1e-9:
        det = 1e-9 if det >= 0 else -1e-9
    inv_det = 1.0 / det

    sx = wx - world.player_x
    sy = wy - world.player_y
    tx =  inv_det * ( dir_y  * sx - dir_x  * sy)
    tz =  inv_det * (-plane_y * sx + plane_x * sy)
    if tz < 0.1:
        return None

    rx = int((RAY_W / 2) * (1.0 + tx / tz))
    ry = RAY_H // 2
    scale_x = GAME_PANEL_W / RAY_W
    scale_y = WIN_H         / RAY_H
    return (int(rx * scale_x), int(ry * scale_y))


# ---------------------------------------------------------------------------
# Side-panel renderer
# ---------------------------------------------------------------------------
def _draw_side_panel(surface: pygame.Surface, vision,
                     tracker: EyeTracker, world: GameWorld,
                     fps: float) -> None:
    surface.fill((6, 9, 6))
    sw, sh = surface.get_size()

    def lbl(text, size, color, bold=False):
        for name in ("segoeui", "calibri", "arial", "consolas"):
            try:
                f = pygame.font.SysFont(name, size, bold=bold)
                break
            except Exception:
                continue
        return f.render(text, True, color)

    y = 10
    surface.blit(lbl("◈ BLINK SPACE FPS", 15, (0, 210, 100), True), (10, y));  y += 28

    # Annotated webcam
    annotated = tracker.draw_overlay(vision.frame)
    rgb       = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
    cam_w, cam_h = sw - 20, int((sw - 20) * 0.75)
    small     = cv2.resize(rgb, (cam_w, cam_h))
    cam_surf  = pygame.surfarray.make_surface(small.transpose(1, 0, 2))
    surface.blit(cam_surf, (10, y))
    pygame.draw.rect(surface, (0, 170, 80), pygame.Rect(10, y, cam_w, cam_h), 1)
    y += cam_h + 10

    # EAR bar
    ear = vision.ear;  thr = tracker.threshold
    bar_w = sw - 20
    pygame.draw.rect(surface, (12, 22, 12), (10, y, bar_w, 12))
    fill = int(bar_w * min(ear / 0.04, 1.0))
    bc   = (45, 185, 65) if vision.state == "OPEN" else (205, 45, 45)
    if fill > 0:
        pygame.draw.rect(surface, bc, (10, y, fill, 12))
    tx = 10 + int(bar_w * min(thr / 0.04, 1.0))
    pygame.draw.line(surface, (255, 205, 0), (tx, y), (tx, y + 12), 2)
    y += 14

    sc = (45, 215, 75) if vision.state == "OPEN" else (215, 55, 55)
    surface.blit(lbl(f"● {vision.state:10s}  EAR {ear:.4f}", 12, sc), (10, y));  y += 18
    surface.blit(lbl(f"  CAMERA INDEX: {tracker.camera_index}  ([C] to cycle)", 11, (110, 185, 110)), (10, y));  y += 16
    surface.blit(lbl(f"  THRESHOLD  {thr:.4f}  (+/- to adjust)", 11,
                     (130, 150, 130)), (10, y));  y += 22

    # Head pose bar
    surface.blit(lbl("HEAD YAW", 11, (150, 190, 150)), (10, y));  y += 14
    pygame.draw.rect(surface, (12, 22, 12), (10, y, sw - 20, 8))
    pygame.draw.rect(surface, (0, 170, 210), (10 + (sw - 20) // 2, y, 1, 8))
    yaw_px = int((sw - 20) / 2 * (1 + vision.head_yaw))
    if 0 <= yaw_px <= sw - 20:
        pygame.draw.rect(surface, (0, 215, 195), (10 + yaw_px - 4, y, 8, 8))
    y += 12
    surface.blit(lbl(f"yaw {vision.head_yaw:+.2f}   pitch {vision.head_pitch:+.2f}",
                     11, (120, 150, 120)), (10, y));  y += 22

    pygame.draw.line(surface, (0, 55, 28), (10, y), (sw - 10, y), 1);  y += 8

    # Stats
    surface.blit(lbl(f"WAVE    {world.wave}",    13, (255, 195, 55), True), (10, y));  y += 18
    surface.blit(lbl(f"KILLS   {world.kills}",   13, (170, 215, 170)),       (10, y));  y += 18
    surface.blit(lbl(f"SCORE   {world.score}",   13, (90, 175, 255)),        (10, y));  y += 18
    surface.blit(lbl(f"HEALTH  {world.player_hp}", 13, (215, 75, 75)),       (10, y));  y += 22

    pygame.draw.line(surface, (0, 55, 28), (10, y), (sw - 10, y), 1);  y += 8
    hints = [("BLINK", "Fire"), ("SPACE", "Fire (backup)"),
             ("R", "Restart"), ("C", "Cycle Camera"), ("+/-", "Sensitivity"), ("ESC", "Quit")]
    for key, action in hints:
        surface.blit(lbl(f"[{key}]  {action}", 11, (90, 120, 90)), (10, y));  y += 14

    surface.blit(lbl(f"FPS  {fps:.0f}", 11, (55, 85, 55)), (sw - 55, sh - 16))


# ---------------------------------------------------------------------------
# Fatal error
# ---------------------------------------------------------------------------
def _show_fatal(msg: str) -> None:
    pygame.init()
    screen = pygame.display.set_mode((680, 220))
    pygame.display.set_caption("Blink Space FPS – Error")
    font  = pygame.font.SysFont("monospace", 15)
    clock = pygame.time.Clock()
    while True:
        for ev in pygame.event.get():
            if ev.type in (pygame.QUIT, pygame.KEYDOWN):
                pygame.quit();  sys.exit(1)
        screen.fill((16, 6, 6))
        for i, line in enumerate(msg.split("\n")):
            screen.blit(font.render(line, True, (215, 65, 65)), (20, 20 + i * 22))
        pygame.display.flip();  clock.tick(30)


# ---------------------------------------------------------------------------
# Enemy-lock check
# ---------------------------------------------------------------------------
def _check_enemy_locked(world: GameWorld, raycaster: Raycaster) -> bool:
    cam_angle = world.cam_angle
    dir_x  =  math.cos(cam_angle)
    dir_y  =  math.sin(cam_angle)
    plane_x = -dir_y  * raycaster.plane_mag
    plane_y =  dir_x  * raycaster.plane_mag
    det = plane_x * dir_y - dir_x * plane_y
    if abs(det) < 1e-9:
        det = 1e-9 if det >= 0 else -1e-9
    inv_det = 1.0 / det
    center  = RAY_W // 2

    for enemy in world.enemies:
        if not enemy.alive or enemy.state == "dead":
            continue
        sx = enemy.x - world.player_x
        sy = enemy.y - world.player_y
        tx =  inv_det * ( dir_y  * sx - dir_x  * sy)
        tz =  inv_det * (-plane_y * sx + plane_x * sy)
        if tz < 0.1:
            continue
        screen_x = int((RAY_W / 2) * (1.0 + tx / tz))
        half_w   = max(abs(int(RAY_H / tz)) // 2, 12)
        if abs(screen_x - center) <= half_w:
            buf = raycaster.z_buffer
            if tz < buf[min(center, len(buf) - 1)]:
                return True
    return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    pygame.init()
    pygame.display.set_caption("✦ BLINK SPACE FPS  —  Head-Controlled Shooter")

    screen = pygame.display.set_mode((WIN_W, WIN_H))
    clock  = pygame.time.Clock()

    game_surf = screen.subsurface(pygame.Rect(0,            0, GAME_PANEL_W, WIN_H))
    side_surf = screen.subsurface(pygame.Rect(GAME_PANEL_W, 0, SIDE_PANEL_W, WIN_H))

    # ── Subsystems ─────────────────────────────────────────────────────
    try:
        tracker = EyeTracker(camera_index=CAMERA_INDEX)
    except RuntimeError as exc:
        _show_fatal(f"Camera Error:\n{exc}\n\nPress any key to quit.")
        return

    sound_manager = SoundManager()
    sound_manager.start_music()
    enemy_sprites = make_enemy_sprites()
    raycaster     = Raycaster(RAY_W, RAY_H, WORLD_MAP)
    world         = GameWorld(enemy_sprites, sound_manager)
    hud           = HUD()
    shake         = ScreenShake(decay=0.78)
    blood_parts   : list[Particle]   = []
    explosions    : list[Explosion]  = []

    # ── Main loop ───────────────────────────────────────────────────────
    running = True
    while running:
        dt = min(clock.tick(TARGET_FPS) / 1000.0, 0.05)

        # ── 1. Vision ───────────────────────────────────────────────────
        vision = tracker.read()

        # ── 2. Fire Trigger Check ───────────────────────────────────────
        fire_triggered = False
        grenade_triggered = False

        # Events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_q, pygame.K_ESCAPE):
                    running = False
                elif event.key == pygame.K_r:
                    world = GameWorld(enemy_sprites, sound_manager)
                    hud   = HUD()
                    shake = ScreenShake(decay=0.78)
                    blood_parts.clear();  explosions.clear()
                elif event.key == pygame.K_SPACE:
                    fire_triggered = True
                elif event.key == pygame.K_g:
                    grenade_triggered = True
                elif event.key in (pygame.K_EQUALS, pygame.K_PLUS):
                    tracker.adjust_threshold(+0.002)
                elif event.key == pygame.K_MINUS:
                    tracker.adjust_threshold(-0.002)
                elif event.key == pygame.K_c:
                    # Cycle through camera indices (0, 1, 2)
                    new_idx = (tracker.camera_index + 1) % 3
                    tracker.switch_camera(new_idx)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 3:  # Right Click
                    grenade_triggered = True

        # Blink event
        if vision.blink_fired:
            fire_triggered = True

        # Automatic firing check (holding key or keeping eyes blinking/closed)
        keys = pygame.key.get_pressed()
        trigger_held = keys[pygame.K_SPACE] or (vision.state == "BLINKING")

        if world.current_weapon.automatic and trigger_held:
            if world._reload_cooldown <= 0:
                fire_triggered = True

        # Process Fire
        if fire_triggered and world._reload_cooldown <= 0:
            hit, killed = world.fire()
            hud.trigger_shoot()
            shake.trigger(4.0 + world.weapon_knockback)
            world.weapon_knockback = 0.0
            _handle_hit(hit, killed, hud, shake, blood_parts,
                        explosions, world, raycaster)

        # Process Grenade
        if grenade_triggered:
            if world.duck_grenades > 0:
                if world.grenade_cooldown <= 0:
                    success = world.throw_grenade()
                    if success:
                        shake.trigger(5.0)
            else:
                hud.trigger_no_grenades()
                if sound_manager:
                    sound_manager.play("melee_swing")

        # ── 3. Update ───────────────────────────────────────────────────
        prev_grenades = world.duck_grenades
        prev_hp = world.player_hp
        world.update(dt,
                     head_yaw     = vision.head_yaw,
                     head_pitch   = vision.head_pitch,
                     blink_fired  = False,
                     trigger_held = trigger_held)
        hud.update(dt)

        if world.duck_grenades > prev_grenades:
            hud.trigger_grenade_pickup(world.duck_grenades - prev_grenades)

        if world.player_hp < prev_hp:   # player took damage
            shake.trigger(10.0)

        # Update particles
        shake_dx, shake_dy = shake.update()
        for p in blood_parts:
            p.update(dt)
        blood_parts = [p for p in blood_parts if p.alive]
        for ex in explosions:
            ex.update(dt)
        explosions = [ex for ex in explosions if ex.alive]

        # Process pending world explosions from DuckProjectile
        if hasattr(world, 'explosion_events') and world.explosion_events:
            for wx, wy, is_duck in world.explosion_events:
                screen_pos = _world_to_screen_pos(wx, wy, world, raycaster)
                if screen_pos:
                    if is_duck:
                        shake.trigger(15.0)
                        # Spawn multiple yellow/orange feather explosions
                        for _ in range(4):
                            ox = screen_pos[0] + random.randint(-40, 40)
                            oy = screen_pos[1] + random.randint(-40, 40)
                            explosions.append(
                                Explosion(ox, oy,
                                          colour_core=(255, 230, 60),
                                          colour_edge=(240, 120, 20),
                                          n_particles=18)
                            )
            world.explosion_events.clear()

        # ── 5. Render 3-D view ──────────────────────────────────────────
        sprites   = world.get_sprites()
        raw_frame = raycaster.render(
            world.player_x, world.player_y,
            world.cam_angle, world.cam_pitch,
            sprites,
        )
        world.set_zbuffer(raycaster.z_buffer, RAY_W)

        # Scale & blit (apply shake offset)
        scaled = pygame.transform.scale(raw_frame, (GAME_PANEL_W, WIN_H))
        game_surf.blit(scaled, (shake_dx, shake_dy))

        # ── 6. Blood particles ──────────────────────────────────────────
        for p in blood_parts:
            p.draw(game_surf)
        for ex in explosions:
            ex.draw(game_surf)

        # ── 7. HUD overlay ──────────────────────────────────────────────
        enemy_locked = _check_enemy_locked(world, raycaster)
        vision_data  = {
            'frame':     vision.frame,
            'ear':       vision.ear,
            'state':     vision.state,
            'threshold': tracker.threshold,
        }
        hud.draw(game_surf, world, vision_data, enemy_locked)

        # ── 8. Side panel ───────────────────────────────────────────────
        _draw_side_panel(side_surf, vision, tracker, world,
                         fps=clock.get_fps())

        pygame.display.flip()

    tracker.release()
    pygame.quit()
    sys.exit(0)


# ---------------------------------------------------------------------------
# Hit handling helper
# ---------------------------------------------------------------------------
def _handle_hit(hit, killed: bool, hud: HUD, shake: ScreenShake,
                blood_parts: list, explosions: list,
                world: GameWorld, raycaster: Raycaster) -> None:
    if hit is None:
        return

    # HUD feedback
    hud.trigger_hit(kill=killed)

    # Lifesteal feedback
    if getattr(world, '_lifesteal_triggered', False):
        hud.trigger_heal(6)

    # Screen shake & explosions/blood depending on weapon type
    pos = _enemy_screen_pos(hit, world, raycaster)
    if world.current_weapon.id == "grenade_launcher":
        shake.trigger(12.0)
        if pos:
            # Spawn cluster of fiery explosions for splash effect
            for _ in range(4):
                ox = pos[0] + random.randint(-35, 35)
                oy = pos[1] + random.randint(-35, 35)
                explosions.append(
                    Explosion(ox, oy,
                              colour_core=(255, 130, 30),
                              colour_edge=(180, 40, 10),
                              n_particles=15)
                )
    else:
        shake.trigger(6.0 if killed else 3.0)
        if pos:
            _spawn_blood(blood_parts, pos[0], pos[1])
            if killed:
                explosions.append(
                    Explosion(pos[0], pos[1],
                              colour_core=(220, 30, 30),
                              colour_edge=(80, 10, 10),
                              n_particles=20)
                )


if __name__ == "__main__":
    main()
