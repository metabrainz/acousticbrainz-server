from utils import load_yaml, FindCreateDirectory
from sklearn.model_selection import cross_val_score
from sklearn.model_selection import cross_validate
from sklearn.model_selection import cross_val_predict
from transformation.transform import Transform
from sklearn.model_selection import KFold
from sklearn.svm import SVC


def display_scores(scores):
    """

    :param scores:
    :return:
    """
    print("Display scores:")
    print("Scores: {}".format(scores))
    print("Mean: {}".format(scores.mean()))
    print("Standard Deviation: {}".format(scores.std()))


def evaluate_gaia_imitation_model(config, class_name, X, y):
    """

    :param config:
    :param class_name:
    :param X:
    :param y:
    :return:
    """
    gaia_params = load_yaml("gaia_best_models/jmp_results_{}.param".format(class_name))
    print("Gaia best model params: {}".format(gaia_params))

    # params data transformation
    preprocessing = gaia_params["model"]["preprocessing"]

    # params SVC
    C = 2 ** gaia_params["model"]["C"]
    gamma = 2 ** gaia_params["model"]["gamma"]
    kernel = gaia_params["model"]["kernel"].lower()
    balance_classes = gaia_params["model"]["balanceClasses"]
    # TODO: declare a dictionary for class weights via automated labels balancing (unresponsive dataset)
    if balance_classes is True:
        class_weights = "balanced"
    elif balance_classes is False:
        class_weights = None
    else:
        print("Define a correct class weight value")
        class_weights = None
    n_fold = gaia_params["evaluation"]["nfold"]

    # Transform dataset
    # pre-processing: data cleaning/enumerating/selecting descriptors
    # pre-processing: scaling
    print("Exports path for the training:")
    exports_dir = "{}_{}".format(config.get("exports_directory"), class_name)
    exports_path = FindCreateDirectory(exports_dir).inspect_directory()
    print(exports_path)
    # transformation of the data
    X_transformed = Transform(config=config,
                              df=X,
                              process=preprocessing,
                              exports_path=exports_path,
                              mode="train").post_processing()

    print(X_transformed.columns)
    print(X_transformed.head())

    X_array_transformed = X_transformed.values

    inner_cv = KFold(n_splits=n_fold,
                     shuffle=config["gaia_kfold_shuffle"],
                     random_state=config["gaia_kfold_random_state"]
                     )

    svm = SVC(
        C=C,
        kernel=kernel,
        gamma=gamma,
        class_weight=class_weights,
        probability=config.get("svc_probability")
    )

    print("Evaluate the classifier with cross_val_score:")
    scores = cross_val_score(estimator=svm,
                             X=X_array_transformed,
                             y=y,
                             scoring="accuracy",
                             cv=inner_cv,
                             n_jobs=config.get("parallel_jobs"),
                             verbose=config.get("verbose")
                             )

    print()
    print("Score results:")
    display_scores(scores)
    print()
    print()


if __name__ == '__main__':

    evaluate_gaia_imitation_model()
