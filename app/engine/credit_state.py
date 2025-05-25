from app.constants import WINHEIGHT, WINWIDTH, COLORKEY

from app.data.database.database import DB
from app.data.database.credit import CreditEntry, CreditCatalog
from app.data.resources.resources import RESOURCES
from app.data.resources.resource_types import ResourceType

from app.engine import base_surf
from app.engine import dialog, engine, gui, image_mods, text_funcs
from app.engine.background import PanoramaBackground, ScrollingBackground
from app.engine.fluid_scroll import FluidScroll
from app.engine.fonts import FONT

from app.engine.state import MapState
from app.engine.game_state import game

from app.engine.game_menus.menu_options import BasicOption, EmptyOption
from app.engine.graphics.text.text_renderer import render_text, text_width
from app.engine.info_menu.info_menu_portrait import InfoMenuPortrait

from app.engine.menus import Choice
from app.engine.sound import get_sound_thread
from app.engine.sprites import SPRITES
from app.engine.state import State
from app.engine.unit_sprite import MapSprite

from app.utilities import utils
from app.utilities.enums import HAlignment

from typing import Tuple, List

def populate_options(credit_catalog: CreditCatalog) -> Tuple[List[str], List[str], List[List[CreditEntry]]]:
    """
    return (options, ignore, ordered_credits), which should all be the same size
    """
    credits = sorted(credit_catalog, key=lambda x: (x.category, x.header()))
    categories = []
    options = []
    ignore = []

    ordered_credits = []
    temp_list = None
    for credit in credits:
        curr_option = credit.header()

        if credit.category not in categories:
            categories.append(credit.category)
            if temp_list:
                ordered_credits.append(temp_list)
            options.append(credit.category)
            ignore.append(True)

            ordered_credits.append([])
            options.append(curr_option)
            ignore.append(False)

            prev_option = curr_option
            temp_list = [credit]
            continue

        if prev_option == curr_option:
            temp_list.append(credit)
            continue

        ordered_credits.append(temp_list)
        options.append(curr_option)
        ignore.append(False)
        prev_option = curr_option
        temp_list = [credit]
    ordered_credits.append(temp_list)

    return options, ignore, ordered_credits

class CreditState(State):
    name = 'credit'

    def __init__(self, name=None):
        super().__init__(name)
        self.fluid = FluidScroll()

    def start(self):
        if game.memory.get('credit_bg'):
            self.bg = game.memory.get('credit_bg')
        else:
            self.bg = game.memory.get('title_bg')
            
        if not self.bg:
            panorama = RESOURCES.panoramas.get('default_background')
            self.bg = ScrollingBackground(panorama)
            self.bg.scroll_speed = 50

        options, ignore, ordered_credits = populate_options(DB.credit)

        self.menu = CreditMenu(options, ignore)
        self.display = CreditDisplay(ordered_credits)
        self.display.update_entry(self.menu.get_current_index())

        game.state.change('transition_in')
        return 'repeat'

    def begin(self):
        self.fluid.reset_on_change_state()

    def take_input(self, event):
        first_push = self.fluid.update()
        directions = self.fluid.get_directions()

        self.menu.handle_mouse()
        if not self.display.current or self.display.current != self.menu.get_current_index():
            self.display.update_entry(self.menu.get_current_index())

        if 'DOWN' in directions:
            if self.menu.move_down(first_push):
                get_sound_thread().play_sfx('Select 6')
            self.display.update_entry(self.menu.get_current_index())

        elif 'UP' in directions:
            if self.menu.move_up(first_push):
                get_sound_thread().play_sfx('Select 6')
            self.display.update_entry(self.menu.get_current_index())

        elif 'RIGHT' in directions:
            if self.display.page_right():
                get_sound_thread().play_sfx('Status_Page_Change')

        elif 'LEFT' in directions:
            if self.display.page_left():
                get_sound_thread().play_sfx('Status_Page_Change')

        if event == 'BACK':
            get_sound_thread().play_sfx('Select 4')
            game.state.change('transition_pop')

        elif event == 'SELECT':
            if self.display.page_right(True):
                get_sound_thread().play_sfx('Status_Page_Change')

    def update(self):
        if self.menu:
            self.menu.update()

    def draw(self, surf):
        if game.game_vars.get('_base_transparent'):
            surf = MapState.draw(self, surf)
        elif self.bg:
            self.bg.draw(surf)
        if self.display:
            self.display.draw(surf)
        if self.menu:
            self.menu.draw(surf)
        return surf

