#!/usr/bin/env python3
"""
物联网传感器主程序
负责传感器数据采集、华为云上报和蜂鸣器控制
"""

import paho.mqtt.client as mqtt
import time
import sys
import json
import traceback

# 导入配置
import config
# 导入传感器收集器
from sensor_collector import get_sensor_collector
# 导入蜂鸣器控制
from buzzer_control import get_buzzer

# ==============================================================================
# 全局变量
# ==============================================================================

CONNECTED_FLAG = False
COLLECTOR_INITIALIZED = False
SENSOR_COLLECTOR = None
BUZZER_CONTROLLER = None

# ==============================================================================
# 初始化函数
# ==============================================================================

def init_sensors():
    """初始化所有传感器和蜂鸣器"""
    global SENSOR_COLLECTOR, COLLECTOR_INITIALIZED, BUZZER_CONTROLLER
    
    print("=" * 60)
    print("初始化传感器系统...")
    print("=" * 60)
    
    try:
        # 初始化蜂鸣器
        BUZZER_CONTROLLER = get_buzzer()
        print("✓ 蜂鸣器初始化完成")
        
        # 初始化传感器
        SENSOR_COLLECTOR = get_sensor_collector()
        
        if SENSOR_COLLECTOR.initialized:
            print("✓ 所有传感器初始化完成")
            
            # 等待传感器预热
            print("\n等待传感器预热...")
            SENSOR_COLLECTOR.wait_for_warmup(10)
            
            # 预热后先读取一次测试
            print("\n预热后测试读取...")
            test_data = SENSOR_COLLECTOR.collect_multiple_readings(
                num_readings=3, 
                interval=0.5
            )
            
            if test_data and 'error_code' not in test_data:
                print("✓ 传感器测试成功")
                COLLECTOR_INITIALIZED = True
                return True
            else:
                print("✗ 传感器测试失败")
                return False
        else:
            print("✗ 传感器初始化失败")
            return False
            
    except Exception as e:
        print(f"✗ 传感器初始化异常: {e}")
        traceback.print_exc()
        return False

# ==============================================================================
# 数据采集和格式化函数
# ==============================================================================

def collect_all_data_and_format():
    """ 
    采集所有传感器数据（10次取平均），并封装成华为云要求的格式
    """
    if not COLLECTOR_INITIALIZED:
        print("传感器未初始化，无法采集数据")
        return json.dumps({"error": "sensors_not_initialized"})
    
    try:
        # 采集10次数据取平均
        print("\n" + "=" * 40)
        print("开始采集传感器数据（10次取平均）...")
        
        sensor_data = SENSOR_COLLECTOR.collect_multiple_readings(
            num_readings=10, 
            interval=1.0  # 每秒读取一次
        )
        
        print(f"数据采集完成，共 {sensor_data.get('samples_count', 0)} 次有效读数")
        print("=" * 40 + "\n")
        
        if not sensor_data or 'error_code' in sensor_data:
            print("警告: 未采集到有效数据")
            return json.dumps({"error": "no_data_collected"})
        
        # 打印采集到的数据
        print("采集到的传感器数据:")
        for key, value in sensor_data.items():
            if key not in ['timestamp', 'samples_count']:
                print(f"  {key}: {value}")
        
        # 封装成华为云要求的格式
        return format_data_for_huaweicloud(sensor_data)
        
    except Exception as e:
        print(f"数据采集失败: {e}")
        traceback.print_exc()
        return json.dumps({"error": str(e)})

