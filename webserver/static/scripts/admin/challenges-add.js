const $ = require("jquery");
require("selectize");

$(function () {

  $("#input-classes").selectize({
    delimiter: ',',
    persist: false,
    create: function (input) {
      return {
        value: input,
        text: input
      }
    }
  });

  $("#input-val-dataset").selectize({
    valueField: 'id',
    labelField: 'name',
    searchField: 'name',
    options: [],
    create: false,
    render: {
      option: function(item, escape) {
        return '<div class="dataset-suggestion">' +
            '<div class="name">' + escape(item.name) + '</div>' +
            '<div class="id">' + escape(item.id) + '</div>' +
            '</div>';
      }
    },
    load: function(query, callback) {
      if (!query.length) return callback();
      $.ajax({
        url: "/datasets/suggest",
        type: 'GET',
        dataType: 'json',
        data: {q: query},
        error: function() {
          callback();
        },
        success: function(result) {
          console.log(result.datasets);
          callback(result.datasets);
        }
      });
    }
  });

});
