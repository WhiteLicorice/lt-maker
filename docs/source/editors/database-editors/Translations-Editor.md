# Translations Editor

_last updated 2026-09-18_

This editor is mainly used to provide info text (also known as R-text) for various menu options, as well as to fill out generic dialogue options such as for shops. If an option is missing a description, its intended NID will act as a placeholder. For help with supporting non-English languages, refer to the [Fonts and Languages Guide](Fonts-Guide).

## Title Screen Text

To replace the text that says '_attribution' on the title screen of your project, simply add an entry to the translations with the NID `_attribution`.

## Event Region Text

If you create an event region, such as an Escape or Seize event, using the `INFO` button on that command in the menu will cause the default text 'EVENTNAME_desc' to appear. This can be replaced with meaningful text by adding an entry with that NID in the translations editor.

## Renaming the Spells Option in the Map Menu

By default, usable staves will be listed under the Spells option in the map menu. To have it read "Staff" like in the official Fire Emblem GBA games, add an entry for `Spells` and its description be `Staff`.