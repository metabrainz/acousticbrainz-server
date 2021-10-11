import React, { Component } from "react";
import ReactDOM from "react-dom";

const EvalRecording = require("./eval-recording.tsx");

const CONTAINER_ELEMENT_ID = "similarity-eval";
const container = document.getElementById(CONTAINER_ELEMENT_ID);

interface SimilarityEvalProps {}

interface SimilarityEvalState {
    refMbid: any;
    refOffset: any;
    formData: any;
    similarYoutubeQuery: string;
    metric: string;
    metricDescription?: string;
    metricCategory?: string;
    hideForm: boolean;
    similarMetadata: any;
    errorMsg: any;
}

class SimilarityEval extends Component<
    SimilarityEvalProps,
    SimilarityEvalState
> {
    private _isMounted: boolean;
    private _metadataLoaded: boolean;
    private readonly _initFormData: any;

    constructor(props: Readonly<SimilarityEvalProps>) {
        super(props);
        this._isMounted = false;
        this._metadataLoaded = false;
        this._initFormData = {};
        this.state = {
            refMbid: container!.dataset.refMbid,
            refOffset: container!.dataset.refOffset,
            metric: container!.dataset.metric!,
            metricDescription: undefined,
            metricCategory: undefined,
            hideForm: false,
            similarMetadata: null,
            errorMsg: null,
            formData: {},
            similarYoutubeQuery: "",
        };
    }

    componentDidMount = () => {
        this._isMounted = true;
        $.get(
            `/similarity/service/similar/${this.state.metric}/${this.state.refMbid}?n=${this.state.refOffset}`,
            (result: any) => {
                if (this._isMounted) {
                    result.metadata.forEach((rec: any) => {
                        this._initFormData[rec.lowlevel_id] = {
                            feedback: "",
                            suggestion: "",
                        };
                    });
                    this.setState({
                        similarMetadata: result.metadata,
                        similarYoutubeQuery: result.metadata[0].youtube_query,
                        metricDescription: result.metric.description,
                        metricCategory: result.metric.category,
                        formData: this._initFormData,
                        hideForm: result.submitted,
                    });
                }
            }
        );
        this._metadataLoaded = true;
    };

    componentWillUnmount() {
        this._isMounted = false;
    }

    handleChange = (event: any) => {
        this.setState((state) => {
            const formData = { ...state.formData };
            const item = {
                ...formData[event.currentTarget.getAttribute("data-lowlevel")],
            };
            item[event.target.name] = event.target.value;
            formData[event.currentTarget.getAttribute("data-lowlevel")] = item;
            return { formData };
        });
    };

    handleYoutubeChange = (query: string) => {
        this.setState({
            similarYoutubeQuery: query,
        });
    };

    handleSubmit = (event: any) => {
        event.preventDefault();
        this.setState({
            errorMsg: null,
        });
        if (
            JSON.stringify(this.state.formData) !==
            JSON.stringify(this._initFormData)
        ) {
            const so = this;
            $.ajax({
                method: "POST",
                url: `/similarity/service/evaluate/${this.state.metric}/${this.state.refMbid}?n=${this.state.refOffset}`,
                data: JSON.stringify({
                    form: this.state.formData,
                    metadata: this.state.similarMetadata,
                }),
                contentType: "application/json",
                success() {
                    so.setState({ hideForm: true });
                    console.log("success");
                },
                error(error: any) {
                    so.setState({
                        errorMsg: error.responseJSON,
                    });
                    console.log(error);
                    console.error("Failed to submit feedback.");
                },
            });
        } else {
            this.setState({
                errorMsg: {
                    error: "A rating or suggestion must be given to at least one similar recording!",
                },
            });
        }
    };

    render() {
        if (this._metadataLoaded) {
            const similarRecordings = this.state.similarMetadata.map(
                (rec: any) => (
                    <EvalRecording
                        key={`${rec.recording_mid}-${rec.offset}`}
                        rec={rec}
                        form={this.state.formData}
                        hideForm={this.state.hideForm}
                        handleChange={this.handleChange}
                        handleYoutubeChange={this.handleYoutubeChange}
                        similarYoutubeQuery={this.state.similarYoutubeQuery}
                    />
                )
            );
            let error;
            if (this.state.errorMsg) {
                error = (
                    <p className="text-danger">
                        <strong>
                            An error occurred while submitting the feedback:
                        </strong>
                        &nbsp;{this.state.errorMsg.error || "Unknown error"}
                    </p>
                );
            } else {
                error = "";
            }
            return (
                <div className="row">
                    <div className="col-md-8">
                        <div>
                            Back to{" "}
                            <a
                                href={`/similarity/${this.state.refMbid}?n=${this.state.refOffset}`}
                            >
                                metrics
                            </a>{" "}
                            /
                            <a
                                href={`/${this.state.refMbid}?n=${this.state.refOffset}`}
                            >
                                {" "}
                                summary
                            </a>
                        </div>
                        <h3>Most similar by {this.state.metricDescription}:</h3>
                        <p
                            className="feedback-request"
                            hidden={this.state.hideForm}
                        >
                            Please give us feedback - in terms of{" "}
                            <strong>{this.state.metricCategory}</strong>, how
                            similar are the result tracks to original one?
                        </p>

                        <form id="feedback-select" onSubmit={this.handleSubmit}>
                            <table className="table table-striped">
                                <thead>
                                    <tr>
                                        <th>Recording</th>
                                        <th
                                            className="feedback-request"
                                            hidden={this.state.hideForm}
                                        >
                                            Feedback
                                        </th>
                                        <th
                                            className="feedback-request"
                                            hidden={this.state.hideForm}
                                        >
                                            Suggestion
                                        </th>
                                    </tr>
                                </thead>
                                <tbody>{similarRecordings}</tbody>
                            </table>
                            {error}
                            {!this.state.hideForm ? (
                                <button
                                    className="btn btn-default btn-primary btn-feedback"
                                    type="submit"
                                >
                                    Submit Feedback
                                </button>
                            ) : (
                                <></>
                            )}
                        </form>
                    </div>
                </div>
            );
        }
        return <strong>Loading...</strong>;
    }
}

if (container) ReactDOM.render(<SimilarityEval />, container);
