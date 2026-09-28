import os
import logging
from collections import OrderedDict
from pathlib import Path

from app.utilities import str_utils


def base_config() -> OrderedDict:
    return OrderedDict([('debug', 1),
                        ('all_saves', 0),
                        ('random_seed', -1),
                        ('screen_size', 2),
                        ('fullscreen', 0),
                        ('sound_buffer_size', 2),
                        ('animation', 'Always'),
                        ('display_fps', 0),
                        ('battle_bg', 0),
                        ('unit_speed', 120),
                        ('text_speed', 32),
                        ('cursor_speed', 66),
                        ('mouse', 1),
                        ('show_terrain', 1),
                        ('forecast', 'Strategic'),
                        ('show_objective', 1),
                        ('autocursor', 1),
                        ('music_volume', 0.3),
                        ('sound_volume', 0.3),
                        ('talk_boop', 1),
                        ('show_bounds', 0),
                        ('grid_opacity', 0),
                        ('autoend_turn', 1),
                        ('confirm_end', 1),
                        ('hp_map_team', 'All'),
                        ('hp_map_cull', 'All'),
                        ('display_hints', 0),
                        ('key_SELECT', 'K_x'),
                        ('key_BACK', 'K_z'),
                        ('key_INFO', 'K_c'),
                        ('key_AUX', 'K_a'),
                        ('key_START', 'K_s'),
                        ('key_LEFT', 'K_LEFT'),
                        ('key_RIGHT', 'K_RIGHT'),
                        ('key_UP', 'K_UP'),
                        ('key_DOWN', 'K_DOWN'),
                        ('joy_SELECT', 'button:a'),
                        ('joy_BACK', 'button:b'),
                        ('joy_INFO', 'button:x,button:rightshoulder,axis:triggerright+'),
                        ('joy_AUX', 'button:leftshoulder,axis:triggerleft+'),
                        ('joy_START', 'button:start,button:y,button:back')])

float_vals = ('music_volume', 'sound_volume')
string_vals = ('animation', 'hp_map_team', 'hp_map_cull', 'forecast')
key_vals = ('key_SELECT', 'key_BACK', 'key_INFO', 'key_AUX',
            'key_START', 'key_LEFT', 'key_RIGHT', 'key_UP', 'key_DOWN')
joy_vals = ('joy_SELECT', 'joy_BACK', 'joy_INFO', 'joy_AUX', 'joy_START')

def convert_setting(k, v):
    if k in float_vals:
        return float(v)
    elif k in string_vals:
        return v
    elif k in key_vals:
        if str_utils.is_int(v):
            return int(v)
        elif v.startswith('K_'):  # pygame key constant
            import pygame
            return getattr(pygame, v)
        raise ValueError("Unknown key constant: %s" % v)
    elif k in joy_vals:
        from app.engine import joy_bindings
        joy_bindings.parse_bindings(v)  # Raises ValueError if malformed
        return v
    else:
        return int(v)

def read_config_file():
    config = base_config()
    
    def parse_ini(fn):
        with open(fn) as fp:
            for line in fp:
                split_line = line.strip().split('=')
                if len(split_line) < 2:
                    continue
                config[split_line[0]] = split_line[1]

    try:
        parse_ini('saves/config.ini')
    except OSError:
        if os.path.exists('data/config.ini'):
            parse_ini('data/config.ini')

    defaults = base_config()
    for k, v in list(config.items()):
        if k not in defaults:
            # Written by a different engine version; type unknown, so drop it
            logging.warning("Ignoring unknown config key: %s", k)
            del config[k]
            continue
        try:
            config[k] = convert_setting(k, v)
        except (ValueError, AttributeError):
            logging.warning("Bad config value %s=%s; using default %s", k, v, defaults[k])
            config[k] = convert_setting(k, defaults[k])

    return config

def reset_settings(keys):
    defaults = base_config()
    for k in keys:
        SETTINGS[k] = convert_setting(k, defaults[k])

def save_config(cfg: OrderedDict, path: Path):
    with open(path, 'w') as fp:
        for k, v in cfg.items():
            fp.write('%s=%s\n' % (k, v))

def save_settings():
    save_config(SETTINGS, 'saves/config.ini')

def save_debug_commands(commands):
    try:
        with open('saves/debug_commands.txt', 'w') as fp:
            write_out = '\n'.join(commands)
            fp.write(write_out)
    except OSError as e:
        logging.exception(e)

def get_debug_commands() -> list:
    commands = []
    if os.path.exists('saves/debug_commands.txt'):
        with open('saves/debug_commands.txt', 'r') as fp:
            for line in fp.readlines():
                commands.append(line.strip())
    return commands

text_speed_options = list(reversed([0, 3, 8, 15, 32, 50, 64, 80, 112, 150]))
SETTINGS = read_config_file()
print("debug: %s" % SETTINGS['debug'])
