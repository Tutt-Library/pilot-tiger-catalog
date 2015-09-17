ko.bindingHandlers.testNullObj = {
    update: function(element, valueAccessor) {
        // First get the latest data that we're bound to
        var value = valueAccessor();
 
        // Next, whether or not the supplied model property is observable, get its current value
        var valueUnwrapped = ko.unwrap(value);
        var objValue = readObj(valueUnwrapped[0],valueUnwrapped[1]);
 				if (objValue) {
 					$(element).text(objValue);
 				} else {
 					$(element).text("");
        }
    }
};


function CatalogViewModel() {
	self = this;
	self.searchHeaders= ['All', 'Works',  'Instances','Agents','Topics'];
	self.sortOptions = ['Relevance','A-Z','Z-A'];
	self.flash = ko.observable();
	self.from = ko.observable(0);
	self.queryPhrase = ko.observable();
	self.queryPhraseForResults = ko.observable()
	self.errorMsg = ko.observable("");
	self.searchResults = ko.observableArray();
	self.shardSize = ko.observable(20);
	self.totalResults = ko.observable(0);
	self.csrf_token = $('#csrf_token').val();
	self.search_url = $('#search-url').val();
	self.chosenBfSearchViewId = ko.observable();
	self.chosenBfSortViewId = ko.observable();
	self.chosenItemData = ko.observable();
	self.viewMode = ko.observable();
	self.showClassCounts = ko.observable();
	self.instances = ko.observableArray();
	self.sumBfTypes = ko.observableArray();
	self.sumAuthTypes = ko.observableArray();
	self.sumMajBfTypes = ko.observableArray();
	self.sortState = ko.computed(function() {
									return self.chosenBfSortViewId();    
								}, this);
	self.resultSummary = ko.computed(function() {
										return (self.errorMsg() !== ""? self.errorMsg() : self.from() + " of " + self.totalResults() + ' for <em>' + self.queryPhraseForResults() + "</em>");
									}, this);
	self.testUrl = function(urlToTest) {
						if (isNotNull(urlToTest)) {
							return '#item/Topic/'+urlToTest;
						} else {
							return '';
						}
					};
    // Behaviours    
    self.goToBfSearchView = function(bfSearchView) { 
		var sFilter = (isNotNull(bfSearchView)?bfSearchView:'All');
		var	sView = (isNotNull(self.chosenBfSortViewId())?self.chosenBfSortViewId():'Relevance'); 
		var queryStr = "/" + (isNotNull(self.queryPhrase())? self.queryPhrase():"#$");
        location.hash = sView + "/" + sFilter + queryStr;    
    };
	self.goToBfSortView = function(bfSortView) {
		var sFilter = (isNotNull(self.chosenBfSearchViewId())?self.chosenBfSearchViewId():'All');
		var	sView = (isNotNull(bfSortView)?bfSortView:'Relevance'); 
		var queryStr = "/" + (isNotNull(self.queryPhrase())? self.queryPhrase():"#$"); 
        location.hash = sView + "/" + sFilter + queryStr;
    };
	
	self.goToBfResultsView = function(bfResultsView) {
		var sFilter = (isNotNull(self.chosenBfSearchViewId())?self.chosenBfSearchViewId():'All');
		var	sView = (isNotNull(self.chosenBfSortViewId())?self.chosenBfSortViewId():'Relevance'); 
		var queryStr = "/" + (isNotNull(self.queryPhrase()) ? self.queryPhrase():"#$");
        location.hash = sView + "/" + sFilter + queryStr;
    };
    
	self.loadResults = function() {
		if((self.from() < self.totalResults())&&(self.viewMode()=='search')) { 
			   searchCatalog();
        }
	}

    // Client-side routes    
    Sammy(function() {
        this.get('#:sort/:filter/:queryPhrase', function() {
        		self.sumBfTypes([]);
        		self.sumAuthTypes([]);
        		self.sumMajBfTypes([]);
            self.searchResults([]);
            self.showClassCounts(null);
            $(".tt-dropdown-menu").hide();
            var queryStr = (this.params.queryPhrase == '#$'?"":this.params.queryPhrase);
            if (this.params.sort === "item") { //load items details into 
							self.viewMode('item');	
							$('.bf_searchToolbar').hide();
							$.get("/itemDetails",
								data = {uuid:this.params.queryPhrase,type:this.params.filter},
								function(datastore_response) {
									self.chosenItemData(datastore_response);
									var testArray = datastore_response['_z_relatedItems']['rel_instances'];
									self.instances(datastore_response['_z_relatedItems']['rel_instances']);
									$('.viewItem').append("<pre>"+JSON.stringify(datastore_response, null, 2)+"</pre>");
								}
							);	
            } else {
            	
							self.viewMode('search');	
							self.chosenItemData(null);
							var sFilter = (isNotNull(this.params.filter)?this.params.filter:'All');
							var	sView = (isNotNull(this.params.sort)?this.params.sort:'Relevance');
							self.chosenBfSearchViewId(sFilter);
							self.chosenBfSortViewId(sView);
							self.queryPhrase(queryStr);		
							if (isNotNull(queryStr)) {
								$('.bf_searchToolbar').show();
								self.from(0);
								searchCatalog();
							} else {
								$('.bf_searchToolbar').hide();
							};
						};
						$(window).scrollTop(0);
        });
        this.get('#:classcount', function() {
        	self.viewMode('item');
        	$('.bf_searchToolbar').hide();
        	self.searchResults([]);
        	self.chosenItemData(null);
        	self.showClassCounts(true);
        	$.get("/classcount",
								data = {req:'none'},
								function(datastore_response) {
									var testArray = datastore_response;
									self.sumBfTypes(datastore_response['bfTypeSum']['aggregations']['2']['buckets']);
									self.sumAuthTypes(datastore_response['bfAuthSum']['aggregations']['2']['buckets']);
									self.sumMajBfTypes(datastore_response['bfMajorSum']['aggregations']['2']['buckets']);
									var tempObj = datastore_response['bfAuthSum']['aggregations']['2']['buckets'];
									var tempArray = []
									for (var key in tempObj) {
										tempArray.push({'doc_count':tempObj[key]['doc_count'],'key':key.replace(/"/g,'').replace(/type:/g,'')})
									}
									self.sumAuthTypes(tempArray);
									//$('.viewItem').append("<pre>"+JSON.stringify(datastore_response, null, 2)+"</pre>");
								}
							);
					}
				);
        
        this.get('', function() { this.app.runRoute('get', '#Relevance/All/#$') });
    }).run();



  
}

var Result = function(search_result, showType) {
	 this.cover_url = '/static/images/cover-placeholder.png';
   if('cover' in search_result) {
     this.cover_url = search_result['cover']['src']; 
   } 
	 var imageOptions =	{
	 										'Person':'',
	 										'Work': this.cover_url,
	 										'Instance': this.cover_url,
	 										'Title': this.cover_url,
	 										'Organization': '',
	 										'Authority':'',
	 										'Resource':''
	 										}
   this.uuid = search_result['uuid'];
   this.url = "#item/	"+search_result['url'];
   this.title = search_result['title'];
   if (showType) {
   		this.title = "<span class='bcSearchItemType'>"+search_result['iType']+"</span>" + this.title;
   };
   this.author = search_result['creators'];
   this.cover_url = imageOptions[search_result['iType']];
   
   /*this.cover_url = '/static/images/cover-placeholder.png';
   this.iType = search_result['iType'];
   if('cover' in search_result) {
     this.cover_url = search_result['cover']['src']; 
   }*/
   this.held_items = [];
   if('held_items' in search_result) {
       this.held_items = search_result['held_items'];
   }
}
	
function searchCatalog() {
	//alert("enter search function");
	$(".tt-dropdown-menu").hide();
	var data = {
	  csrfmiddlewaretoken: self.csrf_token,
	  phrase: self.queryPhrase(),
	  from: self.from(),
	  size: self.shardSize() 
        }
        if(self.chosenBfSortViewId()) {
          data['sort'] =  self.chosenBfSortViewId();
		}
        if(self.chosenBfSearchViewId()) {
          data['filter'] = self.chosenBfSearchViewId();
        }
  var displayItemType = false;
	var displayItemTypeFor = ['All','Agents'];
  if (displayItemTypeFor.indexOf(data.filter)>-1) {
		displayItemType = true;
	}
	$.post(self.search_url, 
			data=data,
			function(datastore_response) {
				if(datastore_response['message'] == 'error') {
					self.flash(datastore_response['body']);
					self.errorMsg("Error with search!");
				} else {
					self.queryPhraseForResults(self.queryPhrase());
					self.errorMsg("");
					self.from(datastore_response['from']);
					if(datastore_response['total'] != self.totalResults()) {
						self.totalResults(datastore_response['total']);
					}
					if(self.from() > self.totalResults()){
						self.from(self.totalResults());
					}
					for(i in datastore_response['hits']) {
						var row = datastore_response['hits'][i];
						self.searchResults
						var result = new Result(row,displayItemType);
						self.searchResults.push(result);
					}
				}
			}
	);
}

