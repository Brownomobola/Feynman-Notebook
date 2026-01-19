from google import genai
import re
import json
from pydantic import BaseModel
from typing import List, Dict, Any


class StreamGenerator:
    """
    Handles streaming of AI analysis responses in Server-Sent Events (SSE) format.
    Progressively parses and streams JSON fields as they're generated.
    """
    
    def __init__(self, client: genai.Client, system_prompt: str, prompt_parts: list, response_schema: type[BaseModel]):
        """
        Initialize the stream generator.
        
        Args:
            client: The Gemini AI client instance
            system_prompt: The system instruction for the AI
            prompt_parts: The prompt content to send to the AI
            response_schema: The Pydantic schema defining the expected response structure
        """
        self.client = client
        self.system_prompt = system_prompt
        self.prompt_parts = prompt_parts
        self.response_schema = response_schema
    
    async def generate(self):
        """
        Async generator that streams the AI response in SSE format.
        Yields chunks of data as they become available.
        Handles string, array, and boolean field types.
        """
        accumulated_text = ""
        field_positions = {}
        
        # Get schema properties
        schema_properties = self.response_schema.model_json_schema().get('properties', {})
        
        # Initialize field positions for string fields
        for field_name, field_info in schema_properties.items():
            field_type = field_info.get('type', '')
            if field_type == 'string':
                field_positions[field_name] = 0
        
        # Track array field separately
        array_field_name = None
        for field_name, field_info in schema_properties.items():
            if field_info.get('type') == 'array':
                array_field_name = field_name
                break
        
        # Track boolean fields
        boolean_fields = []
        boolean_fields_sent = {}
        for field_name, field_info in schema_properties.items():
            if field_info.get('type') == 'boolean':
                boolean_fields.append(field_name)
                boolean_fields_sent[field_name] = False
        
        try:
            response = await self.client.aio.models.generate_content_stream(
                model="gemini-2.0-flash-exp",
                config={
                    'system_instruction': self.system_prompt,
                    'response_mime_type': 'application/json',
                    'response_schema': self.response_schema
                },
                contents={'parts': self.prompt_parts}
            )
            
            last_array_content = ""
            
            async for chunk in response:
                if chunk.text:
                    accumulated_text += chunk.text
                    
                    # Extract and stream string fields progressively
                    for field_name in field_positions.keys():
                        pattern = rf'"{field_name}"\s*:\s*"([^"]*(?:\\"[^"]*)*)'
                        match = re.search(pattern, accumulated_text)
                        
                        if match:
                            current_value = match.group(1)
                            # Unescape JSON strings
                            current_value = current_value.replace('\\"', '"')
                            current_value = current_value.replace('\\n', '\n')
                            current_value = current_value.replace('\\t', '\t')
                            
                            # Get only new content for this field
                            last_pos = field_positions[field_name]
                            new_content = current_value[last_pos:]
                            
                            if new_content:
                                # Send SSE formatted data
                                event_data = {
                                    'type': 'partial',
                                    'field': field_name,
                                    'content': new_content,
                                    'is_complete': False
                                }
                                yield f"data: {json.dumps(event_data)}\n\n".encode('utf-8')
                                field_positions[field_name] = len(current_value)
                    
                    # Handle boolean fields
                    for field_name in boolean_fields:
                        if not boolean_fields_sent[field_name]:
                            # Pattern to match boolean values (true or false)
                            bool_pattern = rf'"{field_name}"\s*:\s*(true|false)'
                            bool_match = re.search(bool_pattern, accumulated_text)
                            
                            if bool_match:
                                bool_value = bool_match.group(1) == 'true'
                                event_data = {
                                    'type': 'boolean',
                                    'field': field_name,
                                    'content': bool_value,
                                    'is_complete': False
                                }
                                yield f"data: {json.dumps(event_data)}\n\n".encode('utf-8')
                                boolean_fields_sent[field_name] = True
                    
                    # Handle array field if it exists
                    if array_field_name:
                        # Extract array content
                        array_pattern = rf'"{array_field_name}"\s*:\s*\[(.*?)(?:\]|$)'
                        array_match = re.search(array_pattern, accumulated_text, re.DOTALL)
                        
                        if array_match:
                            array_content = array_match.group(1)
                            
                            # Check if there's new array content
                            if array_content != last_array_content:
                                # Extract individual array items
                                items = re.findall(r'"([^"]*(?:\\"[^"]*)*)"', array_content)
                                
                                if items:
                                    # Unescape items
                                    unescaped_items = [
                                        item.replace('\\"', '"').replace('\\n', '\n')
                                        for item in items
                                    ]
                                    
                                    event_data = {
                                        'type': 'array',
                                        'field': array_field_name,
                                        'content': unescaped_items,
                                        'is_complete': False
                                    }
                                    yield f"data: {json.dumps(event_data)}\n\n".encode('utf-8')
                                    last_array_content = array_content
            
            # Try to parse complete JSON at the end
            try:
                complete_json = json.loads(accumulated_text)
                completion_data = {
                    'type': 'complete',
                    'field': 'all',
                    'content': complete_json,
                    'is_complete': True
                }
                yield f"data: {json.dumps(completion_data)}\n\n".encode('utf-8')
            except json.JSONDecodeError:
                # Send accumulated text as fallback
                completion_data = {
                    'type': 'complete',
                    'field': 'all',
                    'content': accumulated_text,
                    'is_complete': True
                }
                yield f"data: {json.dumps(completion_data)}\n\n".encode('utf-8')
            
        except Exception as e:
            error_data = {
                'type': 'error',
                'field': 'error',
                'content': str(e),
                'is_complete': True
            }
            yield f"data: {json.dumps(error_data)}\n\n".encode('utf-8')

