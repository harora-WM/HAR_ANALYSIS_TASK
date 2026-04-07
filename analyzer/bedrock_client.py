import json
import os
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, ReadTimeoutError, ConnectTimeoutError
from dotenv import load_dotenv

load_dotenv()

DEFAULT_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "global.anthropic.claude-sonnet-4-6")
DEFAULT_REGION = os.getenv("AWS_REGION", "ap-south-1")

# connect_timeout: time to establish TCP connection
# read_timeout:    time to wait for response bytes — heavy files need more
BOTO_CONFIG = Config(
    connect_timeout=10,
    read_timeout=120,
    retries={"max_attempts": 2, "mode": "standard"},
)


class BedrockClient:
    def __init__(self, region: str = DEFAULT_REGION, model_id: str = DEFAULT_MODEL_ID):
        self.model_id = model_id
        self.client = boto3.client(
            "bedrock-runtime",
            region_name=region,
            config=BOTO_CONFIG,
        )

    def analyze(
        self,
        user_prompt: str,
        system_prompt: str,
        max_tokens: int = 8192,
        temperature: float = 0.2,
    ) -> dict:
        """
        Send a prompt to Claude via Bedrock and return the parsed JSON response.
        temperature=0.2 for consistent, deterministic analysis output.
        """
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": user_prompt}
            ],
        }

        try:
            response = self.client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(body),
                contentType="application/json",
                accept="application/json",
            )
        except ReadTimeoutError:
            raise RuntimeError(
                "Bedrock timed out waiting for a response (120s). "
                "The prompt may be too large — try uploading fewer files at once."
            )
        except ConnectTimeoutError:
            raise RuntimeError("Could not connect to Bedrock (connection timeout). Check your AWS credentials and region.")
        except ClientError as e:
            code = e.response["Error"]["Code"]
            msg = e.response["Error"]["Message"]
            raise RuntimeError(f"Bedrock invocation failed [{code}]: {msg}") from e

        raw = json.loads(response["body"].read())
        text = raw["content"][0]["text"]
        return self._parse_json_response(text)

    def analyze_stream(
        self,
        user_prompt: str,
        system_prompt: str,
        max_tokens: int = 8192,
        temperature: float = 0.2,
    ):
        """
        Stream response chunks from Bedrock. Yields text chunks as they arrive,
        then yields a final dict with key 'final_json' containing the parsed result.
        """
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        }

        try:
            response = self.client.invoke_model_with_response_stream(
                modelId=self.model_id,
                body=json.dumps(body),
                contentType="application/json",
                accept="application/json",
            )
        except ConnectTimeoutError:
            raise RuntimeError("Could not connect to Bedrock. Check your AWS credentials and region.")
        except ClientError as e:
            code = e.response["Error"]["Code"]
            msg = e.response["Error"]["Message"]
            raise RuntimeError(f"Bedrock invocation failed [{code}]: {msg}") from e

        full_text = ""
        for event in response["body"]:
            chunk = event.get("chunk")
            if not chunk:
                continue
            data = json.loads(chunk["bytes"].decode())
            if data.get("type") == "content_block_delta":
                delta = data.get("delta", {})
                if delta.get("type") == "text_delta":
                    token = delta.get("text", "")
                    full_text += token
                    yield {"chunk": token}

        # stream finished — yield the parsed JSON as final item
        yield {"final_json": self._parse_json_response(full_text)}

    def _parse_json_response(self, text: str) -> dict:
        """Extract JSON from Claude's response, handling markdown code fences."""
        text = text.strip()

        # strip ```json ... ``` fences if present
        if text.startswith("```"):
            lines = text.split("\n")
            # remove first and last fence lines
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # fallback: return raw text wrapped so callers don't crash
            return {"raw_response": text, "parse_error": True}
