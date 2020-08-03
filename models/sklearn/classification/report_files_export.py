import os
from datetime import datetime
from termcolor import colored
from utils import load_yaml, FindCreateDirectory, TrainingProcesses


def export_report(config, name, report, filename, train_class, exports_path):
    exports_dir = "{}_{}".format(config.get("exports_directory"), train_class)
    reports_path = FindCreateDirectory(exports_path, os.path.join(exports_dir, "reports")).inspect_directory()
    # take current date and convert to string
    now = datetime.now()
    datetime_str = now.strftime("%Y-%m-%d")
    datetime_str_verbose = now.strftime("%Y-%m-%d, %H:%M:%S")
    print("Creating report file..")
    with open(os.path.join(reports_path, "{}.txt".format(filename)), 'w+') as file:
        file.write("{}".format(name))
        file.write('\n')
        file.write('\n')
        file.write(str(report))
        file.write('\n')
        file.write('\n')
        file.write('\n')
        file.write("Date of execution: {}".format(datetime_str_verbose))
        file.close()
    print(colored('{} file for class {} is created successfully.'.format(name, train_class), "cyan"))

