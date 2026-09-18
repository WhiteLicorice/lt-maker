from app.constants import WINWIDTH, WINHEIGHT
from app.data.database.database import DB

from app.engine.sound import get_sound_thread
from app.engine.fonts import FONT
from app.engine.game_menus import menu_options
from app.engine.state import MapState

from app.engine import engine, text_funcs, menus, action, \
    icons, help_menu, banner, base_surf
from app.engine.game_state import game
from app.engine.source_type import SourceType

class SkillOption(menu_options.BasicOption):
    """
    Skill Prefabs, not Skill Objects
    """
    def __init__(self, idx, skill):
        self.idx = idx
        self.skill = skill
        self.help_box = None
        self.font = 'text'
        self.color = 'white'
        self.ignore = False

    def get(self):
        return self.skill

    def set_text(self, text):
        pass

    def set_skill(self, skill):
        self.skill = skill

    def width(self):
        return FONT[self.font].width(self.skill.name) + 24

    def height(self):
        return 16

    def get_color(self):
        main_color = 'grey'
        if not self.ignore and self.color:
            main_color = self.color
        return main_color

    def get_help_box(self):
        text = text_funcs.translate_and_text_evaluate(
            self.skill.desc,
            unit=game.get_unit(self.skill.owner_nid),
            self=self.skill,
            local_args={'skill': self.skill})
        return help_menu.HelpDialog(text, name=self.skill.name)

    def draw(self, surf, x, y):
        icon = icons.get_icon(self.skill)
        if icon:
            surf.blit(icon, (x + 2, y))
        color = self.get_color()
        FONT[self.font].blit(self.skill.name, surf, (x + 20, y), color)

class FeatChoice(menus.Table):
    def create_options(self, options, info_desc=None):
        self.options.clear()
        for idx, option in enumerate(options):
            option = SkillOption(idx, option)
            option.help_box = option.get_help_box()
            self.options.append(option)

class FeatChoiceState(MapState):
    name = 'feat_choice'
    transparent = True
    menu = None
    unit = None

    def start(self):
        self.unit = game.memory['current_unit']
        feats = DB.skills.get_feats()

        current_skills = [skill.nid for skill in self.unit.skills]
        ignore = [True if feat.nid in current_skills else False for feat in feats]
        self.menu = FeatChoice(self.unit, feats, (5, 2), 'center')
        self.menu.shimmer = 2
        self.menu.topleft = (self.menu.get_topleft()[0], WINHEIGHT - self.menu.get_menu_height() - 4)
        self.menu.set_ignore(ignore)

    def begin(self):
        self.fluid.reset_on_change_state()

    def take_input(self, event):
        first_push = self.fluid.update()
        directions = self.fluid.get_directions()

        self.menu.handle_mouse()
        if 'DOWN' in directions:
            if self.menu.move_down(first_push):
                get_sound_thread().play_sfx('Select 6')
        elif 'UP' in directions:
            if self.menu.move_up(first_push):
                get_sound_thread().play_sfx('Select 6')
        if 'RIGHT' in directions:
            if self.menu.move_right(first_push):
                get_sound_thread().play_sfx('Select 6')
        elif 'LEFT' in directions:
            if self.menu.move_left(first_push):
                get_sound_thread().play_sfx('Select 6')

        if event == 'BACK':
            if self.menu.info_flag:
                get_sound_thread().play_sfx('Info Out')
            else:
                get_sound_thread().play_sfx('Info In')
            self.menu.toggle_info()

        elif event == 'INFO':
            get_sound_thread().play_sfx('Select 2')
            game.memory['current_unit'] = self.unit
            game.memory['next_state'] = 'info_menu'
            game.state.change('transition_to')

        elif event == 'SELECT':
            get_sound_thread().play_sfx('Select 1')
            selection = self.menu.get_current()
            game.state.back()
            act = action.AddSkill(self.unit, selection.nid, source=self.unit.nid, source_type=SourceType.PERSONAL)
            action.do(act)
            if act.skill_obj:
                game.alerts.append(banner.GiveSkill(self.unit, act.skill_obj))
                game.state.change('alert')

    def update(self):
        self.menu.update()

    def draw_face(self, surf):
        im = icons.get_portrait_with_size(self.unit, 80, 72)
        if im:
            topleft = self.menu.get_topleft()
            surf.blit(im, ((WINWIDTH - im.get_width())//2, topleft[1] - im.get_height()))

    def draw_label(self, surf):
        label = text_funcs.translate('Feat Choice')
        label_width = FONT['text'].width(label) + 16
        bg_surf = base_surf.create_base_surf(label_width, 24)
        FONT['text'].blit_center(label, bg_surf, (bg_surf.get_width()//2, 4))
        surf.blit(bg_surf, (0, 0))

    def draw(self, surf):
        if self.menu:
            self.draw_face(surf)
            self.draw_label(surf)
            self.menu.draw(surf)
            if self.menu.info_flag:
                self.menu.draw_info(surf)
        return surf
