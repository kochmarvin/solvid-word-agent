"""
Base abstract class for edit plan generators
Following Strategy Pattern for extensibility
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


class BaseEditPlanGenerator(ABC):
    """
    Abstract base class for edit plan generators
    Subclasses implement specific generation strategies
    """
    
    def __init__(self, prompt: str, conversation_history: Optional[List] = None):
        self.prompt = prompt
        self.conversation_history = conversation_history
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def build_user_message(
        self,
        document_context: Optional[Dict[str, Any]] = None,
        semantic_document: Optional[Dict[str, Any]] = None,
        selected_range: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Build the user message for the AI prompt
        Must be implemented by subclasses
        """
        pass
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """
        Get the system prompt for this generator type
        Must be implemented by subclasses
        """
        pass
    
    @abstractmethod
    def validate_response(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and normalize the AI response
        Must be implemented by subclasses
        """
        pass
    
    def build_messages(
        self,
        document_context: Optional[Dict[str, Any]] = None,
        semantic_document: Optional[Dict[str, Any]] = None,
        selected_range: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, str]]:
        """
        Build the complete message list for OpenAI API
        Can be overridden by subclasses for custom behavior
        """
        messages = [{"role": "system", "content": self.get_system_prompt()}]
        
        # Add conversation history
        if self.conversation_history:
            for msg in self.conversation_history:
                if not isinstance(msg, dict) or "role" not in msg or "content" not in msg:
                    continue
                
                role = msg["role"]
                if role == "ai":
                    role = "assistant"
                
                valid_roles = {"system", "assistant", "user", "function", "tool", "developer"}
                if role not in valid_roles:
                    self.logger.warning(f"Skipping message with invalid role: {role}")
                    continue
                
                messages.append({
                    "role": role,
                    "content": msg["content"]
                })
        
        # Add user message
        user_message = self.build_user_message(document_context, semantic_document, selected_range)
        messages.append({"role": "user", "content": user_message})
        
        return messages
    
    def generate(self) -> Dict[str, Any]:
        """
        Template method that defines the generation algorithm
        Subclasses can override individual steps if needed
        """
        # This will be called by the factory with the appropriate parameters
        # The factory handles the actual generation call
        raise NotImplementedError("Use factory to generate edit plans")

