$(function () {
    // Make the "show" text change youtube source in bottom iframe
    $('.change-youtube').click(function() {
        $('#youtube_iframe').attr('src', 'https://www.youtube.com/embed?listType=search&amp;list='
            + $(this).attr('data-youtube'))
    });

    // Evaluation of the metrics
    let feedbackCallback = function () {
        $('.feedback-request').hide();
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

    $('form').submit(function (e) {
        e.preventDefault();
        $.ajax({
            method: 'POST',
            url: location.pathname + '/eval',
            data: JSON.stringify({
                form: $('form').serialize(),
                metadata: metadata
            }),
            contentType: 'application/json',
            success: function () {
                history.push(location.pathname);
                localStorage['history'] = JSON.stringify(history);
                feedbackCallback();
            },
            error: function () {
                console.log(error)
                console.error('Failed to submit feedback.');
            }
        });

        $.ajaxSetup({
            beforeSend: function(xhr, settings) {
                if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
                    xhr.setRequestHeader("X-CSRFToken", csrftoken)
                }
            }
        });
    });
});
