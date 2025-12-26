#!/usr/bin/env python3
"""
简化版BMP280驱动 - 数字版本
返回温度和气压，海拔通过气压计算
"""

import time
import smbus2

class SimpleBMP280:
    def __init__(self, bus=1, address=0x76):
        self.bus = smbus2.SMBus(bus)
        self.address = address
        self.t_fine = 0
        
        # 检测传感器
        try:
            chip_id = self.bus.read_byte_data(self.address, 0xD0)
            if chip_id == 0x58:
                print(f"找到BMP280 (地址: 0x{self.address:02X})")
            else:
                # 尝试另一个地址
                self.address = 0x77
                chip_id = self.bus.read_byte_data(self.address, 0xD0)
                if chip_id != 0x58:
                    raise RuntimeError("无效的芯片ID")
                print(f"找到BMP280 (地址: 0x{self.address:02X})")
        except Exception as e:
            raise RuntimeError(f"检测BMP280失败: {e}")
        
        # 读取校准数据
        self._read_calibration()
        
        # 配置传感器
        self._configure()
    
    def _read_calibration(self):
        """读取校准数据"""
        self.dig_T1 = self._read_unsigned_short(0x88)
        self.dig_T2 = self._read_signed_short(0x8A)
        self.dig_T3 = self._read_signed_short(0x8C)
        
        self.dig_P1 = self._read_unsigned_short(0x8E)
        self.dig_P2 = self._read_signed_short(0x90)
        self.dig_P3 = self._read_signed_short(0x92)
        self.dig_P4 = self._read_signed_short(0x94)
        self.dig_P5 = self._read_signed_short(0x96)
        self.dig_P6 = self._read_signed_short(0x98)
        self.dig_P7 = self._read_signed_short(0x9A)
        self.dig_P8 = self._read_signed_short(0x9C)
        self.dig_P9 = self._read_signed_short(0x9E)
    
    def _read_unsigned_short(self, reg):
        """读取无符号16位整数 (小端序)"""
        data = self.bus.read_i2c_block_data(self.address, reg, 2)
        return data[0] + (data[1] << 8)
    
    def _read_signed_short(self, reg):
        """读取有符号16位整数 (小端序)"""
        data = self.bus.read_i2c_block_data(self.address, reg, 2)
        value = data[0] + (data[1] << 8)
        if value > 32767:
            value -= 65536
        return value
    
    def _configure(self):
        """配置传感器"""
        # 控制寄存器: 温度过采样x2，气压过采样x4，正常模式 (0x67)
        self.bus.write_byte_data(self.address, 0xF4, 0x67)
        time.sleep(0.01)
        
        # 配置寄存器: IIR滤波器x4 (0x10)
        self.bus.write_byte_data(self.address, 0xF5, 0x10)
        time.sleep(0.01)
    
    def _read_raw_data(self):
        """读取原始传感器数据"""
        # 等待数据就绪
        time.sleep(0.005)
        
        # 读取6个字节的数据
        data = self.bus.read_i2c_block_data(self.address, 0xF7, 6)
        
        # 气压数据 (20位)
        press_raw = (data[0] << 12) | (data[1] << 4) | (data[2] >> 4)
        
        # 温度数据 (20位)
        temp_raw = (data[3] << 12) | (data[4] << 4) | (data[5] >> 4)
        
        return temp_raw, press_raw
    
    def _compensate_temperature(self, temp_raw):
        """温度补偿计算"""
        var1 = (((temp_raw >> 3) - (self.dig_T1 << 1)) * self.dig_T2) >> 11
        var2 = (((((temp_raw >> 4) - self.dig_T1) * ((temp_raw >> 4) - self.dig_T1)) >> 12) * self.dig_T3) >> 14
        self.t_fine = var1 + var2
        temperature = (self.t_fine * 5 + 128) >> 8
        return temperature / 100.0
    
    def _compensate_pressure(self, press_raw):
        """气压补偿计算"""
        var1 = self.t_fine - 128000
        var2 = var1 * var1 * self.dig_P6
        var2 = var2 + ((var1 * self.dig_P5) << 17)
        var2 = var2 + (self.dig_P4 << 35)
        var1 = ((var1 * var1 * self.dig_P3) >> 8) + ((var1 * self.dig_P2) << 12)
        var1 = ((1 << 47) + var1) * self.dig_P1 >> 33
        
        if var1 == 0:
            return None
        
        p = 1048576 - press_raw
        p = (((p << 31) - var2) * 3125) // var1
        var1 = (self.dig_P9 * (p >> 13) * (p >> 13)) >> 25
        var2 = (self.dig_P8 * p) >> 19
        p = ((p + var1 + var2) >> 8) + (self.dig_P7 << 4)
        
        return p / 25600.0
    
    def read(self):
        """读取温度和气压"""
        try:
            temp_raw, press_raw = self._read_raw_data()
            
            if temp_raw is None or press_raw is None:
                return None, None
            
            temperature = self._compensate_temperature(temp_raw)
            if temperature is None:
                return None, None
            
            pressure = self._compensate_pressure(press_raw)
            if pressure is None:
                return None, None
            
            return round(temperature, 2), round(pressure, 2)
            
        except Exception as e:
            print(f"BMP280读取失败: {e}")
            return None, None
    
    def close(self):
        """关闭连接"""
        try:
            self.bus.close()
        except:
            pass