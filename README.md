## About 
**TACHYS Editor** is a QT-based editor for encoding (primarily Ancient Greek) texts in Leiden+ according
to the EpiDoc standard. It provides helpful functions to make encoding as simple, correct, and **fast** as
humanly possible.

## Main Features
- Live Debugging with error highlighting
- Syntax Highlighting
- Whitelist for Ancient Greek text (which proactively avoids typos produced by confusing Latin and Greek characters)
- Keyboard shortcuts for Leiden+ syntax
- Automatic line numbering
- Automatic \<div> numbering
- Automatic numeral conversion (according to the Byzantine system)
- Automatic lunate sigma conversion
- Change tracking for peer review (view changes, export changes, import changes)
- XML export

## Quick Guide
### Tips for encoding faster
- Use shortcuts on marked text (e.g. Ctrl + 0 will instantly apply numeral markup)

## Planned Features
(*Ranked from higher to lower priority*)
- Change all line numbers within a \<div>
- Tag system for references similar to abbreviations used in papyrological editions (e.g. Pr for Preisendanz)
- Support for encoding Latin texts


## Known Issues
| Description                                                                                    | Priority | Workaround                  |
|------------------------------------------------------------------------------------------------|----------|-----------------------------|
| Rare application crash when a \<div> is automatically created                                  | high     | Write the \<div\> manually  |
| Keyboard shortcuts may not work for all international keyboards                                | high     | None                        |
| Syntax highlighting is not correctly applied in heavily nested apparatus tags                  | low      | None                        |              
| A character with underdot directly followed by supralinear stroke is treated as a syntax error | low      | Use alternative syntax ¯ν̣¯ |


## Copyright & License
**Required Notice**: Copyright Oliver Donath (https://github.com/oli-do). 
This software is licensed under the terms and conditions of PolyForm Noncommercial 1.0.0.