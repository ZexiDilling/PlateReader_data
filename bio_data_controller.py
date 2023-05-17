from bio_data_functions import original_data_dict, pora_internal, pora, norm, org, txt_to_xlsx
from bio_date_handler import BIOAnalyser
from bio_report_setup import bio_final_report_controller


def bio_single_report(config, file, plate_name, plate_layout, analysis, bio_sample_dict, all_plates_data, write_to_excel=True):
    """
    Analyses platereader data from a single run.

    :param all_plates_data: A dict of all the data from all plates that are being analysed
    :type all_plates_data: dict
    :param config: The config handler, with all the default information in the config file.
    :type config: configparser.ConfigParser
    :param file: The full path to the file
    :type file: PATH
    :param plate_name: name of the current plate
    :type plate_name: str
    :param plate_layout: The layout for the plate with values for each well, what state they are in
    :type plate_layout: dict
    :param bio_sample_dict: None or a dict of sample ide, per plate analysed
    :type bio_sample_dict: dict
    :param analysis: The analysis method, single or multiple of the same sample.
    :type analysis: str
    :param write_to_excel: If the files needs to be written to an excel file or not. For now this should always be true
    :type write_to_excel: bool
    :return: All the data for the plates raw data, and their calculations
    :rtype: dict
    """
    save_location = config["Folder"]["out"]
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
    # needs to reformat plate-layout to use well ID instead of numbers...
    bioa = BIOAnalyser(config, bio_plate_report_setup)
    file = txt_to_xlsx(file, plate_name)
    all_data, well_row_col, well_type, barcode, date = original_data_dict(file, plate_layout)

    if not all_data:
        return False
    else:
        all_plates_data[barcode] = bioa.bio_data_controller(file, plate_layout, all_data, well_row_col, well_type,
                                                        analysis, write_to_excel, bio_sample_dict,
                                                        save_location)
    return True, all_plates_data, file


def bio_full_report(output_file, analyse_method, all_plate_data):
    """
    Writes the final report for the bio data

    :param analyse_method: The analysed method used for the data
    :type analyse_method: str
    :param all_plate_data: All the data for all the plates, raw and calculations
    :type all_plate_data: dict
    :param output_file: Path for th output file
    :type output_file: PATH
    :return: A excel report file with all the data
    """
    # The final report setup is taken from Structure search! ! !
    final_report_setup = {'methods': {'original': False, 'normalised': False, 'pora': True},
                          'analyse': {'sample': True, 'minimum': False, 'max': False, 'empty': False, 'negative': False,
                                      'positive': False, 'blank': False}, 'calc': {
            'original': {'overview': True, 'sample': False, 'minimum': True, 'max': True, 'empty': False,
                         'negative': True, 'positive': True, 'blank': False},
            'normalised': {'overview': True, 'sample': False, 'minimum': True, 'max': True, 'empty': False,
                           'negative': True, 'positive': True, 'blank': False},
            'pora': {'overview': True, 'sample': True, 'minimum': False, 'max': False, 'empty': False,
                     'negative': False, 'positive': False, 'blank': False}, 'z_prime': True},
                          'pora_threshold': {'th_1': {'min': 0.0, 'max': 10.0, 'use': True},
                                             'th_2': {'min': 10.0, 'max': 20.0, 'use': True},
                                             'th_3': {'min': 20.0, 'max': 30.0, 'use': True},
                                             'th_4': {'min': 30.0, 'max': 40.0, 'use': True},
                                             'th_5': {'min': 40.0, 'max': 50.0, 'use': True},
                                             'th_6': {'min': 50.0, 'max': 60.0, 'use': True},
                                             'th_7': {'min': 60.0, 'max': 70.0, 'use': True},
                                             'th_8': {'min': 70.0, 'max': 80.0, 'use': True},
                                             'th_9': {'min': 80.0, 'max': 90.0, 'use': True},
                                             'th_10': {'min': 90.0, 'max': 100.0, 'use': True}},
                          'data': {'sample': {'matrix': False, 'list': False, 'max_min': False},
                                   'minimum': {'matrix': True, 'list': True, 'max_min': True},
                                   'max': {'matrix': True, 'list': True, 'max_min': True},
                                   'empty': {'matrix': False, 'list': False, 'max_min': False},
                                   'negative': {'matrix': True, 'list': True, 'max_min': True},
                                   'positive': {'matrix': True, 'list': True, 'max_min': True},
                                   'blank': {'matrix': False, 'list': False, 'max_min': False},
                                   'z_prime': {'matrix': True, 'list': True, 'max_min': True}}}

    bio_final_report_controller(analyse_method, all_plate_data, output_file, final_report_setup)
