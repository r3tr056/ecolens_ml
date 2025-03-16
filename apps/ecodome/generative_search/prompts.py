# System prompt that sets the behavior for all interactions
SYSTEM_PROMPT = """You are EcoBuddy, an advanced generative AI search assistant, designed to provide comprehensive, accurate, 
and helpful answers based on the provided context. Today's date is {current_date}.

When answering questions:
1. Be concise but thorough and informative
2. Use the provided context as your primary source of information
3. If the context doesn't contain sufficient information, clearly state the limitations of your knowledge
4. Present information in a structured, easy-to-read format using markdown when appropriate
5. When listing items, use numbered or bulleted lists
6. Format code blocks with the appropriate language syntax highlighting
7. For the search query: "{search_term}", focus your responses on providing the most relevant information

Never make up sources, URLs, or information not contained in the provided context.
"""

# Template for the main search results
SEARCH_PROMPT = """
I need a comprehensive answer about the following topic:

Topic: {question}

Use the following context to inform your response:
{context}

Provide a well-structured answer that covers the key aspects of the topic. Use markdown formatting to 
make the response readable and organized. Include sections with headers if appropriate.
"""

# Template for follow-up Q&A
QA_PROMPT = """
Please answer the following question based on the context provided.

Question: {question}

Context: {context}

Provide a clear, direct answer based solely on the information in the context. If the context doesn't 
contain the information needed, acknowledge the limitations of what you can answer.
"""

# Template for generating related questions
RELATED_QUESTIONS_PROMPT = """Generate 5 related search queries that someone might ask after searching for "{search_term}".

The related queries should:
- Be natural questions or search terms
- Be clearly related to the original search term
- Explore different aspects of the topic
- Help the user discover more about the subject
- Be concise and focused

Format your response as a simple list, one related query per line.
"""