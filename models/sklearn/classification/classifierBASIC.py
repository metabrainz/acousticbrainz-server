from sklearn.svm import SVC


class TrainClassifier:
    def __init__(self, classifier, params):
        self.classifier = classifier
        self.params = params

    def model(self):
        validClassifiers = ['NN', 'svm']
        if self.classifier not in validClassifiers:
            raise ValueError('The classifier name must be valid.')

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
