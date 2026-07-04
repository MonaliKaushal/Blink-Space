"""
sounds.py – Procedural Audio Synthesis System
===============================================
Generates high-quality sound effects mathematically at runtime using numpy.
This avoids requiring external asset downloads and works out-of-the-box.
"""

import numpy as np
import pygame
import random

class SoundManager:
    def __init__(self):
        self.enabled = False
        self.sounds = {}

        # Safely try to initialize the mixer
        try:
            # Initialize with standard settings: 44.1kHz, 16-bit signed, stereo, 512 buffer
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            self.enabled = True
        except Exception as e:
            print(f"[SoundManager] Warning: Audio mixer could not be initialized: {e}")
            print("[SoundManager] Running in silent fallback mode.")
            return

        if self.enabled:
            self._generate_sounds()

    def play(self, name: str) -> None:
        """Play a procedurally synthesized sound effect by name."""
        if not self.enabled or name not in self.sounds:
            return
        try:
            self.sounds[name].play()
        except Exception:
            pass # catch playing errors if audio output fails momentarily

    def start_music(self) -> None:
        """Start playing procedural background music on a looped channel."""
        if not self.enabled or "bg_music" not in self.sounds:
            return
        try:
            pygame.mixer.Channel(7).play(self.sounds["bg_music"], loops=-1)
            pygame.mixer.Channel(7).set_volume(0.55) # Loud enough to hear clearly
        except Exception as e:
            print(f"[SoundManager] Error playing music: {e}")

    def _generate_sounds(self):
        """Synthesize all game sound effects and load them as pygame.mixer.Sound."""
        sample_rate = 44100

        # Helper to create a stereo Pygame Sound from mono float data [-1.0, 1.0]
        def to_sound(mono_data: np.ndarray) -> pygame.mixer.Sound:
            # Clamp range to avoid clipping distortion
            clamped = np.clip(mono_data, -1.0, 1.0)
            # Convert to 16-bit signed integers
            int_data = (clamped * 32767).astype(np.int16)
            # Stack into stereo (Left, Right)
            stereo = np.column_stack((int_data, int_data))
            return pygame.sndarray.make_sound(stereo)

        # -------------------------------------------------------------------
        # 1. Pistol Fire: Snappy bang
        # -------------------------------------------------------------------
        dur = 0.15
        t = np.linspace(0, dur, int(sample_rate * dur), False)
        freq = 900 - 700 * (t / dur)
        sine = np.sin(2 * np.pi * freq * t)
        noise = np.random.uniform(-0.8, 0.8, len(t))
        env = np.exp(-12 * t / dur)
        audio = (0.4 * sine + 0.6 * noise) * env
        self.sounds["pistol_fire"] = to_sound(audio)

        # -------------------------------------------------------------------
        # 2. Gatling Fire: Extremely quick snap
        # -------------------------------------------------------------------
        dur = 0.08
        t = np.linspace(0, dur, int(sample_rate * dur), False)
        freq = 1100 - 800 * (t / dur)
        sine = np.sin(2 * np.pi * freq * t)
        noise = np.random.uniform(-0.9, 0.9, len(t))
        env = np.exp(-18 * t / dur)
        audio = (0.3 * sine + 0.7 * noise) * env
        self.sounds["gatling_fire"] = to_sound(audio)

        # -------------------------------------------------------------------
        # 3. Blunderbuss Fire: Heavy shotgun burst
        # -------------------------------------------------------------------
        dur = 0.45
        t = np.linspace(0, dur, int(sample_rate * dur), False)
        freq = 300 - 240 * (t / dur)
        sine = np.sin(2 * np.pi * freq * t)
        noise = np.random.uniform(-1.0, 1.0, len(t))
        env = np.exp(-7 * t / dur)
        audio = (0.25 * sine + 0.75 * noise) * env
        self.sounds["blunderbuss_fire"] = to_sound(audio)

        # -------------------------------------------------------------------
        # 4. Grenade Fire: Hollow pop / launch thump
        # -------------------------------------------------------------------
        dur = 0.22
        t = np.linspace(0, dur, int(sample_rate * dur), False)
        freq = 350 - 280 * (t / dur)
        sine = np.sin(2 * np.pi * freq * t)
        env = np.exp(-9 * t / dur)
        audio = sine * env
        self.sounds["grenade_fire"] = to_sound(audio)

        # -------------------------------------------------------------------
        # 5. Grenade Explosion: Deep rumble + distortion explosion
        # -------------------------------------------------------------------
        dur = 0.85
        t = np.linspace(0, dur, int(sample_rate * dur), False)
        freq = 120 - 90 * (t / dur)
        sine = np.sin(2 * np.pi * freq * t)
        noise = np.random.uniform(-1.0, 1.0, len(t))
        env = np.exp(-4 * t / dur)
        audio = (0.2 * sine + 0.8 * noise) * env
        # Apply a bit of overdrive distortion
        audio = np.tanh(audio * 1.5)
        self.sounds["grenade_explosion"] = to_sound(audio)

        # -------------------------------------------------------------------
        # 6. Melee Swing (Cutlass / Crowbar): Quiet whistle
        # -------------------------------------------------------------------
        dur = 0.16
        t = np.linspace(0, dur, int(sample_rate * dur), False)
        freq = 650 - 400 * (t / dur)
        sine = np.sin(2 * np.pi * freq * t)
        noise = np.random.uniform(-0.15, 0.15, len(t)) # low level noise
        env = np.sin(np.pi * (t / dur)) # bell shape envelope
        audio = (0.8 * sine + 0.2 * noise) * env * 0.45
        self.sounds["melee_swing"] = to_sound(audio)

        # -------------------------------------------------------------------
        # 7. Melee Hit: Metallic slice clang
        # -------------------------------------------------------------------
        dur = 0.12
        t = np.linspace(0, dur, int(sample_rate * dur), False)
        # High metallic ping + noise crunch
        freq = 1800 - 1300 * (t / dur)
        sine = np.sin(2 * np.pi * freq * t)
        noise = np.random.uniform(-0.8, 0.8, len(t))
        env = np.exp(-15 * t / dur)
        audio = (0.5 * sine + 0.5 * noise) * env
        self.sounds["melee_hit"] = to_sound(audio)

        # -------------------------------------------------------------------
        # 8. Player Hurt: Deep grunt
        # -------------------------------------------------------------------
        dur = 0.25
        t = np.linspace(0, dur, int(sample_rate * dur), False)
        freq = 140 - 80 * (t / dur)
        sine = np.sin(2 * np.pi * freq * t)
        noise = np.random.uniform(-0.3, 0.3, len(t))
        env = np.sin(np.pi * (t / dur)) * np.exp(-3 * t / dur)
        audio = (0.7 * sine + 0.3 * noise) * env * 0.7
        self.sounds["player_hurt"] = to_sound(audio)

        # -------------------------------------------------------------------
        # 9. Lifesteal: High rising chimes arpeggio
        # -------------------------------------------------------------------
        dur = 0.4
        t = np.linspace(0, dur, int(sample_rate * dur), False)
        audio = np.zeros_like(t)
        # 4 distinct rising note waves mixed together at offsets
        notes = [440, 554, 659, 880]
        step_len = len(t) // len(notes)
        for idx, freq_val in enumerate(notes):
            start = idx * step_len
            t_sub = t[start:]
            wave_sub = np.sin(2 * np.pi * freq_val * (t_sub - t_sub[0]))
            env_sub = np.exp(-14 * (t_sub - t_sub[0]) / dur)
            audio[start:] += wave_sub * env_sub * 0.28
        self.sounds["lifesteal"] = to_sound(audio)

        # -------------------------------------------------------------------
        # 10. Wave Start Fanfare: Rising minor-to-major synth chord
        # -------------------------------------------------------------------
        dur = 0.8
        t = np.linspace(0, dur, int(sample_rate * dur), False)
        audio = np.zeros_like(t)
        # Synth chord note frequencies (C4, E4, G4, C5)
        chords = [261.63, 329.63, 392.00, 523.25]
        env = np.exp(-3.5 * t / dur) * np.sin(np.pi * (t / dur))
        for freq_val in chords:
            audio += np.sin(2 * np.pi * freq_val * t) * env * 0.16
        self.sounds["wave_intro"] = to_sound(audio)

        # -------------------------------------------------------------------
        # 11. Game Over Fanfare: Descending somber sweep
        # -------------------------------------------------------------------
        dur = 1.3
        t = np.linspace(0, dur, int(sample_rate * dur), False)
        audio = np.zeros_like(t)
        notes = [220.00, 261.63, 329.63] # Minor triad (A3, C4, E4)
        env = np.exp(-2.2 * t / dur)
        for freq_val in notes:
            # Slowly pitch drop the chords
            audio += np.sin(2 * np.pi * (freq_val - 40 * (t / dur)) * t) * env * 0.22
        self.sounds["game_over"] = to_sound(audio)

        # -------------------------------------------------------------------
        # 12. Duck Squeak: High-pitched rubber duck squeak
        # -------------------------------------------------------------------
        dur = 0.14
        t = np.linspace(0, dur, int(sample_rate * dur), False)
        freq = 1200 + 800 * np.sin(np.pi * (t / dur))
        sine = np.sin(2 * np.pi * freq * t)
        env = np.sin(np.pi * (t / dur))
        audio = sine * env * 0.45
        self.sounds["duck_squeak"] = to_sound(audio)

        # -------------------------------------------------------------------
        # 13. Duck Explosion: Loud quacking detonation
        # -------------------------------------------------------------------
        dur = 0.95
        t = np.linspace(0, dur, int(sample_rate * dur), False)
        # Base explosion rumble
        freq_exp = 110 - 80 * (t / dur)
        sine_exp = np.sin(2 * np.pi * freq_exp * t)
        noise = np.random.uniform(-1.0, 1.0, len(t))
        env_exp = np.exp(-3.5 * t / dur)
        audio_exp = (0.2 * sine_exp + 0.8 * noise) * env_exp
        audio_exp = np.tanh(audio_exp * 1.6) # distorted rumble

        # Quack component
        q_dur = 0.45
        q_len = int(sample_rate * q_dur)
        t_q = t[:q_len]
        f_q = 550 + 350 * np.sin(np.pi * (t_q / q_dur))
        quack = np.sin(2 * np.pi * f_q * t_q) + 0.5 * np.sin(2 * np.pi * f_q * 1.45 * t_q)
        quack += np.random.uniform(-0.15, 0.15, len(t_q)) # raspy / nasal
        q_env = np.sin(np.pi * (t_q / q_dur)) * np.exp(-4 * t_q / q_dur)
        audio_quack = quack * q_env * 0.70

        mixed = audio_exp.copy()
        mixed[:len(audio_quack)] += audio_quack
        self.sounds["duck_explosion"] = to_sound(mixed)

        # -------------------------------------------------------------------
        # 14. Crowbar Swing: Heavy swoosh / metal resonance
        # -------------------------------------------------------------------
        dur = 0.28
        t = np.linspace(0, dur, int(sample_rate * dur), False)
        freq = 320 - 180 * (t / dur)
        sine = np.sin(2 * np.pi * freq * t)
        noise = np.random.uniform(-0.35, 0.35, len(t))
        env = np.sin(np.pi * (t / dur)) * np.exp(-2.2 * t / dur)
        audio = (0.65 * sine + 0.35 * noise) * env * 0.7
        self.sounds["crowbar_swing"] = to_sound(audio)

        # -------------------------------------------------------------------
        # 15. Reload Start: Mechanical click/clink
        # -------------------------------------------------------------------
        dur = 0.25
        t = np.linspace(0, dur, int(sample_rate * dur), False)
        audio = np.zeros_like(t)
        # click 1
        t1 = t[t < 0.08]
        audio[t < 0.08] = np.random.uniform(-0.6, 0.6, len(t1)) * np.exp(-45 * t1)
        # click 2
        t2 = t[t >= 0.12]
        audio[t >= 0.12] = np.random.uniform(-0.8, 0.8, len(t2)) * np.exp(-45 * (t2 - 0.12))
        self.sounds["reload_start"] = to_sound(audio)

        # -------------------------------------------------------------------
        # 16. Reload Done: Mechanical slide-chamber chamber clack
        # -------------------------------------------------------------------
        dur = 0.22
        t = np.linspace(0, dur, int(sample_rate * dur), False)
        freq = 150 + 400 * np.exp(-20 * t)
        sine = np.sin(2 * np.pi * freq * t)
        noise = np.random.uniform(-0.5, 0.5, len(t))
        env = np.exp(-12 * t / dur)
        audio = (0.4 * sine + 0.6 * noise) * env * 0.7
        self.sounds["reload_done"] = to_sound(audio)

        # -------------------------------------------------------------------
        # 17. Wave Incoming: Pulse klaxon warning siren
        # -------------------------------------------------------------------
        dur = 1.2
        t = np.linspace(0, dur, int(sample_rate * dur), False)
        audio = np.zeros_like(t)
        for i in range(3):
            start = int(i * 0.4 * sample_rate)
            end = int((i + 1) * 0.4 * sample_rate)
            t_sub = t[start:end] - t[start]
            freq_val = 320 + 380 * (t_sub / 0.4)
            wave = np.sin(2 * np.pi * freq_val * t_sub)
            env_val = np.sin(np.pi * (t_sub / 0.4))
            audio[start:end] = wave * env_val * 0.25
        self.sounds["wave_incoming"] = to_sound(audio)

        # -------------------------------------------------------------------
        # 18. Background Music Loop: Space Pirate Sea Shanty Chiptune (22kHz)
        # -------------------------------------------------------------------
        music_rate = 22050
        music_dur = 12.0
        t_m = np.linspace(0, music_dur, int(music_rate * music_dur), False)
        music_audio = np.zeros_like(t_m)
        beat_len = int(music_rate * 0.5)

        bass_prog = [
            110.0, 110.0, 110.0, 110.0,
            130.8, 130.8, 130.8, 130.8,
            146.8, 146.8, 164.8, 164.8,
            110.0, 110.0, 110.0, 110.0,
            130.8, 130.8, 164.8, 164.8,
            110.0, 110.0, 110.0, 110.0
        ]

        melody_prog = [
            440, 440, 523, 523, 659, 659, 523, 440,
            523, 523, 587, 587, 659, 784, 659, 587,
            440, 440, 523, 523, 659, 659, 440, 440
        ]

        for step in range(24):
            start_idx = step * beat_len
            end_idx = min(start_idx + beat_len, len(t_m))
            if start_idx >= len(t_m):
                break
            t_step = t_m[start_idx:end_idx] - t_m[start_idx]

            # Bassline
            freq_b = bass_prog[step % len(bass_prog)]
            bass_wave = np.zeros_like(t_step)
            for harm in range(1, 4):
                bass_wave += (1.0 / harm) * np.sin(2 * np.pi * freq_b * harm * t_step)
            bass_env = np.exp(-4.5 * t_step)
            music_audio[start_idx:end_idx] += bass_wave * bass_env * 0.14

            # Melody
            freq_m = melody_prog[step % len(melody_prog)]
            mel_wave = np.sign(np.sin(2 * np.pi * freq_m * t_step))
            mel_env = np.sin(np.pi * (t_step / 0.5)) * np.exp(-3.5 * t_step)
            music_audio[start_idx:end_idx] += mel_wave * mel_env * 0.05

            # Kick & Snare Beat
            if step % 2 == 0:
                kick_env = np.exp(-22 * t_step)
                kick_wave = np.sin(2 * np.pi * (160 - 130 * (t_step / 0.5)) * t_step)
                music_audio[start_idx:end_idx] += kick_wave * kick_env * 0.16
            else:
                snare_env = np.exp(-15 * t_step)
                snare_noise = np.random.uniform(-0.5, 0.5, len(t_step))
                music_audio[start_idx:end_idx] += snare_noise * snare_env * 0.09

        def to_music_sound(mono_data: np.ndarray) -> pygame.mixer.Sound:
            clamped = np.clip(mono_data, -1.0, 1.0)
            int_data = (clamped * 32767).astype(np.int16)
            stereo = np.column_stack((int_data, int_data))
            return pygame.sndarray.make_sound(stereo)

        self.sounds["bg_music"] = to_music_sound(music_audio)

        # -------------------------------------------------------------------
        # 19. Enemy Laugh: Sinclair/lo-fi evil chuckle
        # -------------------------------------------------------------------
        dur = 0.55
        t = np.linspace(0, dur, int(sample_rate * dur), False)
        audio = np.zeros_like(t)
        for i in range(3):
            start = int(i * 0.18 * sample_rate)
            end = int((i + 1) * 0.18 * sample_rate)
            t_sub = t[start:end] - t[start]
            freq_val = (250 - i * 35) - 80 * (t_sub / 0.18)
            wave = np.sin(2 * np.pi * freq_val * t_sub)
            env_val = np.sin(np.pi * (t_sub / 0.18)) * np.exp(-4 * t_sub)
            audio[start:end] = wave * env_val * 0.85
        self.sounds["enemy_laugh"] = to_sound(audio)

        # -------------------------------------------------------------------
        # 20. Enemy Death: Somber pirate groan
        # -------------------------------------------------------------------
        dur = 0.65
        t = np.linspace(0, dur, int(sample_rate * dur), False)
        freq = 180 - 110 * (t / dur)
        sine = np.sin(2 * np.pi * freq * t)
        noise = np.random.uniform(-0.4, 0.4, len(t))
        env = np.sin(np.pi * (t / dur)) * np.exp(-2.5 * t / dur)
        audio = (0.6 * sine + 0.4 * noise) * env * 0.95
        self.sounds["enemy_death"] = to_sound(audio)
        # -------------------------------------------------------------------
        # 22. Enemy Hit: Thud impact
        # -------------------------------------------------------------------
        dur = 0.2
        t = np.linspace(0, dur, int(sample_rate * dur), False)
        freq = 120
        sine = np.sin(2 * np.pi * freq * t)
        env = np.exp(-8 * t / dur)
        audio = sine * env * 0.6
        self.sounds["enemy_hit"] = to_sound(audio)

        # -------------------------------------------------------------------
        # 21. Flintlock Fire: Crackling old black-powder explosion
        # -------------------------------------------------------------------
        dur = 0.65
        t = np.linspace(0, dur, int(sample_rate * dur), False)
        freq = 400 - 320 * (t / dur)
        sine = np.sin(2 * np.pi * freq * t)
        noise = np.random.uniform(-1.0, 1.0, len(t))
        env = np.exp(-5.5 * t / dur)
        audio = (0.2 * sine + 0.8 * noise) * env
        audio = np.tanh(audio * 1.8)
        self.sounds["flintlock_fire"] = to_sound(audio)

        # -------------------------------------------------------------------
        # 22. Revolver Fire: High-pressure metallic cowboy gunshot
        # -------------------------------------------------------------------
        dur = 0.35
        t = np.linspace(0, dur, int(sample_rate * dur), False)
        freq = 750 - 550 * (t / dur)
        sine = np.sin(2 * np.pi * freq * t)
        noise = np.random.uniform(-0.9, 0.9, len(t))
        env = np.exp(-9.5 * t / dur)
        audio = (0.35 * sine + 0.65 * noise) * env
        self.sounds["revolver_fire"] = to_sound(audio)

        # -------------------------------------------------------------------
        # 23. Cursed Cutlass Swing: Echoing ghostly sword swing
        # -------------------------------------------------------------------
        dur = 0.35
        t = np.linspace(0, dur, int(sample_rate * dur), False)
        freq = 550 + 200 * np.sin(2 * np.pi * 3.5 * t) - 200 * (t / dur)
        sine = np.sin(2 * np.pi * freq * t)
        env = np.sin(np.pi * (t / dur)) * np.exp(-1.5 * t / dur)
        audio = sine * env * 0.4
        self.sounds["cursed_cutlass_swing"] = to_sound(audio)

        # -------------------------------------------------------------------
        # 24. Cutlass Swing: Fast metallic blade swoosh
        # -------------------------------------------------------------------
        dur = 0.15
        t = np.linspace(0, dur, int(sample_rate * dur), False)
        freq = 750 - 450 * (t / dur)
        sine = np.sin(2 * np.pi * freq * t)
        noise = np.random.uniform(-0.1, 0.1, len(t))
        env = np.sin(np.pi * (t / dur))
        audio = (0.85 * sine + 0.15 * noise) * env * 0.4
        self.sounds["cutlass_swing"] = to_sound(audio)

