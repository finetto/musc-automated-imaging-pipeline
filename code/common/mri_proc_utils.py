# module with utility functions for MRI data processing

from pathlib import Path
from datetime import datetime
import re
import os
import glob
import json
import shutil

def list_dicom_files(dicom_folder):

    # check if file exists
    if not Path(dicom_folder).exists():
        print("ERROR: Could not find dicom folder \"" + dicom_folder + "\".")
        return -1
    
    # get files
    files = os.listdir(dicom_folder)
    return files
    
def list_converted_files(nifti_folder):

    # check if file exists
    if not Path(nifti_folder).exists():
        print("ERROR: Could not find nifti folder \"" + nifti_folder + "\".")
        return -1
    
    # get files
    nifti_files = glob.glob("*.nii.gz", root_dir=nifti_folder)
    sidecar_files = glob.glob("*.json", root_dir=nifti_folder)
    bval_files = glob.glob("*.bval", root_dir=nifti_folder)
    bvec_files = glob.glob("*.bvec", root_dir=nifti_folder)

    return nifti_files+sidecar_files+bval_files+bvec_files

def parse_converted_file_name(file_name):

    # strip file name until we get the true stem
    file_name_stem = str(Path(file_name).stem)
    while file_name != file_name_stem:
        file_name = file_name_stem
        file_name_stem = str(Path(file_name).stem)

        # make sure we removed a file extension and not part of the file name (some files have a period in the name...)
        if (len(file_name) - len(file_name_stem))>8:
            break

    # split parts
    parts = file_name.split('_')
    if len(parts)>=2:
        series_number = int(parts[0])
        series_description = "_".join(parts[1:])
    else:
        print("WARNING: invalid converted file name \"" + file_name + "\".")
        return -1
    
    return {"series_number": series_number, "series_description": series_description}


def parse_summary_file(summary_file):

    # check if file exists
    if not Path(summary_file).exists():
        print("ERROR: Could not find session summary file \"" + summary_file + "\".")
        return -1
    
    # read file line by line
    reading_header = True
    reading_series = False
    reading_total= False

    series_info = []
    session_info = {}

    try:
        with open(summary_file, "r") as file:
            for line in file:

                # skip empty lines
                if line.strip() == "":
                    continue

                # look for section delimiter ("-----")
                new_section_start = False
                if line.lstrip().startswith("-----"):
                    new_section_start = True

                # handle different file sections
                if reading_header:
                    # do nothing other than looking for section delimiter
                    # NOTE: here we could potentially add functionality to parse information contained in the header
                    if new_section_start:
                        reading_header = False
                        reading_series = True
                    
                elif reading_series:

                    # check if this line is a new section start or a series descriptor
                    if new_section_start:
                        reading_series = False
                        reading_total = True

                    else:
                        # parse line
                        columns = line.strip().split()
                        if len(columns) < 5:
                            print("ERROR: Could not parse session summary file \"" + summary_file + "\". Invalid column number.")
                            return -1
                        
                        # convert date and time
                        series_date = columns[1]
                        series_time = columns[2]

                        if len(series_date) == 8:
                            series_date = series_date[:4] + "/" + series_date[4:6] + "/" + series_date[6:8]
                        else:
                            series_date = None

                        if len(series_time) != 12:
                            series_time = None

                        # calculate datetime
                        series_datetime = None
                        if (series_date != None) and (series_time != None):
                            dt_string = " ".join((series_date, series_time))
                            series_datetime = datetime.strptime(dt_string, "%Y/%m/%d %H:%M:%S.%f")

                        # compile information and append to series info
                        series_info_i = {
                            "series_number": int(columns[0]),
                            "date": series_date,
                            "time": series_time,
                            "datetime": series_datetime,
                            "number_files": int(columns[3]),
                            "series_description": columns[4]
                        }

                        series_info.append(series_info_i)

                elif reading_total:
                    # parse line
                    columns = line.strip().split()
                    if len(columns) < 5:
                        print("ERROR: Could not parse session summary file \"" + summary_file + "\". Invalid column number.")
                        return -1

                    # convert date and time
                    session_date = columns[1]
                    session_duration = columns[2]

                    if len(session_date) == 8:
                        session_date = session_date[:4] + "/" + session_date[4:6] + "/" + session_date[6:8]
                    else:
                        series_date = None

                    if len(session_duration) != 12:
                        session_duration = None

                    session_info = {
                        "number_series": int(columns[0]),
                        "date": session_date,
                        "duration": session_duration,
                        "total_files": int(columns[3])
                    }

    except Exception as e:
        print("ERROR: Could not read session summary file \"" + summary_file + "\":")
        print(e)
        return -1
    
    return {"session_info": session_info, "series_info": series_info}

