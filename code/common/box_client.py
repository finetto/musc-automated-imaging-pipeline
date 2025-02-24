# class managing uploads to Box
import os
import sys
from datetime import datetime
import shutil
from pathlib import Path
import hashlib
import time

from box_sdk_gen import BoxClient, BoxCCGAuth, CCGConfig
from box_sdk_gen.managers.folders import CreateFolderParent
from box_sdk_gen.managers.uploads import PreflightFileUploadCheckParent, UploadFileAttributesParentField, UploadFileAttributes
from box_sdk_gen.box.errors import BoxAPIError
from box_sdk_gen.internal.utils import ByteStream

class box_client:

    # class constructor
    def __init__(self):
        
        self._connected = False
        self._client = None
       

    # class destructor
    def __del__(self):
        self._connected = False
        del self._client        

    # establish connection
    def connect(self, client_id = None, client_secret = None, user_id = None):

        # check if connection was already established
        if self._connected:
            return True
        
        # check inputs
        if client_id == None or client_id == "":
            print("WARNING: invalid Box client ID.")
            return False
        if client_secret == None or client_secret == "":
            print("WARNING: invalid Box client secret.")
            return False
        if user_id == None or user_id == "":
            print("WARNING: invalid Box user ID.")
            return False

        # attempt connection
        try:
            ccg_config = CCGConfig(
                client_id=client_id,
                client_secret=client_secret,
                user_id=user_id
            )
            auth = BoxCCGAuth(config=ccg_config)
            
            self._client = BoxClient(auth=auth)
        except Exception as e:
                print("WARNING: Could not connect to Box:")
                print(e)
                return False
        
        # success
        self._connected = True
        return True

    def check_id(self, id):

        # check ID
        if id==None or id=="":
            return -1
        
        # check if id is numeric
        if isinstance(id, str):
            if not id.isnumeric():
                print("WARNING: invalid Box item ID.")
                return -1
        elif isinstance(id, (int, float, complex)):
            id = str(int(id))

        return id


    # check if folder exists
    def folder_exists(self, folder_id=None):
        
        # check if connected
        if not self._connected:
            return -1
        
        # check folder ID
        folder_id = self.check_id(folder_id)
        if folder_id==-1:
            return -1
        
        try:
            folder_info = self._client.folders.get_folder_by_id(folder_id)
        except Exception as e:
            return False
        
        return True
        

    # get items in folder
    def get_items_in_folder(self, folder_id=None):

        # check if connected
        if not self._connected:
            return -1
        
        # check folder ID
        folder_id = self.check_id(folder_id)
        if folder_id==-1:
            return -1
    

        # get all items
        folders = []
        files = []
        try:
            folderItems = self._client.folders.get_folder_items(folder_id)

            for item in folderItems.entries:
                
                i_id = item.id
                i_type = item.type
                i_name = item.name

                if i_type == "file":

                    i_sha1 = item.sha_1
                    i_version_id = item.file_version.id
                    i_version_sha1 = item.file_version.sha_1

                    files.append({
                        "id": i_id,
                        "name": i_name,
                        "sha1": i_sha1,
                        "version": {
                            "id": i_version_id,
                            "sha1": i_version_sha1
                        }
                    })

                elif i_type == "folder":
                    folders.append({
                        "id": i_id, 
                        "name": i_name
                        })


        except Exception as e:
                print("WARNING: Could not get items from Box:")
                print(e)
                return -1
        
        return {"folders": folders, "files": files}
    
    # check if folder exists
    def get_folder_id(self, root_folder_id=None, relative_path = ()):

        # check if connected
        if not self._connected:
            return -1
        
        # check root folder ID
        root_folder_id = self.check_id(root_folder_id)
        if root_folder_id==-1:
            return -1

        # cycle throgh items in the relative path and make sure each one exists
        current_folder_id = root_folder_id
        for item in relative_path:

            # get all contents of current folder
            items_in_current_folder = self.get_items_in_folder(current_folder_id)
            if items_in_current_folder==-1:
                return -1
            
            # get folders matching current item
            matching_folders = list(filter(lambda folder_info:folder_info["name"]==item, items_in_current_folder["folders"]))
            
            if (matching_folders == None) or (len(matching_folders)<1):
                return -1
            
            # update current folder
            current_folder_id = matching_folders[0]["id"]

        return current_folder_id
    
    # check if file exists
    def get_file_id(self, root_folder_id=None, relative_path = (), file_name=""):

        # check if connected
        if not self._connected:
            return -1
        
        # check root folder ID
        root_folder_id = self.check_id(root_folder_id)
        if root_folder_id==-1:
            return -1
        
        # get ID of parent folder
        current_folder_id = self.get_folder_id(root_folder_id=root_folder_id,relative_path=relative_path)
        if current_folder_id == -1:
            return -1

        # get all contents of current folder
        items_in_current_folder = self.get_items_in_folder(current_folder_id)
        if items_in_current_folder==-1:
            return -1
        
        # get files matching current item
        matching_files = list(filter(lambda file_info:file_info["name"]==file_name, items_in_current_folder["files"]))
        
        if (matching_files == None) or (len(matching_files)<1):
            return -1

        return matching_files[0]["id"]
    
    # check if folder exists
    def create_folder(self, root_folder_id=None, relative_path = ()):

        # check if connected
        if not self._connected:
            return -1
        
        # check root folder ID
        root_folder_id = self.check_id(root_folder_id)
        if root_folder_id==-1:
            return -1

        # cycle throgh items in the relative path and make sure each one exists
        current_folder_id = root_folder_id
        for item in relative_path:

            # get all contents of current folder
            items_in_current_folder = self.get_items_in_folder(current_folder_id)
            if items_in_current_folder==-1:
                return -1
            
            # get folders matching current item
            matching_folders = list(filter(lambda folder_info:folder_info["name"]==item, items_in_current_folder["folders"]))
            
            if (matching_folders == None) or (len(matching_folders)<1):
                try:
                    res = self._client.folders.create_folder(item, CreateFolderParent(id=current_folder_id))
                    current_folder_id = res.id

                except Exception as e:
                    print("WARNING: Could not create new folder on Box:")
                    print(e)
                    return -1
                
            else:
                current_folder_id = matching_folders[0]["id"]

        return current_folder_id
    
    # upload a file
    def upload_file(self, file, folder_id):

        # check if connected
        if not self._connected:
            return -1
        
        # check root folder ID
        folder_id = self.check_id(folder_id)
        if folder_id==-1:
            return -1
        
        # get file name
        file = file.strip().replace("\\","/")
        tmp = file.split("/")
        file_name = tmp[-1]

        # make sure file exists
        if not Path(file).exists:
            return -1
        
        # get file size
        file_size_bytes = os.path.getsize(file)

        # create sha1 hash of file
        hash = ""
        #tstart = time.perf_counter()
        chunck_size = 2**20
        with open(file, 'rb') as fid:
            sha1_hash = hashlib.sha1()
            while chunk := fid.read(chunck_size):
                sha1_hash.update(chunk)
            hash = sha1_hash.hexdigest()
        #tend = time.perf_counter()
        #duration1 = tend-tstart

        # if using python 3.11 or newer, one could try this:
        #hash2 = ""
        #tstart = time.perf_counter()
        #with open(file, 'rb') as fid:
        #    sha1_hash = hashlib.file_digest(fid,"sha1")
        #    hash2 = sha1_hash.hexdigest()
        #tend = time.perf_counter()
        #duration2 = tend-tstart

        #print("the hash of " + file_name + " is " + hash + ".\n\t\tcalculation time was " + str(duration1))
        #print("the hash 2 of " + file_name + " is " + hash2 + ".\n\t\tcalculation time was " + str(duration2))
        
        # run preflight check
        file_already_exists = False
        file_id = ""
        try:
            res = self._client.uploads.preflight_file_upload_check(name = file_name,
                                                                size = file_size_bytes,
                                                                parent = PreflightFileUploadCheckParent(id=folder_id))

        except BoxAPIError as e:
            if e.response_info.body.get("code", None) == "item_name_in_use":
                file_id = e.response_info.body["context_info"]["conflicts"]["id"]
                file_already_exists = True
            else:
                print("ERROR: Unsuccessful data upload preflight test:")
                print(e)
                return -1
        except Exception as e:
            print("ERROR: Unsuccessful data upload preflight test:")
            print(e)
            return -1
        
        # upload file or new file version
        if not file_already_exists:
            try:
                res = self._client.uploads.upload_file(
                    attributes = UploadFileAttributes(
                        name=file_name, 
                        parent = UploadFileAttributesParentField(id=folder_id)
                        ),
                    file=open(file,"rb"),
                    content_md_5 = hash)
            except Exception as e:
                print("ERROR: Unsuccessful file upload:")
                print(e)
                return -1
        else:
            try:
                res = self._client.uploads.upload_file_version(
                    file_id = file_id,
                    attributes = UploadFileAttributes(
                        name = file_name, 
                        parent = UploadFileAttributesParentField(id=folder_id)
                        ),
                    file=open(file,"rb"),
                    content_md_5 = hash)
            except Exception as e:
                print("ERROR: Unsuccessful upload of new file version:")
                print(e)
                return -1
            
        return 1
        
     # upload a file - chunked
    def upload_file_chunked(self, file, folder_id):
        # NOTE: this works for first upload, but will throw an error when tryig to upload a new version
        # Gives about a 10-15 s faster upload on a 700 MB file, compared to the above upload function
        # Currently, each session has only one large file (zip file), so it may not be worth the effort to 
        # further develop this feature. May want to revisit this in the future

        # check if connected
        if not self._connected:
            return -1
        
        # check root folder ID
        folder_id = self.check_id(folder_id)
        if folder_id==-1:
            return -1
        
        # get file name
        file = file.strip().replace("\\","/")
        tmp = file.split("/")
        file_name = tmp[-1]

        # make sure file exists
        if not Path(file).exists:
            return -1
        
        # get file size
        file_size_bytes = os.path.getsize(file)
        if file_size_bytes < 20_000_000:
            print("ERROR: File is too small for chuncked upload. Minimum file size is 20 MB. Use standard upload instead.")
            return -1
        
        # upload big file
        # NOTE: for future development, we may want to go through the full process of creating an upload session,
        # uploading the file chunks and committing the upload. This would give more flexibility when trying to upload
        # a new version.
        try:
            res = self._client.chunked_uploads.upload_big_file(
                file=open(file,"rb"),
                file_name = file_name,
                file_size = file_size_bytes,
                parent_folder_id = folder_id
            )
        except Exception as e:
                print("ERROR: Unable to create file upload session:")
                print(e)
                return -1
        
        return 1

