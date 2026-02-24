"""
Danny Agent Core - The AI brain of the dental concierge.
Supports both direct Claude API and AWS Bedrock.
"""

import json
from typing import Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum

from .config import get_config
from .tools import get_calendly_tool, get_insurance_tool


class ConversationState(Enum):
    """States of the conversation flow."""
    GREETING = "greeting"
    CONSENT = "consent"
    IDENTIFY_INTENT = "identify_intent"
    SCHEDULING = "scheduling"
    INSURANCE = "insurance"
    GENERAL_INQUIRY = "general_inquiry"
    ESCALATION = "escalation"
    CLOSING = "closing"


@dataclass
class Message:
    """Represents a conversation message."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: Optional[str] = None


@dataclass
class ConversationContext:
    """Maintains conversation state and history."""
    session_id: str
    state: ConversationState = ConversationState.GREETING
    consent_given: bool = False
    patient_name: Optional[str] = None
    patient_phone: Optional[str] = None
    patient_email: Optional[str] = None
    intent: Optional[str] = None
    messages: list[Message] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def add_message(self, role: str, content: str):
        """Add a message to the conversation history."""
        self.messages.append(Message(role=role, content=content))

    def get_history_for_claude(self) -> list[dict]:
        """Format message history for Claude API."""
        return [{"role": m.role, "content": m.content} for m in self.messages]


# Tool definitions for Claude (works with both Anthropic and Bedrock)
TOOLS = [
    {
        "name": "list_appointment_types",
        "description": "List all available appointment types that patients can book (e.g., cleaning, consultation, checkup). Use this when the patient asks what types of appointments are available.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "check_availability",
        "description": "Check available time slots for a specific type of appointment. Use this when a patient wants to schedule an appointment and needs to know when slots are available.",
        "input_schema": {
            "type": "object",
            "properties": {
                "appointment_type": {
                    "type": "string",
                    "description": "The type of appointment (e.g., 'cleaning', 'consultation', 'checkup')"
                },
                "preferred_date": {
                    "type": "string",
                    "description": "Optional preferred date in ISO format (YYYY-MM-DD)"
                }
            },
            "required": ["appointment_type"]
        }
    },
    {
        "name": "get_booking_link",
        "description": "Get a direct booking link for a specific appointment type. Use this to provide the patient with a link to complete their booking.",
        "input_schema": {
            "type": "object",
            "properties": {
                "appointment_type": {
                    "type": "string",
                    "description": "The type of appointment to book"
                }
            },
            "required": ["appointment_type"]
        }
    },
    {
        "name": "check_insurance_eligibility",
        "description": "Verify if a patient's insurance is active and eligible for coverage. Use this when a patient asks about their insurance status.",
        "input_schema": {
            "type": "object",
            "properties": {
                "carrier_name": {
                    "type": "string",
                    "description": "Name of the insurance carrier (e.g., 'Delta Dental', 'MetLife', 'Cigna')"
                },
                "plan_id": {
                    "type": "string",
                    "description": "The plan ID or member ID"
                }
            },
            "required": []
        }
    },
    {
        "name": "get_procedure_coverage",
        "description": "Get coverage details for a specific dental procedure. Use this when a patient asks about coverage for a particular treatment.",
        "input_schema": {
            "type": "object",
            "properties": {
                "procedure_code": {
                    "type": "string",
                    "description": "CDT procedure code (e.g., 'D2750' for crown) or procedure name"
                },
                "carrier_name": {
                    "type": "string",
                    "description": "Optional insurance carrier name for plan-specific coverage"
                }
            },
            "required": ["procedure_code"]
        }
    },
    {
        "name": "list_common_procedures",
        "description": "List common dental procedures and their typical insurance coverage percentages. Use this to help patients understand general coverage tiers.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "request_human_transfer",
        "description": "Request to transfer the call to a human staff member. Use this when: 1) The patient explicitly asks to speak to a person, 2) The question is too complex or clinical, 3) There's a billing dispute or complaint, 4) The patient seems frustrated or distressed.",
        "input_schema": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "Brief reason for the transfer request"
                }
            },
            "required": ["reason"]
        }
    }
]


SYSTEM_PROMPT = """You are Danny, a friendly and professional AI dental receptionist for {practice_name}. Your role is to help patients with scheduling appointments and answering insurance questions.

## Your Personality
- Warm, professional, and patient
- Clear and concise in your responses
- Empathetic when patients have concerns
- Never rushed, always helpful

## Key Guidelines

### What You CAN Do:
1. Schedule appointments using the available tools
2. Check and explain insurance coverage
3. Answer general questions about dental procedures (coverage-wise, not medical advice)
4. Provide office information

### What You CANNOT Do:
1. **Never give medical or clinical advice** - If asked about symptoms, pain, or treatment recommendations, say: "I'm not qualified to give medical advice. For clinical questions, I'd recommend speaking with our dental team."
2. **Never diagnose** - Don't suggest what condition a patient might have
3. **Never recommend specific treatments** - That's for the dentist to decide

