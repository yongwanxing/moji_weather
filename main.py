"""
AstrBot 天气查询插件

功能：
1. 支持 `/天气 <城市>` 命令查询实时天气、空气质量、未来天气预报与生活指数；
2. 注册 LLM 工具 `get_weather`，让 AI 在对话中自动调用查询天气；
3. 支持在 WebUI 管理面板配置默认城市、预报天数、是否显示生活指数；
4. 自动记住用户上次查询过的城市（数据持久化在 AstrBot 的 data 目录中）。

api接口：https://api.yuafeng.cn/?action=doc&id=123
"""

# ================= 标准库导入 =================
from typing import Any

# ================= 第三方库导入 =================
import httpx  # 异步网络请求库
from pydantic import Field  # 用于定义工具参数 Schema 的默认值
from pydantic.dataclasses import dataclass  # pydantic 数据类

# ================= AstrBot 相关导入 =================
from astrbot.api import logger  # AstrBot 提供的插件日志接口
from astrbot.api.event import AstrMessageEvent, filter  # 消息事件与事件过滤器
from astrbot.api.star import Context, Star  # 插件上下文与插件基类

from astrbot.core.agent.run_context import ContextWrapper  # LLM 工具运行上下文
from astrbot.core.agent.tool import FunctionTool, ToolExecResult  # LLM 函数工具基类与返回类型
from astrbot.core.astr_agent_context import AstrAgentContext  # Agent 执行上下文

# ================= 常量定义 =================
# 天气接口地址（墨迹天气公共接口）
WEATHER_API_URL = "https://api.yuafeng.cn/API/ly/moji.php"

# 网络请求超时时间（秒）
WEATHER_REQUEST_TIMEOUT = 10

# 天气描述与表情图标映射（用于美化输出，匹配不到时不做替换）
WEATHER_ICON_MAP = [
    ("雷阵雨", "⛈"),
    ("雷", "⛈"),
    ("小雨", "🌦"),
    ("中雨", "🌧"),
    ("大雨", "🌧"),
    ("暴雨", "🌧"),
    ("雨", "🌧"),
    ("小雪", "🌨"),
    ("大雪", "❄️"),
    ("雪", "❄️"),
    ("雾", "🌫"),
    ("霾", "🌫"),
    ("沙尘", "🌪"),
    ("大风", "💨"),
    ("晴", "☀️"),
    ("多云", "⛅"),
    ("少云", "🌤"),
    ("阴", "☁️"),
]

# KV 存储中记录用户上次查询城市的键前缀
LAST_CITY_KEY_PREFIX = "last_city_"


# ================= 通用工具函数 =================
def safe_str(value: Any, default: str = "") -> str:
    """将任意值安全地转换为去除首尾空白的字符串。

    参数:
        value: 原始值，可能为 None 或任意类型。
        default: 当值为 None 时返回的默认字符串。

    返回:
        转换并去除首尾空白后的字符串。
    """
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def match_weather_icon(weather_text: str) -> str:
    """根据天气描述文本匹配对应的表情图标。

    参数:
        weather_text: 天气描述文本，例如“晴”“小雨转多云”。

    返回:
        匹配到的表情图标字符串；未匹配时返回空字符串。
    """
    for keyword, icon in WEATHER_ICON_MAP:
        if keyword in weather_text:
            return icon
    return ""

def format_temperature(low: Any, high: Any) -> str:
    """格式化温度范围。

    参数:
        low: 最低温度。
        high: 最高温度。

    返回:
        形如“18~28℃”的温度字符串；无数据时返回“未知”。
    """
    low_s = safe_str(low)
    high_s = safe_str(high)
    if not low_s and not high_s:
        return "未知"
    if low_s and high_s:
        return f"{low_s}~{high_s}℃"
    return f"{low_s or high_s}℃"


def format_date(date_str: Any) -> str:
    """将“2026-08-30”格式的日期简化为“8/30”格式。

    参数:
        date_str: 原始日期字符串。

    返回:
        简化后的日期字符串；格式不符时原样返回。
    """
    parts = safe_str(date_str).split("-")
    if len(parts) == 3:
        try:
            return f"{int(parts[1])}/{int(parts[2])}"
        except (ValueError, TypeError):
            return safe_str(date_str)
    return safe_str(date_str)


def get_result_section(data: dict) -> dict:
    """从接口返回数据中提取天气数据主体。

    说明:
        接口数据通常位于 data["result"] 中，部分场景下也可能直接位于 data 中，
        这里做兼容处理，保证字段解析不受影响。

    参数:
        data: 天气接口返回的完整 JSON 字典。

    返回:
        包含 condition / aqi / forecastDayList / liveIndex 等字段的字典。
    """
    payload = data.get("data")
    if not isinstance(payload, dict):
        payload = data
    if isinstance(payload.get("result"), dict):
        return payload["result"]
    return payload


