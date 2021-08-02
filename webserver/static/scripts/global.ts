let glo;
if (typeof global === "undefined") {
    glo = window;
} else {
    glo = global;
}

export default glo;
