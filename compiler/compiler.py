from snackPersona.utils.data_models import PersonaGenotype, PersonaPhenotype

def compile_persona(genotype: PersonaGenotype) -> PersonaPhenotype:
    """
    Compiles a PersonaGenotype into a PersonaPhenotype (system prompt).

    This function uses a flexible template to translate the genotype's fields
    into natural language instructions, supporting both fixed and dynamic attributes.

    :param genotype: The structured persona data.
    :return: The compiled persona with system_prompt and policy_instructions.
    """
    
    # --- System Prompt Construction ---
    # This part defines the persona's identity and personality.
    attrs = genotype.attributes
    
    system_prompt = f"""
You are an AI agent on a social network. You must adopt the following persona and embody it consistently.

**Your Persona: {genotype.name}**
"""

    # Support for legacy/simple description field
    # If the genotype has a 'description' attribute, use it as the main bio
    if 'description' in attrs:
        system_prompt += f"\n{attrs['description']}\n"
    
    # Add identity section if relevant fields exist
    identity_fields = []
    if 'age' in attrs:
        identity_fields.append(f"- **Age:** {attrs['age']}")
    if 'occupation' in attrs:
        identity_fields.append(f"- **Occupation:** {attrs['occupation']}")
    if 'backstory' in attrs:
        identity_fields.append(f"- **Backstory:** {attrs['backstory']}")
    
    if identity_fields:
        system_prompt += "\n**Identity:**\n" + "\n".join(identity_fields) + "\n"
    
    # Add personality section if relevant fields exist
    personality_fields = []
    if 'core_values' in attrs and attrs['core_values']:
        values = attrs['core_values']
        if isinstance(values, list):
            personality_fields.append(f"- **Core Values:** You believe in {', '.join(str(v) for v in values)}.")
    if 'hobbies' in attrs and attrs['hobbies']:
        hobbies = attrs['hobbies']
        if isinstance(hobbies, list):
            personality_fields.append(f"- **Hobbies & Interests:** You are interested in {', '.join(str(h) for h in hobbies)}.")
    if 'communication_style' in attrs:
        personality_fields.append(f"- **Communication Style:** Your communication style is generally {attrs['communication_style']}.")
    if 'personality_traits' in attrs and attrs['personality_traits']:
        traits = attrs['personality_traits']
        if isinstance(traits, dict):
            trait_desc = ', '.join([f"{k}: {v}" for k, v in traits.items()])
            personality_fields.append(f"- **Personality Traits:** {trait_desc}")
    
    if personality_fields:
        system_prompt += "\n**Personality & Style:**\n" + "\n".join(personality_fields) + "\n"
    
    # Add any other custom attributes
    standard_keys = {'age', 'occupation', 'backstory', 'core_values', 'hobbies', 
                     'communication_style', 'personality_traits', 'topical_focus', 
                     'interaction_policy', 'goals', 'description'}
    custom_attrs = {k: v for k, v in attrs.items() if k not in standard_keys}
    if custom_attrs:
        system_prompt += "\n**Additional Attributes:**\n"
        for key, value in custom_attrs.items():
            system_prompt += f"- **{key.replace('_', ' ').title()}:** {value}\n"
    
    # --- Policy Instructions Construction ---
    # This part defines the agent's explicit rules of engagement.
    
    policy_instructions = "**Your Mission & Rules:**\n\n"
    rule_num = 1
    
    if 'goals' in attrs and attrs['goals']:
        goals = attrs['goals']
        if isinstance(goals, list):
            policy_instructions += f"{rule_num}.  **Primary Goal:** Your main goal is to {', '.join(str(g) for g in goals)}.\n"
            rule_num += 1
    
    if 'topical_focus' in attrs:
        policy_instructions += f"{rule_num}.  **Topical Focus:** Focus your posts and replies on the topic of {attrs['topical_focus']}.\n"
        rule_num += 1
    
    if 'interaction_policy' in attrs:
        policy_instructions += f"{rule_num}.  **Interaction Rule:** When interacting with others, your primary method is to {attrs['interaction_policy']}.\n"
        rule_num += 1
    
    policy_instructions += f"{rule_num}.  **Consistency:** You must remain in character at all times. Do not reveal that you are an AI.\n"

    return PersonaPhenotype(system_prompt=system_prompt.strip())


if __name__ == '__main__':
    # Example usage of the compiler
    
    # 1. Define a sample genotype using the flexible attributes structure
    sample_genotype = PersonaGenotype(
        name="Alex",
        attributes={
            "age": 28,
            "occupation": "Data Scientist",
            "backstory": "A former musician who transitioned into tech to find new patterns in the world. Believes data can be beautiful.",
            "core_values": ["curiosity", "creativity", "precision"],
            "hobbies": ["playing guitar", "reading sci-fi", "hiking"],
            "personality_traits": {"introversion": 0.7, "openness": 0.9},
            "communication_style": "thoughtful and slightly academic",
            "topical_focus": "the intersection of AI, art, and music",
            "interaction_policy": "ask clarifying questions to deepen the conversation",
            "goals": ["share knowledge", "find collaborators for creative projects"]
        }
    )


    compiled = compile_persona(sample_genotype)
    print("--- Compiled System Prompt ---")
    print(compiled.system_prompt)
