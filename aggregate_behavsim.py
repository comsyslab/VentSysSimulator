import os, os.path
import csv
import sys
import collections

class Data_formatting(object):
    def __init__(self, path, destination_path):
        self.path = path
        self.destination_path = destination_path

    def data_format(self):

        # getting names of all folders and files  in the specified path
        print "Starting Generation"
        dir_name = [self.path for self.path in os.listdir('.') if os.path.isdir(self.path)]
        directory = dir_name[1]
        appliances_folder = [x for x in os.walk(directory)]
        app_folder_format = appliances_folder[0][1]
        folder = app_folder_format[0]
        data_files = [x for x in os.walk('%s/%s' % (directory, folder))]
        print data_files
        data_files_format = data_files[0][2]
        data_files_format.remove('desktop.ini') # file that appears when using GoogleDrive
        print data_files_format

        # initialising dictionary for data handling
        file_names = dict()
        dict_ini = dict()
        for data_file in data_files_format:
            with open("%s/%s/%s" % (directory, folder, data_file), 'rb') as csvfile:
                reader = csv.reader(csvfile, delimiter=';', quotechar='|')
                t_duration = 0
                for row in reader:
                    try:
                        t_duration += 60
                        dict_ini[t_duration] = 0
                    except:
                        print "Unexpected error 1:", sys.exc_info()[0]

            for folder in app_folder_format:
                with open("%s/%s/%s" % (directory, folder, data_file), 'rb') as csvfile:
                    reader = csv.reader(csvfile, delimiter=';', quotechar='|')
                    t_duration = 0
                    counter = 1
                    house_number = os.path.splitext(data_file)[0]
                    for row in reader:
                        try:
                            t_duration += 60
                            dict_ini[t_duration] = dict_ini[t_duration] + float(row[0])
                        except:
                            print "Unexpected error 2:", sys.exc_info()[0]

            dict_ini_sorted = collections.OrderedDict(sorted(dict_ini.items()))
            file_names[house_number] = dict_ini_sorted
            list_val = file_names.values()[0]

            with open(self.destination_path+"\%s.csv" % house_number, 'a+') as f:
                    num_lines = sum(1 for line in f)

            with open(self.destination_path+"\%s.csv" % house_number, 'wb') as csvfile:
                    fieldnames = ['Time duration [s]', 'Power [W]']
                    log_fs = csv.DictWriter(csvfile, delimiter=';', lineterminator='\n',fieldnames=fieldnames)
                    if num_lines == 0:
                        log_fs.writeheader()
                    for key in list_val.keys():
                        log_fs.writerow({'Time duration [s]': key, 'Power [W]': dict_ini[key]})
        print "Aggregated house data is generated"

if __name__ == "__main__":
    f_path = os.path.dirname(os.path.abspath('__file__'))
    path_files = os.path.join(f_path, 'household-loads') 
    print 'Extract data from: %s' % path_files
    path_destination = os.path.join(f_path, 'results')
    print 'Send data to: %s' % path_destination
    x = Data_formatting(path=path_files, destination_path=path_destination)
    x.data_format()
