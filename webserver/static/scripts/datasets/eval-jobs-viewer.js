/*
 This is a viewer for dataset evaluation jobs.

 Attribute "data-dataset-id" which references existing dataset by its ID need
 to be specified on container element.
 */
var React = require('react');
var ReactDOM = require('react-dom');

var CONTAINER_ELEMENT_ID = "eval-viewer-container";
var container = document.getElementById(CONTAINER_ELEMENT_ID);

var SECTION_JOB_LIST = "dataset_details";
var SECTION_JOB_DETAILS = "class_details";

// See database code for more info about these.
var JOB_STATUS_PENDING = "pending";
var JOB_STATUS_RUNNING = "running";
var JOB_STATUS_FAILED = "failed";
var JOB_STATUS_DONE = "done";


var EvaluationJobsViewer = React.createClass({
    getInitialState: function () {
        return {
            active_section: SECTION_JOB_LIST,
            isAuthorViewing: false,
            jobs: null
        };
    },
    componentDidMount: function() {
        let user = null;
        $.get("/user-info", function(data) {
            user = data.user;
            console.debug("Received user info:", user);
        });

        // Do not confuse property called "dataset" with our own datasets. See
        // https://developer.mozilla.org/en-US/docs/Web/API/HTMLElement/dataset
        // for more info about it.
        if (!container.dataset.datasetId) {
            console.error("ID of existing dataset needs to be specified" +
                "in data-dataset-id property.");
            return;
        } else if (container.dataset.jobId) {
            this.state.active_section = SECTION_JOB_DETAILS;
        }

        $.get("/datasets/" + container.dataset.datasetId + "/evaluation/json", function(data) {
            if (this.isMounted()) {
                let isAuthorViewing = false;
                if (user !== null) {
                    isAuthorViewing = user.id === data.dataset.author.id;
                }
                this.setState({
                    jobs: data.jobs,
                    isAuthorViewing: isAuthorViewing
                });
                console.debug("Received jobs:", data);
                console.debug("Is author viewing:", isAuthorViewing);
            }
        }.bind(this));

        window.onpopstate = (event) => {
            if (this.state.active_section == SECTION_JOB_LIST) {
                this.handleViewDetails(event.state.active_job_index);
            } else {
                this.handleReturn();
            }
        };
        
    },  
    handleJobChange: function(e) {
        if (this.state.jobs) {
            var job_id = this.state.active_job_index;
            var active_section = SECTION_JOB_LIST;
            if (job_id) {
                active_section = SECTION_JOB_DETAILS;
                for (var i = 0; i < this.state.jobs.length; ++i) {
                    if (this.state.jobs[i].id == job_id) {
                        this.handleViewDetails(i);
                        console.debug(
                            "Found job with a specified ID (" + job_id + "). " +
                            "Switching view."
                        );
                        return;
                    }
                }
                console.debug(
                    "Couldn't find any job with a specified ID (" + job_id + "). " +
                    "Resetting to job list."
                );
                this.handleReturn();
            } else {
                this.handleReturn();
            }
        }
    },
    handleViewDetails: function (index) {
        this.setState({
            active_section: SECTION_JOB_DETAILS,
            active_job_index: index
        });
    },
    handleReturn: function () {
        this.setState({
            active_section: SECTION_JOB_LIST,
            active_job_index: undefined
        });
    },
    handleJobDelete: function (jobID, index) {
        $.ajax({
            type: "DELETE",
            url: "/datasets/" + container.dataset.datasetId + "/" + jobID,
            success: function (data, textStatus, jqXHR) {
                console.log("Evaluation job " + jobID + " has been removed from the queue.")
            },
            error: function (jqXHR, textStatus, errorThrown) {
                console.error("Error occurred during job deletion:", jqXHR.responseJSON);
                alert("Failed to remove evaluation job " + jobID +
                        " from the queue. Reason: " + jqXHR.responseJSON.error);
            }
        });

        // Removing job from the list
        let jobs = this.state.jobs;
        jobs.splice(index, 1);
        this.setState({jobs: jobs});
    },
    render: function () {
        if (this.state.jobs) {
            if (this.state.active_section == SECTION_JOB_LIST) {
                return (
                    <JobList
                        jobs={this.state.jobs}
                        showDelete={this.state.isAuthorViewing}
                        onViewDetails={this.handleViewDetails}
                        onDelete={this.handleJobDelete} />
                );
            } else { // SECTION_JOB_DETAILS
               if (container.dataset.jobId) {
                    var active_job_index;
                    this.state.jobs.forEach(function (cls, index) {
                       if (container.dataset.jobId == cls.id) {
                           active_job_index = index;
                       }
                    });
                    this.state.active_job_index = active_job_index;
                }

                var active_job = this.state.jobs[this.state.active_job_index];
                return (
                    <JobDetails
                        index={this.state.active_job_index}
                        id={active_job.id}
                        created={active_job.created}
                        updated={active_job.updated}
                        status={active_job.status}
                        statusMsg={active_job.status_msg}
                        result={active_job.result}
                        showDelete={this.state.isAuthorViewing}
                        outdated={active_job.outdated}
                        onReturn={this.handleReturn} />
                );

            }
        } else {
            return (<strong>Loading job list...</strong>);
        }
    }
});


