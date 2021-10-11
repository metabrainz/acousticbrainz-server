/*
 This is a viewer for classes in existing datasets.
 The Dataset class is the main component which is used to show the dataset
 */
import React, { Component } from "react";

const SECTION_DATASET_DETAILS = "dataset_details";
const SECTION_CLASS_DETAILS = "class_details";

// Components used with SECTION_DATASET_DETAILS:

interface ClassProps {
    id: number;
    name: string | JSX.Element;
    description: string;
    recordingCounter: number;
    onViewClass: (cls: number) => void;
}

function Class(props: ClassProps) {
    let { name } = props;
    if (!name) name = <em>Unnamed class #{props.id + 1}</em>;
    let recordingsCounterText = `${props.recordingCounter.toString()} `;
    if (props.recordingCounter === 1) {
        recordingsCounterText += "recording";
    } else {
        recordingsCounterText += "recordings";
    }
    return (
        <div className="col-md-3 class">
            <a
                href="#"
                onClick={(e) => {
                    e.preventDefault();
                    props.onViewClass(props.id);
                }}
                className="thumbnail"
            >
                <div className="name">{name}</div>
                <div className="counter">{recordingsCounterText}</div>
            </a>
        </div>
    );
}

interface ClassListProps {
    classes: any[];
    onViewClass: (cls: number) => void;
}

function ClassList(props: ClassListProps) {
    const items = props.classes.map((cls, index) => {
        return (
            <Class
                id={index}
                key={index} // eslint-disable-line react/no-array-index-key
                name={cls.name}
                description={cls.description}
                recordingCounter={cls.recordings.length}
                onViewClass={props.onViewClass}
            />
        );
    });
    return (
        <div>
            <h3>Classes</h3>
            <div className="class-list row">{items}</div>
        </div>
    );
}

// Components used with SECTION_CLASS_DETAILS:

// TODO: Turn into enum
const RECORDING_STATUS_LOADING = "loading"; // loading info from the server
const RECORDING_STATUS_ERROR = "error"; // failed to load info about recording
const RECORDING_STATUS_LOADED = "loaded"; // info has been loaded

interface RecordingProps {
    datasetId: string;
    mbid: string;
}

interface RecordingState {
    status: string;
    details?: any;
    error?: string;
}

class Recording extends Component<RecordingProps, RecordingState> {
    constructor(props: Readonly<RecordingProps>) {
        super(props);
        this.state = {
            status: RECORDING_STATUS_LOADING,
            details: undefined,
            error: undefined,
        };
    }

    componentDidMount() {
        $.ajax({
            type: "GET",
            url: `/datasets/metadata/dataset/${this.props.datasetId}/${this.props.mbid}`,
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
        let details: JSX.Element;
        let rowClassName = "";
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
                details = <em>{this.state.error}</em>;
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
            </tr>
        );
    }
}

interface RecordingListProps {
    datasetId: string;
    recordings: string[];
}

function RecordingList(props: RecordingListProps) {
    const items = props.recordings.map((recording) => (
        <Recording
            datasetId={props.datasetId}
            key={recording}
            mbid={recording}
        />
    ));
    if (items.length > 0) {
        return (
            <table className="recordings table table-condensed table-hover">
                <thead>
                    <tr>
                        <th>MusicBrainz ID</th>
                        <th>Recording</th>
                    </tr>
                </thead>
                <tbody>{items}</tbody>
            </table>
        );
    }
    return <p className="text-muted">No recordings.</p>;
}

interface ClassDetailsProps {
    datasetId: string;
    id: number;
    name: string;
    description: string;
    recordings: string[];
    datasetName: string;
    onReturn: () => void;
}

function ClassDetails(props: ClassDetailsProps) {
    return (
        <div className="class-details">
            <h3>
                <a
                    href="#"
                    onClick={props.onReturn}
                    title="Back to dataset details"
                >
                    {props.datasetName}
                </a>
                &nbsp;/&nbsp;
                {props.name}
            </h3>
            <p>
                <a href="#" onClick={props.onReturn}>
                    <strong>&larr; Back to class list</strong>
                </a>
            </p>
            <p>{props.description}</p>
            <RecordingList
                datasetId={props.datasetId}
                recordings={props.recordings}
            />
        </div>
    );
}

/*
 Dataset is the primary class in the dataset viewer. Its state contains
 dataset itself and other internal variables:
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
   - SECTION_DATASET_DETAILS (dataset info and list of classes)
   - SECTION_CLASS_DETAILS (specific class; this also requires
     active_class_index variable to be set in Dataset state)
 */

interface DatasetProps {
    datasetId: string;
}

interface DatasetState {
    active_section: any;
    active_class_index?: number;
    data: any;
}

class Dataset extends Component<DatasetProps, DatasetState> {
    constructor(props: Readonly<DatasetProps>) {
        super(props);
        this.state = {
            active_section: SECTION_DATASET_DETAILS,
            data: null,
            active_class_index: undefined,
        };
    }

    componentDidMount() {
        $.get(`/datasets/service/${this.props.datasetId}/json`, (result) => {
            this.setState({ data: result });
        });
    }

    handleViewDetails = (index: number) => {
        this.setState({
            active_section: SECTION_CLASS_DETAILS,
            active_class_index: index,
        });
    };

    handleReturn = () => {
        this.setState({
            active_section: SECTION_DATASET_DETAILS,
            active_class_index: undefined,
        });
    };

    render() {
        if (this.state.data) {
            if (this.state.active_section === SECTION_DATASET_DETAILS) {
                // TODO: Move ClassList into DatasetDetails
                return (
                    <ClassList
                        classes={this.state.data.classes}
                        onViewClass={this.handleViewDetails}
                    />
                );
            } // SECTION_CLASS_DETAILS
            if (this.state.active_class_index !== undefined) {
                const active_class =
                    this.state.data.classes[this.state.active_class_index];
                return (
                    <ClassDetails
                        datasetId={this.props.datasetId}
                        id={this.state.active_class_index}
                        name={active_class.name}
                        description={active_class.description}
                        recordings={active_class.recordings}
                        datasetName={this.state.data.name}
                        onReturn={this.handleReturn}
                    />
                );
            }
        }
        return <strong>Loading...</strong>;
    }
}

export default Dataset;
