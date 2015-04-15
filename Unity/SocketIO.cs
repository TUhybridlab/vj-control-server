using UnityEngine;
using SocketIOClient;

public class SocketIO {

	private static SocketIO instance = null;

	private Client client;
	private IEndPointClient socket;
	private bool isJumpOngoing = false;
	private bool isLevelReset = true;
	private bool isReadyToJump = false;

	public static SocketIO getInstance() {
		if (instance == null) {
			instance = new SocketIO();
			instance.InitSocket();
		}

		return instance;
	}

	// Use this for initialization
	private void InitSocket () {
		client = new Client("http://192.168.1.50:5000");

		client.Error += SocketError;
		client.Message += SocketMessage;

		client.On ("connect", "/events", (fn) =>
		{
			EventOpenParachute();
			EventWaterSplasherOn();
			EventFanSpeed(100);

			EventWaterSplasherOff();
		});

		client.On ("raspiStartJumpEvent", "/events", (data) =>
		{
			Debug.LogError("TODO: Hook up start");

			EventJumpStarted();
			//EventLanding();
		});

		client.On ("raspiPlayerReadyEvent", "/events", (data) =>
		{
			EventUnityReady();
		});

		socket = client.Connect ("/events");
	}

	/* -------------------- */
	/* - Eventemitter     - */
	/* -------------------- */
	public void EventUnityReady() {
		isReadyToJump = true;
		socket.Emit("unityReadyEvent", "Unity is ready to go", null);
	}

	public void EventJumpStarted() {
		isJumpOngoing = true;
		isReadyToJump = false;
		isLevelReset = false;
		socket.Emit ("unityJumpStartedEvent", "Jump was started", null);
	}
	
	public void EventOpenParachute() {
		socket.Emit("unityParachuteOpenEvent", "Parachute opened", null);
	}

	public void EventLanding() {
		socket.Emit("unityLandingEvent", "Player landed", null);
		isJumpOngoing = false;
	}
	
	public void EventFanSpeed(int speed) {
		socket.Emit("unityFanSpeedEvent", "" + speed, null);
	}
	
	public void EventWaterSplasherOn() {
		socket.Emit("unityWaterSplasherOnEvent", "Water splasher ON", null);
	}

	public void EventWaterSplasherOff() {
		socket.Emit("unityWaterSplasherOffEvent", "Water splasher OFF", null);
	}

	public void EventResetLevel() {
		socket.Emit("unityResetLevel", "Unity resets", null);
		isLevelReset = true;
	}

	/* -------------------- */
	/* - Socket handler   - */
	/* -------------------- */
	private void SocketError(object sender, SocketIOClient.ErrorEventArgs e) {
		Debug.Log ("Error: " + e.Message);
	}

	private void SocketMessage(object sender, SocketIOClient.MessageEventArgs e) {
		//Debug.Log ("Message: " + e.Message.Event + "-" + e.Message.MessageText);
	}

	/* -------------------- */
	/* - Other stuff      - */
	/* -------------------- */
	void OnApplicationQuit() {
		Debug.Log("OnQuit");

		Debug.Log ("Close SocketIO client");
		client.Close ();
	}
}
