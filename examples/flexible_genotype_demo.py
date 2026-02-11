#!/usr/bin/env python3
"""
Demo: Flexible PersonaGenotype with Custom Attributes

This demonstrates how the new flexible PersonaGenotype structure allows
the LLM to define completely custom attributes beyond the standard ones.

Requirements:
    Set PYTHONPATH to include the snackPersona directory:
    export PYTHONPATH=/path/to/snackPersona:$PYTHONPATH
    
    Or run from the repository root:
    cd /path/to/snackPersona && python3 snackPersona/examples/flexible_genotype_demo.py
"""

from snackPersona.utils.data_models import PersonaGenotype
from snackPersona.compiler.compiler import compile_persona


def main():
    print("=" * 80)
    print("Flexible PersonaGenotype Demo")
    print("=" * 80)
    print()
    
    # Example 1: Standard attributes (backward compatible)
    print("Example 1: Standard Persona (backward compatible)")
    print("-" * 80)
    standard_persona = PersonaGenotype(
        name="Alice",
        attributes={
            "age": 25,
            "occupation": "Digital Artist",
            "backstory": "Always loved drawing.",
            "core_values": ["creativity", "freedom"],
            "hobbies": ["sketching"],
            "communication_style": "enthusiastic",
            "goals": ["become famous"]
        }
    )
    print(f"Persona: {standard_persona.name}")
    print(f"Age: {standard_persona.get('age')}")
    print(f"Occupation: {standard_persona.get('occupation')}")
    print()
    
    # Example 2: Persona with completely custom attributes
    print("Example 2: Persona with Custom Attributes")
    print("-" * 80)
    custom_persona = PersonaGenotype(
        name="Zephyr",
        attributes={
            "age": 28,
            "occupation": "Time Traveler",
            "backstory": "Born in 2156, accidentally sent back to 2024.",
            "favorite_quote": "The future is not set in stone, but carved in time.",
            "secret_ambition": "Prevent the AI singularity of 2087",
            "speaking_accent": "Futuristic slang mixed with archaic terms",
            "pet_peeves": ["people who waste resources", "temporal paradoxes"],
            "hidden_talent": "Can predict weather patterns with 97% accuracy",
            "communication_style": "cryptic and philosophical",
            "emotional_trigger": "mentions of historical events they witnessed",
            "social_quirk": "always knows what time it is without checking",
            "goals": ["warn people about the future", "find a way home"]
        }
    )
    print(f"Persona: {custom_persona.name}")
    print(f"Occupation: {custom_persona.get('occupation')}")
    print(f"Favorite Quote: {custom_persona.get('favorite_quote')}")
    print(f"Secret Ambition: {custom_persona.get('secret_ambition')}")
    print(f"Speaking Accent: {custom_persona.get('speaking_accent')}")
    print(f"Pet Peeves: {custom_persona.get('pet_peeves')}")
    print(f"Hidden Talent: {custom_persona.get('hidden_talent')}")
    print()
    
    # Compile the custom persona to see how it's rendered
    print("Compiled System Prompt for Custom Persona:")
    print("-" * 80)
    phenotype = compile_persona(custom_persona)
    print(phenotype.system_prompt)
    print()
    print("Policy Instructions:")
    print("-" * 80)
    print(phenotype.policy_instructions)
    print()
    
    # Example 3: Minimal persona (only name required)
    print("Example 3: Minimal Persona (only name)")
    print("-" * 80)
    minimal_persona = PersonaGenotype(
        name="Mystery Person",
        attributes={}
    )
    print(f"Persona: {minimal_persona.name}")
    print(f"Attributes: {minimal_persona.attributes}")
    print()
    
    # Example 4: Persona with nested structures
    print("Example 4: Persona with Nested Custom Data")
    print("-" * 80)
    complex_persona = PersonaGenotype(
        name="Dr. Nova Chen",
        attributes={
            "age": 42,
            "occupation": "Quantum Physicist",
            "credentials": {
                "phd": "MIT - Quantum Computing",
                "postdoc": "CERN - Particle Physics",
                "current_position": "Lead Researcher at QubitLab"
            },
            "research_interests": [
                "quantum entanglement",
                "consciousness studies",
                "multiverse theory"
            ],
            "published_papers": 47,
            "controversy_level": "high - challenges mainstream physics",
            "communication_style": "passionate but technical",
            "signature_phrase": "Reality is what we make it—literally.",
            "goals": ["prove multiverse theory", "bridge quantum and consciousness"]
        }
    )
    print(f"Persona: {complex_persona.name}")
    print(f"Occupation: {complex_persona.get('occupation')}")
    print(f"Credentials: {complex_persona.get('credentials')}")
    print(f"Published Papers: {complex_persona.get('published_papers')}")
    print(f"Signature Phrase: {complex_persona.get('signature_phrase')}")
    print()
    
    print("=" * 80)
    print("Key Takeaway: The LLM can now freely add any custom attributes")
    print("to make personas more interesting and diverse!")
    print("=" * 80)


if __name__ == "__main__":
    main()
