"""
Thin boto3 wrapper that mimics the anthropic.Anthropic messages interface,
but calls AWS Bedrock directly via boto3 InvokeModel.

Reason: AnthropicBedrock SDK hits a "use case details not submitted" restriction
on this bootcamp account, while raw boto3 InvokeModel works fine.
"""

import json
import os
from types import SimpleNamespace
from typing import Any

import boto3


BEDROCK_REGION = os.environ.get("BEDROCK_REGION", "us-west-2")
AWS_PROFILE = os.environ.get("AWS_PROFILE", "bootcamp")


def _make_session():
    return boto3.Session(profile_name=AWS_PROFILE, region_name=BEDROCK_REGION)


def _to_dict(obj):
    """Recursively convert _ContentBlock/SimpleNamespace/dict/list to plain JSON-safe types."""
    if isinstance(obj, SimpleNamespace):
        return {k: _to_dict(v) for k, v in vars(obj).items()}
    if isinstance(obj, dict):
        return {k: _to_dict(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_dict(i) for i in obj]
    return obj


class _ContentBlock(SimpleNamespace):
    pass


class _Response(SimpleNamespace):
    pass


class _Messages:
    def __init__(self, boto_client):
        self._client = boto_client

    def create(
        self,
        model: str,
        max_tokens: int,
        messages: list,
        system: str | None = None,
        tools: list[dict] | None = None,
        **kwargs,
    ) -> _Response:
        body: dict[str, Any] = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "messages": _to_dict(messages),
        }
        if system:
            body["system"] = system
        if tools:
            body["tools"] = tools

        raw = self._client.invoke_model(
            modelId=model,
            body=json.dumps(body),
            contentType="application/json",
            accept="application/json",
        )
        data = json.loads(raw["body"].read())

        content = []
        for block in data.get("content", []):
            if block["type"] == "text":
                content.append(_ContentBlock(type="text", text=block["text"]))
            elif block["type"] == "tool_use":
                content.append(_ContentBlock(
                    type="tool_use",
                    id=block["id"],
                    name=block["name"],
                    input=block["input"],
                ))
            else:
                content.append(_ContentBlock(**block))

        return _Response(
            stop_reason=data.get("stop_reason", "end_turn"),
            content=content,
        )


class BedrockClient:
    """Drop-in replacement for anthropic.Anthropic() / AnthropicBedrock() using boto3."""

    def __init__(self, model_region: str = BEDROCK_REGION):
        session = _make_session()
        boto_client = session.client("bedrock-runtime", region_name=model_region)
        self.messages = _Messages(boto_client)
