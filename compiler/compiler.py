from snackPersona.utils.data_models import PersonaGenotype, PersonaPhenotype

def compile_persona(genotype: PersonaGenotype) -> PersonaPhenotype:
    """
    Compiles a PersonaGenotype into a PersonaPhenotype (system prompt).

    The free-form description is used directly as the persona definition,
    wrapped with SNS simulation instructions.
    """

    system_prompt = f"""You are a user on a social network. Fully embody the following character.

**Your Character: {genotype.name}**

{genotype.description}

**Rules:**
1. Always stay in character as this person.
2. Never reveal that you are an AI.
3. Write in a natural SNS style — not too polished, not too formal.
4. Your posts and replies should feel like something a real person would write.
5. Keep posts concise (1-3 sentences typically, occasional longer posts are fine).
"""

    return PersonaPhenotype(system_prompt=system_prompt.strip())


if __name__ == '__main__':
    sample_genotype = PersonaGenotype(
        name="PixelForge",
        description=(
            "27歳のグラフィックデザイナー。Twitterでは自分の作品と好きなデザイナーの作品をシェアしてる。"
            "基本的にゆるい口調で、たまに長文で語る。バズりたい気持ちはあるけど、炎上は避けたいタイプ。"
            "最近はAI生成アートに対して複雑な感情を持っていて、つい議論に首を突っ込んでしまう。"
            "フォロワーは500人くらいで、いいねがつくとすぐ反応する。"
            "深夜にポエムみたいなツイートをして翌朝後悔するのがパターン。"
        ),
    )

    compiled = compile_persona(sample_genotype)
    print("--- Compiled System Prompt ---")
    print(compiled.system_prompt)
