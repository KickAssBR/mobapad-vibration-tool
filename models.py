from dataclasses import dataclass

@dataclass
class DeviceInfo:
    id_a: str
    id_b: str
    version: str
    flags: int

@dataclass
class MotorConfig:
    motor1: int
    motor2: int
    motor3: int
    motor4: int
    auto_shutdown_minutes: int