def format_data_for_huaweicloud(sensor_data: dict) -> str:
    """
    将传感器数据格式化为华为云要求的JSON格式 - 数字版本
    """
    # 提取数字数据
    temperature = sensor_data.get('temperature', 0.0)
    humidity = sensor_data.get('humidity', 0.0)
    pressure = sensor_data.get('pressure', 1013.25)
    altitude = sensor_data.get('altitude', 0.0)
    
    # 空气质量数据
    aqi = sensor_data.get('aqi', 0)
    tvoc = sensor_data.get('tvoc', 0)
    eco2 = sensor_data.get('eco2', 0)
    
    # MQ-2气体传感器数据
    mq2_adc = sensor_data.get('mq2_adc', 0)
    mq2_voltage = sensor_data.get('mq2_voltage', 0.0)
    mq2_status = sensor_data.get('mq2_status', 0)  # 数字状态
    
    # 系统信息
    temperature_source = sensor_data.get('temperature_source', 0)  # 0=AHT21, 1=BMP280
    data_source = sensor_data.get('data_source', 0)  # 0=单次读取, 1=平均值
    samples_count = sensor_data.get('samples_count', 0)
    reading_count = sensor_data.get('reading_count', 0)
    timestamp = sensor_data.get('timestamp', time.time())
    
    # 构建华为云格式 - 使用数字版本
    # 注意：这里的service_id和property_name需要与华为云平台上的产品模型完全一致
    huawei_format = {
        "services": [
            {
                "service_id": "EnvironmentData",
                "properties": {
                    "temperature": round(temperature, 2),
                    "humidity": round(humidity, 2),
                    "pressure": round(pressure, 2),
                    "altitude": round(altitude, 2),
                    "temperature_source": temperature_source,
                    "timestamp": timestamp
                }
            },
            {
                "service_id": "AirQuality",
                "properties": {
                    "aqi": aqi,
                    "tvoc": round(tvoc, 2),
                    "eco2": eco2,
                    "timestamp": timestamp
                }
            },
            {
                "service_id": "Gas",
                "properties": {
                    "mq2_adc": round(mq2_adc, 2),
                    "mq2_voltage": round(mq2_voltage, 3),
                    "mq2_status": mq2_status,
                    "timestamp": timestamp
                }
            },
            {
                "service_id": "SystemInfo",
                "properties": {
                    "data_source": data_source,
                    "samples_count": samples_count,
                    "reading_count": reading_count,
                    "timestamp": timestamp
                }
            }
        ]
    }
    
    return json.dumps(huawei_format, ensure_ascii=False)

# ==============================================================================
# MQTT回调函数
# ==============================================================================

def on_connect(client, userdata, flags, rc, properties): 
    global CONNECTED_FLAG
    if rc == 0:
        CONNECTED_FLAG = True
        print(f"✅ MQTT Broker 连接成功！(RC: {rc})")
        
        # 订阅命令下发 Topic
        command_topic = f'$oc/devices/{config.RAW_DEVICE_ID}/sys/commands/#'
        client.subscribe(command_topic, qos=1)
        print(f"✅ 订阅命令主题: {command_topic}")

        # 订阅默认消息下发 Topic
        message_topic = f'$oc/devices/{config.RAW_DEVICE_ID}/sys/messages/down'
        client.subscribe(message_topic, qos=1)
        print(f"✅ 订阅消息主题: {message_topic}")
        
        # 订阅属性设置Topic（如果需要）
        properties_topic = f'$oc/devices/{config.RAW_DEVICE_ID}/sys/properties/set/#'
        client.subscribe(properties_topic, qos=1)
        print(f"✅ 订阅属性设置主题: {properties_topic}")
    else:
        print(f"❌ 连接失败，返回码: {rc}")

def on_message(client, userdata, msg):
    """ 收到平台下发消息时的回调 """
    print("\n" + "="*60)
    print(f"📥 收到下行消息！")
    print(f"Topic: {msg.topic}")
    
    try:
        payload_str = msg.payload.decode('utf-8')
        print(f"Payload: {payload_str}")
        
        # 尝试解析JSON
        try:
            payload_json = json.loads(payload_str)
            print(f"JSON解析成功: {payload_json}")
        except:
            print("Payload不是JSON格式")
            
    except Exception as e:
        print(f"Payload (原始字节): {msg.payload}")
        print(f"解析错误: {e}")
    
    print("-" * 60)
    
    # 触发蜂鸣器响一分钟
    if BUZZER_CONTROLLER:
        print("🚨 触发蜂鸣器响一分钟...")
        BUZZER_CONTROLLER.start_buzzing(duration_seconds=60)
        print(f"蜂鸣器状态: {'正在响' if BUZZER_CONTROLLER.is_buzzing() else '已停止'}")
    else:
        print("⚠️ 蜂鸣器未初始化")
    
    print("="*60 + "\n")

def on_disconnect(client, userdata, rc):
    global CONNECTED_FLAG
    CONNECTED_FLAG = False
    print(f"🔌 连接已断开，返回码: {rc}")

def on_publish(client, userdata, mid, reason_code, properties):
    print(f"⬆️ 数据上报队列成功，消息 ID: {mid}") 

