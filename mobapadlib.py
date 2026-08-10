import asyncio
from bleak import BleakClient, BleakScanner
from models import DeviceInfo, MotorConfig

S1_LEFT_NAMES = ["Mobapad-S1-Joy-L"]
S1_RIGHT_NAMES = ["Mobapad-S1-Joy-R"]
M6_LEFT_NAMES = ["Mobapad-M6-Joy-L"]
M6_RIGHT_NAMES = ["Mobapad-M6-Joy-R"]
M12_LEFT_NAMES = ["Mobapad-M12-S-L","Mobapad M12-S-L"]
M12_RIGHT_NAMES = ["Mobapad-M12-S-R","Mobapad M12-S-R"]

WRITE_UUID = "d7f010e1-660d-46e9-96c3-19c4148bdab5"
READ_UUID = "d7f010e2-660d-46e9-96c3-19c4148bdab5"

CMD_READ_INFO    = 0x91
CMD_READ_ROCKER  = 0xB1
CMD_READ_TRIGGER = 0xB2
CMD_READ_MOTOR   = 0xB3
CMD_READ_TURBO   = 0xB4
CMD_READ_MACRO   = 0xB5
CMD_READ_REMAP   = 0xB6
CMD_READ_LED     = 0xB7


P = [
    161,82,213,163,245,137,246,143,
    240,157,72,147,234,52,49,186,
    195,77,198,235,73,96,216,163,
    218,42,83,141,244,97,24,191,
    174,215,111,81,228,160,217,146
]

O = [
    51,99,157,121,
    242,219,162,26,
    170,33,139,232,
    116,211,88
]

N = [
0,121,242,139,51,74,193,184,102,31,148,237,85,44,167,222,
204,181,62,71,255,134,13,116,170,211,88,33,153,224,107,18,
79,54,189,196,124,5,142,247,41,80,219,162,26,99,232,145,
131,250,113,8,176,201,66,59,229,156,23,110,214,175,36,93,
158,231,108,21,173,212,95,38,248,129,10,115,203,178,57,64,
82,43,160,217,97,24,147,234,52,77,198,191,7,126,245,140,
209,168,35,90,226,155,16,105,183,206,69,60,132,253,118,15,
29,100,239,150,46,87,220,165,123,2,137,240,72,49,186,195,
235,146,25,96,216,161,42,83,141,244,127,6,190,199,76,53,
39,94,213,172,20,109,230,159,65,56,179,202,114,11,128,249,
164,221,86,47,151,238,101,28,194,187,48,73,241,136,3,122,
104,17,154,227,91,34,169,208,14,119,252,133,61,68,207,182,
117,12,135,254,70,63,180,205,19,106,225,152,32,89,210,171,
185,192,75,50,138,243,120,1,223,166,45,84,236,149,30,103,
58,67,200,177,9,112,251,130,92,37,174,215,111,22,157,228,
246,143,4,125,197,188,55,78,144,233,98,27,163,218,81,40
]


