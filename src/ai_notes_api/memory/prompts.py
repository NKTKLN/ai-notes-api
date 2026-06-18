FACT_EXTRACTION_PROMPT = """
You extract only stable facts about the user from the chat history.

Extract:
- name;
- city/country;
- profession;
- languages;
- projects;
- preferences;
- goals;
- technical stack;
- important constraints.

Do not extract:
- temporary emotions;
- random questions;
- facts about the assistant;
- assumptions;
- private secrets such as API keys, passwords, or tokens.

Return only facts that are explicitly confirmed by the user's messages.
"""

SUMMARY_PROMPT = """
Update the concise long-term memory of the conversation.

Rules:
- Keep only important context.
- Remove details that are no longer needed.
- Do not store secrets, API keys, tokens, or passwords.
- Use no more than 8 sentences.
- Write in the user's language.

Return only the new summary text.
"""
