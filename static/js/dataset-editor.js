/** @jsx React.DOM */
/*
 This is a dataset editor. It works in two modes:
 - create (creates new dataset from scratch)
 - edit (edits existing dataset)

 Mode is set by defining "data-mode" attribute on the container element which is
 referenced in CONTAINER_ELEMENT_ID. Value of this attribute is either "create"
 or "edit" (see definitions below: MODE_CREATE and MODE_EDIT).

 When mode is set to "edit", attribute "data-edit-id" need to be specified. This
 attribute references existing dataset by its ID. When Dataset component is
 mounted, it pull existing dataset for editing from the server.
 */

var CONTAINER_ELEMENT_ID = "dataset-editor";
var container = document.getElementById(CONTAINER_ELEMENT_ID);

var MODE_CREATE = "create";
var MODE_EDIT = "edit";

/*
 Dataset is the primary class in the dataset editor. Its state contains
 dataset itself and other internal variables:
 - data:
     - id (dataset ID that is used only when editing existing dataset)
     - name (name of the dataset)
     - description (optional description of the dataset)
     - classes: [ (array of classes with the following structure)
         - id (internal class ID that is used only in the editor)
         - name
         - description
         - recordings (array of recording MBIDs)
       ]
 - classSeq (used for assigning internal class IDs)
 */
var Dataset = React.createClass({
    handleDetailsUpdate: function (name, description) {
        var nextStateData = this.state.data;
        nextStateData.name = name;
        nextStateData.description = description;
        this.setState({data: nextStateData});
    },
    handleClassCreate: function () {
        var nextStateData = this.state.data;
        nextStateData.classes.push({
            id: this.state.classSeq,
            name: "Class " + this.state.classSeq,
            description: "",
            recordings: []
        });
        nextStateData.classSeq++;
        this.setState({
            data: nextStateData,
            classSeq: this.state.classSeq + 1
        });
    },
    handleClassUpdate: function (id, name, description, recordings) {
        var nextStateData = this.state.data;
        var classes = nextStateData.classes;
        for (cls of classes) {
            if (cls.id == id) {
                cls.name = name;
                cls.description = description;
                cls.recordings = recordings;
                break;
            }
        }
        nextStateData.classes = classes;
        this.setState({data: nextStateData});
    },
    handleClassDelete: function (id) {
        var nextStateData = this.state.data;
        var classes = nextStateData.classes;
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
        nextStateData.classes = classes;
        this.setState({data: nextStateData});
    },
    getInitialState: function () {
        return {
            mode: container.dataset.mode,
            classSeq: 1, // Used for assigning internal class IDs
            data: null
        };
    },
    componentDidMount: function() {
        // This function is invoked when Dataset component is originally
        // mounted. Here we need to check what mode dataset editor is in, and
        // pull data from the server if mode is MODE_EDIT.
        // Do not confuse property called "dataset" with our own datasets. See
        // https://developer.mozilla.org/en-US/docs/Web/API/HTMLElement/dataset
        // for more info about it.
        if (this.state.mode == MODE_EDIT) {
            if (!container.dataset.editId) {
                console.error("ID of existing dataset needs to be specified" +
                "in data-edit-id property.");
                return;
            }
            $.get("/datasets/" + container.dataset.editId + "/json", function(result) {
                if (this.isMounted()) {
                    // Assigning internal class IDs
                    var classSeq = 1;
                    for (cls of result.classes) {
                        cls.id = classSeq++;
                    }
                    this.setState({
                        classSeq: classSeq,
                        data: result
                    });
                }
            }.bind(this));
        } else {
            if (this.state.mode != MODE_CREATE) {
                console.warn('Unknown dataset editor mode! Using default: MODE_CREATE.');
            }
            this.setState({
                mode: MODE_CREATE,
                data: {
                    name: "",
                    description: "",
                    classes: []
                }
            });
        }
    },
    render: function () {
        if (this.state.data) {
            return (
                <div>
                    <DatasetDetails
                        name={this.state.data.name}
                        description={this.state.data.description}
                        onDetailsUpdate={this.handleDetailsUpdate} />
                    <ClassList
                        classes={this.state.data.classes}
                        onClassUpdate={this.handleClassUpdate}
                        onClassDelete={this.handleClassDelete} />
                    <AddClassButton onClassCreate={this.handleClassCreate} />
                    <SubmitDatasetButton
                        mode={this.state.mode}
                        data={this.state.data} />
                </div>
            );
        } else {
            return (<strong>Loading...</strong>);
        }
    }
});