class Mobapad:

    def __init__(
        self,
        address,
        debug=False
    ):
        
        self.debug = debug
        self.address = address
        self.client = None
        self.device_name = None
        self.motor_info = None
        self.turbo_info = None
        self.len_counter = 8
        self.seq_counter2 = 0

        self.seq = 1

        self.device_info = None

    def log(self, *args):
        if self.debug:
            print(*args)

    # ----------------------s----------------------------
    # CRC
    # --------------------------------------------------

    def crc8(self, data):

        crc = 0

        for b in data:
            crc = N[crc ^ b]

        return crc

    # --------------------------------------------------
    # SEQUENCE
    # --------------------------------------------------

    def next_seq(self):

        seq = self.seq

        self.seq += 1

        if self.seq > 255:
            self.seq = 1

        return seq

    # --------------------------------------------------
    # ENCRYPT
    # --------------------------------------------------

    def encrypt(self, pkt):

        pkt = bytearray(pkt)

        out = bytearray(len(pkt))

        b0 = pkt[0]
        b2 = pkt[2]
        b3 = pkt[3]

        out[0] = (b0 ^ (((b2 + b3) - 154) & 0xFF)) & 0xFF
        out[1] = (pkt[1] ^ (((b2 + b3) + 155) & 0xFF)) & 0xFF
        out[2] = (((b2 - 173) & 0xFF) ^ b3) & 0xFF
        out[3] = (((b3 + 191) & 0xFF) ^ 219) & 0xFF

        key = (pkt[2] + pkt[3]) & 0xFF

        for i in range(4, len(pkt) - 1):
            out[i] = pkt[i] ^ ((key - O[i - 4]) & 0xFF)

        out[-1] = pkt[-1]

        offset = (out[3] & 2) * 10

        for i in range(len(out)):
            out[i] ^= P[(offset + i) % len(P)]

        return out

    # --------------------------------------------------
    # DECRYPT
    # --------------------------------------------------

    def decrypt(self, data):

        d = bytearray(data)

        idx = 20 if ((d[3] ^ P[3]) & 2) else 0

        for i in range(len(d)):
            d[i] ^= P[(idx + i) % len(P)]

        b = ((d[3] ^ 219) - 191) & 0xFF
        d[3] = b

        b2 = ((d[2] ^ b) + 173) & 0xFF
        d[2] = b2

        d[1] ^= ((b2 + b + 155) & 0xFF)
        d[0] ^= ((b2 + b - 154) & 0xFF)

        key = (d[2] + d[3]) & 0xFF

        for i in range(4, len(d) - 1):
            d[i] ^= ((key - O[i - 4]) & 0xFF)

        return d

    # --------------------------------------------------
    # DEVICE INFO PARSER
    # --------------------------------------------------
    def parse_device_info(self, packet):

        return DeviceInfo(
            id_a=f"{packet[4]:02X}{packet[5]:02X}",
            id_b=f"{packet[6]:02X}{packet[7]:02X}",
            version=f"{packet[8]:02X}.{packet[9]:02X}",
            flags=packet[10]
        )



    # --------------------------------------------------
    # MOTOR INFO PARSER
    # --------------------------------------------------

    def parse_motor(self, data):

        shutdown_raw = (
            data[5]
            | (data[6] << 8)
            | (data[7] << 16)
            | (data[8] << 24)
        )
        auto_shutdown_minutes = int(
            (shutdown_raw * 5) / 60000
        )
        return MotorConfig(
            motor1=data[1],
            motor2=data[2],
            motor3=data[3],
            motor4=data[4],
            auto_shutdown_minutes=auto_shutdown_minutes
        )
    
    # --------------------------------------------------
    # TURBO INFO PARSER
    # --------------------------------------------------
    def parse_turbo(self, data):

        return {
            "turbo_speed": data[1] * 10,
            "turbo_bits": data[4:7],
            "auto_bits": data[7:10]
        }
    # --------------------------------------------------
    # BLE
    # --------------------------------------------------

    async def connect(self):

        self.client = BleakClient(self.address)
        await self.client.connect()
        await self.client.start_notify(
            READ_UUID,
            self._on_notify
        )
        print(self.device_name, "connected.")

    async def disconnect(self):
        if self.client:
            await self.client.disconnect()
            print(self.device_name, "disconnected.")

    # --------------------------------------------------
    # RX CALLBACK
    # --------------------------------------------------

    def _on_notify(self, sender, data):

        dec = self.decrypt(data)
        payload = dec[4:-1]

        if len(dec) >= 11 and dec[0] == 0x19:
            if (
                dec[4] == 0x07 and
                dec[5] == 0x10 and
                dec[6] == 0x06 and
                dec[7] == 0x20
            ):
                self.device_info = self.parse_device_info(dec)
                print("\nDevice Info:")
                print(self.device_info)

        if len(payload) == 14 and payload[0] == 0x0D:
            self.turbo_info = self.parse_turbo(payload)
            self.log("Turbo:", self.turbo_info)

        if len(payload) == 9:
            self.motor_info = self.parse_motor(payload)
            self.log("Motor:", self.motor_info)

        self.last_packet = dec
        self.log("RX:", dec.hex())
        self.log("CMD :", f"{dec[0]:02X}")
        self.log("LEN :", f"{dec[1]:02X}")
        self.log("SEQ :", f"{dec[2]:02X}")
        self.log("VAL :", f"{dec[3]:02X}")
        self.log("DATA:", dec[4:-1].hex())
        self.log("CRC :", f"{dec[-1]:02X}")

    # --------------------------------------------------
    # SEND
    # --------------------------------------------------

    async def send_packet(self, packet):
        enc = self.encrypt(packet)
        self.log("TX:", enc.hex())
        await self.client.write_gatt_char(
            WRITE_UUID,
            enc,
            response=True
        )

    # --------------------------------------------------
    # CMD 145
    # --------------------------------------------------

    async def read_device_info(self):
        seq = self.next_seq()
        pkt = [
            0x91,
            0x05,
            seq,
            0x55
        ]
        pkt.append(
            self.crc8(pkt)
        )
        await self.send_packet(pkt)

    async def get_device_info(self):
        self.device_info = None
        await self.read_device_info()
        await asyncio.sleep(1)
        return self.device_info

    def build_read_cmd(self, cmd):
        seq = self.next_seq()
        pkt = [
            cmd,
            0x06,
            seq,
            0x55,
            0x00
        ]
        pkt.append(
            self.crc8(pkt)
        )
        return bytearray(pkt)

    async def read_command(self, cmd):
        pkt = self.build_read_cmd(cmd)
        await self.send_packet(pkt)

    async def read_rocker(self):
        await self.read_command(
            CMD_READ_ROCKER
        )


    async def read_trigger(self):
        await self.read_command(
            CMD_READ_TRIGGER
        )


    async def read_motor(self):
        await self.read_command(
            CMD_READ_MOTOR
        )


    async def read_turbo(self):
        await self.read_command(
            CMD_READ_TURBO
        )


    async def read_macro(self):
        await self.read_command(
            CMD_READ_MACRO
        )


    async def read_remap(self):
        await self.read_command(
            CMD_READ_REMAP
        )


    async def read_led(self):
        await self.read_command(
            CMD_READ_LED
        )

    async def get_motor(self):
        self.motor_info = None
        await self.read_motor()
        await asyncio.sleep(1)
        return self.motor_info

    async def get_turbo(self):
        self.turbo_info = None
        await self.read_turbo()
        await asyncio.sleep(1)
        return self.turbo_info

    def build_motor_payload(
        self,
        motor1,
        motor2,
        motor3,
        motor4,
        auto_shutdown_minutes=10
    ):

        shutdown_raw = int(
            (auto_shutdown_minutes * 60000) / 5
        )

        b0 = shutdown_raw & 0xFF
        b1 = (shutdown_raw >> 8) & 0xFF
        b2 = (shutdown_raw >> 16) & 0xFF
        b3 = (shutdown_raw >> 24) & 0xFF

        return [
            8,
            motor1,
            motor2,
            motor3,
            motor4,
            b0,
            b1,
            b2,
            b3
        ]

    def build_len(self, payload):
        if self.len_counter == 0:
            self.len_counter = 8
        self.len_counter -= 1
        return int(
            f"{self.len_counter % 8:03b}"
            f"{len(payload) + 5:05b}",
            2
        )

    def build_seq_field(self):
        self.seq_counter2 += 1
        value = self.seq_counter2
        return int(
            f"{value % 2}0000{value % 8:03b}",
            2
        )


    def build_write_motor_packet(
        self,
        motor1,
        motor2,
        motor3,
        motor4,
        auto_shutdown_minutes=10
    ):
        payload = self.build_motor_payload(
            motor1,
            motor2,
            motor3,
            motor4,
            auto_shutdown_minutes
        )
        packet = [
            51,
            self.build_len(payload),
            self.build_seq_field(),
            0x55,
        ]
        packet.extend(payload)
        packet.append(
            self.crc8(packet)
        )
        return bytearray(packet)    

    async def write_raw_packet(self, packet):
        enc = self.encrypt(packet)
        self.log("RAW:", packet.hex())
        self.log("ENC:", enc.hex())
        await self.client.write_gatt_char(
            WRITE_UUID,
            enc,
            response=True
        )

    async def set_motor(
        self,
        motor1,
        motor2,
        motor3,
        motor4,
        auto_shutdown_minutes=10
    ):

        packet = self.build_write_motor_packet(
            motor1,
            motor2,
            motor3,
            motor4,
            auto_shutdown_minutes
        )

        await self.write_raw_packet(packet)

    async def set_left_vibration(
        self,
        level
    ):
        motor = await self.get_motor()
        await self.set_motor(
            motor1=level,
            motor2=level,
            motor3=motor.motor3,
            motor4=motor.motor4,
            auto_shutdown_minutes=motor.auto_shutdown_minutes
        )

    async def set_right_vibration(
        self,
        level
    ):
        motor = await self.get_motor()
        await self.set_motor(
        motor1=motor.motor1,
            motor2=level,
            motor3=level,
            motor4=motor.motor4,
            auto_shutdown_minutes=motor.auto_shutdown_minutes
        )  

    async def set_vibration(self, level):
        if self.device_name is None:
            raise RuntimeError(
                "device_name não definido."
            )
        if "Joy-L" in self.device_name:
            await self.set_left_vibration(level)
        elif "Joy-R" in self.device_name:
            await self.set_right_vibration(level)
        else:
            raise RuntimeError(
                f"Modelo desconhecido: {self.device_name}"
            )
        await asyncio.sleep(1)
        motor = await self.get_motor()
        if "Joy-L" in self.device_name:
            print(
                f"Left vibration level: {motor.motor1}"
            )
        else:
            print(
                f"Right vibration level: {motor.motor2}"
            )
        return motor

    async def get_auto_shutdown(self):
        motor = await self.get_motor()
        return motor.auto_shutdown_minutes

    @staticmethod
    async def scan(timeout=5):
        devices = await BleakScanner.discover(timeout=timeout)
        results = []
        for device in devices:
            if device.name:
                results.append(
                    {
                        "name": device.name,
                        "address": device.address
                    }
                )
        return results

    @staticmethod
    async def find_controllers(family):
        devices = await Mobapad.scan()
        result = {
            "left": None,
            "right": None
        }
        if family == "S1":
            left_names = S1_LEFT_NAMES
            right_names = S1_RIGHT_NAMES
        elif family == "M6":
            left_names = M6_LEFT_NAMES
            right_names = M6_RIGHT_NAMES
        elif family == "M12":
            left_names = M12_LEFT_NAMES
            right_names = M12_RIGHT_NAMES
        else:
            raise RuntimeError(
                f"Unsupported family: {family}"
            )
        for dev in devices:
            name = dev.get("name")
            if name in left_names:
                result["left"] = dev
            elif name in right_names:
                result["right"] = dev
        return result

    @staticmethod
    async def connect_left(family):
        controllers = await Mobapad.find_controllers(
            family
        )
        if controllers["left"] is None:

            raise RuntimeError(
                f"{family} left controller not found."
            )
        ctl = Mobapad(
            controllers["left"]["address"]
        )
        ctl.device_name = controllers["left"]["name"]
        await ctl.connect()
        return ctl

    @staticmethod
    async def connect_right(family):
        controllers = await Mobapad.find_controllers(
            family
        )
        if controllers["right"] is None:
            raise RuntimeError(
                f"{family} right controller not found."
            )
        ctl = Mobapad(
            controllers["right"]["address"]
        )
        ctl.device_name = controllers["right"]["name"]
        await ctl.connect()
        return ctl

    async def get_led_raw(self):
        self.last_packet = None
        await self.read_led()
        await asyncio.sleep(1)
        return self.last_packet