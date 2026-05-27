import math
import threading
import time
from collections import deque
from dataclasses import dataclass, field

import rclpy
from dvl_msgs.msg import ConfigCommand
from geometry_msgs.msg import PoseWithCovarianceStamped
from geometry_msgs.msg import TwistWithCovarianceStamped
from rclpy.executors import SingleThreadedExecutor
from nav_msgs.msg import Odometry
from rclpy.node import Node
from sensor_msgs.msg import Imu
from sensor_msgs.msg import Joy


def _yaw_from_quaternion(x: float, y: float, z: float, w: float) -> float:
    siny_cosp = 2.0 * (w * z + x * y)
    cosy_cosp = 1.0 - 2.0 * (y * y + z * z)
    return math.atan2(siny_cosp, cosy_cosp)


@dataclass
class TopicHealth:
    name: str
    stale_after: float = 1.0
    last_seen: float | None = None
    stamps: deque[float] = field(default_factory=lambda: deque(maxlen=120))

    def tick(self) -> None:
        now = time.monotonic()
        self.last_seen = now
        self.stamps.append(now)

    def snapshot(self) -> dict:
        now = time.monotonic()
        age = None if self.last_seen is None else now - self.last_seen
        return {
            "name": self.name,
            "alive": age is not None and age <= self.stale_after,
            "age": age,
            "hz": self._hz(now),
        }

    def _hz(self, now: float) -> float:
        recent = [stamp for stamp in self.stamps if now - stamp <= 2.0]
        if len(recent) < 2:
            return 0.0
        return (len(recent) - 1) / (recent[-1] - recent[0])


class LocalizationRosNode(Node):
    def __init__(self):
        super().__init__("kmu26_auv_web_gui_bridge")
        self._lock = threading.Lock()
        self._health = {
            "odom": TopicHealth("/odometry/filtered"),
            "dvl": TopicHealth("/dvl/twist"),
            "depth": TopicHealth("/depth/pose"),
            "imu": TopicHealth("/mavros/imu/data"),
            "joy": TopicHealth("/joy", stale_after=0.5),
        }
        self._pose = {"x": 0.0, "y": 0.0, "z": 0.0, "yaw": 0.0}
        self._velocity = {"x": 0.0, "y": 0.0, "z": 0.0}
        self._depth = {"z": 0.0}
        self._joy = {"axes": [], "buttons": []}
        self._path: deque[dict[str, float]] = deque(maxlen=1200)

        self._dvl_config_pub = self.create_publisher(
            ConfigCommand,
            "/dvl/config/command",
            10,
        )
        self.create_subscription(Odometry, "/odometry/filtered", self._on_odom, 20)
        self.create_subscription(TwistWithCovarianceStamped, "/dvl/twist", self._on_dvl, 20)
        self.create_subscription(PoseWithCovarianceStamped, "/depth/pose", self._on_depth, 20)
        self.create_subscription(Imu, "/mavros/imu/data", self._on_imu, 20)
        self.create_subscription(Joy, "/joy", self._on_joy, 20)

    def publish_dvl_reset(self) -> None:
        msg = ConfigCommand()
        msg.command = "reset_dead_reckoning"
        msg.parameter_name = ""
        msg.parameter_value = ""
        self._dvl_config_pub.publish(msg)

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "topics": {name: item.snapshot() for name, item in self._health.items()},
                "pose": dict(self._pose),
                "velocity": dict(self._velocity),
                "depth": dict(self._depth),
                "joy": {
                    "axes": list(self._joy["axes"]),
                    "buttons": list(self._joy["buttons"]),
                },
                "path": list(self._path),
            }

    def _on_odom(self, msg: Odometry) -> None:
        pose = msg.pose.pose
        yaw = _yaw_from_quaternion(
            pose.orientation.x,
            pose.orientation.y,
            pose.orientation.z,
            pose.orientation.w,
        )
        with self._lock:
            self._health["odom"].tick()
            self._pose = {
                "x": pose.position.x,
                "y": pose.position.y,
                "z": pose.position.z,
                "yaw": yaw,
            }
            self._path.append({"x": pose.position.x, "y": pose.position.y})

    def _on_dvl(self, msg: TwistWithCovarianceStamped) -> None:
        linear = msg.twist.twist.linear
        with self._lock:
            self._health["dvl"].tick()
            self._velocity = {"x": linear.x, "y": linear.y, "z": linear.z}

    def _on_depth(self, msg: PoseWithCovarianceStamped) -> None:
        with self._lock:
            self._health["depth"].tick()
            self._depth = {"z": msg.pose.pose.position.z}

    def _on_imu(self, msg: Imu) -> None:
        del msg
        with self._lock:
            self._health["imu"].tick()

    def _on_joy(self, msg: Joy) -> None:
        with self._lock:
            self._health["joy"].tick()
            self._joy = {
                "axes": [round(value, 3) for value in msg.axes],
                "buttons": list(msg.buttons),
            }


class RosInterface:
    def __init__(self):
        self.node: LocalizationRosNode | None = None
        self._executor: SingleThreadedExecutor | None = None
        self._spin_thread: threading.Thread | None = None

    def start(self) -> None:
        if not rclpy.ok():
            rclpy.init(args=None)
        self.node = LocalizationRosNode()
        self._executor = SingleThreadedExecutor()
        self._executor.add_node(self.node)
        self._spin_thread = threading.Thread(target=self._executor.spin, daemon=True)
        self._spin_thread.start()

    def stop(self) -> None:
        if self._executor is not None:
            self._executor.shutdown()
            self._executor = None
        if self.node is not None:
            self.node.destroy_node()
            self.node = None
        if self._spin_thread is not None:
            self._spin_thread.join(timeout=1.0)
            self._spin_thread = None
        if rclpy.ok():
            rclpy.shutdown()

    def status(self) -> dict:
        if self.node is None:
            return {}
        return self.node.snapshot()

    def reset_dvl_dead_reckoning(self) -> None:
        if self.node is None:
            raise RuntimeError("ROS interface is not running")
        self.node.publish_dvl_reset()
