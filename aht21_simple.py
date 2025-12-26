#!/usr/bin/env python3
"""
简化版AHT21驱动 - 数字版本
"""

import time
import smbus2

class AHT21_Reliable:
    def __init__(self, bus=1, address=0x38):
        self.address = address
        self.bus = smbus2.SMBus(bus)
        
        # 初始化
        try:
            self.bus.write_byte(self.address, 0xBA)
            time.sleep(0.02)
            self.bus.write_i2c_block_data(self.address, 0xBE, [0x08, 0x00])
            time.sleep(0.01)
            print(f"找到AHT21 (地址: 0x{self.address:02X})")
        except:
            raise RuntimeError("未检测到AHT21")
    
    def read(self):
        """读取温湿度，返回数字"""
        try:
            self.bus.write_i2c_block_data(self.address, 0xAC, [0x33, 0x00])
            time.sleep(0.08)
            data = self.bus.read_i2c_block_data(self.address, 0, 6)
            
            humidity_raw = ((data[1] << 12) | (data[2] << 4) | (data[3] >> 4))
            humidity = (humidity_raw / 1048576.0) * 100.0
            
            temperature_raw = (((data[3] & 0x0F) << 16) | (data[4] << 8) | data[5])
            temperature = (temperature_raw / 1048576.0) * 200.0 - 50.0
            
            if (0 <= humidity <= 100) and (-40 <= temperature <= 85):
                return round(humidity, 1), round(temperature, 1)
            else:
                return None, None
        except:
            return None, None
    
    def close(self):
        self.bus.close()