"""
Cat's Undertale – Ultra‑robust version.
Loads OST from 'music' folder; falls back to procedural generation.
If procedural generation fails, sound is disabled silently.
"""

import pygame
import numpy as np
import sys
import math
import random
import os

# ==================== CONFIGURATION ====================
GBA_WIDTH, GBA_HEIGHT = 240, 160
SCALE = 3
SCREEN_SIZE = (GBA_WIDTH * SCALE, GBA_HEIGHT * SCALE)
TILE_SIZE = 16
FPS = 60

COLOR_BLACK = (0, 0, 0)
COLOR_WHITE = (255, 255, 255)
COLOR_RUINS = (100, 70, 120)
COLOR_SNOW = (200, 230, 255)
COLOR_WATER = (80, 160, 200)
COLOR_HOTLAND = (200, 100, 50)
COLOR_CORE = (150, 80, 80)
COLOR_CAT = (210, 180, 140)
COLOR_ENEMY = (255, 100, 100)
# FIX: Defined the missing COLOR_WALL variable
COLOR_WALL = (0, 0, 0) 

# ==================== EMBEDDED LEVEL DATA ====================
LEVELS = {
    "ruins": [
        "################",
        "#..............#",
        "#.....#........#",
        "#.....#...E....#",
        "#..............#",
        "#.....##.......#",
        "#..............#",
        "################"
    ],
    "snowdin": [
        "################",
        "#..............#",
        "#...E..........#",
        "#......##......#",
        "#..............#",
        "#..............#",
        "#..............#",
        "################"
    ],
    "waterfall": [
        "################",
        "#..............#",
        "#.....##.......#",
        "#.....##.......#",
        "#......E.......#",
        "#..............#",
        "#..............#",
        "################"
    ],
    "hotland": [
        "################",
        "#..............#",
        "#.....##.......#",
        "#.....##...E...#",
        "#..............#",
        "#..............#",
        "#..............#",
        "################"
    ],
    "core": [
        "################",
        "#..............#",
        "#......E.......#",
        "#....#####.....#",
        "#..............#",
        "#..............#",
        "#..............#",
        "################"
    ],
    "last": [
        "################",
        "#..............#",
        "#......E.......#",
        "#....#####.....#",
        "#..............#",
        "#..............#",
        "#..............#",
        "################"
    ]
}

