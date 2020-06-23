const PropTypes = require("prop-types");
/*
 This is a viewer for dataset evaluation jobs.

 Attribute "data-dataset-id" which references existing dataset by its ID need
 to be specified on container element.
 */
const React = require("react");
const ReactDOM = require("react-dom");

const CONTAINER_ELEMENT_ID = "eval-viewer-container";
const container = document.getElementById(CONTAINER_ELEMENT_ID);

const SECTION_JOB_LIST = "dataset_details";
const SECTION_JOB_DETAILS = "class_details";

// See database code for more info about these.
const JOB_STATUS_PENDING = "pending";
const JOB_STATUS_RUNNING = "running";
const JOB_STATUS_FAILED = "failed";
const JOB_STATUS_DONE = "done";

class EvaluationJobsViewer extends React.Component {
    state = {
        active_section: SECTION_JOB_LIST,
        isAuthorViewing: false,
        jobs: null,
    };

    componentDidMount() {
        let user = null;
        $.get("/user-info", function (data) {
            user = data.user;
            console.debug("Received user info:", user);
        });

        // Do not confuse property called "dataset" with our own datasets. See
        // https://developer.mozilla.org/en-US/docs/Web/API/HTMLElement/dataset
        // for more info about it.
        if (!container.dataset.datasetId) {
            console.error(
                "ID of existing dataset needs to be specified" +
                    "in data-dataset-id property."
            );
            return;
        }
        $.get(
            `/datasets/service/${container.dataset.datasetId}/evaluation/json`,
            function (data) {
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
            }.bind(this)
        );

        // Hash is used to store ID of the job that is currently viewed.
        window.addEventListener("hashchange", this.handleHashChange);
    }

    componentWillUnmount() {
        window.removeEventListener("hashchange", this.handleHashChange);
    }

