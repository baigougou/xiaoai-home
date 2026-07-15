# XiaoAI Home Assistant Bridge

通过小爱音箱语音控制第三方智能家居设备（格力空调、美的空调、冰箱、洗碗机等），基于 Home Assistant 实现。

## 功能特性

- 🔊 **语音控制**：通过小爱音箱语音指令控制家电设备
- ❄️ **空调控制**：支持开/关、温度调节、模式切换（制冷/制热/除湿/自动/送风）
- 📊 **状态查询**：支持查询冰箱温度、洗碗机状态等设备状态
- 🔊 **TTS 播报**：操作结果通过小爱音箱语音播报反馈
- 🐳 **Docker 部署**：支持 Docker 一键部署到 NAS
- 🌐 **Web 界面**：可视化配置界面，无需手动编辑配置文件
- 🔍 **实体发现**：自动发现 Home Assistant 中的设备实体

## 技术方案

使用 Home Assistant 的 `xiaomi_miot_raw` 服务实现语音交互：

1. 通过 `xiaomi_miot_raw.execute_text` 执行文本指令到小爱音箱
2. 通过 `xiaomi_miot_raw.play_text` 实现 TTS 语音播报反馈
3. 轮询小爱音箱 `media_player` 实体状态获取语音转文本结果

> 此方案不需要直接连接小米账号，完全通过 Home Assistant 集成，更稳定可靠。

---

## 部署指南（NAS + Docker）

### 前置准备

#### 1. 获取 Home Assistant Long-Lived Access Token

1. 登录你的 Home Assistant 网页界面
2. 点击左下角你的用户名 → 滚动到底部 **"长期访问令牌"** (Long-Lived Access Tokens)
3. 点击 **"创建令牌"**，输入名称（如 `xiaoai-bridge`），点击确定
4. **立即复制保存令牌**（关闭后无法再次查看）

#### 2. 确认小爱音箱实体 ID

1. 进入 Home Assistant → **设置** → **设备与服务** → **实体**
2. 找到你的小爱音箱（类型为 `media_player`），记录实体 ID（例如 `media_player.xiaoai_lx06`）

#### 3. 确认已控制的设备实体 ID

在实体列表中找到格力空调、美的空调等设备，记录它们的实体 ID：
- 空调：`climate.xxx`
- 冰箱：`sensor.xxx_temperature` 等
- 洗碗机：`sensor.xxx_status` 等

---

### 方式一：Docker Compose 部署（推荐）

#### 步骤 1：上传文件到 NAS

将项目文件上传到 NAS 的某个目录，例如：
```
/volume1/docker/xiaoai-home-assistant/
```

确保目录结构如下：
```
xiaoai-home-assistant/
├── src/
├── config/
│   └── config-example.json
├── Dockerfile
├── docker-compose.yml
└── .dockerignore
```

#### 步骤 2：创建 config 目录

```bash
cd /volume1/docker/xiaoai-home-assistant
mkdir -p config
```

> 注意：不要提前创建 `config/config.json`，首次启动后通过 Web 界面配置。

#### 步骤 3：启动容器

```bash
docker-compose up -d
```

如果需要重新构建镜像：
```bash
docker-compose up -d --build
```

#### 步骤 4：访问 Web 界面进行配置

打开浏览器访问：`http://你的NAS-IP:18015`

在 Web 界面中：
1. 填写 Home Assistant URL（例如 `http://192.168.1.100:8123`）
2. 粘贴 Long-Lived Access Token
3. 填写小爱音箱实体 ID（例如 `media_player.xiaoai_lx06`）
4. 点击 **"保存配置"**
5. 点击 **"重启服务"** 或重启容器

#### 步骤 5：设备绑定

1. 配置保存并连接成功后，进入 **"设备绑定"** 标签页
2. 点击 **"发现实体"** 按钮，系统会列出 HA 中可用的设备
3. 对空调/设备点击 **"绑定"**
4. 添加语音关键词（例如："格力空调"、"主卧空调"、"客厅空调"）
5. 点击 **"保存"**
6. 在 **"指令测试"** 标签页测试语音指令解析是否正确

---

### 方式二：本地 Python 运行（开发调试）

```bash
# 安装依赖
pip install fastapi uvicorn[standard] httpx pydantic python-dotenv

# 启动服务（Windows PowerShell）
$env:PYTHONPATH="src"
python -m uvicorn xiaoai_ha_bridge.main:app --host 0.0.0.0 --port 18015 --reload

# 启动服务（Linux/macOS）
PYTHONPATH=src python -m uvicorn xiaoai_ha_bridge.main:app --host 0.0.0.0 --port 18015 --reload
```

访问 http://localhost:18015 进行配置。

---

## 支持的语音指令示例

### 空调控制
| 语音指令 | 效果 |
|---------|------|
| 打开格力空调 | 打开空调 |
| 关闭格力空调 | 关闭空调 |
| 格力空调调到26度 | 设置温度为26°C |
| 格力空调开制冷 | 设置制冷模式 |
| 格力空调开制热模式 | 设置制热模式 |
| 格力空调26度开制冷 | 同时设置温度和模式 |
| 美的空调除湿模式 | 设置除湿模式 |

### 状态查询
| 语音指令 | 效果 |
|---------|------|
| 冰箱温度是多少 | 查询冰箱温度并语音播报 |
| 洗碗机什么状态 | 查询洗碗机状态 |

