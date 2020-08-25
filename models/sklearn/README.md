# Machine Learning Infrastructure with scikit-learn (GSoC 2020)

This folder contains the tool that is built for training SVM models of 
AcousticBrainz's datasets, as well as predicting where a single AcousticBrainz 
track instance can be classified based on the trained models. It is part of the 
*Google Summer of Code 2020* in collaboration with the **MetaBrainz** Open-Source 
organization.

Given a dataset, a Grid Search algorithm using n-fold cross-validation is executed 
for an exhaustive search over specified parameter values for an estimator.

A final model is trained with all the data (without a validation set) featuring 
the best parameter combination in terms of accuracy.

Finally, a prediction functionality is part of the tool, which gives the user the 
capability of predicting where a track instance is classified based on a trained model.


## Functionalities

### Train
The main model training function is the `create_classification_project` which is located in
the `model.classification_project.py` Python script. It can be imported as a module. 
It requires a path to the dataset directory that contains sub-folders 
composed of the groundtruth yaml file/s (tracks, tracks paths, labels, target class), and
the features (low-level data) in JSON format.

```
create_classification_project()

Generates a model trained using descriptor files specified in the groundtruth yaml file.

positional parameters:
groundtruth             Path of the main dataset directory containing the 
                        groundtruth yaml file/s. (required)

file                    Name of the project configuration file (.yaml) will be stored. 
                        If not specified it takes automatically the name <project_CLASS_NAME>."

exportsdir              Name of the exports directory that the project's results 
                        will be stored (best model, grid models, transformation 
                        pipelines, folded and shuffled dataset).

path                    Path where the project results will be stored. If empty,
                        the results will be saved in the main app directory.

optional parameters:

c_values                The C values parameter (list) for the SVM Grid Search 
                        (e.g. [-2, 3, 5, 10]). In case of None, the values will be set up
                        by the specified in the configuration template.

gamma_values            The gamma values parameter (list) for the SVM Grid Search 
                        (e.g. [ 3, 1, -1, -3]). In case of None, the values will be set up
                        by the specified in the configuration template.

preprocessing_values:   The preprocessing values parameter (list) for the 
                        SVM Grid Search. They must be one or more of the following list: 
                        ["basic", "lowlevel", "nobands", "normalized", "gaussianized"]
                        In case of None, the values will be set up
                        by the specified in the configuration template.

logging                 The logging level (int) that will be printed (0: DEBUG, 1: INFO, 
                        2: WARNING, 3: ERROR, 4: CRITICAL). Can be set only in the
                        prescribed integer values (0, 1, 2, 3, 4)

seed                    Seed (int) is used to generate the random shuffled dataset 
                        applied later to folding. If no seed is specified, the seed
                        will be automatically set to current clock value.

jobs                    Parallel jobs (int). Set a value of cores to be used.
                        The default is -1, which means that all the available cores
                        will be used.
  
verbose                 Controls the verbosity (int) of the Grid Search print messages
                        on the console: the higher, the more messages.
```

For example, a dataset path directory structure could be like this one:

    dataset (e.g. danceability)
    |- features
    |  |-happy
    |  |  |- 1.json
    |  |  |- 2.json
    |  |  |- 3.json
    |  |  |- 4.json
    |  |-sad
    |  |  |- 1.json
    |  |  |- 2.json
    |  |  |- 3.json
    |- metadata
    |  |- groundtruth.yaml
    
The tool will train a model with 2 classes (happy, sad), with 4 and 3 files in each class, respectively.

The tool generates a `.yaml` project file to the path and exports directory specified or by the 
arguments or automatically by the tool itself. This project file contains information about the 
preprocessing steps that are followed through the training process, as well as the path and directory
where the results after the model training will be stored to.


### How the Training mode works

There are several steps which are followed in the training phase. First of all, the project 
configuration template file is loaded. Then, based on the arguments that are specified via the 
`create_classification_project` function invoke, the`ListGroundTruthFiles` class searches for 
the available `.yaml` file/s which contain the target class and the *groundtruth* data. These files 
are inside the specified dataset directory.

Afterwards, for each target class, the following actions take place inside the 
`train_class` function:

1. It starts with the `GroundTruthLoad` class that loads the *groundtruth* data from the related `.yaml` file. By
   using its included methods, the tracks with their labels shuffled, in tuples, are exported as well as the 
   target class exploiting the `export_gt_tracks()` and the `export_train_class()` accordingly. The shuffled 
   dataset is also exported and saved locally in `.csv` format. A logger object is also set up and the logging
   results are exported into the relevant `.log` file.

2. It creates a project configuration file based on the specified paths for the exported results, as well as
   a relevant directory that these results will be stored to. The training model results comprise:

3. The `DatasetExporter` class is used then to load the tracks' features and exports them in a `pandas DataFrame`. 
   The tracks and the labels are also exported in separate `NumPy arrays` too.

4. The `ClassificationTaskManager` class is invoked which is used for extracting the different classification tasks
   that are specified in the configuration file. This is done be calling the `TrainingProcesses` class, which reads 
   the configuration file, and extracts the available training processes in a list. Each item of the list is 
   composed of a Python dictionary that comprises the evaluation that will take place with its: a) the classifier used, 
   b) the preprocess steps (features selection, scaling type, etc.), the k-fold cross-validation (number of folds), 
   and finally, c) the combination parameters that a Grid Search algorithm will use to find the best model that will 
   be assigned to the classifier.
   
