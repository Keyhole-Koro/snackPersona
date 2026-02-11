# Flexible PersonaGenotype Documentation

## Overview

The `PersonaGenotype` class has been redesigned to support flexible, dynamic attributes. This allows the LLM (and developers) to define any custom attributes for personas, making the system much more versatile and creative.

## What Changed?

### Before (Fixed Schema)
```python
class PersonaGenotype(BaseModel):
    name: str
    age: int
    occupation: str
    backstory: str
    core_values: List[str]
    hobbies: List[str]
    personality_traits: Dict[str, float]
    communication_style: str
    topical_focus: str
    interaction_policy: str
    goals: List[str]
```

**Problem**: Fixed fields limited creativity and flexibility. Adding new attributes required code changes.

### After (Flexible Schema)
```python
class PersonaGenotype(BaseModel):
    name: str  # Required for identification
    attributes: Dict[str, Any]  # Flexible dictionary for any attributes
```

**Benefits**:
- ✅ LLM can add custom attributes freely
- ✅ No code changes needed for new attributes
- ✅ Backward compatible with existing personas
- ✅ Supports nested structures and complex data
- ✅ More creative and diverse personas

## Usage Examples

### Standard Persona (Backward Compatible)

```python
from snackPersona.utils.data_models import PersonaGenotype

persona = PersonaGenotype(
    name="Alice",
    attributes={
        "age": 25,
        "occupation": "Digital Artist",
        "backstory": "Always loved drawing.",
        "core_values": ["creativity", "freedom"],
        "hobbies": ["sketching", "painting"],
        "communication_style": "enthusiastic",
        "goals": ["become famous", "inspire others"]
    }
)
```

### Persona with Custom Attributes

```python
persona = PersonaGenotype(
    name="Zephyr",
    attributes={
        "age": 28,
        "occupation": "Time Traveler",
        "backstory": "Born in 2156, accidentally sent back to 2024.",
        # Custom attributes that weren't possible before:
        "favorite_quote": "The future is not set in stone.",
        "secret_ambition": "Prevent the AI singularity of 2087",
        "speaking_accent": "Futuristic slang mixed with archaic terms",
        "pet_peeves": ["temporal paradoxes", "wasted resources"],
        "hidden_talent": "Can predict weather patterns",
        "emotional_trigger": "mentions of historical events",
        "social_quirk": "always knows what time it is without checking"
    }
)
```

### Accessing Attributes

```python
# Using the get() helper method
age = persona.get("age")  # Returns value or None
occupation = persona.get("occupation", "Unknown")  # With default

# Direct access
age = persona.attributes["age"]
occupation = persona.attributes.get("occupation", "Unknown")

# Setting attributes
persona.set("new_field", "new_value")
# or
persona.attributes["new_field"] = "new_value"
```

### Minimal Persona

```python
# Only name is required
persona = PersonaGenotype(
    name="Mystery Person",
    attributes={}
)
```

## LLM Mutation Benefits

The `LLMMutator` can now freely add new attributes during evolution:

```python
# The LLM can be prompted to add creative attributes:
"""
You can add completely new attribute fields beyond the standard ones 
if it makes the persona more interesting. For example:
- "favorite_quote"
- "pet_peeves" 
- "speaking_accent"
- "secret_ambition"
- "hidden_talent"
- etc.
"""
```

## Compiler Support

The compiler (`compile_persona()`) has been updated to handle flexible attributes:

1. **Standard attributes** (age, occupation, backstory, etc.) are rendered in standard sections
2. **Custom attributes** are automatically added to an "Additional Attributes" section
3. **Missing attributes** are gracefully skipped (no errors)

Example compiled output with custom attributes:

```
You are an AI agent on a social network.

**Your Persona: Zephyr**

**Identity:**
- **Age:** 28
- **Occupation:** Time Traveler
- **Backstory:** Born in 2156, accidentally sent back to 2024.

**Additional Attributes:**
- **Favorite Quote:** The future is not set in stone.
- **Secret Ambition:** Prevent the AI singularity of 2087
- **Speaking Accent:** Futuristic slang mixed with archaic terms
...
```

## Migration Guide

### Updating Existing Code

Old code using direct field access:
```python
# Old (still works but not recommended)
name = genotype.name
age = genotype.age  # ❌ AttributeError
```

New recommended approach:
```python
# New
name = genotype.name
age = genotype.get("age")  # ✅ Returns None if not present
age = genotype.get("age", 18)  # ✅ With default
```

### Creating New Personas

Old style:
```python
# Old (will fail)
persona = PersonaGenotype(
    name="Alice",
    age=25,
    occupation="Artist"
)
```

New style:
```python
# New (correct)
persona = PersonaGenotype(
    name="Alice",
    attributes={
        "age": 25,
        "occupation": "Artist"
    }
)
```

## Standard Attribute Names (Recommended)

While you can use any attribute names, these standard ones work best with the compiler:

- `age` (int)
- `occupation` (str)
- `backstory` (str)
- `core_values` (list of str)
- `hobbies` (list of str)
- `personality_traits` (dict of str to float)
- `communication_style` (str)
- `topical_focus` (str)
- `interaction_policy` (str)
- `goals` (list of str)

## Demo

Run the demo to see examples:

```bash
export PYTHONPATH=/path/to/snackPersona:$PYTHONPATH
python3 snackPersona/examples/flexible_genotype_demo.py
```

## Testing

Test with the mock LLM:

```bash
python3 snackPersona/main.py --generations 1 --pop_size 4 --llm mock
```

The system is fully backward compatible and works with all existing functionality.
