# main.py

import asyncio
import argparse
import parlant.sdk as p
from dotenv import load_dotenv

load_dotenv()

async def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="Run Parlant agent with different NLP providers")
    parser.add_argument("--provider", type=str, default="zhipu", choices=["zhipu", "ollama", "emcie"],
                        help="NLP provider to use (default: zhipu)")
    args = parser.parse_args()
    
    # 根据 provider 选择 NLP 服务
    nlp_service = {
        "zhipu": p.NLPServices.zhipu,
        "ollama": p.NLPServices.ollama,
        "emcie": p.NLPServices.emcie
    }[args.provider]
    async with p.Server(nlp_service=nlp_service) as server:
        agent = await server.create_agent(
            name="Otto Carmen",
            description="You work at a car dealership",
        )

        print(f"✅ Agent {agent.name} is running with {args.provider.capitalize()} backend!")
if __name__ == "__main__":
    asyncio.run(main())