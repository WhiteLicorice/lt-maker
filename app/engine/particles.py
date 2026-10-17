import math, random

from enum import IntEnum

from app.constants import TILEX, WINWIDTH, WINHEIGHT, TILEWIDTH, TILEHEIGHT, FPS
from app.engine.sprites import SPRITES

from app.engine import engine, image_mods
from app.engine.game_state import game

class RateMethod(IntEnum):
    CONSTANT = 0
    RANDOM = 1

class ReusablePool:
    def __init__(self, particle_type, size):
        self.particle_type = particle_type
        self.size = size
        self._reusables = [particle_type() for _ in range(size)]

    def acquire(self):
        if not self._reusables:
            self.size = self.size + 100
            self._reusables.extend([self.particle_type() for _ in range(100)])
        return self._reusables.pop()

    def release(self, reusable):
        self._reusables.append(reusable)

class SimpleParticleSystem():
    def __init__(self, nid, particle, position, bounds, rate, rate_method=RateMethod.CONSTANT):
        self.nid = nid
        self.pos = tuple(position) if position else None
        self.particle = particle
        self.rate = rate / FPS  # Number to generate each frame
        self.current_created = 0

        self.particle_pool = ReusablePool(self.particle, 100)
        self.particles = []

        self.lx, self.ux, self.ly, self.uy = bounds
        self.rate_method = rate_method

        self.remove_me_flag = False

    def save(self):
        return self.nid, self.pos

    def generate_new_particle(self):
        xpos = random.randint(self.lx, self.ux)
        ypos = random.randint(self.ly, self.uy)
        new_particle = self.particle_pool.acquire()
        new_particle.reset((xpos, ypos))
        self.particles.append(new_particle)

    def update(self):
        for particle in self.particles:
            particle.update()

        # Remove particles that have left the map
        keep, remove = [], []
        for particle in self.particles:
            (keep, remove)[particle.remove_me_flag].append(particle)

        self.particles = keep
        for particle in remove:
            self.particle_pool.release(particle)

        if self.rate > 0:
            if self.rate_method == RateMethod.CONSTANT:
                self.current_created += self.rate
                if self.current_created >= 1:
                    self.generate_new_particle()
                    self.current_created -= 1
            elif self.rate_method == RateMethod.RANDOM:
                current_rate = self.rate
                while current_rate >= 1:
                    self.generate_new_particle()
                    current_rate -= 1
                if random.random() < current_rate:
                    self.generate_new_particle()

        if self.rate < 0:
            if self.rate_method == RateMethod.CONSTANT:
                self.current_created -= self.rate
                if self.current_created >= 1 and self.particles:
                    self.particles.pop(0)
                    self.current_created -= 1
            elif self.rate_method == RateMethod.RANDOM:
                current_rate = self.rate
                while current_rate <= 1 and self.particles:
                    self.particles.pop(0)
                    current_rate += 1
                if random.random() > current_rate and self.particles:
                    self.particles.pop(0)

        if self.rate <= 0 and not self.particles:
            self.remove_me_flag = True

    def prefill(self):
        for _ in range(300):
            self.update()

    def draw(self, surf, offset_x=0, offset_y=0):
        for particle in self.particles:
            particle.draw(surf, offset_x, offset_y)

class MapParticleSystem(SimpleParticleSystem):
    def __init__(self, nid, particle, abundance, bounds, size, blend=None, blend_type=engine.BLEND_RGB_ADD):
        width, height = size
        self.nid = nid
        self.pos = None
        self.particle = particle
        self.abundance = int(abundance * width * height)

        self.particle_pool = ReusablePool(self.particle, 100)
        self.particles = []

        self.lx, self.ux, self.ly, self.uy = bounds
        self.blend = blend
        self.blend_type = blend_type

        self.remove_me_flag = False

    def update(self):
        for particle in self.particles:
            particle.update()

        # Remove particles that have left the map
        keep, remove = [], []
        for particle in self.particles:
            (keep, remove)[particle.remove_me_flag].append(particle)

        self.particles = keep
        for particle in remove:
            self.particle_pool.release(particle)

        while len(self.particles) < self.abundance:
            self.generate_new_particle()    

        if self.abundance <= 0 and not self.particles:
            self.remove_me_flag = True

    def draw(self, surf, offset_x=0, offset_y=0):
        if self.blend:
            engine.blit(surf, self.blend, (0, 0), None, self.blend_type)
        for particle in self.particles:
            particle.draw(surf, offset_x, offset_y)

