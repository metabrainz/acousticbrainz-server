/*
 This is a viewer for dataset evaluation jobs.

 Attribute "data-dataset-id" which references existing dataset by its ID need
 to be specified on container element.
 */
import React, { Component } from "react";
import ReactDOM from "react-dom";

const CONTAINER_ELEMENT_ID = "eval-viewer-container";
const container = document.getElementById(CONTAINER_ELEMENT_ID)!;

// TODO: enum
const SECTION_JOB_LIST = "dataset_details";
const SECTION_JOB_DETAILS = "class_details";

// See database code for more info about these.
const JOB_STATUS_PENDING = "pending";
const JOB_STATUS_RUNNING = "running";
const JOB_STATUS_FAILED = "failed";
const JOB_STATUS_DONE = "done";

// Classes used with SECTION_JOB_LIST:

interface JobDeleteButtonProps {
    onDelete: (a: string, b: number) => void;
}

interface JobDeleteButtonState {
    showConfirmation: boolean;
}

class JobDeleteButton extends React.Component<
    JobDeleteButtonProps,
    JobDeleteButtonState
> {
    constructor(props: Readonly<JobDeleteButtonProps>) {
        super(props);
        this.state = { showConfirmation: false };
    }

    render() {
        if (!this.state.showConfirmation) {
            return (
                <a
                    href="#"
                    className="btn btn-danger btn-xs"
                    title="Delete this evaluation job"
                    onClick={(e) => {
                        e.preventDefault();
                        this.setState({ showConfirmation: true });
                    }}
                >
                    Delete
                </a>
            );
        }
        return (
            <div>
                <em>Are you sure?&nbsp;&nbsp;</em>
                <a
                    href="#"
                    className="btn btn-danger btn-xs"
                    onClick={(e) => {
                        e.preventDefault();
                        this.props.onDelete("s", 1);
                    }}
                >
                    Delete
                </a>
                <a
                    href="#"
                    className="btn btn-default btn-xs"
                    onClick={(e) => {
                        e.preventDefault();
                        this.setState({ showConfirmation: true });
                    }}
                >
                    Cancel
                </a>
            </div>
        );
    }
}

interface JobRowProps {
    index: number;
    id: string;
    created: string;
    status: string;
    modelDownloadUrl: string | null;
    outdated: string;
    showDelete: boolean;
    onViewDetails: (index: number) => void;
    onDelete: (id: string, index: number) => void;
}

function JobRow(props: JobRowProps) {
    let status;
    switch (props.status) {
        case JOB_STATUS_PENDING:
            status = <span className="label label-info">In queue</span>;
            break;
        case JOB_STATUS_RUNNING:
            status = <span className="label label-primary">Running</span>;
            break;
        case JOB_STATUS_FAILED:
            status = <span className="label label-danger">Failed</span>;
            break;
        case JOB_STATUS_DONE:
            if (props.outdated) {
                status = (
                    <span className="label label-primary">Done, Outdated</span>
                );
            } else {
                status = <span className="label label-success">Done</span>;
            }
            break;
    }
    let download;
    if (props.status === JOB_STATUS_DONE && props.modelDownloadUrl) {
        download = <a href={props.modelDownloadUrl}>Download model</a>;
    }
    let controls;
    if (props.showDelete) {
        if (props.status === JOB_STATUS_PENDING) {
            controls = <JobDeleteButton onDelete={props.onDelete} />;
        }
    }
    return (
        <tr className="job">
            <td className="id">
                <a
                    href="#"
                    onClick={(e) => {
                        e.preventDefault();
                        props.onViewDetails(props.index);
                    }}
                >
                    {props.id}
                </a>
            </td>
            <td className="status">{status}</td>
            <td className="created">
                <span>{props.created}</span>
            </td>
            <td className="download">{download}</td>
            <td className="controls">{controls}</td>
        </tr>
    );
}

interface JobListProps {
    datasetId: string;
    jobs: any[];
    showDelete: boolean;
    onViewDetails: (index: number) => void;
    onDelete: (jobID: string, index: number) => void;
}

