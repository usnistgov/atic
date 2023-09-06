#-----------------------------------------------------------------------------
# Name:        logs
# Purpose:    
# Authors:     Aric Sanders 
# Created:     11/20/2020
# License:     MIT License
#-----------------------------------------------------------------------------
"""Logs is a module that holds classes and functions for creating and storing a log of events
Examples
--------
    #!python
    >>


Requirements
------------
+ 

"""
#-----------------------------------------------------------------------------
# Standard Imports
import sys
import os
import glob
import yaml
#import pymongo
import datetime
import re
import pickle
import json



#-----------------------------------------------------------------------------
# Third Party Imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

#-----------------------------------------------------------------------------
# Module Constants

#-----------------------------------------------------------------------------
# Module Functions
def get_filename_iterator(base_name=None, directory=None, extension=None, padding=3):
    """ Returns the number of files in directory with base_name +1, padded by padding"""
    iterator = 0
    replacement_string = "{:0" + str(padding) + "d}"
    if extension is None:
        extension = "*"
    if base_name is None:
        return replacement_string.format(1)
    elif directory is None:
        file_names = glob.glob('*.' + extension)
        for name in file_names:
            if re.match(base_name, name):
                iterator += 1
        return replacement_string.format(iterator + 1)

    else:
        file_names = glob.glob(directory + '/*.' + extension)
        for name in file_names:
            name = os.path.split(name)[1]
            if re.match(base_name, name):
                iterator += 1
        return replacement_string.format(iterator + 1)


def get_mongodb_iterator(base_name=None, db_name=None, padding=3, mongo_url=None):
    """ Returns the number of collections in database with base_name +1, padded by padding"""
    iterator = 0
    try:
        replacement_string = "{:0" + str(padding) + "d}"
        if mongo_url is None:
            client = pymongo.MongoClient()
        else:
            client = pymongo.MongoClient(mongo_url)

        db = client[db_name]
        collections = db.list_collection_names()
    except:
        print(f'The connection to the mongoDB failed: MongoDB URL: {mongo_url} Database name: {db_name}')
        raise

    if base_name is None:
        return replacement_string.format(1)
    else:
        for collection_name in collections:
            if re.match(base_name, collection_name):
                iterator += 1
        return replacement_string.format(iterator + 1)

def auto_name_mongodb(specific_descriptor=None, general_descriptor=None, db_name=None, padding=3, mongo_url=None):
    """ Returns an automatically generated name for a collection in a database"""
    if not specific_descriptor is None:
        name = specific_descriptor
        if not general_descriptor is None:
            name = name + '_' + general_descriptor
        name = name + '_' + get_date() + '_'
        name = name + get_mongodb_iterator(name, db_name, padding, mongo_url)
        return name
    else:
        return None


def auto_name(specific_descriptor=None, general_descriptor=None, directory=None, extension='json', padding=3):
    """ Returns an automatically generated name for a file in a directory"""
    if not specific_descriptor is None:
        name = specific_descriptor
        if not general_descriptor is None:
            name = name + '_' + general_descriptor
        name = name + '_' + get_date() + '_'
        name = name + get_filename_iterator(name, directory, extension, padding) + '.' + extension
        return name
    else:
        return None


def get_date():
    """Returns todays date in 'yyyymmdd' format"""
    today = datetime.date.today()
    return today.strftime('%Y%m%d')

def split_filename(filename):
    """Returns a list of file name pieces. The list will contain any CamelCase, snake_case or
    common delimiter seperated words (last element is nominally the file extension)"""
    out_string=re.sub("([\a-z])([\A-Z])",r'\1 \2',filename)
    out_list=re.split("[\W|\.|_]+",out_string)
    return out_list

def change_extension(file_path,new_extension=None):
    "Changes the extension of file path to the new one"
    if new_extension is None:
        return file_path
    else:
    # just to make it uniform, remove any . and add it back in
        new_extension="."+new_extension.replace(".","")
        return re.sub("\.\w+",new_extension,file_path)
