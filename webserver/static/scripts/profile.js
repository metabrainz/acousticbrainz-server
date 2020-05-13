const $ = require("jquery");

$(document).ready(function () {
    const apiKey = $("#api-key");
    if (apiKey) {
        // Only when key is displayed (user is viewing their own page)

        // Not showing confirmation dialog if there's no active key (key value is not displayed).
        let ignoreConfirmation = apiKey.css("display") === "none";

        $("#btn-generate-api-key").click(function () {
            if (
                ignoreConfirmation ||
                confirm(
                    "Are you sure you want to generate new API key?\n" +
                        "Current key will be revoked!"
                )
            ) {
                $.ajax({
                    type: "POST",
                    url: "/user/generate-api-key",
                    success(data) {
                        apiKey.html(data.key);
                        apiKey.show();
                        ignoreConfirmation = false;
                    },
                    error(jqXHR, textStatus, errorThrown) {
                        let msg = "Failed to generate new API key!";
                        if (jqXHR.status == 429) {
                            msg += `\n${JSON.parse(jqXHR.responseText).error}`;
                        }
                        alert(msg);
                    },
                });
            }
        });
    }
});
