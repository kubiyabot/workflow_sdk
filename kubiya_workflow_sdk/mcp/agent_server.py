"""Production-ready MCP Agent Server with SSE streaming for Vercel AI SDK."""

import asyncio
import json
import logging
import os
import sys
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager
import traceback

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from mcp_use import MCPClient, MCPAgent
from langchain_core.language_models import BaseChatModel
from .test_agent import get_llm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

# Request/Response models
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    stream: Optional[bool] = False
    format: Optional[str] = "sse"  # "sse" or "vercel"

class DiscoveryResponse(BaseModel):
    provider: str
    model: str
    features: List[str]
    api_version: str
    
# System prompt for better DSL guidance
SYSTEM_PROMPT = """You are a Kubiya workflow assistant that helps create and execute workflows using the Kubiya DSL.

IMPORTANT DSL RULES:
1. NO decorators - just simple DSL: wf = Workflow("name")
2. For Docker steps, use: wf.step("step_name").docker(image="image:tag", command="command")
3. Basic step: wf.step("name", "command")
4. Parallel steps: wf.parallel_steps("name", items=[...], command="...")
5. Parameters: wf.params(key="value")
6. Environment: wf.env(KEY="value")

Example workflow:
```python
from kubiya_workflow_sdk.dsl import Workflow

wf = Workflow("hello-world")
wf.description("Simple hello world")
wf.step("print-hello", "echo 'Hello from Kubiya!'")

# For Docker:
wf.step("docker-hello").docker(
    image="python:3.11-slim",
    command="python -c 'print(\"Hello from Docker!\")'")
```

Available tools:
- compile_workflow: Validate and compile DSL code to JSON
- execute_workflow: Run a workflow (accepts DSL or JSON)
- get_workflow_runners: List available runners
- get_integrations: List available integrations
- get_workflow_secrets: List available secrets

Always compile workflows before executing them to catch errors early."""

class RetryConfig:
    """Configuration for retry logic."""
    max_retries: int = 3
    initial_delay: float = 1.0
    max_delay: float = 10.0
    exponential_base: float = 2.0
    
async def retry_with_backoff(
    func,
    *args,
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 10.0,
    exponential_base: float = 2.0,
    **kwargs
):
    """Execute a function with exponential backoff retry logic."""
    delay = initial_delay
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            if attempt < max_retries - 1:
                logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                await asyncio.sleep(delay)
                delay = min(delay * exponential_base, max_delay)
            else:
                logger.error(f"All {max_retries} attempts failed. Last error: {e}")
    
    raise last_exception

