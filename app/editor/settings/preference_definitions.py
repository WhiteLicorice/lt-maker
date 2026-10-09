"""
Declarative preference definitions using enums.
All preferences are defined here in one central location.
"""
from enum import Enum
from dataclasses import dataclass
from typing import Any, Optional, List
from PyQt5.QtCore import Qt

from app import dark_theme


class PreferenceType(Enum):
    """Types of preference widgets available."""
    BOOLEAN = "boolean"
    INTEGER = "integer"
    DOUBLE = "double"
    CHOICE = "choice"
    FONT = "font"
    MOUSEBINDING = "mousebinding"
    KEYBINDING = "keybinding"


class PreferenceCategory(Enum):
    """Categories/tabs for organizing preferences."""
    EDITOR = "Editor"
    INTERFACE = "Interface"
    KEYBINDINGS = "Keybindings"
    ADVANCED = "Advanced"


@dataclass
class PreferenceDefinition:
    """
    Complete definition of a preference setting.

    Fields:
        setting_name: Internal name used by settings controller (e.g., 'select_button')
        label: Display label shown in UI (e.g., 'Select Button')
        pref_type: Type of preference widget (BOOLEAN, INTEGER, etc.)
        category: Which tab/category it belongs to
        default_value: Default value if not set
        section: Optional section name within the tab
        tooltip: Optional tooltip text

        # Type-specific parameters:
        min_val: Minimum value for INTEGER/DOUBLE types
        max_val: Maximum value for INTEGER/DOUBLE types
        decimals: Decimal places for DOUBLE type
        options: List of choices for CHOICE type
        monospace_only: Whether to filter only monospace fonts (FONT type)
    """
    setting_name: str
    label: str
    pref_type: PreferenceType
    category: PreferenceCategory
    default_value: Any
    section: Optional[str] = None
    tooltip: Optional[str] = None

    # Type-specific parameters
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    decimals: Optional[int] = None
    options: Optional[List[str]] = None
    monospace_only: Optional[bool] = None


