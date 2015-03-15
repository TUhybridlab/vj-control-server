ajax = function(uri, method, data, is_async, sucess, error) {
	var request = {
		url: uri,
		type: method,
		contentType: "application/json",
		accepts: "application/json",
		cache: false,
		dataType: 'json',
		async: is_async,
		data: JSON.stringify(data),
		success: function() {
			serverDown = false;
		},
		error: function(jqXHR) {
			console.log("ajax error " + jqXHR.status);
			serverDown = true;
		}
	};
	return $.ajax(request);
}

setFanSpeed = function(speed_percentage) {
	ajax("/fan/" + speed_percentage, "GET", "", true, setFanSpeed_success, default_error);
}

setFanSpeed_success = function() {
	alert("TODO")
}

default_error = function (jqXHR) {
	console.log("ajax error " + jqXHR.status);
	serverDown = true;
}