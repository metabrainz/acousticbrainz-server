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

var SECTION_DATASET_DETAILS = "dataset_details";
var SECTION_CLASS_DETAILS = "class_details";

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

 It is divided into two sections (current section is set in active_section):
 - SECTION_DATASET_DETAILS (editing dataset info and list of classes)
 - SECTION_CLASS_DETAILS (editing specific class; this also requires
 active_class_id variable to be set in Dataset state)
 */
var Dataset = React.createClass({
    getInitialState: function () {
        return {
            mode: container.dataset.mode,
            active_section: SECTION_DATASET_DETAILS,
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
    handleDetailsUpdate: function (name, description) {
        var nextStateData = this.state.data;
        nextStateData.name = name;
        nextStateData.description = description;
        this.setState({data: nextStateData});
    },
    handleReturn: function () {
        this.setState({
            active_section: SECTION_DATASET_DETAILS,
            active_class_id: undefined
        });
    },
    handleClassCreate: function () {
        var nextStateData = this.state.data;
        nextStateData.classes.push({
            id: this.state.classSeq,
            name: "Class #" + this.state.classSeq,
            description: "",
            recordings: []
        });
        nextStateData.classSeq++;
        this.setState({
            data: nextStateData,
            classSeq: this.state.classSeq + 1
        });
    },
    handleClassEdit: function (id) {
        this.setState({
            active_section: SECTION_CLASS_DETAILS,
            active_class_id: id
        });
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
    render: function () {
        if (this.state.data) {
            if (this.state.active_section == SECTION_DATASET_DETAILS) {
                // TODO: Move ClassList into DatasetDetails
                return (
                    <div>
                        <DatasetDetails
                            name={this.state.data.name}
                            description={this.state.data.description}
                            onDetailsUpdate={this.handleDetailsUpdate} />
                        <ClassList
                            classes={this.state.data.classes}
                            onClassCreate={this.handleClassCreate}
                            onClassEdit={this.handleClassEdit}
                            onClassDelete={this.handleClassDelete} />
                        <hr />
                        <SubmitDatasetButton
                            mode={this.state.mode}
                            data={this.state.data} />
                    </div>
                );
            } else { // SECTION_CLASS_DETAILS
                for (cls of this.state.data.classes) {
                    if (cls.id == this.state.active_class_id) {
                        return (
                            <ClassDetails
                                id={cls.id}
                                name={cls.name}
                                description={cls.description}
                                recordings={cls.recordings}
                                datasetName={this.state.data.name}
                                onReturn={this.handleReturn}
                                onClassUpdate={this.handleClassUpdate} />
                        );
                    }
                }
            }
        } else {
            return (<strong>Loading...</strong>);
        }
    }
});


// Classes used with SECTION_DATASET_DETAILS:

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
            <div className="dataset-details">
                <h2>
                    <input type="text"
                           placeholder="Name" required="required"
                           value={this.props.name} ref="name"
                           size={this.props.name.length}
                           onChange={this.handleDetailsUpdate} />
                </h2>
                <textarea ref="description"
                          placeholder="Description (optional)"
                          value={this.props.description}
                          onChange={this.handleDetailsUpdate}></textarea>
            </div>
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

var ClassList = React.createClass({
    propTypes: {
        onClassCreate: React.PropTypes.func.isRequired,
        onClassEdit: React.PropTypes.func.isRequired,
        onClassDelete: React.PropTypes.func.isRequired
    },
    render: function () {
        var items = [];
        this.props.classes.forEach(function (cls) {
            items.push(<Class id={cls.id}
                              name={cls.name}
                              description={cls.description}
                              recordingCounter={cls.recordings.length}
                              onClassEdit={this.props.onClassEdit}
                              onClassDelete={this.props.onClassDelete} />);
        }.bind(this));
        return (
            <div>
                <h3>Classes</h3>
                <div className="class-list row">
                    {items}
                    <div className="col-md-3">
                        <a className="thumbnail add-class-link" href='#'
                           onClick={this.props.onClassCreate}>
                            + Add new class
                        </a>
                    </div>
                </div>
            </div>
        );
    }
});

var Class = React.createClass({
    propTypes: {
        id: React.PropTypes.number.isRequired,
        name: React.PropTypes.string.isRequired,
        description: React.PropTypes.string.isRequired,
        recordingCounter: React.PropTypes.number.isRequired,
        onClassDelete: React.PropTypes.func.isRequired,
        onClassEdit: React.PropTypes.func.isRequired
    },
    handleDelete: function (event) {
        event.preventDefault();
        this.props.onClassDelete(this.props.id);
    },
    handleEdit: function (event) {
        event.preventDefault();
        this.props.onClassEdit(this.props.id);
    },
    render: function () {
        var name = this.props.name;
        if (!name) name = "Class #" + this.props.id;
        var recordingsCounterText = this.props.recordingCounter.toString() + " ";
        if (this.props.recordingCounter == 1) recordingsCounterText += "recording";
        else recordingsCounterText += "recordings";
        return (
            <div className="col-md-3">
                <a href="#" onClick={this.handleEdit} className="thumbnail">
                    <div className="name">{name}</div>
                    <div className="counter">{recordingsCounterText}</div>
                </a>
                <div className="controls clearfix">
                    <button type="button" className="close pull-right" title="Remove class"
                            onClick={this.handleDelete}>&times;</button>
                </div>
            </div>
        );
    }
});


// Classes used with SECTION_CLASS_DETAILS:

var ClassDetails = React.createClass({
    propTypes: {
        id: React.PropTypes.number.isRequired,
        name: React.PropTypes.string.isRequired,
        description: React.PropTypes.string.isRequired,
        recordings: React.PropTypes.array.isRequired,
        datasetName: React.PropTypes.string.isRequired,
        onReturn: React.PropTypes.func.isRequired,
        onClassUpdate: React.PropTypes.func.isRequired
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
    render: function () {
        return (
            <div className="class-details">
                <h2>
                    <a href='#' onClick={this.props.onReturn}
                       title="Back to dataset details">
                        {this.props.datasetName}
                    </a>
                    &nbsp;/&nbsp;
                    <input type="text" placeholder="Class name"
                           ref="name" required="required"
                           id="class-name"
                           onChange={this.handleClassUpdate}
                           size={this.props.name.length}
                           value={this.props.name} />
                </h2>
                <p>
                    <a href='#' onClick={this.props.onReturn}>
                        <strong>&larr; Back to dataset details</strong>
                    </a>
                </p>
                <textarea ref="description"
                          placeholder="Description of this class (optional)"
                          onChange={this.handleClassUpdate}
                          value={this.props.description}></textarea>
                <Recordings
                    recordings={this.props.recordings}
                    onRecordingsUpdate={this.handleRecordingsUpdate} />
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
