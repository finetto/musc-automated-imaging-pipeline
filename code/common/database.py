# module with functions managing the MRI database
import os
import sqlite3
from filelock import FileLock, Timeout

class db:

    _connection = None
    _cursor = None
    lastrowid = None
    _lock = None

    # class constructor
    def __init__(self, db_file):
        
        # initialize connection and cursor
        self._connection = None
        self._cursor = None
        self.lastrowid = None

        # create necessary folders, if they don't exist
        db_folder = os.path.dirname(db_file)
        if (len(db_folder)>0) and (not os.path.isdir(db_folder)):
            os.makedirs(db_folder, exist_ok=True)

        # initialize file lock
        self._locked = False
        timeout = 5
        try:
            self._lock = FileLock(db_file + ".lock",timeout=0,mode=0o664)
        except Timeout as te:
                pass # will try again below
        except Exception as e:
            print("ERROR: Could not acquire database lock:")
            print(e)
            return
        
        while not self._lock.is_locked:
            try:
                self._lock.acquire(timeout=timeout)
            except Timeout as te:
                print("WARNING: Another process is currently accessing the database. Waiting for another " + str(timeout) + " s.")
                continue
            except Exception as e:
                print("ERROR: Could not acquire database lock:")
                print(e)
                return

        # initialize other attributes
        self.n_default_query_attempts = 2

        # open connection
        try:
            self._connection = sqlite3.connect(db_file)
            self._cursor = self._connection.cursor()
        except Exception as e:
            print("ERROR: Could not connect to database:")
            print(e)
            self._connection = None
            self._cursor = None
            self.lastrowid = None
            return

        # make sure all tables are in the database
        try:
            # create studies table if it doesn't exist
            self._cursor.execute("CREATE TABLE IF NOT EXISTS studies (\
                                id INTEGER PRIMARY KEY, \
                                title TEXT, \
                                description TEXT);")
            
            # create participants table if it doesn't exist
            self._cursor.execute("CREATE TABLE IF NOT EXISTS participants (\
                                id INTEGER PRIMARY KEY, \
                                study TEXT, \
                                study_id TEXT, \
                                deidentified_id TEXT, \
                                group_assignment TEXT);")

            # create mri sessions table if it doesn't exist
            self._cursor.execute("CREATE TABLE IF NOT EXISTS mri_sessions (\
                                id INTEGER PRIMARY KEY, \
                                study TEXT, \
                                participant_id INTEGER, \
                                participant_session_id TEXT, \
                                data_file TEXT, \
                                summary_file TEXT, \
                                description TEXT, \
                                data_recorded_date TEXT, \
                                data_recorded_time TEXT, \
                                data_recorded_dt REAL, \
                                data_downloaded_dt REAL, \
                                notification_sent_dt REAL, \
                                summary_downloaded_dt REAL, \
                                converted_to_nifti_dt REAL, \
                                conversion_validated_dt REAL, \
                                conversion_validated_with_summary_dt REAL, \
                                conversion_valid INTEGER, \
                                study_id_validated_dt REAL, \
                                session_id_validated_dt REAL, \
                                skip_processing INTEGER, \
                                data_converted_dt REAL, \
                                data_uploaded_dt REAL);")

            # create mri scans table if it doesn't exist
            self._cursor.execute("CREATE TABLE IF NOT EXISTS mri_series (\
                                id INTEGER PRIMARY KEY, \
                                study TEXT, \
                                participant_id INTEGER, \
                                session_id INTEGER, \
                                series_number INTEGER, \
                                series_recorded_dt REAL, \
                                description TEXT, \
                                number_files INTEGER, \
                                files_validated_dt REAL, \
                                files_validated_with_summary_dt REAL, \
                                files_valid INTEGER, \
                                dcm2bids_criteria TEXT, \
                                dcm2bids_criteria_in_config INTEGER, \
                                duplicate_series TEXT, \
                                skip_processing INTEGER, \
                                data_converted_dt REAL);")
            
            # participants, mri_sessions and mri_series tables originally did not have the "study" column
            # therefore, we need to check if it should be added
            if not self.column_exists(table="participants", column="study"):
                self._cursor.execute("ALTER TABLE participants ADD COLUMN study TEXT;")

            if not self.column_exists(table="mri_sessions", column="study"):
                self._cursor.execute("ALTER TABLE mri_sessions ADD COLUMN study TEXT;")

            if not self.column_exists(table="mri_series", column="study"):
                self._cursor.execute("ALTER TABLE mri_series ADD COLUMN study TEXT;")

            # commit changes (just to be safe, this does not seem to be necessary but doesn't hurt)
            self._connection.commit()

        except Exception as e:
            print("ERROR: Could not initialize database:")
            print(e)
            self._connection = None
            self._cursor = None
            self.lastrowid = None
            return

    # class destructor
    def __del__(self):
        self.close()        

    # close database connection
    def close(self):
        if (self._connection != None):
            self._connection.close()

        del self._cursor, self._connection
        self._connection = None
        self._cursor = None
        self.lastrowid = None    

        # release lock
        while self._lock.is_locked:
            self._lock.release()      


    # execute command
    def execute(self, cmd, parameters = (), n_attempts = None):

        # make sure connection is open
        if (self._connection == None) or (self._cursor == None):
            print("ERROR: Database not opened.")
            return -1
        
        # check if number of attempts was provided
        if n_attempts != None:
            attempts = n_attempts
        else:
            attempts = self.n_default_query_attempts
        
        # execute query
        # if an error is caught, try again
        success = False
        result = -1
        for i in range (attempts):
            try:
                self._cursor.execute(cmd, parameters)
                result = self._cursor.fetchall()
                self.lastrowid = self._cursor.lastrowid
                success = True
            except Exception as e:
                print("WARNING: Could not execute database query:")
                print(e)
                print("Remaining attempts: " + str(attempts-i-1) + "/" + str(attempts))
                self.lastrowid = None
                success = False
                result = -1
                continue

            if success:
                break

        if not success:
            print("ERROR: Failed to execute query: \"" + cmd + "\"")
            if parameters:
                print("with parameters:")
                print(parameters)

        return result
    

    # commit changes
    def commit(self):

        # make sure connection is open
        if (self._connection == None) or (self._cursor == None):
            print("ERROR: Database not opened.")
            return -1
        
        # execute commit
        self._connection.commit()

    # check if table exists
    def table_exists(self, table=""):

        # make sure connection is open
        if (self._connection == None) or (self._cursor == None):
            print("ERROR: Database not opened.")
            return -1
        
        # make sure table is a valid string
        if (table == None) or (not isinstance(table, str)) or (table == ""):
            print("ERROR: Invalid table name.")
            return -1

        # generate query
        cmd = "SELECT * FROM sqlite_schema WHERE type='table' AND name='" + table + "'"
        
        # execute query
        res = self.execute(cmd)
        if res == -1:
            print("ERROR: Could not check if table exists.")
            return -1
        
        # check result
        return (res!=None) and (len(res)>0)
    
    # check if column exists
    def column_exists(self, table="", column=""):

        # make sure connection is open
        if (self._connection == None) or (self._cursor == None):
            print("ERROR: Database not opened.")
            return -1
        
        # make sure table is a valid string
        if (table == None) or (not isinstance(table, str)) or (table == ""):
            print("ERROR: Invalid table name.")
            return -1
        
        # make sure column is a valid string
        if (column == None) or (not isinstance(column, str)) or (column == ""):
            print("ERROR: Invalid column name.")
            return -1

        # generate query
        cmd = "PRAGMA table_info(" + table + ")"
        
        # execute query
        res = self.execute(cmd)
        if res == -1:
            print("ERROR: Could not check if column exists.")
            return -1
        
        column_found = False
        for column_info in res:
            if column_info[1]==column:
                column_found = True
                break
        
        # check result
        return column_found

    
    # add record
    def add_record(self, table_name, query_args):

        # make sure connection is open
        if (self._connection == None) or (self._cursor == None):
            print("ERROR: Database not opened.")
            return -1
        
        # make sure there is data to add
        if query_args["n_columns"] <=0:
            print("ERROR: Table can't be updated because no data was provided.")
            return -1
        
        # generate query command
        cmd = "INSERT INTO " + table_name + " (" + query_args["columns"] + ") VALUES (" + query_args["questionmarks"] + ");"
        
        # generate parameter list
        params = tuple(query_args["values"])

        # run query
        res = self.execute(cmd, params)
        if res == -1: 
            print("ERROR: Could not add record to table '" + table_name + "'.")
            return -1
        
        # get id
        res = self.execute("SELECT * FROM " + table_name + " WHERE rowid = ?;",(self.lastrowid,))
        if res == -1: 
            print("ERROR: Could not find record added to table '" + table_name + "'.")
            return -1
        
        # return id
        if (res!=None) and (len(res)>0):
            return res[0][0]
        else:
            return None

    # update record
    def update_record(self, table_name, id, query_args):

        # make sure connection is open
        if (self._connection == None) or (self._cursor == None):
            print("ERROR: Database not opened.")
            return -1
        
        # make sure there is data to add
        if query_args["n_columns"] <=0:
            print("ERROR: Table can't be updated because no data was provided.")
            return -1

        # generate query command
        cmd = "UPDATE " + table_name + " SET " + query_args["columns_and_questionmarks"] + " WHERE id = ?;"
        
        # generate parameter list
        params = list(query_args["values"])
        params.append(id)
        params = tuple(params)

        # run query
        res = self.execute(cmd, params)
        if res == -1: 
            print("ERROR: Could not update record in table '" + table_name + "'.")
            return -1

        # success
        return 1
    
    # remove record
    def remove_record(self, table_name, id):

        # make sure connection is open
        if (self._connection == None) or (self._cursor == None):
            print("ERROR: Database not opened.")
            return -1
        
        # generate query command
        cmd = "DELETE FROM " + table_name + " WHERE id = ?;"
        
        # generate parameter list
        params = (id,)

        # run query
        res = self.execute(cmd, params)
        if res == -1: 
            print("ERROR: Could not remove record from table '" + table_name + "'.")
            return -1
        
        # success
        return 1
    
    # get records by multiple keys
    def get_records_by_keys(self, table_name, keys, sort_column=None, sort_dir=None):

        # make sure connection is open
        if (self._connection == None) or (self._cursor == None):
            print("ERROR: Database not opened.")
            return -1
        
        # parse key columns and values
        conditions = ""
        key_values = []
        for key, value in keys.items():
            conditions = conditions + "(" + key + " = ?) AND "
            key_values.append(value)
        conditions = conditions[:-5]
        
        # get data and sort if requested
        if sort_column == None:
            qry_res = self.execute("SELECT * FROM " + table_name + " WHERE " + conditions + ";",list(key_values))
        else:
            if (sort_dir != None) and any(item.lower() == sort_dir.lower() for item in ("ASC", "ascending", "+")):
                direction = "ASC"
            elif (sort_dir != None) and any(item.lower() == sort_dir.lower() for item in ("DESC", "descending", "-")):
                direction = "DESC"
            else:
                direction = "ASC"

            qry_res = self.execute("SELECT * FROM " + table_name + " WHERE " + conditions + " ORDER BY " + sort_column + " " + direction + ";",list(key_values))   
        if qry_res == -1: 
            print("ERROR: Could not get matching records from table '" + table_name + "'.")
            return -1
        
        # get table information (containing column names)
        info_res = self.execute("PRAGMA table_info(" + table_name + ");")
        if info_res == -1: 
            print("ERROR: Could not get information for table '" + table_name + "'.")
            return -1
        
        if (qry_res==None) or (len(qry_res)<1) or (info_res==None) or (len(info_res)<1):
            return None
        
        # get column names
        column_names = []
        for column in info_res:
            column_names.append(column[1])

        # convert data to dict
        res = []
        for row in qry_res:
            res.append(dict(zip(column_names, row)))

        return res

    # get record id by key
    def get_record_id_by_keys(self, table_name, keys):

        # make sure connection is open
        if (self._connection == None) or (self._cursor == None):
            print("ERROR: Database not opened.")
            return -1
        
        res = self.get_records_by_keys(table_name, keys)
        if res == -1: 
            print("ERROR: Could not check if record exists in table '" + table_name + "'.")
            return -1

        if (res!=None) and (len(res)>0):
            if "id" in res[0]:
                return res[0]["id"] # get column named "id"
            else:
                key, value = list(res.items())[0] # get first column
                return value
        else:
            return None
        
    # add study to database
    def add_study(self,
                  title = None,
                  description = None):

        # get input arguments
        args = locals()

        # get query arguments from input arguments
        query_args = self.dict_to_query_input(args)

        # update table
        res = self.add_record("studies", query_args)

        return res

    # add participant to database
    def add_participant(self,
                        study = None,
                        study_id = None,
                        deidentified_id = None,
                        group_assignment = None):

        # get input arguments
        args = locals()

        # get query arguments from input arguments
        query_args = self.dict_to_query_input(args)

        # update table
        res = self.add_record("participants", query_args)

        return res
        
    # add mri session to database
    def add_mri_session(self,
                    study = None,
                    participant_id = None,
                    participant_session_id = None,
                    data_file = None,
                    summary_file = None,
                    description = None,
                    data_recorded_date = None,
                    data_recorded_time = None,
                    data_recorded_dt = None,
                    data_downloaded_dt = None,
                    notification_sent_dt = None,
                    summary_downloaded_dt = None,
                    converted_to_nifti_dt = None,
                    conversion_validated_dt = None,
                    conversion_validated_with_summary_dt = None,
                    conversion_valid = None,
                    study_id_validated_dt = None,
                    session_id_validated_dt = None,
                    skip_processing = None,
                    data_converted_dt = None,
                    data_uploaded_dt = None):

        # get input arguments
        args = locals()

        # get query arguments from input arguments
        query_args = self.dict_to_query_input(args)

        # update table
        res = self.add_record("mri_sessions", query_args)

        return res
    
    # add mri scan to database
    def add_mri_series(self,
                       study = None,
                       participant_id = None,
                       session_id = None,
                       series_number = None,
                       series_recorded_dt = None,
                       description = None,
                       number_files = None,
                       files_validated_dt = None,
                       files_validated_with_summary_dt = None,
                       files_valid = None,
                       dcm2bids_criteria = None,
                       dcm2bids_criteria_in_config = None,
                       duplicate_series = None,
                       skip_processing = None,
                       data_converted_dt = None):

        # get input arguments
        args = locals()

        # get query arguments from input arguments
        query_args = self.dict_to_query_input(args)

        # update table
        res = self.add_record("mri_series", query_args)

        return res
    
    # update study
    def update_study(self,
                  title = None,
                  description = None):
        
        # get input arguments
        args = locals()

        # get query arguments from input arguments
        query_args = self.dict_to_query_input(args, ("id",))

        # update table
        res = self.update_record("studies", id, query_args)

        return res
    
    # update participant
    def update_participant(self, id, 
                           study = None,
                           study_id = None,
                           deidentified_id = None,
                           group_assignment = None):
        
        # get input arguments
        args = locals()

        # get query arguments from input arguments
        query_args = self.dict_to_query_input(args, ("id",))

        # update table
        res = self.update_record("participants", id, query_args)

        return res

    # update mri session
    def update_mri_session(self, id, 
                       study = None,
                       participant_id = None,
                       participant_session_id = None,
                       data_file = None,
                       summary_file = None,
                       description = None,
                       data_recorded_date = None,
                       data_recorded_time = None,
                       data_recorded_dt = None,
                       data_downloaded_dt = None,
                       notification_sent_dt = None,
                       summary_downloaded_dt = None,
                       converted_to_nifti_dt = None,
                       conversion_validated_dt = None,
                       conversion_validated_with_summary_dt = None,
                       conversion_valid = None,
                       study_id_validated_dt = None,
                       session_id_validated_dt = None,
                       skip_processing = None,
                       data_converted_dt = None,
                       data_uploaded_dt = None):
        
        # get input arguments
        args = locals()

        # get query arguments from input arguments
        query_args = self.dict_to_query_input(args, ("id",))

        # update table
        res = self.update_record("mri_sessions", id, query_args)

        return res
        
     # update mri scan
    def update_mri_series(self, id,
                       study = None, 
                       participant_id = None,
                       session_id = None,
                       series_number = None,
                       series_recorded_dt = None,
                       description = None,
                       number_files = None,
                       files_validated_dt = None,
                       files_validated_with_summary_dt = None,
                       files_valid = None,
                       dcm2bids_criteria = None,
                       dcm2bids_criteria_in_config = None,
                       duplicate_series = None,
                       skip_processing = None,
                       data_converted_dt = None):
        
        # get input arguments
        args = locals()

        # get query arguments from input arguments
        query_args = self.dict_to_query_input(args, ("id",))

        # update table
        res = self.update_record("mri_series", id, query_args)

        return res
    
    # clear values from study
    def clear_values_from_study(self,
                  title = None,
                  description = None):
        
        # get input arguments
        args = locals()

        # get query arguments from input arguments
        query_args = self.dict_to_query_input(args, ("id",))

        # set all values to None
        for i in range(len(query_args["values"])):
            query_args["values"][i] = None

        # update table
        res = self.update_record("studies", id, query_args)

        return res

    # clear values from participant
    def clear_values_from_participant(self, id, 
                           study = None,
                           study_id = None,
                           deidentified_id = None,
                           group_assignment = None):
        
        # get input arguments
        args = locals()

        # get query arguments from input arguments
        query_args = self.dict_to_query_input(args, ("id",))

        # set all values to None
        for i in range(len(query_args["values"])):
            query_args["values"][i] = None

        # update table
        res = self.update_record("participants", id, query_args)

        return res

    # clear values from mri session
    def clear_values_from_mri_session(self, id,
                       study = None, 
                       participant_id = None,
                       participant_session_id = None,
                       data_file = None,
                       summary_file = None,
                       description = None,
                       data_recorded_date = None,
                       data_recorded_time = None,
                       data_recorded_dt = None,
                       data_downloaded_dt = None,
                       notification_sent_dt = None,
                       summary_downloaded_dt = None,
                       converted_to_nifti_dt = None,
                       conversion_validated_dt = None,
                       conversion_validated_with_summary_dt = None,
                       conversion_valid = None,
                       study_id_validated_dt = None,
                       session_id_validated_dt = None,
                       skip_processing = None,
                       data_converted_dt = None,
                       data_uploaded_dt = None):
        
        # get input arguments
        args = locals()

        # get query arguments from input arguments
        query_args = self.dict_to_query_input(args, ("id",))

        # set all values to None
        for i in range(len(query_args["values"])):
            query_args["values"][i] = None

        # update table
        res = self.update_record("mri_sessions", id, query_args)

        return res
        
    # clear values from mri series
    def clear_values_from_mri_series(self, id,
                       study = None, 
                       participant_id = None,
                       session_id = None,
                       series_number = None,
                       series_recorded_dt = None,
                       description = None,
                       number_files = None,
                       files_validated_dt = None,
                       files_validated_with_summary_dt = None,
                       files_valid = None,
                       dcm2bids_criteria = None,
                       dcm2bids_criteria_in_config = None,
                       duplicate_series = None,
                       skip_processing = None,
                       data_converted_dt = None):
        
        # get input arguments
        args = locals()

        # get query arguments from input arguments
        query_args = self.dict_to_query_input(args, ("id",))

        # set all values to None
        for i in range(len(query_args["values"])):
            query_args["values"][i] = None

        # update table
        res = self.update_record("mri_series", id, query_args)

        return res
    
    # remove study
    def remove_study(self, id):
        return self.remove_record("studies", id)

    # remove participant
    def remove_participant(self, id):
        return self.remove_record("participants", id)
    
    # remove mri session
    def remove_mri_session(self, id):
        return self.remove_record("mri_sessions", id)
    
    # remove mri series
    def remove_mri_series(self, id):
        return self.remove_record("mri_series", id)
    
    # get study from database
    def get_study(self, title=None, description=None):

        # get input arguments
        args = locals()
        keys = self.remove_keys_from_dict(args, ("self",))

        if len(keys)<1:
            res = -1
        else:
            res = self.get_record_id_by_keys("studies", keys)

        return res

    # get participant id from database
    def get_participant_id(self, study=None, study_id=None, deidentified_id=None):

        # get input arguments
        args = locals()
        keys = self.remove_keys_from_dict(args, ("self",))

        if len(keys)<1:
            res = -1
        else:
            res = self.get_record_id_by_keys("participants", keys)

        return res
        
    # get participant data
    def get_participant_data(self, id=None, study=None, study_id=None, deidentified_id=None, return_only_first=False, sort_column=None, sort_dir=None):

        # get input arguments
        args = locals()
        keys = self.remove_keys_from_dict(args, ("self", "return_only_first", "sort_column", "sort_dir"))

        if len(keys)<1:
            res = -1
        else:
            res = self.get_records_by_keys("participants", keys, sort_column, sort_dir)

        if (res!=None) and (res != -1) and return_only_first:
            if len(res)>0:
                return res[0]
            else:
                return None
        else:
            return res
    
    # get all participants
    def get_all_participant_data(self, sort_column=None, sort_dir=None):

        # make sure connection is open
        if (self._connection == None) or (self._cursor == None):
            print("ERROR: Database not opened.")
            return -1
        
        # get data and sort if requested
        if sort_column == None:
            qry_res = self.execute("SELECT * FROM participants;")
        else:
            if (sort_dir != None) and any(item.lower() == sort_dir.lower() for item in ("ASC", "ascending", "+")):
                direction = "ASC"
            elif (sort_dir != None) and any(item.lower() == sort_dir.lower() for item in ("DESC", "descending", "-")):
                direction = "DESC"
            else:
                direction = "ASC"

            qry_res = self.execute("SELECT * FROM participants ORDER BY " + sort_column + " " + direction + ";")

        if qry_res == -1: 
            print("ERROR: Could not get all participants.")
            return -1
        
        # get table information (containing column names)
        info_res = self.execute("PRAGMA table_info(participants);")
        if info_res == -1: 
            print("ERROR: Could not get information for table 'participants'.")
            return -1
        
        if (qry_res==None) or (info_res==None):
            return None
        
        # get column names
        column_names = []
        for column in info_res:
            column_names.append(column[1])

        # convert data to dict
        res = []
        for row in qry_res:
            res.append(dict(zip(column_names, row)))
        
        return res  
    
    # get mri session id from database
    def get_mri_session_id(self, data_file=None, study=None):

        # get input arguments
        args = locals()
        keys = self.remove_keys_from_dict(args, ("self",))

        if len(keys)<1:
            res = -1
        else:
            res = self.get_record_id_by_keys("mri_sessions", keys)

        return res
    
    # get MRI session data
    def get_mri_session_data(self, id=None, data_file=None, study=None, participant_id=None, return_only_first=False, sort_column=None, sort_dir=None):

        # get input arguments
        args = locals()
        keys = self.remove_keys_from_dict(args, ("self", "return_only_first", "sort_column", "sort_dir"))

        if len(keys)<1:
            res = -1
        else:
            res = self.get_records_by_keys("mri_sessions", keys, sort_column, sort_dir)

        if (res!=None) and (res != -1) and return_only_first:
            if len(res)>0:
                return res[0]
            else:
                return None
        else:
            return res

    # get all MRI sessions
    def get_all_mri_session_data(self, sort_column=None, sort_dir=None):

        # make sure connection is open
        if (self._connection == None) or (self._cursor == None):
            print("ERROR: Database not opened.")
            return -1

        # get data and sort if requested
        if sort_column == None:
            qry_res = self.execute("SELECT * FROM mri_sessions;")
        else:
            if (sort_dir != None) and any(item.lower() == sort_dir.lower() for item in ("ASC", "ascending", "+")):
                direction = "ASC"
            elif (sort_dir != None) and any(item.lower() == sort_dir.lower() for item in ("DESC", "descending", "-")):
                direction = "DESC"
            else:
                direction = "ASC"

            qry_res = self.execute("SELECT * FROM mri_sessions ORDER BY " + sort_column + " " + direction + ";")

        if qry_res == -1: 
            print("ERROR: Could not get all MRI sessions.")
            return -1
        
        # get table information (containing column names)
        info_res = self.execute("PRAGMA table_info(mri_sessions);")
        if info_res == -1: 
            print("ERROR: Could not get information for table 'mri_sessions'.")
            return -1
        
        if (qry_res==None) or (info_res==None):
            return None
        
        # get column names
        column_names = []
        for column in info_res:
            column_names.append(column[1])

        # convert data to dict
        res = []
        for row in qry_res:
            res.append(dict(zip(column_names, row)))
        
        return res 
    
    # get MRI scan data
    def get_mri_series_data(self, id=None, session_id=None, study=None, participant_id=None, series_number=None, return_only_first=False, sort_column=None, sort_dir=None):

        # get input arguments
        args = locals()
        keys = self.remove_keys_from_dict(args, ("self", "return_only_first", "sort_column", "sort_dir"))

        if len(keys)<1:
            res = -1
        else:
            res = self.get_records_by_keys("mri_series", keys, sort_column, sort_dir)

        if (res!=None) and (res != -1) and return_only_first:
            if len(res)>0:
                return res[0]
            else:
                return None
        else:
            return res

    # get all MRI scans
    def get_all_mri_series_data(self):

        # make sure connection is open
        if (self._connection == None) or (self._cursor == None):
            print("ERROR: Database not opened.")
            return -1
        
        # get data
        qry_res = self.execute("SELECT * FROM mri_series;")
        if qry_res == -1: 
            print("ERROR: Could not get all MRI series.")
            return -1
        
        # get table information (containing column names)
        info_res = self.execute("PRAGMA table_info(mri_series);")
        if info_res == -1: 
            print("ERROR: Could not get information for table 'mri_series'.")
            return -1
        
        if (qry_res==None) or (info_res==None):
            return None
        
        # get column names
        column_names = []
        for column in info_res:
            column_names.append(column[1])

        # convert data to dict
        res = []
        for row in qry_res:
            res.append(dict(zip(column_names, row)))

        return res  

    # find mri sessions with missing summary file
    def find_mri_sessions_with_missing_summary(self, exclude_skipped = False):

        # make sure connection is open
        if (self._connection == None) or (self._cursor == None):
            print("ERROR: Database not opened.")
            return -1

        # get data
        column_names = ["id", "data_file", "data_recorded_date", "data_recorded_time"]
        column_list = ", ".join(column_names)
        if exclude_skipped:
            qry_res = self.execute("SELECT " + column_list + " FROM mri_sessions WHERE ((summary_file IS NULL) OR (summary_file == \"\")) AND (skip_processing IS NOT 1);")
        else:
            qry_res = self.execute("SELECT " + column_list + " FROM mri_sessions WHERE (summary_file IS NULL) OR (summary_file == \"\");")
        if qry_res == -1: 
            print("ERROR: Could not get MRI sessions with missing summary from database.")
            return -1
        
        if (qry_res==None):
            return None
        
        # convert data to dict
        res = []
        for row in qry_res:
            res.append(dict(zip(column_names, row)))
        
        return res   
    
    # find mri sessions for which data still needs to be downloaded
    def find_mri_sessions_requiring_data_download(self, exclude_skipped = False):

        # make sure connection is open
        if (self._connection == None) or (self._cursor == None):
            print("ERROR: Database not opened.")
            return -1

        # get data
        column_names = ["id", "data_file"]
        column_list = ", ".join(column_names)
        if exclude_skipped:
            qry_res = self.execute("SELECT " + column_list + " FROM mri_sessions WHERE (data_downloaded_dt IS NULL) AND (skip_processing IS NOT 1);")
        else:
            qry_res = self.execute("SELECT " + column_list + " FROM mri_sessions WHERE data_downloaded_dt IS NULL;")
        if qry_res == -1: 
            print("ERROR: Could not get MRI sessions with missing summary from database.")
            return -1
        
        if (qry_res==None):
            return None
        
        # convert data to dict
        res = []
        for row in qry_res:
            res.append(dict(zip(column_names, row)))
        
        return res  
    
    # find mri sessions for which summary files still needs to be downloaded
    def find_mri_sessions_requiring_summary_download(self, exclude_skipped = False):

        # make sure connection is open
        if (self._connection == None) or (self._cursor == None):
            print("ERROR: Database not opened.")
            return -1

        # get data
        column_names = ["id", "data_file", "summary_file"]
        column_list = ", ".join(column_names)
        if exclude_skipped:
            qry_res = self.execute("SELECT " + column_list + " FROM mri_sessions WHERE (summary_file IS NOT NULL) AND (summary_file != \"\") AND (summary_downloaded_dt IS NULL) AND (skip_processing IS NOT 1);")
        else:
            qry_res = self.execute("SELECT " + column_list + " FROM mri_sessions WHERE (summary_file IS NOT NULL) AND (summary_file != \"\") AND (summary_downloaded_dt IS NULL);")
        if qry_res == -1: 
            print("ERROR: Could not get MRI sessions with missing summary from database.")
            return -1
        
        if (qry_res==None):
            return None
        
        # convert data to dict
        res = []
        for row in qry_res:
            res.append(dict(zip(column_names, row)))

        return res 
    
    # find all mri sessions for which no notification has been sent
    def find_mri_sessions_requiring_first_notification(self, exclude_skipped = False):

        # make sure connection is open
        if (self._connection == None) or (self._cursor == None):
            print("ERROR: Database not opened.")
            return -1
        
        # get data
        column_names = ["id", "description", "data_recorded_date", "data_recorded_time"]
        column_list = ", ".join(column_names)
        if exclude_skipped:
            qry_res = self.execute("SELECT " + column_list + " FROM mri_sessions WHERE (notification_sent_dt IS NULL) AND (skip_processing IS NOT 1);")
        else:
            qry_res = self.execute("SELECT " + column_list + " FROM mri_sessions WHERE notification_sent_dt IS NULL;")
        if qry_res == -1: 
            print("ERROR: Could not get MRI sessions requirig first notification from database.")
            return -1
        
        if (qry_res==None):
            return None
        
        # convert data to dict
        res = []
        for row in qry_res:
            res.append(dict(zip(column_names, row)))

        return res  
    
    # find all mri sessions for which a notification has been sent, but that have not been validated yet
    def find_mri_sessions_requiring_reminder_notification(self, exclude_skipped = False):

        # make sure connection is open
        if (self._connection == None) or (self._cursor == None):
            print("ERROR: Database not opened.")
            return -1
        
        # get data
        column_names = ["id", "description", "data_recorded_date", "data_recorded_time", "notification_sent_dt"]
        column_list = ", ".join(column_names)
        if exclude_skipped:
            qry_res = self.execute("SELECT " + column_list + " FROM mri_sessions WHERE (notification_sent_dt IS NOT NULL) AND ((study_id_validated_dt IS NULL) OR (session_id_validated_dt IS NULL)) AND (skip_processing IS NOT 1);")
        else:
            qry_res = self.execute("SELECT " + column_list + " FROM mri_sessions WHERE (notification_sent_dt IS NOT NULL) AND ((study_id_validated_dt IS NULL) OR (session_id_validated_dt IS NULL));")
        if qry_res == -1: 
            print("ERROR: Could not get MRI sessions requirig reminder notification from database.")
            return -1
        
        if (qry_res==None):
            return None
        
        # convert data to dict
        res = []
        for row in qry_res:
            res.append(dict(zip(column_names, row)))

        return res   
    
    # find all mri sessions for which data is available but not yet extracted and converted to nifti
    def find_mri_sessions_requiring_conversion_to_nifti(self, exclude_skipped = False):
        # make sure connection is open
        if (self._connection == None) or (self._cursor == None):
            print("ERROR: Database not opened.")
            return -1
        
        # get data
        column_names = ["id", "participant_id", "data_file"]
        column_list = ", ".join(column_names)

        if exclude_skipped:
            qry_res = self.execute("SELECT " + column_list + " FROM mri_sessions WHERE (data_downloaded_dt IS NOT NULL) AND (converted_to_nifti_dt IS NULL) AND (skip_processing IS NOT 1);")
        else:
            qry_res = self.execute("SELECT " + column_list + " FROM mri_sessions WHERE (data_downloaded_dt IS NOT NULL) AND (converted_to_nifti_dt IS NULL);")
        if qry_res == -1: 
            print("ERROR: Could not get MRI sessions requirig nifti conversion from database.")
            return -1
        
        if (qry_res==None):
            return None
        
        # convert data to dict
        res = []
        for row in qry_res:
            res.append(dict(zip(column_names, row)))

        return res  

    # find all mri sessions for which data is available and extracted but not yet validated
    def find_mri_sessions_requiring_data_validation(self, exclude_skipped = False):
        # make sure connection is open
        if (self._connection == None) or (self._cursor == None):
            print("ERROR: Database not opened.")
            return -1
        
        # get data
        column_names = ["id", "participant_id", "data_file"]
        column_list = ", ".join(column_names)

        if exclude_skipped:
            qry_res = self.execute("SELECT " + column_list + " FROM mri_sessions WHERE (data_downloaded_dt IS NOT NULL) AND (converted_to_nifti_dt IS NOT NULL) AND (conversion_validated_dt IS NULL) AND (skip_processing IS NOT 1);")
        else:
            qry_res = self.execute("SELECT " + column_list + " FROM mri_sessions WHERE (data_downloaded_dt IS NOT NULL) AND (converted_to_nifti_dt IS NOT NULL) AND (conversion_validated_dt IS NULL);")
        if qry_res == -1: 
            print("ERROR: Could not get MRI sessions requirig data validation from database.")
            return -1
        
        if (qry_res==None):
            return None
        
        # convert data to dict
        res = []
        for row in qry_res:
            res.append(dict(zip(column_names, row)))

        return res   

    # find all mri sessions for which data is available and validated but not yet validated with summary
    def find_mri_sessions_requiring_data_validation_with_summary(self, exclude_skipped = False):
        # make sure connection is open
        if (self._connection == None) or (self._cursor == None):
            print("ERROR: Database not opened.")
            return -1
        
        # get data
        column_names = ["id", "participant_id", "data_file", "summary_file", "data_recorded_dt", "summary_downloaded_dt", "conversion_valid"]
        column_list = ", ".join(column_names)

        if exclude_skipped:
            qry_res = self.execute("SELECT " + column_list + " FROM mri_sessions WHERE (data_downloaded_dt IS NOT NULL) AND (converted_to_nifti_dt IS NOT NULL) AND (conversion_validated_dt IS NOT NULL) AND (conversion_validated_with_summary_dt IS NULL) AND (skip_processing IS NOT 1);")
        else:
            qry_res = self.execute("SELECT " + column_list + " FROM mri_sessions WHERE (data_downloaded_dt IS NOT NULL) AND (converted_to_nifti_dt IS NOT NULL) AND (conversion_validated_dt IS NOT NULL) AND (conversion_validated_with_summary_dt IS NULL);")
        if qry_res == -1: 
            print("ERROR: Could not get MRI sessions requirig data validation with summary from database.")
            return -1
        
        if (qry_res==None):
            return None
        
        # convert data to dict
        res = []
        for row in qry_res:
            res.append(dict(zip(column_names, row)))

        return res  

    # find duplicate series for session
    def find_duplicate_series_in_session(self, session_id):
        # make sure connection is open
        if (self._connection == None) or (self._cursor == None):
            print("ERROR: Database not opened.")
            return -1
        
        # get data
        column_names = ["id", "participant_id", "session_id", "series_number", "duplicate_series"]
        column_list = ", ".join(column_names)

        qry_res = self.execute("SELECT " + column_list + " FROM mri_series WHERE (session_id = ?) AND (duplicate_series IS NOT NULL);", (session_id,))
        if qry_res == -1: 
            print("ERROR: Could not get duplicate MRI series from database.")
            return -1
        
        if (qry_res==None):
            return None
        
        # convert data to dict
        res = []
        for row in qry_res:
            res.append(dict(zip(column_names, row)))

        return res  

    # find all mri sessions for which data is available but not yet converted to BIDS
    def find_mri_sessions_requiring_conversion_to_bids(self, exclude_skipped = False):
        # make sure connection is open
        if (self._connection == None) or (self._cursor == None):
            print("ERROR: Database not opened.")
            return -1
        
        # get data
        column_names = ["id", "participant_id", "data_file", "summary_file", "participant_session_id"]
        column_list = ", ".join(column_names)

        filter = "(data_downloaded_dt IS NOT NULL) \
        AND (converted_to_nifti_dt IS NOT NULL) \
        AND (conversion_validated_dt IS NOT NULL) AND (conversion_validated_with_summary_dt IS NOT NULL) AND (conversion_valid IS 1) \
        AND (study_id_validated_dt IS NOT NULL) AND (session_id_validated_dt IS NOT NULL) \
        AND (participant_id IS NOT NULL) \
        AND (participant_session_id IS NOT NULL) AND (participant_session_id IS NOT \"\") \
        AND (data_converted_dt IS NULL)"
        if exclude_skipped:
            qry_res = self.execute("SELECT " + column_list + " FROM mri_sessions WHERE " + filter + " AND (skip_processing IS NOT 1);")
        else:
            qry_res = self.execute("SELECT " + column_list + " FROM mri_sessions WHERE " + filter + ";")
        if qry_res == -1: 
            print("ERROR: Could not get MRI sessions requirig BIDS conversion from database.")
            return -1
        
        if (qry_res==None):
            return None
        
        # convert data to dict
        res = []
        for row in qry_res:
            res.append(dict(zip(column_names, row)))

        return res
    
    # find all mri sessions for which data was converted to BIDS but not yet uploaded
    def find_mri_sessions_requiring_upload(self, exclude_skipped = False):
        # make sure connection is open
        if (self._connection == None) or (self._cursor == None):
            print("ERROR: Database not opened.")
            return -1
        
        # get data
        column_names = ["id", "participant_id", "data_file", "summary_file", "participant_session_id"]
        column_list = ", ".join(column_names)

        filter = "(data_downloaded_dt IS NOT NULL) \
        AND (converted_to_nifti_dt IS NOT NULL) \
        AND (conversion_validated_dt IS NOT NULL) AND (conversion_validated_with_summary_dt IS NOT NULL) AND (conversion_valid IS 1) \
        AND (study_id_validated_dt IS NOT NULL) AND (session_id_validated_dt IS NOT NULL) \
        AND (participant_id IS NOT NULL) \
        AND (participant_session_id IS NOT NULL) AND (participant_session_id IS NOT \"\") \
        AND (data_converted_dt IS NOT NULL) \
        AND (data_uploaded_dt IS NULL)"
        if exclude_skipped:
            qry_res = self.execute("SELECT " + column_list + " FROM mri_sessions WHERE " + filter + " AND (skip_processing IS NOT 1);")
        else:
            qry_res = self.execute("SELECT " + column_list + " FROM mri_sessions WHERE " + filter + ";")
        if qry_res == -1: 
            print("ERROR: Could not get MRI sessions requirig data upload from database.")
            return -1
        
        if (qry_res==None):
            return None
        
        # convert data to dict
        res = []
        for row in qry_res:
            res.append(dict(zip(column_names, row)))

        return res
    
    # find all mri sessions for which data can be removed
    def find_mri_sessions_ready_for_cleanup(self):
        # make sure connection is open
        if (self._connection == None) or (self._cursor == None):
            print("ERROR: Database not opened.")
            return -1
        
        # get data
        column_names = ["id", "participant_id", "data_file", "summary_file", "participant_session_id"]
        column_list = ", ".join(column_names)

        filter = "(data_uploaded_dt IS NOT NULL) \
        OR (skip_processing IS 1)"
        qry_res = self.execute("SELECT " + column_list + " FROM mri_sessions WHERE " + filter + ";")
        if qry_res == -1: 
            print("ERROR: Could not get MRI sessions ready for cleanup from database.")
            return -1
        
        if (qry_res==None):
            return None
        
        # convert data to dict
        res = []
        for row in qry_res:
            res.append(dict(zip(column_names, row)))

        return res

    # convert dictionary to query inputs
    def dict_to_query_input(self, d, keys_to_exclude = ()):

        # remove all excluded keys and all None values
        d = self.remove_keys_from_dict(d, keys_to_exclude)

        # cycle through all arguments
        columns = ""
        questionmarks = ""
        columns_and_questionmarks = ""
        values = []
        n_columns = 0
        for key, value in d.items():
            
            # append column, question mark and value
            columns = columns + key + ", "
            questionmarks = questionmarks + "?,"
            columns_and_questionmarks = columns_and_questionmarks + key + " = ?, "
            values.append(value)
            n_columns = n_columns+1
            
        # remove last comma from strings (if any columns were specified)
        if n_columns>0:
            columns = columns[:-2]
            questionmarks = questionmarks[:-1]
            columns_and_questionmarks = columns_and_questionmarks[:-2]
            
        return {"n_columns": n_columns, "columns": columns, "values": values, "questionmarks": questionmarks, "columns_and_questionmarks": columns_and_questionmarks}

    # remove keys from dictionary
    def remove_keys_from_dict(self, d, keys_to_exclude = ()):

        # since this is a class method, add the "self" argument from the keys to exclude
        keys_to_exclude = list(keys_to_exclude)
        if not "self" in keys_to_exclude:
            keys_to_exclude.append("self")

        # exclude keys with None values
        for key, value in d.items():
            if (key not in keys_to_exclude) and (value == None):
                keys_to_exclude.append(key)

        # remove all keys to exclude from dict
        for key in keys_to_exclude:
            if key in d:
                del d[key]

        return d
