# Automated pipeline for processing imaging data collected at MUSC

A pipeline for processing research imaging data collected at the Medical University of South Carolina. The scripts automatically run the following steps:
- Execute queries to find newly acquired data
- Download data to the local system
- Extract relevant information from data (metadata, subject ID, session ID, etc.)
- Notify user via e-mail and ask to validate the extracted information
- Validate all downloaded files
- Organize files following BIDS format
- Deidentify files (replace subject ID, deface images, etc.)
- Upload processed data to Box

Currently, the pipeline supports MR data recorded at CBI.

## Installation
The pipeline can be installed either un Linux or WSL2. The installation script leverages the `apt` package manager, therefore Ubuntu and similar distributions are recommended.\
To use the software, download the repository to an appropriate folder (e.g. /opt). Navigate to the directory and make sure the `install.sh` script is executable (`chmod +x install.sh`). Then execute `./install.sh`.\
The installation script will install all required OS packages and will create a virtual Python environment for the application. The script will also make sure that [FSL](https://fsl.fmrib.ox.ac.uk/fsl) is available.

<details>
<summary>Notes on FSL</summary>

 The script will look for an existing installation of FSL by checking if `FSLDIR` is defined. If the FSL installation is not found, the script will install it automatically to your home directory. If you have a custom installation of FSL, make sure to add the `FSLDIR` to your environment variables _before_ running the installation script. For example, if your FSL installation is in /usr/local/fsl, make sure the following lines are in your .bashrc file:
```
export FSLDIR=/usr/local/fsl
. ${FSLDIR}/etc/fslconf/fsl.sh
```
 </details> <br/>

The script will then proceed to create all necessary directories. Finally, a cronjob will be created under the current user that will run the pipeline every hour. You can change the relevant line in the installation script if you need a different interval.

## Configuration
The software stores its configuration in multiple .json files located in the settings folder. Most of these files will be automatically generated when the pipeline is executed for the first time, but will likely cause errors as the default setting are incorrect. You can either modify the generated files, or create them manually.

### CBI configuration
These settings are needed to connect to the CBI Home server and to navigate to the correct project folder.

<details>
<summary>cbi_settings.json</summary>

```json
{
    "connection": {
        "host": "cbihome.musc.edu",
        "credentials_file": "settings/.cbicredentials.json"
    },
    "remote_data_dir": ""
}
```

`credentials_file` allows to set the location of the file containing the login credentials (see below)\
`remote_data_dir` allows to set the location of the project folder on CBI Home (e.g. "/MRdata/McTeague/DARPA_RECOVERS/upload")
 </details>
<details>
<summary>.cbicredentials.json</summary>

```json
{
    "user": "",
    "password": ""
}
```

`user` user name used to connect to CBI Home\
`password` password associated with above user\
\
__NOTE:__ this file is not generated automatically and will always need to be created manually. It can be stored anywhere on the system, as long as the corresponding setting in cbi_settings.json reflects this location. It is recommended to set the permissions of the file (e.g. chmod 640) so that only authorized users can view it.
 </details>

 ### Database configuration
 The application generates a database to keep track of study participants, sessions, data files etc. The relevant settings are stored in the database configuration file.

 <details>
<summary>database_settings.json</summary>

```json
{
    "db_path": "database/db.sqlite",
    "n_default_query_attempts": 5
}
```

`db_path` is the path to the database file. This can be a relative or absolute path\
`n_default_query_attempts` determines how many attempts will be made to run a query before returning an error. Occasionally queries can be blocked by other database transactions, although this should be rare.
 </details>

### Study configuration
The study configuration file contains settings that determine the format of the study and session IDs, and on how data will be deidentified.

 <details>
<summary>study_settings.json</summary>

```json
{
    "subject_identifier_format": {
        "regex": "[mM][0-9][0-9]+",
        "desired_prefix": "sub-",
        "desired_start_str": "M",
        "desired_digits": 3
    },
    "deidentify_data": true,
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
```

`subject_identifier_format`->`regex` is a regular expression used to find the subject ID in the raw data file names\
`subject_identifier_format`->`desired_prefix` is the desired prefix that will be added to the subject ID\
`subject_identifier_format`->`desired_start_str` is a string that will be added between the prefix and the subject number\
`subject_identifier_format`->`desired_digits` is the number of desired digits in the subject number.\
\
`deidentify_data` determines if data will be deidentified (true) or not (false)\
`deidentified_subject_identifier_format` determines how the deidentified subject ID will be formatted. The settings are equivalent to those available under `subject_identifier_format`\
\
`session_identifier_format`->`desired_prefix` is the desired prefix that will be added to the session ID\
`session_identifier_format`->`desired_digits` is the number of desired digits in the session number.
 </details>

### Data processing configuration
The data processing configuration file contains settings that determine how data will be processed and where it will be stored.

 <details>
<summary>processing_settings.json</summary>

```json
{
    "mri": {
        "workdir": "",
        "sourcedata_dir": "",
        "data_dir": "",
        "deidentified_data_dir": "",
        "summary_file_wait_timeout_h": 36
    }
}
```

`mri`->`workdir` is the location of the temporary work directory used by the processing scripts. Data in this folder will eventually be deleted, so the folder should not be seen as a permanent storage location.\
`mri`->`sourcedata_dir` is the directory where the source data will be stored. The path can be relative or absolute.\
`mri`->`data_dir` is the directory where data will be stored in BIDS format. The path can be relative or absolute.\
`mri`->`deidentified_data_dir` is the directory where all deidentified data will be stored (if data deidentification is enabled - see study configuration settings). The path can be relative or absolute.\
`mri`->`summary_file_wait_timeout_h` determines how long (in hours) the application will wait for the session summary file on CBI Home. If the file is not generated within this time frame, all validation steps requiring the summary file will be skipped

 </details>

### Notification settings
The application will send notifications when errors occurr or when new data needs to be vaildated by the user.

 <details>
<summary>notification_settings.json</summary>

```json
{
    "mail_server": {
        "address": "smtp.gmail.com",
        "port": 465,
        "user": "",
        "password": ""
    },
    "errors": {
        "send_notification": true,
        "subject": "Automated Pipeline: Error during pipeline execution",
        "recipients": [
            "test123@musc.edu"
        ]
    },
    "mri_data_validation": {
        "send_notification": true,
        "subject": "Automated Pipeline: MRI data validation required",
        "recipients": [
            "test123@musc.edu"
        ],
        "send_reminder": true,
        "reminder_interval_h": 24
    }
}
```

`mail_server`->`address` address of mail server (For gmail, information is available [online](https://support.google.com/a/answer/176600?hl=en)).\
`mail_server`->`address` port of mail server.\
`mail_server`->`user` is the user/account used to send e-mails. One option is to create a free gmail account used just for these notifications.\
`mail_server`->`password` is the password used to sign in to the above account. If using gmail, it is recommended to create an [app password](https://support.google.com/mail/answer/185833?hl=en)\
\
`errors`->`send_notification` determines whether error notificatns will be sent (true) or not (false)\
`errors`->`subject` is the string used as the subject of the e-mail notification\
`errors`->`recipients` is a list of recipients that will receive the notification. Addresses should be comma-separated\
\
`mri_data_validation`->`send_notification` determines whether mri data validation notificatns will be sent (true) or not (false)\
`mri_data_validation`->`subject` is the string used as the subject of the e-mail notification\
`mri_data_validation`->`recipients` is a list of recipients that will receive the notification. Addresses should be comma-separated\
`mri_data_validation`->`send_reminder` determines wheter reminder notifications will be sent if data is not validated within a given time\
`mri_data_validation`->`reminder_interval_h` sets the interval between reminder notifications\

 </details>

### dcm2bids settings
The application uses [dcm2niix](https://github.com/rordenlab/dcm2niix) and [dcm2bids](https://unfmontreal.github.io/Dcm2Bids) to convert MR images from raw DICOM files to NIfTI files in BIDS format. This requires a `dcm2bids_config.json` file to be in the settings folder. Instructions on how to create the configuration file are available [here](https://unfmontreal.github.io/Dcm2Bids/3.2.0/how-to/create-config-file/) and [here](https://unfmontreal.github.io/Dcm2Bids/3.2.0/tutorial/first-steps/#building-the-configuration-file).

### Box settings

The application can be configured to automatically upload data to Box. To do so, one first needs to configure a [Box developer account](https://developer.box.com/). Then, follow these steps:

1. Log in to the Box account and access the _Developer Console_.
<details><summary>screenshot</summary>

![Screenshot of where to access the Developer Console.](/docs/images/dev_console_1.png)

</details><br/>

2. Create a new _Platform App_
    - select "Custom App"
    - enter the app name and select a purpose ("Automation" is suggested)
    - select "Server Authentication (Client Credentials Grant)" as the authentication method. __This is important__.
    - click on "Create App"
3. Once the Platform App is created, go to "Configuration" and take note of the _Client ID_ and _Client Secret_ (found under OAuth 2.0 Credentials). We will need these later.
4. Under "App Access Level", select "App + Enterprise Access". Then, under "Application Scopes", make sure that "Read all files and folders stored in Box" and "Write all files and folders stored in Box" are checked. All other options in this section can be disabled.
5. Click on "Save Changes"
6. Go to the "General Settings" tab of the application, and take note of the "User ID". We will need this later.
7. Go to the "Authorization" tab and click on "Review and Submit". Enter an app description and click on "Submit".
8. Go back to your Box account ("Back to My Account"), then go to the _Admin Console_.
<details><summary>screenshot</summary>

![Screenshot of where to access the Admin Console.](/docs/images/admin_console_1.png)

</details><br/>

9. Navigate to "Integrations", then go to the "Platform Apps Manager" tab and click on the app you just created.
<details><summary>screenshot</summary>

![Screenshot of where to access the Platform Apps Manager.](/docs/images/admin_console_2.png)

</details><br/>

10. Click on "Authorize", and then again on "Authorize"


Next, we need to update the `box_sync_settings.json` file:

 <details>
<summary>box_sync_settings.json</summary>

```json
{
    "use_box_sync": true,
    "authentication": {
        "user_id": "",
        "client_id": "",
        "client_secret": ""
    },
    "sourcedata_dir_id": "",
    "data_dir_id": "",
    "deidentified_data_dir_id": ""
}
```

`use_box_sync` determines whether data will be uploaded to box (true) or not (false)\
\
`authentication`->`user_id` is the user ID we obtained in step 6 above\
`authentication`->`client_id` is the Client ID we obtained in step 3 above\
`authentication`->`client_secret` is the Client Secret we obtained in step 3 above\
\
`sourcedata_dir_id` is the ID of the Box folder where the source data will be uploaded.\
`data_dir_id` is the ID of the Box folder where the data in BIDS format will be uploaded.\
`deidentified_data_dir_id` is the ID of the Box folder where the deidentified data will be uploaded.

__NOTE:__ To get the ID of a folder on Box, go to your Box developer account and navigate to the folder. The URL in the address bar will contain the numeric folder ID (e.g. https://app.box.com/folder/__308004028317__). This applies both to folders owned by the account, and to folders shared with the account.\
The ID needs to be added as a string to the settings file, meaning it needs to be enclosed in quotation marks.

 </details>

 If you'd like to upload data to folders owned by a different account, share those folders with the developer account and take note of the correct folder IDs.

 ## Running the pipeline
 Once configured, the pipeline will run automatically every hour. User interaction is only needed for data validation, for exluding or including certain datasets and, if desired, for resetting the processing stage of one or more datasets.\
 The user can interact with the pipeline through the _Data Viewer_ GUI. The Data Viewer can be accessed by running the `run_data_viewer.sh` script.

 ### Participants
 The first visible view after opening the Data Viewer will be the _Participants_ view. This view shows a list of all participants, of their deidentified ID and of their group assignment. 
![Screenshot of the Participants view.](/docs/images/participants_1.png)
 
To add a new participant, click on the "New Participant" button and enter the participant's ID. Then click "OK".

If none of the participant's data has yet been fully processed, one can edit the participant by clicking on the "Edit" button. Once at least one data set has been fully processed, this option is not available anymore.
![Screenshot of the Edit Participant dialog.](/docs/images/participants_2.png)

Here you can enter a new de-identified ID, generate a random de-identified ID by clicking "Generate", and change the group assignment. Click "OK" to return to the main view.

### MRI sessions
To view all available MRI sessions, navigate to the "MRI" tab. This will show the date and time each session was recorded, the session description, the ID and de-identified ID of the associated participant, the associated session ID, and some flags indicating the validation and processing state of each session.
![Screenshot of the MRI Session view.](/docs/images/mri_sessions_1.png).

If a session has not yet been fully processed, or if the associated participant and session IDs still need to be validated, you will have the option to _Edit_ or _Validate_ the session. If the session has been fully processed, then this option will not be available.
![Screenshot of the MRI Edit Session dialog.](/docs/images/mri_sessions_2.png).

The Session Edit/Validate dialog allows to select the subject ID of the participant associated with this session. You can also create a new participant by clicking "New". The de-identified ID of the associated participant can be edited either by entering a new ID in the textbox, or by generating a new random ID with the "Generate" button. You can also use this dialog to change the group assignment of the participant.\
The dialog also allows to change the ID of the associated session. Finally, the "Skip processing" checkbox can be used to skip any future processing steps of this session. If selected, all associated data will be removed from the temporary work directory. You can always uncheck this option at a later stage.

Each session can also be reprocessed at any point if there are issues with any of the data processing stages. To do so, click on the "Reprocess" button. If the session has not yet been fully processed, you will have the option to only run the validation steps again, or to download the data again and fully reprocess it. If the data was already fully processed, you will only have the option to download and reprocess the data.

### MRI series
All series collected for a session can be viewed by going to the "Series" tab. The list to the left allows to select the session, while the table to the right shows information about all series in that session.
![Screenshot of the MRI Series view.](/docs/images/mri_series_1.png).

For each series, the table will show the acquisition date ant time, the series description and the number of files. It will also show if all files are valid (i.e. available and matching the CBI session summary) and if the sidecar file matches any of the criteria specified in the dcm2bids configuration file. The "Duplicates" column will indicate wheter there are any duplicate series that match the same dcm2bids criteria. If so, the pipeline will choose the most recent series by default and skip all other duplicates. The "Skip" column indicates wheter a series will be skipped (i.e. not processed), which is usually the case when the series has invalid data or when it has a more recent duplicate. Finally, the "Data Converted" column indicates if the data was successfully converted. When a session has not yet been fully processed, there will be the option to include or exclude it from processing. If you decide to include a series that has duplicates, all other duplicates will be automatically excluded.