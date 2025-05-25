from __future__ import annotations

import json
import logging
import os
from pathlib import Path
import re
import shutil
from typing import Any, Dict, List

from app.data.category import Categories, CategorizedCatalog
from app.data.database import (ai, constants, difficulty_modes, equations,
                               factions, items, klass, levels, lore, mcost,
                               minimap, overworld, parties, credit,
                               raw_data, skills, stats, supports, tags, teams,
                               terrain, translations, units, varslot, weapons)
from app.data.serialization import disk_loader
from app.events import event_prefab
from app.utilities.data_order import parse_order_keys_file
from app.utilities.serialization import load_json, save_json
from app.utilities.typing import NID

CATEGORY_SUFFIX = '.category'

class Database(object):
    save_data_types = ("constants", "stats", "equations", "mcost", "terrain", "weapon_ranks",
                       "weapons", "teams", "factions", "items", "skills", "tags", "game_var_slots",
                       "classes", "support_constants", "support_ranks", "affinities", "units",
                       "support_pairs", "ai", "parties", "difficulty_modes", "credit",
                       "translations", "lore", "levels", "events", "overworlds", "raw_data")
    save_as_chunks = ("events", 'items', 'skills', 'units', 'classes', 'levels', "credit")

    def __init__(self):
        self.current_proj_dir = None

        self.constants = constants.constants
        self.teams = teams.TeamCatalog()
        self.stats = stats.StatCatalog()
        self.equations = equations.EquationCatalog()
        self.mcost = mcost.McostGrid()
        self.terrain = terrain.TerrainCatalog()
        self.minimap = minimap.MinimapCatalog()
        self.weapon_ranks = weapons.RankCatalog()
        self.weapons = weapons.WeaponCatalog()
        self.factions = factions.FactionCatalog()
        self.items = items.ItemCatalog()
        self.skills = skills.SkillCatalog()
        self.tags = tags.TagCatalog(['Lord', 'Boss', 'Armor', 'Horse', 'Mounted', 'Dragon', 'ZeroMove', 'AutoPromote', 'NoAutoPromote'])
        self.game_var_slots = varslot.VarSlotCatalog([])
        self.classes = klass.ClassCatalog()

        self.support_constants = supports.constants
        self.support_ranks = supports.SupportRankCatalog(['C', 'B', 'A'])
        self.affinities = supports.AffinityCatalog()

        self.units = units.UnitCatalog()

        self.support_pairs = supports.SupportPairCatalog()

        self.parties = parties.PartyCatalog()
        self.ai = ai.AICatalog()
        self.difficulty_modes = difficulty_modes.DifficultyModeCatalog()

        self.overworlds = overworld.OverworldCatalog()

        self.levels = levels.LevelCatalog()
        self.events = event_prefab.EventCatalog()

        self.translations = translations.TranslationCatalog()
        self.lore = lore.LoreCatalog()

        self.raw_data = raw_data.RawDataCatalog()

        self.credit = credit.CreditCatalog()

    @property
    def music_keys(self) -> List[str]:
        keys = []
        for team in self.teams:
            keys.append("%s_phase" % team.nid)
        for team in self.teams:
            keys.append("%s_battle" % team.nid)
        keys.append("boss_battle")
        return keys

    # === Saving and loading important data functions ===
    def restore(self, save_obj):
        for data_type in self.save_data_types:
            data = getattr(self, data_type)
            if save_obj[data_type] is None:
                logging.warning("Database: Skipping %s..." % (data_type))
            else:
                logging.info("Database: Restoring %s..." % (data_type))
                data.restore(save_obj[data_type])
            # Also restore the categories if it has any
            if isinstance(data, CategorizedCatalog):
                data.categories = Categories.load(save_obj.get(data_type + CATEGORY_SUFFIX, {}))

    def save(self):
        # import time
        to_save = {}
        for data_type in self.save_data_types:
            # logging.info("Saving %s..." % data_type)
            # time1 = time.time_ns()/1e6
            data = getattr(self, data_type)
            to_save[data_type] = data.save()
            # also save the categories if it has any
            if isinstance(data, CategorizedCatalog):
                to_save[data_type + CATEGORY_SUFFIX] = data.categories.save()
            # time2 = time.time_ns()/1e6 - time1
            # logging.info("Time taken: %s ms" % time2)
        return to_save

    def serialize(self, proj_dir) -> bool:
        # Returns whether we were successful
        from app.editor.settings import MainSettingsController
        main_settings = MainSettingsController()

        data_dir = os.path.join(proj_dir, 'game_data')
        if not os.path.exists(data_dir):
            os.mkdir(data_dir)
        logging.info("Serializing data in %s..." % data_dir)

        import time
        start = time.perf_counter() * 1000

        to_save = self.save()
        # This section is what takes so long!
        try:
            for key, value in to_save.items():
                # divide save data into chunks based on key value
                if key in self.save_as_chunks and main_settings.get_should_save_as_chunks():
                    save_dir = os.path.join(data_dir, key)
                    if os.path.exists(save_dir):
                        shutil.rmtree(save_dir)
                    os.mkdir(save_dir)
                    orderkeys: List[str] = []
                    for idx, subvalue in enumerate(value):
                        # ordering
                        name = subvalue['nid']
                        name = re.sub(r'[\\/*?:"<>|]', "", name)
                        name = name.replace(' ', '_')
                        orderkeys.append(name)
                        save_loc = Path(save_dir, name + '.json')
                        # logging.info("Serializing %s to %s" % ('%s/%s.json' % (key, name), save_loc))
                        save_json(save_loc, [subvalue])
                    save_json(Path(save_dir, '.orderkeys'), orderkeys)
                else:  # Save as a single file
                    # Which means deleting the old directory
                    save_dir = Path(data_dir, key)
                    if os.path.exists(save_dir):
                        shutil.rmtree(save_dir)
                    save_loc = Path(data_dir, key + '.json')
                    # logging.info("Serializing %s to %s" % (key, save_loc))
                    save_json(save_loc, value)

        except OSError as e:  # In case we ran out of memory
            logging.error("Editor was unable to save your project. Free up memory in your hard drive or try saving somewhere else, otherwise progress will be lost when the editor is closed.")
            logging.exception(e)
            return False

        end = time.perf_counter() * 1000
        logging.info("Total Time Taken for Database: %s ms" % (end - start))
        logging.info("Done serializing!")
        return True

    def load(self, proj_dir: Path | str, version: int):
        proj_dir = Path(proj_dir)
        self.current_proj_dir = proj_dir
        data_dir = proj_dir / 'game_data'
        logging.info("Deserializing data from %s..." % data_dir)

        import time
        start = time.perf_counter() * 1000

        save_obj = disk_loader.load_database(data_dir, version)
        self.restore(save_obj)

        # TODO -- This is a shitty fix that should be superseded
        from app.engine import equations
        equations.clear()
        from app.engine import achievements, persistent_records
        achievements.reset()
        persistent_records.reset()
        # -- End shitty fix

        end = time.perf_counter() * 1000

        logging.info("Total Time Taken for Database: %s ms" % (end - start))
        logging.info("Done deserializing!")

DB = Database()

# Testing
# Run "python -m app.data.database.database" from main directory
