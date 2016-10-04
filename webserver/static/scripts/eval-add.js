const $ = require("jquery");
require("selectize");

$(function() {
  $("#challenge-id").selectize({
    valueField: 'id',
    labelField: 'name',
    searchField: 'name',
    options: [],
    create: false,
    render: {
      option: function(item, escape) {
        return '<div class="challenge-suggestion">' +
            '<div class="name">' + escape(item.name) + '</div>' +
            '<div class="id">' + escape(item.id) + '</div>' +
            '</div>';
      }
    },
    load: function(query, callback) {
      if (!query.length) return callback();
      $.ajax({
        url: "/challenges/active-suggest",
        type: 'GET',
        dataType: 'json',
        data: {q: query},
        error: function() {
          callback();
        },
        success: function(result) {
          console.log(result.challenges);
          callback(result.challenges);
        }
      });
    }
  });
});
