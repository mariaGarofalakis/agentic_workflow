import json
from typing import Any, Literal
from openai import AsyncOpenAI
from pydantic import BaseModel, ConfigDict, PrivateAttr
from src.tools.tool_reginstry import tool_registry

ToolChoice = Literal["auto", "none", "required"]


class AsyncClient(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    api_key: str = "lmstudio"
    base_url: str = "http://localhost:1234/v1"
    model: str = "nvidia/nemotron-3-nano-4b"
    tool_choice: ToolChoice = "auto"
    max_output_tokens: int = 1024
    print_stream: bool = True

    _client: AsyncOpenAI = PrivateAttr()

    def model_post_init(self, __context: Any) -> None:
        self._client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )

    async def stream_one_turn(
        self,
        input_data: str | list[dict[str, Any]],
        previous_response_id: str | None = None,
    ):
        streamed_any_text = False

        async with self._client.responses.stream(
            model=self.model,
            input=input_data,
            tools=tool_registry.schemas,
            tool_choice=self.tool_choice,
            previous_response_id=previous_response_id,
            max_output_tokens=self.max_output_tokens,
        ) as stream:
            async for event in stream:
                if not self.print_stream:
                    continue

                delta = getattr(event, "delta", None)
                if isinstance(delta, str) and delta:
                    print(delta, end="", flush=True)
                    streamed_any_text = True

            if self.print_stream and streamed_any_text:
                print()

            return await stream.get_final_response()
        

    async def run_agent(self, user_input: str):
            response = await self.stream_one_turn(
                input_data=user_input,
            )

            while True:
                tool_results: list[dict[str, Any]] = []

                for item in response.output:
                    item_type = getattr(item, "type", None)

                    if item_type not in {"function_call", "tool_call"}:
                        continue

                    raw_args = getattr(item, "arguments", {})
                    if isinstance(raw_args, str):
                        try:
                            args = json.loads(raw_args)
                        except json.JSONDecodeError:
                            args = {}
                    elif isinstance(raw_args, dict):
                        args = raw_args
                    else:
                        args = {}

                    result = await tool_registry.run(item.name, args)

                    tool_results.append(
                        {
                            "type": "function_call_output",
                            "call_id": item.call_id,
                            "output": json.dumps(result),
                        }
                    )

                if not tool_results:
                    return response

                response = await self.client.stream_one_turn(
                    input_data=tool_results,
                    tools=tools,
                    previous_response_id=response.id,
                )