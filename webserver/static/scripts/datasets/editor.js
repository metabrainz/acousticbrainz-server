const PropTypes = require("prop-types");
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
const React = require("react");
const ReactDOM = require("react-dom");

const CONTAINER_ELEMENT_ID = "dataset-editor";
const container = document.getElementById(CONTAINER_ELEMENT_ID);

const MODE_CREATE = "create";
const MODE_EDIT = "edit";

const SECTION_DATASET_DETAILS = "dataset_details";
const SECTION_CLASS_DETAILS = "class_details";

/*
 Dataset is the primary class in the dataset editor. Its state contains
 dataset itself and other internal variables:
   - mode (determines what mode dataset editor is in; can be either MODE_CREATE
     when creating new dataset or MODE_EDIT when modifying existing dataset)
   - data:
     - id (dataset ID that is used only when editing existing dataset)
     - name (name of the dataset)
     - description (optional description of the dataset)
     - classes: [ (array of classes with the following structure)
       - name
       - description
       - recordings (array of recording MBIDs)
     ]
   - active_section (determines what major part of the UI is currently shown
     to a user)

 It is divided into two sections (current section is set in active_section):
   - SECTION_DATASET_DETAILS (editing dataset info and list of classes)
   - SECTION_CLASS_DETAILS (editing specific class; this also requires
     active_class_index variable to be set in Dataset state)
 */
class Dataset extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            autoAddRecording: false,
            mode: container.dataset.mode,
            active_section: SECTION_DATASET_DETAILS,
            data: null,
        };
    }

    componentDidMount() {
        // This function is invoked when Dataset component is originally
        // mounted. Here we need to check what mode dataset editor is in, and
        // pull data from the server if mode is MODE_EDIT.
        // Do not confuse property called "dataset" with our own datasets. See
        // https://developer.mozilla.org/en-US/docs/Web/API/HTMLElement/dataset
        // for more info about it.
        if (this.state.mode === MODE_EDIT) {
            if (!container.dataset.editId) {
                console.error(
                    "ID of existing dataset needs to be specified" +
                        "in data-edit-id property."
                );
                return;
            }
            $.get(
                `/datasets/service/${container.dataset.editId}/json`,
                function (result) {
                    this.setState({ data: result });
                }.bind(this)
            );
        } else {
            if (this.state.mode !== MODE_CREATE) {
                console.warn(
                    "Unknown dataset editor mode! Using default: MODE_CREATE."
                );
            }
            this.setState({
                mode: MODE_CREATE,
                data: {
                    name: "",
                    description: "",
                    classes: [],
                    public: true,
                },
            });
        }
    }

    handleDetailsUpdate = (name, description) => {
        const nextStateData = this.state.data;
        nextStateData.name = name;
        nextStateData.description = description;
        this.setState({ data: nextStateData });
    };

    handlePrivacyUpdate = (event) => {
        const nextStateData = this.state.data;
        nextStateData.public = event.target.checked;
        this.setState({ data: nextStateData });
    };

    handleReturn = () => {
        this.setState({
            active_section: SECTION_DATASET_DETAILS,
            active_class_index: undefined,
        });
    };

    handleClassCreate = () => {
        const nextStateData = this.state.data;
        nextStateData.classes.push({
            name: "",
            description: "",
            recordings: [],
        });
        this.setState({ data: nextStateData });
    };

    handleClassEdit = (index) => {
        this.setState({
            active_section: SECTION_CLASS_DETAILS,
            active_class_index: index,
        });
    };

    handleClassDelete = (index) => {
        const { data } = this.state;
        data.classes.splice(index, 1);
        this.setState({ data });
    };

    handleClassUpdate = (index, name, description, recordings) => {
        const { data } = this.state;
        data.classes[index].name = name;
        data.classes[index].description = description;
        data.classes[index].recordings = recordings;
        this.setState({ data });
    };

    handleAutoAddRecordingUpdate = (autoAddRecording) => {
        this.setState({ autoAddRecording });
    };

    render() {
        if (this.state.data) {
            if (this.state.active_section === SECTION_DATASET_DETAILS) {
                // TODO: Move ClassList into DatasetDetails
                return (
                    <div>
                        <DatasetDetails
                            name={this.state.data.name}
                            description={this.state.data.description}
                            onDetailsUpdate={this.handleDetailsUpdate}
                        />
                        <ClassList
                            classes={this.state.data.classes}
                            onClassCreate={this.handleClassCreate}
                            onClassEdit={this.handleClassEdit}
                            onClassDelete={this.handleClassDelete}
                        />
                        <hr />
                        <p className="checkbox">
                            <label>
                                <input
                                    type="checkbox"
                                    checked={this.state.data.public}
                                    onChange={this.handlePrivacyUpdate}
                                />
                                &nbsp;<strong>Make this dataset public</strong>
                            </label>
                        </p>
                        <DatasetControlButtons
                            mode={this.state.mode}
                            data={this.state.data}
                        />
                    </div>
                );
            } // SECTION_CLASS_DETAILS
            const active_class = this.state.data.classes[
                this.state.active_class_index
            ];
            return (
                <ClassDetails
                    id={this.state.active_class_index}
                    name={active_class.name}
                    description={active_class.description}
                    recordings={active_class.recordings}
                    datasetName={this.state.data.name}
                    autoAddRecording={this.state.autoAddRecording}
                    onAutoAddRecordingUpdate={this.handleAutoAddRecordingUpdate}
                    onReturn={this.handleReturn}
                    onClassUpdate={this.handleClassUpdate}
                />
            );
        }
        return <strong>Loading...</strong>;
    }
}