def filename_decrement(filename,padding=3):
    """Takes an autogenrated file name in the form specific_descriptor_general_descriptor_date_iterator and
    decreases the iterator by 1"""
    replacement_string="{:0"+str(padding)+"d}"
    filename_pattern="(?P<base_name>[\w|_]+)_(?P<iterator>\d+).[\w]+"
    match=re.search(filename_pattern,filename,re.IGNORECASE)
    if match:
        i=match.groupdict()["iterator"]
        iterator=int(i)
        iterator-=1
        new_filename=re.sub(i,replacement_string.format(iterator),filename)
        return new_filename
    else:
        print("Filename did not conform to the base_name_iterator.extension pattern")

def filename_increment(filename,padding=3):
    """Takes an autogenrated file name in the form specific_descriptor_general_descriptor_date_iterator and
    decreases the iterator by 1"""
    replacement_string="{:0"+str(padding)+"d}"
    filename_pattern="(?P<base_name>[\w|_]+)_(?P<iterator>\d+).[\w]+"
    match=re.search(filename_pattern,filename,re.IGNORECASE)
    if match:
        i=match.groupdict()["iterator"]
        iterator=int(i)
        iterator+=1
        new_filename=re.sub(i,replacement_string.format(iterator),filename)
        return new_filename
    else:
        print("Filename did not conform to the base_name_iterator.extension pattern")
#-----------------------------------------------------------------------------
# Module Classes
class Serializer(object):
    """Abstract class defining a serializer interface"""

    def load(self,file_path):
        pass

    def save(self,file_path,data):
        pass


class PickleSerializer(Serializer):
    def __init__(self):
        self.extension = 'pickle'

    def load(self, file_path):
        with open(file_path, 'rb') as infile:
            output = pickle.load(infile)
        return output

    def save(self, file_path, data):
        with open(file_path, 'wb') as outfile:
            pickle.dump(data, outfile)


class JsonSerializer(Serializer):
    def __init__(self):
        self.extension = 'json'

    def load(self, file_path):
        with open(file_path, "r") as in_file:
            output = json.load(in_file)
        return output

    def save(self, file_path, data):
        with open(file_path, "w") as out_file:
            # convert everything to its string representation if possible
            output = []
            for dictionary in data[:]:
                converted_dictionary = {}
                for key, value in dictionary.items():
                    converted_dictionary[str(key)] = str(value)
                output.append(converted_dictionary)
            json.dump(output, out_file, indent=4)


class YamlSerializer(Serializer):
    def __init__(self):
        self.extension = 'yaml'

    def load(self, file_path):
        with open(file_path, "r") as in_file:
            output = yaml.load(in_file, Loader=yaml.FullLoader)
        return output

    def save(self, file_path, data):
        with open(file_path, "w") as out_file:
            yaml.dump(data, out_file, default_flow_style=False)


class DbSerializer(Serializer):
    """Abstract class for serializers interacting with a database"""
    def __init__(self):
        pass

    def save(self):
        pass

    def load(self):
        pass


class MongoSerializer(DbSerializer):
    def __init__(self, mongo_url=None, db_name=None, **options):
        defaults = {'default_db_name': "db_" + get_date()}

        db_options = {}
        for key, value in defaults.items():
            db_options[key] = value

        for key, value in options.items():
            db_options[key] = value
        self.db_name = db_name
        self.mongo_url = mongo_url
        try:
            if mongo_url is None:
                self.client = pymongo.MongoClient()
            else:
                self.client = pymongo.MongoClient(mongo_url)
            if db_name:
                self.db = client[db_name]
            else:
                self.db = client[db_options['default_db_name']]
            self.extension = None
        except:
            print(f'The connection to the mongoDB failed: MongoDB URL: {mongo_url} Database name: {db_name}')
            raise

    def save(self, collection_name, data):
        # break the reference by calling dict on each of the elements
        data = list(map(lambda x: dict(x), data))
        collection = self.db[collection_name]
        collection.insert_many(data)

    def load(self, collection_name):
        output = []
        collection = self.db[collection_name]
        for document in collection.find():
            document.pop("_id")
            output.append(document)
        return output

