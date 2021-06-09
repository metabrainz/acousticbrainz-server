const PropTypes = require("prop-types");
/*
 This is a viewer for classes in existing datasets.

 Attribute "data-dataset-id" which references existing dataset by its ID need
 to be specified on container element. When Dataset component is mounted, it
 fetches existing dataset from the server.
 */
const React = require("react");
const ReactDOM = require("react-dom");

const CONTAINER_ELEMENT_ID = "dataset-class-viewer";
const container = document.getElementById(CONTAINER_ELEMENT_ID);

const SECTION_DATASET_DETAILS = "dataset_details";
const SECTION_CLASS_DETAILS = "class_details";

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
class Dataset extends React.Component {
    state = {
        active_section: SECTION_DATASET_DETAILS,
        data: null,
    };

    componentDidMount() {
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
            `/datasets/service/${container.dataset.datasetId}/json`,
            function (result) {
                this.setState({ data: result });
            }.bind(this)
        );
    }

    handleViewDetails = (index) => {
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
            if (this.state.active_section == SECTION_DATASET_DETAILS) {
                // TODO: Move ClassList into DatasetDetails
                return (
                    <ClassList
                        classes={this.state.data.classes}
                        onViewClass={this.handleViewDetails}
                    />
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
                    onReturn={this.handleReturn}
                />
            );
        }
        return <strong>Loading...</strong>;
    }
}

// Classes used with SECTION_DATASET_DETAILS:

class ClassList extends React.Component {
    static propTypes = {
        classes: PropTypes.array.isRequired,
        onViewClass: PropTypes.func.isRequired,
    };

    render() {
        const items = [];
        this.props.classes.forEach(
            function (cls, index) {
                items.push(
                    <Class
                        id={index}
                        key={index}
                        name={cls.name}
                        description={cls.description}
                        recordingCounter={cls.recordings.length}
                        onViewClass={this.props.onViewClass}
                    />
                );
            }.bind(this)
        );
        return (
            <div>
                <h3>Classes</h3>
                <div className="class-list row">{items}</div>
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
        onViewClass: PropTypes.func.isRequired,
    };

    handleViewDetails = (event) => {
        event.preventDefault();
        this.props.onViewClass(this.props.id);
    };

    render() {
        let { name } = this.props;
        if (!name) name = <em>Unnamed class #{this.props.id + 1}</em>;
        let recordingsCounterText = `${this.props.recordingCounter.toString()} `;
        if (this.props.recordingCounter == 1)
            recordingsCounterText += "recording";
        else recordingsCounterText += "recordings";
        return (
            <div className="col-md-3 class">
                <a
                    href="#"
                    onClick={this.handleViewDetails}
                    className="thumbnail"
                >
                    <div className="name">{name}</div>
                    <div className="counter">{recordingsCounterText}</div>
                </a>
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
                    {this.props.name}
                </h3>
                <p>
                    <a href="#" onClick={this.props.onReturn}>
                        <strong>&larr; Back to class list</strong>
                    </a>
                </p>
                <p>{this.props.description}</p>
                <RecordingList recordings={this.props.recordings} />
            </div>
        );
    }
}

class RecordingList extends React.Component {
    static propTypes = {
        recordings: PropTypes.array.isRequired,
    };

    render() {
        const items = [];
        this.props.recordings.forEach(function (recording) {
            items.push(<Recording key={recording} mbid={recording} />);
        });
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
}

const RECORDING_STATUS_LOADING = "loading"; // loading info from the server
const RECORDING_STATUS_ERROR = "error"; // failed to load info about recording
const RECORDING_STATUS_LOADED = "loaded"; // info has been loaded

class Recording extends React.Component {
    static propTypes = {
        mbid: PropTypes.string.isRequired,
    };

    state = {
        status: RECORDING_STATUS_LOADING,
    };

    componentDidMount() {
        $.ajax({
            type: "GET",
            url: `/datasets/metadata/dataset/${container.dataset.datasetId}/${this.props.mbid}`,
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
            </tr>
        );
    }
}

if (container) ReactDOM.render(<Dataset />, container);