# ==================== SOUND MANAGER ====================
class SoundManager:
    """Loads external music; falls back to procedural generation. Handles all errors."""
    def __init__(self):
        self.mixer_available = True
        self.music_channel = None
        self.proc_channels = []

        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
            # Allocate channels only if mixer init succeeded
            self.music_channel = pygame.mixer.Channel(0)
            self.proc_channels = [pygame.mixer.Channel(i) for i in range(1, 4)]
        except Exception as e:
            print(f"Warning: Could not initialize mixer ({e}). Sound disabled.")
            self.mixer_available = False

        self.procedural_enabled = False
        self.current_level = None
        self.route = "pacifist"
        self.target_volume = 0.5
        self.current_volume = 0.5
        self.speed = 0.0
        self.enemy_near = False

        # Procedural fallback storage
        self.proc_sounds = {}
        self.proc_target_volumes = [0.5, 0.5, 0.5]
        self.proc_current_volumes = [0.0, 0.0, 0.0]

    # ---------- External music ----------
    def load_music(self, level_name):
        """Load and play external music file."""
        if not self.mixer_available or self.music_channel is None:
            return False

        music_map = {
            "ruins": "ruins",
            "snowdin": "snowdin",
            "waterfall": "waterfall",
            "hotland": "hotland",
            "core": "core",
            "last": "asriel" if self.route == "pacifist" else "omega"
        }
        filename = music_map.get(level_name)
        if not filename:
            return False

        # Try .ogg then .mp3
        music_path = os.path.join("music", filename + ".ogg")
        if not os.path.exists(music_path):
            music_path = os.path.join("music", filename + ".mp3")
        if not os.path.exists(music_path):
            print(f"Music file not found: {filename}.ogg/.mp3")
            return False

        try:
            sound = pygame.mixer.Sound(music_path)
            self.music_channel.stop()
            self.music_channel.play(sound, loops=-1)
            self.music_channel.set_volume(self.current_volume)
            return True
        except Exception as e:
            print(f"Error loading music: {e}")
            return False

    # ---------- Procedural generation (with extreme caution) ----------
    def generate_tone(self, freq, duration, waveform='sine', volume=0.5):
        try:
            if not self.mixer_available:
                return None
            sample_rate = pygame.mixer.get_init()[0]
            samples = int(duration * sample_rate)
            if samples <= 0:
                return None
            t = np.linspace(0, duration, samples, endpoint=False)
            if waveform == 'sine':
                wave = np.sin(2 * np.pi * freq * t)
            elif waveform == 'square':
                wave = np.sign(np.sin(2 * np.pi * freq * t))
            elif waveform == 'sawtooth':
                wave = 2 * (t * freq - np.floor(t * freq + 0.5))
            else:
                wave = np.random.uniform(-1, 1, samples)

            envelope = np.ones(samples)
            fade = int(0.01 * sample_rate)
            if fade > 0:
                envelope[:fade] = np.linspace(0, 1, fade)
                envelope[-fade:] = np.linspace(1, 0, fade)
            wave *= envelope
            wave = (wave * volume * 32767).astype(np.int16)
            stereo = np.repeat(wave.reshape(-1, 1), 2, axis=1)
            return pygame.sndarray.make_sound(stereo)
        except Exception:
            return None

    def generate_drum(self, duration, type='kick', volume=0.5):
        try:
            if not self.mixer_available:
                return None
            sample_rate = pygame.mixer.get_init()[0]
            samples = int(duration * sample_rate)
            if samples <= 0:
                return None
            t = np.linspace(0, duration, samples, endpoint=False)
            if type == 'kick':
                freq = 100 * np.exp(-t * 10)
                wave = np.sin(2 * np.pi * freq * t) * np.exp(-t * 15)
            elif type == 'snare':
                noise = np.random.uniform(-1, 1, samples)
                tone = np.sin(2 * np.pi * 200 * t) * np.exp(-t * 20)
                wave = 0.5 * noise + 0.5 * tone
            elif type == 'hat':
                noise = np.random.uniform(-1, 1, samples)
                wave = noise * np.exp(-t * 30)
            else:
                wave = np.zeros(samples)
            wave *= volume
            wave = (wave * 32767).astype(np.int16)
            stereo = np.repeat(wave.reshape(-1, 1), 2, axis=1)
            return pygame.sndarray.make_sound(stereo)
        except Exception:
            return None

    def generate_proc_loop(self, level_name, duration=2.0):
        if not self.mixer_available:
            return None

        try:
            # Define musical parameters
            if level_name == "ruins":
                bass_freqs = [110, 110, 98, 98]
                melody_notes = [220, 262, 294, 330, 0, 330, 294, 262]
                tempo = 120
            elif level_name == "snowdin":
                bass_freqs = [98, 98, 110, 110]
                melody_notes = [330, 294, 262, 220, 0, 220, 262, 294]
                tempo = 140
            elif level_name == "waterfall":
                bass_freqs = [65, 65, 73, 73]
                melody_notes = [196, 220, 262, 294, 0, 262, 220, 196]
                tempo = 100
            elif level_name == "hotland":
                bass_freqs = [82, 82, 92, 92]
                melody_notes = [330, 311, 294, 262, 0, 294, 311, 330]
                tempo = 160
            elif level_name == "core":
                bass_freqs = [110, 98, 110, 98]
                melody_notes = [349, 330, 311, 294, 0, 294, 311, 330]
                tempo = 180
            else:  # last
                bass_freqs = [65, 73, 65, 73]
                melody_notes = [220, 262, 330, 392, 0, 392, 330, 262]
                tempo = 200

            beat_duration = 60.0 / tempo
            sample_rate = pygame.mixer.get_init()[0]
            samples_per_beat = int(beat_duration * sample_rate)
            if samples_per_beat <= 0:
                return None

            # Bass
            bass_pattern = []
            for freq in bass_freqs:
                if freq == 0:
                    bass_pattern.append(np.zeros(samples_per_beat))
                else:
                    tone = self.generate_tone(freq, beat_duration, waveform='sawtooth', volume=0.4)
                    if tone is None:
                        return None
                    arr = pygame.sndarray.array(tone)
                    if arr.size == 0:
                        return None
                    bass_pattern.append(arr[:, 0])  # mono
            bass_array = np.concatenate(bass_pattern)
            repeats = int(duration / (len(bass_freqs) * beat_duration))
            if repeats > 0:
                bass_array = np.tile(bass_array, repeats)

            # Melody
            melody_pattern = []
            for note in melody_notes:
                if note == 0:
                    melody_pattern.append(np.zeros(samples_per_beat))
                else:
                    tone = self.generate_tone(note, beat_duration, waveform='sine', volume=0.3)
                    if tone is None:
                        return None
                    arr = pygame.sndarray.array(tone)
                    if arr.size == 0:
                        return None
                    melody_pattern.append(arr[:, 0])
            melody_array = np.concatenate(melody_pattern)
            repeats = int(duration / (len(melody_notes) * beat_duration))
            if repeats > 0:
                melody_array = np.tile(melody_array, repeats)

            # Drums
            drums_pattern = []
            for i in range(16):
                if i % 4 == 0:
                    drum = self.generate_drum(beat_duration, 'kick', 0.5)
                elif i % 8 == 6:
                    drum = self.generate_drum(beat_duration, 'snare', 0.4)
                elif i % 2 == 1:
                    drum = self.generate_drum(beat_duration, 'hat', 0.2)
                else:
                    drums_pattern.append(np.zeros(samples_per_beat))
                    continue
                if drum is None:
                    return None
                arr = pygame.sndarray.array(drum)
                if arr.size == 0:
                    return None
                drums_pattern.append(arr[:, 0])
            drums_array = np.concatenate(drums_pattern)
            repeats = int(duration / (16 * beat_duration))
            if repeats > 0:
                drums_array = np.tile(drums_array, repeats)

            # Trim to exact duration
            target_samples = int(duration * sample_rate)
            if target_samples <= 0:
                return None
            bass_array = bass_array[:target_samples]
            melody_array = melody_array[:target_samples]
            drums_array = drums_array[:target_samples]

            # Convert to stereo
            def to_stereo(mono):
                try:
                    if mono.size == 0:
                        return None
                    stereo = np.repeat(mono.reshape(-1, 1), 2, axis=1)
                    return pygame.sndarray.make_sound(stereo.astype(np.int16))
                except Exception:
                    return None

            bass_snd = to_stereo(bass_array)
            melody_snd = to_stereo(melody_array)
            drums_snd = to_stereo(drums_array)

            if bass_snd is None or melody_snd is None or drums_snd is None:
                return None

            return (bass_snd, melody_snd, drums_snd)

        except Exception as e:
            print(f"Procedural generation failed: {e}")
            return None

    def load_procedural(self, level_name):
        """Fallback: generate and play procedural music."""
        if not self.mixer_available or not self.proc_channels:
            return

        # Stop any existing procedural music first
        for ch in self.proc_channels:
            try:
                ch.stop()
            except:
                pass

        if level_name in self.proc_sounds:
            loops = self.proc_sounds[level_name]
        else:
            loops = self.generate_proc_loop(level_name, duration=4.0)
            if loops is None:
                print("Procedural generation failed; disabling sound.")
                self.mixer_available = False
                return
            self.proc_sounds[level_name] = loops

        bass, melody, drums = loops
        try:
            self.proc_channels[0].play(bass, loops=-1)
            self.proc_channels[1].play(melody, loops=-1)
            self.proc_channels[2].play(drums, loops=-1)
        except Exception as e:
            print(f"Failed to play procedural music: {e}")
            self.mixer_available = False
            return

        self.proc_target_volumes = [0.5, 0.5, 0.5]
        self.proc_current_volumes = [0.0, 0.0, 0.0]

    def load_level(self, level_name):
        """Load music for a level – try external file, fallback to procedural."""
        if not self.mixer_available:
            return
        if level_name == self.current_level:
            return
        self.current_level = level_name

        # Stop all current sounds safely
        if self.music_channel:
            try:
                self.music_channel.stop()
            except:
                pass
        for ch in self.proc_channels:
            try:
                ch.stop()
            except:
                pass

        # Try external music
        success = self.load_music(level_name)
        if success:
            self.procedural_enabled = False
        else:
            self.procedural_enabled = True
            self.load_procedural(level_name)

    def set_route(self, route):
        if route != self.route:
            self.route = route
            if self.current_level == "last":
                self.load_level("last")

    def update(self, player_speed, enemy_near):
        if not self.mixer_available:
            return
        self.speed = player_speed
        self.enemy_near = enemy_near

        base_vol = 0.3 + 0.4 * min(1.0, self.speed / 5.0)
        if enemy_near:
            base_vol *= 0.5
        self.target_volume = base_vol

        diff = self.target_volume - self.current_volume
        self.current_volume += diff * 0.1

        if not self.procedural_enabled:
            if self.music_channel:
                try:
                    self.music_channel.set_volume(self.current_volume)
                except:
                    pass
        else:
            for i in range(3):
                diff = self.target_volume - self.proc_current_volumes[i]
                self.proc_current_volumes[i] += diff * 0.1
                if i < len(self.proc_channels):
                    try:
                        self.proc_channels[i].set_volume(self.proc_current_volumes[i])
                    except:
                        pass

