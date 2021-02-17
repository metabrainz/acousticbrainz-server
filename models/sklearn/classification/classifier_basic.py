from sklearn.svm import SVC


class TrainClassifier:
    """
    This class initiates a simple classifier. It is used for initiating a simple model from
    sklearn or other APIs in the future, like TensorFlow.
    TODO: Initiating other models from sklearn (e.g. Random Forests, Decision Tree, etc.)
    """
    def __init__(self, classifier, params):
        """
        Args:
            classifier: the classifier name (str) to be set. A string that is among the valid
                classifiers list.
            params: The parameters of the classifier (dictionary).

        Returns:
            The model object that is initiated (including its set of parameters)
        """
        self.classifier = classifier
        self.params = params

    def model(self):
        validClassifiers = ["NN", "svm", "rf"]
        if self.classifier not in validClassifiers:
            raise ValueError("The classifier name must be valid.")

        if self.classifier == "svm":
            param_C = self.params["C"]
            param_gamma = self.params["gamma"]
            param_class_weight = self.params["class_weight"]
            param_kernel = self.params["kernel"]
            model = SVC(C=param_C,  # 2 ** param_C
                        gamma=param_gamma,  # 2 ** param_gamma
                        kernel=param_kernel,
                        class_weight=param_class_weight,
                        probability=True)
            return model
        else:
            return None
