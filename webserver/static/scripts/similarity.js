$(function () {
    $('.change-youtube').each(function () {
        $(this).click(function() {
            $('#youtube_iframe').attr('src', 'https://www.youtube.com/embed?listType=search&amp;list='
                + $(this).attr('data-youtube'))
        });
    })

});

