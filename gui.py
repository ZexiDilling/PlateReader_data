import PySimpleGUI as sg
import configparser

from helper_func import config_writer


def _menu():
    """
    Top menu of the gui
    :return: The top menu
    :rtype: list
    """
    menu_top_def = [
        # ["&File", ["&Open    Ctrl-O", "&Save    Ctrl-S", "---", '&Properties', "&Exit", ]],
        ["&Listening", ["Folder", ["In", "Out", ], "E-mail", "reset"], ],
        ["&Help", ["Info", "About"]],
        ["Reports", ["Transfer", "Setup"]] #todo make these work
    ]
    layout = [[sg.Menu(menu_top_def)]]
    return layout


def _gui_main_layout():
    """
    The main layout for the gui
    :return: The main layout for the gui
    :rtype: list
    """
    tool_tip_plate_number = "This is the amount of Destination plates for the transfer"

    main = sg.Frame("Listening", [[
        sg.Column([
            [sg.ProgressBar(100, key="-BAR-", size=(25, 5), expand_x=True), sg.Checkbox("KILL", visible=False, key="-KILL-")],
            [sg.Button("Listen", key="-LISTEN-", expand_x=True,
                       tooltip="starts the program that listen to the folder for files"),
             sg.Button("Kill", key="-KILL_BUTTON-", expand_x=True,
                       tooltip="stops the program that listen to the folder for files"),
             sg.Button("Close", key="-CLOSE-", expand_x=True,
                       tooltip="Closes the whole program")],
            [sg.Text("Plates:"),
             sg.Input("", key="-PLATE_NUMBER-", size=3,
                      tooltip=tool_tip_plate_number),
             sg.Text("Counter", key="-PLATE_COUNTER-", visible=True, tooltip="Plate analysed"),
             sg.Checkbox("Show Plate", key="-SHOW_PLATE_LIST-", enable_events=True,
                         tooltip="Will show a list of all the plates that have been transferred so far")],
            [sg.Checkbox("Transfer", key="-ADD_TRANSFER_REPORT_TAB-", visible=False),
             sg.Text(key="-TIME_TEXT-", visible=False), sg.Text(key="-INIT_TIME_TEXT-", visible=False)],

        ]),
        sg.VerticalSeparator(),
        sg.Column([
            [sg.Multiline(key="-TEXT_FIELD-", visible=False)],
            [sg.Checkbox("E-Mail Report", visible=False, key="-E_MAIL_REPORT-"),
             sg.Checkbox("Send E-mail", visible=False, key="-SEND_E_MAIL-")]
        ])
    ]])

    layout = [[main]]

    return layout


def main_layout():
    """
    The main setup for the layout for the gui
    :return: The setup and layout for the gui
    :rtype: sg.Window
    """

    # sg.theme()
    top_menu = _menu()

    layout = [[
        top_menu,
        _gui_main_layout()
    ]]

    return sg.Window("Echo Data", layout, finalize=True, resizable=True)


def _gui_popup_email_list(data, headings):
    """
    Layout for a popup menu
    :param data: The data that needs to be displayed
    :type data: list
    :param headings: The headings of the table where the data is displayed
    :type headings: list
    :return: The popup window
    :rtype: sg.Window
    """
    # headings = ["Source Plate", "Source Well", "Volume Needed", "Volume left", "Counters", "New Well"]

    col = sg.Frame("Table", [[
        sg.Column([
            [sg.Table(headings=headings, values=data, key="-TABLE-")],
            [sg.Button("Save", key="-TABLE_SAVE-"), sg.Button("Add", key="-TABLE_ADD-"),
             sg.Button("close", key="-TABLE_CLOSE-")]
        ])
    ]])

    layout = [[col]]

    return sg.Window("Table", layout, finalize=True, resizable=True)


def popup_email_list_controller(data, config, headings):
    """
    A popup menu
    :param data: The data that needs to be displayed
    :type data: list
    :param config: The config handler, with all the default information in the config file.
    :type config: configparser.ConfigParser
    :param headings: The headings of the table where the data is displayed
    :type headings: list
    :return:
    """
    window = _gui_popup_email_list(data, headings)

    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED or event == "-TABLE_CLOSE-":
            window.close()
            break

        if event == "-TABLE_SAVE-":
            config_data = {}
            table_data = window["-TABLE-"].get()
            for list in table_data:
                for data_index, data in enumerate(list):
                    if data_index == 0:
                        temp_name = data
                    if data_index == 1:
                        temp_email = data
                config_data[temp_name] = temp_email

            heading = "Email_list"
            config_writer(config, heading, config_data)

        if event == "-TABLE_ADD-":
            name = sg.PopupGetText("Name")
            email = sg.PopupGetText("Email")
            if name and email:
                table_data = window["-TABLE-"].get()
                table_data.append([name, email])
                window["-TABLE-"].update(values=table_data)


def _gui_popup_settings(config):

    config.read("config.ini")

    col_1 = sg.Column([
        [sg.Text("Time limit for no plate counter:"),
         sg.Input(default_text=config["Time"]["time_limit_no_plate_counter"],
                  key="-SETTINGS_TIME_LIMIT_NO_PLATE_COUNTER-", size=5)],
        [sg.Text("Time limit for plate counter:"),
         sg.Input(default_text=config["Time"]["time_limit_plate_counter"],
                  key="-SETTINGS_TIME_LIMIT_PLATE_COUNTER-", size=5)],
        [sg.Button("Save", expand_x=True, key="-SETTINGS_SAVE-"),
         sg.Button("Close", expand_x=True, key="-SETTINGS_CLOSE-")]
    ])

    layout = [[sg.Frame("Settings", [[col_1]])]]

    return sg.Window("Table", layout, finalize=True, resizable=True)


def popup_settings_controller(config):
    window = _gui_popup_settings(config)

    while True:
        event, values = window.read()
        if event == "-SETTINGS_CLOSE-":
            break
        elif event == "-SETTINGS_SAVE-":
            try:
                time_limit_no_plate_counter = float(values["-SETTINGS_TIME_LIMIT_NO_PLATE_COUNTER-"])
                time_limit_plate_counter = float(values["-SETTINGS_TIME_LIMIT_PLATE_COUNTER-"])
            except ValueError:
                sg.popup("Please enter a valid float number")
                continue

            config.set("Time", "time_limit_no_plate_counter", str(time_limit_no_plate_counter))
            config.set("Time", "time_limit_plate_counter", str(time_limit_plate_counter))

            with open("config.ini", "w") as configfile:
                config.write(configfile)
            break

    window.close()