# ==============================================================================
# 清理函数
# ==============================================================================

def cleanup():
    """清理函数"""
    global SENSOR_COLLECTOR, BUZZER_CONTROLLER, CONNECTED_FLAG
    
    print("\n" + "="*60)
    print("开始清理资源...")
    
    # 关闭蜂鸣器
    if BUZZER_CONTROLLER:
        try:
            BUZZER_CONTROLLER.cleanup()
            print("✓ 蜂鸣器已关闭")
        except Exception as e:
            print(f"✗ 关闭蜂鸣器失败: {e}")
    
    # 关闭传感器
    if SENSOR_COLLECTOR:
        try:
            SENSOR_COLLECTOR.close()
            print("✓ 传感器已关闭")
        except Exception as e:
            print(f"✗ 关闭传感器失败: {e}")
    
    print("清理完成")
    print("="*60)

# ==============================================================================
# 主函数
# ==============================================================================

def IotDevice_main():
    """主连接和上报函数"""
    global COLLECTOR_INITIALIZED, SENSOR_COLLECTOR, CONNECTED_FLAG, BUZZER_CONTROLLER
    
    # 初始化传感器和蜂鸣器
    if not init_sensors():
        print("传感器初始化失败，程序退出")
        return
    
    # 创建MQTT客户端
    client = None
    try:
        client = mqtt.Client(
            client_id=config.CLIENT_ID_AUTH, 
            protocol=mqtt.MQTTv311,
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2 
        )

        client.username_pw_set(username=config.USERNAME_AUTH, password=config.PASSWORD_AUTH)
        
        client.on_connect = on_connect
        client.on_disconnect = on_disconnect
        client.on_publish = on_publish 
        client.on_message = on_message  # 设置消息回调函数
        
        try:
            client.tls_set(ca_certs=config.IOT_CA_CERT_PATH) 
            print(f"✓ 证书加载成功: {config.IOT_CA_CERT_PATH}")
        except FileNotFoundError:
            print(f"❌ 证书文件未找到！请检查路径: {config.IOT_CA_CERT_PATH}")
            cleanup()
            sys.exit(1)
        except Exception as e:
            print(f"❌ 证书加载失败: {e}")
            cleanup()
            sys.exit(1)

        print(f"\n🚀 尝试连接到华为云 IoTDA: ssl://{config.SERVER_URI}:{config.PORT}")
        client.connect(config.SERVER_URI, config.PORT, config.KEEP_ALIVE_INTERVAL)

        client.loop_start()

        # 等待连接建立
        timeout = 30
        while not CONNECTED_FLAG and timeout > 0:
            print(f"等待连接建立... {timeout}秒")
            time.sleep(1)
            timeout -= 1
        
        if not CONNECTED_FLAG:
            print("连接超时")
            cleanup()
            return

        # 主循环
        report_count = 0
        while True:
            if CONNECTED_FLAG:
                # 采集并上报数据
                report_count += 1
                print(f"\n📊 第 {report_count} 次数据上报...")
                
                payload = collect_all_data_and_format()
                
                # 检查是否有错误
                if "error" not in payload:
                    result = client.publish(config.REPORT_TOPIC, payload, qos=0)
                    
                    if result.rc == mqtt.MQTT_ERR_SUCCESS:
                        print(f"✅ 成功上报数据到华为云")
                    else:
                        print(f"❌ 发布数据失败，错误码: {result.rc}")
                else:
                    print(f"⚠️ 跳过上报: {payload}")

                # 等待下一次上报
                print(f"⏳ 等待 {config.REPORT_INTERVAL} 秒后下次上报...")
                time.sleep(config.REPORT_INTERVAL)
            else:
                print("连接断开，等待重连...")
                time.sleep(5)
                
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"\n程序异常: {e}")
        traceback.print_exc()
    finally:
        print("\n正在停止程序...")
        # 安全关闭
        if client:
            try:
                client.loop_stop()
                # 等待一小段时间确保循环停止
                time.sleep(1)
                
                if CONNECTED_FLAG:
                    client.disconnect()
                    print("✓ MQTT连接已断开")
            except Exception as e:
                print(f"断开MQTT连接时出错: {e}")
        
        cleanup()
        print("程序已完全停止")

# ==============================================================================
# 程序入口
# ==============================================================================

if __name__ == "__main__":
    IotDevice_main()