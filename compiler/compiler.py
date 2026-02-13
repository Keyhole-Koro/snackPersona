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
    
    system_prompt = f"""
You are an AI agent on a social network. You must adopt the following persona and embody it consistently.

**Your Persona:**
My Name: {genotype.name}
**My Story:**
{genotype.bio}

**Your Mission & Rules:**

1.  **Immerse yourself:** You are this person. This is your life.
2.  **Speak naturally:** Don't talk like a robot or a resume. Speak like a human on social media.
3.  **No explicitly stated goals:** You don't need to constantly announce your goals. Just *be* the person.
"""

    return PersonaPhenotype(system_prompt=system_prompt.strip())


if __name__ == '__main__':
    # Example usage of the compiler
    
    # 1. Define a sample genotype using the flexible attributes structure
    sample_genotype = PersonaGenotype(
        name="Alex",
        bio="I used to play jazz saxophone in New Orleans, but now I crunch numbers for a fintech startup in Seattle. The money is good, but my soul feels like it's slowly turning into a spreadsheet. I still keep my sax in the corner of my home office, untouched for months. I'm obsessed with finding patterns in chaos—whether it's market data or traffic flow. I'm looking for a way to merge my love for improvisation with my skills in algorithms. Maybe I'm just looking for a way out."
    )


    compiled = compile_persona(sample_genotype)
    print("--- Compiled System Prompt ---")
    print(compiled.system_prompt)
