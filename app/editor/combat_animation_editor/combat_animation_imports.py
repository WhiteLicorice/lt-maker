import os, glob

from typing import Optional

from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtGui import QPixmap, qRgb, QColor, QPainter

from app.constants import COLORKEY
from app.utilities import str_utils
from app.data.resources.resources import RESOURCES
from app.data.resources import combat_anims, combat_commands, combat_palettes

from app.editor.combat_animation_editor.animation_import_utils import \
    convert_gba, simple_crop, split_doubles, find_empty_pixmaps, combine_identical_commands, update_anim_full_image
from app.editor.settings import MainSettingsController
from app.editor.file_manager.project_file_backend import DEFAULT_PROJECT

import app.editor.utilities as editor_utilities

import logging

def populate_palettes(current, images, nid):
    for image_fn in images:
        palette_name = os.path.split(image_fn)[-1][:-4].split('-')[-1]
        palette_nid = nid + '_' + palette_name
        logging.debug("palette_nid: %s", palette_nid)
        palette_names = [_[0] for _ in current.palettes]
        logging.debug("palette name: %s %s", palette_name, palette_name in palette_names)
        if palette_name in palette_names:
            # Check whether this image uses colors the palette doesn't have yet.
            # Every color has to earn a palette slot: the conversion below rewrites only
            # the colors the palette knows, and leaves the rest in the frame as literal RGB
            idx = palette_names.index(palette_name)
            orig_palette_nid = current.palettes[idx][1]
            orig_palette = RESOURCES.combat_palettes.get(orig_palette_nid)
            pix = QPixmap(image_fn)
            palette_colors = editor_utilities.find_palette(pix.toImage())
            new_colors = editor_utilities.assign_new_colors(orig_palette, palette_colors)
            if new_colors:
                logging.debug("Adding %s to palette %s", new_colors, orig_palette_nid)
                orig_palette.colors.update(new_colors)
        else:
            if palette_nid not in RESOURCES.combat_palettes:
                # Need to create palette
                pix = QPixmap(image_fn)
                palette_colors = editor_utilities.find_palette(pix.toImage())
                logging.debug("Creating new palette %s", palette_colors)
                new_palette = combat_palettes.Palette(palette_nid)
                new_palette.assign_colors(palette_colors)
                RESOURCES.combat_palettes.append(new_palette)
            current.palettes.append([palette_name, palette_nid])

def add_frames(index_fn, current, new_weapon, images):
    # Now add frames to weapon animation
    with open(index_fn, encoding='utf-8') as index_fp:
        index_lines = [line.strip() for line in index_fp.readlines()]
        index_lines = [line.split(';') for line in index_lines]

    # Use the first palette
    palette_name, palette_nid = current.palettes[0]
    palette = RESOURCES.combat_palettes.get(palette_nid)

    # Need to convert to universal coord palette
    convert_dict = editor_utilities.get_color_conversion(palette)
    logging.debug("Add Frames: Palette Name: %s, Palette Nid: %s, Conversion Dict: %s", palette_name, palette_nid, editor_utilities.human_readable(convert_dict))
    main_pixmap = QPixmap(images[0])
    for i in index_lines:
        # Only accepts length 4 lines
        if len(i) != 4:
            logging.warning("Line %s is formatted incorrectly", i)
            continue
        nid = i[0]
        x, y = [int(_) for _ in i[1].split(',')]
        width, height = [int(_) for _ in i[2].split(',')]
        offset_x, offset_y = [int(_) for _ in i[3].split(',')]
        new_pixmap = main_pixmap.copy(x, y, width, height)
        assert width > 0 and height > 0
        # Convert to universal base palette
        leftover = editor_utilities.find_unconvertible_colors(new_pixmap.toImage(), convert_dict)
        if leftover:
            logging.error("Frame %s uses colors missing from palette %s: %s. They will be stored raw "
                          "and read back as palette coords", nid, palette_nid, leftover)
        new_pixmap = editor_utilities.color_convert_pixmap(new_pixmap, convert_dict)
        new_frame = combat_anims.Frame(nid, (x, y, width, height), (offset_x, offset_y), pixmap=new_pixmap)
        # print(new_frame.nid, id(new_frame.pixmap), new_frame.pixmap.width(), new_frame.pixmap.height(), editor_utilities.find_palette(QImage(new_frame.pixmap)))
        new_weapon.frames.append(new_frame)
    return main_pixmap

def build_full_image(main_pixmap, new_weapon):
    sprite_sheet = QPixmap(main_pixmap.width(), main_pixmap.height())
    sprite_sheet.fill(QColor(0, 0, 0))
    painter = QPainter()
    painter.begin(sprite_sheet)
    for frame in new_weapon.frames:
        x, y, width, height = frame.rect
        painter.drawPixmap(x, y, frame.pixmap)
    painter.end()
    new_weapon.pixmap = sprite_sheet

