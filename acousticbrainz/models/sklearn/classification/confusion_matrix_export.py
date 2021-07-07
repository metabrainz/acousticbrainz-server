# encoding: utf-8
from collections import defaultdict
import json

def load_as_confusion_matrix(filename):
    with open(filename) as f:
        data = json.load(f)

    # convert to a defaultdict the data we just loaded
    matrix = defaultdict(lambda: defaultdict(list))
    for k, v in data['matrix'].items():
        matrix[k] = defaultdict(list, v)

    return matrix
