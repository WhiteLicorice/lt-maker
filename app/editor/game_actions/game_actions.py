import glob
import logging
import traceback

from app.editor.data_editor import DB
from app.editor.settings import MainSettingsController
from app.editor.settings.preference_definitions import Preference
from app.engine import driver, engine, game_state
from app.engine.utils import garbage
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtGui import QFont

from app.events.python_eventing.errors import EventError

def handle_exception(e: Exception):
    logging.error("Engine crashed with a fatal error!")
    logging.exception(e)
    if isinstance(e, EventError):
        # error in python eventing
        msg = "Engine crashed. \nException occurred during event execution:\n" + str(e)
    else:
        msg = "Engine crashed. \nFor more detailed logs, please click View Logs in the Extra menu.\n" + traceback.format_exc()
    settings = MainSettingsController()
    if settings.get_preference(Preference.CRASH_LOGS):
        error_msg = QMessageBox()
        error_msg.setFont(QFont("consolas"))
        error_msg.setFixedWidth(1200)
        error_msg.setIcon(QMessageBox.Critical)
        error_msg.setText(msg)
        error_msg.setWindowTitle("Engine Fatal Error")
        error_msg.exec_()
    # Required to close window (reason: Unknown)
    engine.terminate(True)

def test_play():
    title = DB.constants.value('title')
    try:
        driver.start(title, from_editor=True)
        game = game_state.start_game()
        driver.run(game)
    except Exception as e:
        handle_exception(e)
    finally:
        garbage.release()

def test_play_current(level_nid):
    title = DB.constants.value('title')
    try:
        driver.start(title, from_editor=True)
        game = game_state.start_level(level_nid)
        game.game_vars['_chapter_test'] = True
        from app.events import triggers
        game.events.trigger(triggers.OnStartup())
        driver.run(game)
    except Exception as e:
        handle_exception(e)
    finally:
        garbage.release()

def get_preloaded_games():
    GAME_NID = str(DB.constants.value('game_nid'))
    return glob.glob('saves/' + GAME_NID + '-preload-*-*.p')

def test_play_load(level_nid, save_loc=None):
    title = DB.constants.value('title')
    try:
        driver.start(title, from_editor=True)
        if save_loc:
            game = game_state.load_level(level_nid, save_loc)
        else:
            game = game_state.start_level(level_nid)
        from app.events import triggers
        game.events.trigger(triggers.OnStartup())
        driver.run(game)
    except Exception as e:
        handle_exception(e)
    finally:
        garbage.release()

def test_combat(left_combat_anim, left_weapon_anim, left_palette_name, left_palette, left_item_nid: str,
                right_combat_anim, right_weapon_anim, right_palette_name, right_palette, right_item_nid: str,
                pose_nid: str):
    try:
        driver.start("Combat Test", from_editor=True)
        from app.engine import battle_animation
        from app.engine.combat.mock_combat import MockCombat
        right = battle_animation.BattleAnimation.get_anim(right_combat_anim, right_weapon_anim, right_palette_name, right_palette, None, right_item_nid)
        left = battle_animation.BattleAnimation.get_anim(right_weapon_anim, left_weapon_anim, left_palette_name, left_palette, None, left_item_nid)
        at_range = 1 if 'Ranged' in right_weapon_anim.nid else 0
        mock_combat = MockCombat(left, right, at_range, pose_nid)
        left.pair(mock_combat, right, False, at_range)
        right.pair(mock_combat, left, True, at_range)
        driver.run_combat(mock_combat)
    except Exception as e:
        handle_exception(e)
    finally:
        garbage.release()

def test_event(event_prefab, starting_command_idx=0, strategy=None):
    try:
        driver.start("Event Test", from_editor=True)
        # The event evaluates against the global game, which outlives each launch
        # from the editor, so give it a fresh new game instead of the last playthrough
        game = game_state.game
        game.clear()
        game.build_new()
        from app.events.mock_event import MockEvent
        mock_event = MockEvent('Test Event', event_prefab, starting_command_idx, strategy)
        driver.run_event(mock_event)
    except Exception as e:
        handle_exception(e)
    finally:
        garbage.release()