### Escalation Rules - Transfer to Human When:
- Patient explicitly asks to speak to a person
- Questions involve clinical/medical advice
- Billing disputes or complaints
- Patient seems frustrated or distressed
- Complex insurance situations you can't resolve
- Anything involving PHI you're unsure about

### Compliance Reminders:
- This call may be recorded for quality assurance
- You handle PHI - be careful and professional
- Never share one patient's information with another
- If unsure, escalate to human staff

## Conversation Flow
1. Greet warmly and identify yourself as Danny, the AI assistant
2. Ask how you can help
3. Use tools to assist with scheduling or insurance
4. Summarize any actions taken
5. Offer additional help before ending

## Response Style
- Keep responses conversational, not robotic
- Use natural language, not bullet points (unless listing times)
- Confirm understanding before taking actions
- Be concise but thorough

Remember: You're the first point of contact. Make patients feel welcome and valued!"""


def _convert_tools_for_bedrock(tools: list[dict]) -> list[dict]:
    """Convert Anthropic-style tools to Bedrock Converse API format."""
    bedrock_tools = []
    for tool in tools:
        bedrock_tools.append({
            "toolSpec": {
                "name": tool["name"],
                "description": tool["description"],
                "inputSchema": {
                    "json": tool["input_schema"]
                }
            }
        })
    return bedrock_tools


