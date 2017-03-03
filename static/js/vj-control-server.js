FAN_URL="/fan/"
PARACHUTE_URL="/parachute/"
WATERSPLASHER_URL = "/watersplasher/"
EVENT_URL="/events/"
JUMP_STATE_URL="/jumpState/"


do_nothing = function() {}

default_error = function (jqXHR) {
			console.log("ajax error " + jqXHR.status);
			serverDown = true;
}

log = function(msg) {
	time = new Date().timeNow();
	$('#log').prepend('<p>'+ time + ' - '+ msg + '</p>');
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

UiSwitch = function(id, onStateChanged) {
	var self = this;
	self.id = id;
	self.uiSwitch = $(id);

	self.setSwitchState = function(state) {
		self.uiSwitch.bootstrapSwitch('state', state, true);
	}

	self.uiSwitch.bootstrapSwitch('state', false, true);
	self.uiSwitch.on('switchChange.bootstrapSwitch', function(event, state) {
		onStateChanged(event, state);
	});

	return self;
}

VjControlAPI = function() {
	var self = this;

	self.setFanSpeed = function(speed_percentage) {
		eventSocket.emit('unityFanSpeedEvent', speed_percentage);
	}

	self.setWatersplasher = function(event, state) {
		if (state)
			eventSocket.emit('unityWaterSplasherOnEvent', '');
		else
			eventSocket.emit('unityWaterSplasherOffEvent', '');
	}

	self.setParachute = function(event, state) {
		if (state)
			eventSocket.emit('unityParachuteOpenEvent', '');
		else
			eventSocket.emit('unityResetLevel', '');
	}

	self.getFanSpeed = function() {
		ajax_json(FAN_URL, "GET", null, true, do_nothing, do_nothing).done(function(data) { self.setSlider(data.speed); });
	}

	self.getParachuteState = function() {
		ajax_json(PARACHUTE_URL, "GET", null, true, function(data) { parachuteSwitch.setSwitchState(data.parachute); });
	}

	self.getWatersplasherState = function() {
		ajax_json(WATERSPLASHER_URL, "GET", null, true, function(data) { watersplasherSwitch.setSwitchState(data.watersplasher); });
	}

	self.getJumpState = function() {
		ajax_json(JUMP_STATE_URL, "GET", null, true, function(data) { jumpStateSwitch.setSwitchState(data.jumpStarted); });
	}

	return self;
}

FanSlider = function(vjAPI) {
	var self = this;
	self.onChangeCallbackEnabled = true;

	self.initSlider = function () {
		ajax_json(FAN_URL, "GET", null, false, do_nothing, do_nothing).done(function(data) {
			// Initilaize slider with value
			$( "#slider" ).slider({
				value: data.speed,
				max: 16,
				step: 1
			});

			// Set speed with slider
			$( "#slider" ).on( "slidechange", function( event, ui ) {
				if (self.onChangeCallbackEnabled)
					vjAPI.setFanSpeed($( "#slider" ).slider( "value" ));
			});
		});
	}

	self.setSlider = function(speed) {
		self.onChangeCallbackEnabled = false;
		$( "#slider" ).slider( "option", "value", speed);
		$("#slider_value").text("Level " + speed);
		self.onChangeCallbackEnabled = true;
	}


	self.initSlider();

	return self;
}

EventSocket = function(){
	var ret = io.connect('http://' + document.domain + ':' + location.port + '/events');

	var self = this;
	self.previousFanSpeed = -1;

	ret.on('connect', function(msg) {
		log('[INFO] Socket connected.');
		serverConnectedStateSwitch.setSwitchState(true);
		vjAPI.getFanSpeed();
		vjAPI.getParachuteState();
		vjAPI.getWatersplasherState();
		vjAPI.getJumpState();
	});

	ret.on('disconnect', function(msg) {
		log('[ERROR] Socket disconnected!');
		serverConnectedStateSwitch.setSwitchState(false);
	});

	// Receive fan event from server
	ret.on('raspiFanEvent', function(msg) {
		fanSlider.setSlider(msg);
		if (previousFanSpeed != msg) {
			log('[DEBUG] Set fan slider to ' + msg);
			previousFanSpeed = msg;
		}
	});

	// Watersplasher switched on
	ret.on('raspiWaterSplasherOnEvent', function(msg) {
		log('[DEBUG] Watersplasher: On');
		watersplasherSwitch.setSwitchState(true);
	});

	// Watersplasher switched off
	ret.on('raspiWaterSplasherOffEvent', function(msg) {
		log('[DEBUG] Watersplasher: Off');
		watersplasherSwitch.setSwitchState(false);
	});

	// Parachute opened
	ret.on('raspiParachuteOpenEvent', function(msg) {
		log('[DEBUG] Parachute opened');
		parachuteSwitch.setSwitchState(true);
	});

	// Parachute closed
	ret.on('raspiParachuteCloseEvent', function(msg) {
		log('[DEBUG] Parachute closed');
		parachuteSwitch.setSwitchState(false);
		jumpStateSwitch.setSwitchState(false);
	});

	// Ready to jump
	ret.on('raspiUnityReadyEvent', function(msg) {
		log('[DEBUG] Unity is ready');
		readyStateSwitch.setSwitchState(true);
	});

	// Start jump
	ret.on('raspiJumpStartedEvent', function(msg) {
		log('[DEBUG] Player jumped');
		jumpStateSwitch.setSwitchState(true);
		readyStateSwitch.setSwitchState(false);
		myWatch.reset();
		myWatch.start();
	});

	// Landing
	ret.on('raspiLandingEvent', function(msg) {
		log('[DEBUG] Player landed');
		jumpStateSwitch.setSwitchState(false);

		myWatch.stop();
	});

	return ret;
}

vjAPI = VjControlAPI();
fanSlider = FanSlider(vjAPI);
eventSocket = EventSocket(vjAPI);


readyStateSwitch = new UiSwitch('input#ready-state', function(event, state) {if (state) eventSocket.emit('unityReadyEvent', '[DEBUG] Unity ready!'); else eventSocket.emit('unityResetLevel', '[DEBUG] Reset level');});
jumpStateSwitch = new UiSwitch('input#jump-state', do_nothing);
serverConnectedStateSwitch = new UiSwitch('input#server-connection-state', do_nothing);

watersplasherSwitch = new UiSwitch('input#watersplasher-state', vjAPI.setWatersplasher);
parachuteSwitch = new UiSwitch('input#parachute-state', vjAPI.setParachute);

updateWatch = function (watch) {
	$('#watchdisplay').text(watch.toString());
	console.log("Updating watch");
};
myWatch = new Stopwatch(updateWatch, 100);


// For the time now
Date.prototype.timeNow = function () {
	return ((this.getHours() < 10)?"0":"") + this.getHours() +":"+ ((this.getMinutes() < 10)?"0":"") + this.getMinutes() +":"+ ((this.getSeconds() < 10)?"0":"") + this.getSeconds();
}