5. For each evaluation, the `ClassificationTask` class is used. The class loads the list of process dictionaries, with 
   their corresponding training steps as described above that contain also the features with their labels, as well as 
   the specified in the configuration file classifier that will be used for training the model.
   
6. The whole specified classification task (i.e. the preprocessing, the training of the model for the selected 
   features, and the evaluation) takes place inside the `ClassificationTask` class. The `TrainGridClassifier` is
   responsible for the classifier training by using a Grid Search algorithm which, in our case loads a 
   `Support Vector Machines` Machine Learning model from sklearn with a grid of parameters. 
   
7. For each preprocessing step, the `Transform` class is responsible for doing the appropriate preprocess, like the
   data cleaning, the features selection, the enumeration, and the scaling, when it is available. For each 
   preprocessing step, the corresponding transformation pipeline (in `.pkl` format) is extracted and saved locally 
   for later use in the predictions mode. 
   
8. The transformed features data is loaded then to the `train_grid` function where the training of the model takes place. 
   The results of the training phase are extracted by using the `save_grid_results` function. Such results are the best 
   parameters that did best in each training phase (i.e. in each training step), as well as the best model from this 
   training step which is saved locally in `.pkl` format. Finally, the best extracted
   models from each training process are compared and the best one is chosen. The information about the best model 
   parameters, with the preprocess step that was followed are exported and saved in a `.json` file locally, and 
   include:
   * Best model's score, the parameters, the preprocess (data cleaning, features selection, enumeration, scaling), 
   and the number of folds that the dataset was split into through the cross-validation training procedure.
   
9. The `evaluation` function is used to evaluate the best model and the relevant reports are
   exported. The best model and the corresponding preprocessing step pipeline are loaded, and a k-fold 
   cross-validation training takes place. The results from this process are:
   * A `yaml` file that contains the tracks' instances and the fold that were classified is exported in this phase.
   * A `.csv` file that includes the tracks, the prediction that took place in the relevant fold, the true label, 
   and the probability of the classifier's decision function  that took for each class prediction. 
   * The plot that depicts the accuracy score delivered from each fold training.
   * A `.txt` file that contains detailed information about each fold's training score, the *mean* of all the 
   accuracies exported from each fold, as well as the *standard deviation* of these accuracies.
   * The `.txt` files that contain the confusion matrix and the classification report of the cross-validation
   training.

10. Finally, the `evaluation` function executes a training to the whole dataset by using the best model that is 
    extracted from the grid search algorithm. After applying predictions to the whole dataset, the related `.txt` 
    files with the confusion matrix and the classification report are exported and saved locally to the disk. The 
    trained model, after this training phase is saved locally in `.pkl` format for later use from the 
    predictions mode of the tool.
   


### Predict

The `model.predict.py` script contains the `prediction` function. This function can be invoked via by 
importing the function in a separate script and invoking it with its corresponding parameters. The 
project `.yaml` file with project's configuration metadata is a required field in the function's
parameters, as well as the **MBID** of the track to be called for predicting to which trained model's
class will be classified. The MBID is actually the Musicbrainz ID which is the unique track's ID
stored in the MusicBrainz and AcousticBrainz database. For example, the following link:
* https://acousticbrainz.org/232b8e6e-0aa5-4310-8df3-583047af3126
has the MBID: `232b8e6e-0aa5-4310-8df3-583047af3126`

This is the only necessary information for the related argument of the `prediction` function to
make the relevant classification.

```
$ python predict.py --help
usage: predict.py [-h] [--path] [--file] [--track] [--logging]

positional arguments:
path                    Path where the project file (.yaml) is stored (required).

file                    Name of the project configuration file (.yaml) that 
                        is to be loaded. (required)
                        The .yaml at the end of the file is not necessary. 
                        Just put the name of the file.

track                   MBID of the the low-level data from the AcousticBrainz API.
                        (required)

optional arguments:

logging                 The logging level (int) that will be printed (0: DEBUG, 1: INFO, 
                        2: WARNING, 3: ERROR, 4: CRITICAL). Can be set only in the
                        prescribed integer values (0, 1, 2, 3, 4)
```

### How the Predictions mode works

The function and the class that are used in this phase are the `prediction` and the `Predict` accordingly. The steps 
that are followed in this mode are:

1. The `prediction` function loads the project configuration file that was created by the training of the 
   corresponding model. This `.yaml` file includes all the relevant information about the paths that the 
   trained model and the preprocessing pipelines were saved to (in `.pkl` format).

2. Then, by using the MBID that was inserted as an argument, it downloads the low-level data from AcousticBrainz API, 
   using the `requests` library.

3. The data, which are in JSON format are then loaded to the `Predict` class, with the built model's configuration 
   data (training results' location, etc.).
   
3. The `Predict` loads the best model's JSON file that was saved from the training mode, and checks the preprocessing 
   step that resulted in the best model.
   
4. After checking which was the preprocessing step that was specified inside the best model's metadata, the
   `TransformPredictions` class is invoked and does the necessary data transformation by loading the corresponding 
   preprocessing pipeline that was saved in `.pkl` format during the training mode.
   
5. After that, it loads the best trained model that was saved in `.pkl` format.

6. It does the prediction.

7. It returns a dictionary that includes:
   * the predicted class
   * the score of the predicted class
   * the probabilities for each class the model took to decide to which one the track will be classified.
