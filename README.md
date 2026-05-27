# Localization Test GUI

Web control panel for running AUV localization tests from a browser.

The intended deployment is:

- Ubuntu robot PC runs ROS 2, MAVROS, DVL, EKF, this GUI server, and bag recording.
- MacBook opens the web page over Ethernet.
- MacBook ROS `joy_node` can publish `/joy` over DDS, while this GUI monitors `/joy` health from the robot PC.

## One-click Run

On the Ubuntu robot PC:

```bash
./kmu26_auv_web_gui/scripts/start_kmu26_auv_web_gui.sh
```

To add a desktop/app launcher on Ubuntu:

```bash
./kmu26_auv_web_gui/scripts/install_desktop_launcher.sh
```

After that, open **KMU26 AUV Web GUI** from the app menu or desktop icon.

## ROS Run

```bash
ros2 run kmu26_auv_web_gui server --host 0.0.0.0 --port 8080
```

Then open:

```text
http://<ubuntu-robot-ip>:8080
```

## Python Dependencies

This package uses FastAPI and Uvicorn for the web server.

```bash
python3 -m pip install fastapi uvicorn
```
