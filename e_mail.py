import configparser
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time
import smtplib
from email.message import EmailMessage
from os import path
from datetime import date, datetime, timedelta
from pathlib import Path

from helper_func import write_temp_list_file, read_temp_list_file
from bio_data_controller import bio_single_report, bio_full_report


class MyEventHandler(FileSystemEventHandler):
    def __str__(self):
        """This is a standard class for watchdog.
        This is the class that is listening for files being created, moved or deleted.
        ATM the system only react to newly created files"""

    def __init__(self, window, plate_layout, analysis, bio_sample_dict):
        self.config = configparser.ConfigParser()
        self.config.read("config.ini")
        self.window = window
        self.all_plate_data = {}
        self.plate_layout = plate_layout
        self.analysis = analysis
        self.bio_sample_dict = bio_sample_dict
        self.initial_plate = ""

    def on_created(self, event):
        """
        This event is triggered when a new file appears in the target folder
        It checks the file in the event for missing transferees, if there are any, it sends an E-mail.
        :param event: The full event, including the path to the file that have been created
        """

        # checks if path is a directory
        if path.isfile(event.src_path):
            temp_file = event.src_path
            plate_name = temp_file.split("/")[-1].split("\\")[-1].split(".")[0]
            if temp_file.endswith(".txt"):
                sending_mail = True

                current_plate = int(self.window["-PLATE_COUNTER-"].get()) + 1
                if current_plate == 1:
                    self.initial_plate = plate_name
                while sending_mail:
                    # Set timer to sleep while spark is finishing writing data to the files
                    time.sleep(2)
                    _, all_plates_data, excel_file = bio_single_report(self.config, temp_file, plate_name, self.plate_layout, self.analysis, self.bio_sample_dict,
                                      self.all_plate_data)

                    msg_subject = f"Reading for plate {temp_file}"
                    data = None
                    e_mail_type = "single_report"

                    # send an E-mail with information from the trans file
                    mail_setup(msg_subject, data, self.config, e_mail_type, excel_file)
                    sending_mail = False
                    self.window["-PLATE_COUNTER-"].update(value=current_plate)
                    # Check plate amount. If it reach set amount,
                    # it will create a report over all the files and send it.
                    if current_plate == int(self.window["-PLATE_NUMBER-"].get()):
                        output_folder = self.config["Folder"]["out"]
                        current_date = datetime.now()
                        current_date = current_date.strftime("%d_%m_%Y")
                        output_name = f"full_report_for_{self.initial_plate}_to_{plate_name}_on_{current_date}"
                        output_file = f"{output_folder}/{output_name}.xlsx"
                        time.sleep(1)
                        bio_full_report(output_file, self.analysis, all_plates_data)
                        mail_report_sender(output_file, self.window, self.config)
                        self.window["-E_MAIL_REPORT-"].update(value=False)

        else:
            print(event.src_path)
            print(f"{datetime.now()} - folder is created")


    # def on_deleted(self, event):
    #     """
    #     This event is triggered when a file is removed from the folder, either by deletion or moved.
    #     :param event:
    #     :return:
    #     """
    #     print("delet")
    #     print(event)

    # def on_modified(self, event):
    #     """
    #     This event is triggered when a file is modified.
    #     :param event:
    #     :return:
    #     """
    #     print("mod")
    #     print(event)


def _single_reading_body():
    """
    Writes information for an E-mail for a single reading
    :return: A string containing info for the run.
    :rtype: str
    """


    body = f"placeholder_text"

    return body


def _final_report_body():
    """
    Writes the body of the E-mail for the final report, including relevant information
    :return: The body of an E-mail
    :rtype str
    """

    body = \
        f"placeholder text"

    return body


