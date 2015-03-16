do_nothing = function() {}

default_error = function (jqXHR) {
			console.log("ajax error " + jqXHR.status);
			serverDown = true;
}

ajax = function(uri, method, request_data, is_async, success_callback, error_callback) {
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
		ajax("/fan/" + speed_percentage, "PUT", null, true, do_nothing, do_nothing);
	}

	self.getFanSpeed = function() {
		ajax("/fan/", "GET", null, false, do_nothing, do_nothing).done(function(data) { self.setSlider(data); });
	}

	return self;
}

FanSlider = function(fanAPI) {
	var self = this;
	self.onChangeCallbackEnabled = true;

	self.initSlider = function () {
		ajax("/fan/", "GET", null, false, do_nothing, do_nothing).done(function(data) {
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

	self.setSlider = function(data) {
		console.log("setting slider to " + data.speed);
		self.onChangeCallbackEnabled = false;
		$( "#slider" ).slider( "option", "value", data.speed);
		self.onChangeCallbackEnabled = true;
	}


	self.initSlider();

	return self;
}

EventSocket = function(){
	var ret = io.connect('http://' + document.domain + ':' + location.port + '/events');

	// Receive event from server
	ret.on('serverEvent', function(msg) {
		time = new Date().timeNow();
		$('#log').append('<p>'+ time + ': ' + msg.data + '</p>');
	});

	// Receive fan event from server
	ret.on('fanEvent', function(msg) {
		fanAPI.getFanSpeed();
	});

	ret.sendEvent = function() {
		// Send event to server
		ret.emit('webEvent', {data: $('#emit_data').val()});
		return false;
	}

	return ret;
}

EventPoster = function() {
	var self = this;

	self.sendEvent = function() {
		data = {data: $('#emit_data').val()}
		ajax("/events/", "POST", data, false, do_nothing, do_nothing);

		return false;
	}

	return self;
}

fanAPI = FanAPI();
fanslider = FanSlider(fanAPI);
eventSocket = EventSocket(fanAPI);
eventPoster = EventPoster();

// For the time now
Date.prototype.timeNow = function () {
	return ((this.getHours() < 10)?"0":"") + this.getHours() +":"+ ((this.getMinutes() < 10)?"0":"") + this.getMinutes() +":"+ ((this.getSeconds() < 10)?"0":"") + this.getSeconds();
}
