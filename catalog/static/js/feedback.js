function AuthenticationFeedbackViewModel() {
  self = this;

  self.CCEmail = ko.observable();
  self.CCGoldCard =  ko.observable();
  self.CCTigerNumber =  ko.observable();
  self.facebook = ko.observable();
  self.gmail = ko.observable();
  self.microsoft = ko.observable();
  self.twitter = ko.observable();
  self.otherAuthentication = ko.observable();

  self.sendFeedback = function() {
   var data = {
     ccemail: self.CCEmail(),
     ccgoldcard: self.CCGoldCard(),
     facebook: self.facebook(),
     gmail:  self.gmail(),
     microsoft: self.microsoft(),
     twitter: self.twitter(),
     other: self.otherAuthentication()
   }
   for(i in data) {
     var item = data[i];
     console.log("Data is " + item);
   }
  }

}