class Preference(Enum):
    """
    Master enum of all preferences in the application.
    Each preference is fully defined with all its metadata.
    """

    # ========== EDITOR TAB ==========

    # Mouse Settings section
    SELECT_BUTTON = PreferenceDefinition(
        setting_name="select_button",
        label="Select Button",
        pref_type=PreferenceType.MOUSEBINDING,
        category=PreferenceCategory.EDITOR,
        section="Mouse Settings",
        default_value=Qt.LeftButton,
        tooltip="Mouse button for selecting in Unit and Tile Painter Menus"
    )

    PLACE_BUTTON = PreferenceDefinition(
        setting_name="place_button",
        label="Place Button",
        pref_type=PreferenceType.MOUSEBINDING,
        category=PreferenceCategory.EDITOR,
        section="Mouse Settings",
        default_value=Qt.RightButton,
        tooltip="Mouse button for placing in Unit and Tile Painter Menus"
    )

    # Autocomplete section
    AUTOCOMPLETE_ENABLED = PreferenceDefinition(
        setting_name="event_autocomplete",
        label="Enable Event Autocomplete",
        pref_type=PreferenceType.BOOLEAN,
        category=PreferenceCategory.EDITOR,
        section="Autocomplete",
        default_value=True
    )

    AUTOCOMPLETE_BUTTON = PreferenceDefinition(
        setting_name="autocomplete_button",
        label="Autocomplete Button",
        pref_type=PreferenceType.KEYBINDING,
        category=PreferenceCategory.EDITOR,
        section="Autocomplete",
        default_value=Qt.Key_Tab
    )

    # Event Editor section
    EVENT_REOPEN_LAST = PreferenceDefinition(
        setting_name="event_reopen_last",
        label="Reopen Last Opened Event",
        pref_type=PreferenceType.BOOLEAN,
        category=PreferenceCategory.EDITOR,
        section="Event Editor",
        default_value=False,
        tooltip="The event editor opens on the event that was open when it last closed, "
                "rather than on the first event of the selected chapter."
    )

    # Save Settings section
    AUTOSAVE_TIME = PreferenceDefinition(
        setting_name="autosave_time",
        label="Autosave Interval (minutes)",
        pref_type=PreferenceType.DOUBLE,
        category=PreferenceCategory.EDITOR,
        section="Save Settings",
        default_value=5.0,
        min_val=0.5,
        max_val=99.0,
        decimals=1
    )

    SAVE_BACKUP = PreferenceDefinition(
        setting_name="save_backup",
        label="Make Additional Backup Save",
        pref_type=PreferenceType.BOOLEAN,
        category=PreferenceCategory.EDITOR,
        section="Save Settings",
        default_value=False
    )

    SAVE_CHUNKS = PreferenceDefinition(
        setting_name="save_chunks",
        label="Save Data in Chunks",
        pref_type=PreferenceType.BOOLEAN,
        category=PreferenceCategory.EDITOR,
        section="Save Settings",
        default_value=False,
        tooltip="Saving data in chunks makes it easier to collaborate with others, but also makes saving slower."
    )

    # ========== INTERFACE TAB ==========

    # Theme section
    THEME = PreferenceDefinition(
        setting_name="theme",
        label="Application Theme",
        pref_type=PreferenceType.CHOICE,
        category=PreferenceCategory.INTERFACE,
        section="Theme",
        default_value="Dark",
        options=[theme.name for theme in dark_theme.ThemeType]  # Will be populated dynamically from dark_theme.ThemeType
    )

    # Fonts section
    CODE_FONT = PreferenceDefinition(
        setting_name="code_font",
        label="Code Font",
        pref_type=PreferenceType.FONT,
        category=PreferenceCategory.INTERFACE,
        section="Fonts",
        default_value="Consolas",
        monospace_only=True
    )

    CODE_FONT_IN_BOXES = PreferenceDefinition(
        setting_name="code_font_in_boxes",
        label="Use Code Font in Code Boxes",
        pref_type=PreferenceType.BOOLEAN,
        category=PreferenceCategory.INTERFACE,
        section="Fonts",
        default_value=False
    )

    # ========== KEYBINDINGS TAB ==========

    EDITOR_CLOSE_BUTTON = PreferenceDefinition(
        setting_name="editor_close_button",
        label="Editor Close Button",
        pref_type=PreferenceType.KEYBINDING,
        category=PreferenceCategory.KEYBINDINGS,
        section="Keyboard Shortcuts",
        default_value=Qt.Key_Escape
    )

    # ========== ADVANCED TAB ==========

    # Startup section
    AUTO_OPEN_LAST = PreferenceDefinition(
        setting_name="auto_open",
        label="Automatically Open Most Recent Project",
        pref_type=PreferenceType.BOOLEAN,
        category=PreferenceCategory.ADVANCED,
        section="Startup",
        default_value=False,
        tooltip="Skips the recent project dialog."
    )

    # Debug section
    CRASH_LOGS = PreferenceDefinition(
        setting_name="crash_logs",
        label="Show Error Logs on Crash",
        pref_type=PreferenceType.BOOLEAN,
        category=PreferenceCategory.ADVANCED,
        section="Debug",
        default_value=True
    )

    @property
    def definition(self) -> PreferenceDefinition:
        """Get the PreferenceDefinition for this preference."""
        return self.value

    @staticmethod
    def get_by_category(category: PreferenceCategory) -> List['Preference']:
        """Get all preferences for a specific category."""
        return [pref for pref in Preference if pref.definition.category == category]

    @staticmethod
    def get_by_section(category: PreferenceCategory, section: str) -> List['Preference']:
        """Get all preferences for a specific section within a category."""
        return [
            pref for pref in Preference
            if pref.definition.category == category and pref.definition.section == section
        ]

    @staticmethod
    def get_sections_for_category(category: PreferenceCategory) -> List[str]:
        """Get all unique section names for a category, in order of first appearance."""
        sections = []
        for pref in Preference:
            if pref.definition.category == category:
                section = pref.definition.section
                if section and section not in sections:
                    sections.append(section)
        return sections


# Mapping helpers for backward compatibility with existing code
name_to_button = {'L-click': Qt.LeftButton, 'R-click': Qt.RightButton}
button_to_name = {v: k for k, v in name_to_button.items()}

# Storage type mapping for QSettings
# Maps PreferenceType to the Python type used for QSettings storage
PREFERENCE_TYPE_TO_STORAGE_TYPE = {
    PreferenceType.BOOLEAN: bool,
    PreferenceType.INTEGER: int,
    PreferenceType.DOUBLE: float,
    PreferenceType.FONT: str,
    PreferenceType.CHOICE: str,  # Default for choices
    PreferenceType.MOUSEBINDING: type(Qt.LeftButton),  # Qt.MouseButton type
    PreferenceType.KEYBINDING: int,  # Qt.Key type
}