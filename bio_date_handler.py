import configparser
from statistics import mean, stdev, pstdev, pvariance, variance

from bio_data_functions import *


class BIOAnalyser:
    """
    :param config: the config file for the program
    :type config: configparser.ConfigParser
    :param bio_plate_report_setup: dict over what state wells should be in, to be printed on the report sheet.
    :type bio_plate_report_setup: dict
    """
    def __init__(self, config, bio_plate_report_setup):
        self.config = config

        def st_dev_p(avg, stdev):
            return (stdev * 100) / avg

        self.cal_stuff = {"avg": mean, "stdev": stdev, "pstdev": pstdev, "pvariance": pvariance, "variance": variance,
                          "st_dev_%": st_dev_p}

        self.well_states_report_method = bio_plate_report_setup["well_states_report_method"]
        self.well_states_report = bio_plate_report_setup["well_states_report"]
        self.plate_report_calc_dict = bio_plate_report_setup["calc_dict"]
        self.plate_calc_dict = bio_plate_report_setup["plate_calc_dict"]
        self.plate_analysis = bio_plate_report_setup["plate_analysis_dict"]
        self.z_prime_calc = bio_plate_report_setup["z_prime_calc"]
        self.heatmap_colours = bio_plate_report_setup["heatmap_colours"]
        self.pora_threshold = bio_plate_report_setup["pora_threshold"]

    def __str__(self):
        """
        A class that handles the data from a Tecan platereader, where the data is in an excel formate.
        It does calculations and analysis of the data, and makes a final report based on everything
        :return: the analysed data
        """

    def _plate_well_dict(self):
        """
        Makes a dict over the state of each well (empty, sample, blank...)

        :return: pw_dict: A dict over the wells and what state they are in.
        :rtype: dict
        """
        # Store the plate information in a dictionary, where each well is key-value pair.
        pw_dict = {}
        for layout in self.plate:
            for counter in self.plate[layout]:
                # Check if the well information exists, skip it if it doesn't
                try:
                    pw_dict[self.plate[layout][counter]["well_id"]] = self.plate[layout][counter]["state"]
                except TypeError:
                    pass

        return pw_dict

    def _data_converter(self, all_data, well_type):
        """
        convert raw data in the analysed data

        :param all_data: A dict over all plate date. all the analysed data will be added to this dict
        :type all_data: dict
        :param well_type: A dict over what state/type each well/cell is in.
        :type well_type: dict
        :return:
            - all_data: A dict over all plate date. all the analysed data will be added to this dict
            - pw_dict: A dict over the wells and what state they are in.
        :rtype:
            - dict
            - dict
        """

        # Create a dictionary mapping well IDs to their states
        pw_dict = self._plate_well_dict()

        # Iterate through each plate analysis method
        for methode in self.plate_analysis:
            # If the method is marked for use
            if self.plate_analysis[methode]["use"]:
                # Calculate the well data for the specified well type and method
                self._well_calculations(well_type, all_data, methode)

        # Create an empty dictionary to store other calculations
        try:
            all_data["calculations"]["other"]
        except KeyError:
            all_data["calculations"]["other"] = {}

        # If z-prime calculation is set to True
        if self.z_prime_calc:
            # Calculate the z-prime value using the normalised data
            all_data["calculations"]["other"]["z_prime"] = z_prime_calculator(all_data, "normalised")

        # Return the final data and the well-ID to state mapping
        return all_data, pw_dict

    def _well_calculations(self, well_type, all_data, methode):
        """
        Calculate each analyse methode for each well

        :param well_type: A dict for each state (empty, sample, blank...) with a list of the wells in that state
        :type well_type: dict
        :param all_data: A dict over all plate date. all the analysed data will be added to this dict
        :type all_data: dict
        :param methode: what analyse method is being used
        :return: The calculations of avg and stdev added to all_data
        """

        if methode != "original":
            # Initialize the data structure for the current analysis method
            all_data["plates"][methode] = {}
            all_data["plates"][methode]["wells"] = {}

        # Apply the analysis method for each well and store the result
        for state in well_type:
            all_data["plates"][methode][state] = []
            for well in well_type[state]:
                all_data["plates"][methode]["wells"][well] = self.plate_analysis[methode]["methode"](all_data, well)
                all_data["plates"][methode][state].append(well)

        # Initialize the calculations data structure for the current analysis method
        all_data["calculations"][methode] = {}

        for state in well_type:
            all_data["calculations"][methode][state] = {}
            for calc in self.cal_stuff:
                if calc != "st_dev_%":
                    # if self.plate_calc_dict[methode][calc]:
                    try:
                        all_data["calculations"][methode][state][calc] = self.cal_stuff[calc](
                            [all_data["plates"][methode]["wells"][well] for well in all_data["plates"][methode][state]])
                    except ValueError:
                        all_data["calculations"][methode][state][calc] = None
                else:
                    try:
                        all_data["calculations"][methode][state][calc] = self.cal_stuff[calc](
                            all_data["calculations"][methode][state]["avg"],
                            all_data["calculations"][methode][state]["stdev"]
                        )
                    except (ValueError, ZeroDivisionError):
                        all_data["calculations"][methode][state][calc] = None

        # calc S/B
        try:
            max_avg = all_data["calculations"][methode]["max"]["avg"]
            min_avg = all_data["calculations"][methode]["minimum"]["avg"]
            s_b = max_avg/min_avg
            all_data["calculations"][methode]["other"] = {"S/B": s_b}

        except (KeyError, ZeroDivisionError):
            pass

    def _cal_info(self, ws, init_col, counter_row, temp_dict, methode):
        """
        Writes in the calculation information.

        :param ws: The worksheet for the excel filere where the data is added
        :type ws: openpyxl.worksheet.worksheet.Worksheet
        :param init_col: column to writing to
        :type init_col: int
        :param counter_row: a counter for what row to write to
        :type counter_row: int
        :param temp_dict: the dict with the data for each well
        :type temp_dict: dict
        :param methode: the analysed method
        :type methode: str
        :return: counter_row: the next row to write on.
        :rtype: int
        """

        temp_row = counter_row
        # Loop through states in the current method
        for state in temp_dict["plates"][methode]:
            temp_col = init_col
            # Check if state calculation is required for the current method
            if state != "wells" and self.plate_calc_dict[methode]["state"][state]:
                # Loop through calculations for the current state

                for calc in temp_dict["calculations"][methode][state]:
                    if self.plate_calc_dict[methode][calc]:

                        # Write the calculation name in the first row of each calculation type
                        if counter_row == temp_row:
                            ws[ex_cell(counter_row, temp_col + 1)] = calc
                            ws[ex_cell(counter_row, temp_col + 1)].font = Font(b=True)
                        # Write the state name in the first column of each state type
                        if temp_col == init_col:
                            # Writes the state
                            ws[ex_cell(counter_row + 1, temp_col)] = state
                            ws[ex_cell(counter_row + 1, temp_col)].font = Font(b=True)

                            # Colour the original data calculations, to show witch wells are what.
                            if methode == "original":
                                temp_colour = self.config["plate_colouring"][state]
                                temp_colour = temp_colour.replace("#", "")
                                ws[ex_cell(counter_row + 1, temp_col)].fill = PatternFill("solid", fgColor=temp_colour)

                        # Write the calculation result in the corresponding cell
                        ws[ex_cell(counter_row + 1, temp_col + 1)] = temp_dict["calculations"][methode][state][calc]
                        temp_col += 1
                counter_row += 1
        if methode == "original":
            ws[ex_cell(temp_row, temp_col + 1)] = "S/B:"
            ws[ex_cell(temp_row, temp_col + 1)].font = Font(b=True)
            try:
                ws[ex_cell(temp_row, temp_col + 2)] = temp_dict["calculations"][methode]["other"]["S/B"]
            except KeyError:
                ws[ex_cell(temp_row, temp_col + 2)] = "could not calculate"
        return counter_row

    def _write_plate(self, ws, counter_row, temp_dict, methode, well_row_col, pw_dict):
        """
        Writes the data for each analyse into the excel file including the calculations

        :param ws: The worksheet for the excel filere where the data is added
        :type ws: openpyxl.worksheet.worksheet.Worksheet
        :param counter_row: What row to write to
        :type counter_row: int
        :param temp_dict: The dict for the specific analysed method
        :type temp_dict: dict
        :param methode: What analysed method are being looked at
        :type methode: str
        :param well_row_col: All the headlines for each row and column
        :type well_row_col: dict
        :param pw_dict: a dict for each well and it's state (empty, sample, blank...)
        :type pw_dict:dict
        :return: counter_row: the next row to write on.
        :rtype: int
        """
        indent_col = 3
        indent_row = 3
        initial_row = counter_row + indent_row
        init_col = indent_col
        translate_wells_to_cells = {}
        counter_row += indent_row

        for index_row, row in enumerate(well_row_col["well_row"]):

            # sets the headline and colour for the headline for row
            ws.cell(column=-1 + indent_col, row=counter_row, value=row).fill = \
                PatternFill("solid", fgColor="DDDDDD")
            for index_col, col in enumerate(well_row_col["well_col"]):
                if index_row == 0:
                    # Merge cell above tables, and writes the name of the method used for the plate
                    # ws.merged_cells(start_row=counter_row - 2, start_column=indent_col - 1,
                    #                 end_row=counter_row - 2, end_column=indent_col + 1)

                    # Finds the right headline for the excel sheet
                    # Finds the headline in the config file, for the method
                    temp_name = self.config["bio_method_headline"][methode]
                    ws.cell(column=indent_col - 1, row=counter_row - 2, value=temp_name).font = Font(b=True)

                    # sets the headline and colour for the headline for column
                    ws.cell(column=index_col + indent_col, row=counter_row - 1, value=int(col)).fill = \
                        PatternFill("solid", fgColor="DDDDDD")

                temp_well = f"{row}{col}"
                temp_cell = ex_cell(counter_row, index_col + indent_col)
                translate_wells_to_cells[temp_well] = temp_cell
                # Writes the data in for each well. ignore wells witch state == empty  - - - - -
                #
                #ToDo ADD TO SETTINGS!!!
                #
                if temp_well not in temp_dict["plates"][methode]["empty"]:
                    ws.cell(column=index_col + indent_col, row=counter_row,
                            value=temp_dict["plates"][methode]["wells"][temp_well])
            counter_row += 1
        free_col = len(well_row_col["well_col"]) + indent_col

        # Writes the info for the calculation for each method

        if self.plate_calc_dict[methode]["use"]:
            counter_row = self._cal_info(ws, init_col, counter_row, temp_dict, methode)

        # colour wells depending on what state the wells are (sample, blank, min, max...) and add a reading guide.
        if self.plate_analysis[methode]["state_map"]:
            state_mapping(self.config, ws, translate_wells_to_cells, self.plate, initial_row, free_col, temp_dict,
                          methode)

        # colour in the heat map, if sets to active. Can set for each method
        if self.plate_analysis[methode]["heatmap"]:
            heatmap(self.config, ws, pw_dict, translate_wells_to_cells, self.heatmap_colours)

        if self.plate_analysis[methode]["hit_map"]:
            hit_mapping(ws, temp_dict, self.pora_threshold, methode, translate_wells_to_cells, free_col, initial_row)

        counter_row += 1
        return counter_row

    def cal_writer(self, ws, all_data, initial_row):
        """
        Writes all the calculations to its own sheet for an overview.

        :param ws: The worksheet for the excel files where the data is added
        :type ws: openpyxl.worksheet.worksheet.Worksheet
        :param all_data: A dict over all plate date. all the analysed data will be added to this dict
        :type all_data: dict
        :param initial_row: The first row to write data to.
        :type initial_row: int
        :return: All the calculations writen in the worksheet called: report
        """
        indent_col = 2
        free_col = indent_col
        row_counter = initial_row
        for plate_analysed in all_data["calculations"]:
            if row_counter != initial_row:
                row_counter += 2

            temp_row_counter = row_counter
            calc_used = []

            if self.plate_report_calc_dict[plate_analysed]["use"]:
                ws.cell(column=-1 + indent_col, row=row_counter, value=plate_analysed).font = Font(b=True)
                initial_row = row_counter
                init_col = indent_col
                for state in all_data["calculations"][plate_analysed]:
                    if state != "other":
                        if plate_analysed != "other":
                            ws.cell(column=init_col + 1, row=initial_row, value=state).font = Font(b=True)

                            for calc_index, calc in enumerate(all_data["calculations"][plate_analysed][state]):

                                if self.plate_report_calc_dict[plate_analysed][calc]:
                                    if calc not in calc_used:
                                        if calc != "S/B":
                                            ws.cell(column=init_col, row=temp_row_counter + 1, value=calc).font = Font(b=True)
                                            temp_row = temp_row_counter + 2
                                            temp_col = init_col
                                        else:
                                            ws.cell(column=temp_col, row=temp_row, value=calc).font = Font(b=True)
                                            ws.cell(column=temp_col + 1, row=temp_row,
                                                    value=all_data["calculations"][plate_analysed][state][calc])
                                            continue
                                        calc_used.append(calc)

                                    ws.cell(column=init_col + 1, row=temp_row_counter + 1,
                                            value=all_data["calculations"][plate_analysed][state][calc])
                                    temp_row_counter += 1
                    # Writes other calculations that are for not calculated on a specific method,
                    # atm, that is only z-prime!
                        else:

                            if self.plate_report_calc_dict[plate_analysed]["calc"]["z_prime"]:
                                ws.cell(column=init_col, row=initial_row, value=state).font = Font(b=True)
                                ws.cell(column=init_col + 1, row=temp_row_counter,
                                        value=all_data["calculations"][plate_analysed][state])
                                ws.cell(column=init_col, row=temp_row_counter + 1,
                                        value="calculated on normalized data")

                    init_col += 1
                    temp_row_counter = initial_row
                    row_counter += 1
            row_counter += 2
            if free_col < init_col:
                free_col = init_col

        free_col += 1
        return free_col

    def _well_writer(self, ws, all_data, initial_row, free_col, plate_name, bio_sample_dict):
        """
        Writes Well data from the different analysis method into the report sheet on the excel ark

        # :param wb: the excel ark / workbook
        # :type wb: openpyxl.workbook.workbook.Workbook
        :param ws: The worksheet for the excel filere where the data is added
        :type ws: openpyxl.worksheet.worksheet.Worksheet
        :param all_data: A dict over all plate date. all the analysed data will be added to this dict
        :type all_data: dict
        :param initial_row: The first row to write data to.
        :type initial_row: int
        :param plate_name: Name of the plate
        type plate_name: str
        :param bio_sample_dict: None or a dict of sample ide, per plate analysed
        :type bio_sample_dict: dict
        :return: All the wells writen in a list in the worksheet called: report
        """
        indent_col = free_col
        row_counter = initial_row
        added = False
        freq_data = {}


        for plate_analysed in all_data["plates"]:
            freq_data[plate_analysed] = {"wells": [], "well_values": []}
            if self.well_states_report_method[plate_analysed]:
                # Writes headline for data inserts to see where the data is coming from
                headlines = [plate_analysed, "Well", "value"]
                if bio_sample_dict:
                    headlines.append("Compound ID")
                for headline_counter, headline in enumerate(headlines):
                    ws.cell(column=indent_col + headline_counter, row=row_counter, value=headline).font = Font(b=True)
                row_counter += 1
                for counter in self.plate["well_layout"]:
                    for _ in self.plate["well_layout"][counter]:

                        # looks through the plate layout, finds the state for each well and check if it needs to be added
                        # based on bool-statment from well_states_report
                        if self.well_states_report[self.plate["well_layout"][counter]["state"]] and not added:
                            well = self.plate["well_layout"][counter]["well_id"]
                            well_value = all_data["plates"][plate_analysed]["wells"][well]
                            ws.cell(column=indent_col + 1, row=row_counter, value=well)
                            ws.cell(column=indent_col + 2, row=row_counter,
                                    value=well_value)
                            freq_data[plate_analysed]["wells"].append(well)
                            freq_data[plate_analysed]["well_values"].append(well_value)

                            added = True
                            row_counter += 1
                    added = False
                if not bio_sample_dict:
                    indent_col += 4
                else:
                    indent_col += 5
                row_counter = initial_row
        free_col = indent_col
        return freq_data, free_col

    def _report_writer_controller(self, wb, all_data, plate_name, bio_sample_dict):
        """
        pass the data into different modules to write data in to an excel ark

        :param wb: the excel ark / workbook
        :type wb: openpyxl.workbook.workbook.Workbook
        :param all_data: A dict over all plate date. all the analysed data will be added to this dict
        :type all_data: dict
        :param plate_name: Name of the plate
        type plate_name: str
        :param bio_sample_dict: None or a dict of sample ide, per plate analysed
        :type bio_sample_dict: dict
        :return: Create a new sheet in the workbook, called Report, and writes in wells and calculations depending on
            the analysis.
        """

        initial_row = 2

        try:
            ws_report = wb["Report"]
        except KeyError:
            ws_report = wb.create_sheet("Report")
        else:
            wb.remove_sheet(ws_report)
            ws_report = wb.create_sheet("Report")

        free_col = self.cal_writer(ws_report, all_data, initial_row)
        freq_data, free_col = self._well_writer(ws_report, all_data, initial_row, free_col, plate_name, bio_sample_dict)

        bin_min = 0
        bin_max = 150
        bin_width = 5
        include_outliers = self.config["Settings_bio"].getboolean("outliers")

        for data_set_headline, data_set in enumerate(freq_data):
            if data_set == "pora":
                # get data set out:
                titel = "Frequency"
                temp_data_set = freq_data[data_set]["well_values"]
                free_col, data_location, category_location = \
                    frequency_writer(ws_report, data_set, temp_data_set, free_col, initial_row, bin_min, bin_max, bin_width,
                                           include_outliers)
                bar_chart(ws_report, titel, free_col, initial_row, data_location, category_location)

    def _excel_controller(self, all_data, well_row_col, pw_dict, bio_sample_dict, save_location):
        """
        Controls the flow for the data, to write into an excel file

        :param all_data: A dict over all plate date. all the analysed data will be added to this dict
        :type all_data: dict
        :param well_row_col: All the headlines for each row and column (numbers and letters for the cell values)
        :type well_row_col: dict
        :param pw_dict: dict over each well and what state it is (empty, sample, blank....)
        :type pw_dict: dict
        :param bio_sample_dict: None or a dict of sample ide, per plate analysed
        :type bio_sample_dict: dict
        :param save_location: where to save all the excel files
        :type save_location: str
        :return: A modified excel file, with all the calculations and data added, depending on the analysis method used.
        """
        plate_name = self.ex_file.split("/")[-1].split(".")[0]
        wb = load_workbook(self.ex_file)
        try:
            ws_data = wb["analysis"]
        except KeyError:
            ws_data = wb.create_sheet("analysis")
        else:
            wb.remove_sheet(ws_data)
            ws_data = wb.create_sheet("analysis")

        counter_row = 0
        # sends each plate-analysed-type into the excel file
        for methode in all_data["plates"]:
            counter_row = self._write_plate(ws_data, counter_row, all_data, methode, well_row_col, pw_dict)
        self._report_writer_controller(wb, all_data, plate_name, bio_sample_dict)

        save_file = f"{save_location}/{plate_name}.xlsx"
        wb.save(save_file)

    def bio_data_controller(self, ex_file, plate_layout, all_data, well_row_col, well_type, analysis, write_to_excel,
                            bio_sample_dict, save_location):
        """
        The control modul for the bio analysing

        :param ex_file: The excel file
        :type ex_file: str
        :param plate_layout: The layout for the plate with values for each well, what state they are in
        :type plate_layout: dict
        :param all_data: A dict over all plate date. all the analysed data will be added to this dict
        :type all_data: dict
        :param well_row_col: All the headlines for each row and column (numbers and letters for the cell values)
        :type well_row_col: dict
        :param well_type: A dict over what state/type each well/cell is in.
        :type well_type: dict
        :param analysis: The analysis method
        :type analysis: str
        :param bio_sample_dict: None or a dict of sample ide, per plate analysed
        :type bio_sample_dict: dict
        :param save_location: where to save all the excel files
        :type save_location: str
        :return: A dict over all plate date. all the analysed data will be added to this dict
        :rtype: dict
        """

        self.ex_file = ex_file
        self.plate = plate_layout

        all_data, pw_dict = self._data_converter(all_data, well_type)
        if write_to_excel:
            self._excel_controller(all_data, well_row_col, pw_dict, bio_sample_dict, save_location)

        return all_data


