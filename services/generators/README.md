# Edit Plan Generator Pattern

This module implements the **Strategy Pattern** combined with a **Factory Pattern** to make the edit plan generator easily extensible.

## Architecture

```
BaseEditPlanGenerator (Abstract Base Class)
    ├── SemanticEditPlanGenerator (Concrete Strategy)
    └── LegacyEditPlanGenerator (Concrete Strategy)

EditPlanGeneratorFactory (Factory)
    └── Creates and executes appropriate generator
```

## How to Add a New Generator

### Step 1: Create a New Generator Class

Create a new file in `services/generators/` (e.g., `custom_generator.py`):

```python
from typing import Dict, Any, Optional, List
from .base import BaseEditPlanGenerator
from prompts import CUSTOM_SYSTEM_PROMPT  # Your custom prompt
from utils.response_parser import validate_custom_response  # Your custom validator

class CustomEditPlanGenerator(BaseEditPlanGenerator):
    """Your custom generator implementation"""
    
    def __init__(
        self,
        prompt: str,
        custom_data: Dict[str, Any],  # Your custom data
        conversation_history: Optional[List] = None
    ):
        super().__init__(prompt, conversation_history)
        self.custom_data = custom_data
    
    def get_system_prompt(self) -> str:
        """Return your custom system prompt"""
        return CUSTOM_SYSTEM_PROMPT
    
    def build_user_message(
        self,
        document_context: Optional[Dict[str, Any]] = None,
        semantic_document: Optional[Dict[str, Any]] = None,
        selected_range: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build user message for your custom format"""
        user_message = f"User request: {self.prompt}\n\n"
        # Add your custom logic here
        user_message += f"Custom data: {self.custom_data}\n\n"
        return user_message
    
    def validate_response(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate your custom response format"""
        # Add your validation logic
        if "custom_field" not in result:
            raise ValueError("Custom response missing 'custom_field'")
        return result
```

### Step 2: Update the Factory

Modify `services/generators/factory.py`:

```python
from .custom_generator import CustomEditPlanGenerator

class EditPlanGeneratorFactory:
    @staticmethod
    def should_use_custom(custom_data: Optional[Dict[str, Any]]) -> bool:
        """Determine if custom mode should be used"""
        # Add your logic to determine when to use custom generator
        return custom_data is not None and custom_data.get("enabled", False)
    
    @staticmethod
    def create_generator(
        prompt: str,
        conversation_history: Optional[List] = None,
        semantic_document: Optional[Dict[str, Any]] = None,
        custom_data: Optional[Dict[str, Any]] = None  # Add your parameter
    ) -> BaseEditPlanGenerator:
        """Factory method - add your custom generator here"""
        # Check custom first (or in priority order)
        if EditPlanGeneratorFactory.should_use_custom(custom_data):
            return CustomEditPlanGenerator(prompt, custom_data, conversation_history)
        
        # Then check semantic
        use_semantic = EditPlanGeneratorFactory.should_use_semantic(semantic_document)
        if use_semantic:
            return SemanticEditPlanGenerator(prompt, semantic_document, conversation_history)
        
        # Default to legacy
        return LegacyEditPlanGenerator(prompt, conversation_history)
    
    @staticmethod
    def generate(
        prompt: str,
        conversation_history: Optional[List] = None,
        document_context: Optional[Dict[str, Any]] = None,
        semantic_document: Optional[Dict[str, Any]] = None,
        selected_range: Optional[Dict[str, Any]] = None,
        custom_data: Optional[Dict[str, Any]] = None  # Add your parameter
    ) -> Dict[str, Any]:
        """Main generation method - add your parameter"""
        # Create generator (will use custom if applicable)
        generator = EditPlanGeneratorFactory.create_generator(
            prompt,
            conversation_history,
            semantic_document,
            custom_data  # Pass your parameter
        )
        
        # Rest of the method stays the same...
        # The factory handles OpenAI call and validation
```

### Step 3: Update Exports

Update `services/generators/__init__.py`:

```python
from .custom_generator import CustomEditPlanGenerator

__all__ = [
    'BaseEditPlanGenerator',
    'SemanticEditPlanGenerator',
    'LegacyEditPlanGenerator',
    'CustomEditPlanGenerator',  # Add your generator
    'EditPlanGeneratorFactory'
]
```

### Step 4: Update Service Interface (Optional)

If you need to expose your custom generator through the service interface, update `services/edit_plan_generator.py`:

```python
def generate_edit_plan(
    prompt: str,
    conversation_history: Optional[List] = None,
    document_context: Optional[Dict[str, Any]] = None,
    semantic_document: Optional[Dict[str, Any]] = None,
    selected_range: Optional[Dict[str, Any]] = None,
    custom_data: Optional[Dict[str, Any]] = None  # Add your parameter
) -> Dict[str, Any]:
    """Generate edit plan - add your parameter"""
    return EditPlanGeneratorFactory.generate(
        prompt,
        conversation_history,
        document_context,
        semantic_document,
        selected_range,
        custom_data  # Pass your parameter
    )
```

## Benefits of This Pattern

1. **Easy Extension**: Add new generators without modifying existing code
2. **Separation of Concerns**: Each generator handles its own logic
3. **Testability**: Each generator can be tested independently
4. **Maintainability**: Changes to one generator don't affect others
5. **Open/Closed Principle**: Open for extension, closed for modification

## Example Use Cases

- **Multi-language support**: Create generators for different languages
- **Domain-specific generators**: Academic papers, legal documents, etc.
- **Format-specific generators**: Markdown, HTML, LaTeX, etc.
- **AI model-specific generators**: Different prompts for different models

