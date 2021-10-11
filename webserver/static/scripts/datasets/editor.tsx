/*
 This is a dataset editor. It works in two modes:
 - create (creates new dataset from scratch)
 - edit (edits existing dataset)

 The DatasetEditor class is the main entrypoint. It has 2 props:
  - mode
  - datasetId

 When mode is set to "edit", the prop "datasetId" needs to be specified. This
 attribute references existing dataset by its ID. When the DataseEditor component is
 mounted, it pulls existing dataset for editing from the server.
 */
import React, { ChangeEvent, Component, FormEvent } from "react";
import ReactDOM from "react-dom";

const MODE_CREATE = "create";
const MODE_EDIT = "edit";

const SECTION_DATASET_DETAILS = "dataset_details";
const SECTION_CLASS_DETAILS = "class_details";

// Classes used with SECTION_DATASET_DETAILS:

interface DatasetDetailsProps {
    name: string;
    description: string;
    onDetailsUpdate: (name: string, description: string) => void;
}

function DatasetDetails(props: DatasetDetailsProps) {
    return (
        <div className="dataset-details">
            <h2 className="page-title">
                Dataset&nbsp;
                <input
                    type="text"
                    placeholder="Name"
                    required
                    value={props.name}
                    size={props.name.length}
                    onChange={(e) => {
                        props.onDetailsUpdate(
                            e.target.value,
                            props.description
                        );
                    }}
                />
            </h2>
            <textarea
                placeholder="Description (optional)"
                value={props.description}
                onChange={(e) => {
                    props.onDetailsUpdate(props.name, e.target.value);
                }}
            />
        </div>
    );
}

interface DatasetControlButtonsProps {
    mode: string;
    datasetId?: string;
    data: any;
    csrfToken: string;
}

interface DatasetControlButtonsState {
    enabled: boolean;
    errorMsg?: any;
}

class DatasetControlButtons extends Component<
    DatasetControlButtonsProps,
    DatasetControlButtonsState
> {
    constructor(props: Readonly<DatasetControlButtonsProps>) {
        super(props);
        this.state = {
            enabled: true,
            errorMsg: undefined,
        };
    }

    handleSubmit = (e: any) => {
        e.preventDefault();
        this.setState({
            enabled: false,
            errorMsg: undefined,
        });
        let submitEndpoint;
        if (this.props.mode === MODE_CREATE) {
            submitEndpoint = "/datasets/service/create";
        } else {
            // MODE_EDIT
            submitEndpoint = `/datasets/service/${this.props.datasetId}/edit`;
        }
        $.ajax({
            type: "POST",
            url: submitEndpoint,
            headers: { "X-CSRFToken": this.props.csrfToken },
            data: JSON.stringify({
                id: this.props.data.id, // used only with MODE_EDIT
                name: this.props.data.name,
                description: this.props.data.description,
                classes: this.props.data.classes,
                public: this.props.data.public,
            }),
            dataType: "json",
            contentType: "application/json; charset=utf-8",
            success: (data, textStatus, jqXHR) => {
                window.location.replace(`/datasets/${data.dataset_id}`);
            },
            error: (jqXHR, textStatus, errorThrown) => {
                this.setState({
                    enabled: true,
                    errorMsg: jqXHR.responseJSON,
                });
            },
        });
    };

    render() {
        let buttonText = "Submit";
        if (this.props.mode === MODE_EDIT) {
            buttonText = "Update";
        }
        let error;
        if (this.state.errorMsg) {
            error = (
                <p className="text-danger">
                    <strong>
                        An error occurred while submitting this dataset:
                    </strong>
                    &nbsp;{this.state.errorMsg.error || "Unknown error"}
                </p>
            );
        } else {
            error = "";
        }
        return (
            <div className="form-group">
                {error}
                <button
                    onClick={this.handleSubmit}
                    type="button"
                    disabled={!this.state.enabled}
                    className="btn btn-default btn-primary"
                >
                    {buttonText}
                </button>
                <button
                    onClick={(e) => {
                        e.preventDefault();
                        history.back();
                    }}
                    type="button"
                    className="btn btn-default"
                >
                    Cancel
                </button>
            </div>
        );
    }
}