class Log(object):
    def __init__(self, file_path=None, log=None, **options):
        """Creates a log object the optional parameters

        """
        defaults = {'serializer': YamlSerializer(),
                    "db_serializer": None,
                    "directory": os.getcwd(),
                    "specific_descriptor": "New",
                    "general_descriptor": "Log",
                    "required_keys": None,
                    "lock_keys": False,
                    "formatting_string": None}

        self.log_options = {}
        for key, value in defaults.items():
            self.log_options[key] = value

        for key, value in options.items():
            self.log_options[key] = value
        if self.log_options['db_serializer']:
            self.serializer = self.log_options['db_serializer']
            self.auto_name = auto_name_mongodb(self.log_options["specific_descriptor"],
                                               self.log_options["general_descriptor"],
                                               db_name=self.serializer.db_name, mongo_url=self.serializer.mongo_url)
        else:
            self.serializer = self.log_options['serializer']
            self.auto_name = auto_name(self.log_options["specific_descriptor"], self.log_options["general_descriptor"],
                                       self.log_options["directory"], self.serializer.extension)

        if file_path:
            try:
                self.file_path = file_path

                self.log = self.serializer.load(self.file_path)
            except:
                print(f"An error occured in opening the log {file_path}")
                raise

        else:
            self.file_path = self.auto_name
            if log:
                self.log = log
            else:
                self.log = []
                self.add_entry("Log Creation")
        self.n = 0

    def add_entry(self, entry):
        """Adds a new entry to the log. By default it uses datetime.now as a timestamp"""
        new_entry = {}
        if self.log_options["required_keys"]:
            for key in self.log_options["required_keys"]:
                new_entry[key] = {}
        else:
            new_entry["timestamp"] = datetime.datetime.now()

        if isinstance(entry, dict):
            for key, value in entry.items():
                if self.log_options["lock_keys"]:
                    if not key in self.log_options["required_keys"]:
                        raise KeyError(f"The key {key} is not in {self.log_options['required_keys']}")
                    new_entry[key] = value
                else:
                    new_entry[key] = value
        else:
            new_entry["event"] = entry
        self.log.append(new_entry)
        self.save()

    def save(self, file_path=None, **options):
        if file_path:
            self.file_path = file_path
        data = list(self.log)
        self.serializer.save(self.file_path, data)
        return self.file_path

    def __str__(self):
        return yaml.dump(self.log, default_flow_style=False)

    def __iter__(self):
        self.n = 0
        return self

    def __next__(self):
        if self.n < len(self.log):
            self.current_entry = self.log[self.n]
            result = self.log[self.n]
            self.n += 1
            return result
        else:
            raise StopIteration

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        del self

    def __add__(self, other):
        assert isinstance(other.log, list)
        new_log = self.log + other.log
        new_log = sorted(new_log, key=lambda x: x["timestamp"])
        return Log(log=new_log)

    def __getitem__(self, key):
        if isinstance(key, int):
            return self.log[key]
        elif isinstance(key, datetime.datetime):
            return list(filter(lambda x: x["timestamp"] == key, self.log))
        elif isinstance(key, list):
            out_list = []
            for item in key:
                if isinstance(item, int):
                    out_list.append(self.log[item])
                elif isinstance(item, datetime.datetime):
                    out_list.extend(list(filter(lambda x: x["timestamp"] == key, self.log)))
            return out_list
        else:
            try:
                return self.log[key]
            except:
                raise KeyError()

#-----------------------------------------------------------------------------
# Module Scripts
def test_Log():
    """Script to test Log class behavior"""
    print("Creating a new log")
    new_log=Log()
    print(f"The new log is named {new_log.file_path}")
    print(f"The current contents of log are \n {str(new_log)}")
    print(f"Adding an entry to the log ...")
    new_log.add_entry("A single added event")
    print(f"The current contents of log are \n {str(new_log)}")
    print(f"Adding a dictionary as an entry")
    test_dictionary = {"space":"none","house":"green","error":None}
    new_log.add_entry(test_dictionary)
    print(f"The current contents of log are \n {str(new_log)}")
    print(new_log.log)



#-----------------------------------------------------------------------------
# Module Runner
if __name__ == '__main__':
    test_Log()
 