// Classes used with SECTION_DATASET_DETAILS:

class DatasetDetails extends React.Component {
    static propTypes = {
        name: PropTypes.string.isRequired,
        description: PropTypes.string.isRequired,
        onDetailsUpdate: PropTypes.func.isRequired,
    };

    handleDescriptionUpdate = (event) => {
        const description = event.target.value;
        this.props.onDetailsUpdate(this.props.name, description);
    };

    handleNameUpdate = (event) => {
        const name = event.target.value;
        this.props.onDetailsUpdate(name, this.props.description);
    };

    render() {
        return (
            <div className="dataset-details">
                <h2 className="page-title">
                    Dataset&nbsp;
                    <input
                        type="text"
                        placeholder="Name"
                        required="required"
                        value={this.props.name}
                        size={this.props.name.length}
                        onChange={this.handleNameUpdate}
                    />
                </h2>
                <textarea
                    placeholder="Description (optional)"
                    value={this.props.description}
                    onChange={this.handleDescriptionUpdate}
                />
            </div>
        );
    }
}

class DatasetControlButtons extends React.Component {
    static propTypes = {
        mode: PropTypes.string.isRequired,
        data: PropTypes.object.isRequired,
    };

    state = {
        enabled: true,
        errorMsg: null,
    };

    handleSubmit = (e) => {
        e.preventDefault();
        this.setState({
            enabled: false,
            errorMsg: null,
        });
        let submitEndpoint = null;
        if (this.props.mode === MODE_CREATE) {
            submitEndpoint = "/datasets/service/create";
        } else {
            // MODE_EDIT
            submitEndpoint = `/datasets/service/${container.dataset.editId}/edit`;
        }
        const so = this;
        $.ajax({
            type: "POST",
            url: submitEndpoint,
            data: JSON.stringify({
                id: this.props.data.id, // used only with MODE_EDIT
                name: this.props.data.name,
                description: this.props.data.description,
                classes: this.props.data.classes,
                public: this.props.data.public,
            }),
            dataType: "json",
            contentType: "application/json; charset=utf-8",
            success(data, textStatus, jqXHR) {
                window.location.replace(`/datasets/${data.dataset_id}`);
            },
            error(jqXHR, textStatus, errorThrown) {
                so.setState({
                    enabled: true,
                    errorMsg: jqXHR.responseJSON,
                });
            },
        });
    };

    handleCancel = (e) => {
        e.preventDefault();
        history.back();
    };

    render() {
        let buttonText = "Submit";
        if (this.props.mode === MODE_EDIT) {
            buttonText = "Update";
        }
        if (this.state.errorMsg) {
            var error = (
                <p className="text-danger">
                    <strong>
                        An error occurred while submitting this dataset:
                    </strong>
                    &nbsp;{this.state.errorMsg.error || "Unknown error"}
                </p>
            );
        } else {
            var error = "";
        }
        return (
            <div className="form-group">
                {error}
                <button
                    onClick={this.handleSubmit}
                    type="button"
                    disabled={this.state.enabled ? "" : "disabled"}
                    className="btn btn-default btn-primary"
                >
                    {buttonText}
                </button>
                <button
                    onClick={this.handleCancel}
                    type="button"
                    className="btn btn-default"
                >
                    Cancel
                </button>
            </div>
        );
    }
}