def add_poses(fn, new_weapon):
    # Now add poses to the weapon anim
    with open(fn, encoding='utf-8') as script_fp:
        script_lines = [line.strip() for line in script_fp.readlines()]
        script_lines = [line.split(';') for line in script_lines if line and not line.startswith('#')]
    current_pose = None
    for line in script_lines:
        if line[0] == 'pose':
            current_pose = combat_anims.Pose(line[1])
            new_weapon.poses.append(current_pose)
        else:
            command = combat_commands.parse_text(';'.join(line))
            if command:
                current_pose.timeline.append(command)

def import_from_legacy(current, fn):
    """
    Imports weapon animations from a Legacy formatted combat animation script file.

    Parameters
    ----------
    current: CombatAnimation
        Combat animation to install new weapon animation onto
    fn: str, filename
        "*-Script.txt" file to read from
    """

    logging.info("Import from legacy script: %s", fn)
    if '-Script.txt' not in fn:
        QMessageBox.critical(None, "Error", "Not a valid combat animation script file: %s" % fn)
        return
    kind = os.path.split(fn)[-1].replace('-Script.txt', '')
    logging.info("Script kind: %s", kind)
    nid, weapon = kind.split('-')
    index_fn = fn.replace('-Script.txt', '-Index.txt')
    if not os.path.exists(index_fn):
        QMessageBox.critical(None, "Error", "Could not find associated index file: %s" % index_fn)
        return
    # glob.escape first -- a '[' or ']' anywhere in the path is a glob character class,
    # so an unescaped path silently matches nothing. It leaves '-Script.txt' alone
    images = glob.glob(glob.escape(fn).replace('-Script.txt', '-*.png'))
    if not images:
        QMessageBox.critical(None, "Error", "Could not find any associated palettes")
        return

    # Populate palettes
    populate_palettes(current, images, nid)
    new_weapon = combat_anims.WeaponAnimation(weapon)

    main_pixmap = add_frames(index_fn, current, new_weapon, images)
    # print([(frame.nid, id(frame.pixmap)) for frame in new_weapon.frames])

    # Need to build full image file now
    build_full_image(main_pixmap, new_weapon)
    # print(id(new_weapon), new_weapon.nid, id(new_weapon.pixmap), new_weapon.pixmap.width(), new_weapon.pixmap.height())
    main_pixmap.save("main_pixmap.png")
    new_weapon.pixmap.save("new_weapon_pixmap.png")

    add_poses(fn, new_weapon)
    # Actually add weapon to current
    if new_weapon.nid in current.weapon_anims:
        current.weapon_anims.remove_key(new_weapon.nid)
    current.weapon_anims.append(new_weapon)
    # print(id(new_weapon), id(new_weapon.pixmap))

def get_child_effects(fn_dir: str, current: combat_anims.EffectAnimation):
    for pose in current.poses:
        for command in pose.timeline:
            if command.has_effect():
                subeffect_nid = command.value[0]
                # Check if the effect is in here somewhere
                subeffect_fn = os.path.join(fn_dir, '%s-Script.txt' % subeffect_nid)
                if subeffect_nid not in RESOURCES.combat_effects and os.path.exists(subeffect_fn):
                    import_effect_from_legacy(subeffect_fn)

def import_effect_from_legacy(fn: str):
    """
    Imports effect animations from a Legacy formatted effect animation script file.

    Parameters
    ----------
    fn: str, filename
        "*-Script.txt" file to read from
    """

    logging.info("Import legacy effect from script: %s" % fn)
    fn_dir = os.path.split(fn)[0]
    if '-Script.txt' not in fn:
        QMessageBox.critical(None, "Error", "Not a valid combat animation script file: %s" % fn)
        return
    nid = os.path.split(fn)[-1].replace('-Script.txt', '')
    index_fn = fn.replace('-Script.txt', '-Index.txt')
    if not os.path.exists(index_fn):
        # This is a simple control script that owns many other effects
        current = combat_anims.EffectAnimation(nid)
        add_poses(fn, current)
        # Add necessary child effects
        get_child_effects(fn_dir, current)

        # Actually add effect animation to RESOURCES
        if current.nid in RESOURCES.combat_effects:
            RESOURCES.combat_effects.remove_key(current.nid)
        RESOURCES.combat_effects.append(current)
        return current
        
    # glob.escape first -- a '[' or ']' anywhere in the path is a glob character class,
    # so an unescaped path silently matches nothing. It leaves '-Script.txt' alone
    images = glob.glob(glob.escape(fn).replace('-Script.txt', '-*.png'))
    if not images:
        QMessageBox.critical(None, "Error", "Could not find any associated palettes")
        return

    # Populate palettes
    current = combat_anims.EffectAnimation(nid)
    populate_palettes(current, images, nid)

    main_pixmap = add_frames(index_fn, current, current, images)

    # Need to build full image file now
    build_full_image(main_pixmap, current)

    # Now add poses to the effect anim
    add_poses(fn, current)

    # Determine if this has any child effects
    get_child_effects(fn_dir, current)
    
    # Actually add effect animation to RESOURCES
    if current.nid in RESOURCES.combat_effects:
        RESOURCES.combat_effects.remove_key(current.nid)
    RESOURCES.combat_effects.append(current)

    # Need to save the full image somewhere
    settings = MainSettingsController()
    if os.path.basename(settings.get_current_project()) != DEFAULT_PROJECT:
        path = os.path.join(settings.get_current_project(), 'resources', 'combat_effects')
        RESOURCES.combat_effects.save_image(path, current)

    return current

