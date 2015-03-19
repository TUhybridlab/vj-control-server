FAN_URL="/fan/"
EVENT_URL="/events/"


do_nothing = function() {}

default_error = function (jqXHR) {
			console.log("ajax error " + jqXHR.status);
			serverDown = true;
}

log = function(msg) {
	time = new Date().timeNow();
	$('#log').append('<p>'+ time + ' - '+ msg + '</p>');
}

ajax_json = function(uri, method, request_data, is_async, success_callback, error_callback) {
	var request = {
		url: uri,
		type: method,
		contentType: "application/json",
		accepts: "application/json",
		cache: false,
		dataType: 'json',
		async: is_async,
		success: function(data) {
			serverDown = false;
			success_callback(data);
		},
		error: function(jqXHR) {
			default_error(jqXHR);
			error_callback();
		}
	};

	if (request_data != null)
		request.data = JSON.stringify(request_data);

	return $.ajax(request);
}

FanAPI = function() {
	var self = this;

	self.setFanSpeed = function(speed_percentage) {
		ajax_json(FAN_URL + speed_percentage, "PUT", null, true, do_nothing, do_nothing);
	}

	self.getFanSpeed = function() {
		ajax_json(FAN_URL, "GET", null, false, do_nothing, do_nothing).done(function(data) { self.setSlider(data); });
	}

	return self;
}

FanSlider = function(fanAPI) {
	var self = this;
	self.onChangeCallbackEnabled = true;

	self.initSlider = function () {
		ajax_json(FAN_URL, "GET", null, false, do_nothing, do_nothing).done(function(data) {
			// Initilaize slider with value
			$( "#slider" ).slider({
				value: data.speed
			});

			// Set speed with slider
			$( "#slider" ).on( "slidechange", function( event, ui ) {
				if (self.onChangeCallbackEnabled)
					fanAPI.setFanSpeed($( "#slider" ).slider( "value" ));
			});
		});
	}

	self.setSlider = function(speed) {
		self.onChangeCallbackEnabled = false;
		$( "#slider" ).slider( "option", "value", speed);
		self.onChangeCallbackEnabled = true;
	}


	self.initSlider();

	return self;
}

EventSocket = function(){
	var ret = io.connect('http://' + document.domain + ':' + location.port + '/events');


	// Receive fan event from server
	ret.on('fanEvent', function(msg) {
		fanSlider.setSlider(msg);
	});


	return ret;
}




}

fanAPI = FanAPI();
fanSlider = FanSlider(fanAPI);
eventSocket = EventSocket(fanAPI);

// For the time now
Date.prototype.timeNow = function () {
	return ((this.getHours() < 10)?"0":"") + this.getHours() +":"+ ((this.getMinutes() < 10)?"0":"") + this.getMinutes() +":"+ ((this.getSeconds() < 10)?"0":"") + this.getSeconds();
}
