const $ = require("jquery");
const React = require('react');
const ReactDOM = require('react-dom');

const STATE_NOT_SUBMITTED = "not_submitted";
const STATE_SUBMITTING = "submitting";
const STATE_SUCCESS = "success";
const STATE_FAILURE = "failure";


var FeedbackCollector = React.createClass({
  propTypes: {
    HLModelRowID: React.PropTypes.number.isRequired
  },
  getInitialState: function () {
    return {
      submission_state: STATE_NOT_SUBMITTED,
    };
  },
  handleSubmitCorrect: function (event) {
    event.preventDefault();
    this.handleSubmit(true);
  },
  handleSubmitIncorrect: function (event) {
    event.preventDefault();
    this.handleSubmit(false);
  },
  handleSubmit: function(is_correct) {
    this.setState({submission_state: STATE_SUBMITTING});
    var so = this;
    $.ajax({
      type: "POST",
      url: "/feedback",
      data: JSON.stringify({
        'row_id': this.props.HLModelRowID,
        'is_correct': is_correct,
      }),
      dataType: "json",
      contentType: "application/json; charset=utf-8",
      success: function (data, textStatus, jqXHR) {
        console.debug("Feedback submitted!");
        so.setState({submission_state: STATE_SUCCESS});
      },
      error: function (jqXHR, textStatus, errorThrown) {
        console.log("Failed to submit feedback!", jqXHR, textStatus);
        so.setState({submission_state: STATE_FAILURE});
      }
    });
  },
  render: function () {
    if (this.state.submission_state == STATE_NOT_SUBMITTED) {
      return <div>
        <span className="text-muted">This result is...</span>&nbsp;
        <a href="#" onClick={this.handleSubmitCorrect} className="btn btn-xs btn-success">Correct</a>
        <a href="#" onClick={this.handleSubmitIncorrect} className="btn btn-xs btn-danger">Incorrect</a>
      </div>;
    } else if (this.state.submission_state == STATE_SUBMITTING) {
      return <div className="text-muted"><em>Submitting your feedback...</em></div>
    } else if (this.state.submission_state == STATE_SUCCESS) {
      return <div className="text-muted"><em>Thanks for your feedback!</em></div>
    } else if (this.state.submission_state == STATE_FAILURE) {
      return <div className="text-muted text-warning"><em>Failed to submit feedback.</em></div>
    }
  }
});


const FEEDBACK_CONTAINER_ID_PREFIX = "feedback-";
$('[id^='+ FEEDBACK_CONTAINER_ID_PREFIX + ']').toArray().forEach(function (container) {
  ReactDOM.render(
      <FeedbackCollector HLModelRowID={parseInt(container.id.substring(FEEDBACK_CONTAINER_ID_PREFIX.length), 10)}/>,
      container
  );
});
