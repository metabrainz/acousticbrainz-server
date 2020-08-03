class ConfusionMatrix:

    def __init__(self, matrix, classes):
        self.matrix = matrix
        self.classes = classes

    def toHtml(self):
        html = '<table>'
        html += '<tr>'
        html += '<th><h3>Predicted (%)</h3></th>'
        html += '<td></td>'
        html += '</tr>'
        html += '<tr>'
        html += '<td><table>'
        html += '<tr>'

        html += '<td></td>'

        labels = self.classes()

