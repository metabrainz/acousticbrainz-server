import numpy as np
import json
import csv
import collections
from scipy import stats
from scipy.stats import spearmanr

def extract_features(decoded_data):

        arr = []
        #length
        arr.append(decoded_data["metadata"]["audio_properties"]["length"])
        #bpm
        arr.append(decoded_data["rhythm"]["bpm"])
        #average_loudness
        arr.append(decoded_data["lowlevel"]["average_loudness"])
        #onset_rate
        arr.append(decoded_data["rhythm"]["onset_rate"])
        #replay_gain
        arr.append(decoded_data["metadata"]["audio_properties"]["replay_gain"])
        #tuning_frequency
        arr.append(decoded_data["tonal"]["tuning_frequency"])

        return arr


def calc_z_scores(data):
        """used to calculate column vise z-scores for the list of data
        """
        data = np.array(data)
        z = np.zeros(data.shape)
        for i in range(0, data.shape[1]):
            arr = data[:, i].astype(np.float)
            arr = np.abs(stats.zscore(arr))
            z[:, i] = arr

        return z


def identify_anomalies(data):
        """returns a list of outlier ides and the offest of the best one 
        threshold is taken to be 1.65 for a 90 % confidence value
        """
        arr = []
        l = len(data)
        z = calc_z_scores(data)
        for i in range(0, z.shape[1]):
            arr = np.concatenate((np.array(arr), np.where(z[:, i] > 1.65)[0]))

        # root mean squate of z values for each offset to detect least varying id
        z_rms = np.sqrt(np.mean(z**2, axis=1))
        best_id = np.argmin(z_rms) + 1

        unique, counts = np.unique(arr, return_counts=True)
        # dict containing {ids,count}
        ids_dict = dict(zip(unique, counts))
        #check for ids which have more than or equalto 3 outlying features
        outliers = [k for k, v in ids_dict.items() if v >= 3]

        correct_offsets = list(x for x in range(1, l+1) if x not in outliers)
        return outliers, correct_offsets, best_id
        
