import configparser
from controller import main


def start_up():
    config = configparser.ConfigParser()
    config.read("config.ini")
    main(config)


if __name__ == "__main__":
    start_up()