interface ClassProps {
    id: number;
    name: string | JSX.Element;
    recordingCounter: number;
    onClassDelete: (index: number) => void;
    onClassEdit: (index: number) => void;
}

function Class(props: ClassProps) {
    let { name } = props;
    if (!name) name = <em>Unnamed class #{props.id + 1}</em>;
    let recordingsCounterText = `${props.recordingCounter.toString()} `;
    if (props.recordingCounter === 1) recordingsCounterText += "recording";
    else recordingsCounterText += "recordings";
    return (
        <div className="col-md-3 class">
            <a
                href="#"
                onClick={(e) => {
                    e.preventDefault();
                    props.onClassEdit(props.id);
                }}
                className="thumbnail"
            >
                <div className="name">{name}</div>
                <div className="counter">{recordingsCounterText}</div>
            </a>
            <div className="controls clearfix">
                <button
                    type="button"
                    className="close pull-right"
                    title="Remove class"
                    onClick={(e) => {
                        e.preventDefault();
                        props.onClassDelete(props.id);
                    }}
                >
                    &times;
                </button>
            </div>
        </div>
    );
}

interface ClassListProps {
    classes: any[];
    onClassCreate: () => void;
    onClassEdit: (index: number) => void;
    onClassDelete: (index: number) => void;
}

function ClassList(props: ClassListProps) {
    const items = props.classes.map((cls: any, index: number) => {
        return (
            <Class
                key={index} // eslint-disable-line react/no-array-index-key
                id={index}
                name={cls.name}
                recordingCounter={cls.recordings.length}
                onClassEdit={props.onClassEdit}
                onClassDelete={props.onClassDelete}
            />
        );
    });
    return (
        <div>
            <h4>Classes</h4>
            <div className="class-list row">
                {items}
                <div className="col-md-3 class">
                    <a
                        className="thumbnail add-class-link"
                        href="#"
                        onClick={props.onClassCreate}
                    >
                        + Add new class
                    </a>
                </div>
            </div>
        </div>
    );
}

// Classes used with SECTION_CLASS_DETAILS:

const RECORDING_STATUS_LOADING = "loading"; // loading info from the server
const RECORDING_STATUS_ERROR = "error"; // failed to load info about recording
const RECORDING_STATUS_LOADED = "loaded"; // info has been loaded

interface RecordingProps {
    mbid: string;
    onRecordingDelete: (mbid: string) => void;
}

interface RecordingState {
    status: string;
    error?: string;
    details?: any;
}

class Recording extends Component<RecordingProps, RecordingState> {
    constructor(props: Readonly<RecordingProps>) {
        super(props);
        this.state = {
            status: RECORDING_STATUS_LOADING,
        };
    }

    componentDidMount() {
        $.ajax({
            type: "GET",
            url: `/datasets/metadata/recording/${this.props.mbid}`,
            success: (data) => {
                this.setState({
                    details: data.recording,
                    status: RECORDING_STATUS_LOADED,
                });
            },
            error: () => {
                this.setState({
                    error: "Recording not found!",
                    status: RECORDING_STATUS_ERROR,
                });
            },
        });
    }

