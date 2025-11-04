# main.py

import asyncio
import parlant.sdk as p

async def main():
    async with p.Server(nlp_service=p.NLPServices.ollama) as server:
        agent = await server.create_agent(
            name="Otto Carmen",
            description="You work at a car dealership",
        )

        print(f"✅ Agent {agent.name} is running with Ollama backend!")
if __name__ == "__main__":
    asyncio.run(main())