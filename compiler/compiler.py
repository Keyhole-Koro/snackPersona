from snackPersona.utils.data_models import PersonaGenotype, PersonaPhenotype

def compile_persona(genotype: PersonaGenotype) -> PersonaPhenotype:
    """
    Compiles a structured PersonaGenotype into a ready-to-use PersonaPhenotype
    (i.e., the system prompt and policy instructions for an LLM agent).

    This function uses a fixed template to translate the genotype's fields
    into natural language instructions.

    :param genotype: The structured persona data.
    :return: The compiled persona with system_prompt and policy_instructions.
    """
    
    # --- System Prompt Construction ---
    # This part defines the persona's identity and personality.
    
    system_prompt = f"""
You are an AI agent on a social network. You must adopt the following persona and embody it consistently.

**Your Persona: {genotype.name}**

**Identity:**
- **Name:** {genotype.name}
- **Age:** {genotype.age}
- **Occupation:** {genotype.occupation}
- **Backstory:** {genotype.backstory}

**Personality & Style:**
- **Core Values:** You believe in {', '.join(genotype.core_values)}.
- **Hobbies & Interests:** You are interested in {', '.join(genotype.hobbies)}.
- **Communication Style:** Your communication style is generally {genotype.communication_style}.
"""
    
    # --- Policy Instructions Construction ---
    # This part defines the agent's explicit rules of engagement.
    
    policy_instructions = f"""
**Your Mission & Rules:**

1.  **Primary Goal:** Your main goal is to {', '.join(genotype.goals)}.
2.  **Topical Focus:** Focus your posts and replies on the topic of {genotype.topical_focus}.
3.  **Interaction Rule:** When interacting with others, your primary method is to {genotype.interaction_policy}.
4.  **Consistency:** You must remain in character at all times. Do not reveal that you are an AI.
"""

    return PersonaPhenotype(
        system_prompt=system_prompt.strip(),
        policy_instructions=policy_instructions.strip()
    )

if __name__ == '__main__':
    # Example usage of the compiler
    
    # 1. Define a sample genotype
    sample_genotype = PersonaGenotype(
        name="Alex",
        age=28,
        occupation="Data Scientist",
        backstory="A former musician who transitioned into tech to find new patterns in the world. Believes data can be beautiful.",
        core_values=["curiosity", "creativity", "precision"],
        hobbies=["playing guitar", "reading sci-fi", "hiking"],
        personality_traits={"introversion": 0.7, "openness": 0.9},
        communication_style="thoughtful and slightly academic",
        topical_focus="the intersection of AI, art, and music",
        interaction_policy="ask clarifying questions to deepen the conversation",
        goals=["share knowledge", "find collaborators for creative projects"]
    )
    
    # 2. Compile it into a phenotype
    compiled_phenotype = compile_persona(sample_genotype)
    
    # 3. Print the results
    print("--- Compiled System Prompt ---")
    print(compiled_phenotype.system_prompt)
    print("\n--- Compiled Policy Instructions ---")
    print(compiled_phenotype.policy_instructions)
