from openpyxl import load_workbook, Workbook
from openpyxl.styles import PatternFill, Font, Alignment
import csv
import xml.etree.ElementTree as ET
import re
import os

from helper_func import folder_to_files






if __name__ == "__main__":
    location = "C:/Users/phch/Desktop/more_data_files"
    file = "2022-12-09-Compound_200sets_with well position.xlsx"
    full_path = f"{location}/{file}"
    file_layout = "ldv_200.xlsx"
    full_path_layout = f"{location}/{file_layout}"
