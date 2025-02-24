# module with functions managing the settings used by the study config

from pathlib import Path
import json

# initialize settings
def _init():
    
    settings = {
        "subject_identifier_format": {
            "regex": "[mM][0-9][0-9]+",
            "desired_prefix": "sub-",
            "desired_start_str": "M",
            "desired_digits": 3
        },
        "deidentify_data": True,
        "deidentified_subject_identifier_format": {
            "desired_prefix": "sub-",
            "desired_start_str": "D",
            "desired_digits": 3
        },
        "session_identifier_format": {
            "desired_prefix": "ses-",
            "desired_digits": 2
        }
    }
        
    return settings

# write settings to file    
def write_to_file(settings, settings_file):
    
    try:
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print("ERROR: Unable to write settings file:\n")
        print(e)
        return -1
        
    return 1        
        
# load settings from file
def load_from_file(settings_file):

    if Path(settings_file).exists():
        #load file
        try:
            with open(settings_file, 'r') as f:
                settings = json.load(f)
        except Exception as e:
            print("ERROR: Unable to load settings file:\n")
            print(e)
            return -1 
            
    else:
        # initialize settings
        settings = _init()
        
        # write settings
        success = write_to_file(settings, settings_file)
        if success != 1:
            return success
            
    return settings