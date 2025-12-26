#!/usr/bin/env python3
"""
传感器数据采集模块 - 数字版本
统一管理BMP280、MQ-2、ENS160、AHT21四个传感器
所有数据都以数字形式表示
"""

import time
import statistics
from typing import Dict, Optional
import threading

# 导入传感器驱动
try:
    from bmp280_simple import SimpleBMP280 
    BMP280_AVAILABLE = True
except ImportError:
    BMP280_AVAILABLE = False
    print("警告: BMP280驱动不可用")

try:
    from mq2_simple import SimpleMQ2
    MQ2_AVAILABLE = True
except ImportError:
    MQ2_AVAILABLE = False
    print("警告: MQ-2驱动不可用")

try:
    from ens160_simple import SimpleENS160
    ENS160_AVAILABLE = True
except ImportError:
    ENS160_AVAILABLE = False
    print("警告: ENS160驱动不可用")

try:
    from aht21_simple import AHT21_Reliable
    AHT21_AVAILABLE = True
except ImportError:
    AHT21_AVAILABLE = False
    print("警告: AHT21驱动不可用")


def calculate_altitude(pressure_hpa: float, sea_level_pressure: float = 1013.25) -> float:
    """
    根据气压计算海拔高度
    """
    if pressure_hpa <= 0:
        return 0.0
    
    try:
        altitude = 44330 * (1.0 - (pressure_hpa / sea_level_pressure) ** 0.1903)
        return round(altitude, 2)
    except (ValueError, ZeroDivisionError):
        return 0.0


