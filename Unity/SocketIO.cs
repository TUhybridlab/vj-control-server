using UnityEngine;
using SocketIOClient;

public class SocketIO : MonoBehaviour {
	private Client client;
	private IEndPointClient socket;
	private bool isJumpOngoing = false;
	private bool isLevelReset = true;
	private bool isReadyToJump = false;

	// Use this for initialization
	void Start () {
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
			if (isReadyToJump) {
				Debug.LogError("TODO: Hook up start");

				EventJumpStarted();
				//EventLanding();
			}
		});

		client.On ("raspiPlayerReadyEvent", "/events", (data) =>
		{
			if (isLevelReset)
				EventUnityReady();
		});

		socket = client.Connect ("/events");
	}

	// Update is called once per frame
	void Update () {
		if (Input.GetKeyDown (KeyCode.Space))
			if (isJumpOngoing)
				EventLanding ();

		if (Input.GetKeyDown (KeyCode.R))
		if (!isJumpOngoing) {
			EventResetLevel ();
		}
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