function JobList(props: JobListProps) {
    if (props.jobs.length > 0) {
        const items = props.jobs.map((cls: any, index: number) => {
            const modelDownloadUrl = `/datasets/${props.datasetId}/${cls.id}/download_model`;
            return (
                <JobRow
                    index={index}
                    id={cls.id}
                    created={cls.created}
                    status={cls.status}
                    modelDownloadUrl={modelDownloadUrl}
                    outdated={cls.outdated}
                    showDelete={props.showDelete}
                    onViewDetails={props.onViewDetails}
                    onDelete={props.onDelete}
                />
            );
        });
        return (
            <table className="table table-hover job-list">
                <thead>
                    <tr>
                        <th className="id">Job ID</th>
                        <th className="status">Status</th>
                        <th className="created">Creation time</th>
                        <th className="download" />
                        <th className="controls" />
                    </tr>
                </thead>
                <tbody>{items}</tbody>
            </table>
        );
    }
    return (
        <div className="alert alert-info">
            This dataset has not been evaluated yet.
        </div>
    );
}

interface ResultsProps {
    accuracy: number;
    table: any;
}

function Results(props: ResultsProps) {
    const classes = props.table.classes.map((cls: any) => {
        return <th className="active">{cls}</th>;
    });
    const header = (
        <tr>
            <th />
            {classes}
            <th />
            <th className="active">Proportion</th>
        </tr>
    );

    const rows = props.table.rows.map((cls: any, index: number) => {
        const predicted = cls.predicted.map(
            (inner_cls: any, inner_index: number) => {
                let className = "";
                if (inner_index === index) {
                    if (inner_cls.percentage > 0) {
                        className = "success";
                    }
                } else if (inner_cls.percentage >= 10) {
                    className = "danger";
                }
                return (
                    <td className={className}>
                        {inner_cls.percentage.toFixed(2)}
                    </td>
                );
            }
        );
        return (
            <tr>
                <th className="active">{props.table.classes[index]}</th>
                {predicted}
                <th className="active">{props.table.classes[index]}</th>
                <td>{cls.proportion.toFixed(2)}</td>
            </tr>
        );
    });

    const table = (
        <table className="table table-bordered table-condensed table-inner">
            <tbody>
                {header}
                {rows}
            </tbody>
        </table>
    );

    return (
        <div className="results">
            <p>
                <strong>Accuracy:</strong> {props.accuracy}%
            </p>
            <table className="table table-bordered">
                <tbody>
                    <tr>
                        <th className="active">Predicted (%)</th>
                    </tr>
                    <tr>
                        <td>{table}</td>
                        <th className="active">Actual (%)</th>
                    </tr>
                </tbody>
            </table>
        </div>
    );
}
// Classes used with SECTION_JOB_DETAILS:

interface JobDetailsProps {
    id: string;
    created: string;
    updated: string;
    status: string;
    outdated: string;
    statusMsg: string | null;
    result: any;
    onReturn: () => void;
}

function JobDetails(props: JobDetailsProps) {
    let status;
    switch (props.status) {
        case JOB_STATUS_PENDING:
            status = (
                <div className="alert alert-info">
                    This job is in evaluation queue.
                </div>
            );
            break;
        case JOB_STATUS_RUNNING:
            status = (
                <div className="alert alert-primary">
                    This evaluation job is being processed right now.
                </div>
            );
            break;
        case JOB_STATUS_FAILED: {
            let errorMsg;
            if (props.statusMsg) {
                errorMsg = (
                    <p>
                        Error details:
                        <br />
                        {props.statusMsg}
                    </p>
                );
            }
            status = (
                <div className="alert alert-danger">
                    <strong>This evaluation job has failed!</strong>
                    {errorMsg}
                </div>
            );
            break;
        }
        case JOB_STATUS_DONE:
            if (props.outdated) {
                status = (
                    <div className="alert alert-success">
                        The dataset has been changed since this job was run, so
                        the results may be out of date.
                    </div>
                );
            } else {
                status = (
                    <div className="alert alert-success">
                        This evaluation job was been completed on{" "}
                        {props.updated}. You can find results below.
                    </div>
                );
            }
            break;
    }
    const header = (
        <div>
            <h3>Job {props.id}</h3>
            <p>
                <a href="#" onClick={props.onReturn}>
                    <strong>&larr; Back to job list</strong>
                </a>
            </p>
            <p>
                <strong>Creation time:</strong> {props.created}
            </p>
            {status}
        </div>
    );
    if (props.status === JOB_STATUS_DONE) {
        return (
            <div className="job-details">
                {header}
                <Results
                    accuracy={props.result.accuracy}
                    table={props.result.table}
                />
            </div>
        );
    }
    return <div>{header}</div>;
}

interface EvaluationJobsViewerProps {
    datasetId: string;
}

