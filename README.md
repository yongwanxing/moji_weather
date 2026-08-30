# 🌤️ 墨迹天气查询 · AstrBot 插件

> 一款轻量易用的 AstrBot 天气查询插件 —— **实时天气 · 空气质量 · 逐日预报 · 生活指数** 一次搞定。

![AstrBot](https://img.shields.io/badge/AstrBot-v4.16%2B-4a90d9?style=for-the-badge&logo=bot&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Version](https://img.shields.io/badge/Version-1.0.0-00b4d8?style=for-the-badge)
![Author](https://img.shields.io/badge/Author-xuanbao-9b5de5?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

---

## ✨ 功能特性

| 🎯 功能 | 📖 说明 |
| :--- | :--- |
| 🌤 **实时天气** | 当前天气、温度、体感温度、湿度、风向风力、日出日落 |
| 🟢 **空气质量** | AQI 数值与空气质量等级 |
| 📆 **逐日预报** | 未来 1-7 天天气、温度区间、风力预报 |
| 🧴 **生活指数** | 感冒、洗车、穿衣、紫外线、运动、钓鱼等指数 |
| 🧠 **LLM 工具** | 注册 `get_weather` 工具，Agent 对话中可让 AI 自动查询天气 |
| 💾 **智能记忆** | 自动记住每位用户上次查询过的城市，下次免输 |
| ⚙️ **可视化配置** | WebUI 管理面板即可配置默认城市、预报天数等 |

> 📌 **数据来源**：墨迹天气 · 枫雨API  
> 接口文档：[https://api.yuafeng.cn/?action=doc&id=123](https://api.yuafeng.cn/?action=doc&id=123)  
> 接口地址：`https://api.yuafeng.cn/API/ly/moji.php`（公共免费接口，仅供学习使用）

---

## 🚀 快速上手

发送 `/天气 北京`，机器人就会回复北京的实时天气与未来预报：

```
🌤 北京 天气
⏱ 实时天气：☀️ 晴 26℃（体感 26℃）
💧 湿度：51%
🌬 风向：西南风 2级
🌅 日出 05:40 / 日落 18:50
🟢 空气质量：优（AQI 22）

📆 未来 3 天预报：
  8/29 少云 21~32℃ 西风 2级
  8/30 少云 23~33℃ 北风 2级
  8/31 少云 20~29℃ 东北风 2级

🧴 生活指数：
  感冒：较易发
  洗车：适宜
  穿衣：炎热
  紫外线：中等
```

---

## 📦 安装

### ✅ 方法一：WebUI 插件市场安装（推荐）

1. 打开 **AstrBot 管理面板**；
2. 进入 **插件管理** 页面；
3. 点击顶部 **插件市场** 选项卡，搜索 `墨迹天气` 或 `moji_weather`；
4. 点击 **安装**，等待安装完成；
5. 安装完成后在插件列表中点击 **启用** 即可使用。

### 📂 方法二：手动安装

1. **前置要求**：已安装 [AstrBot](https://astrbot.app) **v4.16 及以上**版本（Python 3.9+）；
2. 将整个 `moji_weather` 文件夹复制到 AstrBot 的插件目录中：

   ```
   AstrBot/
   ├── data/
   │   └── plugins/
   │       └── moji_weather/          ← 整个文件夹放这里
   │           ├── main.py
   │           ├── metadata.yaml
   │           ├── _conf_schema.json
   │           └── requirements.txt
   └── main.py
   ```

3. 回到 **AstrBot 管理面板 → 插件管理**，点击右上角 **⋯** 菜单 → **重载插件**；
4. 若列表中的插件显示为 **禁用**，点击 **启用**；
5. 当日志出现以下信息，即表示安装成功 ✅：

   ```
   [INFO] 天气插件加载完成，LLM 工具 get_weather 已注册。
   ```

### 📌 依赖说明

| 依赖 | 版本要求 | 说明 |
| :--- | :--- | :--- |
| `httpx` | ≥ 0.24 | AstrBot 本体已内置，通常无需额外安装 |

> 💡 若提示依赖缺失，可在 AstrBot 运行环境中手动执行：`pip install httpx`


---

## 🎮 使用说明

### 💬 指令

| 指令 | 说明 |
| :--- | :--- |
| `/天气 北京` | 查询北京天气 |
| `/天气` | 不带城市时，依次使用「配置的默认城市」→「该用户上次查询的城市」 |
| `/weather 上海` | 英文指令别名 |
| `/tianqi 广州` | 拼音指令别名 |

> 🔧 所有指令均可配合机器人唤醒词使用（例如 `@机器人 天气 北京`）。

### 🧠 LLM 工具（Agent 自动调用）

插件加载后会自动注册名为 **`get_weather`** 的 LLM 工具，在 Agent 模式下 AI 会根据对话内容自动查询天气，例如：

- *「北京今天天气怎么样？」* → AI 自动调用 `get_weather(city="北京")`
- *「明天上海会不会下雨，要不要带伞？」* → AI 自动查询上海天气后回答

### 🔄 城市解析优先级

```
1. 用户输入的城市     （/天气 成都 → 成都）
2. 配置的默认城市     （default_city，默认：北京）
3. 该用户上次查询过的城市（自动记忆，数据存于 data 目录）
```

---

## ⚙️ 插件配置

在 **AstrBot 管理面板 → 插件管理 → moji_weather → 设置** 中进行配置：

| 配置项 | 类型 | 默认值 | 说明 |
| :--- | :--- | :--- | :--- |
| `default_city` | 字符串 | `北京` | 不带城市查询时使用的默认城市 |
| `forecast_days` | 整数 | `3` | 预报天数，范围 1-7 天 |
| `show_live_index` | 布尔 | `true` | 是否展示生活指数 |

配置保存后即时生效，无需重启。


---

## ❓ 常见问题（FAQ）

<details>
<summary><b>1️⃣ 插件加载后提示「已被禁用」，无法使用怎么办？</b></summary>

插件本体加载正常，只是处于禁用状态。请到 **插件管理** 页面点击该插件右上角的 **启用** 按钮。
若启用后仍提示禁用，可能是历史残留状态：编辑 AstrBot `data/shared_preferences.json`，
删除 `inactivated_plugins` 数组中包含 `moji_weather` 的条目后保存，再重载插件。
</details>

<details>
<summary><b>2️⃣ 查询失败 / 返回「接口错误」？</b></summary>

天气数据来自第三方公共接口，偶发不稳定。请稍后重试；若持续失败，说明接口暂时不可用，
可等待接口恢复后再使用（插件已做完整异常捕获，不会影响机器人正常运行）。
</details>

<details>
<summary><b>3️⃣ 查询某些小城市查不到数据？</b></summary>

接口按「城市名」匹配数据，请使用常见城市名（如 `北京`、`上海`）或带上省/市全称尝试。
</details>

<details>
<summary><b>4️⃣ 修改配置后不生效？</b></summary>

配置保存在 `data/config/moji_weather_config.json`，保存后通常即时生效；
若未生效，请重载插件或重启 AstrBot。
</details>

---

## ⚠️ 免责声明

- 本项目仅供学习与个人使用，天气数据来源于第三方公共接口，**不保证数据的准确性与实时性**；
- 请勿将本插件用于任何商业用途；
- 第三方接口若调整或停止服务，本插件可能随之失效，敬请谅解。

---

## 📄 License

本项目使用 [MIT License](LICENSE) 开源。

---

<p align="center">
  Made with ❤️ by <b>xuanbao</b> · Powered by <a href="https://astrbot.app">AstrBot</a> & <a href="https://api.yuafeng.cn/?action=doc&id=123">枫雨API</a>
</p>

