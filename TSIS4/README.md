# TSIS4 - Snake Game

Base files used: `practice10.md` and `practice11.md`, Snake sections.

Implemented from the base practices:
- Border collision and self collision.
- Food placement that avoids walls, snake body and obstacles.
- Level progression and speed increase by level.
- Score and level display.
- Weighted food and food timeout.
- Comments explain spawning, collision and database logic.

Added from TSIS4:
- PostgreSQL tables `players` and `game_sessions`.
- Username entry on the main menu.
- Automatic score saving after game over.
- Leaderboard screen with Top 10 database results.
- Personal best shown during gameplay.
- Poison food that shortens the snake by 2 segments.
- Power-ups: speed boost, slow motion and shield.
- Temporary field power-up timeout of 8 seconds.
- Obstacles from level 3 that avoid trapping the snake head.
- `settings.json` for snake color, grid overlay and sound toggle.
- Main Menu, Game Over, Leaderboard and Settings screens.
- Visual assets for snake head/body, food, poison, power-ups, obstacles and UI panel.
- Sound effects for menu selection, eating food, poison, power-ups, collision and game over.

Assets:
- Images are in `assets/images/`: `snake_head.bmp`, `snake_body.bmp`, `food.bmp`, `poison.bmp`, `speed.bmp`, `slow.bmp`, `shield.bmp`, `obstacle.bmp`, `ui_panel.bmp`.
- Sounds are in `assets/sounds/`: `menu.wav`, `eat.wav`, `poison.wav`, `powerup.wav`, `collision.wav`, `gameover.wav`.
- `assets.py` loads everything by relative path from the TSIS4 folder.
- Fallback: if an image is missing, the game draws the cell with `pygame.draw`. If sound loading fails, the game continues silently.
- Sound is controlled by the Settings screen and saved in `settings.json`.

Run:
```bash
pip install -r requirements.txt
python main.py
```

Before running with leaderboard support, create the PostgreSQL database or set
`PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, `PGPASSWORD`. The default database
name is `snake_tsis4`. If the database is unavailable, the game still opens but
leaderboard features are disabled.

You can replace the placeholder `.bmp` and `.wav` files with your own assets using the same filenames.
