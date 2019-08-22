import React from "react"

function EvalRecording(props) {
    const formRecording = props.form[props.rec.lowlevel_id]
    return (
        <tr>
            <td>
                <a href={`/${props.rec.mbid}?n=${props.rec.submission_offset}`} target="_blank">{props.rec.artist} - {props.rec.title}</a>
                <br/>
                {
                    props.rec.youtube_query !== props.similarYoutubeQuery ?
                    <a href="javascript:;" onClick={() => props.handleYoutubeChange(props.rec.youtube_query)}>(show YouTube)</a> :
                    null
                }
            </td>
            <td className="feedback-request" hidden={props.hideForm}>
                <select data-lowlevel={props.rec.lowlevel_id} 
                        name="feedback"
                        value={formRecording["feedback"]}
                        onChange={props.handleChange}>
                    <option value="">Select</option>
                    <option value="more similar">More Similar</option>
                    <option value="accurate">Accurate</option>
                    <option value="less similar">Less Similar</option>
                </select>
            </td>
            <td className="feedback-request" hidden={props.hideForm}>
                <textarea name="suggestion"
                          maxLength="100"
                          style={{position: 'relative'}}
                          data-lowlevel={props.rec.lowlevel_id}
                          value={formRecording["suggestion"]}
                          onChange={props.handleChange} />
            </td>
        </tr>
    )
}

export default EvalRecording