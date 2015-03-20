/** @jsx React.DOM */

var Dataset = React.createClass({
    handleClassCreate: function () {
        var classes = this.state.classes;
        var counter = this.state.classSeq + 1;
        classes.push({
            id: counter,
            name: "Class " + counter,
            description: "",
            recordings: []
        });
        this.setState({
            classes: classes,
            classSeq: counter
        });
    },
    handleClassUpdate: function (id, name, description, recordings) {
        var classes = this.state.classes;
        console.log(id, name);
        for (cls of classes) {
            if (cls.id == id) {
                cls.name = name;
                cls.description = description;
                cls.recordings = recordings;
                break;
            }
        }
        this.setState({classes: classes});
    },
    handleClassDelete: function (id) {
        var classes = this.state.classes;
        var index = -1;
        for (var i = 0; i < classes.length; ++i) {
            if (classes[i].id == id) {
                index = i;
                break;
            }
        }
        if (index > -1) {
            classes.splice(index, 1);
        }
        this.setState({classes: classes});
    },
    handleDatasetUpdate: function () {
        console.log(this.refs.name.getDOMNode().value);
        this.setState({
            name: this.refs.name.getDOMNode().value,
            description: this.refs.description.getDOMNode().value,
            classes: this.state.classes
        });
    },
    getInitialState: function () {
        return {
            name: "",
            description: "",
            classes: [],
            classSeq: 0 // Used for assigning internal class IDs
        };
    },
    render: function () {
        return (
            <div>
                <form className="form-horizontal dataset-details">
                    <div className="form-group form-group-sm">
                        <label for="inputName" className="col-sm-2 control-label">
                            Name<span className="red">*</span>:
                        </label>
                        <div className="col-sm-3">
                            <input type="text" className="form-control"
                                ref="name" id="inputName" required="required"
                                onChange={this.handleDatasetUpdate} />
                        </div>
                    </div>
                    <div className="form-group form-group-sm">
                        <label for="inputDescr" className="col-sm-2 control-label">Description:</label>
                        <div className="col-sm-3">
                            <textarea className="form-control"
                                rows="2" ref="description" id="inputDescr"
                                onChange={this.handleDatasetUpdate}></textarea>
                        </div>
                    </div>
                </form>
                <ClassList
                    classes={this.state.classes}
                    onClassUpdate={this.handleClassUpdate}
                    onClassDelete={this.handleClassDelete} />
                <AddClassButton onClassCreate={this.handleClassCreate} />
                <SubmitDatasetButton
                    name={this.state.name}
                    description={this.state.description}
                    classes={this.state.classes} />
            </div>
        );
    }
});

var SubmitDatasetButton = React.createClass({
    handleSubmit: function (e) {
        e.preventDefault();
        // TODO: Make sure that all classes contain at least one recording!
        this.setState({
            enabled: false,
            errorMsg: null
        });
        var so = this;
        console.log(this.props.classes);
        $.ajax({
            type: "POST",
            url: "/datasets/create/",
            data: JSON.stringify({
                'name': this.props.name,
                'description': this.props.description,
                'classes': this.props.classes
            }),
            dataType: "json",
            contentType: "application/json; charset=utf-8",
            success: function (data, textStatus, jqXHR) {
                window.location.replace("/datasets/" + data.dataset_id);
            },
            error: function (jqXHR, textStatus, errorThrown) {
                so.setState({
                    enabled: true,
                    errorMsg: jqXHR.responseJSON
                });
            }
        });
    },
    getInitialState: function () {
        return {
            enabled: true,
            errorMsg: null
        };
    },
    render: function () {
        return (
            <div className="form-group">
                <p className={this.state.errorMsg ? 'text-danger' : 'hidden'}>
                    <strong>Error occured while submitting this dataset:</strong>
                    <br />{ this.state.errorMsg }
                </p>
                <button onClick={this.handleSubmit} type="button"
                    disabled={this.state.enabled ? '' : 'disabled'}
                    className="btn btn-default btn-primary">Submit</button>
            </div>
        );
    }
});

var AddClassButton = React.createClass({
    render: function () {
        return (
            <div className="form-group">
                <button onClick={this.props.onClassCreate} type="button"
                    className="btn btn-sm btn-success">Add class</button>
            </div>
        );
    }
});

var ClassList = React.createClass({
    render: function () {
        var items = [];
        this.props.classes.forEach(function (cls) {
            console.log(cls.recordings);
            items.push(<Class id={cls.id} name={cls.name} description={cls.description} recordings={cls.recordings}
                onClassUpdate={this.props.onClassUpdate}
                onClassDelete={this.props.onClassDelete} />);
        }.bind(this));
        return (<div>{items}</div>);
    }
});