// Classes used with SECTION_JOB_LIST:

var JobList = React.createClass({
    propTypes: {
        jobs: React.PropTypes.array.isRequired,
        showDelete: React.PropTypes.bool.isRequired,
        onViewDetails: React.PropTypes.func.isRequired,
        onDelete: React.PropTypes.func.isRequired
    },
    render: function () {
        if (this.props.jobs.length > 0) {
            var items = [];
            this.props.jobs.forEach(function (cls, index) {
                items.push(
                    <JobRow
                        index={index}
                        id={cls.id}
                        created={cls.created}
                        status={cls.status}
                        outdated={cls.outdated}
                        showDelete={this.props.showDelete}
                        onViewDetails={this.props.onViewDetails}
                        onDelete={this.props.onDelete} />
                );
            }.bind(this));
            return (
                <table className="table table-hover job-list">
                    <thead>
                    <tr>
                        <th className="id">Job ID</th>
                        <th className="status">Status</th>
                        <th className="created">Creation time</th>
                        <th className="controls"></th>
                    </tr>
                    </thead>
                    <tbody>{items}</tbody>
                </table>
            );
        } else {
            return (
                <div className="alert alert-info">
                    This dataset has not been evaluated yet.
                </div>
            );
        }
    }
});

var JobRow = React.createClass({
    propTypes: {
        index: React.PropTypes.number.isRequired,
        id: React.PropTypes.string.isRequired,
        created: React.PropTypes.string.isRequired,
        status: React.PropTypes.string.isRequired,
        outdated: React.PropTypes.string.isRequired,
        showDelete: React.PropTypes.bool.isRequired,
        onViewDetails: React.PropTypes.func.isRequired,
        onDelete: React.PropTypes.func.isRequired
    },
    handleViewDetails: function (event) {
        event.preventDefault();
        this.props.onViewDetails(this.props.index);
    },
    handleDelete: function () {
        this.props.onDelete(this.props.id, this.props.index);
    },
    render: function () {
        var status = "";
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
                    status = <span className="label label-primary">Done, Outdated</span>;
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
                <td className="id"><a href={"evaluation/" + this.props.id} onClick={this.handleViewDetails}>{this.props.id}</a></td>
                <td className="status">{status}</td>
                <td className="created"><span>{this.props.created}</span></td>
                <td className="controls">{controls}</td>
            </tr>
        );
    }
});


let JobDeleteButton = React.createClass({
    propTypes: {
        onDelete: React.PropTypes.func.isRequired
    },
    getInitialState: function () {
        return {showConfirmation: false};
    },
    delete: function (event) {
        event.preventDefault();
        this.props.onDelete();
    },
    confirm: function (event) {
        event.preventDefault();
        this.setState({showConfirmation: true});
    },
    cancel: function (event) {
        event.preventDefault();
        this.setState({showConfirmation: false});
    },
    render: function () {
        if (!this.state.showConfirmation) {
            return <a href="#" className="btn btn-danger btn-xs"
                      title="Delete this evaluation job"
                      onClick={this.confirm}>Delete</a>;
        } else {
            return <div>
                <em>Are you sure?&nbsp;&nbsp;</em>
                <a href="#" className="btn btn-danger btn-xs"
                   onClick={this.delete}>Delete</a>
                <a href="#" className="btn btn-default btn-xs"
                   onClick={this.cancel}>Cancel</a>
            </div>;
        }
    }
});


// Classes used with SECTION_JOB_DETAILS:

var JobDetails = React.createClass({
    propTypes: {
        index: React.PropTypes.number.isRequired,
        id: React.PropTypes.string.isRequired,
        created: React.PropTypes.string.isRequired,
        updated: React.PropTypes.string.isRequired,
        status: React.PropTypes.string.isRequired,
        outdated: React.PropTypes.string.isRequired,
        statusMsg: React.PropTypes.string,
        result: React.PropTypes.object,
        onReturn: React.PropTypes.func.isRequired
    },
    componentDidMount() { 
        var url = window.location.href;

        if(window.location.href.indexOf("evaluation") == -1 )   
        url +=  "/evaluation" ;
         
        if(window.location.href.indexOf(this.props.id) == -1 )   
        url +=  "/"+this.props.id ;
         
        window.history.pushState({active_job_index:this.props.index},'job-details', url);    
    },
    render: function () {
        var status = "";
        switch (this.props.status) {
            case JOB_STATUS_PENDING:
                status = <div className="alert alert-info">
                    This job is in evaluation queue.
                </div>;
                break;
            case JOB_STATUS_RUNNING:
                status = <div className="alert alert-primary">
                    This evaluation job is being processed right now.
                </div>;
                break;
            case JOB_STATUS_FAILED:
                var errorMsg = "";
                if (this.props.statusMsg) {
                    errorMsg = <p>
                        Error details:<br />
                        {this.props.statusMsg}
                    </p>
                }
                status = <div className="alert alert-danger">
                    <strong>This evaluation job has failed!</strong>
                    {errorMsg}
                </div>;
                break;
            case JOB_STATUS_DONE:
                if (this.props.outdated) {
                    status = <div className="alert alert-success">
                        The dataset has been changed since this job was run, so the results may be out of date.
                    </div>;
                } else {
            status = <div className="alert alert-success">
                        This evaluation job has been completed on {this.props.updated}.
                        You can find results below.
                    </div>;
                }
                break;
        }
        var header = <div>
            <h3>Job {this.props.id}</h3>
            <p>
                <a href="javascript:window.history.back()" >
                    <strong>&larr; Back to job list</strong>
                </a>
            </p>
            <p><strong>Creation time:</strong> {this.props.created}</p>
            {status}
        </div>;
        if (this.props.status === JOB_STATUS_DONE) {
            return <div className="job-details">
                {header}
                <Results
                    accuracy={this.props.result.accuracy}
                    table={this.props.result.table}
                    />
            </div>;
        } else {
            return <div>{header}</div>;
        }
    }
});

var Results = React.createClass({
    propTypes: {
        accuracy: React.PropTypes.number.isRequired,
        table: React.PropTypes.string.isRequired
    },
    render: function () {
        var classes = [];
        this.props.table.classes.forEach(function (cls) {
            classes.push(<th className="active">{cls}</th>);
        }.bind(this));
        var header = <tr>
            <th></th>
            {classes}
            <th></th>
            <th className="active">Proportion</th>
        </tr>;

        var rows = [];
        var so = this;
        this.props.table.rows.forEach(function (cls, index) {
            var predicted = [];
            cls.predicted.forEach(function (inner_cls, inner_index) {
                var className = "";
                if (inner_index == index) {
                    if (inner_cls.percentage > 0) { className = "success"; }
                } else {
                    if (inner_cls.percentage >= 10) { className = "danger"; }
                }
                predicted.push(
                    <td className={className}>{inner_cls.percentage.toFixed(2)}</td>
                );
            }.bind(so));
            rows.push(
                <tr>
                    <th className="active">{so.props.table.classes[index]}</th>
                    {predicted}
                    <th className="active">{so.props.table.classes[index]}</th>
                    <td>{cls.proportion.toFixed(2)}</td>
                </tr>
            );
        }.bind(this));

        var table = <table className="table table-bordered table-condensed table-inner">
            <tbody>{header}{rows}</tbody>
        </table>;

        return (
            <div className="results">
                <p><strong>Accuracy:</strong> {this.props.accuracy}%</p>
                <table className="table table-bordered">
                    <tbody>
                    <tr><th className="active">Predicted (%)</th></tr>
                    <tr>
                        <td>{table}</td>
                        <th className="active">Actual (%)</th>
                    </tr>
                    </tbody>
                </table>
            </div>
        );

    }
});


if (container) ReactDOM.render(<EvaluationJobsViewer />, container);