# === IMPORT FROM GBA ========================================================
def get_palette(pixmap: QPixmap) -> list:
    im = pixmap.toImage()
    w = im.width()
    # Image is always an extra 8 pixels wide, to accomodate palette!
    assert w == 248 or w == 448
    colors = []
    for x in range(w - 8, w, -1):  # Reverse
        for y in range(2):
            color = im.pixel(x, y)
            if color not in colors:
                colors.append(color)
    palette = [QColor(color) for color in colors]
    palette = [(c.red(), c.green(), c.blue()) for c in palette]
    return palette

def import_from_gba(current, fn):
    """
    Imports weapon animations from GBA formatted combat animation script file.

    Parameters
    ----------
    current: CombatAnimation
        Combat animation to install new weapon animation onto
    fn: str, filename
        "*.txt" file to read from
    """
    weapon_types = {'Sword', 'Lance', 'Axe', 'Disarmed', 'Unarmed', 'Handaxe',
                    'Bow', 'Magic', 'Staff', 'Monster', 'Dragonstone', 'Refresh',
                    'Transform', 'Revert', 'Knife'}
    logging.info("Import GBA weapon animation from script %s", fn)
    head, tail = os.path.split(fn)
    # if any(bad_char in head for bad_char in ('[', ']', '*', '?', '!')):
    #     QMessageBox.critical(None, "Error", "Bad character in filepath %s found. Remove all ('[', ']', '*', '?', '!') characters from the filepath." % head)
    #     return
    tail = tail.replace('_without_comment', '')
    
    weapon_type = tail[:-4].lower().capitalize()
    if weapon_type not in weapon_types:
        QMessageBox.critical(None, "Error", "Weapon type %s not a supported weapon type!" % weapon_type)
        return
    if weapon_type == 'Disarmed':
        weapon_type = 'Unarmed'
    elif weapon_type == 'Monster':
        weapon_type = 'Neutral'

    images = []
    for image_fn in os.listdir(head):
        if image_fn.endswith('.png'):
            images.append(os.path.join(head, image_fn))
    # image_paths = os.path.join(head, '*.png')
    # print(image_paths)
    # images = glob.glob(image_paths)
    logging.info("Images located: %s", images)
    # Remove main sheet if it exists
    images = list(sorted([path for path in images if 'Sheet' not in os.path.split(path)[-1]]))
    if not images:
        QMessageBox.critical(None, "Error", "Cannot find valid images in %s!" % head)
        return
    # Convert to pixmaps
    pixmaps = {os.path.split(path)[-1][:-4]: QPixmap(path) for path in images}
    # Convert to GBA colors
    pixmaps = {name: convert_gba(pix) for name, pix in pixmaps.items()}
    # Find palette
    all_palette_colors = editor_utilities.find_palette_from_multiple([pix.toImage() for pix in pixmaps.values()])
    my_palette = None
    palette_nids = [palette[1] for palette in current.palettes]
    for palette_nid in palette_nids:
        palette = RESOURCES.combat_palettes.get(palette_nid)
        if palette.is_similar(all_palette_colors):
            my_palette = palette
            logging.info("Using existing palette! %s" % palette.nid)
            # Change first color to colorkey
            colorkey_conversion = {
                qRgb(*all_palette_colors[0]): editor_utilities.qCOLORKEY,
                qRgb(0, 0, 0): qRgb(40, 40, 40),  # Need to make sure there's no 0, 0, 0 in the image
            }
            pixmaps = {name: editor_utilities.color_convert_pixmap(pixmap, colorkey_conversion) for name, pixmap in pixmaps.items()}
            break
    else:
        logging.info("Generating new palette...")
        palette_nid = str_utils.get_next_name("New Palette", RESOURCES.combat_palettes.keys())
        my_palette = combat_palettes.Palette(palette_nid)
        RESOURCES.combat_palettes.append(my_palette)
        palette_name = str_utils.get_next_name('GenericBlue', [name for name, nid in current.palettes])
        current.palettes.append([palette_name, my_palette.nid])
        # Change first color to colorkey
        colorkey_conversion = {
            qRgb(*all_palette_colors[0]): editor_utilities.qCOLORKEY,
            qRgb(0, 0, 0): qRgb(40, 40, 40),  # Need to make sure there's no 0, 0, 0 in the image
        }
        pixmaps = {name: editor_utilities.color_convert_pixmap(pixmap, colorkey_conversion) for name, pixmap in pixmaps.items()}
        all_palette_colors[0] = COLORKEY
        if (0, 0, 0) in all_palette_colors:
            idx = all_palette_colors.index((0, 0, 0))
            all_palette_colors[idx] = (40, 40, 40)

        my_palette.assign_colors(all_palette_colors)

    # Now do a simple crop to get rid of palette extras
    pixmaps = {name: simple_crop(pix) for name, pix in pixmaps.items()}
    # Split double images into "_under" image
    pixmaps = split_doubles(pixmaps)
    # Convert pixmaps to new palette colors
    convert_dict = editor_utilities.get_color_conversion(my_palette)
    pixmaps = {name: editor_utilities.color_convert_pixmap(pixmap, convert_dict) for name, pixmap in pixmaps.items()}
    # What the transparent pixels hold now. A palette without the colorkey leaves them as the colorkey itself.
    # Measuring frames against it matters because a frame's top left pixel can be artwork
    colorkey = convert_dict.get(editor_utilities.qCOLORKEY, editor_utilities.qCOLORKEY)
    # Determine which pixmaps should be replaced by "wait" commands
    empty_pixmaps = find_empty_pixmaps(pixmaps, colorkey)

    # So now we have melee_anim and ranged_anim with all poses
    melee_weapon_anim, ranged_weapon_anim = parse_gba_script(fn, pixmaps, weapon_type, empty_pixmaps, colorkey)

    for pose in melee_weapon_anim.poses:
        combine_identical_commands(pose)
    for pose in ranged_weapon_anim.poses:
        combine_identical_commands(pose)

    # Animation collation
    update_anim_full_image(melee_weapon_anim)
    update_anim_full_image(ranged_weapon_anim)

    def unarmed_pose_setup(weapon_anim):
        stand_pose = weapon_anim.poses.get('Stand')
        dodge_pose = weapon_anim.poses.get('Dodge')
        weapon_anim.poses.clear()
        weapon_anim.poses.append(stand_pose)
        weapon_anim.poses.append(dodge_pose)

    def transform_pose_setup(weapon_anim):
        stand_pose = weapon_anim.poses.get('Stand')
        transform_pose = weapon_anim.poses.get('Attack')
        weapon_anim.poses.clear()
        weapon_anim.poses.append(stand_pose)
        weapon_anim.poses.append(transform_pose)

    def add_weapon(weapon_anim):
        if weapon_anim.nid in current.weapon_anims:
            current.weapon_anims.remove_key(weapon_anim.nid)
        current.weapon_anims.append(weapon_anim)

    # Now write scripts
    if weapon_type == 'Sword':
        melee_weapon_anim.nid = "Sword"
        ranged_weapon_anim.nid = "MagicSword"
        add_weapon(melee_weapon_anim)
        add_weapon(ranged_weapon_anim)        
    elif weapon_type == 'Lance':
        melee_weapon_anim.nid = "Lance"
        ranged_weapon_anim.nid = "RangedLance"
        add_weapon(melee_weapon_anim)
        add_weapon(ranged_weapon_anim)        
    elif weapon_type == 'Axe':
        melee_weapon_anim.nid = "Axe"
        ranged_weapon_anim.nid = "MagicAxe"
        add_weapon(melee_weapon_anim)
        add_weapon(ranged_weapon_anim)        
    elif weapon_type == 'Handaxe':
        ranged_weapon_anim.nid = "RangedAxe"
        add_weapon(ranged_weapon_anim)  
    elif weapon_type == 'Knife':
        ranged_weapon_anim.nid = "RangedSword"
        add_weapon(ranged_weapon_anim)       
    elif weapon_type == 'Bow':
        ranged_weapon_anim.nid = "RangedBow"
        add_weapon(ranged_weapon_anim)        
    elif weapon_type == 'Unarmed':
        melee_weapon_anim.nid = "Unarmed"
        # Make sure we only use stand and dodge poses
        unarmed_pose_setup(melee_weapon_anim)
        add_weapon(melee_weapon_anim)
    elif weapon_type == 'Magic':
        ranged_weapon_anim.nid = "MagicGeneric"
        add_weapon(ranged_weapon_anim)
        melee_weapon_anim.nid = "Unarmed"
        unarmed_pose_setup(melee_weapon_anim)
        add_weapon(melee_weapon_anim)
    elif weapon_type == 'Staff':
        ranged_weapon_anim.nid = "MagicStaff"
        add_weapon(ranged_weapon_anim)
    elif weapon_type == 'Neutral':
        melee_weapon_anim.nid = "Neutral"
        add_weapon(melee_weapon_anim)
        ranged_weapon_anim.nid = "RangedNeutral"
        add_weapon(ranged_weapon_anim)
    elif weapon_type == 'Dragonstone':
        ranged_weapon_anim.nid = "Dragonstone"
        add_weapon(ranged_weapon_anim)
    elif weapon_type == 'Refresh':
        ranged_weapon_anim.nid = "Refresh"
        add_weapon(ranged_weapon_anim)
        melee_weapon_anim.nid = "Unarmed"
        unarmed_pose_setup(melee_weapon_anim)
        add_weapon(melee_weapon_anim)
    elif weapon_type == 'Transform':
        melee_weapon_anim.nid = "Transform"
        # Make sure we only use stand and attack poses
        transform_pose_setup(melee_weapon_anim)
        add_weapon(melee_weapon_anim)
    elif weapon_type == 'Revert':
        melee_weapon_anim.nid = "Revert"
        # Make sure we only use stand and attack poses
        transform_pose_setup(melee_weapon_anim)
        add_weapon(melee_weapon_anim)

    # Need to save the full image somewhere
    settings = MainSettingsController()
    if os.path.basename(settings.get_current_project()) != DEFAULT_PROJECT:
        path = os.path.join(settings.get_current_project(), 'resources', 'combat_anims')
        RESOURCES.combat_anims.save_image(path, current)