class ClassList extends React.Component {
    static propTypes = {
        classes: PropTypes.array.isRequired,
        onClassCreate: PropTypes.func.isRequired,
        onClassEdit: PropTypes.func.isRequired,
        onClassDelete: PropTypes.func.isRequired,
    };

    render() {
        const items = [];
        this.props.classes.forEach(
            function (cls, index) {
                items.push(
                    <Class
                        key={index}
                        id={index}
                        name={cls.name}
                        description={cls.description}
                        recordingCounter={cls.recordings.length}
                        onClassEdit={this.props.onClassEdit}
                        onClassDelete={this.props.onClassDelete}
                    />
                );
            }.bind(this)
        );
        return (
            <div>
                <h4>Classes</h4>
                <div className="class-list row">
                    {items}
                    <div className="col-md-3 class">
                        <a
                            className="thumbnail add-class-link"
                            href="#"
                            onClick={this.props.onClassCreate}
                        >
                            + Add new class
                        </a>
                    </div>
                </div>
            </div>
        );
    }
}

class Class extends React.Component {
    static propTypes = {
        id: PropTypes.number.isRequired,
        name: PropTypes.string.isRequired,
        description: PropTypes.string.isRequired,
        recordingCounter: PropTypes.number.isRequired,
        onClassDelete: PropTypes.func.isRequired,
        onClassEdit: PropTypes.func.isRequired,
    };

    handleDelete = (event) => {
        event.preventDefault();
        this.props.onClassDelete(this.props.id);
    };

    handleEdit = (event) => {
        event.preventDefault();
        this.props.onClassEdit(this.props.id);
    };

    render() {
        let { name } = this.props;
        if (!name) name = <em>Unnamed class #{this.props.id + 1}</em>;
        let recordingsCounterText = `${this.props.recordingCounter.toString()} `;
        if (this.props.recordingCounter === 1)
            recordingsCounterText += "recording";
        else recordingsCounterText += "recordings";
        return (
            <div className="col-md-3 class">
                <a href="#" onClick={this.handleEdit} className="thumbnail">
                    <div className="name">{name}</div>
                    <div className="counter">{recordingsCounterText}</div>
                </a>
                <div className="controls clearfix">
                    <button
                        type="button"
                        className="close pull-right"
                        title="Remove class"
                        onClick={this.handleDelete}
                    >
                        &times;
                    </button>
                </div>
            </div>
        );
    }
}

// Classes used with SECTION_CLASS_DETAILS:

class ClassDetails extends React.Component {
    static propTypes = {
        id: PropTypes.number.isRequired,
        name: PropTypes.string.isRequired,
        description: PropTypes.string.isRequired,
        recordings: PropTypes.array.isRequired,
        datasetName: PropTypes.string.isRequired,
        onReturn: PropTypes.func.isRequired,
        onClassUpdate: PropTypes.func.isRequired,
        autoAddRecording: PropTypes.bool.isRequired,
        onAutoAddRecordingUpdate: PropTypes.func.isRequired,
    };

    handleNameUpdate = (event) => {
        const name = event.target.value;
        this.props.onClassUpdate(
            this.props.id,
            name,
            this.props.description,
            this.props.recordings
        );
    };

    handleDescriptionUpdate = (event) => {
        const description = event.target.value;
        this.props.onClassUpdate(
            this.props.id,
            this.props.name,
            description,
            this.props.recordings
        );
    };

    handleRecordingsUpdate = (recordings) => {
        this.props.onClassUpdate(
            this.props.id,
            this.props.name,
            this.props.description,
            recordings
        );
    };