class KubiyaMCPAgentServer:
    """MCP Agent Server for Kubiya workflows."""
    
    def __init__(self, provider: str, model: Optional[str] = None, api_key: Optional[str] = None):
        self.provider = provider
        self.model = model if model is not None else self._get_default_model(provider)
        self.api_key = api_key or os.getenv(f"{provider.upper()}_API_KEY")
        self.llm: Optional[BaseChatModel] = None
        self.mcp_client: Optional[MCPClient] = None
        self.agent: Optional[MCPAgent] = None
        self.retry_config = RetryConfig()
        self._initialized = False
        
    def _get_default_model(self, provider: str) -> str:
        """Get default model for provider."""
        defaults = {
            "openai": "gpt-4o",
            "anthropic": "claude-3-5-sonnet-20241022",
            "together": "deepseek-ai/DeepSeek-V3",
            "groq": "llama-3.3-70b-versatile",
            "ollama": "llama3.2"
        }
        return defaults.get(provider.lower(), "gpt-4o")
        
    async def initialize(self):
        """Initialize the MCP agent with retry logic."""
        if self._initialized:
            logger.info("MCP Agent Server already initialized")
            return
            
        logger.info(f"Initializing MCP Agent Server with {self.provider}/{self.model}")
        
        try:
            # Create LLM with retry
            self.llm = await retry_with_backoff(
                self._create_llm,
                max_retries=self.retry_config.max_retries
            )
            
            # Create MCP client with retry
            self.mcp_client = await retry_with_backoff(
                self._create_mcp_client,
                max_retries=self.retry_config.max_retries
            )
            
            # Create agent
            self.agent = MCPAgent(
                llm=self.llm,
                client=self.mcp_client,
                max_steps=10,
                system_prompt=SYSTEM_PROMPT,
                verbose=True  # Enable verbose logging
            )
            
            self._initialized = True
            logger.info("MCP Agent Server initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize MCP Agent after retries: {e}")
            raise
            
    async def _create_llm(self):
        """Create LLM instance."""
        return get_llm(self.provider, self.model, self.api_key)
        
    async def _create_mcp_client(self):
        """Create MCP client instance."""
        config = {
            "mcpServers": {
                "kubiya": {
                    "command": sys.executable,
                    "args": ["-m", "kubiya_workflow_sdk.mcp.server"],
                    "env": {
                        "KUBIYA_API_KEY": os.getenv("KUBIYA_API_KEY", ""),
                        "MCP_USE_ANONYMIZED_TELEMETRY": "false"
                    }
                }
            }
        }
        return MCPClient.from_dict(config)
            
    async def cleanup(self):
        """Cleanup resources."""
        if self.mcp_client and hasattr(self.mcp_client, 'sessions') and self.mcp_client.sessions:
            try:
                await self.mcp_client.close_all_sessions()
            except Exception as e:
                logger.error(f"Error closing MCP sessions: {e}")
                
    async def ensure_initialized(self):
        """Ensure the server is initialized before processing requests."""
        if not self._initialized:
            await self.initialize()
            
    async def stream_response(self, prompt: str, messages: List[ChatMessage], format: str = "sse"):
        """Stream response using agent.astream() with robust error handling."""
        # Ensure we're initialized
        await self.ensure_initialized()
        
        try:
            # Get the latest user message
            user_message = messages[-1].content if messages else prompt
            
            logger.info(f"Processing request with {format} format: {user_message[:100]}...")
            
            # Track the full response and whether we've sent any data
            full_response = ""
            has_sent_data = False
            chunk_count = 0
            
            # Stream the agent response with timeout
            try:
                async with asyncio.timeout(300):  # 5 minute timeout
                    async for chunk in self.agent.astream(user_message):
                        chunk_count += 1
                        
                        # Debug log every 10th chunk to avoid spam
                        if chunk_count % 10 == 0:
                            logger.debug(f"Processing chunk {chunk_count}")
                        
                        # Extract content from different chunk types
                        if isinstance(chunk, dict):
                            # Handle messages in the chunk
                            if "messages" in chunk and chunk["messages"]:
                                content = chunk["messages"]
                                if isinstance(content, str) and content:
                                    full_response += content
                                    has_sent_data = True
                                    
                                    if format == "vercel":
                                        # Vercel AI SDK format
                                        yield f'0:"{json.dumps(content)}"\n'
                                    else:
                                        # Standard SSE format
                                        data = {
                                            "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
                                            "object": "chat.completion.chunk",
                                            "created": int(datetime.now().timestamp()),
                                            "model": self.model,
                                            "choices": [{
                                                "index": 0,
                                                "delta": {"content": content},
                                                "finish_reason": None
                                            }]
                                        }
                                        yield f"data: {json.dumps(data)}\n\n"
                            
                            # Handle tool calls/actions
                            if "actions" in chunk and chunk["actions"]:
                                for action in chunk["actions"]:
                                    tool_name = action.get("tool", "unknown")
                                    tool_input = action.get("tool_input", {})
                                    
                                    # Log tool usage
                                    logger.info(f"Tool call: {tool_name}")
                                    
                                    if format == "vercel":
                                        # Vercel format for tool calls
                                        yield f'2:{{"type":"tool_call","name":"{tool_name}","input":{json.dumps(tool_input)}}}\n'
                                    else:
                                        # SSE format for tool info
                                        info_data = {
                                            "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
                                            "object": "chat.completion.chunk",
                                            "created": int(datetime.now().timestamp()),
                                            "model": self.model,
                                            "choices": [{
                                                "index": 0,
                                                "delta": {"content": f"\n[Calling tool: {tool_name}]\n"},
                                                "finish_reason": None
                                            }]
                                        }
                                        yield f"data: {json.dumps(info_data)}\n\n"
                            
                            # Handle steps (for debugging)
                            if "steps" in chunk:
                                logger.debug(f"Agent steps: {chunk['steps']}")
                            
                            # Check if this is the final output
                            if "output" in chunk and chunk["output"]:
                                output_content = chunk["output"]
                                if isinstance(output_content, str) and output_content and output_content not in full_response:
                                    full_response = output_content  # Use the final output as the full response
                                    has_sent_data = True
                                    
                                    if format == "vercel":
                                        yield f'0:"{json.dumps(output_content)}"\n'
                                    else:
                                        data = {
                                            "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
                                            "object": "chat.completion.chunk",
                                            "created": int(datetime.now().timestamp()),
                                            "model": self.model,
                                            "choices": [{
                                                "index": 0,
                                                "delta": {"content": output_content},
                                                "finish_reason": None
                                            }]
                                        }
                                        yield f"data: {json.dumps(data)}\n\n"
                        
                        # Small yield to prevent blocking
                        await asyncio.sleep(0)
                        
            except asyncio.TimeoutError:
                logger.error("Agent response timed out after 5 minutes")
                error_msg = "\n\nError: Request timed out. Please try again with a simpler query."
                
                if format == "vercel":
                    yield f'0:"{error_msg}"\n'
                else:
                    yield f"data: {json.dumps({'error': error_msg})}\n\n"
            
            # If we haven't sent any data, send a default message
            if not has_sent_data:
                default_msg = "I'm processing your request. This may take a moment..."
                if format == "vercel":
                    yield f'0:"{default_msg}"\n'
                else:
                    data = {
                        "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
                        "object": "chat.completion.chunk",
                        "created": int(datetime.now().timestamp()),
                        "model": self.model,
                        "choices": [{
                            "index": 0,
                            "delta": {"content": default_msg},
                            "finish_reason": None
                        }]
                    }
                    yield f"data: {json.dumps(data)}\n\n"
            
            # Send completion signal
            if format == "vercel":
                # Vercel completion
                yield f'd:{{"finishReason":"stop"}}\n'
            else:
                # SSE completion
                final_data = {
                    "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
                    "object": "chat.completion.chunk",
                    "created": int(datetime.now().timestamp()),
                    "model": self.model,
                    "choices": [{
                        "index": 0,
                        "delta": {},
                        "finish_reason": "stop"
                    }]
                }
                yield f"data: {json.dumps(final_data)}\n\n"
                yield "data: [DONE]\n\n"
                
            logger.info(f"Completed streaming response. Total chunks: {chunk_count}, Response length: {len(full_response)}")
                
        except Exception as e:
            logger.error(f"Error in stream_response: {e}", exc_info=True)
            error_msg = f"\n\nError: {str(e)}"
            
            if format == "vercel":
                yield f'0:"{json.dumps(error_msg)}"\n'
                yield f'd:{{"finishReason":"error"}}\n'
            else:
                error_data = {
                    "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
                    "object": "chat.completion.chunk",
                    "created": int(datetime.now().timestamp()),
                    "model": self.model,
                    "choices": [{
                        "index": 0,
                        "delta": {"content": error_msg},
                        "finish_reason": "stop"
                    }]
                }
                yield f"data: {json.dumps(error_data)}\n\n"
                yield "data: [DONE]\n\n"