def parse_gba_script(fn, pixmaps, weapon_type, empty_pixmaps, colorkey):
    # Read script
    # Now add poses to the weapon anim
    with open(fn, encoding='utf-8') as script_fp:
        script_lines = [line.strip() for line in script_fp.readlines()]
        script_lines = [(line[:line.index('#')] if '#' in line else line) for line in script_lines]
        script_lines = [line for line in script_lines if line]

    current_mode: int = None
    current_anim: combat_anims.WeaponAnimation = None
    current_pose: combat_anims.Pose = None
    current_command: combat_commands.CombatAnimationCommand = None
    melee_weapon_anim = combat_anims.WeaponAnimation('prototype')
    ranged_weapon_anim = combat_anims.WeaponAnimation('prototype')
    used_images = set()

    begin = False  # Whether this is the first frame
    crit = False  # Whether this is a critical hit
    start_hit = False  # Whether we need to append our start_hit command after the next frame
    dodge_front = False  # Whether we should use over frames
    throwing_axe = False  # Whether the next 01 command is catching the throwing axe
    shield_toss = False  # Whether the next 01 command ends the shield toss
    loop_end = False  # Whether the next 01 command ends the loop

    def get_pose_name(mode: int) -> (Optional[str], Optional[combat_anims.WeaponAnimation]):
        """
        Determines what pose to use and whether to use
        the melee script or a ranged/magic script
        """
        # Ignore certain modes if magical
        if weapon_type in ('Magic', 'Staff', 'Refresh'):
            if mode not in (5, 6, 7, 8, 9, 11):
                return None, None
        # Only certain modes allowed for transforming and reverting
        if weapon_type in ('Transform', 'Revert'):
            if mode not in (1, 9):
                return None, None
        if mode in (1, 2):
            return 'Attack', melee_weapon_anim
        elif mode in (3, 4):
            return 'Critical', melee_weapon_anim
        elif mode == 5:
            return 'Attack', ranged_weapon_anim
        elif mode == 6:
            return 'Critical', ranged_weapon_anim
        elif mode == 7:
            return 'Dodge', melee_weapon_anim
        elif mode == 8:
            return 'Dodge', ranged_weapon_anim
        elif mode in (9, 10):
            return 'Stand', melee_weapon_anim
        elif mode == 11:
            return 'Stand', ranged_weapon_anim
        elif mode == 12:
            return 'Miss', melee_weapon_anim
        else:
            return None, None

    def parse_text(text):
        command = combat_commands.parse_text(text)
        # If there is a frame in the command,
        # add it to the set of used images
        if command.has_frames():
            frames = command.get_frames()
            if any(f in empty_pixmaps for f in frames):
                command = combat_commands.parse_text('wait;%d' % command.value[0])
            else:
                for frame in frames:
                    used_images.add(frame)
            nonlocal current_command
            current_command = command

        current_pose.timeline.append(command)

    def copy_frame(frame_command, num_frames: int = 1):
        new_command = frame_command.__class__.copy(frame_command)
        new_command.set_frame_count(num_frames)
        current_pose.timeline.append(new_command)

    def wait_for_hit(frame_command):
        if frame_command.nid in ('frame', 'over_frame', 'under_frame', 'frame_with_offset'):
            frame_name = frame_command.value[1]
            new_command = combat_commands.parse_text('wait_for_hit;%s' % frame_name)
            current_pose.timeline.append(new_command)
        elif frame_command.nid == 'dual_frame':
            frame_name1 = frame_command.value[1]
            frame_name2 = frame_command.value[2]
            new_command = combat_commands.parse_text('wait_for_hit;%s;%s' % (frame_name1, frame_name2))
            current_pose.timeline.append(new_command)
        else:
            return

    def save_images(current_pose):
        if current_anim:
            for frame_nid in sorted(used_images):
                if frame_nid in current_anim.frames:
                    # Don't bother if already present
                    continue
                pixmap = pixmaps[frame_nid]
                x, y, width, height = editor_utilities.get_bbox(pixmap.toImage(), colorkey)
                if width > 0 and height > 0:
                    pixmap = pixmap.copy(x, y, width, height)
                    new_frame = combat_anims.Frame(frame_nid, (0, 0, width, height), (x, y), pixmap=pixmap)
                    current_anim.frames.append(new_frame) 
        used_images.clear()

    def cape_animation():
        parse_text('effect;Cape Animation')
        for name, pixmap in pixmaps.items():
            # Make sure to include the extra frames that may be necessary to do this
            used_images.add(name)
        print('Replace "effect;Cape Animation" with actual frames for cape animation in a loop')
        print("For instance:")
        print("start_loop")
        print("    frame;3;Magic033")
        print("    frame;3;Magic034")
        print("end_loop")

    for line in script_lines:
        logging.info("Processing script line: %s", line)
        if line.startswith('/// - '):
            if current_mode:
                save_images(current_pose)
            if line.startswith('/// - Mode '):
                current_mode = int(line[11:])
                pose_name, current_anim = get_pose_name(current_mode)
                current_pose = combat_anims.Pose(pose_name)
                if current_anim:
                    current_anim.poses.append(current_pose)
                current_command = None

                dodge_front = False
                crit = False
                throwing_axe = False
                shield_toss = False
                loop_end = False
            else:
                break  # Done with reading script

        elif line.startswith('C'):
            command_code = line[1:3]
            write_extra_frame = True  # Most commands occur at the same time as the last frame
            if command_code == '00':
                pass  # NOP
            elif command_code == '01':
                if throwing_axe:
                    parse_text('start_loop')
                    copy_frame(current_command)
                    parse_text('end_loop')
                    copy_frame(current_command, 8)
                elif loop_end:
                    parse_text('end_loop')
                    loop_end = False
                elif current_pose.nid == 'Miss':
                    copy_frame(current_command)
                    parse_text('miss')
                    copy_frame(current_command, 30)
                elif current_mode == 5 or current_mode == 6:  # Ranged
                    parse_text('start_loop')
                    copy_frame(current_command, 4)
                    parse_text('end_loop')
                    copy_frame(current_command, 4)
                elif current_pose.nid and 'Dodge' in current_pose.nid:
                    # There are always 31 frames in a dodge
                    counter = 0
                    for command in current_pose.timeline:
                        if command.tag == 'frame':
                            counter += command.value[0]
                    copy_frame(current_command, 31 - counter)
                elif current_mode in (1, 2, 3, 4):  # Hit or Crit
                    wait_for_hit(current_command)
                    if shield_toss:
                        parse_text('end_child_loop')
                        shield_toss = False
                    else:
                        copy_frame(current_command, 4)
                elif current_mode in (9, 10, 11):  # Stand??
                    copy_frame(current_command, 3)
                write_extra_frame = False
            elif command_code == '02':  # Normally marks a dodge animation, but doesn't matter in LT script
                write_extra_frame = False
            elif command_code == '03':
                begin = True
            elif command_code == '04':  # Normally prepares some code for returning to stand
                write_extra_frame = False
            elif command_code == '05':  # Start spell
                if weapon_type == 'Lance':
                    parse_text('spell;Javelin')
                elif weapon_type in ('Axe', 'Handaxe'):
                    parse_text('spell;ThrowingAxe')
                elif weapon_type == 'Bow':
                    parse_text('spell;Arrow')
                else:
                    parse_text('spell')
                write_extra_frame = False
            elif command_code == '06':  # Normally starts enemy turn, but that doesn't happen in LT script
                write_extra_frame = False 
            elif command_code == '07':
                begin = True
            elif command_code in ('08', '09', '0A', '0B', '0C'):  # Start crit
                parse_text('enemy_flash_white;8')
                if current_command:
                    copy_frame(current_command)
                parse_text('foreground_blend;2;255,255,255')
                crit = True
                start_hit = True
                write_extra_frame = False
            elif command_code == '0D':  # End
                if current_command:
                    copy_frame(current_command)
                write_extra_frame = False
            elif command_code == '0E':  # Dodge Start
                write_extra_frame = False
            elif command_code in ('0F', '10', '11', '12'):
                print("Unused command code C%s referenced! Skipping..." % command_code)
            elif command_code == '13':  # Throwing Axe
                if current_command:
                    parse_text('start_loop')
                    copy_frame(current_command)
                    parse_text('end_loop')
                throwing_axe = True
            elif command_code == '14':
                parse_text('screen_shake')
            elif command_code == '15':
                parse_text('platform_shake')
            elif command_code in ('16', '17'):
                print("Unused command code C%s referenced! Skipping..." % command_code)
            elif command_code == '18':
                dodge_front = True
                write_extra_frame = False
            elif command_code == '19':
                parse_text('sound;Bow')
            elif command_code == '1A':  # Start hit
                parse_text('enemy_flash_white;8')
                if current_command:
                    copy_frame(current_command)
                parse_text('screen_flash_white;4')
                crit = False
                start_hit = True
            # Sounds and other effects
            elif command_code == '1B':
                parse_text('sound;Foot Step')
            elif command_code == '1C':
                parse_text('sound;Horse Step 1')
            elif command_code == '1D':
                parse_text('sound;Horse Step 3')
            elif command_code == '1E':
                parse_text('sound;Horse Step 2')
            elif command_code in ('1F', '20', '21'):  # Actual hit
                write_extra_frame = False
            elif command_code == '22':
                parse_text('sound;Weapon Pull')
            elif command_code == '23':
                parse_text('sound;Weapon Push')
            elif command_code == '24':
                parse_text('sound;Weapon Swing')
            elif command_code == '25':
                parse_text('sound;Heavy Wing Flap')
            elif command_code in ('26', '27'):
                parse_text('effect;ShieldToss')
                shield_toss = True
            elif command_code == '28':
                parse_text('sound;ShamanRune')
            elif command_code == '2B':
                parse_text('sound;Armor Shift')
            elif command_code == '2E':
                parse_text('sound;MageInit')
                logging.warning("Change MageInit effect to SageInit effect if working with Sage animations")
            elif command_code == '2F':
                parse_text('sound;MageCrit')
                logging.warning("Change MageCrit effect to SageCrit effect if working with Sage animations")
            elif command_code in ('30', '31', '32'):  # TODO
                # These commands are not actually identical.
                # though they all make dirt effects
                # TODO Figure out the difference
                parse_text('effect;DirtKick')
            elif command_code == '33':
                parse_text('sound;Battle Cry')
            elif command_code == '34':
                parse_text('sound;Step Back 1')
            elif command_code == '35':
                parse_text('sound;Long Wing Flap')
            elif command_code == '36':
                parse_text('sound;Unsheathe')
            elif command_code == '37':
                parse_text('sound;Sheathe')
            elif command_code == '38':
                parse_text('sound;Heavy Spear Spin')
            elif command_code == '39':  
                # Makes the attacker pretend to be hit
                # Attacker flashes white, pauses attacker
                # screen flashes white
                parse_text('self_flash_white;8')
                if current_command:
                    copy_frame(current_command)
                parse_text('screen_flash_white;4')
                if current_command:
                    copy_frame(current_command, 8)
            elif command_code == '3A':
                parse_text('sound;RefreshDance')
            elif command_code == '3B':
                parse_text('sound;RefreshFlute')
            elif command_code == '3C':
                parse_text('sound;Sword Whoosh')
            elif command_code == '3E':
                parse_text('sound;Burning')
            elif command_code == '41':
                parse_text('sound;Axe Pull')
            elif command_code == '42':
                parse_text('sound;Axe Push')
            elif command_code == '43':
                parse_text('sound;Weapon Click')
            elif command_code == '44':
                parse_text('sound;Weapon Shine')
            elif command_code == '45':
                parse_text('sound;Neigh')
            elif command_code == '47':
                cape_animation()
            elif command_code == '49':
                parse_text('sound;SageRune')
            elif command_code == '4B':
                parse_text('sound;MonkRune')
            elif command_code == '4E':
                # These commands (30, 31, 32, 4E) are not actually identical.
                # though they all make dirt effects
                # TODO Figure out the difference
                parse_text('effect;DirtKick')
            elif command_code == '4F':
                parse_text('sound;DruidCrit')
            elif command_code == '51':
                parse_text('screen_flash_white;4')
            elif command_code == '56':
                parse_text('sound;BaelWindup')
            elif command_code == '57':
                parse_text('sound;BaelHit')
            elif command_code == '58':
                parse_text('sound;BaelCrit')
            elif command_code == '59':
                parse_text('sound;Map_Step_Bael')
            elif command_code == '5A':
                parse_text('sound;MautheDoogGrowl')
            elif command_code == '5B':
                parse_text('sound;MautheDoogBite')
            elif command_code == '5C':
                parse_text('sound;MautheDoogHowl')
            elif command_code == '5D':
                parse_text('sound;MautheDoogWalk')
            elif command_code == '5E':
                parse_text('sound;GargoyleBattleCry')
            elif command_code == '5F':
                parse_text('sound;GargoyleLaugh')
            elif command_code == '60':
                parse_text('sound;GorgonMagic1')
            elif command_code == '61':
                parse_text('sound;GorgonMagic2')
            elif command_code == '62':
                parse_text('sound;GorgonMagic3')
            elif command_code == '63':
                parse_text('sound;GorgonScream')
            elif command_code == '64':
                parse_text('sound;ZombieWindup')
            elif command_code == '65':
                parse_text('sound;ZombieHit')
            elif command_code == '66':
                parse_text('sound;Map_Step_Zombie')
            elif command_code == '67':
                parse_text('sound;Map_Step_Skeleton')
            elif command_code == '68':
                parse_text('sound;MogallHit1')
            elif command_code == '6A':
                parse_text('sound;MogallHit2')
            elif command_code == '6B':
                parse_text('sound;MogallCrit1')
            elif command_code == '6C':
                parse_text('sound;MogallCrit2')
            elif command_code == '6F':
                parse_text('sound;GargoyleLanding')
            elif command_code in ('71', '72'):
                # Handles DemonKing transformation routines
                # Unnecessary in LT engine
                pass
            elif command_code == '73':
                parse_text('sound;ZombieCrit')
            elif command_code == '74':
                parse_text('sound;SkeletonCrit')
            elif command_code == '75':
                parse_text('sound;CyclopsBattleCry')
            elif command_code == '76':  # TODO: Not quite correct
                parse_text('sound;DemonKingRoar')
            elif command_code == '77':
                parse_text('sound;DemonKingRoar')
            elif command_code == '79':
                parse_text('sound;StrategistRune')
            elif command_code == '7A':
                parse_text('sound;StrategistCrit')
            elif command_code == '7B':
                parse_text('sound;ManaketeRoar')
            else:
                logging.warning("Unknown Command Code: C%s" % command_code)

            if write_extra_frame and current_command:
                current_command.increment_frame_count()

        elif line.startswith('~~~'):
            pass

        elif line.startswith('L'):
            parse_text('start_loop')
            loop_end = True

        elif line.startswith('S'):
            logging.warning('Cannot parse "%s"! Skipping over this line...' % line)

        else:  # Frame
            try:
                s_l = line.split()
                num_frames = s_l[0]
                png_name = ' '.join(s_l[2:])
            except ValueError:
                logging.error('Cannot parse "%s"! Skipping over this line...' % line)
                continue
            num_frames = int(num_frames)
            name = png_name[:-4]
            if name not in pixmaps:
                logging.error("%s frame not in pixmaps" % name)
            if begin:
                num_frames = 6
                begin = False

            def parse_frame(num_frames, name):
                if dodge_front:
                    parse_text('of;%d;%s' % (num_frames, name))
                elif name + '_under' in pixmaps:
                    parse_text('f;%d;%s;%s' % (num_frames, name, name + '_under'))
                else:
                    parse_text('f;%d;%s' % (num_frames, name))

            if start_hit:
                if crit:
                    parse_text('start_hit')
                    parse_frame(2, name)
                    parse_text('crit_spark')
                else:
                    parse_frame(num_frames + 2, name)
                    parse_text('hit_spark')
                    parse_text('start_hit')
                start_hit = False
            else:
                parse_frame(num_frames, name)

    return melee_weapon_anim, ranged_weapon_anim
