# ==============================================================================
# config.py: 存储所有配置参数
# ==============================================================================

# MQTT Broker 配置
SERVER_URI = "434118086a.st1.iotda-device.cn-north-4.myhuaweicloud.com" 
PORT = 8883
KEEP_ALIVE_INTERVAL = 60
IOT_CA_CERT_PATH = "/home/user/iot_project/root.pem" 

# 设备和认证凭证 (请使用你当前成功的参数)
RAW_DEVICE_ID = "692ecab7f69b1239b084578e_SmokeDetector_001" 
USERNAME_AUTH = RAW_DEVICE_ID
CLIENT_ID_AUTH = "692ecab7f69b1239b084578e_SmokeDetector_001_0_0_2025120307" 
PASSWORD_AUTH = "da30065c9bd59bd49221839f572a69ab7b15abd1502c501544aab489fd8c6c7e"

# 华为云规定的属性上报主题
REPORT_TOPIC = f"$oc/devices/{RAW_DEVICE_ID}/sys/properties/report"

# 上报间隔 (秒)
REPORT_INTERVAL = 30