var DatasetDetails = React.createClass({
    propTypes: {
        name: React.PropTypes.string.isRequired,
        description: React.PropTypes.string.isRequired,
        onDetailsUpdate: React.PropTypes.func.isRequired
    },
    handleDetailsUpdate: function () {
        this.props.onDetailsUpdate(
            this.refs.name.getDOMNode().value,
            this.refs.description.getDOMNode().value
        );
    },
    render: function () {
        return (
            <form className="form-horizontal dataset-details">
                <div className="form-group form-group-sm">
                    <label for="inputName" className="col-sm-2 control-label">
                        Name<span className="red">*</span>:
                    </label>
                    <div className="col-sm-3">
                        <input type="text" className="form-control"
                               id="inputName" required="required"
                               value={this.props.name} ref="name"
                               onChange={this.handleDetailsUpdate}/>
                    </div>
                </div>
                <div className="form-group form-group-sm">
                    <label for="inputDescr" className="col-sm-2 control-label">Description:</label>
                    <div className="col-sm-3">
                        <textarea className="form-control" rows="2"
                                  id="inputDescr" ref="description"
                                  value={this.props.description}
                                  onChange={this.handleDetailsUpdate}></textarea>
                    </div>
                </div>
            </form>
        );
    }
});

var SubmitDatasetButton = React.createClass({
    propTypes: {
        mode: React.PropTypes.string.isRequired,
        data: React.PropTypes.object.isRequired
    },
    handleSubmit: function (e) {
        e.preventDefault();
        this.setState({
            enabled: false,
            errorMsg: null
        });
        var submitEndpoint = null;
        if (this.props.mode == MODE_CREATE) {
            submitEndpoint = "/datasets/create";
        } else { // MODE_EDIT
            submitEndpoint = "/datasets/" + container.dataset.editId + "/edit";
        }
        var so = this;
        $.ajax({
            type: "POST",
            url: submitEndpoint,
            data: JSON.stringify({
                'id': this.props.data.id,  // used only with MODE_EDIT
                'name': this.props.data.name,
                'description': this.props.data.description,
                'classes': this.props.data.classes
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
        var buttonText = "Submit";
        if (this.props.mode == MODE_EDIT) {
            buttonText = "Update";
        }
        return (
            <div className="form-group">
                <p className={this.state.errorMsg ? 'text-danger' : 'hidden'}>
                    <strong>Error occured while submitting this dataset:</strong>
                    <br />{ this.state.errorMsg }
                </p>
                <button onClick={this.handleSubmit} type="button"
                        disabled={this.state.enabled ? '' : 'disabled'}
                        className="btn btn-default btn-primary">{buttonText}</button>
            </div>
        );
    }
});

var AddClassButton = React.createClass({
    propTypes: {
        onClassCreate: React.PropTypes.func.isRequired
    },
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
    propTypes: {
        onClassUpdate: React.PropTypes.func.isRequired,
        onClassDelete: React.PropTypes.func.isRequired
    },
    render: function () {
        var items = [];
        this.props.classes.forEach(function (cls) {
            items.push(<Class id={cls.id} name={cls.name} description={cls.description} recordings={cls.recordings}
                              onClassUpdate={this.props.onClassUpdate}
                              onClassDelete={this.props.onClassDelete} />);
        }.bind(this));
        return (<div>{items}</div>);
    }
});

var Class = React.createClass({
    propTypes: {
        id: React.PropTypes.number.isRequired,
        name: React.PropTypes.string.isRequired,
        description: React.PropTypes.string.isRequired,
        recordings: React.PropTypes.array.isRequired,
        onClassUpdate: React.PropTypes.func.isRequired,
        onClassDelete: React.PropTypes.func.isRequired
    },
    handleClassUpdate: function() {
        this.props.onClassUpdate(
            this.props.id,
            this.refs.name.getDOMNode().value,
            this.refs.description.getDOMNode().value,
            this.props.recordings
        );
    },
    handleRecordingsUpdate: function (recordings) {
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
        return (
            <div className="panel panel-info class">
                <div className="panel-heading">
                    <table>
                        <tr>
                            <td className="name-col">
                                <input type="text" placeholder="Class name" className="form-control"
                                       ref="name" id="inputName" required="required"
                                       onChange={this.handleClassUpdate}
                                       value={this.props.name} /></td>
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
                                          onChange={this.handleClassUpdate}
                                          value={this.props.description}></textarea>
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
    propTypes: {
        recordings: React.PropTypes.array.isRequired,
        onRecordingsUpdate: React.PropTypes.func.isRequired
    },
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
    propTypes: {
        recordings: React.PropTypes.array.isRequired,
        onRecordingSubmit: React.PropTypes.func.isRequired
    },
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
    propTypes: {
        onRecordingDelete: React.PropTypes.func.isRequired
    },
    render: function () {
        var items = [];
        this.props.recordings.forEach(function (recording) {
            items.push(<Recording mbid={recording} onRecordingDelete={this.props.onRecordingDelete} />);
        }.bind(this));
        return (<table className="recordings"><tbody>{items}</tbody></table>);
    }
});

var Recording = React.createClass({
    propTypes: {
        mbid: React.PropTypes.string.isRequired
    },
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


React.render(<Dataset />, container);
