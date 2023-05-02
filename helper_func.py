import os


def config_writer(config, heading, data_dict):
    """
    The code is a function for writing data to a configuration file using the configparser library.
    The function takes in a config object (the handler for the configuration file), a heading string
    (the section heading in the configuration file), and a data_dict dictionary (the key-value pairs to be written to
    the configuration file). The function iterates through the key-value pairs in the data_dict and sets the values in
    the config object using the config.set method. Finally, the function opens the configuration file for writing,
    writes the config object to the file, and closes the file.
    :param config: The config handler, with all the default information in the config file.
    :type config: configparser.ConfigParser
    :param heading: The heading of the specific configuration
    :type heading: str
    :param data_dict: The data that needs to be added to the dict
    :type data_dict: dict
    :return:
    """

    # Iterate through each key-value pair in the data dictionary
    for data in data_dict:
        # Set the value in the config file for the given heading and data
        config.set(heading, data, data_dict[data])

    # Open the config file for writing
    with open("config.ini", "w") as config_file:
        # Write the config data to the file
        config.write(config_file)


def config_header_to_list(config, header):
    """
    Extracts data from a config section into a list of lists format for table display
    :param config: The config handler
    :type config: configparser.ConfigParser
    :param header: The section of the config to extract data from
    :type header: str
    :return: List of lists containing the key-value pairs from the config section
    :rtype: list
    """
    # Initialize an empty list to store the table data
    table_data = []

    # Iterate through each key-value pair in the config section
    for data in config[header]:
        # Create a temporary list with the key-value pair
        temp_data = [data, config[header][data]]
        # Append the temporary list to the table data list
        table_data.append(temp_data)

    # Return the list of lists with the table data
    return table_data


def clear_file(file, config):
    """
    clears the file for data
    :param config: The config handler, with all the default information in the config file.
    :type config: configparser.ConfigParser
    :param file: The name of the file to create, specified in the "Temp_files" section of the config
    :type file: str
    """
    # Open the specified file in write mode, specified in the "Temp_files" section of the config
    with open(config["Temp_files"][file], "w") as f:
        # Close the file immediately
        f.close()


def write_temp_list_file(temp_file_name, file, config):
    """
    Appends data to a temporary file specified in the config file
    :param config: The config handler, with all the default information in the config file.
    :type config: configparser.ConfigParser
    :param temp_file_name: The name of the temporary file, specified in the "Temp_files" section of the config
    :type temp_file_name: str
    :param file: The data to append to the temporary file
    :type file: str
    """
    # Get the path to the temporary file, specified in the "Temp_files" section of the config
    trans_list_file = config["Temp_files"][temp_file_name]

    # Open the file in append mode
    with open(trans_list_file, "a") as f:
        # Write the data to the file, followed by a comma
        f.write(file)
        f.write(",")


def read_temp_list_file(temp_file_name, config):
    """
    Reads data from a temporary file specified in the config file
    :param config: The config handler, with all the default information in the config file.
    :type config: configparser.ConfigParser
    :param temp_file_name: The name of the temporary file, specified in the "Temp_files" section of the config
    :type temp_file_name: str
    :return: A list of data read from the temporary file
    :rtype: list
    """
    # Get the path to the temporary file, specified in the "Temp_files" section of the config
    trans_list_file = config["Temp_files"][temp_file_name]
    if os.path.isfile(trans_list_file):
        # Open the file in read mode
        with open(trans_list_file, "r") as f:
            # Read the data from the file
            lines = f.read()
            # Remove the trailing comma
            lines = lines.rstrip(",")
            # Split the data into a list of strings, separated by commas
            file_list = lines.split(",")

        return file_list
    else:
        return None

def folder_to_files(folder_path):
    """
    Gets a list of all files in a folder and its subfolders
    :param folder_path: The path to the folder
    :type folder_path: str
    :return: A list of file paths
    :rtype: list
    """
    # Create an empty list to store the file paths
    file_list = []

    # Use the os.walk function to get a list of all the files in the folder and its subfolders
    for root, dirs, files in os.walk(folder_path):
        # Loop through each file in the list of files
        for file in files:
            # Get the full path to the file and add it to the list of file paths
            file_list.append(os.path.join(root, file))

    return file_list

if __name__ == "__main__":
    import configparser
    config = configparser.ConfigParser()
    config.read("config.ini")
    file = "trans_list"
    write_temp_list_file(file, config)
    read_temp_list_file(config)

    # sg.main_get_debug_data()