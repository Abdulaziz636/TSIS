from game import SnakeGame


def print_controls():
    print("TSIS4 Snake controls:")
    print("  Menu: type your player name, press Enter or click Play.")
    print("  Game: arrow keys change direction.")
    print("  Power-ups: speed, slow and shield. Shield removes the obstacle it hits.")
    print("  Settings: click buttons to change color, grid and sound.")


if __name__ == "__main__":
    print_controls()
    SnakeGame().run()
