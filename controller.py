import PySimpleGUI as sg

import threading
from os import path
import time
from datetime import date

from gui import main_layout, popup_email_list_controller, popup_settings_controller
from helper_func import config_writer, config_header_to_list, clear_file, plate_dict_reader
from e_mail import listening_controller, mail_report_sender


def main(config):
    """
    The main GUI setup and control for the whole program
    The while loop, is listening for button presses (Events) and will call different functions depending on
    what have been pushed.
    :param config: The config handler, with all the default information in the config file.
    :type config: configparser.ConfigParser
    :return:
    """
    plate_file = config["Temp_files"]["plate_layouts"]
    plate_list, archive_plates_dict = plate_dict_reader(plate_file)

    window = main_layout(plate_list)

    while True:

        event, values = window.read()
        if event == sg.WIN_CLOSED or event == "-CLOSE-":
            break

        if event == "-LISTEN-":
            window["-KILL-"].update(value=False)
            window["-PLATE_COUNTER-"].update(value=0)
            window["-E_MAIL_REPORT-"].update(value=True)
            window["-TEXT_FIELD-"].update(value="")

            if not window["-PLATE_NUMBER-"].get():
                window["-PLATE_NUMBER-"].update(value=0)

            # Clears out the temp_list file. to make sure only new data is in the file.
            clear_file("trans_list", config)

            if not path.exists(config["Folder"]["in"]):
                folder_in = sg.PopupGetFolder("Please select the folder you would like to listen to")
                config_heading = "Folder"
                sub_heading = "in"
                data_dict = {sub_heading: folder_in}
                config_writer(config, config_heading, data_dict)

            if not path.exists(config["Folder"]["out"]):
                folder_out = sg.PopupGetFolder("Please select the folder where your reports ends up")
                config_heading = "Folder"
                sub_heading = "out"
                data_dict = {sub_heading: folder_out}
                config_writer(config, config_heading, data_dict)

            plate_layout = archive_plates_dict[values["-BIO_PLATE_LAYOUT-"]]
            analysis = values["-ANALYSIS_METHOD-"]
            bio_sample_dict = None

            threading.Thread(target=listening_controller, args=(config, True, window, plate_layout, analysis,
                                                                bio_sample_dict,), daemon=True).start()
            threading.Thread(target=progressbar, args=(config, True, window,), daemon=True).start()

        if event == "-KILL_BUTTON-":
            window["-KILL-"].update(value=True)

        if event == "-SHOW_PLATE_LIST-":
            window["-TEXT_FIELD-"].update(visible=values["-SHOW_PLATE_LIST-"])

        if event == "reset":
            window["-PLATE_COUNTER-"].update(value=0)
            window["-TIME_TEXT-"].update(value="")
            window["-INIT_TIME_TEXT-"].update(value="")
            window["-ADD_TRANSFER_REPORT_TAB-"].update(value=False)
            window["-TEXT_FIELD-"].update(value="")
            window["-E_MAIL_REPORT-"].update(value=False)
            window["-SEND_E_MAIL-"].update(value=False)

        if event == "In":
            config_heading = "Folder"
            sub_heading = "in"
            new_folder = sg.PopupGetFolder(f"Current folder: {config[config_heading][sub_heading]}", "Data Folder")
            if new_folder:
                data_dict = {sub_heading: new_folder}
                config_writer(config, config_heading, data_dict)

        if event == "Out":
            config_heading = "Folder"
            sub_heading = "out"
            new_folder = sg.PopupGetFolder(f"Current folder: {config[config_heading][sub_heading]}", "Data Folder")
            if new_folder:
                data_dict = {sub_heading: new_folder}
                config_writer(config, config_heading, data_dict)

        if event == "E-mail":
            config_header = "Email_list"
            table_data = config_header_to_list(config, config_header)

            headings = ["Name", "E-mail"]

            popup_email_list_controller(table_data, config, headings)

        if event == "Info":
            with open("README.txt") as file:
                info = file.read()

            sg.Popup(info)

        if event == "About":
            sg.Popup("Find data, send data. Programmed By Charlie for DTU SCore")

        if event == "Setup":
            popup_settings_controller(config)


def progressbar(config, run, window):
    """
    The progress bar, that shows the program working
    :param run: If the bar needs to be running or not
    :type run: bool
    :param window: Where the bar is displayed
    :type window: PySimpleGUI.PySimpleGUI.Window
    :return:
    """
    min_timer = 0
    max_timer = 100
    counter = 0

    # Timer for when too sent a report. if there are no files created for the period of time, a report will be sent.
    # set one for runs where there is not set a plate counter, or if the platform fails.
    # set one for if plate counter is used. To avoid sending multiple report files, one for each source plate
    time_limit_no_plate_counter = float(config["Time"]["time_limit_no_plate_counter"])
    time_limit_plate_counter = float(config["Time"]["time_limit_plate_counter"])

    temp_file_name = "trans_list"
    total_plates = int(window["-PLATE_NUMBER-"].get())
    procent_splitter = [
        round(total_plates / 100 * 10),
        round(total_plates / 100 * 25),
        round(total_plates / 100 * 50),
        round(total_plates / 100 * 75)
    ]
    time_estimates_send = []

    while run:
        current_time = time.time()
        if counter == min_timer:
            runner = "pos"
        elif counter == max_timer:
            runner = "neg"
            # This is a setup to send a E-mail with a full report over all failed wells.
            # It is set up for time.

        if runner == "pos":
            counter += 10
        elif runner == "neg":
            counter -= 10

        window["-BAR-"].update(counter)

        time.sleep(0.1)
        if window["-KILL-"].get():
            run = False


if __name__ == "__main__":
    import configparser
    config = configparser.ConfigParser()
    config.read("config.ini")
    main(config)
