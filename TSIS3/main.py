from racer import RacerApp


def print_controls():
    print("TSIS3 Racer controls:")
    print("  Menu: type your driver name, press Enter or click Start Run.")
    print("  Driving: Left / Right arrows move the car.")
    print("  Settings: click buttons to change sound, color and difficulty.")
    print("  Power-ups: nitro speeds up, shield blocks one crash, repair removes an obstacle.")


if __name__ == "__main__":
    print_controls()
    RacerApp().run()
