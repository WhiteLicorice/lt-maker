from app.engine.sound import get_sound_thread

class UnitSound():
    # Which sound plays on which frame of the walk, and when it starts over, as on the
    # GBA (MuSoundScr_Foot and the rest). Each plays Map_Step_<name>
    sound_catalog = {
        'Flier': {0: 'Flier', 20: 'repeat'},
        'Mounted': {0: 'Mounted1', 3: 'Mounted2', 10: 'Mounted3', 21: 'repeat'},
        'Armor': {0: 'Armor1', 16: 'Armor2', 32: 'repeat'},
        'Infantry': {0: 'Infantry1', 8: 'Infantry2', 16: 'repeat'},
        'Mogall': {0: 'Mogall', 20: 'repeat'},
        'Zombie': {0: 'Zombie', 15: 'repeat'},
        'Skeleton': {0: 'Skeleton', 15: 'repeat'},
        'Spider': {0: 'Bael', 10: 'repeat'},
        # Map_Step_Tarvos is the GBA's Mauthe Doog walk (song 0x30A), whatever its name
        'Dog': {0: 'Tarvos', 3: 'Tarvos', 10: 'Tarvos', 21: 'repeat'},
        'Gorgon': {0: 'Gorgon', 15: 'repeat'},
        'Manakete': {0: 'Manakete', 16: 'repeat'},
        'Boat': {0: 'Boat', 12: 'Boat', 24: 'repeat'}}
    # Tags with sounds of their own, before the ones that most units have
    tagged_sounds = ('Mogall', 'Zombie', 'Skeleton', 'Spider', 'Dog', 'Gorgon', 'Manakete', 'Boat')

    def __init__(self, unit):
        self.unit = unit
        self.frame = 0
        self.current_sound = 0
        self.playing_sound = 0

    def play(self):
        tagged = [tag for tag in self.tagged_sounds if tag in self.unit.tags]
        if tagged:
            self.current_sound = tagged[0]
        elif 'Flying' in self.unit.tags:
            self.current_sound = 'Flier'
        elif 'Mounted' in self.unit.tags:
            self.current_sound = 'Mounted'
        elif 'Armor' in self.unit.tags:
            self.current_sound = 'Armor'
        else:
            self.current_sound = 'Infantry'

    def update(self, volume=1):
        if self.current_sound:
            catalog = self.sound_catalog[self.current_sound]
            if self.frame in catalog:
                sound = catalog[self.frame]
                if sound == 'repeat':
                    # The cycle starts over on this frame, so it is as long as the GBA's
                    self.frame = 0
                    sound = catalog[0]
                self.playing_sound = 'Map_Step_' + sound
                get_sound_thread().play_sfx(self.playing_sound, volume=volume)
            self.frame += 1

    def stop(self):
        get_sound_thread().stop_sfx(self.playing_sound)
        self.current_sound, self.playing_sound = None, None
        self.frame = 0
