"""方太洗碗机集成常量。"""

DOMAIN = "fotile_dishwasher"

BASE_URL = "https://api.fotile.com"
ROUTE_URL = f"{BASE_URL}/iot-mqttManager/routeService"
SHADOW_URL = f"{BASE_URL}/v2/device/batchQueryShadow"
DEVICES_URL = f"{BASE_URL}/v2/home/{{home_id}}/devices"
REFRESH_URL = f"{BASE_URL}/v2/user/token/refresh2"

DEFAULT_SOURCE = "android.4.4"
DEFAULT_MODEL = "SM-G9700"
DEFAULT_SOFTWARE = "Android 9"
DEFAULT_APPVER = "android.3.3.08"

CONF_USER_ID = "user_id"
CONF_PHONE = "phone"
CONF_ACCESS_TOKEN = "access_token"
CONF_REFRESH_TOKEN = "refresh_token"
CONF_HOME_ID = "home_id"
CONF_DEVICE_ID = "device_id"
CONF_PRODUCT_ID = "product_id"
CONF_PRODUCT_TYPE = "product_type"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_SCAN_INTERVAL = 30
DEFAULT_PRODUCT_ID = "1025A"

# 令牌在剩余时间低于该值时主动刷新（秒）
TOKEN_REFRESH_MARGIN = 6 * 3600

# 设备属性 -> 名称
PROP_WORK_STATE = "WorkState"
PROP_RUN_STATE = "RunState"
PROP_WORK_MODE = "WorkMode"
PROP_POWER = "PowerSwitchAll"
PROP_GSC_POWER = "GSCPowerSwitch"
PROP_GSC_WORK_STATE = "GSCWorkSta"
PROP_DOOR = "DoorLockSta"
PROP_ERROR = "ErrorNum"
PROP_REMINDER = "Reminder"
PROP_REMAIN = "SetWorkTime"
PROP_CL_REMAIN = "ClRemTime"
PROP_ST_REMAIN = "StRemTime"
PROP_STORE_TOTAL = "StoreTotalTime"
PROP_DETERGENT = "DetergentLevel"
PROP_SOFTENER = "SoftensaltLevel"
PROP_AUTH_TYPE = "AuthType"
PROP_REMOTE_AUTH = "RemoteAuth"
PROP_NEW_REMOTE_AUTH = "NewRemoteAuth"
PROP_TURBIDITY = "Turbidity"
PROP_SMART_CHAMBER = "SmartChamber"
PROP_APPOINT_TIME = "SetAppointmentTime"
PROP_WATER_TEMP = "TemperatureSensor1"
PROP_ADD_FUN_H = "AddFunH"
PROP_ADD_FUN_L = "AddFunL"

WORK_STATE_MAP = {
    0: "待机",
    1: "待机",
    2: "运行中",
    3: "运行中",
    4: "运行中",
    5: "已完成",
    6: "已暂停",
    7: "预约中",
}

# 洗碗机工作模式（productId 1025A）
WORK_MODE_MAP = {
    0: "智能洗",
    1: "强力洗",
    2: "标准洗",
    3: "节能洗",
    4: "快速洗",
    5: "漂洗",
    6: "消毒",
    7: "烘干",
    135: "预约",
}

# 只允许在待机状态下启动的模式
SELECTABLE_MODES = [0, 1, 2, 3, 4]