    render() {
        return (
            <div className="class-details">
                <h3>
                    <a
                        href="#"
                        onClick={this.props.onReturn}
                        title="Back to dataset details"
                    >
                        {this.props.datasetName}
                    </a>
                    &nbsp;/&nbsp;
                    <input
                        type="text"
                        placeholder="Class name"
                        required="required"
                        id="class-name"
                        onChange={this.handleNameUpdate}
                        size={this.props.name.length}
                        value={this.props.name}
                    />
                </h3>
                <p>
                    <a href="#" onClick={this.props.onReturn}>
                        <strong>&larr; Back to class list</strong>
                    </a>
                </p>
                <textarea
                    placeholder="Description of this class (optional)"
                    onChange={this.handleDescriptionUpdate}
                    value={this.props.description}
                />
                <Recordings
                    recordings={this.props.recordings}
                    onRecordingsUpdate={this.handleRecordingsUpdate}
                    autoAddRecording={this.props.autoAddRecording}
                    onAutoAddRecordingUpdate={
                        this.props.onAutoAddRecordingUpdate
                    }
                />
            </div>
        );
    }
}

class Recordings extends React.Component {
    static propTypes = {
        recordings: PropTypes.array.isRequired,
        onRecordingsUpdate: PropTypes.func.isRequired,
        autoAddRecording: PropTypes.bool.isRequired,
        onAutoAddRecordingUpdate: PropTypes.func.isRequired,
    };

    handleRecordingSubmit = (mbid) => {
        const { recordings } = this.props;
        recordings.push(mbid);
        this.props.onRecordingsUpdate(recordings);
    };

    handleRecordingDelete = (mbid) => {
        const { recordings } = this.props;
        const index = recordings.indexOf(mbid);
        if (index > -1) {
            recordings.splice(index, 1);
        }
        this.props.onRecordingsUpdate(recordings);
    };

    render() {
        return (
            <div>
                <h4>Recordings</h4>
                <RecordingList
                    recordings={this.props.recordings}
                    onRecordingDelete={this.handleRecordingDelete}
                />
                <RecordingAddForm
                    recordings={this.props.recordings}
                    onRecordingSubmit={this.handleRecordingSubmit}
                    autoAddRecording={this.props.autoAddRecording}
                    onAutoAddRecordingUpdate={
                        this.props.onAutoAddRecordingUpdate
                    }
                />
            </div>
        );
    }
}

const RECORDING_MBID_RE = /^(https?:\/\/(?:beta\.)?musicbrainz\.org\/recording\/)?([0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12})/i;

recordingAddFormGetInitialState = () => {
    return {
        mbid: "",
        validUUID: false,
        duplicate: false,
        validInput: false,
    };
};

class RecordingAddForm extends React.Component {
    static propTypes = {
        recordings: PropTypes.array.isRequired,
        onRecordingSubmit: PropTypes.func.isRequired,
        autoAddRecording: PropTypes.bool.isRequired,
        onAutoAddRecordingUpdate: PropTypes.func.isRequired,
    };

    constructor(props) {
        super(props);
        this.state = recordingAddFormGetInitialState();
    }

    componentDidUpdate(prevProps, prevState, snapshot) {
        if (
            this.state.validUUID &&
            !this.state.duplicate &&
            this.props.autoAddRecording
        ) {
            this.addMbid();
        }
    }

    addMbid() {
        let mbid = RECORDING_MBID_RE.exec(this.state.mbid)[2];
        if (!mbid) {
            return;
        }
        mbid = mbid.toLowerCase();
        this.props.onRecordingSubmit(mbid);
        this.setState(recordingAddFormGetInitialState());
    }

    handleSubmit = (event) => {
        event.preventDefault();
        this.addMbid();
    };

    handleChange = (event) => {
        const mbidField = event.target.value;
        const isValidUUID = RECORDING_MBID_RE.test(mbidField);
        let isDuplicate = true;
        if (isValidUUID) {
            let mbid = RECORDING_MBID_RE.exec(mbidField)[2];
            mbid = mbid.toLowerCase();
            isDuplicate = this.props.recordings.indexOf(mbid) !== -1;
        }
        this.setState({
            mbid: mbidField,
            validUUID: isValidUUID,
            duplicate: isDuplicate,
            validInput: isValidUUID && !isDuplicate,
        });
    };

    changeAutoAddRecording = (event) => {
        this.props.onAutoAddRecordingUpdate(!this.props.autoAddRecording);
    };