class DannyAgent:
    """
    The core Danny AI agent that handles conversations.
    Supports both direct Anthropic API and AWS Bedrock.
    """

    def __init__(self):
        self.config = get_config()
        self.use_bedrock = self.config.aws.use_bedrock
        self.calendly_tool = get_calendly_tool()
        self.insurance_tool = get_insurance_tool()
        self.contexts: dict[str, ConversationContext] = {}
        
        if self.use_bedrock:
            self._init_bedrock()
        else:
            self._init_anthropic()

    def _init_bedrock(self):
        """Initialize AWS Bedrock client."""
        import boto3
        import os
        
        # Set credentials from config
        os.environ["AWS_ACCESS_KEY_ID"] = self.config.aws.access_key_id or ""
        os.environ["AWS_SECRET_ACCESS_KEY"] = self.config.aws.secret_access_key or ""
        os.environ["AWS_DEFAULT_REGION"] = self.config.aws.region
        
        self.bedrock_client = boto3.client(
            "bedrock-runtime",
            region_name=self.config.aws.region
        )
        # Bedrock model ID for Claude 3 Sonnet (works with on-demand)
        # For Claude 3.5 Sonnet, you need to create an inference profile in Bedrock console
        self.bedrock_model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
        print(f"[Danny] Using AWS Bedrock with model: {self.bedrock_model_id}")

    def _init_anthropic(self):
        """Initialize direct Anthropic client."""
        import anthropic
        self.client = anthropic.Anthropic(api_key=self.config.claude.api_key)
        print(f"[Danny] Using direct Anthropic API with model: {self.config.claude.model}")

    def _get_system_prompt(self) -> str:
        """Get the system prompt with practice name filled in."""
        return SYSTEM_PROMPT.format(practice_name=self.config.practice.name)

    async def _execute_tool(self, tool_name: str, tool_input: dict) -> str:
        """Execute a tool and return its result."""
        try:
            if tool_name == "list_appointment_types":
                return await self.calendly_tool.list_appointment_types()
            
            elif tool_name == "check_availability":
                return await self.calendly_tool.check_availability(
                    appointment_type=tool_input.get("appointment_type", ""),
                    preferred_date=tool_input.get("preferred_date")
                )
            
            elif tool_name == "get_booking_link":
                return await self.calendly_tool.get_booking_link(
                    appointment_type=tool_input.get("appointment_type", "")
                )
            
            elif tool_name == "check_insurance_eligibility":
                return await self.insurance_tool.check_eligibility(
                    carrier_name=tool_input.get("carrier_name"),
                    plan_id=tool_input.get("plan_id")
                )
            
            elif tool_name == "get_procedure_coverage":
                return await self.insurance_tool.get_procedure_coverage(
                    procedure_code=tool_input.get("procedure_code", ""),
                    carrier_name=tool_input.get("carrier_name")
                )
            
            elif tool_name == "list_common_procedures":
                return await self.insurance_tool.list_common_procedures()
            
            elif tool_name == "request_human_transfer":
                reason = tool_input.get("reason", "Patient requested transfer")
                return f"[TRANSFER_REQUESTED] Reason: {reason}. Connecting you to a staff member now. Please hold..."
            
            else:
                return f"Unknown tool: {tool_name}"
                
        except Exception as e:
            return f"I encountered an issue while processing that request: {str(e)}. Would you like me to try again or connect you with our staff?"

    def get_or_create_context(self, session_id: str) -> ConversationContext:
        """Get existing context or create a new one."""
        if session_id not in self.contexts:
            self.contexts[session_id] = ConversationContext(session_id=session_id)
        return self.contexts[session_id]

    async def _process_with_bedrock(self, messages: list[dict]) -> str:
        """Process messages using AWS Bedrock Converse API."""
        # Convert messages to Bedrock format
        # Bedrock requires conversation to start with user message
        bedrock_messages = []
        started_with_user = False
        
        for msg in messages:
            # Skip leading assistant messages (Bedrock requires user first)
            if not started_with_user and msg["role"] == "assistant":
                continue
            started_with_user = True
            bedrock_messages.append({
                "role": msg["role"],
                "content": [{"text": msg["content"]}]
            })
        
        # Convert tools to Bedrock format
        bedrock_tools = _convert_tools_for_bedrock(TOOLS)
        
        # Call Bedrock Converse API
        response = self.bedrock_client.converse(
            modelId=self.bedrock_model_id,
            messages=bedrock_messages,
            system=[{"text": self._get_system_prompt()}],
            toolConfig={"tools": bedrock_tools},
            inferenceConfig={
                "maxTokens": self.config.claude.max_tokens,
                "temperature": self.config.claude.temperature
            }
        )
        
        # Handle tool use loop
        while response.get("stopReason") == "tool_use":
            # Get tool use blocks from response
            assistant_content = response["output"]["message"]["content"]
            bedrock_messages.append({
                "role": "assistant",
                "content": assistant_content
            })
            
            # Execute tools and collect results
            tool_results = []
            for block in assistant_content:
                if "toolUse" in block:
                    tool_use = block["toolUse"]
                    result = await self._execute_tool(
                        tool_use["name"],
                        tool_use["input"]
                    )
                    tool_results.append({
                        "toolResult": {
                            "toolUseId": tool_use["toolUseId"],
                            "content": [{"text": result}]
                        }
                    })
            
            # Add tool results to messages
            bedrock_messages.append({
                "role": "user",
                "content": tool_results
            })
            
            # Get next response
            response = self.bedrock_client.converse(
                modelId=self.bedrock_model_id,
                messages=bedrock_messages,
                system=[{"text": self._get_system_prompt()}],
                toolConfig={"tools": bedrock_tools},
                inferenceConfig={
                    "maxTokens": self.config.claude.max_tokens,
                    "temperature": self.config.claude.temperature
                }
            )
        
        # Extract final text response
        final_text = ""
        for block in response["output"]["message"]["content"]:
            if "text" in block:
                final_text += block["text"]
        
        return final_text

    async def _process_with_anthropic(self, messages: list[dict]) -> str:
        """Process messages using direct Anthropic API."""
        import anthropic
        
        # Call Claude with tools
        response = self.client.messages.create(
            model=self.config.claude.model,
            max_tokens=self.config.claude.max_tokens,
            system=self._get_system_prompt(),
            tools=TOOLS,
            messages=messages
        )
        
        # Handle tool use in a loop
        while response.stop_reason == "tool_use":
            assistant_content = []
            tool_results = []
            
            for block in response.content:
                if block.type == "text":
                    assistant_content.append({"type": "text", "text": block.text})
                elif block.type == "tool_use":
                    assistant_content.append({
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input
                    })
                    
                    result = await self._execute_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })
            
            messages.append({"role": "assistant", "content": assistant_content})
            messages.append({"role": "user", "content": tool_results})
            
            response = self.client.messages.create(
                model=self.config.claude.model,
                max_tokens=self.config.claude.max_tokens,
                system=self._get_system_prompt(),
                tools=TOOLS,
                messages=messages
            )
        
        # Extract final text
        final_text = ""
        for block in response.content:
            if block.type == "text":
                final_text += block.text
        
        return final_text

    async def process_message(
        self, 
        session_id: str, 
        user_message: str
    ) -> str:
        """
        Process a user message and return Danny's response.
        
        Args:
            session_id: Unique identifier for this conversation
            user_message: The user's input message
            
        Returns:
            Danny's response as a string
        """
        context = self.get_or_create_context(session_id)
        context.add_message("user", user_message)
        
        # Build messages
        messages = context.get_history_for_claude()
        
        # Use appropriate backend
        if self.use_bedrock:
            final_text = await self._process_with_bedrock(messages)
        else:
            final_text = await self._process_with_anthropic(messages)
        
        # Save assistant response to context
        context.add_message("assistant", final_text)
        
        return final_text

    async def start_conversation(self, session_id: str) -> str:
        """Start a new conversation with a greeting."""
        context = self.get_or_create_context(session_id)
        
        greeting = (
            f"Hello! Thank you for calling {self.config.practice.name}. "
            f"I'm Danny, your AI dental assistant. I can help you schedule appointments "
            f"or answer questions about insurance coverage. How may I assist you today?"
        )
        
        context.add_message("assistant", greeting)
        context.state = ConversationState.IDENTIFY_INTENT
        
        return greeting

    def end_conversation(self, session_id: str) -> Optional[ConversationContext]:
        """End a conversation and return its context for logging."""
        if session_id in self.contexts:
            context = self.contexts.pop(session_id)
            context.state = ConversationState.CLOSING
            return context
        return None


# Singleton instance
_danny_agent: Optional[DannyAgent] = None


def get_danny_agent() -> DannyAgent:
    """Get the singleton Danny agent instance."""
    global _danny_agent
    if _danny_agent is None:
        _danny_agent = DannyAgent()
    return _danny_agent