class ChatStreamGenerator:
    """
    Handles streaming of conversational AI responses in Server-Sent Events (SSE) format.
    Uses conversation history to provide context-aware responses.
    """
    
    def __init__(self, client: genai.Client, system_prompt: str, conversation_history: List[Dict[str, Any]], user_message: str):
        """
        Initialize the chat stream generator.
        
        Args:
            client: The Gemini AI client instance
            system_prompt: The system instruction for the AI
            conversation_history: List of previous messages in the conversation
            user_message: The current user message
        """
        self.client = client
        self.system_prompt = system_prompt
        self.conversation_history = conversation_history
        self.user_message = user_message
    
    def _build_conversation_contents(self) -> List[Dict[str, Any]]:
        """
        Builds the conversation contents from history and current message.
        
        Returns:
            List of content dictionaries formatted for the Gemini API
        """
        contents = []
        
        # Add conversation history
        for message in self.conversation_history:
            role = message.get('role', 'user')
            content = message.get('content', '')
            
            if role == 'user':
                contents.append({
                    'role': 'user',
                    'parts': [{'text': content}]
                })
            elif role == 'assistant' or role == 'model':
                contents.append({
                    'role': 'model',
                    'parts': [{'text': content}]
                })
        
        # Add current user message
        contents.append({
            'role': 'user',
            'parts': [{'text': self.user_message}]
        })
        
        return contents
    
    async def generate(self):
        """
        Async generator that streams the AI chat response in SSE format.
        Yields text chunks as they become available.
        """
        accumulated_text = ""
        
        try:
            # Build conversation contents
            contents = self._build_conversation_contents()
            
            # Stream the response
            response = await self.client.aio.models.generate_content_stream(
                model="gemini-2.5-flash",
                config={
                    'system_instruction': self.system_prompt
                },
                contents=contents
            )
            
            async for chunk in response:
                if chunk.text:
                    accumulated_text += chunk.text
                    
                    # Send the new text chunk
                    event_data = {
                        'type': 'text',
                        'content': chunk.text,
                        'is_complete': False
                    }
                    yield f"data: {json.dumps(event_data)}\n\n".encode('utf-8')
            
            # Send completion signal
            completion_data = {
                'type': 'complete',
                'content': accumulated_text,
                'is_complete': True
            }
            yield f"data: {json.dumps(completion_data)}\n\n".encode('utf-8')
            
        except Exception as e:
            error_data = {
                'type': 'error',
                'content': str(e),
                'is_complete': True
            }
            yield f"data: {json.dumps(error_data)}\n\n".encode('utf-8')