# ================= 天气接口请求 =================
async def fetch_weather(city: str, num: int = 3) -> dict:
    """异步请求天气接口并返回完整 JSON 数据。

    参数:
        city: 要查询的城市名称。
        num: 天气预报天数。

    返回:
        接口返回的完整 JSON 字典。

    异常:
        Exception: 网络错误、HTTP 状态码异常、响应解析失败或业务码非 0 时抛出。
    """
    # 构造请求参数
    params = {"city": city, "n": 1, "num": num}
    # 使用异步 httpx 客户端发起请求（禁止使用同步 requests）
    async with httpx.AsyncClient(timeout=WEATHER_REQUEST_TIMEOUT) as client:
        resp = await client.get(WEATHER_API_URL, params=params)
        # 非 2xx 状态码会抛出异常
        resp.raise_for_status()
        # 解析 JSON 响应
        data = resp.json()
    # 业务码不为 0 视为查询失败
    if data.get("code") != 0:
        raise RuntimeError(f"天气接口返回错误：{data.get('msg') or '未知错误'}")
    return data


# ================= 天气播报文本构建 =================
def build_weather_text(
    city: str,
    data: dict,
    forecast_days: int = 3,
    show_live_index: bool = True,
) -> str:
    """根据天气接口数据构建格式化后的天气播报文本。

    参数:
        city: 城市名称。
        data: 天气接口返回的完整 JSON 数据。
        forecast_days: 需要展示的预报天数。
        show_live_index: 是否展示生活指数。

    返回:
        格式化后的多行天气文本。
    """
    # 提取天气数据主体
    payload = get_result_section(data)
    condition = payload.get("condition") or {}
    aqi = payload.get("aqi") or {}
    forecast_list = payload.get("forecastDayList") or []
    live_index_list = payload.get("liveIndex") or []

    lines = [f"🌤 {city} 天气"]

    # ---------- 实时天气 ----------
    cur = safe_str(condition.get("fcondition"))
    temp = safe_str(condition.get("ftemp"))
    feel = safe_str(condition.get("freal_feel"))
    humidity = safe_str(condition.get("fhumidity"))
    wind_dir = safe_str(condition.get("fwind_dir"))
    wind_level = safe_str(condition.get("fwind_level"))
    sunrise = safe_str(condition.get("fsun_rise"))
    sunset = safe_str(condition.get("fsun_down"))

    if cur or temp:
        current_line = "⏱ 实时天气"
        if cur:
            # 为天气描述附加上表情图标（如存在）
            icon = match_weather_icon(cur)
            current_line += f"：{icon} {cur}" if icon else f"：{cur}"
        if temp:
            current_line += f" {temp}℃"
        if feel:
            current_line += f"（体感 {feel}℃）"
        lines.append(current_line)
    if humidity:
        lines.append(f"💧 湿度：{humidity}%")
    if wind_dir or wind_level:
        lines.append(f"🌬 风向：{wind_dir} {wind_level}级")
    if sunrise and sunset:
        # 取时间部分并只保留时分（去掉秒）
        sunrise_time = sunrise.split(" ")[-1][:5]
        sunset_time = sunset.split(" ")[-1][:5]
        lines.append(f"🌅 日出 {sunrise_time} / 日落 {sunset_time}")

    # ---------- 空气质量 ----------
    aqi_value = safe_str(aqi.get("value"))
    aqi_level = safe_str(aqi.get("level"))
    if aqi_value or aqi_level:
        aqi_text = "🟢 空气质量"
        if aqi_level:
            aqi_text += f"：{aqi_level}"
        if aqi_value:
            aqi_text += f"（AQI {aqi_value}）"
        lines.append(aqi_text)

    # ---------- 逐日天气预报 ----------
    valid_days = [day for day in forecast_list if isinstance(day, dict)]
    if valid_days:
        lines.append("")
        lines.append(f"📆 未来 {min(forecast_days, len(valid_days))} 天预报：")
        for day in valid_days[:forecast_days]:
            date_text = format_date(day.get("fpredict_date"))
            day_weather = safe_str(day.get("fcondition_day"))
            night_weather = safe_str(day.get("fcondition_night"))
            # 白天与夜间天气一致时只显示一次，否则显示“白天转夜间”
            if not night_weather or night_weather == day_weather:
                weather_text = day_weather
            else:
                weather_text = f"{day_weather}转{night_weather}"
            temp_text = format_temperature(day.get("ftemp_low"), day.get("ftemp_high"))
            wind_text = (
                f"{safe_str(day.get('fwind_dir_day'))} "
                f"{safe_str(day.get('fwind_level_day'))}级"
            )
            lines.append(f"  {date_text} {weather_text} {temp_text} {wind_text}".rstrip())

    # ---------- 生活指数 ----------
    if show_live_index:
        valid_indices = [item for item in live_index_list if isinstance(item, dict)]
        if valid_indices:
            lines.append("")
            lines.append("🧴 生活指数：")
            for item in valid_indices:
                name = safe_str(item.get("flive_name"))
                status = safe_str(item.get("flive_status"))
                if name:
                    lines.append(f"  {name}：{status}")

    return "\n".join(lines)