def parse_dcm2niix_log(log_file):

    # check if file exists
    if not Path(log_file).exists():
        print("ERROR: Could not find dcm2niix log file \"" + log_file + "\".")
        return -1
    
    # define search pattern
    search_pattern = "Convert \d+ DICOM as "

    # parse file
    conversion_summary = []
    try:
        with open(log_file, "r") as file:
            for line in file:

                line = line.strip()

                # skip empty lines
                if line == "":
                    continue

                # search for pattern in line
                m = re.search(search_pattern, line)
                if not m: # pattern not found
                    continue
                if m.span()[0] != 0: # pattern not at beginnig of line
                    continue

                # get number of files
                m2 = re.search("\d+",m.group())
                if not m2:
                    print("ERROR: could not find file number in dcm2niix log file \"" + log_file + "\":\n\t\"" + line + "\"")
                    continue
                else:
                    number_files = int(m2.group())

                # find start and end of series size description
                size_start = line.rfind("(")
                size_end = line.rfind(")")
                if (size_start==-1) or (size_end==-1):
                    print("WARNING: invalid line in dcm2niix log file \"" + log_file + "\":\n\t\"" + line + "\"")
                    continue

                # extract path and name of nifti file
                nifti_file_path = (line[m.span()[1]:(size_start-1)]).strip().replace("\\","/")
                tmp = nifti_file_path.split("/")
                nifti_file_name = tmp[-1]

                # get series number and series description
                series_info = parse_converted_file_name(nifti_file_name)
                if series_info == -1:
                    print("WARNING: invalid line in dcm2niix log file \"" + log_file + "\":\n\t\"" + line + "\"")
                    continue
                series_number = series_info["series_number"]
                series_description = series_info["series_description"]

                # get dimensions of nifti file
                nifti_dimensions = [int(val) for val in line[(size_start+1):size_end].split("x")]
                if len(nifti_dimensions)!=4:
                    print("WARNING: invalid line in dcm2niix log file \"" + log_file + "\":\n\t\"" + line + "\"")
                    continue

                conversion_info_i = {
                    "series_number": series_number,
                    "series_description": series_description,
                    "file": nifti_file_name,
                    "number_files": number_files,
                    "dimensions": nifti_dimensions
                }
                conversion_summary.append(conversion_info_i)
                

    except Exception as e:
        print("ERROR: Could not read dcm2niix log file \"" + log_file + "\":")
        print(e)
        return -1
    
    return conversion_summary

def parse_dcm2bids_config(config_file):

    # check if file exists
    if not Path(config_file).exists():
        print("ERROR: Could not find dcm2bids config file.")
        return -1

    try:
        with open(config_file, 'r') as f:
            config_dcm2bids = json.load(f)
    except Exception as e:
        print("ERROR: Unable to load dcm2bids config file:\n")
        print(e)
        return -1
    

    # get all dcm2bids search criteria in config file
    unique_criteria = []
    unique_keys = []#["SeriesDescription", "ProtocolName", "EchoNumber"]
    unique_values = []
    if "descriptions" in config_dcm2bids:

        # find unique criteria
        for description in config_dcm2bids["descriptions"]:
            if "criteria" in description:
                if not description["criteria"] in unique_criteria:
                    unique_criteria.append(description["criteria"])

        # find unique keys
        for criteria in unique_criteria:
            search_keys = list(criteria.keys())
            for key in search_keys:
                if not key in unique_keys:
                    unique_keys.append(key)

        # find unique values
        for criteria in unique_criteria:
            values = []
            for key in unique_keys:
                if key in criteria:
                    values.append(criteria[key])
                else:
                    values.append(None)

                if not values in unique_values:
                    unique_values.append(values)

    # add fields to config
    config_dcm2bids["search_criteria"] = {
        "criteria": unique_criteria,
        "keys": unique_keys,
        "values": unique_values
    }

    return config_dcm2bids
    
    
# deidentify file contents
def deidentify_file_contents(old_file_path, new_file_path, old_id, new_id):

    # check if file exists
    if not Path(old_file_path).exists():
        print("ERROR: Could not find file to be deidentified.")
        return -1

    try:
        with open(old_file_path, 'r', encoding='utf-8', errors='ignore') as file:
            content = file.read()

        new_content = content.replace(old_id, new_id)

        with open(new_file_path, 'w', encoding='utf-8') as file:
            file.write(new_content)

    except Exception as e:
        print("ERROR: Unable to deidentify file:\n")
        print(e)
        return -1

    return True

# deidentify files
def deidentify_files_and_folders(old_root_folder, new_root_folder, old_id, new_id):

    # make sure old root folder exists
    if not Path(old_root_folder).exists():
        print("ERROR: Could not find root folder to be deidentified.")
        return -1

    # create new root folder
    if Path(new_root_folder).exists():
        shutil.rmtree(new_root_folder)
    os.mkdir(new_root_folder)

    # cycle through all files and subdirectories
    for dirpath, dirnames, filenames in os.walk(old_root_folder):

        # get equivalent path in deidentified folder structure
        new_dirpath_stem = dirpath.removeprefix(old_root_folder).replace(old_id, new_id)
        new_dirpath_stem = new_dirpath_stem.removeprefix("/").removeprefix("\\")
        new_dirpath = os.path.join(new_root_folder,new_dirpath_stem)


        # cycle through folders and add them to deidentified folder structure
        for dirname in dirnames:
            new_dirname = dirname.replace(old_id, new_id)
            new_path = os.path.join(new_dirpath,new_dirname)
            if not Path(new_path).exists():
                os.mkdir(new_path)

        # cycle through files and deidentify them
        for filename in filenames:
            old_filepath = os.path.join(dirpath, filename)
            new_filename = filename.replace(old_id, new_id)
            new_filepath = os.path.join(new_dirpath, new_filename)

            # copy file and modify contents if needed
            if filename.endswith(('.txt', '.json')):
                res = deidentify_file_contents(old_filepath, new_filepath, old_id, new_id)
                if res==-1:
                    return -1
            else:
                shutil.copyfile(old_filepath, new_filepath)
                    


    return True