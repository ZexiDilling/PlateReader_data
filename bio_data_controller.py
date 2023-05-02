


def bio_data(config, folder, plate_layout, bio_plate_report_setup, analysis, bio_sample_dict, save_location,
             write_to_excel=True):
    """
    Handles the Bio data.

    :param config: The config handler, with all the default information in the config file.
    :type config: configparser.ConfigParser
    :param folder: The folder where the raw data is located
    :type folder: str
    :param plate_layout: The layout for the plate with values for each well, what state they are in
    :type plate_layout: dict
    :param bio_plate_report_setup: The setup for what is included in the report
    :type bio_plate_report_setup: dict
    :param bio_sample_dict: None or a dict of sample ide, per plate analysed
    :type bio_sample_dict: dict
    :param analysis: The analysis method
    :type analysis: str
    :param save_location: where to save all the excel files
    :type save_location: str
    :return: All the data for the plates raw data, and their calculations
    :rtype: dict
    """
    # needs to reformat plate-layout to use well ID instead of numbers...
    bioa = BIOAnalyser(config, bio_plate_report_setup)
    file_list = get_file_list(folder)   # ToDo use PATH!!!!
    all_plates_data = {}
    for files in file_list:
        if isfile(files) and files.endswith(".txt"):
            files = txt_to_xlsx(files)
        if isfile(files) and files.endswith(".xlsx"):
            all_data, well_row_col, well_type, barcode, date = original_data_dict(files, plate_layout)
            if not all_data:
                return False

            all_plates_data[barcode] = bioa.bio_data_controller(files, plate_layout, all_data, well_row_col, well_type,
                                                                analysis, write_to_excel, bio_sample_dict,
                                                                save_location)
        else:
            print(f"{files} is not the right formate")
    return True, all_plates_data, date


def bio_full_report(analyse_method, all_plate_data, final_report_setup, output_folder, final_report_name):
    """
    Writes the final report for the bio data

    :param analyse_method: The analysed method used for the data
    :type analyse_method: str
    :param all_plate_data: All the data for all the plates, raw and calculations
    :type all_plate_data: dict
    :param final_report_setup: The settings for the report
    :type final_report_name: dict
    :param output_folder: The output folder, where the final report ends up
    :type output_folder: str
    :param final_report_name: The name for the report
    :type final_report_name: str
    :return: A excel report file with all the data
    """

    output_file = f"{output_folder}/{final_report_name}.xlsx"
    bio_final_report_controller(analyse_method, all_plate_data, output_file, final_report_setup)



def original_data_dict(file, plate_layout):
    """
    The original data from the plate reader, loaded in from the excel file

    :param file: the excel file, with the platereaders data
    :type file: str
    :param plate_layout: The platelayout to tell witch cell/well is in witch state (sample, blank, empty....)
    :type plate_layout: dict
    :return:
        - all_data: all_data: A dict over the original data, and what each cell/well is
        - well_col_row: a dict with a list of values for rows and for columns,
        - well_type: a dict over the type/state of each well/cell
        - barcode: The barcode for the plate
    :rtype:
        - dict
        - dict
        - dict
        - str
    """

    # Get well column, row, and type data
    well_col_row, well_type = well_row_col_type(plate_layout)
    try:
        wb = load_workbook(file)
    except InvalidFileException:
        return
    sheet = wb.sheetnames[0]
    ws = wb[sheet]

    # Initialize variables for plate type detection
    plate_type_384 = False
    plate_type_1536 = False

    # Initialize dictionary for all data
    all_data = {"plates": {}, "calculations": {}}
    n_rows = len(well_col_row["well_row"])

    # Iterate through each row in the sheet
    for row_index, row in enumerate(ws.values):     #Todo Change this to be a dict, as there can be multiple readings per data. There can be multiple plate readings inside an excel sheet
        for index_row, value in enumerate(row):

            # Get the date
            if value == "Date:":
                date = row[4]

            # Get the barcode
            if value == "Name" and row[1]:
                barcode = row[1]

            # Get the number of rows to skip
            if value == "<>":
                skipped_rows = row_index

            # Check if the plate is 384-well
            if value == "I":
                plate_type_384 = True

            # Check if the plate is 1536-well
            if value == "AA":
                plate_type_1536 = True

    # Load the data into a pandas dataframe, skipping the rows that were specified earlier
    df_plate = pd.read_excel(file, sheet_name=sheet, skiprows=skipped_rows, nrows=n_rows)

    # Convert the dataframe to a dictionary
    df_plate_dict = df_plate.to_dict()

    # Check the size of the plate and display an error message if the size does not match the expected size
    expected_plate_sizes = {
        8: not plate_type_384 or plate_type_1536,
        16: plate_type_384,
        32: plate_type_1536
    }

    if n_rows not in expected_plate_sizes or not expected_plate_sizes[n_rows]:
        PySimpleGUI.PopupError(f"Wrong plate size, data is not {expected_plate_sizes[n_rows]}-wells")
        return None, None, None

    # temp_reading_dict stores the data from the dataframe in a dictionary format
    temp_reading_dict = {}
    for counter, heading in enumerate(df_plate_dict):
        for index, values in enumerate(df_plate_dict[heading]):
            temp_reading_dict[f"{well_col_row['well_row'][index]}{counter}"] = df_plate_dict[heading][values]

    # The code below stores the data in the all_data dictionary
    all_data["plates"]["original"] = {}
    all_data["plates"]["original"]["wells"] = {}
    for state in well_type:
        for well in well_type[state]:
            try:
                all_data["plates"]["original"]["wells"][well] = temp_reading_dict[well]

            # Incase blanked wells are skipped for the reading
            except KeyError:
                all_data["plates"]["original"]["wells"][well] = 1
    try:
        barcode
    except UnboundLocalError:
        barcode = file.split("/")[-1]

    try:
        date
    except UnboundLocalError:
        date = datetime.today()

    return all_data, well_col_row, well_type, barcode, date
