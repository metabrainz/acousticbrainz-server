import os
from datetime import datetime
from termcolor import colored


def export_report(config, name, report, filename, train_class, exports_path):
    reports_path = os.path.join(exports_path, "reports")
    # take current datetime
    now = datetime.now()
    datetime_str_verbose = now.isoformat()
    print("Creating report file..")
    with open(os.path.join(reports_path, "{}.txt".format(filename)), 'w+') as fp:
        fp.write("Date of execution: {}".format(datetime_str_verbose))
        fp.write("\n\n")
        fp.write(str(name))
        fp.write("\n\n")
        fp.write(str(report))
        fp.close()
    print(colored("{} file for class {} is created successfully.".format(name, train_class), "cyan"))
