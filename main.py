import asyncio

from src.providers.openai import AsyncClient



async def main():
    client = AsyncClient()

    print("🤖 Agent ready. Type 'exit' to quit.\n")

    while True:
        user_input = input("You: ")

        if user_input.lower() in {"exit", "quit"}:
            print("Goodbye 👋")
            break

        response = await client.run_agent(user_input)

        print("\nAssistant:")
        print(response.output_text)
        print("-" * 40)


if __name__ == "__main__":
    asyncio.run(main())