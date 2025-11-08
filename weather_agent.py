# weather_agent.py
# 简化的天气查询代理 - 更自然流畅的对话体验

import os
import parlant.sdk as p
import asyncio
from datetime import datetime
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
load_dotenv()

# 设置智谱 AI 环境变量
# 请确保设置了 ZHIPUAI_API_KEY 环境变量
# export ZHIPUAI_API_KEY=your_api_key_here


# 设置 Ollama 环境变量
os.environ["OLLAMA_BASE_URL"] = "http://localhost:11434"
os.environ["OLLAMA_MODEL"] = "qwen2.5:latest"
os.environ["OLLAMA_EMBEDDING_MODEL"] = "nomic-embed-text:latest"
os.environ["OLLAMA_API_TIMEOUT"] = "300"

@p.tool
async def get_weather(context: p.ToolContext, location: str) -> p.ToolResult:
    """查询指定地区的天气信息"""
    
    # 模拟天气数据
    weather_data = {
        "北京": {"temp": 15, "unit": "°C", "condition": "晴朗", "humidity": 45},
        "上海": {"temp": 20, "unit": "°C", "condition": "多云", "humidity": 60},
        "广州": {"temp": 25, "unit": "°C", "condition": "小雨", "humidity": 75},
        "成都": {"temp": 18, "unit": "°C", "condition": "阴天", "humidity": 70},
        "深圳": {"temp": 26, "unit": "°C", "condition": "晴朗", "humidity": 65},
        "杭州": {"temp": 19, "unit": "°C", "condition": "多云", "humidity": 58},
        "new york": {"temp": 68, "unit": "°F", "condition": "Sunny", "humidity": 50},
        "los angeles": {"temp": 75, "unit": "°F", "condition": "Clear", "humidity": 40},
        "chicago": {"temp": 55, "unit": "°F", "condition": "Cloudy", "humidity": 65},
        "london": {"temp": 12, "unit": "°C", "condition": "Rainy", "humidity": 80},
        "tokyo": {"temp": 16, "unit": "°C", "condition": "Partly Cloudy", "humidity": 55},
    }

    data = weather_data.get(location)
    
    if not data:
        return p.ToolResult(
            data={
                "success": False,
                "message": f"抱歉，暂时没有 {location} 的天气数据",
                "available_cities": "北京、上海、广州、成都、深圳、杭州、New York、Los Angeles、Chicago、London、Tokyo"
            }
        )
    
    return p.ToolResult(
        data={
            "success": True,
            "location": location,
            "temperature": data["temp"],
            "unit": data["unit"],
            "condition": data["condition"],
            "humidity": data["humidity"],
            "current_time": datetime.now().strftime("%Y-%m-%d %H:%M")
        }
    )


async def create_weather_journey(agent: p.Agent) -> p.Journey:
    """创建天气查询流程 - 灵活但有必要的校验"""
    journey = await agent.create_journey(
        title="查询天气",
        description="帮助用户查询城市天气",
        conditions=["用户想查询天气", "用户提到城市名称"]
    )
    
    # 如果用户已经提到城市，直接查询
    t1 = await journey.initial_state.transition_to(
        tool_state=get_weather,
        condition="用户消息中包含城市名称"
    )
    
    # 如果没有提到城市，友好地询问
    t2 = await journey.initial_state.transition_to(
        chat_state="友好地询问用户想查询哪个城市的天气",
        condition="用户没有提到具体城市"
    )
    
    # 用户回复城市后查询
    t3 = await t2.target.transition_to(tool_state=get_weather)
    
    # 查询成功 - 展示结果
    t4 = await t1.target.transition_to(
        chat_state="简洁友好地告诉用户天气情况：温度、天气状况、湿度",
        condition="查询成功"
    )
    
    t5 = await t3.target.transition_to(
        chat_state="简洁友好地告诉用户天气情况：温度、天气状况、湿度",
        condition="查询成功"
    )
    
    # 查询失败 - 提示可用城市
    t6 = await t1.target.transition_to(
        chat_state="告知暂不支持该城市，列出可查询的城市列表",
        condition="查询失败"
    )
    
    t7 = await t3.target.transition_to(
        chat_state="告知暂不支持该城市，列出可查询的城市列表",
        condition="查询失败"
    )
    
    # 成功后询问是否还要查询其他城市
    t8 = await t4.target.transition_to(
        chat_state="询问用户是否还想查询其他城市",
    )
    
    t9 = await t5.target.transition_to(
        chat_state="询问用户是否还想查询其他城市",
    )
    
    # 用户想继续查询 - 回到查询流程
    await t8.target.transition_to(
        tool_state=get_weather,
        condition="用户想查询其他城市"
    )
    
    await t9.target.transition_to(
        tool_state=get_weather,
        condition="用户想查询其他城市"
    )
    
    # 用户不想继续 - 结束
    await t8.target.transition_to(
        state=p.END_JOURNEY,
        condition="用户不想继续查询"
    )
    
    await t9.target.transition_to(
        state=p.END_JOURNEY,
        condition="用户不想继续查询"
    )
    
    # 失败后用户可以重新选择城市
    await t6.target.transition_to(tool_state=get_weather)
    await t7.target.transition_to(tool_state=get_weather)
    
    # Journey 内的指导原则
    await journey.create_guideline(
        condition="用户输入的城市名称不清晰或有歧义",
        action="礼貌地请用户确认具体是哪个城市"
    )
    
    await journey.create_guideline(
        condition="用户一次提到多个城市",
        action="逐个查询并对比展示各城市天气"
    )
    
    return journey


async def main() -> None:

    async with p.Server(nlp_service=p.NLPServices.zhipu) as server:
        agent = await server.create_agent(
            name="小天",
            description="友好的天气助手，用自然对话方式帮助用户查询天气"
        )
        
        # 创建天气查询流程（工具通过 @p.tool 装饰器自动注册）
        await create_weather_journey(agent)
        
        # 全局指导原则
        await agent.create_guideline(
            condition="用户问候",
            action="友好回应，简单介绍自己可以查询天气，支持的城市包括：北京、上海、广州、成都、深圳、杭州等"
        )
        
        await agent.create_guideline(
            condition="用户询问温度单位或转换",
            action="简单解释：中国用摄氏度(°C)，美国用华氏度(°F)。转换公式：°F = °C × 1.8 + 32"
        )
        
        await agent.create_guideline(
            condition="对话中的任何时候",
            action="保持简洁友好，像朋友聊天一样自然，避免过于正式或冗长"
        )
        
        await agent.create_guideline(
            condition="用户询问天气预报或未来天气",
            action="告知目前只能查询当前天气，暂不支持预报功能"
        )


if __name__ == "__main__":
    asyncio.run(main())
