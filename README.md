# 方太洗碗机 · Home Assistant 集成

> [!WARNING]
> **暂停维护，不建议安装。** 实际使用中发现，本集成可能导致方太手机 App 掉线。
> 与手机 App 的会话共存问题尚未解决，也未验证能够稳定同时使用。已安装的用户建议先卸载本集成，再重新登录手机 App。
> 项目代码保留供后续研究，暂无恢复维护或发布新版本的计划。

把方太（Fotile）嵌入式洗碗机接入 Home Assistant，支持状态监控与远程控制。

> 已适配：嵌入式洗碗机 **JBCD7E-02-S7**

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
![version](https://img.shields.io/badge/version-1.1.0-blue)
![license](https://img.shields.io/badge/license-MIT-green)
[![Validate](https://github.com/doubly-yi/fotile-dishwasher/actions/workflows/validate.yml/badge.svg)](https://github.com/doubly-yi/fotile-dishwasher/actions/workflows/validate.yml)

---

## 功能

**状态**

- 电源、工作状态（待机 / 运行 / 完成 / 预约）
- 当前洗涤模式、剩余时间、存储时长
- 门开关、故障代码
- 洗碗液余量、软水盐余量、浊度
- 设备在线状态

**控制**

- 开关机
- 选择洗涤模式（智能洗 / 强力洗 / 标准洗 / 节能洗 / 快速洗）
- 一键开始洗涤、一键停止

状态变化会实时推送到 Home Assistant，同时每 30 秒做一次同步兜底。

---

## 安装

### HACS（推荐）

1. HACS → 集成 → 右上角 `⋮` → **自定义存储库**
2. 填入本仓库地址，类别选 **Integration**
3. 搜索「方太洗碗机」安装，重启 Home Assistant

### 手动

把 `custom_components/fotile_dishwasher` 整个目录复制到 HA 配置目录的 `custom_components/` 下，重启 Home Assistant。

---

## 配置

「设置 → 设备与服务 → 添加集成」→ 搜索 **方太洗碗机** → 粘贴**授权码**即可。

授权码只需填一次，之后集成会自动续期，不用再管。

> 方太没有提供第三方登录接口，授权码需要从你的账号导出一次。
> 使用仓库里的 [`tools/export_auth.py`](tools/export_auth.py) 生成，按提示操作即可。

---

## 实体

| 实体 | 类型 |
|---|---|
| `switch.xxx_电源` | 开关机 |
| `select.xxx_洗涤模式` | 选择模式 |
| `button.xxx_开始洗涤` / `xxx_停止` | 一键操作 |
| `sensor.xxx_工作状态` / `工作模式` | 状态 |
| `sensor.xxx_剩余时间` / `存储时长` | 时间 |
| `sensor.xxx_故障代码` / `洗碗液余量` / `软水盐余量` / `浊度` | 状态 |
| `binary_sensor.xxx_门` | 门开关 |
| `binary_sensor.xxx_在线` | 在线状态 |

---

## 排错

**提示授权失效**

授权码过期或被执行了刷新。重新生成一个授权码，在集成里重新配置即可。

**状态能读，但控制没反应**

云端连接还没就绪，等 10 秒左右重试；持续不行请提交 issue 并附上日志。

**打开调试日志**

```yaml
logger:
  logs:
    custom_components.fotile_dishwasher: debug
```

---

## 免责声明

- 本项目为个人作品，与方太集团无关。
- 远程操作电器存在风险（例如误启动），请在了解自己设备行为的前提下使用，风险自负。
- 云端接口可能随时变更，届时本项目可能失效。

## License

[MIT](LICENSE)