class Particle():
    sprite = None

    def reset(self, pos):
        self.x, self.y = pos
        self.remove_me_flag = False
        return self

    def update(self):
        raise NotImplementedError

    def draw(self, surf, offset_x=0, offset_y=0):
        pos = (self.x - offset_x, self.y - offset_y)
        surf.blit(self.sprite, pos)

class Raindrop(Particle):
    sprite = SPRITES.get('particle_raindrop')
    # As on the GBA (WfxRain_Init), each drop falls at one of 16 speeds in three bands, in
    # pixels a frame across and down: 6 slow ones, 7 middling and 3 fast
    speeds = ((2.0625, 6.0), (2.0625, 6.5), (2.0625, 7.0), (2.0625, 7.5), (2.0625, 8.0), (2.0625, 8.5),
              (2.8125, 10.0), (2.8125, 10.5), (2.8125, 11.0), (2.8125, 11.5), (2.8125, 12.0), (2.8125, 12.5), (2.8125, 13.0),
              (3.0, 16.0), (2.8125, 17.0), (2.625, 18.0))
    # There are as many of each on the GBA. A slower drop takes longer to cross the map, so
    # each speed is picked as often as it is fast, to keep as many of each falling at once
    weights = tuple(y for _, y in speeds)

    def reset(self, pos):
        super().reset(pos)
        self.x_speed, self.y_speed = random.choices(self.speeds, weights=self.weights)[0]
        return self

    def update(self):
        self.x += self.x_speed
        self.y += self.y_speed
        if game.tilemap and (self.x > game.tilemap.width * TILEWIDTH or self.y > game.tilemap.height * TILEHEIGHT):
            self.remove_me_flag = True

class Sand(Particle):
    sprite = SPRITES.get('particle_sand')

    def reset(self, pos):
        super().reset(pos)
        # As on the GBA (WfxSandStorm_Init), sand blows straight to the left, each cloud of
        # it at its own speed: 25 to 32 pixels every other frame
        self.speed = random.randint(25, 32) / 2
        return self

    def update(self):
        self.x -= self.speed
        if self.x < -32:
            self.remove_me_flag = True

