#!/usr/bin/env python3
"""
蜂鸣器控制模块 - 数字版本
用于有源蜂鸣器（低电平触发）
"""

import threading
import time
import RPi.GPIO as GPIO

class BuzzerController:
    """蜂鸣器控制器"""
    
    def __init__(self, gpio_pin=18):
        """
        初始化蜂鸣器控制器
        
        Args:
            gpio_pin: 控制蜂鸣器的GPIO引脚编号 (BCM模式)
        """
        self.gpio_pin = gpio_pin
        self.buzzing = False
        self.timer = None
        
        # 设置GPIO模式为BCM
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # 设置引脚为输出模式
        GPIO.setup(self.gpio_pin, GPIO.OUT)
        
        # 初始状态：高电平，蜂鸣器不响
        GPIO.output(self.gpio_pin, GPIO.HIGH)
        
        print(f"蜂鸣器初始化完成 (GPIO {self.gpio_pin})")
    
    def start_buzzing(self, duration_seconds=60):
        """
        启动蜂鸣器
        
        Args:
            duration_seconds: 蜂鸣持续时间（秒）
        """
        # 如果蜂鸣器已经在响，先停止之前的
        if self.buzzing:
            self.stop_buzzing()
        
        print(f"蜂鸣器启动，将持续 {duration_seconds} 秒")
        
        # 启动蜂鸣器（低电平触发）
        GPIO.output(self.gpio_pin, GPIO.LOW)
        self.buzzing = True
        
        # 设置定时器，在指定时间后自动停止
        self.timer = threading.Timer(duration_seconds, self.stop_buzzing)
        self.timer.start()
    
    def stop_buzzing(self):
        """停止蜂鸣器"""
        if self.buzzing:
            print("蜂鸣器停止")
            GPIO.output(self.gpio_pin, GPIO.HIGH)
            self.buzzing = False
        
        # 取消定时器
        if self.timer and self.timer.is_alive():
            self.timer.cancel()
    
    def cleanup(self):
        """清理GPIO资源"""
        self.stop_buzzing()
        GPIO.cleanup(self.gpio_pin)
        print("蜂鸣器资源已清理")
    
    def is_buzzing(self):
        """检查蜂鸣器是否在响"""
        return self.buzzing
    
    def __del__(self):
        """析构函数"""
        try:
            self.cleanup()
        except:
            pass


# 全局蜂鸣器实例
_buzzer_instance = None

def get_buzzer() -> BuzzerController:
    """获取蜂鸣器实例（单例模式）"""
    global _buzzer_instance
    if _buzzer_instance is None:
        _buzzer_instance = BuzzerController(gpio_pin=18)  # 默认使用GPIO18
    return _buzzer_instance