class SensorCollector:
    """传感器数据收集器 - 数字版本"""
    
    def __init__(self):
        """初始化所有传感器"""
        self.sensors = {}
        self.reading_count = 0
        self.initialized = False
        self.lock = threading.Lock()
        
        self.init_success = {
            'bmp280': False,
            'mq2': False,
            'ens160': False,
            'aht21': False
        }
        
        self._init_all_sensors()
    
    def _init_all_sensors(self):
        """初始化所有传感器"""
        print("=" * 60)
        print("正在初始化所有传感器...")
        print("=" * 60)
        
        start_time = time.time()
        
        # 1. 初始化AHT21
        if AHT21_AVAILABLE:
            try:
                print(f"正在初始化AHT21...")
                self.sensors['aht21'] = AHT21_Reliable()
                self.init_success['aht21'] = True
                print(f"  ✓ AHT21初始化成功")
            except Exception as e:
                print(f"  ✗ AHT21初始化失败: {e}")
        
        # 2. 初始化BMP280
        if BMP280_AVAILABLE:
            try:
                print(f"正在初始化BMP280...")
                try:
                    self.sensors['bmp280'] = SimpleBMP280(address=0x76)
                    self.init_success['bmp280'] = True
                    print(f"  ✓ BMP280初始化成功 (地址: 0x76)")
                except Exception as e1:
                    try:
                        self.sensors['bmp280'] = SimpleBMP280(address=0x77)
                        self.init_success['bmp280'] = True
                        print(f"  ✓ BMP280初始化成功 (地址: 0x77)")
                    except Exception as e2:
                        print(f"  ✗ BMP280初始化失败")
            except Exception as e:
                print(f"  ✗ BMP280初始化失败: {e}")
        
        # 3. 初始化ENS160
        if ENS160_AVAILABLE:
            try:
                print(f"正在初始化ENS160...")
                self.sensors['ens160'] = SimpleENS160()
                self.init_success['ens160'] = True
                print(f"  ✓ ENS160初始化成功")
                
                if self.init_success['aht21']:
                    try:
                        for _ in range(3):
                            humidity, temperature = self.sensors['aht21'].read()
                            if humidity is not None and temperature is not None:
                                success = self.sensors['ens160'].set_environment(
                                    temperature=temperature, 
                                    humidity=humidity
                                )
                                if success:
                                    print(f"  ✓ ENS160环境补偿设置成功")
                                    break
                            time.sleep(0.5)
                    except Exception as e:
                        print(f"  ! ENS160环境补偿设置失败: {e}")
                    
            except Exception as e:
                print(f"  ✗ ENS160初始化失败: {e}")
        
        # 4. 初始化MQ-2
        if MQ2_AVAILABLE:
            try:
                print(f"正在初始化MQ-2...")
                self.sensors['mq2'] = SimpleMQ2()
                self.init_success['mq2'] = True
                print(f"  ✓ MQ-2初始化成功")
            except Exception as e:
                print(f"  ✗ MQ-2初始化失败: {e}")
        
        elapsed_time = time.time() - start_time
        print("\n" + "=" * 60)
        
        successful_sensors = sum(1 for status in self.init_success.values() if status)
        if successful_sensors > 0:
            self.initialized = True
            print(f"✓ 传感器系统初始化完成 ({successful_sensors}/4个传感器就绪)")
            print(f"初始化耗时: {elapsed_time:.1f}秒")
        else:
            self.initialized = False
            print("✗ 传感器系统初始化失败")
        
        print("=" * 60)
    
    def read_single_measurement(self) -> Optional[Dict]:
        """读取一次所有传感器的数据"""
        data = {}
        
        # 读取AHT21
        if self.init_success['aht21']:
            try:
                humidity, temperature = self.sensors['aht21'].read()
                if humidity is not None and temperature is not None:
                    data['temperature_aht'] = temperature
                    data['humidity'] = humidity
                else:
                    print("  ! AHT21读取失败")
            except Exception as e:
                print(f"  ! AHT21读取错误: {e}")
        
        # 读取BMP280
        if self.init_success['bmp280']:
            try:
                temp_bmp, pressure = self.sensors['bmp280'].read()
                if temp_bmp is not None and pressure is not None:
                    data['temperature_bmp'] = temp_bmp
                    data['pressure'] = pressure
                    altitude = calculate_altitude(pressure)
                    data['altitude'] = altitude
                    print(f"  BMP280: 气压={pressure:.2f}, 海拔={altitude:.2f}")
                else:
                    print("  ! BMP280读取失败")
            except Exception as e:
                print(f"  ! BMP280读取错误: {e}")
        
        # 读取ENS160
        if self.init_success['ens160']:
            try:
                ens_data = self.sensors['ens160'].read()
                if ens_data:
                    data['aqi'] = ens_data['aqi']
                    data['tvoc'] = ens_data['tvoc_ppb']
                    data['eco2'] = ens_data['eco2_ppm']
                else:
                    print("  ! ENS160读取失败")
            except Exception as e:
                print(f"  ! ENS160读取错误: {e}")
        
        # 读取MQ-2
        if self.init_success['mq2']:
            try:
                mq2_data = self.sensors['mq2'].read()
                if mq2_data:
                    data['mq2_adc'] = mq2_data['adc']
                    data['mq2_voltage'] = mq2_data['voltage']
                    data['mq2_status'] = mq2_data['status']  # 已经是数字
                else:
                    print("  ! MQ-2读取失败")
            except Exception as e:
                print(f"  ! MQ-2读取错误: {e}")
        
        if data:
            data['timestamp'] = time.time()
            data['reading_count'] = self.reading_count
            self.reading_count += 1
            
            # 确定最终温度值
            if 'temperature_aht' in data:
                data['temperature'] = data['temperature_aht']
                data['temperature_source'] = 0  # AHT21
            elif 'temperature_bmp' in data:
                data['temperature'] = data['temperature_bmp']
                data['temperature_source'] = 1  # BMP280
            
            # 移除临时字段
            data.pop('temperature_aht', None)
            data.pop('temperature_bmp', None)
            
            # 设置数据源标记
            data['data_source'] = 0  # 0表示单次读取
            
            return data
        else:
            print("  ! 所有传感器读取失败")
            return None
    
    def collect_multiple_readings(self, num_readings: int = 10, interval: float = 1.0) -> Dict:
        """
        收集多次读数并计算平均值
        """
        all_readings = []
        
        print(f"\n开始收集 {num_readings} 次读数，间隔 {interval} 秒...")
        
        for i in range(num_readings):
            print(f"  读取 {i+1}/{num_readings}...", end='')
            
            try:
                data = self.read_single_measurement()
                
                if data:
                    all_readings.append(data)
                    print(" ✓")
                    print(f"    温度: {data.get('temperature', 0):.2f}, 湿度: {data.get('humidity', 0):.2f}, AQI: {data.get('aqi', 0)}")
                else:
                    print(" ✗")
                    
            except Exception as e:
                print(f" ✗ {e}")
            
            if i < num_readings - 1:
                time.sleep(interval)
        
        if not all_readings:
            print("错误: 没有读取到有效数据")
            return {
                'error_code': 1,
                'timestamp': time.time(),
                'samples_count': 0
            }
        
        averaged_data = self._calculate_averages(all_readings)
        
        print(f"\n数据收集完成，共 {len(all_readings)} 次有效读数")
        return averaged_data
    
    def _calculate_averages(self, readings: list) -> Dict:
        """计算多次读数的平均值"""
        if not readings:
            return {}
        
        result = {
            'timestamp': time.time(),
            'samples_count': len(readings),
            'data_source': 1  # 1表示平均值
        }
        
        numeric_fields = {}
        last_reading = readings[-1] if readings else {}
        
        for reading in readings:
            for key, value in reading.items():
                if isinstance(value, (int, float)):
                    if key not in numeric_fields:
                        numeric_fields[key] = []
                    numeric_fields[key].append(value)
        
        # 连续数值字段计算平均值
        for key, values in numeric_fields.items():
            if len(values) > 0:
                # 特殊处理：离散值取最后一次
                if key in ['aqi', 'mq2_status', 'temperature_source']:
                    result[key] = last_reading.get(key, 0)
                else:
                    try:
                        result[key] = round(statistics.mean(values), 2)
                    except:
                        result[key] = round(sum(values) / len(values), 2)
        
        # 重新计算海拔（基于平均气压）
        if 'pressure' in result:
            result['altitude'] = calculate_altitude(result['pressure'])
        
        return result
    
    def wait_for_warmup(self, warmup_seconds: int = 10):
        """等待传感器预热"""
        print(f"\n等待传感器预热 {warmup_seconds} 秒...")
        
        for i in range(warmup_seconds, 0, -1):
            if i % 5 == 0 or i <= 3:
                print(f"  {i}秒...")
            else:
                print(f"  {i}秒...", end='\r')
            time.sleep(1)
        
        print("传感器预热完成")
    
    def get_sensor_status(self) -> Dict:
        """获取传感器状态信息"""
        return {
            'initialized': 1 if self.initialized else 0,
            'sensor_status': {
                'bmp280': 1 if self.init_success['bmp280'] else 0,
                'mq2': 1 if self.init_success['mq2'] else 0,
                'ens160': 1 if self.init_success['ens160'] else 0,
                'aht21': 1 if self.init_success['aht21'] else 0
            },
            'total_readings': self.reading_count,
            'timestamp': time.time()
        }
    
    def close(self):
        """关闭所有传感器连接"""
        print("\n正在关闭传感器连接...")
        
        closed_count = 0
        for name, sensor in self.sensors.items():
            try:
                if hasattr(sensor, 'close'):
                    sensor.close()
                    closed_count += 1
            except:
                pass
        
        print(f"传感器关闭完成 ({closed_count}/{len(self.sensors)}个已关闭)")
        self.initialized = False
        self.sensors.clear()
    
    def __del__(self):
        """析构函数"""
        try:
            if self.initialized:
                self.close()
        except:
            pass


# 单例实例
_collector_instance = None

def get_sensor_collector() -> SensorCollector:
    """获取传感器收集器实例（单例模式）"""
    global _collector_instance
    if _collector_instance is None:
        _collector_instance = SensorCollector()
    return _collector_instance