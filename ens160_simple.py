#!/usr/bin/env python3
"""
简化版ENS160驱动 - 数字版本
"""

import time
import smbus2

class SimpleENS160:
    def __init__(self, bus=1, address=0x52):
        self.bus = smbus2.SMBus(bus)
        self.address = address
        
        # 检测传感器
        try:
            data = self.bus.read_i2c_block_data(self.address, 0x00, 2)
            part_id = data[0] + (data[1] << 8)
            if part_id == 0x0160:
                print(f"找到ENS160 (地址: 0x{self.address:02X})")
            else:
                raise RuntimeError("无效的部件ID")
        except:
            raise RuntimeError("未检测到ENS160")
        
        # 配置
        self.bus.write_byte_data(self.address, 0x10, 0xF0)
        time.sleep(0.1)
        self.bus.write_byte_data(self.address, 0x10, 0x02)
        time.sleep(0.5)
    
    def set_environment(self, temperature=25.0, humidity=50.0):
        """设置环境补偿"""
        try:
            temp_k = int((temperature + 273.15) * 64)
            self._write_word(0x13, temp_k)
            
            rh_fraction = int((humidity / 100.0) * 512)
            self._write_word(0x15, rh_fraction)
            return True
        except:
            return False
    
    def read(self):
        """读取空气质量数据，返回数字形式"""
        try:
            # 读取AQI
            aqi = self.bus.read_byte_data(self.address, 0x21)
            
            # 读取TVOC
            tvoc_data = self.bus.read_i2c_block_data(self.address, 0x22, 2)
            tvoc = tvoc_data[0] + (tvoc_data[1] << 8)
            
            # 读取eCO2
            eco2_data = self.bus.read_i2c_block_data(self.address, 0x24, 2)
            eco2 = eco2_data[0] + (eco2_data[1] << 8)
            
            # AQI描述转换为数字等级 (1-5)
            aqi_desc_num = aqi  # ENS160的AQI已经是1-5的数字
            
            return {
                'aqi': aqi,
                'aqi_desc': aqi_desc_num,  # 这里实际上就是aqi，但为了兼容性保留
                'tvoc_ppb': tvoc,
                'eco2_ppm': eco2
            }
        except:
            return None
    
    def _write_word(self, reg, value):
        """写入16位数据"""
        low = value & 0xFF
        high = (value >> 8) & 0xFF
        self.bus.write_i2c_block_data(self.address, reg, [low, high])
    
    def close(self):
        self.bus.close()