import React, { Component } from "react";
import ReactDOM from "react-dom";

const CONTAINER_ELEMENT_ID = "similarity-eval";
const container = document.getElementById(CONTAINER_ELEMENT_ID);

interface SimilarityEvalProps {}

interface SimilarityEvalState {
    refMbid: any;
    refOffset: any;
    metric: string;
    metricDescription?: string;
    similarMetadata?: any;
    noSimilarityData: boolean;
}

class SimilarityEval extends Component<
    SimilarityEvalProps,
    SimilarityEvalState
> {
    constructor(props: Readonly<SimilarityEvalProps>) {
        super(props);
        this.state = {
            refMbid: container!.dataset.refMbid,
            refOffset: container!.dataset.refOffset,
            metric: container!.dataset.metric!,
            metricDescription: undefined,
            similarMetadata: null,
            noSimilarityData: false,
        };
    }

    componentDidMount = () => {
        fetch(
            `/similarity/service/similar/${this.state.metric}/${this.state.refMbid}?n=${this.state.refOffset}`
        )
            .then((response) => response.json())
            .then((result: any) => {
                this.setState({
                    similarMetadata: result.metadata,
                    metricDescription: result.metric.description,
                });
            })
            .catch((error: any) => {
                this.setState({
                    noSimilarityData: true,
                });
            });
    };

    render() {
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
                    {this.state.noSimilarityData && (
                        <p>
                            We have no similarity data for this recording, sorry
                        </p>
                    )}
                    {this.state.similarMetadata && (
                        <>
                            <h3>
                                Most similar by {this.state.metricDescription}:
                            </h3>
                            <table className="table table-striped">
                                <thead>
                                    <tr>
                                        <th>Recording</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {this.state.similarMetadata.map(
                                        (rec: any) => {
                                            return (
                                                <tr
                                                    key={`${rec.mbid}?n=${rec.submission_offset}`}
                                                >
                                                    <td>
                                                        <a
                                                            href={`/${rec.mbid}?n=${rec.submission_offset}`}
                                                            target="_blank"
                                                            rel="noreferrer"
                                                        >
                                                            {rec.artist} -{" "}
                                                            {rec.title}
                                                        </a>
                                                    </td>
                                                </tr>
                                            );
                                        }
                                    )}
                                </tbody>
                            </table>
                        </>
                    )}
                    {!this.state.similarMetadata &&
                        !this.state.noSimilarityData && (
                            <strong>Loading...</strong>
                        )}
                </div>
            </div>
        );
    }
}

if (container) ReactDOM.render(<SimilarityEval />, container);
