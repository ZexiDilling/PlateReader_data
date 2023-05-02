import configparser
from statistics import mean, stdev, pstdev, pvariance, variance


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