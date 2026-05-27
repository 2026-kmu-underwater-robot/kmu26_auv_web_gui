import argparse
import asyncio
import os
from pathlib import Path

import uvicorn
from ament_index_python.packages import get_package_share_directory
from fastapi import FastAPI
from fastapi import Request
from fastapi import WebSocket
from fastapi import WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from kmu26_auv_web_gui.process_manager import ProcessManager
from kmu26_auv_web_gui.ros_interface import RosInterface


DEFAULT_BAG_TOPICS = [
    "/joy",
    "/dvl/data",
    "/dvl/twist",
    "/depth/pose",
    "/mavros/imu/data",
    "/odometry/filtered",
    "/localization/path",
    "/tf",
    "/tf_static",
]


def create_app(robot_package: str, robot_launch: str) -> FastAPI:
    app = FastAPI(title="AUV Localization Test GUI")
    process_manager = ProcessManager(robot_package=robot_package, robot_launch=robot_launch)
    ros_interface = RosInterface()
    web_dir_override = os.environ.get("KMU26_WEB_GUI_WEB_DIR")
    if web_dir_override:
        web_dir = Path(web_dir_override)
    else:
        package_share = Path(get_package_share_directory("kmu26_auv_web_gui"))
        web_dir = package_share / "web"

    app.mount("/static", StaticFiles(directory=web_dir), name="static")

    @app.on_event("startup")
    def on_startup() -> None:
        ros_interface.start()

    @app.on_event("shutdown")
    def on_shutdown() -> None:
        process_manager.stop_all()
        ros_interface.stop()

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(web_dir / "index.html")

    @app.get("/api/status")
    def status() -> dict:
        return _status(process_manager, ros_interface)

    @app.post("/api/stack/start")
    async def start_stack(request: Request) -> dict:
        body = await _json_or_empty(request)
        process_manager.start_stack(body.get("launch_args", {}))
        return _status(process_manager, ros_interface)

    @app.post("/api/stack/stop")
    def stop_stack() -> dict:
        process_manager.stop_stack()
        return _status(process_manager, ros_interface)

    @app.post("/api/dvl/setup")
    async def run_dvl_setup(request: Request) -> dict:
        body = await _json_or_empty(request)
        process_manager.run_dvl_setup(body.get("topic", "/dvl/config/command"))
        return _status(process_manager, ros_interface)

    @app.post("/api/dvl/reset_dr")
    def reset_dvl() -> dict:
        ros_interface.reset_dvl_dead_reckoning()
        return _status(process_manager, ros_interface)

    @app.post("/api/bag/start")
    async def start_bag(request: Request) -> dict:
        body = await _json_or_empty(request)
        topics = body.get("topics") or DEFAULT_BAG_TOPICS
        output_dir = process_manager.start_bag(topics)
        payload = _status(process_manager, ros_interface)
        payload["bag_output"] = output_dir
        return payload

    @app.post("/api/bag/stop")
    def stop_bag() -> dict:
        process_manager.stop_bag()
        return _status(process_manager, ros_interface)

    @app.websocket("/ws/status")
    async def status_ws(websocket: WebSocket) -> None:
        await websocket.accept()
        try:
            while True:
                await websocket.send_json(_status(process_manager, ros_interface))
                await asyncio.sleep(0.2)
        except WebSocketDisconnect:
            return

    return app


async def _json_or_empty(request: Request) -> dict:
    try:
        return await request.json()
    except Exception:
        return {}


def _status(process_manager: ProcessManager, ros_interface: RosInterface) -> dict:
    return {
        "process": process_manager.status(),
        "ros": ros_interface.status(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", default=8080, type=int)
    parser.add_argument("--robot-package", default="hit25_auv_ros2")
    parser.add_argument("--robot-launch", default="localization_test.launch.py")
    args = parser.parse_args()

    app = create_app(robot_package=args.robot_package, robot_launch=args.robot_launch)
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