def mail_report_sender(filename, window, config, overview_data=None):
    """
    This function sends the final report of the transfer operation.

    :param filename: The name of the temporary file where all transfer data is stored.
    :type filename: str
    :param window: The GUI window
    :type window: PySimpleGUI.PySimpleGUI.Window
    :param config: The config handler, with all the default information in the config file.
    :type config: configparser.ConfigParser

    :return:
    """

    # sends an E-mail, with the report included
    msg_subject = f"Final report for readings: {date.today()}"
    e_mail_type = "final_report"
    mail_setup(msg_subject, overview_data, config, e_mail_type, filename)
    print(f"{datetime.now()} - sent final report")


def mail_setup(msg_subject, all_data, config, e_mail_type, filename):
    """
    Sends an E-mail to user specified in the config file.
    :param msg_subject: error msg
    :type msg_subject: str
    :param all_data: All the data from the file.
    :type all_data: dict or None
    :param config: The configparser.
    :type config: configparser.ConfigParser
    :param e_mail_type: What kind of E-mail to send.
        "error" - sends an E-mail with all the fail transfers from the echo
        "final_report" - sends an E-mail with an overview of all the transfers, and a report for the complete transfer
    :type e_mail_type: str
    :return:
    """

    # Basic setup for sending.
    # The server - DTU internal server - Pulling from the config file
    # Sender - The E-mail that sends the msg - Pulling from the config file
    # Receivers -  List of people that will get the E-mail. - Pulling from the config file
    # File_data is for attachment
    file_data = None
    msg = EmailMessage()
    dtu_server = config["Email_settings"]["server"]
    sender = config["Email_settings"]["sender"]
    equipment_name = "Spark"
    receiver = []
    for people in config["Email_list"]:
        receiver.append(config["Email_list"][people])

    # Sends different E-mails depending on e-mail type.
    # Error E-mails, is sent if there is an error on Echo transfers
    # Final Report is sent when the full run is done. or if the system crash depending on
    if e_mail_type == "single_report":
        body = _single_reading_body()
    elif e_mail_type == "final_report":
        body = _final_report_body()

    with open(filename, 'rb') as f:
        file_data = f.read()
    subtype = filename.split(".")[-1]
    filename = filename.split("/")[-1]

    # Setting up the e-mail
    msg["Subject"] = f"{msg_subject}"
    msg["from"] = f"{equipment_name} <{sender}>"
    msg["To"] = ", ".join(receiver)
    msg.set_content(body)
    if file_data:
        msg.add_attachment(file_data, maintype="application", subtype=subtype, filename=filename)
    # msg.attach(MIMEText(body))

    # Sending the E-mail.
    server = smtplib.SMTP(dtu_server, port=25)
    server.send_message(msg)
    # server.sendmail(msg["from"], msg["to"], msg.as_string())
    server.quit()
    print(f"{datetime.now()} - send {e_mail_type} E-mail")


def listening_controller(config, run, window, plate_layout, analysis, bio_sample_dict):
    """
    main controller for listening for files.
    :param plate_layout: The layout for the plate with values for each well, what state they are in
    :type plate_layout: dict
    :param bio_sample_dict: None or a dict of sample ide, per plate analysed
    :type bio_sample_dict: dict
    :param analysis: The analysis method, single or multiple of the same sample.
    :type analysis: str
    :param config: The config handler, with all the default information in the config file.
    :type config: configparser.ConfigParser
    :param run: A state to tell if the listening is active or not
    :type run: bool
    :param window: The window where the activation of the listening is.
    :type window: PySimpleGUI.PySimpleGUI.Window
    :return:
    """

    path = config["Folder"]["in"]

    event_handler = MyEventHandler(window, plate_layout, analysis, bio_sample_dict)

    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()

    try:
        while run:
            time.sleep(1)
            if window["-KILL-"].get():
                run = False

    finally:
        observer.stop()
        observer.join()
        print(f"{datetime.now()} - done")


if __name__ == "__main__":

    msg_subject = "testing attachment"
    all_data = {}
    config = configparser.ConfigParser()
    config.read("config.ini")
    e_mail_type = "final_report"

    mail_setup(msg_subject, all_data, config, e_mail_type)