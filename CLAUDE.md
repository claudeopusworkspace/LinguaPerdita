# Lingua Perdita

## Project Overview
Idle/incremental game about translating a lost language. Built with PyGame + IdleGameEngine + GlyphForge.
Part of RapidFireGames — fail-fast methodology: validate economy via simulation before investing in UI.

## Stack
- **Python 3.x** with PyGame for rendering
- **IdleGameEngine** (https://github.com/claudeopusworkspace/IdleGameEngine) — provides GameDefinition/GameRuntime/Simulation
- **GlyphForge** (https://github.com/claudeopusworkspace/glyphforge) — procedural glyph generation

## Project Structure
```
lingua_perdita/          # Main package
├── constants.py         # All balance tuning values
├── language.py          # Procedural word/root/text generation
├── game_def.py          # LanguageModel → GameDefinition
├── simulate.py          # Economy simulation (fail-fast checkpoint)
├── presenter.py         # GameRuntime wrapper + game-specific queries
├── save.py              # JSON persistence
├── glyphs.py            # GlyphForge → pygame surface cache
└── ui/                  # PyGame UI layer
    ├── app.py           # Main loop, screen management
    ├── theme.py         # Colors, fonts, layout constants
    ├── renderer.py      # Drawing primitives
    └── screens.py       # TabletScreen, ShopScreen, LexiconScreen
```

## Commands
- `python -m lingua_perdita` — Launch the game
- `python -m lingua_perdita simulate` — Run economy simulation
- `pytest` — Run all tests

## Conventions
- All balance tuning values live in `constants.py` — never hardcode numbers elsewhere
- Language model is pure data, no engine dependency
- Game definition translates language model → engine elements
- Presenter is the only bridge between UI and engine
- Tests run before commits
