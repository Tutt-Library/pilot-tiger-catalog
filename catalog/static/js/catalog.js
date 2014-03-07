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
   displayReserveDialog = function() {
      $('#reserve-now-dlg').modal('show');
    } 
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
  self.pageNumber = ko.observable(0);
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
  self.inViewPoint = function(index) {
    var index1 = parseInt(index) + 1;
    if(index1 <= self.resultEndSlice()) { 
      if(index1 >= self.resultStartSlice()) {
        return true;
      }
    }
    return false;  
  }


  self.displayResultView = function() {
    $.map($('.result-div'), function(n ,i) {
      if(!self.inViewPoint(parseInt(i))) {
       $(n).css('display', 'none');
      } else {
        $(n).css('display', 'block');
    }
   });
  }
  
  self.searchResults = ko.observableArray();
  self.shardSize = ko.observable(8);
  self.pageNumber(0);

  self.isPreviousPage = ko.observable(false);
  self.isNextPage = ko.observable(true);
  
  self.nextPage = function() {
    self.isPreviousPage(true);
    var current_start = self.resultStartSlice();
    var current_end = self.resultEndSlice();
    var next_start = current_start+(self.shardSize() / 2);
    var next_end = current_end+(self.shardSize() / 2);
 
    if(next_end >= self.resultSize()) {
      self.isNextPage(false);
      next_start = current_start;
      next_end = self.resultSize();
    }
    self.resultStartSlice(next_start);
    self.resultEndSlice(next_end);
    self.displayResultView();

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


  self.runSearch = function(context, data) {
    self = context;
    self.searchQuery(data['q']);
    self.showError(false);
    self.searchResults.removeAll();
    self.resultStartSlice(1);
    self.resultEndSlice(4);
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
  // if(server_response['total'] <= self.resultEndSlice()) {
  // self.resultEndSlice(server_response['total']);
  // }
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
  

}

function LoginViewModel() {
 var self = this;

 self.logging = ko.observable(false);

 self.showLogin = function() {
  self.logging(true);
 }
 

}

function SearchViewModel(resultsViewModel) {
  var self = this;
  self.searchQuery = ko.observable();
  self.resultsVM = resultsViewModel;

  self.newSearch = function() {
   var csrf_token = $('#csrf_token').val();
   var data = {
     csrfmiddlewaretoken: csrf_token,
     q: self.searchQuery(),
     page: self.resultsVM.pageNumber()
   }
   self.resultsVM.runSearch(self.resultsVM, data);
  }
}

function AuthenticationViewModel() {
  var self = this;

  self.loginAction = function() {
   $('#login-feedback-dlg').modal('show');
  }

}

function WorkViewModel() {
  var self = this;

  self.displayMARC = ko.observable(false);

  self.showMARC = function() {
    if(self.displayMARC()===true) {
      self.displayMARC(false);
    } else {
      self.displayMARC(true);
    }
  }
}
