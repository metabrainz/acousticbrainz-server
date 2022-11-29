const hljs = require("highlight.js/lib/core");
hljs.registerLanguage("json", require("highlight.js/lib/languages/json"));

hljs.HighlightJS = hljs;
hljs.default = hljs;

// @ts-ignore
(global ?? window).hljs = hljs;
