/** @jsx React.DOM */

var Dataset = React.createClass({
    handleClassCreate: function (name) {
        var classes = this.state.classes;
        classes.push(name);
        this.setState({classes: classes});
        console.debug("CLASS CREATED", this.state.classes);
    },
    handleClassUpdate: function (oldName, name, description, recordings) {
        var classes = this.state.classes;
        for (cls of classes) {
            if (cls.name == oldName) {
                cls.name = name;
                cls.description = description;
                cls.recordings = recordings;
                break;
            }
        }
        this.setState({classes: classes});
        console.debug("CLASS UPDATED", this.state.classes);
    },
    handleClassDelete: function (name) {
        var classes = this.state.classes;
        var index = -1;
        for (var i = 0; i < classes.length; ++i) {
            if (classes[i].name == name) {
                index = i;
                break;
            }
        }
        if (index > -1) {
            classes.splice(index, 1);
        }
        this.setState({classes: classes});
        console.debug("CLASS DELETED", this.state.classes);
    },
    handleDatasetUpdate: function () {
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
            classes: []
        };
    },
    render: function () {
        return (
            <div>
                <form className="form-horizontal">
                    <div className="form-group">
                        <label for="inputName" className="col-sm-2 control-label">
                            Name<span className="red">*</span>
                        </label>
                        <div className="col-sm-4">
                            <input type="text" className="form-control" placeholder="Dataset name"
                                ref="name" id="inputName" required="required"
                                onChange={this.handleDatasetUpdate} />
                        </div>
                    </div>
                    <div className="form-group">
                        <label for="inputDescr" className="col-sm-2 control-label">Description</label>
                        <div className="col-sm-4">
                            <textarea className="form-control" placeholder="Description (optional)"
                                rows="3" ref="description" id="inputDescr"
                                onChange={this.handleDatasetUpdate}></textarea>
                        </div>
                    </div>
                </form>
                <h3>Classes</h3>
                <AddClassForm onClassCreate={this.handleClassCreate}
                    classes={this.state.classes} />
                <ClassList classes={this.state.classes}
                    onClassUpdate={this.handleClassUpdate}
                    onClassDelete={this.handleClassDelete} />
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
                    className="btn btn-default btn-primary">Create</button>
            </div>
        );
    }
});

var AddClassForm = React.createClass({
    handleSubmit: function (e) {
        e.preventDefault();
        var name = this.refs.name.getDOMNode().value.trim();
        if (!name) {
            return;
        }
        this.props.onClassCreate({
            name: name,
            description: "",  // TODO: Implement
            recordings: []
        });
        this.refs.name.getDOMNode().value = '';
    },
    handleChange: function() {
        // Making sure that class name is unique
        var new_name = this.refs.name.getDOMNode().value;
        var classes = this.props.classes;
        var index = -1;
        for (var i = 0; i < classes.length; ++i) {
            if (classes[i].name == new_name) {
                index = i;
                break;
            }
        }
        this.setState({validInput: index == -1 || new_name.length == 0});
        // TODO: Show informative error message if input is invalid.
    },
    getInitialState: function () {
        return {validInput: true};
    },
    render: function () {
        // TODO: Add description input
        return (
            <form className="addClassForm form-inline" onSubmit={this.handleSubmit}>
                <div className={this.state.validInput ? 'input-group' : 'input-group has-error'}>
                    <input type="text" className="form-control" placeholder="Class name"
                        ref="name" onChange={this.handleChange} />
                    <span className="input-group-btn">
                        <button disabled={this.state.validInput ? '' : 'disabled'}
                            className="btn btn-default" type="submit">Add</button>
                    </span>
                </div>
            </form>
        );
    }
});

var ClassList = React.createClass({
    render: function () {
        var items = [];
        this.props.classes.forEach(function (cls) {
            items.push(<Class name={cls.name} description={cls.description} recordings={cls.recordings}
                onClassUpdate={this.props.onClassUpdate} onClassDelete={this.props.onClassDelete} />);
        }.bind(this));
        if (items.length > 0) {
            return (<ul>{items}</ul>);
        } else {
            return (<p><strong>No classes in this dataset</strong></p>)
        }
    }
});

var Class = React.createClass({
    handleRecordingUpdate: function (recordings) {
        this.props.onClassUpdate(this.props.name, this.props.name, this.props.description, recordings);
    },
    handleEdit: function (event) {
        event.preventDefault();
        // TODO: Implement class editor
    },
    handleDelete: function (event) {
        event.preventDefault();
        this.props.onClassDelete(this.props.name);
    },
    render: function () {
        return (
            <div>
                <h3>{this.props.name}</h3>
                <p><em>{this.props.description}</em></p>
                <button onClick={this.handleEdit} className="btn btn-xs btn-default" type="button">Edit</button>&nbsp;
                <button onClick={this.handleDelete} className="btn btn-xs btn-danger" type="submit">Delete</button>
                <Recordings recordings={this.props.recordings} onRecordingsUpdate={this.handleRecordingUpdate} />
                <hr />
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
        console.log("Deleted", mbid);
    },
    render: function () {
        return (
            <div>
                <h4>Recordings</h4>
                <RecordingAddForm recordings={this.props.recordings} onRecordingSubmit={this.handleRecordingSubmit} />
                <RecordingList recordings={this.props.recordings} onRecordingDelete={this.handleRecordingDelete} />
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
            <form className="addClassForm clearfix form-inline" onSubmit={this.handleSubmit}>
                <div className={this.state.validInput ? 'input-group' : 'input-group has-error'}>
                    <input type="text" className="form-control" placeholder="MusicBrainz ID"
                        ref="mbid" onChange={this.handleChange} />
                    <span className="input-group-btn">
                        <button disabled={this.state.validInput ? '' : 'disabled'}
                            className="btn btn-default" type="submit">Add</button>
                    </span>
                </div>
            </form>
        );
    }
});

var RecordingList = React.createClass({
    render: function () {
        var items = [];
        this.props.recordings.forEach(function (recording) {
            items.push(<Recording mbid={recording} onRecordingDelete={this.props.onRecordingDelete} />);
        }.bind(this));
        if (items.length > 0) {
            return (<ul>{items}</ul>);
        } else {
            return (<p><strong>No recordings</strong></p>)
        }
    }
});

var Recording = React.createClass({
    handleDelete: function (event) {
        event.preventDefault();
        this.props.onRecordingDelete(this.props.mbid);
    },
    render: function () {
        return (
            <li>
                <strong>{this.props.mbid}</strong>&nbsp;
                <button onClick={this.handleDelete} type="button" className="btn btn-xs btn-danger">Delete</button>
            </li>
        );
    }
});

React.render(<Dataset />, document.getElementById('content'));
