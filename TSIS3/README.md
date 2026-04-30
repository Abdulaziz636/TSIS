# TSIS3 - Racer Game

Base files used: `practice10.md` and `practice11.md`, Racer sections.

Implemented from the base practices:
- Player car movement and scrolling lane-based road.
- Random coins, visible coin counter and weighted coin values.
- Enemy/traffic speed increases as progress and coins grow.
- Comments explain gameplay state, spawning and persistence.

Added from TSIS3:
- Lane hazards: barriers, oil spills and speed bumps.
- Dynamic road events through random hazards and traffic density scaling.
- Traffic cars and safe spawn logic that avoids directly spawning over the player lane most of the time.
- Power-ups: Nitro, Shield and Repair.
- Score combines distance and coins.
- Distance meter and remaining finish distance.
- Persistent Top 10 leaderboard in `leaderboard.json`.
- Username entry on the main menu.
- Main Menu, Leaderboard, Settings and Game Over screens.
- Settings saved in `settings.json`: sound, car color and difficulty.
- Visual assets for the player car, traffic cars, coins, power-ups, hazards and road.
- Sound effects for menu selection, coins, collisions, power-ups and game over.

Assets:
- Images are in `assets/images/`: `player_car.bmp`, `traffic_car.bmp`, `coin.bmp`, `nitro.bmp`, `shield.bmp`, `repair.bmp`, `barrier.bmp`, `oil.bmp`, `bump.bmp`, `road.bmp`.
- Sounds are in `assets/sounds/`: `menu.wav`, `coin.wav`, `collision.wav`, `powerup.wav`, `gameover.wav`.
- `assets.py` loads all files through paths relative to the TSIS3 folder.
- Fallback: if an image is missing, the game draws the old rectangle version with `pygame.draw`. If a sound is missing or audio cannot initialize, only that sound is skipped.
- Sound is controlled by the Settings screen and saved in `settings.json`.

Run:
```bash
pip install -r requirements.txt
python main.py
```

You can replace placeholder `.bmp` and `.wav` files with your own assets using the same filenames.