    render() {
        let error = <div />;
        if (this.state.mbid.length > 0 && !this.state.validUUID) {
            error = (
                <div className="has-error small">
                    Not a valid recording MBID
                </div>
            );
        } else if (this.state.mbid.length > 0 && this.state.duplicate) {
            error = <div className="has-error small">MBID is duplicate</div>;
        }
        return (
            <form
                className="recording-add clearfix form-inline form-group-sm"
                onSubmit={this.handleSubmit}
            >
                <div
                    className={
                        this.state.validInput || this.state.mbid.length === 0
                            ? "input-group"
                            : "input-group has-error"
                    }
                >
                    <input
                        type="text"
                        className="form-control input-sm"
                        placeholder="MusicBrainz ID or URL"
                        value={this.state.mbid}
                        onChange={this.handleChange}
                    />
                    <span className="input-group-btn">
                        <button
                            disabled={this.state.validInput ? "" : "disabled"}
                            className="btn btn-default btn-sm"
                            type="submit"
                        >
                            Add recording
                        </button>
                    </span>
                </div>
                <div>
                    <span>
                        <input
                            id="autoadd-check"
                            type="checkbox"
                            checked={
                                this.props.autoAddRecording ? "checked" : ""
                            }
                            onChange={this.changeAutoAddRecording}
                        />
                        &nbsp;
                        <label htmlFor="autoadd-check">
                            Automatically add recordings
                        </label>
                    </span>
                </div>
                {error}
            </form>
        );
    }
}

class RecordingList extends React.Component {
    static propTypes = {
        recordings: PropTypes.array.isRequired,
        onRecordingDelete: PropTypes.func.isRequired,
    };

    render() {
        const items = [];
        this.props.recordings.forEach(
            function (recording) {
                items.push(
                    <Recording
                        key={recording}
                        mbid={recording}
                        onRecordingDelete={this.props.onRecordingDelete}
                    />
                );
            }.bind(this)
        );
        if (items.length > 0) {
            return (
                <table className="recordings table table-condensed table-hover">
                    <thead>
                        <tr>
                            <th>MusicBrainz ID</th>
                            <th>Recording</th>
                            <th />
                        </tr>
                    </thead>
                    <tbody>{items}</tbody>
                </table>
            );
        }
        return <p className="text-muted">No recordings.</p>;
    }
}

const RECORDING_STATUS_LOADING = "loading"; // loading info from the server
const RECORDING_STATUS_ERROR = "error"; // failed to load info about recording
const RECORDING_STATUS_LOADED = "loaded"; // info has been loaded

class Recording extends React.Component {
    static propTypes = {
        mbid: PropTypes.string.isRequired,
        onRecordingDelete: PropTypes.func.isRequired,
    };

    state = {
        status: RECORDING_STATUS_LOADING,
    };

    componentDidMount() {
        $.ajax({
            type: "GET",
            url: `/datasets/metadata/recording/${this.props.mbid}`,
            success: function (data) {
                this.setState({
                    details: data.recording,
                    status: RECORDING_STATUS_LOADED,
                });
            }.bind(this),
            error: function () {
                this.setState({
                    error: "Recording not found!",
                    status: RECORDING_STATUS_ERROR,
                });
            }.bind(this),
        });
    }

    handleDelete = (event) => {
        event.preventDefault();
        this.props.onRecordingDelete(this.props.mbid);
    };

    render() {
        let details = "";
        let rowClassName = "";
        switch (this.state.status) {
            case RECORDING_STATUS_LOADED:
                details = (
                    <a href={`/${this.props.mbid}`} target="_blank">
                        {this.state.details.title} - {this.state.details.artist}
                    </a>
                );
                rowClassName = "";
                break;
            case RECORDING_STATUS_ERROR:
                details = this.state.error;
                rowClassName = "warning";
                break;
            case RECORDING_STATUS_LOADING:
            default:
                details = <em className="text-muted">loading information</em>;
                rowClassName = "active";
                break;
        }
        return (
            <tr className={rowClassName}>
                <td className="mbid-col">{this.props.mbid}</td>
                <td className="details-col">{details}</td>
                <td className="remove-col">
                    <button
                        type="button"
                        className="close"
                        title="Remove recording"
                        onClick={this.handleDelete}
                    >
                        &times;
                    </button>
                </td>
            </tr>
        );
    }
}

if (container) ReactDOM.render(<Dataset />, container);