# ==================== GAME OBJECTS ====================
class Cat(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((TILE_SIZE, TILE_SIZE))
        self.image.fill(COLOR_CAT)
        pygame.draw.circle(self.image, COLOR_BLACK, (4, 4), 2)
        pygame.draw.circle(self.image, COLOR_BLACK, (12, 4), 2)
        pygame.draw.polygon(self.image, COLOR_BLACK, [(2,2), (0,0), (4,0)])
        pygame.draw.polygon(self.image, COLOR_BLACK, [(14,2), (12,0), (16,0)])
        self.rect = self.image.get_rect(topleft=(x, y))
        self.vx = self.vy = 0
        self.speed = 3

    def update(self, walls):
        self.rect.x += self.vx
        self.collide(self.vx, 0, walls)
        self.rect.y += self.vy
        self.collide(0, self.vy, walls)

    def collide(self, dx, dy, walls):
        for wall in walls:
            if self.rect.colliderect(wall.rect):
                if dx > 0:
                    self.rect.right = wall.rect.left
                if dx < 0:
                    self.rect.left = wall.rect.right
                if dy > 0:
                    self.rect.bottom = wall.rect.top
                if dy < 0:
                    self.rect.top = wall.rect.bottom

class Wall(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((TILE_SIZE, TILE_SIZE))
        self.image.fill(COLOR_BLACK)
        self.rect = self.image.get_rect(topleft=(x, y))

class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y, level):
        super().__init__()
        self.image = pygame.Surface((TILE_SIZE, TILE_SIZE))
        self.image.fill(COLOR_ENEMY)
        self.rect = self.image.get_rect(topleft=(x, y))
        self.direction = 1
        self.speed = 1
        self.level = level

    def update(self, walls):
        self.rect.x += self.speed * self.direction
        if self.rect.left <= 0 or self.rect.right >= GBA_WIDTH:
            self.direction *= -1
        for wall in walls:
            if self.rect.colliderect(wall.rect):
                self.direction *= -1
                self.rect.x += self.speed * self.direction

# ==================== MAIN GAME ====================
class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode(SCREEN_SIZE)
        pygame.display.set_caption("Cat's Undertale (with OST)")
        self.clock = pygame.time.Clock()
        self.running = True

        self.level_names = ["ruins", "snowdin", "waterfall", "hotland", "core", "last"]
        self.current_level_idx = 0
        self.level = self.level_names[self.current_level_idx]

        self.player = None
        self.walls = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group()
        self.load_level(self.level)

        self.sound = SoundManager()
        self.sound.load_level(self.level)

    def load_level(self, level_name):
        self.walls.empty()
        self.enemies.empty()
        level_data = LEVELS[level_name]
        for row, line in enumerate(level_data):
            for col, char in enumerate(line):
                x = col * TILE_SIZE
                y = row * TILE_SIZE
                if char == '#':
                    self.walls.add(Wall(x, y))
                elif char == 'E':
                    self.enemies.add(Enemy(x, y, level_name))
        for row, line in enumerate(level_data):
            for col, char in enumerate(line):
                if char == '.':
                    self.player = Cat(col * TILE_SIZE, row * TILE_SIZE)
                    return

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            self.handle_events()
            self.update(dt)
            self.draw()
        pygame.quit()
        sys.exit()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    self.player.vx = -self.player.speed
                elif event.key == pygame.K_RIGHT:
                    self.player.vx = self.player.speed
                elif event.key == pygame.K_UP:
                    self.player.vy = -self.player.speed
                elif event.key == pygame.K_DOWN:
                    self.player.vy = self.player.speed
                elif event.key == pygame.K_n:
                    self.current_level_idx = (self.current_level_idx + 1) % len(self.level_names)
                    self.level = self.level_names[self.current_level_idx]
                    self.load_level(self.level)
                    self.sound.load_level(self.level)
                elif event.key == pygame.K_p:
                    self.sound.set_route("pacifist")
                elif event.key == pygame.K_g:
                    self.sound.set_route("genocide")
            elif event.type == pygame.KEYUP:
                if event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                    self.player.vx = 0
                if event.key in (pygame.K_UP, pygame.K_DOWN):
                    self.player.vy = 0

    def update(self, dt):
        self.player.update(self.walls)
        self.enemies.update(self.walls)

        enemy_near = any(abs(e.rect.centerx - self.player.rect.centerx) < 48 and
                         abs(e.rect.centery - self.player.rect.centery) < 48
                         for e in self.enemies)
        speed_mag = math.hypot(self.player.vx, self.player.vy)

        self.sound.update(speed_mag, enemy_near)

    def draw(self):
        if self.level == "ruins":
            bg_color = COLOR_RUINS
        elif self.level == "snowdin":
            bg_color = COLOR_SNOW
        elif self.level == "waterfall":
            bg_color = COLOR_WATER
        elif self.level == "hotland":
            bg_color = COLOR_HOTLAND
        elif self.level == "core":
            bg_color = COLOR_CORE
        else:
            bg_color = COLOR_CORE

        self.screen.fill(bg_color)

        scale = SCALE
        for sprite in self.walls:
            scaled_rect = pygame.Rect(sprite.rect.x * scale, sprite.rect.y * scale,
                                      TILE_SIZE * scale, TILE_SIZE * scale)
            pygame.draw.rect(self.screen, COLOR_WALL, scaled_rect)

        for sprite in self.enemies:
            scaled_rect = pygame.Rect(sprite.rect.x * scale, sprite.rect.y * scale,
                                      TILE_SIZE * scale, TILE_SIZE * scale)
            pygame.draw.rect(self.screen, COLOR_ENEMY, scaled_rect)

        player_scaled = pygame.transform.scale(self.player.image,
                                               (TILE_SIZE * scale, TILE_SIZE * scale))
        self.screen.blit(player_scaled, (self.player.rect.x * scale, self.player.rect.y * scale))

        pygame.display.flip()

# ==================== ENTRY POINT ====================
if __name__ == "__main__":
    game = Game()
    game.run()
