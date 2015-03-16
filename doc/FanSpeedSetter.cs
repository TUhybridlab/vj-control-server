using UnityEngine;

public class FanSpeedSetter : MonoBehaviour {
	void Start()
	{
		// Get request
		WWW www_get = new WWW("192.168.1.50:5000/fan/0");

		// Post request
		WWWForm speedData = new WWWForm ();
		speedData.AddField ("speed", 100);
		WWW www_post = new WWW("192.168.1.50:5000/fan/", speedData);
	}
}