interface EvaluationJobsViewerState {
    active_section: string;
    isAuthorViewing: boolean;
    // TODO: This is a list of data from
    //   /datasets/service/${container.dataset.datasetId}/evaluation/json
    jobs?: any[];
    active_job_index?: number;
}

class EvaluationJobsViewer extends Component<
    EvaluationJobsViewerProps,
    EvaluationJobsViewerState
> {
    constructor(props: Readonly<EvaluationJobsViewerProps>) {
        super(props);
        this.state = {
            active_section: SECTION_JOB_LIST,
            isAuthorViewing: false,
            jobs: undefined,
        };
    }

    componentDidMount() {
        let user: {
            created: string;
            id: number;
            musicbrainz_id: string;
        } | null = null;
        // TODO: User info should be global props
        $.get("/user-info", (data) => {
            user = data.user;
            console.debug("Received user info:", user);
        });

        $.get(
            `/datasets/service/${this.props.datasetId}/evaluation/json`,
            (data) => {
                let isAuthorViewing = false;
                if (user !== null) {
                    isAuthorViewing = user.id === data.dataset.author.id;
                }
                this.setState({
                    jobs: data.jobs,
                    isAuthorViewing,
                });
                console.debug("Received jobs:", data);
                console.debug("Is author viewing:", isAuthorViewing);
                this.handleHashChange();
            }
        );

        // Hash is used to store ID of the job that is currently viewed.
        window.addEventListener("hashchange", this.handleHashChange);
    }

    componentWillUnmount() {
        window.removeEventListener("hashchange", this.handleHashChange);
    }

    handleHashChange = () => {
        // Hash is used to store ID of the currently viewed job.
        if (this.state.jobs) {
            const hash = window.location.hash.substr(1);
            if (hash.length > 0) {
                for (let i = 0; i < this.state.jobs.length; ++i) {
                    if (this.state.jobs[i].id === hash) {
                        this.handleViewDetails(i);
                        console.debug(
                            `Found job with a specified ID (${hash}). ` +
                                `Switching view.`
                        );
                        return;
                    }
                }
                console.debug(
                    `Couldn't find any job with a specified ID (${hash}). ` +
                        `Resetting to job list.`
                );
                this.handleReturn();
            } else {
                this.handleReturn();
            }
        }
    };

    handleViewDetails = (index: number) => {
        this.setState({
            active_section: SECTION_JOB_DETAILS,
            active_job_index: index,
        });
        if (this.state.jobs) {
            window.location.hash = `#${this.state.jobs[index].id}`;
        }
    };

    handleReturn = () => {
        this.setState({
            active_section: SECTION_JOB_LIST,
            active_job_index: undefined,
        });
        window.location.hash = "";
    };

    handleJobDelete = (jobID: string, index: number) => {
        const { jobs } = this.state;
        if (!jobs) {
            return;
        }
        $.ajax({
            type: "DELETE",
            url: `/datasets/service/${this.props.datasetId}/${jobID}`,
            success(data, textStatus, jqXHR) {
                console.log(
                    `Evaluation job ${jobID} has been removed from the queue.`
                );
            },
            error(jqXHR, textStatus, errorThrown) {
                console.error(
                    "Error occurred during job deletion:",
                    jqXHR.responseJSON
                );
                alert(
                    `Failed to remove evaluation job ${jobID} from the queue. Reason: ${jqXHR.responseJSON.error}`
                );
            },
        });

        // Removing job from the list
        jobs.splice(index, 1);
        this.setState({ jobs });
    };

    render() {
        if (this.state.jobs) {
            if (this.state.active_section === SECTION_JOB_LIST) {
                return (
                    <JobList
                        datasetId={this.props.datasetId}
                        jobs={this.state.jobs}
                        showDelete={this.state.isAuthorViewing}
                        onViewDetails={this.handleViewDetails}
                        onDelete={this.handleJobDelete}
                    />
                );
            } // SECTION_JOB_DETAILS
            if (this.state.active_job_index) {
                const active_job = this.state.jobs[this.state.active_job_index];
                return (
                    <JobDetails
                        id={active_job.id}
                        created={active_job.created}
                        updated={active_job.updated}
                        status={active_job.status}
                        statusMsg={active_job.status_msg}
                        result={active_job.result}
                        outdated={active_job.outdated}
                        onReturn={this.handleReturn}
                    />
                );
            }
        }
        return <strong>Loading job list...</strong>;
    }
}

export default EvaluationJobsViewer;
