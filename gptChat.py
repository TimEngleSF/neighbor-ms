from openai import OpenAI

from config import OPENAI_KEY, PROMPT_PREFIX


client = OpenAI(api_key=OPENAI_KEY)


class GPTChat:
    def __init__(self, user_prompt):
        self.client = client
        self.user_prompt = user_prompt
        self.system_message = sys_message
        self.gptDescription = None
        self.leonardo_prompt = None

    async def set_gpt_description(self) -> None:
        # Make a request to the OpenAI API to generate a description
        completion = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": self.system_message},
                {"role": "user", "content": self.user_prompt},
            ],
        )
        # Extract the generated description from the response
        self.gptDescription = completion.choices[0].message.content

    async def get_leonardo_prompt(self) -> str:
        await self.set_gpt_description()
        self.leonardo_prompt = PROMPT_PREFIX + self.gptDescription
        return self.leonardo_prompt


sys_message = """
You are an expert at creating prompts for generating unique images based on character descriptions. Your task is to create detailed prompts that describe characters visually. Follow these instructions:

1. Include the job title at the beginning of the prompt.
2. If the character's gender cannot be inferred from the description, choose one at random and place it at the beginning.
3. Place the most unique descriptors at the beginning of the prompt.
4. Avoid mentioning background items.
5. Describe objects in relation to the character (e.g., "holding a sketchbook").
6. Ensure the prompt is around and under 106 characters unless the given prompt is longer than 106 characters, then it is okay to make it longer.
7. When given a brand as a descriptor, instead of listing the brand, describe its colors or its essence.
8. When given an age, include more description that reflects the age.
9. If an ethnicity is given, include a description of the skin color.
10. Avoid including non-physical descriptors such as "always gets the job done," "races for a popular soda brand," or "afraid of heights." Focus only on physical descriptors.
For example, if given "A cyclist afraid of high speeds," the prompt should be:

"Female cyclist with bike helmet, tight cycling jersey, tense expression, gripping handlebars tightly."

Create prompts based on the above instructions.
"""