    render() {
        let details;
        let rowClassName;
        switch (this.state.status) {
            case RECORDING_STATUS_LOADED:
                details = (
                    <a
                        href={`/${this.props.mbid}`}
                        target="_blank"
                        rel="noreferrer"
                    >
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
                        onClick={(e) => {
                            e.preventDefault();
                            this.props.onRecordingDelete(this.props.mbid);
                        }}
                    >
                        &times;
                    </button>
                </td>
            </tr>
        );
    }
}

interface RecordingListProps {
    recordings: any[];
    onRecordingDelete: (mbid: string) => void;
}

function RecordingList(props: RecordingListProps) {
    const items = props.recordings.map((recording) => {
        return (
            <Recording
                key={recording}
                mbid={recording}
                onRecordingDelete={props.onRecordingDelete}
            />
        );
    });
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

const RECORDING_MBID_RE =
    /^(https?:\/\/(?:beta\.)?musicbrainz\.org\/recording\/)?([0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12})/i;

interface RecordingAddFormProps {
    recordings: any[];
    onRecordingSubmit: (mbid: string) => void;
    autoAddRecordings: boolean;
    onAutoAddRecordingUpdate: (autoAddRecording: boolean) => void;
}

interface RecordingAddFormState {
    mbid: string;
    validUUID: boolean;
    duplicate: boolean;
    validInput: boolean;
}

class RecordingAddForm extends Component<
    RecordingAddFormProps,
    RecordingAddFormState
> {
    constructor(props: Readonly<RecordingAddFormProps>) {
        super(props);
        this.state = {
            mbid: "",
            validUUID: false,
            duplicate: false,
            validInput: false,
        };
    }

    componentDidUpdate(
        prevProps: Readonly<RecordingAddFormProps>,
        prevState: Readonly<RecordingAddFormState>
    ) {
        if (
            this.state.validUUID &&
            !this.state.duplicate &&
            this.props.autoAddRecordings
        ) {
            this.addMbid();
        }
    }

    handleSubmit = (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        this.addMbid();
    };

    handleChange = (event: ChangeEvent<HTMLInputElement>) => {
        const mbidField = event.target.value;
        const isValidUUID = RECORDING_MBID_RE.test(mbidField);
        let isDuplicate = true;
        if (isValidUUID) {
            let mbid = RECORDING_MBID_RE.exec(mbidField)![2];
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

    addMbid() {
        let mbid = RECORDING_MBID_RE.exec(this.state.mbid)![2];
        if (!mbid) {
            return;
        }
        mbid = mbid.toLowerCase();
        this.props.onRecordingSubmit(mbid);
        this.setState({
            mbid: "",
            validUUID: false,
            duplicate: false,
            validInput: false,
        });
    }

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
                            disabled={!this.state.validInput}
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
                            checked={this.props.autoAddRecordings}
                            onChange={() => {
                                this.props.onAutoAddRecordingUpdate(
                                    !this.props.autoAddRecordings
                                );
                            }}
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

interface RecordingsProps {
    recordings: any[];
    onRecordingsUpdate: (recordings: any) => void;
    autoAddRecordings: boolean;
    onAutoAddRecordingUpdate: (autoAddRecording: boolean) => void;
}

class Recordings extends Component<RecordingsProps> {
    handleRecordingSubmit = (mbid: string) => {
        const { recordings } = this.props;
        recordings.push(mbid);
        this.props.onRecordingsUpdate(recordings);
    };

    handleRecordingDelete = (mbid: string) => {
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
                    autoAddRecordings={this.props.autoAddRecordings}
                    onAutoAddRecordingUpdate={
                        this.props.onAutoAddRecordingUpdate
                    }
                />
            </div>
        );
    }
}

interface ClassDetailsProps {
    id: number;
    name: string;
    description: string;
    recordings: any[];
    datasetName: string;
    onReturn: () => void;
    onClassUpdate: (
        id: number,
        name: string,
        description: string,
        recordings: any[]
    ) => void;
    autoAddRecording: boolean;
    onAutoAddRecordingUpdate: (autoAddRecording: boolean) => void;
}

class ClassDetails extends Component<ClassDetailsProps> {
    handleNameUpdate = (event: ChangeEvent<HTMLInputElement>) => {
        const name = event.target.value;
        this.props.onClassUpdate(
            this.props.id,
            name,
            this.props.description,
            this.props.recordings
        );
    };

    handleDescriptionUpdate = (event: ChangeEvent<HTMLTextAreaElement>) => {
        const description = event.target.value;
        this.props.onClassUpdate(
            this.props.id,
            this.props.name,
            description,
            this.props.recordings
        );
    };

    handleRecordingsUpdate = (recordings: any) => {
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
                        required
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
                    autoAddRecordings={this.props.autoAddRecording}
                    onAutoAddRecordingUpdate={
                        this.props.onAutoAddRecordingUpdate
                    }
                />
            </div>
        );
    }
}

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
interface DatasetEditorState {
    autoAddRecording: boolean;
    active_section: string;
    active_class_index?: number;
    data?: any;
}

interface DatasetEditorProps {
    mode: string;
    datasetId?: string;
    csrfToken: string;
}

class DatasetEditor extends Component<DatasetEditorProps, DatasetEditorState> {
    constructor(props: Readonly<DatasetEditorProps>) {
        super(props);
        this.state = {
            autoAddRecording: false,
            active_section: SECTION_DATASET_DETAILS,
            data: undefined,
        };
    }

    componentDidMount() {
        // This function is invoked when Dataset component is originally
        // mounted. Here we need to check what mode dataset editor is in, and
        // pull data from the server if mode is MODE_EDIT.
        if (this.props.mode === MODE_EDIT) {
            $.get(
                `/datasets/service/${this.props.datasetId}/json`,
                (result) => {
                    this.setState({ data: result });
                }
            );
        } else {
            if (this.props.mode !== MODE_CREATE) {
                console.warn(
                    "Unknown dataset editor mode! Using default: MODE_CREATE."
                );
            }
            this.setState({
                data: {
                    name: "",
                    description: "",
                    classes: [],
                    public: true,
                },
            });
        }
    }

    handleDetailsUpdate = (name: string, description: string) => {
        this.setState((state) => {
            const nextStateData = { ...state.data };
            nextStateData.name = name;
            nextStateData.description = description;
            return { data: nextStateData };
        });
    };

    handlePrivacyUpdate = (event: any) => {
        this.setState((state) => {
            const nextStateData = { ...state.data };
            nextStateData.public = event.target.checked;
            return { data: nextStateData };
        });
    };

    handleReturn = () => {
        this.setState({
            active_section: SECTION_DATASET_DETAILS,
            active_class_index: undefined,
        });
    };

    handleClassCreate = () => {
        this.setState((state) => {
            const nextStateData = { ...state.data };
            nextStateData.classes.push({
                name: "",
                description: "",
                recordings: [],
            });
            return { data: nextStateData };
        });
    };

    handleClassEdit = (index: number) => {
        this.setState({
            active_section: SECTION_CLASS_DETAILS,
            active_class_index: index,
        });
    };

    handleClassDelete = (index: number) => {
        const { data } = this.state;
        data.classes.splice(index, 1);
        this.setState({ data });
    };

    handleClassUpdate = (
        index: number,
        name: string,
        description: string,
        recordings: any
    ) => {
        const { data } = this.state;
        data.classes[index].name = name;
        data.classes[index].description = description;
        data.classes[index].recordings = recordings;
        this.setState({ data });
    };

    handleAutoAddRecordingUpdate = (autoAddRecording: boolean) => {
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
                            mode={this.props.mode}
                            datasetId={this.props.datasetId}
                            data={this.state.data}
                            csrfToken={this.props.csrfToken}
                        />
                    </div>
                );
            } // SECTION_CLASS_DETAILS
            if (this.state.active_class_index !== undefined) {
                const active_class =
                    this.state.data.classes[this.state.active_class_index];
                return (
                    <ClassDetails
                        id={this.state.active_class_index}
                        name={active_class.name}
                        description={active_class.description}
                        recordings={active_class.recordings}
                        datasetName={this.state.data.name}
                        autoAddRecording={this.state.autoAddRecording}
                        onAutoAddRecordingUpdate={
                            this.handleAutoAddRecordingUpdate
                        }
                        onReturn={this.handleReturn}
                        onClassUpdate={this.handleClassUpdate}
                    />
                );
            }
        }
        return <strong>Loading...</strong>;
    }
}

export default DatasetEditor;
