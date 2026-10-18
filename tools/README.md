# 工具

## `export_auth.py` —— 生成授权码

Home Assistant 集成需要一串授权码才能连接你的方太账号。这个脚本负责生成它。

### 准备

在同目录新建 `session.json`：

```json
{
  "user_id":       "用户 ID",
  "phone":         "账号手机号",
  "access_token":  "访问令牌",
  "refresh_token": "刷新令牌"
}
```

> 这是方太 App 登录后的一对令牌，导出一次即可。
> 集成会自动续期，所以只需要弄这一次。

### 生成

```bash
python export_auth.py
```

输出一串字符，复制整行，粘贴到 Home Assistant 里「方太洗碗机」集成的配置框。

授权码里已经包含续期所需的信息，填一次就好。

> ⚠️ 授权码等同于账号凭证，不要发给别人。

---

## `make_brand_assets.py` —— 生成图标

维护用。重新生成 `custom_components/fotile_dishwasher/brand/` 下的图标：

```bash
python make_brand_assets.py
```

需要 `pillow`。
