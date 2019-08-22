import React, {Component} from "react"
import ReactDOM from "react-dom"
import EvalRecording from "./eval-recording"

var CONTAINER_ELEMENT_ID = "similarity-eval";
var container = document.getElementById(CONTAINER_ELEMENT_ID);

// pass ref_metadata, metric
// make request to python view function to get similar recordings and metadata on componentDidMount
// set state with similar recordings 
// render form with all similar recordings
// update state whenever form is altered
// ajax request to submit form
// hide form when submission is made
// check if current user has already made a submission, if they do then do not display form

class SimilarityEval extends Component {
    constructor() {
        super()
        this._isMounted = false
        this._metadataLoaded = false
        this._initFormData = {}
        this.state = {
            refMbid: container.dataset.refMbid,
            refOffset: container.dataset.refOffset,
            refYoutubeQuery: container.dataset.refYoutubeQuery,
            metric: container.dataset.metric,
            hideForm: false,
            similarMetadata: null,
            errorMsg: null
        }
        this.handleChange = this.handleChange.bind(this)
        this.handleYoutubeChange = this.handleYoutubeChange.bind(this)
        this.handleSubmit = this.handleSubmit.bind(this)
    }

    componentDidMount() {
        this._isMounted = true
        var so = this
        $.get(`/similarity/service/${this.state.refMbid}/${this.state.metric}?n=${this.state.refOffset}`, function(result) {
            if (this._isMounted) {
                result.metadata.forEach(function(rec) {
                    so._initFormData[rec.lowlevel_id] = {"feedback": "", "suggestion": ""}
                })
                this.setState({
                    similarMetadata: result.metadata,
                    similarYoutubeQuery: result.metadata[0].youtube_query,
                    metricDescription: result.metric.description,
                    metricCategory: result.metric.category,
                    formData: so._initFormData,
                    hideForm: result.submitted
                }); 
            }
        }.bind(this));
        this._metadataLoaded = true
    }

    componentWillUnmount() {
        this._isMounted = false
    }

    handleChange(event) {
        let formData = {...this.state.formData}
        let item = {...formData[event.currentTarget.getAttribute('data-lowlevel')]}
        item[event.target.name] = event.target.value
        formData[event.currentTarget.getAttribute('data-lowlevel')] = item
        this.setState({formData})
    }

    handleYoutubeChange(query) {
        this.setState({
            similarYoutubeQuery: query
        })
    }

    handleSubmit(event) {
        event.preventDefault()
        this.setState({
            errorMsg: null
        })
        if (JSON.stringify(this.state.formData) !== JSON.stringify(this._initFormData)) {
            var so = this
            $.ajax({
                method: 'POST',
                url: `/similarity/service/${this.state.refMbid}/${this.state.metric}/evaluate?n=${this.state.refOffset}`,
                data: JSON.stringify({
                    form: this.state.formData,
                    metadata: this.state.similarMetadata
                }),
                contentType: 'application/json',
                success: function () {

                    so.setState({hideForm: true})
                    console.log("success")
                },
                error: function (error) {
                    so.setState({
                        errorMsg: error.responseJSON
                    });
                    console.log(error);
                    console.error('Failed to submit feedback.');
                }
            });
        } else {
            this.setState({
                errorMsg: {error: "A rating or suggestion must be given to at least one similar recording!"}
            })
        }
    }

    render() {
        if (this._metadataLoaded) {
            const similarRecordings = this.state.similarMetadata.map(
                rec => <EvalRecording key={rec.lowlevelId} 
                                      rec={rec}
                                      form={this.state.formData}
                                      hideForm={this.state.hideForm}
                                      handleChange={this.handleChange}
                                      handleYoutubeChange={this.handleYoutubeChange}
                                      similarYoutubeQuery={this.state.similarYoutubeQuery}/>)
            if (this.state.errorMsg) {
                var error = <p className='text-danger'>
                                <strong>An error occurred while submitting the feedback:</strong>
                                &nbsp;{ this.state.errorMsg.error ||  "Unknown error" }
                            </p>
            } else {
                var error = ''
            }
            return (
                <div className="row">
                    <div className="col-md-8">
                        <div>
                            Back to <a href={`/similarity/${this.state.refMbid}?n=${this.state.refOffset}`}>metrics</a> /
                            <a href={`/${this.state.refMbid}?n=${this.state.refOffset}`}> summary</a>
                        </div>
                        <h3>Most similar by { this.state.metricDescription }:</h3>
                        <p className="feedback-request" hidden={this.state.hideForm}>
                            Please give us feedback - in terms of <strong>{this.state.metricCategory}</strong>, 
                            how similar are the result tracks to original one?
                        </p>

                        <form id="feedback-select" onSubmit={this.handleSubmit}>
                            <table className="table table-striped">
                                <thead>
                                <tr>
                                    <th>Recording</th>
                                    <th className="feedback-request" hidden={this.state.hideForm}>Feedback</th>
                                    <th className="feedback-request" hidden={this.state.hideForm}>Suggestion</th>
                                </tr>
                                </thead>
                                <tbody>
                                    {similarRecordings}
                                </tbody>
                            </table>
                            {error}
                            {
                                this.state.hideForm ? 
                                <div>
                                    <p><strong>Thank you for your feedback!</strong></p>
                                </div> :
                                <button className="btn btn-default btn-primary btn-feedback"
                                        type="submit">Submit Feedback
                                </button>
                            }
                        </form>
                    </div>

                    <div className="col-md-4">
                        <iframe src={`https://www.youtube.com/embed?listType=search&amp;list=${this.state.refYoutubeQuery}`}
                                width="100%" height="260" frameBorder="0" allowFullScreen></iframe>
                        <iframe src={`https://www.youtube.com/embed?listType=search&amp;list=${this.state.similarYoutubeQuery}`}
                            id="youtube_iframe" width="100%" height="260" frameBorder="0" allowFullScreen></iframe>
                    </div>
                </div>
            )
        } else {
            return (<strong>Loading...</strong>);
        }
    }
}

if (container) ReactDOM.render(<SimilarityEval />, container)