var Class = React.createClass({
    handleClassUpdate: function() {
        console.log(this.props.name);
        this.props.onClassUpdate(
            this.props.id,
            this.refs.name.getDOMNode().value,
            this.refs.description.getDOMNode().value,
            this.props.recordings
        );
    },
    handleRecordingsUpdate: function (recordings) {
        console.log(this.props.name);
        this.props.onClassUpdate(
            this.props.id,
            this.props.name,
            this.props.description,
            recordings
        );
    },
    handleDelete: function (event) {
        event.preventDefault();
        this.props.onClassDelete(this.props.id);
    },
    render: function () {
        console.log(this.props);
        // TODO: Move delete button into the header
        return (
            <div className="panel panel-info class">
                <div className="panel-heading">
                    <table>
                        <tr>
                            <td className="name-col">
                                <input type="text" placeholder="Class name" className="form-control"
                                    ref="name" id="inputName" required="required"
                                    onChange={this.handleClassUpdate} /></td>
                            <td className="remove-col">
                                <button type="button" className="close" title="Remove class"
                                    onClick={this.handleDelete}>&times;</button>
                            </td>
                        </tr>
                    </table>
                </div>
                <div className="panel-body">
                    <form className="form-horizontal dataset-details">
                        <div className="form-group form-group-sm">
                            <div className="col-sm-12">
                                <textarea className="form-control" placeholder="Description (optional)"
                                    rows="2" ref="description" id="inputDescr"
                                    onChange={this.handleClassUpdate}></textarea>
                            </div>
                        </div>
                    </form>
                    <Recordings
                        recordings={this.props.recordings}
                        onRecordingsUpdate={this.handleRecordingsUpdate} />
                </div>
            </div>
        );
    }
});

var Recordings = React.createClass({
    handleRecordingSubmit: function (mbid) {
        var recordings = this.props.recordings;
        recordings.push(mbid);
        this.props.onRecordingsUpdate(recordings);
    },
    handleRecordingDelete: function (mbid) {
        var recordings = this.props.recordings;
        var index = recordings.indexOf(mbid);
        if (index > -1) {
            recordings.splice(index, 1);
        }
        this.props.onRecordingsUpdate(recordings);
    },
    render: function () {
        return (
            <div>
                <h4>Recordings</h4>
                <RecordingList
                    recordings={this.props.recordings}
                    onRecordingDelete={this.handleRecordingDelete} />
                <RecordingAddForm
                    recordings={this.props.recordings}
                    onRecordingSubmit={this.handleRecordingSubmit} />
            </div>
        );
    }
});

var RecordingAddForm = React.createClass({
    handleSubmit: function (event) {
        event.preventDefault();
        var mbid = this.refs.mbid.getDOMNode().value.trim();
        if (!mbid) {
            return;
        }
        this.props.onRecordingSubmit(mbid);
        this.refs.mbid.getDOMNode().value = '';
    },
    handleChange: function () {
        var mbid = this.refs.mbid.getDOMNode().value;
        var isValidUUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(mbid);
        var isNotDuplicate = this.props.recordings.indexOf(mbid) == -1;
        this.setState({validInput: (isValidUUID && isNotDuplicate) || mbid.length == 0});
        // TODO: Show informative error messages if input is invalid.
    },
    getInitialState: function () {
        return {validInput: true};
    },
    render: function () {
        return (
            <form className="recording-add clearfix form-inline form-group-sm" onSubmit={this.handleSubmit}>
                <div className={this.state.validInput ? 'input-group' : 'input-group has-error'}>
                    <input type="text" className="form-control input-sm" placeholder="MusicBrainz ID"
                        ref="mbid" onChange={this.handleChange} />
                    <span className="input-group-btn">
                        <button disabled={this.state.validInput ? '' : 'disabled'}
                            className="btn btn-default btn-sm" type="submit">Add recording</button>
                    </span>
                </div>
            </form>
        );
    }
});

var RecordingList = React.createClass({
    render: function () {
        var items = [];
        console.log("recordings", this.props.recordings);
        this.props.recordings.forEach(function (recording) {
            items.push(<Recording mbid={recording} onRecordingDelete={this.props.onRecordingDelete} />);
        }.bind(this));
        return (<table className="table recordings">{items}</table>);
    }
});

var Recording = React.createClass({
    handleDelete: function (event) {
        event.preventDefault();
        this.props.onRecordingDelete(this.props.mbid);
    },
    render: function () {
        return (
            <tr>
                <td className="mbid-col">{this.props.mbid}</td>
                <td className="remove-col">
                    <button type="button" className="close" title="Remove recording"
                        onClick={this.handleDelete}>&times;</button>
                </td>
            </tr>
        );
    }
});

React.render(<Dataset />, document.getElementById('dataset-editor'));