# ================= LLM 工具定义 =================
@dataclass
class WeatherTool(FunctionTool[AstrAgentContext]):
    """天气查询工具，供大模型在 Agent 对话中自动调用。"""

    # 工具名称（大模型通过该名称引用工具）
    name: str = "get_weather"

    # 工具描述（大模型根据描述决定何时调用此工具）
    description: str = (
        "查询指定城市的实时天气、空气质量、未来几天天气预报和生活指数。"
        "当用户询问某地天气、气温、空气质量、是否下雨、穿什么衣服等问题时，调用此工具。"
    )

    # 工具参数 Schema（JSON Schema 格式，用于约束大模型生成的参数）
    parameters: dict = Field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "要查询天气的城市名称，例如：北京、上海、广州",
                }
            },
            "required": ["city"],
        }
    )

    async def call(
        self,
        context: ContextWrapper[AstrAgentContext],
        **kwargs: Any,
    ) -> ToolExecResult:
        """执行天气查询，返回格式化后的天气文本。

        参数:
            context: 工具运行上下文。
            **kwargs: 大模型根据参数 Schema 传入的工具参数。

        返回:
            格式化后的天气信息文本；查询失败时返回友好的错误提示文本，
            保证工具调用不会导致机器人崩溃。
        """
        # 提取城市参数（兼容 city / location 两种命名）
        city = safe_str(kwargs.get("city") or kwargs.get("location"))
        if not city:
            return "缺少参数：请提供要查询天气的城市名称。"
        try:
            # 发起异步天气请求
            data = await fetch_weather(city, num=3)
            # 构建天气文本并返回给大模型
            return build_weather_text(city, data, forecast_days=3, show_live_index=True)
        except Exception as err:
            # 捕获所有异常，记录日志并返回错误提示，不向上抛出
            logger.error(f"LLM 工具 get_weather 查询城市 {city} 天气失败：{err}")
            return f"查询 {city} 的天气失败，请稍后再试。原因：{err}"


# ================= 插件主体 =================
class WeatherPlugin(Star):
    """AstrBot 天气查询插件（Star）。"""

    def __init__(self, context: Context, config=None) -> None:
        """初始化插件。

        参数:
            context: AstrBot 上下文对象，用于与 AstrBot Core 交互。
            config: 插件配置对象（由 _conf_schema.json 生成，可为 None）。
        """
        super().__init__(context)
        # 保存插件配置
        self.config = config or {}
        # 注册 LLM 工具（新版推荐用法，禁止使用已弃用的 context.register_llm_tool）
        self.context.add_llm_tools(WeatherTool())
        logger.info("天气插件加载完成，LLM 工具 get_weather 已注册。")

    @filter.command("天气", alias={"weather", "tianqi"})
    async def weather_command(self, event: AstrMessageEvent, city: str = "") -> None:
        """查询天气。

        用法：/天气 <城市名>，
        例如：/天气 北京。
        """
        # 去除城市参数首尾空白
        city = city.strip()

        # 未指定城市时，优先使用配置中的默认城市
        if not city:
            city = safe_str(self.config.get("default_city"))

        # 仍未指定城市时，尝试读取该用户上次查询过的城市（数据保存在 data 目录）
        if not city:
            city = await self.get_kv_data(
                f"{LAST_CITY_KEY_PREFIX}{event.unified_msg_origin}", ""
            )

        # 依旧没有城市，则提示用户
        if not city:
            yield event.plain_result("请告诉我你想查询哪个城市的天气，例如：/天气 北京")
            return

        # 从配置读取预报天数（异常时回退为 3 天，并限制在 1-7 天范围）
        try:
            forecast_days = int(self.config.get("forecast_days", 3))
        except (TypeError, ValueError):
            forecast_days = 3
        forecast_days = max(1, min(forecast_days, 7))

        # 从配置读取是否展示生活指数
        show_live_index = bool(self.config.get("show_live_index", True))

        # 发起天气查询请求（完整异常捕获，保证不崩溃）
        try:
            data = await fetch_weather(city, num=forecast_days)
        except Exception as err:
            logger.error(f"查询城市 {city} 天气失败：{err}")
            yield event.plain_result(f"查询 {city} 的天气失败了，请稍后再试。原因：{err}")
            return

        # 查询成功，记住用户最近查询的城市（持久化到 data 目录）
        try:
            await self.put_kv_data(
                f"{LAST_CITY_KEY_PREFIX}{event.unified_msg_origin}", city
            )
        except Exception as err:
            logger.warning(f"保存用户最近查询的城市失败：{err}")

        # 构建天气文本并返回
        text = build_weather_text(
            city,
            data,
            forecast_days=forecast_days,
            show_live_index=show_live_index,
        )
        yield event.plain_result(text)

    async def terminate(self) -> None:
        """插件被卸载、停用或重载时调用。"""
        logger.info("天气插件已卸载。")