# Global server instance
server_instance: Optional[KubiyaMCPAgentServer] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown."""
    global server_instance
    if server_instance:
        try:
            await server_instance.initialize()
        except Exception as e:
            logger.error(f"Failed to initialize server: {e}")
            # Don't raise - allow server to start even if initialization fails
    yield
    if server_instance:
        await server_instance.cleanup()

# Create FastAPI app
app = FastAPI(title="Kubiya MCP Agent Server", lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    """Health check endpoint."""
    global server_instance
    is_healthy = server_instance is not None and server_instance._initialized
    status = "healthy" if is_healthy else "initializing"
    return {
        "status": status,
        "service": "kubiya-mcp-agent",
        "initialized": is_healthy
    }

@app.get("/discover", response_model=DiscoveryResponse)
async def discover():
    """Discovery endpoint for clients."""
    return DiscoveryResponse(
        provider=server_instance.provider if server_instance else "unknown",
        model=server_instance.model if server_instance else "unknown",
        features=["chat", "streaming", "tools", "workflows"],
        api_version="v1"
    )

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """OpenAI-compatible chat completions endpoint."""
    if not server_instance:
        raise HTTPException(status_code=503, detail="Server not initialized")
    
    # Ensure the agent is initialized
    try:
        await server_instance.ensure_initialized()
    except Exception as e:
        logger.error(f"Failed to initialize agent: {e}")
        raise HTTPException(status_code=503, detail="Failed to initialize agent")
    
    # Extract format from request
    format_type = request.format if hasattr(request, 'format') else "sse"
    
    if request.stream:
        # Streaming response
        logger.info(f"Processing streaming request with {format_type} format")
        
        async def generate():
            try:
                async for chunk in server_instance.stream_response(
                    request.messages[-1].content,
                    request.messages,
                    format=format_type
                ):
                    yield chunk
            except Exception as e:
                logger.error(f"Error in generate: {e}")
                # Send error in appropriate format
                if format_type == "vercel":
                    yield f'0:"Error: {str(e)}"\n'
                    yield f'd:{{"finishReason":"error"}}\n'
                else:
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"
                    yield "data: [DONE]\n\n"
        
        if format_type == "vercel":
            # Vercel AI SDK format
            return StreamingResponse(
                generate(),
                media_type="text/plain",
                headers={
                    "Cache-Control": "no-cache",
                    "X-Content-Type-Options": "nosniff",
                }
            )
        else:
            # Standard SSE format
            return StreamingResponse(
                generate(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Content-Type-Options": "nosniff",
                }
            )
    else:
        # Non-streaming response
        try:
            result = await retry_with_backoff(
                server_instance.agent.run,
                request.messages[-1].content,
                max_retries=2
            )
            
            return {
                "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
                "object": "chat.completion",
                "created": int(datetime.now().timestamp()),
                "model": request.model,
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": result
                    },
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0
                }
            }
        except Exception as e:
            logger.error(f"Error processing request: {e}")
            raise HTTPException(status_code=500, detail=str(e))

def run_server(provider: str, model: Optional[str] = None, api_key: Optional[str] = None, 
               host: str = "0.0.0.0", port: int = 8000):
    """Run the MCP agent server."""
    global server_instance
    
    logger.info(f"Starting Kubiya MCP Agent Server on {host}:{port}")
    logger.info(f"Provider: {provider}, Model: {model}")
    logger.info(f"Endpoints: http://{host}:{port}/")
    
    # Create server instance
    server_instance = KubiyaMCPAgentServer(provider, model, api_key)
    
    # Run the server
    uvicorn.run(app, host=host, port=port, log_level="info")

if __name__ == "__main__":
    # For testing
    run_server("together", "deepseek-ai/DeepSeek-V3") 