    handleHashChange = (e) => {
        // Hash is used to store ID of the currently viewed job.
        if (this.state.jobs) {
            const hash = window.location.hash.substr(1);
            let active_section = SECTION_JOB_LIST;
            if (hash.length > 0) {
                active_section = SECTION_JOB_DETAILS;
                for (let i = 0; i < this.state.jobs.length; ++i) {
                    if (this.state.jobs[i].id == hash) {
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

    handleViewDetails = (index) => {
        this.setState({
            active_section: SECTION_JOB_DETAILS,
            active_job_index: index,
        });
        window.location.hash = `#${this.state.jobs[index].id}`;
    };

    handleReturn = () => {
        this.setState({
            active_section: SECTION_JOB_LIST,
            active_job_index: undefined,
        });
        window.location.hash = "";
    };

    handleJobDelete = (jobID, index) => {
        $.ajax({
            type: "DELETE",
            url: `/datasets/service/${container.dataset.datasetId}/${jobID}`,
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
        const { jobs } = this.state;
        jobs.splice(index, 1);
        this.setState({ jobs });
    };

    render() {
        if (this.state.jobs) {
            if (this.state.active_section == SECTION_JOB_LIST) {
                return (
                    <JobList
                        jobs={this.state.jobs}
                        showDelete={this.state.isAuthorViewing}
                        onViewDetails={this.handleViewDetails}
                        onDelete={this.handleJobDelete}
                    />
                );
            } // SECTION_JOB_DETAILS
            const active_job = this.state.jobs[this.state.active_job_index];
            return (
                <JobDetails
                    id={active_job.id}
                    created={active_job.created}
                    updated={active_job.updated}
                    status={active_job.status}
                    statusMsg={active_job.status_msg}
                    result={active_job.result}
                    showDelete={this.state.isAuthorViewing}
                    outdated={active_job.outdated}
                    onReturn={this.handleReturn}
                />
            );
        }
        return <strong>Loading job list...</strong>;
    }
}

// Classes used with SECTION_JOB_LIST:

class JobList extends React.Component {
    static propTypes = {
        jobs: PropTypes.array.isRequired,
        showDelete: PropTypes.bool.isRequired,
        onViewDetails: PropTypes.func.isRequired,
        onDelete: PropTypes.func.isRequired,
    };

    render() {
        if (this.props.jobs.length > 0) {
            const items = [];
            this.props.jobs.forEach(
                function (cls, index) {
                    items.push(
                        <JobRow
                            index={index}
                            id={cls.id}
                            created={cls.created}
                            status={cls.status}
                            outdated={cls.outdated}
                            showDelete={this.props.showDelete}
                            onViewDetails={this.props.onViewDetails}
                            onDelete={this.props.onDelete}
                        />
                    );
                }.bind(this)
            );
            return (
                <table className="table table-hover job-list">
                    <thead>
                        <tr>
                            <th className="id">Job ID</th>
                            <th className="status">Status</th>
                            <th className="created">Creation time</th>
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
}

class JobRow extends React.Component {
    static propTypes = {
        index: PropTypes.number.isRequired,
        id: PropTypes.string.isRequired,
        created: PropTypes.string.isRequired,
        status: PropTypes.string.isRequired,
        outdated: PropTypes.string.isRequired,
        showDelete: PropTypes.bool.isRequired,
        onViewDetails: PropTypes.func.isRequired,
        onDelete: PropTypes.func.isRequired,
    };

    handleViewDetails = (event) => {
        event.preventDefault();
        this.props.onViewDetails(this.props.index);
    };

    handleDelete = () => {
        this.props.onDelete(this.props.id, this.props.index);
    };

    render() {
        let status = "";
        switch (this.props.status) {
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
                if (this.props.outdated) {
                    status = (
                        <span className="label label-primary">
                            Done, Outdated
                        </span>
                    );
                } else {
                    status = <span className="label label-success">Done</span>;
                }
                break;
        }
        let controls = "";
        if (this.props.showDelete) {
            if (this.props.status === JOB_STATUS_PENDING) {
                controls = <JobDeleteButton onDelete={this.handleDelete} />;
            }
        }
        return (
            <tr className="job">
                <td className="id">
                    <a href="#" onClick={this.handleViewDetails}>
                        {this.props.id}
                    </a>
                </td>
                <td className="status">{status}</td>
                <td className="created">
                    <span>{this.props.created}</span>
                </td>
                <td className="controls">{controls}</td>
            </tr>
        );
    }
}

class JobDeleteButton extends React.Component {
    static propTypes = {
        onDelete: PropTypes.func.isRequired,
    };

    state = { showConfirmation: false };

    delete = (event) => {
        event.preventDefault();
        this.props.onDelete();
    };

    confirm = (event) => {
        event.preventDefault();
        this.setState({ showConfirmation: true });
    };

    cancel = (event) => {
        event.preventDefault();
        this.setState({ showConfirmation: false });
    };

    render() {
        if (!this.state.showConfirmation) {
            return (
                <a
                    href="#"
                    className="btn btn-danger btn-xs"
                    title="Delete this evaluation job"
                    onClick={this.confirm}
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
                    onClick={this.delete}
                >
                    Delete
                </a>
                <a
                    href="#"
                    className="btn btn-default btn-xs"
                    onClick={this.cancel}
                >
                    Cancel
                </a>
            </div>
        );
    }
}

// Classes used with SECTION_JOB_DETAILS:

class JobDetails extends React.Component {
    static propTypes = {
        id: PropTypes.string.isRequired,
        created: PropTypes.string.isRequired,
        updated: PropTypes.string.isRequired,
        status: PropTypes.string.isRequired,
        outdated: PropTypes.string.isRequired,
        statusMsg: PropTypes.string,
        result: PropTypes.object,
        onReturn: PropTypes.func.isRequired,
    };

    render() {
        let status = "";
        switch (this.props.status) {
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
            case JOB_STATUS_FAILED:
                var errorMsg = "";
                if (this.props.statusMsg) {
                    errorMsg = (
                        <p>
                            Error details:
                            <br />
                            {this.props.statusMsg}
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
            case JOB_STATUS_DONE:
                if (this.props.outdated) {
                    status = (
                        <div className="alert alert-success">
                            The dataset has been changed since this job was run,
                            so the results may be out of date.
                        </div>
                    );
                } else {
                    status = (
                        <div className="alert alert-success">
                            This evaluation job has been completed on{" "}
                            {this.props.updated}. You can find results below.
                        </div>
                    );
                }
                break;
        }
        const header = (
            <div>
                <h3>Job {this.props.id}</h3>
                <p>
                    <a href="#" onClick={this.props.onReturn}>
                        <strong>&larr; Back to job list</strong>
                    </a>
                </p>
                <p>
                    <strong>Creation time:</strong> {this.props.created}
                </p>
                {status}
            </div>
        );
        if (this.props.status === JOB_STATUS_DONE) {
            return (
                <div className="job-details">
                    {header}
                    <Results
                        accuracy={this.props.result.accuracy}
                        table={this.props.result.table}
                    />
                </div>
            );
        }
        return <div>{header}</div>;
    }
}

class Results extends React.Component {
    static propTypes = {
        accuracy: PropTypes.number.isRequired,
        table: PropTypes.string.isRequired,
    };

    render() {
        const classes = [];
        this.props.table.classes.forEach(function (cls) {
            classes.push(<th className="active">{cls}</th>);
        });
        const header = (
            <tr>
                <th />
                {classes}
                <th />
                <th className="active">Proportion</th>
            </tr>
        );

        const rows = [];
        const so = this;
        this.props.table.rows.forEach(function (cls, index) {
            const predicted = [];
            cls.predicted.forEach(function (inner_cls, inner_index) {
                let className = "";
                if (inner_index == index) {
                    if (inner_cls.percentage > 0) {
                        className = "success";
                    }
                } else if (inner_cls.percentage >= 10) {
                    className = "danger";
                }
                predicted.push(
                    <td className={className}>
                        {inner_cls.percentage.toFixed(2)}
                    </td>
                );
            });
            rows.push(
                <tr>
                    <th className="active">{so.props.table.classes[index]}</th>
                    {predicted}
                    <th className="active">{so.props.table.classes[index]}</th>
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
                    <strong>Accuracy:</strong> {this.props.accuracy}%
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
}

if (container) ReactDOM.render(<EvaluationJobsViewer />, container);