---

## 配置说明

配置文件保存在 `config/config.json`（Docker 中挂载为卷持久化）：

```json
{
  "home_assistant": {
    "url": "http://192.168.1.100:8123",
    "api_token": "your-long-lived-access-token"
  },
  "xiaomi_speaker": {
    "entity_id": "media_player.xiaoai_lx06",
    "execute_text_service": "xiaomi_miot_raw.execute_text",
    "play_text_service": "xiaomi_miot_raw.play_text"
  },
  "bridge": {
    "host": "0.0.0.0",
    "port": 18015,
    "debug": false,
    "log_level": "INFO",
    "polling_interval": 3
  },
  "tts": {
    "enabled": true,
    "volume": 50
  },
  "commands": {
    "climate_gree": {
      "name": "格力空调",
      "entity_id": "climate.gree_air_conditioner",
      "device_type": "climate",
      "keywords": ["格力空调", "主卧空调"]
    }
  }
}
```

### 配置项说明

| 配置项 | 说明 | 默认值 |
|-------|------|-------|
| `home_assistant.url` | Home Assistant 地址 | - |
| `home_assistant.api_token` | 长期访问令牌 | - |
| `xiaomi_speaker.entity_id` | 小爱音箱 media_player 实体 ID | - |
| `xiaomi_speaker.execute_text_service` | 文本执行服务 | `xiaomi_miot_raw.execute_text` |
| `xiaomi_speaker.play_text_service` | TTS 播放服务 | `xiaomi_miot_raw.play_text` |
| `bridge.polling_interval` | 轮询间隔（秒） | `3` |
| `tts.enabled` | 是否启用语音播报 | `true` |
| `commands` | 设备绑定字典（通过 Web 界面配置） | `{}` |

---

## 常用 Docker 命令

```bash
# 查看日志
docker-compose logs -f

# 重启服务
docker-compose restart

# 停止服务
docker-compose down

# 更新后重新构建启动
docker-compose up -d --build

# 进入容器
docker exec -it xiaoai-home-assistant bash
```

---

## API 接口

- `GET /` - Web 配置界面
- `GET /api/health` - 健康检查
- `GET /api/config` - 获取配置
- `POST /api/config` - 保存配置
- `POST /api/restart` - 重启服务
- `POST /api/test/ha` - 测试 HA 连接
- `GET /api/discover` - 发现 HA 实体
- `POST /api/test/parse` - 测试指令解析
- `POST /api/test/execute` - 测试执行指令
- `GET /docs` - FastAPI 自动文档

---

## 常见问题

### 1. 容器启动后无法访问 Web 界面？
- 检查 NAS 防火墙是否开放 18015 端口
- 确认 docker-compose.yml 中端口映射正确
- 查看日志：`docker-compose logs`

### 2. 连接 HA 失败？
- 确认 HA URL 可从 NAS 访问（使用 `curl` 在 NAS 上测试）
- 如果 HA 使用 HTTPS，URL 需要填写 `https://...`
- 确认 API Token 正确且未过期
- 如果 HA 开启了"仅限本地网络"，确保 NAS 在同一局域网

### 3. 小爱音箱不响应？
- 确认小爱音箱实体 ID 正确
- 确认 Xiaomi Miot Auto 集成已正确配置
- 确认小爱音箱已开启"Action调试模式"（在 Xiaomi Miot Auto 集成的设备配置中）
- 检查服务名 `xiaomi_miot_raw.execute_text` 是否正确（部分集成可能是 `xiaomi_miot.execute_text`）

### 4. 如何自定义服务名称？
如果你的 Xiaomi Miot 集成服务名不同，可以在 Web 配置界面修改 `execute_text_service` 和 `play_text_service`：
- 常见服务名：`xiaomi_miot_raw.execute_text`、`xiaomi_miot.execute_text`、`xiaomi_home.execute_text`

### 5. 如何推送到 GitHub？
```bash
cd xiaoai-home-assistant
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/你的用户名/xiaoai-home-assistant.git
git push -u origin main
```

---

## 项目结构

```
xiaoai-home-assistant/
├── src/xiaoai_ha_bridge/
│   ├── config/           # 配置管理
│   ├── ha_client/        # Home Assistant API 客户端
│   ├── engine/           # 指令解析与拦截引擎
│   ├── miservice/        # 小爱音箱轮询服务
│   ├── web/              # Web 界面与 API
│   ├── logging/          # 日志管理
│   └── main.py           # 主入口
├── config/               # 配置文件目录（持久化）
├── tests/                # 测试
├── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## 后续扩展

项目架构支持轻松扩展新设备类型：
- 在 [parser.py](file:///C:/Users/seele/AppData/Roaming/TRAE%20SOLO%20CN/ModularData/ai-agent/work-mode-projects/6a4f73e8fdb0381cd9354698/xiaoai-home-assistant/src/xiaoai_ha_bridge/engine/parser.py) 添加新的指令解析规则
- 在 [client.py](file:///C:/Users/seele/AppData/Roaming/TRAE%20SOLO%20CN/ModularData/ai-agent/work-mode-projects/6a4f73e8fdb0381cd9354698/xiaoai-home-assistant/src/xiaoai_ha_bridge/ha_client/client.py) 添加对应的 HA 服务调用
- 在 Web 界面添加对应的设备类型配置

## License

MIT License
