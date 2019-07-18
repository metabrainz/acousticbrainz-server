$(function () {
    // Make the "show" text change youtube source in bottom iframe
    $('.change-youtube').click(function() {
        $('#youtube_iframe').attr('src', 'https://www.youtube.com/embed?listType=search&amp;list='
            + $(this).attr('data-youtube'))
    });

    // Evaluation of the metrics
    let feedbackCallback = function () {
        $('#feedback-request').hide();
        $('#feedback-result').show();
    };

    let history = localStorage['history'];
    if(history)
        history = JSON.parse(history);
    else
        history = [];

    let history_set = new Set(history);
    if(history_set.has(location.pathname))
        feedbackCallback();

    $('.btn-feedback').click(function () {
        let value = $(this).attr('data-value');
        $.ajax({
            method: 'POST',
            url: location.pathname + '/rate/' + value,
            success: function () {
                history.push(location.pathname);
                localStorage['history'] = JSON.stringify(history);
                feedbackCallback();
            },
            error: function () {
                console.error('Failed to submit feedback');
            }
        });
    });
});
