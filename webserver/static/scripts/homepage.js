$(function () {
    const last_collected = $("#last_collected");
    const lc_time = last_collected.data("timestamp");
    if (lc_time > 0) {
        // lc_time of 0 means never
        const d = new Date(lc_time);
        // Date.getMonth is 0-indexed, so if we use it to construct a month string, add 1
        const collected_str = `${d.getFullYear()}-${`0${
            d.getMonth() + 1
        }`.slice(-2)}-${`0${d.getDate()}`.slice(-2)} ${`0${d.getHours()}`.slice(
            -2
        )}:${`0${d.getMinutes()}`.slice(-2)}`;
        last_collected.html(collected_str);
    }
});