class CreditDisplay():
    icon_size_dict = {ResourceType.ICONS16: 16, 
                      ResourceType.ICONS32: 32,
                      ResourceType.MAP_ICONS: 32,
                      ResourceType.MAP_SPRITES: 16}

    def __init__(self, credits):
        self.contents = []
        self.credits = credits
        self.current = None
        self.pages = []
        self.font = 'text'

        self.topleft = (84, 4)
        self.width = WINWIDTH - 84
        self.height = WINHEIGHT - 8

        self.bg_surf = base_surf.create_base_surf(self.width, self.height, 'menu_bg_brown')
        shimmer = SPRITES.get('menu_shimmer3')
        self.bg_surf.blit(shimmer, (
            self.bg_surf.get_width() - shimmer.get_width() - 1, self.bg_surf.get_height() - shimmer.get_height() - 5))
        self.bg_surf = image_mods.make_translucent(self.bg_surf, .1)

        self.left_arrow = gui.ScrollArrow('left', (self.topleft[0] + 4, 8))
        self.right_arrow = gui.ScrollArrow('right', (self.topleft[0] + self.width - 17, 8), 0.5)

        self.clear_display()

    def clear_display(self):       
        self.bg = None
        self.dlg = None
        self.portrait = None
        self.static_surf = None

    def update_entry(self, idx):
        if self.current == idx:
            return  # No need to update

        self.current = idx
        self.page_num = 0
        self.pages = []

        self.contents = []

        lst = self.credits[idx]
        if lst:
            if lst[0].credit_type in (ResourceType.ICONS16, ResourceType.ICONS32, 
                                      ResourceType.MAP_ICONS, ResourceType.MAP_SPRITES):
                limit = self.height - 24
                icon_size = self.icon_size_dict.get(lst[0].credit_type) + 4
                font_height = FONT[self.font].height
                page_height = 0
                page = []

                for credit in lst:
                    line = 0
                    if credit.contrib and credit.contrib[0]:
                        line = len(text_funcs.line_wrap(self.font, 
                                                        "by %s" % credit.contrib[0][0], 
                                                        self.width - 16 - icon_size))
                    credit_height = max(line * font_height, icon_size)
                    if page_height + credit_height <= limit:
                        page_height += credit_height
                        page.append(credit)
                        continue
                    self.pages.append(page)
                    page_height = credit_height
                    page = [credit]
                self.pages.append(page)

            elif not isinstance(lst[0].credit_type, ResourceType):
                for credit in lst:
                    if not (credit.contrib and credit.contrib[0]):
                        self.contents.append(None)
                        self.pages.append([credit])
                        continue

                    if credit.credit_type == 'Text':
                        text = text_funcs.translate_and_text_evaluate(credit.contrib[0][1]).split('\n')
                        for line in text:
                            dlg = dialog.Dialog(line, font_type=self.font, font_color="white", num_lines=8, draw_cursor=False)
                            dlg.position = self.topleft[0], self.topleft[1] + 12
                            dlg.text_width = WINWIDTH - 100
                            dlg.reformat()
                            self.contents.append(dlg)
                            self.pages.append([credit])

                    elif credit.credit_type == 'List':
                        limit = self.height - 24
                        font_height = FONT[self.font].height
                        page_height = 0
                        page = []

                        for c in credit.contrib:
                            line = len(text_funcs.line_wrap(self.font, "%s by %s" % (c[1], c[0]), self.width - 16))
                            if page_height + line * font_height <= limit:
                                page_height += line * font_height
                                page.append(c)
                                continue
                            self.contents.append(page)
                            self.pages.append([credit])
                            page_height = line * font_height
                            page = [c]
                        self.contents.append(page)
                        self.pages.append([credit])

            else:
                self.pages = [[credit] for credit in lst]
            self.num_pages = len(self.pages)

        self.clear_display()

    def page_right(self, first_push=False) -> bool:
        if self.page_num < self.num_pages - 1:
            self.page_num += 1
            self.right_arrow.pulse()
            self.clear_display()
            return True
        elif first_push:
            self.page_num = (self.page_num + 1) % self.num_pages
            self.right_arrow.pulse()
            self.clear_display()
            return True
        return False

    def page_left(self, first_push=False) -> bool:
        if self.page_num > 0:
            self.page_num -= 1
            self.left_arrow.pulse()
            self.clear_display()
            return True
        elif first_push:
            self.page_num = (self.page_num - 1) % self.num_pages
            self.left_arrow.pulse()
            self.clear_display()
            return True
        return False

    def draw(self, surf):
        if not self.pages:
            return surf

        lst = self.pages[self.page_num]
        credit = lst[0]

        if credit.credit_type == ResourceType.PANORAMAS and not self.bg:
            imgs = RESOURCES.panoramas.get(credit.sub_nid)
            self.bg = PanoramaBackground(imgs) if imgs else None

        if self.bg:
            self.bg.draw(surf)
            lines = 0
            if credit.contrib and credit.contrib[0]:
                c = credit.contrib[0]
                lines = text_funcs.line_wrap(self.font, "%s by %s" % (c[1], c[0]), self.width - 16)
            temp_menu = base_surf.create_base_surf(self.width, 28 + len(lines) * FONT[self.font].height, 'menu_bg_clear')
            surf.blit(temp_menu, self.topleft)
        else:
            surf.blit(self.bg_surf, self.topleft)

        if credit.credit_type == ResourceType.PORTRAITS and not self.portrait:
            portrait = RESOURCES.portraits.get(credit.sub_nid)
            self.portrait = InfoMenuPortrait(portrait, DB.constants.value('info_menu_blink')) if portrait else None

        if self.portrait:
            self.portrait.update()
            im = self.portrait.create_image()
            surf.blit(im, utils.tuple_add((self.width - 8 - 96, WINHEIGHT - 12 - 80), self.topleft))

        elif credit.credit_type == ResourceType.MAP_SPRITES:
            y_pos = 20
            icon_size = self.icon_size_dict.get(credit.credit_type) + 4
            for c in lst:
                res = RESOURCES.map_sprites.get(c.sub_nid)
                if not res:
                    continue
                map_sprite = game.map_sprite_registry.get("%s_player" % res.nid)
                if not map_sprite:
                    map_sprite = MapSprite(res, "player")
                    game.map_sprite_registry["%s_player" % map_sprite.nid] = map_sprite
                im = map_sprite.create_image('passive')
                surf.blit(im, utils.tuple_add((8 - 24, y_pos - 24), self.topleft))

                lines = []
                if c.contrib and c.contrib[0]:
                    lines = text_funcs.line_wrap(self.font, "by %s" % c.contrib[0][0], self.width - 16 - icon_size)
                    for idx, line in enumerate(lines):
                        render_text(surf, [self.font], [line], [], 
                                    utils.tuple_add((8 + icon_size, y_pos + idx * FONT[self.font].height), self.topleft))
                y_pos += max(len(lines) * FONT[self.font].height, icon_size)

        elif credit.credit_type == 'Text':
            if not self.dlg:
                self.dlg = self.contents[self.page_num]
            if self.dlg:
                self.dlg.update()
                self.dlg.draw(surf)

        if not self.static_surf:
            self.static_surf = self.create_static_surf(lst)
        surf.blit(self.static_surf, (0, 0))

        if self.num_pages > 1:
            self.left_arrow.draw(surf)
            self.right_arrow.draw(surf)

        return surf

    def create_static_surf(self, lst):
        credit = lst[0]
        surf = engine.create_surface((WINWIDTH, WINHEIGHT), transparent=True)

        header = credit.header()
        render_text(surf, ['text'], [header], ['blue'], utils.tuple_add((self.width // 2, 4), self.topleft), HAlignment.CENTER)

        if credit.credit_type == ResourceType.ICONS80:
            im = self.get_icon_by_credit(credit)
            if im:
                surf.blit(im, utils.tuple_add((self.width - 8 - 80, WINHEIGHT - 12 - 72), self.topleft))

        lines = []
        if credit.credit_type in (ResourceType.ICONS16, ResourceType.ICONS32, ResourceType.MAP_ICONS):
            y_pos = 20
            icon_size = self.icon_size_dict.get(credit.credit_type) + 4
            for c in lst:
                im = self.get_icon_by_credit(c)
                if not im:
                    continue

                surf.blit(im, utils.tuple_add((8, y_pos), self.topleft))
                lines = []
                if c.contrib and c.contrib[0]:
                    lines = text_funcs.line_wrap(self.font, "by %s" % c.contrib[0][0], self.width - 16 - icon_size)
                    for idx, line in enumerate(lines):
                        render_text(surf, [self.font], [line], [], 
                                    utils.tuple_add((8 + icon_size, y_pos + idx * FONT[self.font].height), self.topleft))
                y_pos += max(len(lines) * FONT[self.font].height, icon_size)

        elif credit.credit_type in (ResourceType.ICONS80, ResourceType.PORTRAITS, ResourceType.PANORAMAS) and \
                credit.contrib and credit.contrib[0]:
            c = credit.contrib[0]
            lines = text_funcs.line_wrap(self.font, c[1], self.width - 16)
            st = lines.pop()
            highlight_lines = range(len(lines))

            lines += text_funcs.line_wrap(self.font, "<orange>%s</> by %s" % (st, c[0]), self.width - 16)
            for idx, line in enumerate(lines):
                render_text(surf, [self.font], [line], ['orange' if idx in highlight_lines else None], 
                            utils.tuple_add((8, 20 + idx * FONT[self.font].height), self.topleft))

        elif credit.credit_type == 'List' and credit.contrib and credit.contrib[0]:
            highlight_lines = []
            for c in self.contents[self.page_num]:
                start = len(lines)
                lines += text_funcs.line_wrap(self.font, c[1], self.width - 16)
                st = lines.pop()
                end = len(lines)
                highlight_lines += range(start, end)
                lines += text_funcs.line_wrap(self.font, "<orange>%s</> by %s" % (st, c[0]), self.width - 16)

            for idx, line in enumerate(lines):
                render_text(surf, [self.font], [line], ['orange' if idx in highlight_lines else None], 
                            utils.tuple_add((8, 20 + idx * FONT[self.font].height), self.topleft))

        if self.num_pages > 1:
            text = '%d / %d' % (self.page_num + 1, self.num_pages)
            render_text(surf, ['text'], [text], ['yellow'], utils.tuple_add((self.width - 8, WINHEIGHT - 12 - 16), self.topleft), HAlignment.RIGHT)

        return surf

    def get_icon_by_credit(self, credit):
        if credit.credit_type == ResourceType.ICONS16:
            database = RESOURCES.icons16
            width, height = 16, 16
        elif credit.credit_type == ResourceType.ICONS32:
            database = RESOURCES.icons32
            width, height = 32, 32
        elif credit.credit_type == ResourceType.ICONS80:
            database = RESOURCES.icons80
            width, height = 80, 72
        elif credit.credit_type == ResourceType.MAP_ICONS:
            database = RESOURCES.map_icons
            image = database.get(credit.sub_nid)
            if not image:
                return None

            if not image.image:
                image.image = engine.image_load(image.full_path)
            im = image.image.copy()
            return im
        else:
            return None

        image = database.get(credit.sub_nid)
        if not image:
            return None

        if not image.image:
            image.image = engine.image_load(image.full_path)
        im = engine.subsurface(image.image, (credit.icon_index[0] * width, credit.icon_index[1] * height, width, height))
        im = im.convert()
        engine.set_colorkey(im, COLORKEY, rleaccel=True)
        return im

class CreditMenu(Choice):
    def __init__(self, options, ignore=None):
        topleft = (4, 4)
        background = 'menu_bg_brown'

        super().__init__(None, options, topleft, background, info=None)

        self.shimmer = 3
        self.gem = 'brown'
        self.set_limit(9)
        if ignore:
            self.set_ignore(ignore)

    def create_options(self, options, info_descs=None):
        self.set_limit(9)
        self.options.clear()
        for idx, option in enumerate(options):
            option = CreditOption(idx, option)
            self.options.append(option)

        buffer = self.limit - len(options)
        for num in range(buffer):
            option = EmptyOption(len(options) + num)
            self.options.append(option)

    def get_menu_width(self):
        return 80

class CreditOption(BasicOption):
    def width(self):
        return 84

    def height(self):
        return 16

    def get_color(self):
        if self.ignore:
            return 'yellow'
        return self.color

    def draw(self, surf, x, y):
        main_color = self.get_color()
        main_font = self.font

        s = self.display_text
        width = text_width(main_font, s)
        if width > 66:
            main_font = 'narrow'

        render_text(surf, [main_font], s, [main_color], (x + 6, y))

# Testing
# Run "python -m app.engine.credit_state" from main directory
if __name__ == '__main__':
    import random
    credit_entries = [CreditEntry(0, 0, ResourceType.ICONS16, 'Graphic'),
                      CreditEntry(1, 0, ResourceType.ICONS16, 'Graphic'),
                      CreditEntry(2, 0, ResourceType.ICONS32, 'Graphic'),
                      CreditEntry(3, 0, ResourceType.ICONS32, 'Graphic'),
                      CreditEntry(4, 0, ResourceType.ICONS16, 'Resources'),
                      CreditEntry(5, 0, ResourceType.ICONS16, 'Resources'),
                      CreditEntry(6, 'Special Thanks', 'List', 'Music'),
                      CreditEntry(7, 'Special Thanks', 'List', 'Resources'),
                      CreditEntry(8, 'Other', 'List', 'Resources'),
                      CreditEntry(9, 'Special Thanks', 'Text', 'Resources'),
                      CreditEntry(10, 'Other', 'Text', 'Music')]
    random.shuffle(credit_entries)
    credit_catalog = CreditCatalog()
    for credit in credit_entries:
        credit_catalog.append(credit)

    options, ignore, ordered_credits = populate_options(credit_catalog)
    for i in range(len(options)):
        print(options[i])
        print(ignore[i])
        for credit in ordered_credits[i]:
            print(credit)
        print()