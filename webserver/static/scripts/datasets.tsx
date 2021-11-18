import ReactDOM from "react-dom";

import React from "react";
import DatasetEditor from "./datasets/editor";
import EvaluationJobsViewer from "./datasets/eval-jobs-viewer";
import Dataset from "./datasets/class-viewer";

interface DatasetPageProps {
    dataset_mode: string;
    data: Record<string, any>;
}

const container = document.getElementById("dataset-react-container");

const propsElement = document.getElementById("page-react-props");
let reactProps: DatasetPageProps | undefined;
if (propsElement?.innerHTML) {
    reactProps = JSON.parse(propsElement!.innerHTML);
}

if (container && reactProps) {
    if (reactProps.dataset_mode === "create") {
        ReactDOM.render(
            <DatasetEditor
                mode="create"
                csrfToken={reactProps.data.csrfToken}
            />,
            container
        );
    } else if (reactProps.dataset_mode === "edit") {
        ReactDOM.render(
            <DatasetEditor
                mode="edit"
                datasetId={reactProps.data.datasetId}
                csrfToken={reactProps.data.csrfToken}
            />,
            container
        );
    } else if (reactProps.dataset_mode === "view") {
        ReactDOM.render(
            <Dataset datasetId={reactProps.data.datasetId} />,
            container
        );
    } else if (reactProps.dataset_mode === "eval-info") {
        ReactDOM.render(
            <EvaluationJobsViewer datasetId={reactProps.data.datasetId} />,
            container
        );
    }
}