class Smoke(Particle):
    sprite = SPRITES.get('particle_smoke')
    if sprite:
        bottom_sprite = engine.subsurface(sprite, (3, 0, 3, 4))
        top_sprite = engine.subsurface(sprite, (0, 0, 3, 4))
    else:
        bottom_sprite = top_sprite = None
    speed = 6

    def update(self):
        self.x += random.randint(self.speed//2, self.speed)
        self.y -= random.randint(self.speed//2, self.speed)
        if game.tilemap and (self.x > max(TILEX, game.tilemap.width) * TILEWIDTH or self.y < -32):
            self.remove_me_flag = True
        elif self.x > WINWIDTH:
            self.remove_me_flag = True
        elif self.y < -32:
            self.remove_me_flag = True

    def draw(self, surf, offset_x=0, offset_y=0):
        if self.y < WINHEIGHT//2:
            sprite = self.top_sprite
        else:
            sprite = self.bottom_sprite
        surf.blit(sprite, (self.x + offset_x, self.y + offset_y))

_fire_sprite = SPRITES.get('particle_fire')
class Fire(Particle):
    if _fire_sprite:
        sprites = [engine.subsurface(_fire_sprite, (0, i*2, 3, 2)) for i in range(6)]
    else:
        sprites = []

    def reset(self, pos):
        super().reset(pos)
        self.speed = random.randint(1, 4)
        self.sprite = self.sprites[-1]
        return self

    def update(self):
        self.x -= random.randint(0, self.speed)
        self.y -= random.randint(0, self.speed)
        if self.y > 112:
            self.sprite = self.sprites[-1]
        elif self.y > 104:
            self.sprite = self.sprites[-2]
        elif self.y > 88:
            self.sprite = self.sprites[-3]
        elif self.y > 80:
            self.sprite = self.sprites[-4]
        elif self.y > 72:
            self.sprite = self.sprites[-5]
        elif self.y > 64:
            self.sprite = self.sprites[-6]
        else:
            self.remove_me_flag = True

    def draw(self, surf, offset_x=0, offset_y=0):
        # Fire does obey camera offset
        surf.blit(self.sprite, (self.x, self.y))

class Snow(Particle):
    full_sprite = SPRITES.get('particle_snow')

    def reset(self, pos):
        super().reset(pos)
        self.sprite = engine.subsurface(self.full_sprite, (0, random.randint(0, 2) * 8, 8, 8))
        speeds = [1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5, 2.75, 3.0, 3.25, 3.5]
        self.y_speed = random.choice(speeds)
        x_speeds = speeds[:speeds.index(self.y_speed) + 1]
        self.x_speed = random.choice(x_speeds)
        return self

    def update(self):
        self.x += self.x_speed
        self.y += self.y_speed
        if game.tilemap and (self.x > game.tilemap.width * TILEWIDTH or self.y > game.tilemap.height * TILEHEIGHT):
            self.remove_me_flag = True

class WarpFlower(Particle):
    sprite = SPRITES.get('particle_warp_flower')
    speed = 0
    angle = 0

    def reset(self, pos, speed, angle):
        super().reset(pos)
        self.speed = speed
        self.angle = angle
        self.counter = 0
        return self

    def update(self):
        self.counter += 1
        self.angle -= math.pi / 64.
        self.x += self.speed * math.cos(self.angle)
        self.y += self.speed * math.sin(self.angle)
        if self.counter >= 40:
            self.remove_me_flag = True

class ReverseWarpFlower(WarpFlower):
    def reset(self, pos, speed, angle):
        super().reset(pos, speed, angle)
        self.init_x, self.init_y = pos
        for _ in range(40):
            self.pre_update()
        return self

    def pre_update(self):
        self.angle -= math.pi / 64.
        self.x += self.speed * math.cos(self.angle)
        self.y += self.speed * math.sin(self.angle)

    def update(self):
        self.counter += 1
        self.angle += math.pi / 64.
        self.x -= self.speed * math.cos(self.angle)
        self.y -= self.speed * math.sin(self.angle)
        if self.counter >= 40:
            self.remove_me_flag = True

class LightMote(Particle):
    sprite = SPRITES.get('particle_light_mote')
    speed = 0.16

    def reset(self, pos):
        super().reset(pos)
        self.transparency = .75
        self.change_over_time = random.choice([0.01, 0.02, 0.03])
        self.transition = True
        return self

    def update(self):
        self.x += self.speed
        self.y += self.speed

        if self.transition:
            self.transparency -= self.change_over_time
            if self.transparency < 0.05:
                self.transition = False
        else:
            self.transparency += self.change_over_time
            if self.transparency >= 0.75:
                self.remove_me_flag = True
                self.transparency = 1.

    def draw(self, surf, offset_x=0, offset_y=0):
        sprite = image_mods.make_translucent(self.sprite, self.transparency)
        surf.blit(sprite, (self.x - offset_x, self.y - offset_y))

class DarkMote(LightMote):
    sprite = SPRITES.get('particle_dark_mote')
    speed = -0.16

class Night(Particle):
    speed = 0

class Sunset(Particle):
    speed = 0

class SwitchTileParticle(Particle):
    sprite = SPRITES.get('particle_switch_tile')
    x_speed = 0
    y_speed = -0.5

    def reset(self, pos):
        super().reset(pos)
        self.orig_pos = pos
        self.transparency = 0.6
        self.height = 16
        self.change_over_time = 0.4 / self.height / 2
        return self

    def update(self):
        self.y += self.y_speed
        self.transparency += self.change_over_time
        if self.y < self.orig_pos[1] - self.height:
            self.remove_me_flag = True

    def draw(self, surf, offset_x=0, offset_y=0):
        sprite = image_mods.make_translucent(self.sprite, self.transparency)
        surf.blit(sprite, (self.x - offset_x, self.y - offset_y))

class PurpleMote(Particle):
    sprite = SPRITES.get('particle_purple_mote')

    def reset(self, pos):
        super().reset(pos)
        self.transparency = .95
        self.speed = 0.1 + random.random() * 0.15
        self.direction = random.random() * math.pi * 2
        self.change_over_time = random.choice([0.01, 0.015, 0.02])
        self.x_change = self.speed * math.cos(self.direction)
        self.y_change = self.speed * math.sin(self.direction)
        self.transition = True
        return self

    def update(self):
        self.x += self.x_change
        self.y += self.y_change

        if self.transition:
            self.transparency -= self.change_over_time
            if self.transparency < 0.05:
                self.transition = False
        else:
            self.transparency += self.change_over_time
            if self.transparency >= 0.95:
                self.remove_me_flag = True
                self.transparency = 1.

    def draw(self, surf, offset_x=0, offset_y=0):
        alpha = 255 * self.transparency
        sprite = image_mods.make_translucent_blend(self.sprite, alpha)
        engine.blit(surf, sprite, (self.x - offset_x, self.y - offset_y), None, engine.BLEND_RGB_ADD)

class EventTileParticle(Particle):
    sprite = SPRITES.get('particle_light_mote')
    x_speed = 0.16
    min_y_speed = 0.33
    y_speed = 1

    def reset(self, pos):
        super().reset(pos)
        self.orig_pos = pos
        self.my_x_speed = (random.random() * self.x_speed * 2) - self.x_speed
        self.my_y_speed = -(random.random() * (self.y_speed - self.min_y_speed)) - self.min_y_speed
        self.transparency = 0.6 * (random.random() * 0.3)
        self.transition = False
        self.change_over_time = 0.05
        return self

    def update(self):
        self.x += self.my_x_speed
        self.y += self.my_y_speed
        if self.y < self.orig_pos[1] - 20:
            self.transition = True

        if self.transition:
            self.transparency += self.change_over_time
        else:
            self.transparency += self.change_over_time / 5
        if self.transparency >= 1:
            self.remove_me_flag = True
            self.transparency = 1.

    def draw(self, surf, offset_x=0, offset_y=0):
        sprite = image_mods.make_translucent(self.sprite, self.transparency)
        surf.blit(sprite, (self.x - offset_x, self.y - offset_y))

class FirePillar(Particle):
    if _fire_sprite:
        sprites = [engine.subsurface(_fire_sprite, (0, i*2, 3, 2)) for i in range(6)]
    else:
        sprites = []

    def reset(self, pos):
        super().reset(pos)
        self.orig_pos = pos
        self.speed = random.randint(1, 4)
        self.sprite = self.sprites[-1]
        self.counter = 0
        return self

    def update(self):
        self.x += (random.random() * self.speed * 2) - self.speed
        self.y -= random.random() * self.speed
        self.counter += 1
        if self.counter < 4:
            self.sprite = self.sprites[-1]
        elif self.counter < 8:
            self.sprite = self.sprites[-2]
        elif self.counter < 12:
            self.sprite = self.sprites[-3]
        elif self.counter < 16:
            self.sprite = self.sprites[-4]
        elif self.counter < 20:
            self.sprite = self.sprites[-5]
        elif self.counter < 24:
            self.sprite = self.sprites[-6]
        else:
            self.remove_me_flag = True

    def draw(self, surf, offset_x=0, offset_y=0):
        surf.blit(self.sprite, (self.x - offset_x, self.y - offset_y))

# As on the GBA (WfxSnow_Init and the rest), there are 64 particles of rain, snow or sand to
# every 256 by 256 pixels, about 37 on the screen, and each is drawn every other frame: so
# about 19 on the screen at a time. Some of each kind are always off the map, coming in from
# its edges, so each kind needs its own abundance to put that many on the screen
RAIN_ABUNDANCE = 0.16
SNOW_ABUNDANCE = 0.19
SAND_ABUNDANCE = 0.16

def create_system(nid, width, height, position):
    twidth, theight = width * TILEWIDTH, height * TILEHEIGHT
    if nid == 'rain':
        # From far enough to the left that the slowest drops, which slant the most, still
        # cover the whole map
        creation_bounds = -theight * 3 // 8, twidth, -16, -8
        ps = MapParticleSystem(nid, Raindrop, RAIN_ABUNDANCE, creation_bounds, (width, height))
    elif nid == 'snow':
        creation_bounds = -theight, twidth, -16, -8
        ps = MapParticleSystem(nid, Snow, SNOW_ABUNDANCE, creation_bounds, (width, height))
    elif nid == 'sand':
        # Blown in from the right, from top to bottom
        creation_bounds = twidth, twidth + 32, -16, theight - 16
        ps = MapParticleSystem(nid, Sand, SAND_ABUNDANCE, creation_bounds, (width, height))
    elif nid == 'smoke':
        creation_bounds = -theight, twidth, theight, theight + 16
        ps = MapParticleSystem(nid, Smoke, .075, creation_bounds, (width, height))
    elif nid == 'light':
        creation_bounds = 0, twidth, 0, theight
        ps = MapParticleSystem(nid, LightMote, .02, creation_bounds, (width, height))
    elif nid == 'purple':
        creation_bounds = 0, twidth, 0, theight
        ps = MapParticleSystem(nid, PurpleMote, .06, creation_bounds, (width, height))
    elif nid == 'dark':
        creation_bounds = 0, twidth, 0, theight
        ps = MapParticleSystem(nid, DarkMote, .02, creation_bounds, (width, height))
    elif nid == 'fire':
        creation_bounds = 0, WINWIDTH + 64, WINHEIGHT, WINHEIGHT + 16
        blend = SPRITES.get('particle_bg_fire')
        ps = MapParticleSystem(nid, Fire, .06, creation_bounds, (width, height), blend=blend)
    elif nid == 'night':
        creation_bounds = 0, WINWIDTH + 64, WINHEIGHT, WINHEIGHT + 16
        blend = SPRITES.get('particle_bg_night')
        blend_type = engine.BLEND_RGB_MULT
        ps = MapParticleSystem(nid, Night, 0, creation_bounds, (width, height), blend=blend, blend_type=blend_type)
    elif nid == 'sunset':
        creation_bounds = 0, WINWIDTH + 64, WINHEIGHT, WINHEIGHT + 16
        blend = SPRITES.get('particle_bg_sunset')
        blend_type = engine.BLEND_RGB_MULT
        ps = MapParticleSystem(nid, Sunset, 0, creation_bounds, (width, height), blend=blend, blend_type=blend_type)
    elif nid == 'event_tile':
        ypos = (position[1] + 1) * TILEHEIGHT
        creation_bounds = position[0] * TILEWIDTH, (position[0] + 1) * TILEWIDTH, ypos - 5, ypos
        ps = SimpleParticleSystem(nid, EventTileParticle, position, creation_bounds, 6)
    elif nid == 'switch_tile':
        x = position[0] * TILEWIDTH
        y = position[1] * TILEWIDTH
        creation_bounds = x, x, y, y
        ps = SimpleParticleSystem(nid, SwitchTileParticle, position, creation_bounds, 5)
    elif nid == 'fire_pillar':
        ypos = (position[1] + 1) * TILEHEIGHT
        creation_bounds = position[0] * TILEWIDTH, (position[0] + 1) * TILEWIDTH, ypos - 5, ypos
        ps = SimpleParticleSystem(nid, FirePillar, position, creation_bounds, 12)

    if ps:
        ps.prefill()
    return ps
