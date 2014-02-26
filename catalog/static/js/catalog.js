function groupify(a, n) {
    var len = a.length,out = [], i = 0;
    while (i < len) {
        var size = Math.ceil((len - i) / n--);
        out.push(a.slice(i, i += size));
    }
    return out;
}


function ResultItem(searchResult) {
   author = ko.observableArray(searchResult['author']);
   coverURL = ko.observable(searchResult['coverURL']);
   instanceDetail = ko.observable(searchResult['instanceDetail']);
   instanceLocation = ko.observable(searchResult['instanceLocation']);
   show = ko.observable(searchResult['show']);
   title = ko.observable(searchResult['title']);
   topics = ko.observable(searchResult['topics']);
   workURL = ko.observable(searchResult['workURL']);
}

function CatalogViewModel() {
  self = this;
  self.contextHeading = ko.observable("Default Content Heading");
  self.errorMessage = ko.observable();
  self.pageNumber = ko.observable(1);
  self.activeNext = ko.observable(true);
  self.activePrevious = ko.observable(true);
  self.searchChoices = ko.observableArray([
   { name: "Keyword", action: "kwSearch" },
   { name: "Author", action: "auSearch" },
   { name: "Title", action: "tSearch" },
   { name: "Journal Title", action: "jtSearch" },
   { name: "LC Subject", action: "lcSearch" },
   { name: "Medical Subject", action: "medSearch" },
   { name: "Children's Subject", action: "NoneSearch" },
   { name: "LC Call Number", action: "lccnSearch" },
   { name: "Gov Doc Number", action: "govSearch" },
   { name: "ISSN/ISBN", action: "isSearch" },
   { name: "Dewey Call Number", action: "dwSearch" },
   { name: "Medical Call Number", action: "medcSearch" },
   { name: "OCLC Number", action: "oclcSearch" }]);

  // Support for Twitter's typeahead.js
  self.catalogEntities = new Bloodhound({
   datumTokenizer: function(d) { return Bloodhound.tokenizers.whitespace(d.value); },
   queryTokenizer: Bloodhound.tokenizers.whitespace,
   remote: 'suggest?q=%QUERY',
//   filter: function(response) { alert("Results are " + response['results']);
//                                return $.map(response['results'], function(row) { return row['value']; }); },
   prefetch: 'suggest?prefetch=alpha'
  });

  self.catalogEntities.initialize();

  $('.typeahead').typeahead(null, {
    displayKey: 'value',
    source: self.catalogEntities.ttAdapter()
   });

 
  
  self.resultPaneSize = ko.observable("col-md-8");

  self.resultStartSlice = ko.observable(1);
  self.resultEndSlice = ko.observable(4);
  self.resultSize = ko.observable(4);

  self.showFilters = ko.observable(true);
  self.showResults = ko.observable(false);

  self.searchQuery = ko.observable();
  self.showError = ko.observable(false);
 

  // Handlers for Search

  self.displayResultView = function() {
	$.map($('.result-div'), function(n ,i) {
	  if(!self.inViewPoint(parseInt(i))) {
	    $(n).css('display', 'none');
	  } else {
	    $(n).css('display', 'block');
	  }
	});
 }
  
  self.inViewPoint = function(index) {
    var index1 = parseInt(index) + 1;
    if(index1 <= self.resultEndSlice()) { 
      if(index1 >= self.resultStartSlice()) {
        return true;
      }
    }
    return false;  
  }

  self.searchResults = ko.observableArray();
  self.searchSlides = ko.observableArray(); 
  self.shardSize = ko.observable(8);
  self.newSearch = function() {
  self.pageNumber(1);
  self.runSearch();
  }

  self.isPreviousPage = ko.observable(false);
  self.isNextPage = ko.observable(true);
  
  self.nextPage = function() {
    self.isPreviousPage(true);
    var current_start = self.resultStartSlice();
    var current_end = self.resultEndSlice();
    var next_start = current_start+4;
    var next_end = current_end+4;
    if(next_end >= self.resultSize()) {
      self.isNextPage(false);
      next_start = current_start;
      next_end = self.resultSize();
    }
    self.resultStartSlice(next_start);
    self.resultEndSlice(next_end);
	self.displayResultView();
	console.log(self.resultSize() , self.searchResults().length);
	if(self.resultSize() <= self.searchResults().length) {
	  return;
	}
    var csrf_token = $('#csrf_token').val();
    var data = {
      csrfmiddlewaretoken: csrf_token,
      q: self.searchQuery(),
      page: self.pageNumber()+self.shardSize()
    }
    $.post('/search', 
           data,
           function(server_response) {
            if(server_response['result'] == 'error'){
             self.showError(true);
             self.errorMessage("Error with search: " + server_response['text']);
             return;
            };
	   var instances = server_response['instances'];
           for(index in instances) {
              var instance = instances[index];
              self.searchResults.push(new ResultItem(instance));
            }
           $(".instance-action").popover({ html: true });
	   self.displayResultView();
           self.pageNumber(self.pageNumber()+self.shardSize());
         });
  }

  self.logging = ko.observable(false);
  self.showLogin = function() { self.logging(true) }

  self.previousPage = function() {
    self.isNextPage(true);
    var current_start = self.resultStartSlice();
    var current_end = self.resultEndSlice();
    var previous_start = current_start-(self.shardSize() / 2);
    var previous_end = current_end-(self.shardSize() / 2);
    if(previous_start < 1) {
       previous_start = 1;
       previous_end = self.shardSize();
       self.isPreviousPage(false);
    }
    self.resultStartSlice(previous_start);
    self.resultEndSlice(previous_end);
	self.displayResultView();
  }

  self.prettyNumber = function(str) {
    var x = str.toString();
    var rgx = /(\d+)(\d{3})/;
    while (rgx.test(x)) {
        x = x.replace(rgx, '$1' + ',' + '$2');
    }
    return x;
  }

  self.runSearch = function() {
    self.showError(false);
    self.searchResults.removeAll();
    var csrf_token = $('#csrf_token').val();
    var data = {
      csrfmiddlewaretoken: csrf_token,
//      q_type: self.searchType(),
      q: self.searchQuery(),
      page: self.pageNumber()
    }
    $.post('/search', 
           data,
           function(server_response) {
            if(server_response['result'] == 'error'){
             self.showError(true);
             self.errorMessage("Error with search: " + server_response['text']);
             return;
            }
            self.searchResults.removeAll(); 
            self.resultSize(self.prettyNumber(server_response["total"]));
            self.pageNumber(server_response['page']); 
            if(server_response["instances"].length > 0) {
               self.showResults(true);
               var instances = server_response['instances'];
               for(index in instances) {
                 var instance = instances[index];
                 self.searchResults.push(new ResultItem(instance));
               }
              $(".instance-action").popover({ html: true });
			  self.displayResultView();
             } else {
              self.showError(true);
              self.errorMessage("Your search " + '"' + self.searchQuery() + '"' + " Returned 0 Works");
            }
        });

  }

  // Handlers for Results
  self.displayFilters = function() {
   if(self.showFilters() == true) {
     self.showFilters(true);
   } else {
     self.showFilters(false);
   }

  }

  self.findInLibrary = function(instance) {
    var info = "<p>" + instance['title'] + " is located at " + instance['instanceLocation'] + "</p>";
    $('#' + instance['instance_key']).popover({content: info, html: true}); 
    $('#' + instance['instance_key']).popover('show');
    alert("Item title is " + instance['title']);

  }

  self.itemDetails = function(instance) {
    alert("Should display instance popover for " + instance['instance_key']);

  }

  self.nextResultsPage = function() {
   var current_page = parseInt(self.pageNumber());
   self.pageNumber(current_page + 1);
   self.runSearch();
    
  }

  self.prevResultsPage = function() {
   self.pageNumber(parseInt(self.pageNumber()) - 1);
   self.runSearch();
  }


  self.auSearch = function() {
  }
  self.childSubjectSearch = function() {
  }
  self.dwSearch = function() {
  }
  self.govSearch = function() {
  }
  self.isSearch = function() {
  }
  self.jtSearch = function() {

  }
  self.kwSearch = function() {
  }
  self.lcSearch = function() {

  }
  self.lccnSearch = function() {

  }
  self.medSearch = function() {

  }
  self.medcSearch = function() {

  }
  self.oclcSearch = function() {

  }
  self.tSearch = function() {

  }
}

