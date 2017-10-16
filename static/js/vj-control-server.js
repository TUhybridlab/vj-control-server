ENVIRONMENT_URL="/environment/";
PARACHUTE_URL="/parachute/";
WATERSPLASHER_URL = "/watersplasher/";
EVENT_URL="/events/";
JUMP_STATE_URL="/jumpState/";

do_nothing = function() {};

default_error = function (jqXHR) {
			console.log("ajax error " + jqXHR.status);
};

log = function(msg) {
	var time = new Date().timeNow();
	$('#log').prepend('<p>'+ time + ' - '+ msg + '</p>');
};

ajax_json = function(uri, method, request_data, is_async, success_callback) {
	var request = {
		url: uri,
		type: method,
		contentType: "application/json",
		accepts: "application/json",
		cache: false,
		dataType: 'json',
		async: is_async,
		success: function(data) {
			success_callback(data);
		},
		error: function(jqXHR) {
			default_error(jqXHR);
		}
	};

	if (!request_data)
		request.data = JSON.stringify(request_data);

	return $.ajax(request);
};


VjControlAPI = function() {
	var self = this;

	self.setFanSpeed = function(speed_percentage) {
		eventSocket.emit('unityFanSpeedEvent', speed_percentage);
	};

	self.setWatersplasher = function(state) {
		if (state)
			eventSocket.emit('unityWaterSplasherEvent', '1');
		else
			eventSocket.emit('unityWaterSplasherEvent', '0');
	};

	self.getEnvironmentState = function () {
		ajax_json(ENVIRONMENT_URL, "GET", null, true, self.applyEnvironment);
    };

	self.applyEnvironment = function(data) {
		console.log("Applying"); console.log(data);
		fanSlider.setSlider(data.duty_cycle);
		watersplasherSwitch.setSwitchState(data.watersplasher_state);
	};

	return self;
};

UiSwitch = function(id, onStateChanged) {
	var self = this;
	self.id = id;
	self.uiSwitch = $(id);

	self.setSwitchState = function(state) {
		self.uiSwitch.prop('checked', state);
	};

	self.uiSwitch.change(function(event) {
		onStateChanged(event.target.checked);
	});

	return self;
};

UiSlider = function(id, onValueChanged) {
	var self = this;
	self.id = id;
	self.slider = $(id);

	self.setSlider = function(speed) {
		$("#slider_value").text("Level " + speed);
		return self.slider.val(speed);
	};

	self.off = function () {
		self.setSlider(0).change();
    };

	self.slider.change(function(event) {
		onValueChanged(event.target.value);
	});

	return self;
};

WatersplasherUiSlider = function(id, onValueChanged) {
	var self = this;
	self.id = id;
	self.slider = $(id);
	self.onValueChanged = onValueChanged;

	self.initSlider = function () {
		console.log("Initializing");
		ajax_json(WATERSPLASHER_URL, "GET", null, false, do_nothing, do_nothing).done(function(data) {
			// Initilaize slider with value
			console.log("Setting slider to " + data.intensity);
			self.setSlider(data.intensity);

			// Set speed with slider
			self.slider.change(function(event) {
				self.onValueChanged(event.target.value);
			});
		});
	};

	self.setSlider = function(speed) {
		return self.slider.val(speed);
	};

	self.off = function () {
		self.setSlider(0).change();
    };

	return self;
};

EventSocket = function(){
	var ret = io.connect('http://' + document.domain + ':' + location.port + '/events');

	var self = this;
	self.previousFanSpeed = -1;

	ret.on('connect', function(msg) {
		log('[INFO] Socket connected.');
		serverConnectedStateSwitch.setSwitchState(true);
		vjAPI.getEnvironmentState();
	});

	ret.on('disconnect', function(msg) {
		log('[ERROR] Socket disconnected!');
		serverConnectedStateSwitch.setSwitchState(false);
	});

	ret.on('update', function (msg) {
		vjAPI.applyEnvironment(msg);
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
};

ConfigSocket = function () {
	var ret = io.connect('http://' + document.domain + ':' + location.port + '/config');

	ret.on('connect', function(msg) {
		watersplasherIntensitySlider.initSlider();
	});

	ret.setWatersplasherIntensity = function(intensity) {
		log('[DEBUG] Setting watersplasher intensity to ' + intensity);
		ret.emit('waterSplasherDutyCycle', intensity);
	};

	return ret;
};

vjAPI = VjControlAPI();
eventSocket = EventSocket(vjAPI);
configSocket = ConfigSocket();

serverConnectedStateSwitch = new UiSwitch('input#server-connection-state', do_nothing);
fanSlider = UiSlider('input#fan-slider', vjAPI.setFanSpeed);
watersplasherSwitch = new UiSwitch('input#watersplasher-state', vjAPI.setWatersplasher);
watersplasherIntensitySlider = new WatersplasherUiSlider('input#watersplasher-intensity-slider', configSocket.setWatersplasherIntensity);

initSequence = function () {
	configSocket.emit('initSequence');
};

// For the time now
Date.prototype.timeNow = function () {
	return ((this.getHours() < 10)?"0":"") + this.getHours() +":"+ ((this.getMinutes() < 10)?"0":"") + this.getMinutes() +":"+ ((this.getSeconds() < 10)?"0":"") + this.getSeconds();
};