if __name__ == "__main__":
    ex_file = "C:/Users/phch/Desktop/more_data_files/bio-data/alpha_so14.xlsx"
    plate_layout = {'well_layout': {1: {'group': 0, 'well_id': 'A1', 'state': 'empty', 'colour': '#1e0bc8'}, 2: {'group': 0, 'well_id': 'B1', 'state': 'empty', 'colour': '#1e0bc8'}, 3: {'group': 0, 'well_id': 'C1', 'state': 'empty', 'colour': '#1e0bc8'}, 4: {'group': 0, 'well_id': 'D1', 'state': 'empty', 'colour': '#1e0bc8'}, 5: {'group': 0, 'well_id': 'E1', 'state': 'empty', 'colour': '#1e0bc8'}, 6: {'group': 0, 'well_id': 'F1', 'state': 'empty', 'colour': '#1e0bc8'}, 7: {'group': 0, 'well_id': 'G1', 'state': 'empty', 'colour': '#1e0bc8'}, 8: {'group': 0, 'well_id': 'H1', 'state': 'empty', 'colour': '#1e0bc8'}, 9: {'group': 0, 'well_id': 'I1', 'state': 'empty', 'colour': '#1e0bc8'}, 10: {'group': 0, 'well_id': 'J1', 'state': 'empty', 'colour': '#1e0bc8'}, 11: {'group': 0, 'well_id': 'K1', 'state': 'empty', 'colour': '#1e0bc8'}, 12: {'group': 0, 'well_id': 'L1', 'state': 'empty', 'colour': '#1e0bc8'}, 13: {'group': 0, 'well_id': 'M1', 'state': 'empty', 'colour': '#1e0bc8'}, 14: {'group': 0, 'well_id': 'N1', 'state': 'empty', 'colour': '#1e0bc8'}, 15: {'group': 0, 'well_id': 'O1', 'state': 'empty', 'colour': '#1e0bc8'}, 16: {'group': 0, 'well_id': 'P1', 'state': 'empty', 'colour': '#1e0bc8'}, 17: {'group': 0, 'well_id': 'A2', 'state': 'empty', 'colour': '#1e0bc8'}, 18: {'group': 0, 'well_id': 'B2', 'state': 'minimum', 'colour': '#ff8000'}, 19: {'group': 0, 'well_id': 'C2', 'state': 'minimum', 'colour': '#ff8000'}, 20: {'group': 0, 'well_id': 'D2', 'state': 'minimum', 'colour': '#ff8000'}, 21: {'group': 0, 'well_id': 'E2', 'state': 'minimum', 'colour': '#ff8000'}, 22: {'group': 0, 'well_id': 'F2', 'state': 'minimum', 'colour': '#ff8000'}, 23: {'group': 0, 'well_id': 'G2', 'state': 'minimum', 'colour': '#ff8000'}, 24: {'group': 0, 'well_id': 'H2', 'state': 'minimum', 'colour': '#ff8000'}, 25: {'group': 0, 'well_id': 'I2', 'state': 'minimum', 'colour': '#ff8000'}, 26: {'group': 0, 'well_id': 'J2', 'state': 'minimum', 'colour': '#ff8000'}, 27: {'group': 0, 'well_id': 'K2', 'state': 'minimum', 'colour': '#ff8000'}, 28: {'group': 0, 'well_id': 'L2', 'state': 'minimum', 'colour': '#ff8000'}, 29: {'group': 0, 'well_id': 'M2', 'state': 'minimum', 'colour': '#ff8000'}, 30: {'group': 0, 'well_id': 'N2', 'state': 'minimum', 'colour': '#ff8000'}, 31: {'group': 0, 'well_id': 'O2', 'state': 'minimum', 'colour': '#ff8000'}, 32: {'group': 0, 'well_id': 'P2', 'state': 'empty', 'colour': '#1e0bc8'}, 33: {'group': 0, 'well_id': 'A3', 'state': 'empty', 'colour': '#1e0bc8'}, 34: {'group': 0, 'well_id': 'B3', 'state': 'max', 'colour': '#790dc1'}, 35: {'group': 0, 'well_id': 'C3', 'state': 'max', 'colour': '#790dc1'}, 36: {'group': 0, 'well_id': 'D3', 'state': 'max', 'colour': '#790dc1'}, 37: {'group': 0, 'well_id': 'E3', 'state': 'max', 'colour': '#790dc1'}, 38: {'group': 0, 'well_id': 'F3', 'state': 'max', 'colour': '#790dc1'}, 39: {'group': 0, 'well_id': 'G3', 'state': 'max', 'colour': '#790dc1'}, 40: {'group': 0, 'well_id': 'H3', 'state': 'max', 'colour': '#790dc1'}, 41: {'group': 0, 'well_id': 'I3', 'state': 'max', 'colour': '#790dc1'}, 42: {'group': 0, 'well_id': 'J3', 'state': 'max', 'colour': '#790dc1'}, 43: {'group': 0, 'well_id': 'K3', 'state': 'max', 'colour': '#790dc1'}, 44: {'group': 0, 'well_id': 'L3', 'state': 'max', 'colour': '#790dc1'}, 45: {'group': 0, 'well_id': 'M3', 'state': 'max', 'colour': '#790dc1'}, 46: {'group': 0, 'well_id': 'N3', 'state': 'max', 'colour': '#790dc1'}, 47: {'group': 0, 'well_id': 'O3', 'state': 'max', 'colour': '#790dc1'}, 48: {'group': 0, 'well_id': 'P3', 'state': 'empty', 'colour': '#1e0bc8'}, 49: {'group': 0, 'well_id': 'A4', 'state': 'empty', 'colour': '#1e0bc8'}, 50: {'group': 0, 'well_id': 'B4', 'state': 'sample', 'colour': '#ff00ff'}, 51: {'group': 0, 'well_id': 'C4', 'state': 'sample', 'colour': '#ff00ff'}, 52: {'group': 0, 'well_id': 'D4', 'state': 'sample', 'colour': '#ff00ff'}, 53: {'group': 0, 'well_id': 'E4', 'state': 'sample', 'colour': '#ff00ff'}, 54: {'group': 0, 'well_id': 'F4', 'state': 'sample', 'colour': '#ff00ff'}, 55: {'group': 0, 'well_id': 'G4', 'state': 'sample', 'colour': '#ff00ff'}, 56: {'group': 0, 'well_id': 'H4', 'state': 'sample', 'colour': '#ff00ff'}, 57: {'group': 0, 'well_id': 'I4', 'state': 'sample', 'colour': '#ff00ff'}, 58: {'group': 0, 'well_id': 'J4', 'state': 'sample', 'colour': '#ff00ff'}, 59: {'group': 0, 'well_id': 'K4', 'state': 'sample', 'colour': '#ff00ff'}, 60: {'group': 0, 'well_id': 'L4', 'state': 'sample', 'colour': '#ff00ff'}, 61: {'group': 0, 'well_id': 'M4', 'state': 'sample', 'colour': '#ff00ff'}, 62: {'group': 0, 'well_id': 'N4', 'state': 'sample', 'colour': '#ff00ff'}, 63: {'group': 0, 'well_id': 'O4', 'state': 'sample', 'colour': '#ff00ff'}, 64: {'group': 0, 'well_id': 'P4', 'state': 'empty', 'colour': '#1e0bc8'}, 65: {'group': 0, 'well_id': 'A5', 'state': 'empty', 'colour': '#1e0bc8'}, 66: {'group': 0, 'well_id': 'B5', 'state': 'sample', 'colour': '#ff00ff'}, 67: {'group': 0, 'well_id': 'C5', 'state': 'sample', 'colour': '#ff00ff'}, 68: {'group': 0, 'well_id': 'D5', 'state': 'sample', 'colour': '#ff00ff'}, 69: {'group': 0, 'well_id': 'E5', 'state': 'sample', 'colour': '#ff00ff'}, 70: {'group': 0, 'well_id': 'F5', 'state': 'sample', 'colour': '#ff00ff'}, 71: {'group': 0, 'well_id': 'G5', 'state': 'sample', 'colour': '#ff00ff'}, 72: {'group': 0, 'well_id': 'H5', 'state': 'sample', 'colour': '#ff00ff'}, 73: {'group': 0, 'well_id': 'I5', 'state': 'sample', 'colour': '#ff00ff'}, 74: {'group': 0, 'well_id': 'J5', 'state': 'sample', 'colour': '#ff00ff'}, 75: {'group': 0, 'well_id': 'K5', 'state': 'sample', 'colour': '#ff00ff'}, 76: {'group': 0, 'well_id': 'L5', 'state': 'sample', 'colour': '#ff00ff'}, 77: {'group': 0, 'well_id': 'M5', 'state': 'sample', 'colour': '#ff00ff'}, 78: {'group': 0, 'well_id': 'N5', 'state': 'sample', 'colour': '#ff00ff'}, 79: {'group': 0, 'well_id': 'O5', 'state': 'sample', 'colour': '#ff00ff'}, 80: {'group': 0, 'well_id': 'P5', 'state': 'empty', 'colour': '#1e0bc8'}, 81: {'group': 0, 'well_id': 'A6', 'state': 'empty', 'colour': '#1e0bc8'}, 82: {'group': 0, 'well_id': 'B6', 'state': 'sample', 'colour': '#ff00ff'}, 83: {'group': 0, 'well_id': 'C6', 'state': 'sample', 'colour': '#ff00ff'}, 84: {'group': 0, 'well_id': 'D6', 'state': 'sample', 'colour': '#ff00ff'}, 85: {'group': 0, 'well_id': 'E6', 'state': 'sample', 'colour': '#ff00ff'}, 86: {'group': 0, 'well_id': 'F6', 'state': 'sample', 'colour': '#ff00ff'}, 87: {'group': 0, 'well_id': 'G6', 'state': 'sample', 'colour': '#ff00ff'}, 88: {'group': 0, 'well_id': 'H6', 'state': 'sample', 'colour': '#ff00ff'}, 89: {'group': 0, 'well_id': 'I6', 'state': 'sample', 'colour': '#ff00ff'}, 90: {'group': 0, 'well_id': 'J6', 'state': 'sample', 'colour': '#ff00ff'}, 91: {'group': 0, 'well_id': 'K6', 'state': 'sample', 'colour': '#ff00ff'}, 92: {'group': 0, 'well_id': 'L6', 'state': 'sample', 'colour': '#ff00ff'}, 93: {'group': 0, 'well_id': 'M6', 'state': 'sample', 'colour': '#ff00ff'}, 94: {'group': 0, 'well_id': 'N6', 'state': 'sample', 'colour': '#ff00ff'}, 95: {'group': 0, 'well_id': 'O6', 'state': 'sample', 'colour': '#ff00ff'}, 96: {'group': 0, 'well_id': 'P6', 'state': 'empty', 'colour': '#1e0bc8'}, 97: {'group': 0, 'well_id': 'A7', 'state': 'empty', 'colour': '#1e0bc8'}, 98: {'group': 0, 'well_id': 'B7', 'state': 'sample', 'colour': '#ff00ff'}, 99: {'group': 0, 'well_id': 'C7', 'state': 'sample', 'colour': '#ff00ff'}, 100: {'group': 0, 'well_id': 'D7', 'state': 'sample', 'colour': '#ff00ff'}, 101: {'group': 0, 'well_id': 'E7', 'state': 'sample', 'colour': '#ff00ff'}, 102: {'group': 0, 'well_id': 'F7', 'state': 'sample', 'colour': '#ff00ff'}, 103: {'group': 0, 'well_id': 'G7', 'state': 'sample', 'colour': '#ff00ff'}, 104: {'group': 0, 'well_id': 'H7', 'state': 'sample', 'colour': '#ff00ff'}, 105: {'group': 0, 'well_id': 'I7', 'state': 'sample', 'colour': '#ff00ff'}, 106: {'group': 0, 'well_id': 'J7', 'state': 'sample', 'colour': '#ff00ff'}, 107: {'group': 0, 'well_id': 'K7', 'state': 'sample', 'colour': '#ff00ff'}, 108: {'group': 0, 'well_id': 'L7', 'state': 'sample', 'colour': '#ff00ff'}, 109: {'group': 0, 'well_id': 'M7', 'state': 'sample', 'colour': '#ff00ff'}, 110: {'group': 0, 'well_id': 'N7', 'state': 'sample', 'colour': '#ff00ff'}, 111: {'group': 0, 'well_id': 'O7', 'state': 'sample', 'colour': '#ff00ff'}, 112: {'group': 0, 'well_id': 'P7', 'state': 'empty', 'colour': '#1e0bc8'}, 113: {'group': 0, 'well_id': 'A8', 'state': 'empty', 'colour': '#1e0bc8'}, 114: {'group': 0, 'well_id': 'B8', 'state': 'sample', 'colour': '#ff00ff'}, 115: {'group': 0, 'well_id': 'C8', 'state': 'sample', 'colour': '#ff00ff'}, 116: {'group': 0, 'well_id': 'D8', 'state': 'sample', 'colour': '#ff00ff'}, 117: {'group': 0, 'well_id': 'E8', 'state': 'sample', 'colour': '#ff00ff'}, 118: {'group': 0, 'well_id': 'F8', 'state': 'sample', 'colour': '#ff00ff'}, 119: {'group': 0, 'well_id': 'G8', 'state': 'sample', 'colour': '#ff00ff'}, 120: {'group': 0, 'well_id': 'H8', 'state': 'sample', 'colour': '#ff00ff'}, 121: {'group': 0, 'well_id': 'I8', 'state': 'sample', 'colour': '#ff00ff'}, 122: {'group': 0, 'well_id': 'J8', 'state': 'sample', 'colour': '#ff00ff'}, 123: {'group': 0, 'well_id': 'K8', 'state': 'sample', 'colour': '#ff00ff'}, 124: {'group': 0, 'well_id': 'L8', 'state': 'sample', 'colour': '#ff00ff'}, 125: {'group': 0, 'well_id': 'M8', 'state': 'sample', 'colour': '#ff00ff'}, 126: {'group': 0, 'well_id': 'N8', 'state': 'sample', 'colour': '#ff00ff'}, 127: {'group': 0, 'well_id': 'O8', 'state': 'sample', 'colour': '#ff00ff'}, 128: {'group': 0, 'well_id': 'P8', 'state': 'empty', 'colour': '#1e0bc8'}, 129: {'group': 0, 'well_id': 'A9', 'state': 'empty', 'colour': '#1e0bc8'}, 130: {'group': 0, 'well_id': 'B9', 'state': 'sample', 'colour': '#ff00ff'}, 131: {'group': 0, 'well_id': 'C9', 'state': 'sample', 'colour': '#ff00ff'}, 132: {'group': 0, 'well_id': 'D9', 'state': 'sample', 'colour': '#ff00ff'}, 133: {'group': 0, 'well_id': 'E9', 'state': 'sample', 'colour': '#ff00ff'}, 134: {'group': 0, 'well_id': 'F9', 'state': 'sample', 'colour': '#ff00ff'}, 135: {'group': 0, 'well_id': 'G9', 'state': 'sample', 'colour': '#ff00ff'}, 136: {'group': 0, 'well_id': 'H9', 'state': 'sample', 'colour': '#ff00ff'}, 137: {'group': 0, 'well_id': 'I9', 'state': 'sample', 'colour': '#ff00ff'}, 138: {'group': 0, 'well_id': 'J9', 'state': 'sample', 'colour': '#ff00ff'}, 139: {'group': 0, 'well_id': 'K9', 'state': 'sample', 'colour': '#ff00ff'}, 140: {'group': 0, 'well_id': 'L9', 'state': 'sample', 'colour': '#ff00ff'}, 141: {'group': 0, 'well_id': 'M9', 'state': 'sample', 'colour': '#ff00ff'}, 142: {'group': 0, 'well_id': 'N9', 'state': 'sample', 'colour': '#ff00ff'}, 143: {'group': 0, 'well_id': 'O9', 'state': 'sample', 'colour': '#ff00ff'}, 144: {'group': 0, 'well_id': 'P9', 'state': 'empty', 'colour': '#1e0bc8'}, 145: {'group': 0, 'well_id': 'A10', 'state': 'empty', 'colour': '#1e0bc8'}, 146: {'group': 0, 'well_id': 'B10', 'state': 'sample', 'colour': '#ff00ff'}, 147: {'group': 0, 'well_id': 'C10', 'state': 'sample', 'colour': '#ff00ff'}, 148: {'group': 0, 'well_id': 'D10', 'state': 'sample', 'colour': '#ff00ff'}, 149: {'group': 0, 'well_id': 'E10', 'state': 'sample', 'colour': '#ff00ff'}, 150: {'group': 0, 'well_id': 'F10', 'state': 'sample', 'colour': '#ff00ff'}, 151: {'group': 0, 'well_id': 'G10', 'state': 'sample', 'colour': '#ff00ff'}, 152: {'group': 0, 'well_id': 'H10', 'state': 'sample', 'colour': '#ff00ff'}, 153: {'group': 0, 'well_id': 'I10', 'state': 'sample', 'colour': '#ff00ff'}, 154: {'group': 0, 'well_id': 'J10', 'state': 'sample', 'colour': '#ff00ff'}, 155: {'group': 0, 'well_id': 'K10', 'state': 'sample', 'colour': '#ff00ff'}, 156: {'group': 0, 'well_id': 'L10', 'state': 'sample', 'colour': '#ff00ff'}, 157: {'group': 0, 'well_id': 'M10', 'state': 'sample', 'colour': '#ff00ff'}, 158: {'group': 0, 'well_id': 'N10', 'state': 'sample', 'colour': '#ff00ff'}, 159: {'group': 0, 'well_id': 'O10', 'state': 'sample', 'colour': '#ff00ff'}, 160: {'group': 0, 'well_id': 'P10', 'state': 'empty', 'colour': '#1e0bc8'}, 161: {'group': 0, 'well_id': 'A11', 'state': 'empty', 'colour': '#1e0bc8'}, 162: {'group': 0, 'well_id': 'B11', 'state': 'sample', 'colour': '#ff00ff'}, 163: {'group': 0, 'well_id': 'C11', 'state': 'sample', 'colour': '#ff00ff'}, 164: {'group': 0, 'well_id': 'D11', 'state': 'sample', 'colour': '#ff00ff'}, 165: {'group': 0, 'well_id': 'E11', 'state': 'sample', 'colour': '#ff00ff'}, 166: {'group': 0, 'well_id': 'F11', 'state': 'sample', 'colour': '#ff00ff'}, 167: {'group': 0, 'well_id': 'G11', 'state': 'sample', 'colour': '#ff00ff'}, 168: {'group': 0, 'well_id': 'H11', 'state': 'sample', 'colour': '#ff00ff'}, 169: {'group': 0, 'well_id': 'I11', 'state': 'sample', 'colour': '#ff00ff'}, 170: {'group': 0, 'well_id': 'J11', 'state': 'sample', 'colour': '#ff00ff'}, 171: {'group': 0, 'well_id': 'K11', 'state': 'sample', 'colour': '#ff00ff'}, 172: {'group': 0, 'well_id': 'L11', 'state': 'sample', 'colour': '#ff00ff'}, 173: {'group': 0, 'well_id': 'M11', 'state': 'sample', 'colour': '#ff00ff'}, 174: {'group': 0, 'well_id': 'N11', 'state': 'sample', 'colour': '#ff00ff'}, 175: {'group': 0, 'well_id': 'O11', 'state': 'sample', 'colour': '#ff00ff'}, 176: {'group': 0, 'well_id': 'P11', 'state': 'empty', 'colour': '#1e0bc8'}, 177: {'group': 0, 'well_id': 'A12', 'state': 'empty', 'colour': '#1e0bc8'}, 178: {'group': 0, 'well_id': 'B12', 'state': 'sample', 'colour': '#ff00ff'}, 179: {'group': 0, 'well_id': 'C12', 'state': 'sample', 'colour': '#ff00ff'}, 180: {'group': 0, 'well_id': 'D12', 'state': 'sample', 'colour': '#ff00ff'}, 181: {'group': 0, 'well_id': 'E12', 'state': 'sample', 'colour': '#ff00ff'}, 182: {'group': 0, 'well_id': 'F12', 'state': 'sample', 'colour': '#ff00ff'}, 183: {'group': 0, 'well_id': 'G12', 'state': 'sample', 'colour': '#ff00ff'}, 184: {'group': 0, 'well_id': 'H12', 'state': 'sample', 'colour': '#ff00ff'}, 185: {'group': 0, 'well_id': 'I12', 'state': 'sample', 'colour': '#ff00ff'}, 186: {'group': 0, 'well_id': 'J12', 'state': 'sample', 'colour': '#ff00ff'}, 187: {'group': 0, 'well_id': 'K12', 'state': 'sample', 'colour': '#ff00ff'}, 188: {'group': 0, 'well_id': 'L12', 'state': 'sample', 'colour': '#ff00ff'}, 189: {'group': 0, 'well_id': 'M12', 'state': 'sample', 'colour': '#ff00ff'}, 190: {'group': 0, 'well_id': 'N12', 'state': 'sample', 'colour': '#ff00ff'}, 191: {'group': 0, 'well_id': 'O12', 'state': 'sample', 'colour': '#ff00ff'}, 192: {'group': 0, 'well_id': 'P12', 'state': 'empty', 'colour': '#1e0bc8'}, 193: {'group': 0, 'well_id': 'A13', 'state': 'empty', 'colour': '#1e0bc8'}, 194: {'group': 0, 'well_id': 'B13', 'state': 'sample', 'colour': '#ff00ff'}, 195: {'group': 0, 'well_id': 'C13', 'state': 'sample', 'colour': '#ff00ff'}, 196: {'group': 0, 'well_id': 'D13', 'state': 'sample', 'colour': '#ff00ff'}, 197: {'group': 0, 'well_id': 'E13', 'state': 'sample', 'colour': '#ff00ff'}, 198: {'group': 0, 'well_id': 'F13', 'state': 'sample', 'colour': '#ff00ff'}, 199: {'group': 0, 'well_id': 'G13', 'state': 'sample', 'colour': '#ff00ff'}, 200: {'group': 0, 'well_id': 'H13', 'state': 'sample', 'colour': '#ff00ff'}, 201: {'group': 0, 'well_id': 'I13', 'state': 'sample', 'colour': '#ff00ff'}, 202: {'group': 0, 'well_id': 'J13', 'state': 'sample', 'colour': '#ff00ff'}, 203: {'group': 0, 'well_id': 'K13', 'state': 'sample', 'colour': '#ff00ff'}, 204: {'group': 0, 'well_id': 'L13', 'state': 'sample', 'colour': '#ff00ff'}, 205: {'group': 0, 'well_id': 'M13', 'state': 'sample', 'colour': '#ff00ff'}, 206: {'group': 0, 'well_id': 'N13', 'state': 'sample', 'colour': '#ff00ff'}, 207: {'group': 0, 'well_id': 'O13', 'state': 'sample', 'colour': '#ff00ff'}, 208: {'group': 0, 'well_id': 'P13', 'state': 'empty', 'colour': '#1e0bc8'}, 209: {'group': 0, 'well_id': 'A14', 'state': 'empty', 'colour': '#1e0bc8'}, 210: {'group': 0, 'well_id': 'B14', 'state': 'sample', 'colour': '#ff00ff'}, 211: {'group': 0, 'well_id': 'C14', 'state': 'sample', 'colour': '#ff00ff'}, 212: {'group': 0, 'well_id': 'D14', 'state': 'sample', 'colour': '#ff00ff'}, 213: {'group': 0, 'well_id': 'E14', 'state': 'sample', 'colour': '#ff00ff'}, 214: {'group': 0, 'well_id': 'F14', 'state': 'sample', 'colour': '#ff00ff'}, 215: {'group': 0, 'well_id': 'G14', 'state': 'sample', 'colour': '#ff00ff'}, 216: {'group': 0, 'well_id': 'H14', 'state': 'sample', 'colour': '#ff00ff'}, 217: {'group': 0, 'well_id': 'I14', 'state': 'sample', 'colour': '#ff00ff'}, 218: {'group': 0, 'well_id': 'J14', 'state': 'sample', 'colour': '#ff00ff'}, 219: {'group': 0, 'well_id': 'K14', 'state': 'sample', 'colour': '#ff00ff'}, 220: {'group': 0, 'well_id': 'L14', 'state': 'sample', 'colour': '#ff00ff'}, 221: {'group': 0, 'well_id': 'M14', 'state': 'sample', 'colour': '#ff00ff'}, 222: {'group': 0, 'well_id': 'N14', 'state': 'sample', 'colour': '#ff00ff'}, 223: {'group': 0, 'well_id': 'O14', 'state': 'sample', 'colour': '#ff00ff'}, 224: {'group': 0, 'well_id': 'P14', 'state': 'empty', 'colour': '#1e0bc8'}, 225: {'group': 0, 'well_id': 'A15', 'state': 'empty', 'colour': '#1e0bc8'}, 226: {'group': 0, 'well_id': 'B15', 'state': 'sample', 'colour': '#ff00ff'}, 227: {'group': 0, 'well_id': 'C15', 'state': 'sample', 'colour': '#ff00ff'}, 228: {'group': 0, 'well_id': 'D15', 'state': 'sample', 'colour': '#ff00ff'}, 229: {'group': 0, 'well_id': 'E15', 'state': 'sample', 'colour': '#ff00ff'}, 230: {'group': 0, 'well_id': 'F15', 'state': 'sample', 'colour': '#ff00ff'}, 231: {'group': 0, 'well_id': 'G15', 'state': 'sample', 'colour': '#ff00ff'}, 232: {'group': 0, 'well_id': 'H15', 'state': 'sample', 'colour': '#ff00ff'}, 233: {'group': 0, 'well_id': 'I15', 'state': 'sample', 'colour': '#ff00ff'}, 234: {'group': 0, 'well_id': 'J15', 'state': 'sample', 'colour': '#ff00ff'}, 235: {'group': 0, 'well_id': 'K15', 'state': 'sample', 'colour': '#ff00ff'}, 236: {'group': 0, 'well_id': 'L15', 'state': 'sample', 'colour': '#ff00ff'}, 237: {'group': 0, 'well_id': 'M15', 'state': 'sample', 'colour': '#ff00ff'}, 238: {'group': 0, 'well_id': 'N15', 'state': 'sample', 'colour': '#ff00ff'}, 239: {'group': 0, 'well_id': 'O15', 'state': 'sample', 'colour': '#ff00ff'}, 240: {'group': 0, 'well_id': 'P15', 'state': 'empty', 'colour': '#1e0bc8'}, 241: {'group': 0, 'well_id': 'A16', 'state': 'empty', 'colour': '#1e0bc8'}, 242: {'group': 0, 'well_id': 'B16', 'state': 'sample', 'colour': '#ff00ff'}, 243: {'group': 0, 'well_id': 'C16', 'state': 'sample', 'colour': '#ff00ff'}, 244: {'group': 0, 'well_id': 'D16', 'state': 'sample', 'colour': '#ff00ff'}, 245: {'group': 0, 'well_id': 'E16', 'state': 'sample', 'colour': '#ff00ff'}, 246: {'group': 0, 'well_id': 'F16', 'state': 'sample', 'colour': '#ff00ff'}, 247: {'group': 0, 'well_id': 'G16', 'state': 'sample', 'colour': '#ff00ff'}, 248: {'group': 0, 'well_id': 'H16', 'state': 'sample', 'colour': '#ff00ff'}, 249: {'group': 0, 'well_id': 'I16', 'state': 'sample', 'colour': '#ff00ff'}, 250: {'group': 0, 'well_id': 'J16', 'state': 'sample', 'colour': '#ff00ff'}, 251: {'group': 0, 'well_id': 'K16', 'state': 'sample', 'colour': '#ff00ff'}, 252: {'group': 0, 'well_id': 'L16', 'state': 'sample', 'colour': '#ff00ff'}, 253: {'group': 0, 'well_id': 'M16', 'state': 'sample', 'colour': '#ff00ff'}, 254: {'group': 0, 'well_id': 'N16', 'state': 'sample', 'colour': '#ff00ff'}, 255: {'group': 0, 'well_id': 'O16', 'state': 'sample', 'colour': '#ff00ff'}, 256: {'group': 0, 'well_id': 'P16', 'state': 'empty', 'colour': '#1e0bc8'}, 257: {'group': 0, 'well_id': 'A17', 'state': 'empty', 'colour': '#1e0bc8'}, 258: {'group': 0, 'well_id': 'B17', 'state': 'sample', 'colour': '#ff00ff'}, 259: {'group': 0, 'well_id': 'C17', 'state': 'sample', 'colour': '#ff00ff'}, 260: {'group': 0, 'well_id': 'D17', 'state': 'sample', 'colour': '#ff00ff'}, 261: {'group': 0, 'well_id': 'E17', 'state': 'sample', 'colour': '#ff00ff'}, 262: {'group': 0, 'well_id': 'F17', 'state': 'sample', 'colour': '#ff00ff'}, 263: {'group': 0, 'well_id': 'G17', 'state': 'sample', 'colour': '#ff00ff'}, 264: {'group': 0, 'well_id': 'H17', 'state': 'sample', 'colour': '#ff00ff'}, 265: {'group': 0, 'well_id': 'I17', 'state': 'sample', 'colour': '#ff00ff'}, 266: {'group': 0, 'well_id': 'J17', 'state': 'sample', 'colour': '#ff00ff'}, 267: {'group': 0, 'well_id': 'K17', 'state': 'sample', 'colour': '#ff00ff'}, 268: {'group': 0, 'well_id': 'L17', 'state': 'sample', 'colour': '#ff00ff'}, 269: {'group': 0, 'well_id': 'M17', 'state': 'sample', 'colour': '#ff00ff'}, 270: {'group': 0, 'well_id': 'N17', 'state': 'sample', 'colour': '#ff00ff'}, 271: {'group': 0, 'well_id': 'O17', 'state': 'sample', 'colour': '#ff00ff'}, 272: {'group': 0, 'well_id': 'P17', 'state': 'empty', 'colour': '#1e0bc8'}, 273: {'group': 0, 'well_id': 'A18', 'state': 'empty', 'colour': '#1e0bc8'}, 274: {'group': 0, 'well_id': 'B18', 'state': 'sample', 'colour': '#ff00ff'}, 275: {'group': 0, 'well_id': 'C18', 'state': 'sample', 'colour': '#ff00ff'}, 276: {'group': 0, 'well_id': 'D18', 'state': 'sample', 'colour': '#ff00ff'}, 277: {'group': 0, 'well_id': 'E18', 'state': 'sample', 'colour': '#ff00ff'}, 278: {'group': 0, 'well_id': 'F18', 'state': 'sample', 'colour': '#ff00ff'}, 279: {'group': 0, 'well_id': 'G18', 'state': 'sample', 'colour': '#ff00ff'}, 280: {'group': 0, 'well_id': 'H18', 'state': 'sample', 'colour': '#ff00ff'}, 281: {'group': 0, 'well_id': 'I18', 'state': 'sample', 'colour': '#ff00ff'}, 282: {'group': 0, 'well_id': 'J18', 'state': 'sample', 'colour': '#ff00ff'}, 283: {'group': 0, 'well_id': 'K18', 'state': 'sample', 'colour': '#ff00ff'}, 284: {'group': 0, 'well_id': 'L18', 'state': 'sample', 'colour': '#ff00ff'}, 285: {'group': 0, 'well_id': 'M18', 'state': 'sample', 'colour': '#ff00ff'}, 286: {'group': 0, 'well_id': 'N18', 'state': 'sample', 'colour': '#ff00ff'}, 287: {'group': 0, 'well_id': 'O18', 'state': 'sample', 'colour': '#ff00ff'}, 288: {'group': 0, 'well_id': 'P18', 'state': 'empty', 'colour': '#1e0bc8'}, 289: {'group': 0, 'well_id': 'A19', 'state': 'empty', 'colour': '#1e0bc8'}, 290: {'group': 0, 'well_id': 'B19', 'state': 'sample', 'colour': '#ff00ff'}, 291: {'group': 0, 'well_id': 'C19', 'state': 'sample', 'colour': '#ff00ff'}, 292: {'group': 0, 'well_id': 'D19', 'state': 'sample', 'colour': '#ff00ff'}, 293: {'group': 0, 'well_id': 'E19', 'state': 'sample', 'colour': '#ff00ff'}, 294: {'group': 0, 'well_id': 'F19', 'state': 'sample', 'colour': '#ff00ff'}, 295: {'group': 0, 'well_id': 'G19', 'state': 'sample', 'colour': '#ff00ff'}, 296: {'group': 0, 'well_id': 'H19', 'state': 'sample', 'colour': '#ff00ff'}, 297: {'group': 0, 'well_id': 'I19', 'state': 'sample', 'colour': '#ff00ff'}, 298: {'group': 0, 'well_id': 'J19', 'state': 'sample', 'colour': '#ff00ff'}, 299: {'group': 0, 'well_id': 'K19', 'state': 'sample', 'colour': '#ff00ff'}, 300: {'group': 0, 'well_id': 'L19', 'state': 'sample', 'colour': '#ff00ff'}, 301: {'group': 0, 'well_id': 'M19', 'state': 'sample', 'colour': '#ff00ff'}, 302: {'group': 0, 'well_id': 'N19', 'state': 'sample', 'colour': '#ff00ff'}, 303: {'group': 0, 'well_id': 'O19', 'state': 'sample', 'colour': '#ff00ff'}, 304: {'group': 0, 'well_id': 'P19', 'state': 'empty', 'colour': '#1e0bc8'}, 305: {'group': 0, 'well_id': 'A20', 'state': 'empty', 'colour': '#1e0bc8'}, 306: {'group': 0, 'well_id': 'B20', 'state': 'sample', 'colour': '#ff00ff'}, 307: {'group': 0, 'well_id': 'C20', 'state': 'sample', 'colour': '#ff00ff'}, 308: {'group': 0, 'well_id': 'D20', 'state': 'sample', 'colour': '#ff00ff'}, 309: {'group': 0, 'well_id': 'E20', 'state': 'sample', 'colour': '#ff00ff'}, 310: {'group': 0, 'well_id': 'F20', 'state': 'sample', 'colour': '#ff00ff'}, 311: {'group': 0, 'well_id': 'G20', 'state': 'sample', 'colour': '#ff00ff'}, 312: {'group': 0, 'well_id': 'H20', 'state': 'sample', 'colour': '#ff00ff'}, 313: {'group': 0, 'well_id': 'I20', 'state': 'sample', 'colour': '#ff00ff'}, 314: {'group': 0, 'well_id': 'J20', 'state': 'sample', 'colour': '#ff00ff'}, 315: {'group': 0, 'well_id': 'K20', 'state': 'sample', 'colour': '#ff00ff'}, 316: {'group': 0, 'well_id': 'L20', 'state': 'sample', 'colour': '#ff00ff'}, 317: {'group': 0, 'well_id': 'M20', 'state': 'sample', 'colour': '#ff00ff'}, 318: {'group': 0, 'well_id': 'N20', 'state': 'sample', 'colour': '#ff00ff'}, 319: {'group': 0, 'well_id': 'O20', 'state': 'sample', 'colour': '#ff00ff'}, 320: {'group': 0, 'well_id': 'P20', 'state': 'empty', 'colour': '#1e0bc8'}, 321: {'group': 0, 'well_id': 'A21', 'state': 'empty', 'colour': '#1e0bc8'}, 322: {'group': 0, 'well_id': 'B21', 'state': 'sample', 'colour': '#ff00ff'}, 323: {'group': 0, 'well_id': 'C21', 'state': 'sample', 'colour': '#ff00ff'}, 324: {'group': 0, 'well_id': 'D21', 'state': 'sample', 'colour': '#ff00ff'}, 325: {'group': 0, 'well_id': 'E21', 'state': 'sample', 'colour': '#ff00ff'}, 326: {'group': 0, 'well_id': 'F21', 'state': 'sample', 'colour': '#ff00ff'}, 327: {'group': 0, 'well_id': 'G21', 'state': 'sample', 'colour': '#ff00ff'}, 328: {'group': 0, 'well_id': 'H21', 'state': 'sample', 'colour': '#ff00ff'}, 329: {'group': 0, 'well_id': 'I21', 'state': 'sample', 'colour': '#ff00ff'}, 330: {'group': 0, 'well_id': 'J21', 'state': 'sample', 'colour': '#ff00ff'}, 331: {'group': 0, 'well_id': 'K21', 'state': 'sample', 'colour': '#ff00ff'}, 332: {'group': 0, 'well_id': 'L21', 'state': 'sample', 'colour': '#ff00ff'}, 333: {'group': 0, 'well_id': 'M21', 'state': 'sample', 'colour': '#ff00ff'}, 334: {'group': 0, 'well_id': 'N21', 'state': 'sample', 'colour': '#ff00ff'}, 335: {'group': 0, 'well_id': 'O21', 'state': 'sample', 'colour': '#ff00ff'}, 336: {'group': 0, 'well_id': 'P21', 'state': 'empty', 'colour': '#1e0bc8'}, 337: {'group': 0, 'well_id': 'A22', 'state': 'empty', 'colour': '#1e0bc8'}, 338: {'group': 0, 'well_id': 'B22', 'state': 'sample', 'colour': '#ff00ff'}, 339: {'group': 0, 'well_id': 'C22', 'state': 'sample', 'colour': '#ff00ff'}, 340: {'group': 0, 'well_id': 'D22', 'state': 'sample', 'colour': '#ff00ff'}, 341: {'group': 0, 'well_id': 'E22', 'state': 'sample', 'colour': '#ff00ff'}, 342: {'group': 0, 'well_id': 'F22', 'state': 'sample', 'colour': '#ff00ff'}, 343: {'group': 0, 'well_id': 'G22', 'state': 'sample', 'colour': '#ff00ff'}, 344: {'group': 0, 'well_id': 'H22', 'state': 'sample', 'colour': '#ff00ff'}, 345: {'group': 0, 'well_id': 'I22', 'state': 'sample', 'colour': '#ff00ff'}, 346: {'group': 0, 'well_id': 'J22', 'state': 'sample', 'colour': '#ff00ff'}, 347: {'group': 0, 'well_id': 'K22', 'state': 'sample', 'colour': '#ff00ff'}, 348: {'group': 0, 'well_id': 'L22', 'state': 'sample', 'colour': '#ff00ff'}, 349: {'group': 0, 'well_id': 'M22', 'state': 'sample', 'colour': '#ff00ff'}, 350: {'group': 0, 'well_id': 'N22', 'state': 'sample', 'colour': '#ff00ff'}, 351: {'group': 0, 'well_id': 'O22', 'state': 'sample', 'colour': '#ff00ff'}, 352: {'group': 0, 'well_id': 'P22', 'state': 'empty', 'colour': '#1e0bc8'}, 353: {'group': 0, 'well_id': 'A23', 'state': 'empty', 'colour': '#1e0bc8'}, 354: {'group': 0, 'well_id': 'B23', 'state': 'empty', 'colour': '#1e0bc8'}, 355: {'group': 0, 'well_id': 'C23', 'state': 'empty', 'colour': '#1e0bc8'}, 356: {'group': 0, 'well_id': 'D23', 'state': 'empty', 'colour': '#1e0bc8'}, 357: {'group': 0, 'well_id': 'E23', 'state': 'empty', 'colour': '#1e0bc8'}, 358: {'group': 0, 'well_id': 'F23', 'state': 'empty', 'colour': '#1e0bc8'}, 359: {'group': 0, 'well_id': 'G23', 'state': 'empty', 'colour': '#1e0bc8'}, 360: {'group': 0, 'well_id': 'H23', 'state': 'empty', 'colour': '#1e0bc8'}, 361: {'group': 0, 'well_id': 'I23', 'state': 'empty', 'colour': '#1e0bc8'}, 362: {'group': 0, 'well_id': 'J23', 'state': 'empty', 'colour': '#1e0bc8'}, 363: {'group': 0, 'well_id': 'K23', 'state': 'empty', 'colour': '#1e0bc8'}, 364: {'group': 0, 'well_id': 'L23', 'state': 'empty', 'colour': '#1e0bc8'}, 365: {'group': 0, 'well_id': 'M23', 'state': 'empty', 'colour': '#1e0bc8'}, 366: {'group': 0, 'well_id': 'N23', 'state': 'empty', 'colour': '#1e0bc8'}, 367: {'group': 0, 'well_id': 'O23', 'state': 'empty', 'colour': '#1e0bc8'}, 368: {'group': 0, 'well_id': 'P23', 'state': 'empty', 'colour': '#1e0bc8'}, 369: {'group': 0, 'well_id': 'A24', 'state': 'empty', 'colour': '#1e0bc8'}, 370: {'group': 0, 'well_id': 'B24', 'state': 'empty', 'colour': '#1e0bc8'}, 371: {'group': 0, 'well_id': 'C24', 'state': 'empty', 'colour': '#1e0bc8'}, 372: {'group': 0, 'well_id': 'D24', 'state': 'empty', 'colour': '#1e0bc8'}, 373: {'group': 0, 'well_id': 'E24', 'state': 'empty', 'colour': '#1e0bc8'}, 374: {'group': 0, 'well_id': 'F24', 'state': 'empty', 'colour': '#1e0bc8'}, 375: {'group': 0, 'well_id': 'G24', 'state': 'empty', 'colour': '#1e0bc8'}, 376: {'group': 0, 'well_id': 'H24', 'state': 'empty', 'colour': '#1e0bc8'}, 377: {'group': 0, 'well_id': 'I24', 'state': 'empty', 'colour': '#1e0bc8'}, 378: {'group': 0, 'well_id': 'J24', 'state': 'empty', 'colour': '#1e0bc8'}, 379: {'group': 0, 'well_id': 'K24', 'state': 'empty', 'colour': '#1e0bc8'}, 380: {'group': 0, 'well_id': 'L24', 'state': 'empty', 'colour': '#1e0bc8'}, 381: {'group': 0, 'well_id': 'M24', 'state': 'empty', 'colour': '#1e0bc8'}, 382: {'group': 0, 'well_id': 'N24', 'state': 'empty', 'colour': '#1e0bc8'}, 383: {'group': 0, 'well_id': 'O24', 'state': 'empty', 'colour': '#1e0bc8'}, 384: {'group': 0, 'well_id': 'P24', 'state': 'empty', 'colour': '#1e0bc8'}}, 'plate_type': 'plate_384'}
    all_data = {'plates': {'original': {'wells': {'A1': 0.0461, 'B1': 0.0461, 'C1': 0.047, 'D1': 0.0477, 'E1': 0.051, 'F1': 0.0522, 'G1': 0.054, 'H1': 0.0552, 'I1': 0.0559, 'J1': 0.0552, 'K1': 0.0545, 'L1': 0.0544, 'M1': 0.0649, 'N1': 0.0554, 'O1': 0.0565, 'P1': 0.0591, 'A2': 0.0545, 'P2': 0.0715, 'A3': 0.047, 'P3': 0.054, 'A4': 0.0475, 'P4': 0.0506, 'A5': 0.0472, 'P5': 0.0691, 'A6': 0.0485, 'P6': 0.0814, 'A7': 0.0479, 'P7': 0.0475, 'A8': 0.0472, 'P8': 0.047, 'A9': 0.0467, 'P9': 0.0545, 'A10': 0.049, 'P10': 0.0467, 'A11': 0.0477, 'P11': 0.0464, 'A12': 0.0493, 'P12': 0.0461, 'A13': 0.0578, 'P13': 0.0519, 'A14': 0.0471, 'P14': 0.0467, 'A15': 0.0468, 'P15': 0.0467, 'A16': 0.0461, 'P16': 0.0522, 'A17': 0.0492, 'P17': 0.0466, 'A18': 0.047, 'P18': 0.0465, 'A19': 0.0553, 'P19': 0.0466, 'A20': 0.047, 'P20': 0.0463, 'A21': 0.0471, 'P21': 0.0464, 'A22': 0.0482, 'P22': 0.0467, 'A23': 0.0552, 'B23': 0.0511, 'C23': 0.0467, 'D23': 0.0498, 'E23': 0.0371, 'F23': 0.0598, 'G23': 0.0509, 'H23': 0.1572, 'I23': 0.056, 'J23': 0.043, 'K23': 0.0351, 'L23': 0.0541, 'M23': 0.0497, 'N23': 0.0497, 'O23': 0.0529, 'P23': 0.0537, 'A24': 0.0464, 'B24': 0.0462, 'C24': 0.0498, 'D24': 0.0616, 'E24': 0.054, 'F24': 0.0528, 'G24': 0.0518, 'H24': 0.0506, 'I24': 0.0513, 'J24': 0.0414, 'K24': 0.04, 'L24': 0.0366, 'M24': 0.0491, 'N24': 0.0471, 'O24': 0.0472, 'P24': 0.049, 'B2': 0.0468, 'C2': 0.0467, 'D2': 0.0483, 'E2': 0.0476, 'F2': 0.0465, 'G2': 0.0465, 'H2': 0.0491, 'I2': 0.0595, 'J2': 0.0547, 'K2': 0.0464, 'L2': 0.0482, 'M2': 0.0465, 'N2': 0.048, 'O2': 0.0477, 'B3': 0.0471, 'C3': 0.0494, 'D3': 0.0495, 'E3': 0.1637, 'F3': 0.2435, 'G3': 0.2726, 'H3': 0.238, 'I3': 0.1689, 'J3': 0.1623, 'K3': 0.0672, 'L3': 0.0457, 'M3': 0.0463, 'N3': 0.053, 'O3': 0.0482, 'B4': 0.0468, 'C4': 0.0657, 'D4': 0.1486, 'E4': 0.3171, 'F4': 0.2748, 'G4': 0.2937, 'H4': 0.1558, 'I4': 0.3233, 'J4': 0.238, 'K4': 0.3487, 'L4': 0.2707, 'M4': 0.0651, 'N4': 0.0522, 'O4': 0.0512, 'B5': 0.0539, 'C5': 0.0599, 'D5': 0.1072, 'E5': 0.3235, 'F5': 0.3355, 'G5': 0.3385, 'H5': 0.3529, 'I5': 0.3938, 'J5': 0.3771, 'K5': 0.2877, 'L5': 0.3583, 'M5': 0.1292, 'N5': 0.0418, 'O5': 0.0395, 'B6': 0.0476, 'C6': 0.0471, 'D6': 0.1441, 'E6': 0.391, 'F6': 0.3895, 'G6': 0.3624, 'H6': 0.3674, 'I6': 0.3693, 'J6': 0.4047, 'K6': 0.3906, 'L6': 0.2966, 'M6': 0.1688, 'N6': 0.0349, 'O6': 0.049, 'B7': 0.05, 'C7': 0.1284, 'D7': 0.2809, 'E7': 0.3643, 'F7': 0.3807, 'G7': 0.3617, 'H7': 0.3635, 'I7': 0.3418, 'J7': 0.3775, 'K7': 0.3793, 'L7': 0.3989, 'M7': 0.3374, 'N7': 0.1954, 'O7': 0.0459, 'B8': 0.0494, 'C8': 0.0593, 'D8': 0.2777, 'E8': 0.4032, 'F8': 0.4565, 'G8': 0.3635, 'H8': 0.3526, 'I8': 0.3147, 'J8': 0.3625, 'K8': 0.3434, 'L8': 0.3793, 'M8': 0.3311, 'N8': 0.2592, 'O8': 0.1487, 'B9': 0.0679, 'C9': 0.1274, 'D9': 0.2681, 'E9': 0.3315, 'F9': 0.4043, 'G9': 0.4301, 'H9': 0.426, 'I9': 0.0389, 'J9': 0.0422, 'K9': 0.3412, 'L9': 0.3028, 'M9': 0.3581, 'N9': 0.2962, 'O9': 0.1356, 'B10': 0.0486, 'C10': 0.0483, 'D10': 0.2516, 'E10': 0.3929, 'F10': 0.411, 'G10': 0.4542, 'H10': 0.3072, 'I10': 0.0337, 'J10': 0.1713, 'K10': 0.212, 'L10': 0.287, 'M10': 0.3548, 'N10': 0.3098, 'O10': 0.1319, 'B11': 0.0526, 'C11': 0.1018, 'D11': 0.3073, 'E11': 0.3667, 'F11': 0.4027, 'G11': 0.4129, 'H11': 0.4041, 'I11': 0.3292, 'J11': 0.4021, 'K11': 0.3987, 'L11': 0.385, 'M11': 0.3636, 'N11': 0.2881, 'O11': 0.12, 'B12': 0.0492, 'C12': 0.0541, 'D12': 0.2429, 'E12': 0.3642, 'F12': 0.3222, 'G12': 0.4039, 'H12': 0.3939, 'I12': 0.4122, 'J12': 0.3668, 'K12': 0.4156, 'L12': 0.4168, 'M12': 0.4167, 'N12': 0.2896, 'O12': 0.1259, 'B13': 0.0556, 'C13': 0.0545, 'D13': 0.3462, 'E13': 0.3654, 'F13': 0.3651, 'G13': 0.3521, 'H13': 0.3611, 'I13': 0.4519, 'J13': 0.3515, 'K13': 0.4208, 'L13': 0.3573, 'M13': 0.271, 'N13': 0.3969, 'O13': 0.2095, 'B14': 0.048, 'C14': 0.0469, 'D14': 0.3325, 'E14': 0.3355, 'F14': 0.2219, 'G14': 0.4176, 'H14': 0.4002, 'I14': 0.4628, 'J14': 0.4193, 'K14': 0.4212, 'L14': 0.3707, 'M14': 0.3146, 'N14': 0.3256, 'O14': 0.178, 'B15': 0.0461, 'C15': 0.0482, 'D15': 0.3088, 'E15': 0.0766, 'F15': 0.4086, 'G15': 0.4484, 'H15': 0.121, 'I15': 0.3988, 'J15': 0.4351, 'K15': 0.2984, 'L15': 0.3617, 'M15': 0.364, 'N15': 0.3418, 'O15': 0.2347, 'B16': 0.05, 'C16': 0.0493, 'D16': 0.2564, 'E16': 0.1883, 'F16': 0.2366, 'G16': 0.4042, 'H16': 0.3705, 'I16': 0.3417, 'J16': 0.3232, 'K16': 0.3682, 'L16': 0.3722, 'M16': 0.3391, 'N16': 0.3908, 'O16': 0.2225, 'B17': 0.0622, 'C17': 0.0541, 'D17': 0.3246, 'E17': 0.3549, 'F17': 0.387, 'G17': 0.4348, 'H17': 0.3907, 'I17': 0.3461, 'J17': 0.437, 'K17': 0.3844, 'L17': 0.3759, 'M17': 0.4078, 'N17': 0.3824, 'O17': 0.172, 'B18': 0.0465, 'C18': 0.0464, 'D18': 0.3025, 'E18': 0.3559, 'F18': 0.3568, 'G18': 0.2927, 'H18': 0.335, 'I18': 0.4592, 'J18': 0.336, 'K18': 0.3917, 'L18': 0.3848, 'M18': 0.4393, 'N18': 0.3174, 'O18': 0.1659, 'B19': 0.0426, 'C19': 0.0448, 'D19': 0.0597, 'E19': 0.1949, 'F19': 0.3647, 'G19': 0.3449, 'H19': 0.3914, 'I19': 0.3061, 'J19': 0.4072, 'K19': 0.4135, 'L19': 0.3424, 'M19': 0.3904, 'N19': 0.3645, 'O19': 0.2055, 'B20': 0.0569, 'C20': 0.0396, 'D20': 0.0412, 'E20': 0.043, 'F20': 0.2671, 'G20': 0.3427, 'H20': 0.111, 'I20': 0.0352, 'J20': 0.2721, 'K20': 0.366, 'L20': 0.3561, 'M20': 0.3115, 'N20': 0.2857, 'O20': 0.1843, 'B21': 0.101, 'C21': 0.0609, 'D21': 0.0836, 'E21': 0.0891, 'F21': 0.2801, 'G21': 0.0447, 'H21': 0.0403, 'I21': 0.0318, 'J21': 0.0518, 'K21': 0.2705, 'L21': 0.3488, 'M21': 0.3047, 'N21': 0.3145, 'O21': 0.2006, 'B22': 0.0472, 'C22': 0.0506, 'D22': 0.0663, 'E22': 0.0416, 'F22': 0.0509, 'G22': 0.1231, 'H22': 0.0597, 'I22': 0.0892, 'J22': 0.2535, 'K22': 0.2321, 'L22': 0.2246, 'M22': 0.2272, 'N22': 0.1513, 'O22': 0.046}}}, 'calculations': {}}
    well_row_col = {'well_col': ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20', '21', '22', '23', '24'], 'well_row': ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P']}
    well_type = {'empty': ['A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1', 'H1', 'I1', 'J1', 'K1', 'L1', 'M1', 'N1', 'O1', 'P1', 'A2', 'P2', 'A3', 'P3', 'A4', 'P4', 'A5', 'P5', 'A6', 'P6', 'A7', 'P7', 'A8', 'P8', 'A9', 'P9', 'A10', 'P10', 'A11', 'P11', 'A12', 'P12', 'A13', 'P13', 'A14', 'P14', 'A15', 'P15', 'A16', 'P16', 'A17', 'P17', 'A18', 'P18', 'A19', 'P19', 'A20', 'P20', 'A21', 'P21', 'A22', 'P22', 'A23', 'B23', 'C23', 'D23', 'E23', 'F23', 'G23', 'H23', 'I23', 'J23', 'K23', 'L23', 'M23', 'N23', 'O23', 'P23', 'A24', 'B24', 'C24', 'D24', 'E24', 'F24', 'G24', 'H24', 'I24', 'J24', 'K24', 'L24', 'M24', 'N24', 'O24', 'P24'], 'minimum': ['B2', 'C2', 'D2', 'E2', 'F2', 'G2', 'H2', 'I2', 'J2', 'K2', 'L2', 'M2', 'N2', 'O2'], 'max': ['B3', 'C3', 'D3', 'E3', 'F3', 'G3', 'H3', 'I3', 'J3', 'K3', 'L3', 'M3', 'N3', 'O3'], 'sample': ['B4', 'C4', 'D4', 'E4', 'F4', 'G4', 'H4', 'I4', 'J4', 'K4', 'L4', 'M4', 'N4', 'O4', 'B5', 'C5', 'D5', 'E5', 'F5', 'G5', 'H5', 'I5', 'J5', 'K5', 'L5', 'M5', 'N5', 'O5', 'B6', 'C6', 'D6', 'E6', 'F6', 'G6', 'H6', 'I6', 'J6', 'K6', 'L6', 'M6', 'N6', 'O6', 'B7', 'C7', 'D7', 'E7', 'F7', 'G7', 'H7', 'I7', 'J7', 'K7', 'L7', 'M7', 'N7', 'O7', 'B8', 'C8', 'D8', 'E8', 'F8', 'G8', 'H8', 'I8', 'J8', 'K8', 'L8', 'M8', 'N8', 'O8', 'B9', 'C9', 'D9', 'E9', 'F9', 'G9', 'H9', 'I9', 'J9', 'K9', 'L9', 'M9', 'N9', 'O9', 'B10', 'C10', 'D10', 'E10', 'F10', 'G10', 'H10', 'I10', 'J10', 'K10', 'L10', 'M10', 'N10', 'O10', 'B11', 'C11', 'D11', 'E11', 'F11', 'G11', 'H11', 'I11', 'J11', 'K11', 'L11', 'M11', 'N11', 'O11', 'B12', 'C12', 'D12', 'E12', 'F12', 'G12', 'H12', 'I12', 'J12', 'K12', 'L12', 'M12', 'N12', 'O12', 'B13', 'C13', 'D13', 'E13', 'F13', 'G13', 'H13', 'I13', 'J13', 'K13', 'L13', 'M13', 'N13', 'O13', 'B14', 'C14', 'D14', 'E14', 'F14', 'G14', 'H14', 'I14', 'J14', 'K14', 'L14', 'M14', 'N14', 'O14', 'B15', 'C15', 'D15', 'E15', 'F15', 'G15', 'H15', 'I15', 'J15', 'K15', 'L15', 'M15', 'N15', 'O15', 'B16', 'C16', 'D16', 'E16', 'F16', 'G16', 'H16', 'I16', 'J16', 'K16', 'L16', 'M16', 'N16', 'O16', 'B17', 'C17', 'D17', 'E17', 'F17', 'G17', 'H17', 'I17', 'J17', 'K17', 'L17', 'M17', 'N17', 'O17', 'B18', 'C18', 'D18', 'E18', 'F18', 'G18', 'H18', 'I18', 'J18', 'K18', 'L18', 'M18', 'N18', 'O18', 'B19', 'C19', 'D19', 'E19', 'F19', 'G19', 'H19', 'I19', 'J19', 'K19', 'L19', 'M19', 'N19', 'O19', 'B20', 'C20', 'D20', 'E20', 'F20', 'G20', 'H20', 'I20', 'J20', 'K20', 'L20', 'M20', 'N20', 'O20', 'B21', 'C21', 'D21', 'E21', 'F21', 'G21', 'H21', 'I21', 'J21', 'K21', 'L21', 'M21', 'N21', 'O21', 'B22', 'C22', 'D22', 'E22', 'F22', 'G22', 'H22', 'I22', 'J22', 'K22', 'L22', 'M22', 'N22', 'O22']}
    analysis = "single point"
    write_to_excel = True
    bio_sample_dict = None

    config = configparser.ConfigParser()
    config.read("config.ini")

    bio_plate_report_setup = {
        "well_states_report_method": {"original": config["Settings_bio"].
            getboolean("well_states_report_method_original"),
                                      "normalised": config["Settings_bio"].
                                          getboolean("well_states_report_method_normalised"),
                                      "pora": config["Settings_bio"].getboolean("well_states_report_method_pora"),
                                      "pora_internal": config["Settings_bio"].
                                          getboolean("well_states_report_method_pora_internal")},
        "well_states_report": {'sample': config["Settings_bio"].getboolean("plate_report_well_states_report_sample"),
                               'blank': config["Settings_bio"].getboolean("plate_report_well_states_report_blank"),
                               'max': config["Settings_bio"].getboolean("plate_report_well_states_report_max"),
                               'minimum': config["Settings_bio"].getboolean("plate_report_well_states_report_minimum"),
                               'positive': config["Settings_bio"].getboolean("plate_report_well_states_report_positive")
            ,
                               'negative': config["Settings_bio"].getboolean("plate_report_well_states_report_negative")
            ,
                               'empty': config["Settings_bio"].getboolean("plate_report_well_states_report_empty")},
        "calc_dict": {"original": {"use": config["Settings_bio"].getboolean("plate_report_calc_dict_original_use"),
                                   "avg": config["Settings_bio"].getboolean("plate_report_calc_dict_original_avg"),
                                   "stdev": config["Settings_bio"].getboolean("plate_report_calc_dict_original_stdev"),
                                   "pstdev": config["Settings_bio"].getboolean(
                                       "plate_report_calc_dict_original_pstdev"),
                                   "pvariance": config["Settings_bio"].getboolean(
                                       "plate_report_calc_dict_original_pvariance"),
                                   "variance": config["Settings_bio"].getboolean(
                                       "plate_report_calc_dict_original_variance"),
                                   "st_dev_%": config["Settings_bio"].getboolean(
                                       "plate_report_calc_dict_original_st_dev_%"),
                                   "state": {"sample": config["Settings_bio"].
                                       getboolean("plate_report_calc_dict_original_state_sample"),
                                             "minimum": config["Settings_bio"].
                                                 getboolean("plate_report_calc_dict_original_state_minimum"),
                                             "max": config["Settings_bio"].
                                                 getboolean("plate_report_calc_dict_original_state_max"),
                                             "empty": config["Settings_bio"].
                                                 getboolean("plate_report_calc_dict_original_state_empty"),
                                             "negative": config["Settings_bio"].
                                                 getboolean("plate_report_calc_dict_original_state_negative"),
                                             "positive": config["Settings_bio"].
                                                 getboolean("plate_report_calc_dict_original_state_positive"),
                                             "blank": config["Settings_bio"].
                                                 getboolean("plate_report_calc_dict_original_state_blank")}},
                      "normalised": {"use": config["Settings_bio"].getboolean("plate_report_calc_dict_normalised_use"),
                                     "avg": config["Settings_bio"].
                                         getboolean("plate_report_calc_dict_normalised_avg"),
                                     "stdev": config["Settings_bio"].
                                         getboolean("plate_report_calc_dict_normalised_stdev"),
                                     "pstdev": config["Settings_bio"].
                                         getboolean("plate_report_calc_dict_normalised_pstdev"),
                                     "pvariance": config["Settings_bio"].
                                         getboolean("plate_report_calc_dict_normalised_pvariance"),
                                     "variance": config["Settings_bio"].
                                         getboolean("plate_report_calc_dict_normalised_variance"),
                                     "st_dev_%": config["Settings_bio"].
                                         getboolean("plate_report_calc_dict_normalised_st_dev_%"),
                                     "state": {"sample": config["Settings_bio"].
                                         getboolean("plate_report_calc_dict_normalised_"
                                                    "state_sample"),
                                               "minimum": config["Settings_bio"].
                                                   getboolean("plate_report_calc_dict_normalised_"
                                                              "state_minimum"),
                                               "max": config["Settings_bio"].
                                                   getboolean("plate_report_calc_dict_normalised_"
                                                              "state_max"),
                                               "empty": config["Settings_bio"].
                                                   getboolean("plate_report_calc_dict_normalised_"
                                                              "state_empty"),
                                               "negative": config["Settings_bio"].
                                                   getboolean("plate_report_calc_dict_normalised_"
                                                              "state_negative"),
                                               "positive": config["Settings_bio"].
                                                   getboolean("plate_report_calc_dict_normalised_"
                                                              "state_positive"),
                                               "blank": config["Settings_bio"].
                                                   getboolean("plate_report_calc_dict_normalised_"
                                                              "state_blank")}},
                      "pora": {"use": config["Settings_bio"].getboolean("plate_report_calc_dict_pora_use"),
                               "avg": config["Settings_bio"].getboolean("plate_report_calc_dict_pora_avg"),
                               "stdev": config["Settings_bio"].getboolean("plate_report_calc_dict_pora_stdev"),
                               "pstdev": config["Settings_bio"].getboolean("plate_report_calc_dict_pora_pstdev"),
                               "pvariance": config["Settings_bio"].getboolean("plate_report_calc_dict_pora_pvariance"),
                               "variance": config["Settings_bio"].getboolean("plate_report_calc_dict_pora_variance"),
                               "st_dev_%": config["Settings_bio"].getboolean("plate_report_calc_dict_pora_st_dev_%"),
                               "state": {"sample": config["Settings_bio"].
                                   getboolean("plate_report_calc_dict_pora_state_sample"),
                                         "minimum": config["Settings_bio"].
                                             getboolean("plate_report_calc_dict_pora_state_minimum"),
                                         "max": config["Settings_bio"].getboolean(
                                             "plate_report_calc_dict_pora_state_max"),
                                         "empty": config["Settings_bio"].
                                             getboolean("plate_report_calc_dict_pora_state_empty"),
                                         "negative": config["Settings_bio"].
                                             getboolean("plate_report_calc_dict_pora_state_negative"),
                                         "positive": config["Settings_bio"].
                                             getboolean("plate_report_calc_dict_pora_state_positive"),
                                         "blank": config["Settings_bio"].
                                             getboolean("plate_report_calc_dict_pora_state_blank")}},
                      "pora_internal": {"use": config["Settings_bio"].
                          getboolean("plate_report_calc_dict_pora_internal_use"),
                                        "avg": config["Settings_bio"].
                                            getboolean("plate_report_calc_dict_pora_internal_avg"),
                                        "stdev": config["Settings_bio"].
                                            getboolean("plate_report_calc_dict_pora_internal_stdev"),
                                        "state": {"sample": config["Settings_bio"].
                                            getboolean("plate_report_calc_dict_pora_internal_state_sample"),
                                                  "minimum": config["Settings_bio"].
                                                      getboolean("plate_report_calc_dict_pora_internal_state_minimum"),
                                                  "max": config["Settings_bio"].
                                                      getboolean("plate_report_calc_dict_pora_internal_state_max"),
                                                  "empty": config["Settings_bio"].
                                                      getboolean("plate_report_calc_dict_pora_internal_state_empty"),
                                                  "negative": config["Settings_bio"].
                                                      getboolean("plate_report_calc_dict_pora_internal_state_negative"),
                                                  "positive": config["Settings_bio"].
                                                      getboolean("plate_report_calc_dict_pora_internal_state_positive"),
                                                  "blank": config["Settings_bio"].
                                                      getboolean("plate_report_calc_dict_pora_internal_state_blank")}},
                      "other": {"use": config["Settings_bio"].getboolean("plate_report_calc_dict_other_use"),
                                "calc": {"z_prime": config["Settings_bio"].
                                    getboolean("plate_report_calc_dict_other_calc_z_prime")}}},
        "plate_calc_dict": {
            "original": {"use": config["Settings_bio"].getboolean("plate_report_plate_calc_dict_original_use"),
                         "avg": config["Settings_bio"].getboolean("plate_report_plate_calc_dict_original_avg"),
                         "stdev": config["Settings_bio"].getboolean("plate_report_plate_calc_dict_original_stdev"),
                         "pstdev": config["Settings_bio"].getboolean("plate_report_plate_calc_dict_original_pstdev"),
                         "pvariance": config["Settings_bio"].getboolean(
                             "plate_report_plate_calc_dict_original_pvariance"),
                         "variance": config["Settings_bio"].getboolean(
                             "plate_report_plate_calc_dict_original_variance"),
                         "st_dev_%": config["Settings_bio"].getboolean(
                             "plate_report_plate_calc_dict_original_st_dev_%"),
                         "state": {"sample": config["Settings_bio"].
                             getboolean("plate_report_plate_calc_dict_original_state_sample"),
                                   "minimum": config["Settings_bio"].
                                       getboolean("plate_report_plate_calc_dict_original_state_minimum"),
                                   "max": config["Settings_bio"].
                                       getboolean("plate_report_plate_calc_dict_original_state_max"),
                                   "empty": config["Settings_bio"].
                                       getboolean("plate_report_plate_calc_dict_original_state_empty"),
                                   "negative": config["Settings_bio"].
                                       getboolean("plate_report_plate_calc_dict_original_state_negative"),
                                   "positive": config["Settings_bio"].
                                       getboolean("plate_report_plate_calc_dict_original_state_positive"),
                                   "blank": config["Settings_bio"].
                                       getboolean("plate_report_plate_calc_dict_original_state_blank")}},
            "normalised": {"use": config["Settings_bio"].getboolean("plate_report_plate_calc_dict_normalised_use"),
                           "avg": config["Settings_bio"].getboolean("plate_report_plate_calc_dict_normalised_avg"),
                           "stdev": config["Settings_bio"].getboolean("plate_report_plate_calc_dict_normalised_stdev"),
                           "pstdev": config["Settings_bio"].getboolean(
                               "plate_report_plate_calc_dict_normalised_pstdev"),
                           "pvariance": config["Settings_bio"].getboolean(
                               "plate_report_plate_calc_dict_normalised_pvariance"),
                           "variance": config["Settings_bio"].getboolean(
                               "plate_report_plate_calc_dict_normalised_variance"),
                           "st_dev_%": config["Settings_bio"].getboolean(
                               "plate_report_plate_calc_dict_normalised_st_dev_%"),
                           "state": {"sample": config["Settings_bio"].
                               getboolean("plate_report_plate_calc_dict_normalised_state_sample"),
                                     "minimum": config["Settings_bio"].
                                         getboolean("plate_report_plate_calc_dict_normalised_state_minimum"),
                                     "max": config["Settings_bio"].
                                         getboolean("plate_report_plate_calc_dict_normalised_state_max"),
                                     "empty": config["Settings_bio"].
                                         getboolean("plate_report_plate_calc_dict_normalised_state_empty"),
                                     "negative": config["Settings_bio"].
                                         getboolean("plate_report_plate_calc_dict_normalised_state_negative"),
                                     "positive": config["Settings_bio"].
                                         getboolean("plate_report_plate_calc_dict_normalised_state_positive"),
                                     "blank": config["Settings_bio"].
                                         getboolean("plate_report_plate_calc_dict_normalised_state_blank")}},
            "pora": {"use": config["Settings_bio"].getboolean("plate_report_plate_calc_dict_pora_use"),
                     "avg": config["Settings_bio"].getboolean("plate_report_plate_calc_dict_pora_avg"),
                     "stdev": config["Settings_bio"].getboolean("plate_report_plate_calc_dict_pora_stdev"),
                     "pstdev": config["Settings_bio"].getboolean("plate_report_plate_calc_dict_pora_pstdev"),
                     "pvariance": config["Settings_bio"].getboolean("plate_report_plate_calc_dict_pora_pvariance"),
                     "variance": config["Settings_bio"].getboolean("plate_report_plate_calc_dict_pora_variance"),
                     "st_dev_%": config["Settings_bio"].getboolean("plate_report_plate_calc_dict_pora_st_dev_%"),
                     "state": {"sample": config["Settings_bio"].
                         getboolean("plate_report_plate_calc_dict_pora_state_sample"),
                               "minimum": config["Settings_bio"].
                                   getboolean("plate_report_plate_calc_dict_pora_state_minimum"),
                               "max": config["Settings_bio"].
                                   getboolean("plate_report_plate_calc_dict_pora_state_max"),
                               "empty": config["Settings_bio"].
                                   getboolean("plate_report_plate_calc_dict_pora_state_empty"),
                               "negative": config["Settings_bio"].
                                   getboolean("plate_report_plate_calc_dict_pora_state_negative"),
                               "positive": config["Settings_bio"].
                                   getboolean("plate_report_plate_calc_dict_pora_state_positive"),
                               "blank": config["Settings_bio"].
                                   getboolean("plate_report_plate_calc_dict_pora_state_blank")}},
            "pora_internal": {"use": config["Settings_bio"].
                getboolean("plate_report_plate_calc_dict_pora_internal_use"),
                              "avg": config["Settings_bio"].
                                  getboolean("plate_report_plate_calc_dict_pora_internal_avg"),
                              "stdev": config["Settings_bio"].
                                  getboolean("plate_report_plate_calc_dict_pora_internal_stdev"),
                              "pstdev": config["Settings_bio"].
                                  getboolean("plate_report_plate_calc_dict_pora_internal_pstdev"),
                              "pvariance": config["Settings_bio"].
                                  getboolean("plate_report_plate_calc_dict_pora_internal_pvariance"),
                              "variance": config["Settings_bio"].
                                  getboolean("plate_report_plate_calc_dict_pora_internal_variance"),
                              "st_dev_%": config["Settings_bio"].
                                  getboolean("plate_report_plate_calc_dict_pora_internal_st_dev_%"),
                              "state": {"sample": config["Settings_bio"].
                                  getboolean("plate_report_plate_calc_dict_pora_internal_state_sample"),
                                        "minimum": config["Settings_bio"].
                                            getboolean("plate_report_plate_calc_dict_pora_internal_state_minimum"),
                                        "max": config["Settings_bio"].
                                            getboolean("plate_report_plate_calc_dict_pora_internal_state_max"),
                                        "empty": config["Settings_bio"].
                                            getboolean("plate_report_plate_calc_dict_pora_internal_state_empty"),
                                        "negative": config["Settings_bio"].
                                            getboolean("plate_report_plate_calc_dict_pora_internal_state_negative"),
                                        "positive": config["Settings_bio"].
                                            getboolean("plate_report_plate_calc_dict_pora_internal_state_positive"),
                                        "blank": config["Settings_bio"].
                                            getboolean("plate_report_plate_calc_dict_pora_internal_state_blank")}},
        },
        "plate_analysis_dict": {"original": {"use": config["Settings_bio"].
            getboolean("plate_report_plate_analysis_dict_original_use"),
                                             "methode": org,
                                             "state_map": config["Settings_bio"].
                                                 getboolean("plate_report_plate_analysis_dict_original_state_map"),
                                             "heatmap": config["Settings_bio"].
                                                 getboolean("plate_report_plate_analysis_dict_original_heatmap"),
                                             "hit_map": config["Settings_bio"].
                                                 getboolean("plate_report_plate_analysis_dict_original_hit_map"),
                                             "none": config["Settings_bio"].
                                                 getboolean("plate_report_plate_analysis_dict_original_none")},
                                "normalised": {"use": config["Settings_bio"].
                                    getboolean("plate_report_plate_analysis_dict_normalised_use"),
                                               "methode": norm,
                                               "state_map": config["Settings_bio"].
                                                   getboolean("plate_report_plate_analysis_dict_normalised_state_map"),
                                               "heatmap": config["Settings_bio"].
                                                   getboolean("plate_report_plate_analysis_dict_normalised_heatmap"),
                                               "hit_map": config["Settings_bio"].
                                                   getboolean("plate_report_plate_analysis_dict_normalised_hit_map"),
                                               "none": config["Settings_bio"].
                                                   getboolean("plate_report_plate_analysis_dict_normalised_none")},
                                "pora": {"use": config["Settings_bio"].
                                    getboolean("plate_report_plate_analysis_dict_pora_use"),
                                         "methode": pora,
                                         "state_map": config["Settings_bio"].
                                             getboolean("plate_report_plate_analysis_dict_pora_state_map"),
                                         "heatmap": config["Settings_bio"].
                                             getboolean("plate_report_plate_analysis_dict_pora_heatmap"),
                                         "hit_map": config["Settings_bio"].
                                             getboolean("plate_report_plate_analysis_dict_pora_hit_map"),
                                         "none": config["Settings_bio"].
                                             getboolean("plate_report_plate_analysis_dict_pora_none")},
                                "pora_internal": {"use": config["Settings_bio"].
                                    getboolean("plate_report_plate_analysis_dict_pora_internal_use"),
                                                  "methode": pora_internal,
                                                  "state_map": config["Settings_bio"].
                                                      getboolean(
                                                      "plate_report_plate_analysis_dict_pora_internal_state_map")
                                    ,
                                                  "heatmap": config["Settings_bio"].
                                                      getboolean(
                                                      "plate_report_plate_analysis_dict_pora_internal_heatmap"),
                                                  "hit_map": config["Settings_bio"].
                                                      getboolean(
                                                      "plate_report_plate_analysis_dict_pora_internal_hit_map"),
                                                  "none": config["Settings_bio"].
                                                      getboolean("plate_report_plate_analysis_dict_pora_internal_none")}
                                },
        "z_prime_calc": config["Settings_bio"].getboolean("plate_report_z_prime_calc"),
        "heatmap_colours": {'low': config["Settings_bio"]["plate_report_heatmap_colours_low"],
                            'mid': config["Settings_bio"]["plate_report_heatmap_colours_mid"],
                            'high': config["Settings_bio"]["plate_report_heatmap_colours_high"]},
        "pora_threshold": {"th_1": {"min": config["Settings_bio"].getfloat("plate_report_pora_threshold_th_1_min"),
                                    "max": config["Settings_bio"].getfloat("plate_report_pora_threshold_th_1_max"),
                                    "use": config["Settings_bio"].getboolean("plate_report_pora_threshold_th_1_use")},
                           "th_2": {"min": config["Settings_bio"].getfloat("plate_report_pora_threshold_th_2_min"),
                                    "max": config["Settings_bio"].getfloat("plate_report_pora_threshold_th_2_max"),
                                    "use": config["Settings_bio"].getboolean("plate_report_pora_threshold_th_2_use")},
                           "th_3": {"min": config["Settings_bio"].getfloat("plate_report_pora_threshold_th_3_min"),
                                    "max": config["Settings_bio"].getfloat("plate_report_pora_threshold_th_3_max"),
                                    "use": config["Settings_bio"].getboolean("plate_report_pora_threshold_th_3_use")},
                           "th_4": {"min": config["Settings_bio"].getfloat("plate_report_pora_threshold_th_4_min"),
                                    "max": config["Settings_bio"].getfloat("plate_report_pora_threshold_th_4_max"),
                                    "use": config["Settings_bio"].getboolean("plate_report_pora_threshold_th_4_use")},
                           "th_5": {"min": config["Settings_bio"].getfloat("plate_report_pora_threshold_th_5_min"),
                                    "max": config["Settings_bio"].getfloat("plate_report_pora_threshold_th_5_max"),
                                    "use": config["Settings_bio"].getboolean("plate_report_pora_threshold_th_5_use")},
                           "th_6": {"min": config["Settings_bio"].getfloat("plate_report_pora_threshold_th_6_min"),
                                    "max": config["Settings_bio"].getfloat("plate_report_pora_threshold_th_6_max"),
                                    "use": config["Settings_bio"].getboolean("plate_report_pora_threshold_th_6_use")},
                           "th_7": {"min": config["Settings_bio"].getfloat("plate_report_pora_threshold_th_7_min"),
                                    "max": config["Settings_bio"].getfloat("plate_report_pora_threshold_th_7_max"),
                                    "use": config["Settings_bio"].getboolean("plate_report_pora_threshold_th_7_use")},
                           "th_8": {"min": config["Settings_bio"].getfloat("plate_report_pora_threshold_th_8_min"),
                                    "max": config["Settings_bio"].getfloat("plate_report_pora_threshold_th_8_max"),
                                    "use": config["Settings_bio"].getboolean("plate_report_pora_threshold_th_8_use")},
                           "th_9": {"min": config["Settings_bio"].getfloat("plate_report_pora_threshold_th_9_min"),
                                    "max": config["Settings_bio"].getfloat("plate_report_pora_threshold_th_9_max"),
                                    "use": config["Settings_bio"].getboolean("plate_report_pora_threshold_th_9_use")},
                           "th_10": {"min": config["Settings_bio"].getfloat("plate_report_pora_threshold_th_10_min"),
                                     "max": config["Settings_bio"].getfloat("plate_report_pora_threshold_th_10_max"),
                                     "use": config["Settings_bio"].getboolean("plate_report_pora_threshold_th_10_use")},
                           "colour": {"th_1": config["Settings_bio"]["plate_report_pora_threshold_colour_th_1"],
                                      "th_2": config["Settings_bio"]["plate_report_pora_threshold_colour_th_2"],
                                      "th_3": config["Settings_bio"]["plate_report_pora_threshold_colour_th_3"],
                                      "th_4": config["Settings_bio"]["plate_report_pora_threshold_colour_th_4"],
                                      "th_5": config["Settings_bio"]["plate_report_pora_threshold_colour_th_5"],
                                      "th_6": config["Settings_bio"]["plate_report_pora_threshold_colour_th_6"],
                                      "th_7": config["Settings_bio"]["plate_report_pora_threshold_colour_th_7"],
                                      "th_8": config["Settings_bio"]["plate_report_pora_threshold_colour_th_8"],
                                      "th_9": config["Settings_bio"]["plate_report_pora_threshold_colour_th_9"],
                                      "th_10": config["Settings_bio"]["plate_report_pora_threshold_colour_th_10"]}
                           }
    }

    bio = BIOAnalyser(config, bio_plate_report_setup)
    save_location = "C:/Users/phch/Desktop/more_data_files"
    bio.bio_data_controller(ex_file, plate_layout, all_data, well_row_col, well_type, analysis, write_to_excel,
                            bio_sample_dict, save_location)

    all_data = {'plates': {'original': {
        'wells': {'A1': 0.0003, 'B1': 0.0001, 'C1': 0.0002, 'D1': 0.0001, 'E1': 0.0001, 'F1': 0.0, 'G1': 0.0003,
                  'H1': 0.0001, 'I1': 0.0002, 'J1': 0.0001, 'K1': 0.0002, 'L1': 0.0003, 'M1': 0.0001, 'N1': 0.0,
                  'O1': 0.0, 'P1': 0.0, 'A2': 0.0001, 'P2': 0.0002, 'A3': 0.0, 'P3': 0.0, 'A4': 0.0001, 'P4': 0.0001,
                  'A5': 0.0, 'P5': 0.0001, 'A6': 0.0, 'P6': 0.0002, 'A7': 0.0001, 'P7': 0.0001, 'A8': 0.0001, 'P8': 0.0,
                  'A9': 0.0, 'P9': 0.0001, 'A10': 0.0, 'P10': 0.0, 'A11': 0.0001, 'P11': 0.0001, 'A12': 0.0001,
                  'P12': 0.0001, 'A13': 0.0001, 'P13': 0.0001, 'A14': 0.0003, 'P14': 0.0001, 'A15': -0.0001,
                  'P15': -0.0001, 'A16': 0.0, 'P16': 0.0, 'A17': 0.0001, 'P17': 0.0001, 'A18': 0.0001, 'P18': 0.0,
                  'A19': 0.0, 'P19': 0.0, 'A20': 0.0001, 'P20': 0.0, 'A21': 0.0001, 'P21': 0.0, 'A22': 0.0003,
                  'P22': 0.0, 'A23': 0.0001, 'B23': 0.0001, 'C23': 0.0, 'D23': 0.0, 'E23': 0.0002, 'F23': 0.0002,
                  'G23': 0.0002, 'H23': 0.0001, 'I23': 0.0001, 'J23': 0.0002, 'K23': -0.0001, 'L23': 0.0, 'M23': 0.0,
                  'N23': -0.0002, 'O23': 0.0, 'P23': -0.0001, 'A24': 0.0, 'B24': 0.0002, 'C24': -0.0001, 'D24': 0.0001,
                  'E24': 0.0001, 'F24': 0.0, 'G24': 0.0, 'H24': 0.0002, 'I24': 0.0001, 'J24': -0.0001, 'K24': 0.0,
                  'L24': 0.0, 'M24': 0.0, 'N24': 0.0001, 'O24': 0.0, 'P24': 0.0, 'B2': 0.0001, 'C2': 0.0, 'D2': 0.0001,
                  'E2': 0.0002, 'F2': 0.0002, 'G2': 0.0002, 'H2': 0.0001, 'I2': 0.0002, 'J2': 0.0004, 'K2': 0.0001,
                  'L2': 0.0001, 'M2': 0.0, 'N2': 0.0001, 'O2': 0.0002, 'B3': 0.0, 'C3': 0.0001, 'D3': 0.0001,
                  'E3': -0.0001, 'F3': 0.0001, 'G3': 0.0, 'H3': 0.0001, 'I3': 0.0001, 'J3': 0.0, 'K3': 0.0001,
                  'L3': 0.0001, 'M3': 0.0001, 'N3': 0.0001, 'O3': 0.0001, 'B4': 0.0, 'C4': 0.0001, 'D4': 0.0001,
                  'E4': 0.0, 'F4': 0.0001, 'G4': 0.0001, 'H4': 0.0002, 'I4': -0.0001, 'J4': 0.0001, 'K4': 0.0001,
                  'L4': 0.0001, 'M4': 0.0, 'N4': -0.0001, 'O4': 0.0, 'B5': 0.0001, 'C5': 0.0, 'D5': 0.0, 'E5': 0.0001,
                  'F5': 0.0001, 'G5': 0.0001, 'H5': 0.0, 'I5': 0.0002, 'J5': 0.0001, 'K5': 0.0, 'L5': 0.0001, 'M5': 0.0,
                  'N5': 0.0001, 'O5': 0.0, 'B6': 0.0, 'C6': 0.0001, 'D6': 0.0, 'E6': 0.0002, 'F6': 0.0, 'G6': 0.0001,
                  'H6': 0.0, 'I6': 0.0001, 'J6': 0.0001, 'K6': 0.0, 'L6': 0.0001, 'M6': 0.0001, 'N6': 0.0001, 'O6': 0.0,
                  'B7': 0.0001, 'C7': 0.0, 'D7': -0.0001, 'E7': 0.0, 'F7': 0.0001, 'G7': 0.0001, 'H7': 0.0,
                  'I7': 0.0001, 'J7': 0.0002, 'K7': 0.0001, 'L7': 0.0001, 'M7': 0.0, 'N7': 0.0, 'O7': 0.0, 'B8': 0.0002,
                  'C8': 0.0002, 'D8': 0.0001, 'E8': 0.0001, 'F8': 0.0003, 'G8': 0.0001, 'H8': 0.0001, 'I8': 0.0,
                  'J8': 0.0, 'K8': 0.0, 'L8': 0.0001, 'M8': 0.0, 'N8': 0.0, 'O8': 0.0002, 'B9': 0.0002, 'C9': 0.0001,
                  'D9': 0.0002, 'E9': 0.0001, 'F9': 0.0, 'G9': 0.0, 'H9': 0.0001, 'I9': 0.0002, 'J9': 0.0002,
                  'K9': 0.0001, 'L9': 0.0002, 'M9': -0.0001, 'N9': 0.0003, 'O9': 0.0, 'B10': 0.0001, 'C10': 0.0002,
                  'D10': 0.0, 'E10': 0.0001, 'F10': 0.0001, 'G10': 0.0, 'H10': 0.0002, 'I10': 0.0, 'J10': 0.0001,
                  'K10': 0.0001, 'L10': -0.0002, 'M10': 0.0, 'N10': 0.0, 'O10': 0.0001, 'B11': 0.0001, 'C11': 0.0001,
                  'D11': 0.0002, 'E11': 0.0001, 'F11': 0.0003, 'G11': 0.0, 'H11': 0.0003, 'I11': 0.0001, 'J11': 0.0001,
                  'K11': 0.0001, 'L11': 0.0, 'M11': 0.0, 'N11': 0.0001, 'O11': 0.0, 'B12': 0.0001, 'C12': 0.0001,
                  'D12': 0.0002, 'E12': 0.0, 'F12': 0.0002, 'G12': 0.0002, 'H12': 0.0, 'I12': 0.0, 'J12': 0.0001,
                  'K12': 0.0003, 'L12': 0.0001, 'M12': 0.0001, 'N12': 0.0, 'O12': 0.0, 'B13': 0.0001, 'C13': 0.0,
                  'D13': 0.0, 'E13': 0.0, 'F13': 0.0, 'G13': 0.0, 'H13': 0.0002, 'I13': 0.0, 'J13': 0.0001,
                  'K13': 0.0001, 'L13': 0.0003, 'M13': 0.0, 'N13': 0.0, 'O13': 0.0002, 'B14': 0.0001, 'C14': 0.0002,
                  'D14': 0.0002, 'E14': 0.0001, 'F14': 0.0001, 'G14': 0.0002, 'H14': 0.0002, 'I14': 0.0003,
                  'J14': 0.0003, 'K14': 0.0001, 'L14': 0.0001, 'M14': -0.0001, 'N14': 0.0, 'O14': 0.0001, 'B15': 0.0001,
                  'C15': 0.0, 'D15': 0.0002, 'E15': 0.0001, 'F15': 0.0001, 'G15': 0.0002, 'H15': 0.0002, 'I15': 0.0001,
                  'J15': 0.0002, 'K15': 0.0001, 'L15': 0.0, 'M15': 0.0, 'N15': 0.0001, 'O15': 0.0, 'B16': 0.0001,
                  'C16': 0.0, 'D16': 0.0, 'E16': 0.0001, 'F16': 0.0001, 'G16': 0.0001, 'H16': 0.0, 'I16': 0.0001,
                  'J16': 0.0, 'K16': 0.0001, 'L16': 0.0, 'M16': -0.0001, 'N16': -0.0001, 'O16': 0.0002, 'B17': 0.0,
                  'C17': 0.0001, 'D17': 0.0001, 'E17': 0.0001, 'F17': 0.0002, 'G17': 0.0, 'H17': 0.0001, 'I17': 0.0,
                  'J17': 0.0, 'K17': 0.0, 'L17': 0.0002, 'M17': 0.0, 'N17': -0.0001, 'O17': 0.0, 'B18': 0.0,
                  'C18': 0.0001, 'D18': 0.0001, 'E18': 0.0001, 'F18': 0.0001, 'G18': 0.0, 'H18': 0.0, 'I18': 0.0002,
                  'J18': 0.0002, 'K18': 0.0001, 'L18': 0.0003, 'M18': 0.0, 'N18': 0.0001, 'O18': 0.0001, 'B19': 0.0001,
                  'C19': 0.0002, 'D19': 0.0001, 'E19': 0.0, 'F19': 0.0001, 'G19': 0.0001, 'H19': 0.0002, 'I19': 0.0001,
                  'J19': 0.0001, 'K19': 0.0001, 'L19': 0.0001, 'M19': 0.0002, 'N19': 0.0, 'O19': 0.0001, 'B20': 0.0001,
                  'C20': 0.0001, 'D20': 0.0003, 'E20': 0.0001, 'F20': 0.0001, 'G20': 0.0001, 'H20': 0.0002,
                  'I20': 0.0001, 'J20': 0.0001, 'K20': 0.0001, 'L20': 0.0, 'M20': 0.0, 'N20': 0.0001, 'O20': 0.0001,
                  'B21': 0.0001, 'C21': 0.0001, 'D21': 0.0, 'E21': 0.0, 'F21': 0.0002, 'G21': 0.0002, 'H21': 0.0,
                  'I21': 0.0, 'J21': 0.0, 'K21': 0.0001, 'L21': 0.0, 'M21': 0.0, 'N21': 0.0, 'O21': 0.0001,
                  'B22': 0.0002, 'C22': 0.0001, 'D22': -0.0001, 'E22': 0.0, 'F22': 0.0002, 'G22': 0.0001, 'H22': 0.0001,
                  'I22': 0.0002, 'J22': -0.0001, 'K22': 0.0002, 'L22': 0.0004, 'M22': 0.0, 'N22': 0.0001,
                  'O22': 0.0002},
        'empty': ['A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1', 'H1', 'I1', 'J1', 'K1', 'L1', 'M1', 'N1', 'O1', 'P1', 'A2',
                  'P2', 'A3', 'P3', 'A4', 'P4', 'A5', 'P5', 'A6', 'P6', 'A7', 'P7', 'A8', 'P8', 'A9', 'P9', 'A10',
                  'P10', 'A11', 'P11', 'A12', 'P12', 'A13', 'P13', 'A14', 'P14', 'A15', 'P15', 'A16', 'P16', 'A17',
                  'P17', 'A18', 'P18', 'A19', 'P19', 'A20', 'P20', 'A21', 'P21', 'A22', 'P22', 'A23', 'B23', 'C23',
                  'D23', 'E23', 'F23', 'G23', 'H23', 'I23', 'J23', 'K23', 'L23', 'M23', 'N23', 'O23', 'P23', 'A24',
                  'B24', 'C24', 'D24', 'E24', 'F24', 'G24', 'H24', 'I24', 'J24', 'K24', 'L24', 'M24', 'N24', 'O24',
                  'P24'],
        'minimum': ['B2', 'C2', 'D2', 'E2', 'F2', 'G2', 'H2', 'I2', 'J2', 'K2', 'L2', 'M2', 'N2', 'O2'],
        'max': ['B3', 'C3', 'D3', 'E3', 'F3', 'G3', 'H3', 'I3', 'J3', 'K3', 'L3', 'M3', 'N3', 'O3'],
        'sample': ['B4', 'C4', 'D4', 'E4', 'F4', 'G4', 'H4', 'I4', 'J4', 'K4', 'L4', 'M4', 'N4', 'O4', 'B5', 'C5', 'D5',
                   'E5', 'F5', 'G5', 'H5', 'I5', 'J5', 'K5', 'L5', 'M5', 'N5', 'O5', 'B6', 'C6', 'D6', 'E6', 'F6', 'G6',
                   'H6', 'I6', 'J6', 'K6', 'L6', 'M6', 'N6', 'O6', 'B7', 'C7', 'D7', 'E7', 'F7', 'G7', 'H7', 'I7', 'J7',
                   'K7', 'L7', 'M7', 'N7', 'O7', 'B8', 'C8', 'D8', 'E8', 'F8', 'G8', 'H8', 'I8', 'J8', 'K8', 'L8', 'M8',
                   'N8', 'O8', 'B9', 'C9', 'D9', 'E9', 'F9', 'G9', 'H9', 'I9', 'J9', 'K9', 'L9', 'M9', 'N9', 'O9',
                   'B10', 'C10', 'D10', 'E10', 'F10', 'G10', 'H10', 'I10', 'J10', 'K10', 'L10', 'M10', 'N10', 'O10',
                   'B11', 'C11', 'D11', 'E11', 'F11', 'G11', 'H11', 'I11', 'J11', 'K11', 'L11', 'M11', 'N11', 'O11',
                   'B12', 'C12', 'D12', 'E12', 'F12', 'G12', 'H12', 'I12', 'J12', 'K12', 'L12', 'M12', 'N12', 'O12',
                   'B13', 'C13', 'D13', 'E13', 'F13', 'G13', 'H13', 'I13', 'J13', 'K13', 'L13', 'M13', 'N13', 'O13',
                   'B14', 'C14', 'D14', 'E14', 'F14', 'G14', 'H14', 'I14', 'J14', 'K14', 'L14', 'M14', 'N14', 'O14',
                   'B15', 'C15', 'D15', 'E15', 'F15', 'G15', 'H15', 'I15', 'J15', 'K15', 'L15', 'M15', 'N15', 'O15',
                   'B16', 'C16', 'D16', 'E16', 'F16', 'G16', 'H16', 'I16', 'J16', 'K16', 'L16', 'M16', 'N16', 'O16',
                   'B17', 'C17', 'D17', 'E17', 'F17', 'G17', 'H17', 'I17', 'J17', 'K17', 'L17', 'M17', 'N17', 'O17',
                   'B18', 'C18', 'D18', 'E18', 'F18', 'G18', 'H18', 'I18', 'J18', 'K18', 'L18', 'M18', 'N18', 'O18',
                   'B19', 'C19', 'D19', 'E19', 'F19', 'G19', 'H19', 'I19', 'J19', 'K19', 'L19', 'M19', 'N19', 'O19',
                   'B20', 'C20', 'D20', 'E20', 'F20', 'G20', 'H20', 'I20', 'J20', 'K20', 'L20', 'M20', 'N20', 'O20',
                   'B21', 'C21', 'D21', 'E21', 'F21', 'G21', 'H21', 'I21', 'J21', 'K21', 'L21', 'M21', 'N21', 'O21',
                   'B22', 'C22', 'D22', 'E22', 'F22', 'G22', 'H22', 'I22', 'J22', 'K22', 'L22', 'M22', 'N22', 'O22']},
                'normalised': {
                    'wells': {'A1': 0.0001571428571428571, 'B1': -4.285714285714286e-05, 'C1': 5.714285714285714e-05,
                              'D1': -4.285714285714286e-05, 'E1': -4.285714285714286e-05, 'F1': -0.00014285714285714287,
                              'G1': 0.0001571428571428571, 'H1': -4.285714285714286e-05, 'I1': 5.714285714285714e-05,
                              'J1': -4.285714285714286e-05, 'K1': 5.714285714285714e-05, 'L1': 0.0001571428571428571,
                              'M1': -4.285714285714286e-05, 'N1': -0.00014285714285714287,
                              'O1': -0.00014285714285714287, 'P1': -0.00014285714285714287,
                              'A2': -4.285714285714286e-05, 'P2': 5.714285714285714e-05, 'A3': -0.00014285714285714287,
                              'P3': -0.00014285714285714287, 'A4': -4.285714285714286e-05, 'P4': -4.285714285714286e-05,
                              'A5': -0.00014285714285714287, 'P5': -4.285714285714286e-05,
                              'A6': -0.00014285714285714287, 'P6': 5.714285714285714e-05, 'A7': -4.285714285714286e-05,
                              'P7': -4.285714285714286e-05, 'A8': -4.285714285714286e-05, 'P8': -0.00014285714285714287,
                              'A9': -0.00014285714285714287, 'P9': -4.285714285714286e-05,
                              'A10': -0.00014285714285714287, 'P10': -0.00014285714285714287,
                              'A11': -4.285714285714286e-05, 'P11': -4.285714285714286e-05,
                              'A12': -4.285714285714286e-05, 'P12': -4.285714285714286e-05,
                              'A13': -4.285714285714286e-05, 'P13': -4.285714285714286e-05,
                              'A14': 0.0001571428571428571, 'P14': -4.285714285714286e-05,
                              'A15': -0.00024285714285714286, 'P15': -0.00024285714285714286,
                              'A16': -0.00014285714285714287, 'P16': -0.00014285714285714287,
                              'A17': -4.285714285714286e-05, 'P17': -4.285714285714286e-05,
                              'A18': -4.285714285714286e-05, 'P18': -0.00014285714285714287,
                              'A19': -0.00014285714285714287, 'P19': -0.00014285714285714287,
                              'A20': -4.285714285714286e-05, 'P20': -0.00014285714285714287,
                              'A21': -4.285714285714286e-05, 'P21': -0.00014285714285714287,
                              'A22': 0.0001571428571428571, 'P22': -0.00014285714285714287,
                              'A23': -4.285714285714286e-05, 'B23': -4.285714285714286e-05,
                              'C23': -0.00014285714285714287, 'D23': -0.00014285714285714287,
                              'E23': 5.714285714285714e-05, 'F23': 5.714285714285714e-05, 'G23': 5.714285714285714e-05,
                              'H23': -4.285714285714286e-05, 'I23': -4.285714285714286e-05,
                              'J23': 5.714285714285714e-05, 'K23': -0.00024285714285714286,
                              'L23': -0.00014285714285714287, 'M23': -0.00014285714285714287,
                              'N23': -0.0003428571428571429, 'O23': -0.00014285714285714287,
                              'P23': -0.00024285714285714286, 'A24': -0.00014285714285714287,
                              'B24': 5.714285714285714e-05, 'C24': -0.00024285714285714286,
                              'D24': -4.285714285714286e-05, 'E24': -4.285714285714286e-05,
                              'F24': -0.00014285714285714287, 'G24': -0.00014285714285714287,
                              'H24': 5.714285714285714e-05, 'I24': -4.285714285714286e-05,
                              'J24': -0.00024285714285714286, 'K24': -0.00014285714285714287,
                              'L24': -0.00014285714285714287, 'M24': -0.00014285714285714287,
                              'N24': -4.285714285714286e-05, 'O24': -0.00014285714285714287,
                              'P24': -0.00014285714285714287, 'B2': -4.285714285714286e-05,
                              'C2': -0.00014285714285714287, 'D2': -4.285714285714286e-05, 'E2': 5.714285714285714e-05,
                              'F2': 5.714285714285714e-05, 'G2': 5.714285714285714e-05, 'H2': -4.285714285714286e-05,
                              'I2': 5.714285714285714e-05, 'J2': 0.00025714285714285715, 'K2': -4.285714285714286e-05,
                              'L2': -4.285714285714286e-05, 'M2': -0.00014285714285714287, 'N2': -4.285714285714286e-05,
                              'O2': 5.714285714285714e-05, 'B3': -0.00014285714285714287, 'C3': -4.285714285714286e-05,
                              'D3': -4.285714285714286e-05, 'E3': -0.00024285714285714286, 'F3': -4.285714285714286e-05,
                              'G3': -0.00014285714285714287, 'H3': -4.285714285714286e-05, 'I3': -4.285714285714286e-05,
                              'J3': -0.00014285714285714287, 'K3': -4.285714285714286e-05, 'L3': -4.285714285714286e-05,
                              'M3': -4.285714285714286e-05, 'N3': -4.285714285714286e-05, 'O3': -4.285714285714286e-05,
                              'B4': -0.00014285714285714287, 'C4': -4.285714285714286e-05, 'D4': -4.285714285714286e-05,
                              'E4': -0.00014285714285714287, 'F4': -4.285714285714286e-05, 'G4': -4.285714285714286e-05,
                              'H4': 5.714285714285714e-05, 'I4': -0.00024285714285714286, 'J4': -4.285714285714286e-05,
                              'K4': -4.285714285714286e-05, 'L4': -4.285714285714286e-05, 'M4': -0.00014285714285714287,
                              'N4': -0.00024285714285714286, 'O4': -0.00014285714285714287,
                              'B5': -4.285714285714286e-05, 'C5': -0.00014285714285714287,
                              'D5': -0.00014285714285714287, 'E5': -4.285714285714286e-05, 'F5': -4.285714285714286e-05,
                              'G5': -4.285714285714286e-05, 'H5': -0.00014285714285714287, 'I5': 5.714285714285714e-05,
                              'J5': -4.285714285714286e-05, 'K5': -0.00014285714285714287, 'L5': -4.285714285714286e-05,
                              'M5': -0.00014285714285714287, 'N5': -4.285714285714286e-05,
                              'O5': -0.00014285714285714287, 'B6': -0.00014285714285714287,
                              'C6': -4.285714285714286e-05, 'D6': -0.00014285714285714287, 'E6': 5.714285714285714e-05,
                              'F6': -0.00014285714285714287, 'G6': -4.285714285714286e-05,
                              'H6': -0.00014285714285714287, 'I6': -4.285714285714286e-05, 'J6': -4.285714285714286e-05,
                              'K6': -0.00014285714285714287, 'L6': -4.285714285714286e-05, 'M6': -4.285714285714286e-05,
                              'N6': -4.285714285714286e-05, 'O6': -0.00014285714285714287, 'B7': -4.285714285714286e-05,
                              'C7': -0.00014285714285714287, 'D7': -0.00024285714285714286,
                              'E7': -0.00014285714285714287, 'F7': -4.285714285714286e-05, 'G7': -4.285714285714286e-05,
                              'H7': -0.00014285714285714287, 'I7': -4.285714285714286e-05, 'J7': 5.714285714285714e-05,
                              'K7': -4.285714285714286e-05, 'L7': -4.285714285714286e-05, 'M7': -0.00014285714285714287,
                              'N7': -0.00014285714285714287, 'O7': -0.00014285714285714287, 'B8': 5.714285714285714e-05,
                              'C8': 5.714285714285714e-05, 'D8': -4.285714285714286e-05, 'E8': -4.285714285714286e-05,
                              'F8': 0.0001571428571428571, 'G8': -4.285714285714286e-05, 'H8': -4.285714285714286e-05,
                              'I8': -0.00014285714285714287, 'J8': -0.00014285714285714287,
                              'K8': -0.00014285714285714287, 'L8': -4.285714285714286e-05,
                              'M8': -0.00014285714285714287, 'N8': -0.00014285714285714287, 'O8': 5.714285714285714e-05,
                              'B9': 5.714285714285714e-05, 'C9': -4.285714285714286e-05, 'D9': 5.714285714285714e-05,
                              'E9': -4.285714285714286e-05, 'F9': -0.00014285714285714287,
                              'G9': -0.00014285714285714287, 'H9': -4.285714285714286e-05, 'I9': 5.714285714285714e-05,
                              'J9': 5.714285714285714e-05, 'K9': -4.285714285714286e-05, 'L9': 5.714285714285714e-05,
                              'M9': -0.00024285714285714286, 'N9': 0.0001571428571428571, 'O9': -0.00014285714285714287,
                              'B10': -4.285714285714286e-05, 'C10': 5.714285714285714e-05,
                              'D10': -0.00014285714285714287, 'E10': -4.285714285714286e-05,
                              'F10': -4.285714285714286e-05, 'G10': -0.00014285714285714287,
                              'H10': 5.714285714285714e-05, 'I10': -0.00014285714285714287,
                              'J10': -4.285714285714286e-05, 'K10': -4.285714285714286e-05,
                              'L10': -0.0003428571428571429, 'M10': -0.00014285714285714287,
                              'N10': -0.00014285714285714287, 'O10': -4.285714285714286e-05,
                              'B11': -4.285714285714286e-05, 'C11': -4.285714285714286e-05,
                              'D11': 5.714285714285714e-05, 'E11': -4.285714285714286e-05, 'F11': 0.0001571428571428571,
                              'G11': -0.00014285714285714287, 'H11': 0.0001571428571428571,
                              'I11': -4.285714285714286e-05, 'J11': -4.285714285714286e-05,
                              'K11': -4.285714285714286e-05, 'L11': -0.00014285714285714287,
                              'M11': -0.00014285714285714287, 'N11': -4.285714285714286e-05,
                              'O11': -0.00014285714285714287, 'B12': -4.285714285714286e-05,
                              'C12': -4.285714285714286e-05, 'D12': 5.714285714285714e-05,
                              'E12': -0.00014285714285714287, 'F12': 5.714285714285714e-05,
                              'G12': 5.714285714285714e-05, 'H12': -0.00014285714285714287,
                              'I12': -0.00014285714285714287, 'J12': -4.285714285714286e-05,
                              'K12': 0.0001571428571428571, 'L12': -4.285714285714286e-05,
                              'M12': -4.285714285714286e-05, 'N12': -0.00014285714285714287,
                              'O12': -0.00014285714285714287, 'B13': -4.285714285714286e-05,
                              'C13': -0.00014285714285714287, 'D13': -0.00014285714285714287,
                              'E13': -0.00014285714285714287, 'F13': -0.00014285714285714287,
                              'G13': -0.00014285714285714287, 'H13': 5.714285714285714e-05,
                              'I13': -0.00014285714285714287, 'J13': -4.285714285714286e-05,
                              'K13': -4.285714285714286e-05, 'L13': 0.0001571428571428571,
                              'M13': -0.00014285714285714287, 'N13': -0.00014285714285714287,
                              'O13': 5.714285714285714e-05, 'B14': -4.285714285714286e-05, 'C14': 5.714285714285714e-05,
                              'D14': 5.714285714285714e-05, 'E14': -4.285714285714286e-05,
                              'F14': -4.285714285714286e-05, 'G14': 5.714285714285714e-05, 'H14': 5.714285714285714e-05,
                              'I14': 0.0001571428571428571, 'J14': 0.0001571428571428571, 'K14': -4.285714285714286e-05,
                              'L14': -4.285714285714286e-05, 'M14': -0.00024285714285714286,
                              'N14': -0.00014285714285714287, 'O14': -4.285714285714286e-05,
                              'B15': -4.285714285714286e-05, 'C15': -0.00014285714285714287,
                              'D15': 5.714285714285714e-05, 'E15': -4.285714285714286e-05,
                              'F15': -4.285714285714286e-05, 'G15': 5.714285714285714e-05, 'H15': 5.714285714285714e-05,
                              'I15': -4.285714285714286e-05, 'J15': 5.714285714285714e-05,
                              'K15': -4.285714285714286e-05, 'L15': -0.00014285714285714287,
                              'M15': -0.00014285714285714287, 'N15': -4.285714285714286e-05,
                              'O15': -0.00014285714285714287, 'B16': -4.285714285714286e-05,
                              'C16': -0.00014285714285714287, 'D16': -0.00014285714285714287,
                              'E16': -4.285714285714286e-05, 'F16': -4.285714285714286e-05,
                              'G16': -4.285714285714286e-05, 'H16': -0.00014285714285714287,
                              'I16': -4.285714285714286e-05, 'J16': -0.00014285714285714287,
                              'K16': -4.285714285714286e-05, 'L16': -0.00014285714285714287,
                              'M16': -0.00024285714285714286, 'N16': -0.00024285714285714286,
                              'O16': 5.714285714285714e-05, 'B17': -0.00014285714285714287,
                              'C17': -4.285714285714286e-05, 'D17': -4.285714285714286e-05,
                              'E17': -4.285714285714286e-05, 'F17': 5.714285714285714e-05,
                              'G17': -0.00014285714285714287, 'H17': -4.285714285714286e-05,
                              'I17': -0.00014285714285714287, 'J17': -0.00014285714285714287,
                              'K17': -0.00014285714285714287, 'L17': 5.714285714285714e-05,
                              'M17': -0.00014285714285714287, 'N17': -0.00024285714285714286,
                              'O17': -0.00014285714285714287, 'B18': -0.00014285714285714287,
                              'C18': -4.285714285714286e-05, 'D18': -4.285714285714286e-05,
                              'E18': -4.285714285714286e-05, 'F18': -4.285714285714286e-05,
                              'G18': -0.00014285714285714287, 'H18': -0.00014285714285714287,
                              'I18': 5.714285714285714e-05, 'J18': 5.714285714285714e-05, 'K18': -4.285714285714286e-05,
                              'L18': 0.0001571428571428571, 'M18': -0.00014285714285714287,
                              'N18': -4.285714285714286e-05, 'O18': -4.285714285714286e-05,
                              'B19': -4.285714285714286e-05, 'C19': 5.714285714285714e-05,
                              'D19': -4.285714285714286e-05, 'E19': -0.00014285714285714287,
                              'F19': -4.285714285714286e-05, 'G19': -4.285714285714286e-05,
                              'H19': 5.714285714285714e-05, 'I19': -4.285714285714286e-05,
                              'J19': -4.285714285714286e-05, 'K19': -4.285714285714286e-05,
                              'L19': -4.285714285714286e-05, 'M19': 5.714285714285714e-05,
                              'N19': -0.00014285714285714287, 'O19': -4.285714285714286e-05,
                              'B20': -4.285714285714286e-05, 'C20': -4.285714285714286e-05,
                              'D20': 0.0001571428571428571, 'E20': -4.285714285714286e-05,
                              'F20': -4.285714285714286e-05, 'G20': -4.285714285714286e-05,
                              'H20': 5.714285714285714e-05, 'I20': -4.285714285714286e-05,
                              'J20': -4.285714285714286e-05, 'K20': -4.285714285714286e-05,
                              'L20': -0.00014285714285714287, 'M20': -0.00014285714285714287,
                              'N20': -4.285714285714286e-05, 'O20': -4.285714285714286e-05,
                              'B21': -4.285714285714286e-05, 'C21': -4.285714285714286e-05,
                              'D21': -0.00014285714285714287, 'E21': -0.00014285714285714287,
                              'F21': 5.714285714285714e-05, 'G21': 5.714285714285714e-05,
                              'H21': -0.00014285714285714287, 'I21': -0.00014285714285714287,
                              'J21': -0.00014285714285714287, 'K21': -4.285714285714286e-05,
                              'L21': -0.00014285714285714287, 'M21': -0.00014285714285714287,
                              'N21': -0.00014285714285714287, 'O21': -4.285714285714286e-05,
                              'B22': 5.714285714285714e-05, 'C22': -4.285714285714286e-05,
                              'D22': -0.00024285714285714286, 'E22': -0.00014285714285714287,
                              'F22': 5.714285714285714e-05, 'G22': -4.285714285714286e-05,
                              'H22': -4.285714285714286e-05, 'I22': 5.714285714285714e-05,
                              'J22': -0.00024285714285714286, 'K22': 5.714285714285714e-05,
                              'L22': 0.00025714285714285715, 'M22': -0.00014285714285714287,
                              'N22': -4.285714285714286e-05, 'O22': 5.714285714285714e-05},
                    'empty': ['A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1', 'H1', 'I1', 'J1', 'K1', 'L1', 'M1', 'N1', 'O1',
                              'P1', 'A2', 'P2', 'A3', 'P3', 'A4', 'P4', 'A5', 'P5', 'A6', 'P6', 'A7', 'P7', 'A8', 'P8',
                              'A9', 'P9', 'A10', 'P10', 'A11', 'P11', 'A12', 'P12', 'A13', 'P13', 'A14', 'P14', 'A15',
                              'P15', 'A16', 'P16', 'A17', 'P17', 'A18', 'P18', 'A19', 'P19', 'A20', 'P20', 'A21', 'P21',
                              'A22', 'P22', 'A23', 'B23', 'C23', 'D23', 'E23', 'F23', 'G23', 'H23', 'I23', 'J23', 'K23',
                              'L23', 'M23', 'N23', 'O23', 'P23', 'A24', 'B24', 'C24', 'D24', 'E24', 'F24', 'G24', 'H24',
                              'I24', 'J24', 'K24', 'L24', 'M24', 'N24', 'O24', 'P24'],
                    'minimum': ['B2', 'C2', 'D2', 'E2', 'F2', 'G2', 'H2', 'I2', 'J2', 'K2', 'L2', 'M2', 'N2', 'O2'],
                    'max': ['B3', 'C3', 'D3', 'E3', 'F3', 'G3', 'H3', 'I3', 'J3', 'K3', 'L3', 'M3', 'N3', 'O3'],
                    'sample': ['B4', 'C4', 'D4', 'E4', 'F4', 'G4', 'H4', 'I4', 'J4', 'K4', 'L4', 'M4', 'N4', 'O4', 'B5',
                               'C5', 'D5', 'E5', 'F5', 'G5', 'H5', 'I5', 'J5', 'K5', 'L5', 'M5', 'N5', 'O5', 'B6', 'C6',
                               'D6', 'E6', 'F6', 'G6', 'H6', 'I6', 'J6', 'K6', 'L6', 'M6', 'N6', 'O6', 'B7', 'C7', 'D7',
                               'E7', 'F7', 'G7', 'H7', 'I7', 'J7', 'K7', 'L7', 'M7', 'N7', 'O7', 'B8', 'C8', 'D8', 'E8',
                               'F8', 'G8', 'H8', 'I8', 'J8', 'K8', 'L8', 'M8', 'N8', 'O8', 'B9', 'C9', 'D9', 'E9', 'F9',
                               'G9', 'H9', 'I9', 'J9', 'K9', 'L9', 'M9', 'N9', 'O9', 'B10', 'C10', 'D10', 'E10', 'F10',
                               'G10', 'H10', 'I10', 'J10', 'K10', 'L10', 'M10', 'N10', 'O10', 'B11', 'C11', 'D11',
                               'E11', 'F11', 'G11', 'H11', 'I11', 'J11', 'K11', 'L11', 'M11', 'N11', 'O11', 'B12',
                               'C12', 'D12', 'E12', 'F12', 'G12', 'H12', 'I12', 'J12', 'K12', 'L12', 'M12', 'N12',
                               'O12', 'B13', 'C13', 'D13', 'E13', 'F13', 'G13', 'H13', 'I13', 'J13', 'K13', 'L13',
                               'M13', 'N13', 'O13', 'B14', 'C14', 'D14', 'E14', 'F14', 'G14', 'H14', 'I14', 'J14',
                               'K14', 'L14', 'M14', 'N14', 'O14', 'B15', 'C15', 'D15', 'E15', 'F15', 'G15', 'H15',
                               'I15', 'J15', 'K15', 'L15', 'M15', 'N15', 'O15', 'B16', 'C16', 'D16', 'E16', 'F16',
                               'G16', 'H16', 'I16', 'J16', 'K16', 'L16', 'M16', 'N16', 'O16', 'B17', 'C17', 'D17',
                               'E17', 'F17', 'G17', 'H17', 'I17', 'J17', 'K17', 'L17', 'M17', 'N17', 'O17', 'B18',
                               'C18', 'D18', 'E18', 'F18', 'G18', 'H18', 'I18', 'J18', 'K18', 'L18', 'M18', 'N18',
                               'O18', 'B19', 'C19', 'D19', 'E19', 'F19', 'G19', 'H19', 'I19', 'J19', 'K19', 'L19',
                               'M19', 'N19', 'O19', 'B20', 'C20', 'D20', 'E20', 'F20', 'G20', 'H20', 'I20', 'J20',
                               'K20', 'L20', 'M20', 'N20', 'O20', 'B21', 'C21', 'D21', 'E21', 'F21', 'G21', 'H21',
                               'I21', 'J21', 'K21', 'L21', 'M21', 'N21', 'O21', 'B22', 'C22', 'D22', 'E22', 'F22',
                               'G22', 'H22', 'I22', 'J22', 'K22', 'L22', 'M22', 'N22', 'O22']}, 'pora': {
            'wells': {'A1': -199.99999999999994, 'B1': 54.54545454545454, 'C1': -72.72727272727272,
                      'D1': 54.54545454545454, 'E1': 54.54545454545454, 'F1': 181.8181818181818,
                      'G1': -199.99999999999994, 'H1': 54.54545454545454, 'I1': -72.72727272727272,
                      'J1': 54.54545454545454, 'K1': -72.72727272727272, 'L1': -199.99999999999994,
                      'M1': 54.54545454545454, 'N1': 181.8181818181818, 'O1': 181.8181818181818,
                      'P1': 181.8181818181818, 'A2': 54.54545454545454, 'P2': -72.72727272727272,
                      'A3': 181.8181818181818, 'P3': 181.8181818181818, 'A4': 54.54545454545454,
                      'P4': 54.54545454545454, 'A5': 181.8181818181818, 'P5': 54.54545454545454,
                      'A6': 181.8181818181818, 'P6': -72.72727272727272, 'A7': 54.54545454545454,
                      'P7': 54.54545454545454, 'A8': 54.54545454545454, 'P8': 181.8181818181818,
                      'A9': 181.8181818181818, 'P9': 54.54545454545454, 'A10': 181.8181818181818,
                      'P10': 181.8181818181818, 'A11': 54.54545454545454, 'P11': 54.54545454545454,
                      'A12': 54.54545454545454, 'P12': 54.54545454545454, 'A13': 54.54545454545454,
                      'P13': 54.54545454545454, 'A14': -199.99999999999994, 'P14': 54.54545454545454,
                      'A15': 309.09090909090907, 'P15': 309.09090909090907, 'A16': 181.8181818181818,
                      'P16': 181.8181818181818, 'A17': 54.54545454545454, 'P17': 54.54545454545454,
                      'A18': 54.54545454545454, 'P18': 181.8181818181818, 'A19': 181.8181818181818,
                      'P19': 181.8181818181818, 'A20': 54.54545454545454, 'P20': 181.8181818181818,
                      'A21': 54.54545454545454, 'P21': 181.8181818181818, 'A22': -199.99999999999994,
                      'P22': 181.8181818181818, 'A23': 54.54545454545454, 'B23': 54.54545454545454,
                      'C23': 181.8181818181818, 'D23': 181.8181818181818, 'E23': -72.72727272727272,
                      'F23': -72.72727272727272, 'G23': -72.72727272727272, 'H23': 54.54545454545454,
                      'I23': 54.54545454545454, 'J23': -72.72727272727272, 'K23': 309.09090909090907,
                      'L23': 181.8181818181818, 'M23': 181.8181818181818, 'N23': 436.3636363636363,
                      'O23': 181.8181818181818, 'P23': 309.09090909090907, 'A24': 181.8181818181818,
                      'B24': -72.72727272727272, 'C24': 309.09090909090907, 'D24': 54.54545454545454,
                      'E24': 54.54545454545454, 'F24': 181.8181818181818, 'G24': 181.8181818181818,
                      'H24': -72.72727272727272, 'I24': 54.54545454545454, 'J24': 309.09090909090907,
                      'K24': 181.8181818181818, 'L24': 181.8181818181818, 'M24': 181.8181818181818,
                      'N24': 54.54545454545454, 'O24': 181.8181818181818, 'P24': 181.8181818181818,
                      'B2': 54.54545454545454, 'C2': 181.8181818181818, 'D2': 54.54545454545454,
                      'E2': -72.72727272727272, 'F2': -72.72727272727272, 'G2': -72.72727272727272,
                      'H2': 54.54545454545454, 'I2': -72.72727272727272, 'J2': -327.27272727272725,
                      'K2': 54.54545454545454, 'L2': 54.54545454545454, 'M2': 181.8181818181818,
                      'N2': 54.54545454545454, 'O2': -72.72727272727272, 'B3': 181.8181818181818,
                      'C3': 54.54545454545454, 'D3': 54.54545454545454, 'E3': 309.09090909090907,
                      'F3': 54.54545454545454, 'G3': 181.8181818181818, 'H3': 54.54545454545454,
                      'I3': 54.54545454545454, 'J3': 181.8181818181818, 'K3': 54.54545454545454,
                      'L3': 54.54545454545454, 'M3': 54.54545454545454, 'N3': 54.54545454545454,
                      'O3': 54.54545454545454, 'B4': 181.8181818181818, 'C4': 54.54545454545454,
                      'D4': 54.54545454545454, 'E4': 181.8181818181818, 'F4': 54.54545454545454,
                      'G4': 54.54545454545454, 'H4': -72.72727272727272, 'I4': 309.09090909090907,
                      'J4': 54.54545454545454, 'K4': 54.54545454545454, 'L4': 54.54545454545454,
                      'M4': 181.8181818181818, 'N4': 309.09090909090907, 'O4': 181.8181818181818,
                      'B5': 54.54545454545454, 'C5': 181.8181818181818, 'D5': 181.8181818181818,
                      'E5': 54.54545454545454, 'F5': 54.54545454545454, 'G5': 54.54545454545454,
                      'H5': 181.8181818181818, 'I5': -72.72727272727272, 'J5': 54.54545454545454,
                      'K5': 181.8181818181818, 'L5': 54.54545454545454, 'M5': 181.8181818181818,
                      'N5': 54.54545454545454, 'O5': 181.8181818181818, 'B6': 181.8181818181818,
                      'C6': 54.54545454545454, 'D6': 181.8181818181818, 'E6': -72.72727272727272,
                      'F6': 181.8181818181818, 'G6': 54.54545454545454, 'H6': 181.8181818181818,
                      'I6': 54.54545454545454, 'J6': 54.54545454545454, 'K6': 181.8181818181818,
                      'L6': 54.54545454545454, 'M6': 54.54545454545454, 'N6': 54.54545454545454,
                      'O6': 181.8181818181818, 'B7': 54.54545454545454, 'C7': 181.8181818181818,
                      'D7': 309.09090909090907, 'E7': 181.8181818181818, 'F7': 54.54545454545454,
                      'G7': 54.54545454545454, 'H7': 181.8181818181818, 'I7': 54.54545454545454,
                      'J7': -72.72727272727272, 'K7': 54.54545454545454, 'L7': 54.54545454545454,
                      'M7': 181.8181818181818, 'N7': 181.8181818181818, 'O7': 181.8181818181818,
                      'B8': -72.72727272727272, 'C8': -72.72727272727272, 'D8': 54.54545454545454,
                      'E8': 54.54545454545454, 'F8': -199.99999999999994, 'G8': 54.54545454545454,
                      'H8': 54.54545454545454, 'I8': 181.8181818181818, 'J8': 181.8181818181818,
                      'K8': 181.8181818181818, 'L8': 54.54545454545454, 'M8': 181.8181818181818,
                      'N8': 181.8181818181818, 'O8': -72.72727272727272, 'B9': -72.72727272727272,
                      'C9': 54.54545454545454, 'D9': -72.72727272727272, 'E9': 54.54545454545454,
                      'F9': 181.8181818181818, 'G9': 181.8181818181818, 'H9': 54.54545454545454,
                      'I9': -72.72727272727272, 'J9': -72.72727272727272, 'K9': 54.54545454545454,
                      'L9': -72.72727272727272, 'M9': 309.09090909090907, 'N9': -199.99999999999994,
                      'O9': 181.8181818181818, 'B10': 54.54545454545454, 'C10': -72.72727272727272,
                      'D10': 181.8181818181818, 'E10': 54.54545454545454, 'F10': 54.54545454545454,
                      'G10': 181.8181818181818, 'H10': -72.72727272727272, 'I10': 181.8181818181818,
                      'J10': 54.54545454545454, 'K10': 54.54545454545454, 'L10': 436.3636363636363,
                      'M10': 181.8181818181818, 'N10': 181.8181818181818, 'O10': 54.54545454545454,
                      'B11': 54.54545454545454, 'C11': 54.54545454545454, 'D11': -72.72727272727272,
                      'E11': 54.54545454545454, 'F11': -199.99999999999994, 'G11': 181.8181818181818,
                      'H11': -199.99999999999994, 'I11': 54.54545454545454, 'J11': 54.54545454545454,
                      'K11': 54.54545454545454, 'L11': 181.8181818181818, 'M11': 181.8181818181818,
                      'N11': 54.54545454545454, 'O11': 181.8181818181818, 'B12': 54.54545454545454,
                      'C12': 54.54545454545454, 'D12': -72.72727272727272, 'E12': 181.8181818181818,
                      'F12': -72.72727272727272, 'G12': -72.72727272727272, 'H12': 181.8181818181818,
                      'I12': 181.8181818181818, 'J12': 54.54545454545454, 'K12': -199.99999999999994,
                      'L12': 54.54545454545454, 'M12': 54.54545454545454, 'N12': 181.8181818181818,
                      'O12': 181.8181818181818, 'B13': 54.54545454545454, 'C13': 181.8181818181818,
                      'D13': 181.8181818181818, 'E13': 181.8181818181818, 'F13': 181.8181818181818,
                      'G13': 181.8181818181818, 'H13': -72.72727272727272, 'I13': 181.8181818181818,
                      'J13': 54.54545454545454, 'K13': 54.54545454545454, 'L13': -199.99999999999994,
                      'M13': 181.8181818181818, 'N13': 181.8181818181818, 'O13': -72.72727272727272,
                      'B14': 54.54545454545454, 'C14': -72.72727272727272, 'D14': -72.72727272727272,
                      'E14': 54.54545454545454, 'F14': 54.54545454545454, 'G14': -72.72727272727272,
                      'H14': -72.72727272727272, 'I14': -199.99999999999994, 'J14': -199.99999999999994,
                      'K14': 54.54545454545454, 'L14': 54.54545454545454, 'M14': 309.09090909090907,
                      'N14': 181.8181818181818, 'O14': 54.54545454545454, 'B15': 54.54545454545454,
                      'C15': 181.8181818181818, 'D15': -72.72727272727272, 'E15': 54.54545454545454,
                      'F15': 54.54545454545454, 'G15': -72.72727272727272, 'H15': -72.72727272727272,
                      'I15': 54.54545454545454, 'J15': -72.72727272727272, 'K15': 54.54545454545454,
                      'L15': 181.8181818181818, 'M15': 181.8181818181818, 'N15': 54.54545454545454,
                      'O15': 181.8181818181818, 'B16': 54.54545454545454, 'C16': 181.8181818181818,
                      'D16': 181.8181818181818, 'E16': 54.54545454545454, 'F16': 54.54545454545454,
                      'G16': 54.54545454545454, 'H16': 181.8181818181818, 'I16': 54.54545454545454,
                      'J16': 181.8181818181818, 'K16': 54.54545454545454, 'L16': 181.8181818181818,
                      'M16': 309.09090909090907, 'N16': 309.09090909090907, 'O16': -72.72727272727272,
                      'B17': 181.8181818181818, 'C17': 54.54545454545454, 'D17': 54.54545454545454,
                      'E17': 54.54545454545454, 'F17': -72.72727272727272, 'G17': 181.8181818181818,
                      'H17': 54.54545454545454, 'I17': 181.8181818181818, 'J17': 181.8181818181818,
                      'K17': 181.8181818181818, 'L17': -72.72727272727272, 'M17': 181.8181818181818,
                      'N17': 309.09090909090907, 'O17': 181.8181818181818, 'B18': 181.8181818181818,
                      'C18': 54.54545454545454, 'D18': 54.54545454545454, 'E18': 54.54545454545454,
                      'F18': 54.54545454545454, 'G18': 181.8181818181818, 'H18': 181.8181818181818,
                      'I18': -72.72727272727272, 'J18': -72.72727272727272, 'K18': 54.54545454545454,
                      'L18': -199.99999999999994, 'M18': 181.8181818181818, 'N18': 54.54545454545454,
                      'O18': 54.54545454545454, 'B19': 54.54545454545454, 'C19': -72.72727272727272,
                      'D19': 54.54545454545454, 'E19': 181.8181818181818, 'F19': 54.54545454545454,
                      'G19': 54.54545454545454, 'H19': -72.72727272727272, 'I19': 54.54545454545454,
                      'J19': 54.54545454545454, 'K19': 54.54545454545454, 'L19': 54.54545454545454,
                      'M19': -72.72727272727272, 'N19': 181.8181818181818, 'O19': 54.54545454545454,
                      'B20': 54.54545454545454, 'C20': 54.54545454545454, 'D20': -199.99999999999994,
                      'E20': 54.54545454545454, 'F20': 54.54545454545454, 'G20': 54.54545454545454,
                      'H20': -72.72727272727272, 'I20': 54.54545454545454, 'J20': 54.54545454545454,
                      'K20': 54.54545454545454, 'L20': 181.8181818181818, 'M20': 181.8181818181818,
                      'N20': 54.54545454545454, 'O20': 54.54545454545454, 'B21': 54.54545454545454,
                      'C21': 54.54545454545454, 'D21': 181.8181818181818, 'E21': 181.8181818181818,
                      'F21': -72.72727272727272, 'G21': -72.72727272727272, 'H21': 181.8181818181818,
                      'I21': 181.8181818181818, 'J21': 181.8181818181818, 'K21': 54.54545454545454,
                      'L21': 181.8181818181818, 'M21': 181.8181818181818, 'N21': 181.8181818181818,
                      'O21': 54.54545454545454, 'B22': -72.72727272727272, 'C22': 54.54545454545454,
                      'D22': 309.09090909090907, 'E22': 181.8181818181818, 'F22': -72.72727272727272,
                      'G22': 54.54545454545454, 'H22': 54.54545454545454, 'I22': -72.72727272727272,
                      'J22': 309.09090909090907, 'K22': -72.72727272727272, 'L22': -327.27272727272725,
                      'M22': 181.8181818181818, 'N22': 54.54545454545454, 'O22': -72.72727272727272},
            'empty': ['A1', 'B1', 'C1', 'D1', 'E1', 'F1', 'G1', 'H1', 'I1', 'J1', 'K1', 'L1', 'M1', 'N1', 'O1', 'P1',
                      'A2', 'P2', 'A3', 'P3', 'A4', 'P4', 'A5', 'P5', 'A6', 'P6', 'A7', 'P7', 'A8', 'P8', 'A9', 'P9',
                      'A10', 'P10', 'A11', 'P11', 'A12', 'P12', 'A13', 'P13', 'A14', 'P14', 'A15', 'P15', 'A16', 'P16',
                      'A17', 'P17', 'A18', 'P18', 'A19', 'P19', 'A20', 'P20', 'A21', 'P21', 'A22', 'P22', 'A23', 'B23',
                      'C23', 'D23', 'E23', 'F23', 'G23', 'H23', 'I23', 'J23', 'K23', 'L23', 'M23', 'N23', 'O23', 'P23',
                      'A24', 'B24', 'C24', 'D24', 'E24', 'F24', 'G24', 'H24', 'I24', 'J24', 'K24', 'L24', 'M24', 'N24',
                      'O24', 'P24'],
            'minimum': ['B2', 'C2', 'D2', 'E2', 'F2', 'G2', 'H2', 'I2', 'J2', 'K2', 'L2', 'M2', 'N2', 'O2'],
            'max': ['B3', 'C3', 'D3', 'E3', 'F3', 'G3', 'H3', 'I3', 'J3', 'K3', 'L3', 'M3', 'N3', 'O3'],
            'sample': ['B4', 'C4', 'D4', 'E4', 'F4', 'G4', 'H4', 'I4', 'J4', 'K4', 'L4', 'M4', 'N4', 'O4', 'B5', 'C5',
                       'D5', 'E5', 'F5', 'G5', 'H5', 'I5', 'J5', 'K5', 'L5', 'M5', 'N5', 'O5', 'B6', 'C6', 'D6', 'E6',
                       'F6', 'G6', 'H6', 'I6', 'J6', 'K6', 'L6', 'M6', 'N6', 'O6', 'B7', 'C7', 'D7', 'E7', 'F7', 'G7',
                       'H7', 'I7', 'J7', 'K7', 'L7', 'M7', 'N7', 'O7', 'B8', 'C8', 'D8', 'E8', 'F8', 'G8', 'H8', 'I8',
                       'J8', 'K8', 'L8', 'M8', 'N8', 'O8', 'B9', 'C9', 'D9', 'E9', 'F9', 'G9', 'H9', 'I9', 'J9', 'K9',
                       'L9', 'M9', 'N9', 'O9', 'B10', 'C10', 'D10', 'E10', 'F10', 'G10', 'H10', 'I10', 'J10', 'K10',
                       'L10', 'M10', 'N10', 'O10', 'B11', 'C11', 'D11', 'E11', 'F11', 'G11', 'H11', 'I11', 'J11', 'K11',
                       'L11', 'M11', 'N11', 'O11', 'B12', 'C12', 'D12', 'E12', 'F12', 'G12', 'H12', 'I12', 'J12', 'K12',
                       'L12', 'M12', 'N12', 'O12', 'B13', 'C13', 'D13', 'E13', 'F13', 'G13', 'H13', 'I13', 'J13', 'K13',
                       'L13', 'M13', 'N13', 'O13', 'B14', 'C14', 'D14', 'E14', 'F14', 'G14', 'H14', 'I14', 'J14', 'K14',
                       'L14', 'M14', 'N14', 'O14', 'B15', 'C15', 'D15', 'E15', 'F15', 'G15', 'H15', 'I15', 'J15', 'K15',
                       'L15', 'M15', 'N15', 'O15', 'B16', 'C16', 'D16', 'E16', 'F16', 'G16', 'H16', 'I16', 'J16', 'K16',
                       'L16', 'M16', 'N16', 'O16', 'B17', 'C17', 'D17', 'E17', 'F17', 'G17', 'H17', 'I17', 'J17', 'K17',
                       'L17', 'M17', 'N17', 'O17', 'B18', 'C18', 'D18', 'E18', 'F18', 'G18', 'H18', 'I18', 'J18', 'K18',
                       'L18', 'M18', 'N18', 'O18', 'B19', 'C19', 'D19', 'E19', 'F19', 'G19', 'H19', 'I19', 'J19', 'K19',
                       'L19', 'M19', 'N19', 'O19', 'B20', 'C20', 'D20', 'E20', 'F20', 'G20', 'H20', 'I20', 'J20', 'K20',
                       'L20', 'M20', 'N20', 'O20', 'B21', 'C21', 'D21', 'E21', 'F21', 'G21', 'H21', 'I21', 'J21', 'K21',
                       'L21', 'M21', 'N21', 'O21', 'B22', 'C22', 'D22', 'E22', 'F22', 'G22', 'H22', 'I22', 'J22', 'K22',
                       'L22', 'M22', 'N22', 'O22']}}, 'calculations': {'original': {
        'empty': {'avg': 7.000000000000001e-05, 'stdev': 9.994380443501147e-05, 'pstdev': 9.938701010583716e-05,
                  'pvariance': 9.877777777777777e-09, 'variance': 9.98876404494382e-09, 'st_dev_%': 142.7768634785878},
        'minimum': {'avg': 0.00014285714285714287, 'stdev': 0.00010163498575623618, 'pstdev': 9.793792286287207e-05,
                    'pvariance': 9.591836734693879e-09, 'variance': 1.0329670329670331e-08,
                    'st_dev_%': 71.14449002936533},
        'max': {'avg': 6.428571428571429e-05, 'stdev': 6.333236937766509e-05, 'pstdev': 6.102859818083951e-05,
                'pvariance': 3.7244897959183676e-09, 'variance': 4.010989010989011e-09, 'st_dev_%': 98.51701903192347},
        'sample': {'avg': 8.383458646616541e-05, 'stdev': 9.153798514163728e-05, 'pstdev': 9.136575924092731e-05,
                   'pvariance': 8.347701961671095e-09, 'variance': 8.379202723790608e-09,
                   'st_dev_%': 109.18880738867945}, 'other': {'S/B': 0.44999999999999996}}, 'normalised': {
        'empty': {'avg': -7.285714285714286e-05, 'stdev': 9.994380443501147e-05, 'pstdev': 9.938701010583716e-05,
                  'pvariance': 9.877777777777777e-09, 'variance': 9.98876404494382e-09, 'st_dev_%': -137.177770793153},
        'minimum': {'avg': -3.8721506160196585e-21, 'stdev': 0.00010163498575623618, 'pstdev': 9.793792286287207e-05,
                    'pvariance': 9.591836734693879e-09, 'variance': 1.0329670329670331e-08,
                    'st_dev_%': -2.6247683996525665e+18},
        'max': {'avg': -7.857142857142858e-05, 'stdev': 6.333236937766509e-05, 'pstdev': 6.102859818083951e-05,
                'pvariance': 3.724489795918367e-09, 'variance': 4.010989010989011e-09, 'st_dev_%': -80.60483375339192},
        'sample': {'avg': -5.902255639097745e-05, 'stdev': 9.153798514163728e-05, 'pstdev': 9.136575924092731e-05,
                   'pvariance': 8.347701961671095e-09, 'variance': 8.379202723790608e-09,
                   'st_dev_%': -155.08983469857014}, 'other': {'S/B': 2.029141848108051e+16}}, 'pora': {
        'empty': {'avg': 92.72727272727272, 'stdev': 127.20120564456005, 'pstdev': 126.49255831652,
                  'pvariance': 16000.367309458215, 'variance': 16180.146717429656, 'st_dev_%': 137.177770793153},
        'minimum': {'avg': 1.0150610510858574e-15, 'stdev': 129.35361823520967, 'pstdev': 124.64826546183716,
                    'pvariance': 15537.190082644625, 'variance': 16732.358550540368,
                    'st_dev_%': 1.2743432338068156e+19},
        'max': {'avg': 100.0, 'stdev': 80.60483375339193, 'pstdev': 77.67276132106846, 'pvariance': 6033.057851239669,
                'variance': 6497.139224411951, 'st_dev_%': 80.60483375339193},
        'sample': {'avg': 75.11961722488039, 'stdev': 116.50289018026562, 'pstdev': 116.28369357936202,
                   'pvariance': 13521.89739245896, 'variance': 13572.923420355033, 'st_dev_%': 155.08983469857014},
        'other': {'S/B': 9.85162418487296e+16}}, 'other': {'z_prime': -5.2987535596580475}}}
    # initial_row = 2
    # cal_writer(ws, all_data, initial_row)