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
     job: 'auth_opts_test',
     ccemail: self.CCEmail(),
     ccgoldcard: self.CCGoldCard(),
     facebook: self.facebook(),
     gmail:  self.gmail(),
     microsoft: self.microsoft(),
     twitter: self.twitter(),
     other: self.otherAuthentication()
   }
   $.post('/feedback',
           data,
           function(server_response) {
             if(server_response['response'] === 'ok') {
               alert(server_response['msg']);
             }
           });
   $('#login-feedback-dlg').modal('hide');
  }

}
