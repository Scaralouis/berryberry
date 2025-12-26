#!/usr/bin/env python3
"""
简化版MQ-2驱动 - 数字版本
"""

import time
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

class SimpleMQ2:
    def __init__(self, i2c_address=0x49):
        self.i2c = busio.I2C(board.SCL, board.SDA)
        self.ads = ADS.ADS1115(self.i2c, address=i2c_address)
        self.ads.gain = 2/3
        self.channel = AnalogIn(self.ads, 0)
    
    def read(self):
        """读取MQ-2数据，返回数字形式"""
        adc_value = self.channel.value
        voltage = self.channel.voltage
        
        # 根据电压判断状态，返回数字等级
        # 0:正常, 1:低浓度, 2:中浓度, 3:高浓度
        if voltage < 0.5:
            status = 0
        elif voltage < 0.8:
            status = 1
        elif voltage < 1.2:
            status = 2
        else:
            status = 3
        
        return {
            'adc': adc_value,
            'voltage': round(voltage, 3),
            'status': status
        }
    
    def close(self):
        """ADS1115没有close方法，但保留接口"""
        pass