import re

def clean_text_for_tts(text: str) -> str:
    """
    Clean markdown and other formatting so the TTS speaks naturally.
    """
    if not text:
        return ""

    # Step 1: Remove code blocks (both fenced and inline)
    text = re.sub(r'```[\s\S]*?```', '', text)      # ```multi-line code blocks```
    text = re.sub(r'`[^`]+`', '', text)             # `inline code`

    # Step 2: Remove links but keep the link text
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)

    # Step 3: Remove headings (## Heading → Heading)
    text = re.sub(r'^\s*#+\s*', '', text, flags=re.MULTILINE)

    # Step 4: Remove bold, italic, strikethrough, etc.
    text = re.sub(r'\*\*\*(.+?)\*\*\*', r'\1', text)   # ***bold italic***
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)       # **bold**
    text = re.sub(r'__(.+?)__', r'\1', text)           # __underline__
    text = re.sub(r'\*(.+?)\*', r'\1', text)           # *italic* or single *
    text = re.sub(r'~~(.+?)~~', r'\1', text)           # ~~strikethrough~~

    # Step 5: Convert list markers to natural pauses
    text = re.sub(r'^\s*[-*+]\s+', ' • ', text, flags=re.MULTILINE)   # bullet lists
    text = re.sub(r'^\s*\d+\.\s+', ' • ', text, flags=re.MULTILINE)   # numbered lists

    # Step 6: Clean up extra whitespace and newlines
    text = re.sub(r'\n\s*\n+', '\n\n', text)   # preserve paragraph breaks
    text = re.sub(r'\s+', ' ', text)           # collapse multiple spaces/tabs

    # Final polish for speech
    text = text.replace('•', ', ')             # make bullets sound better
    text = re.sub(r'\s*([.,!?])\s*', r'\1 ', text)  # fix spacing around punctuation

    return text.strip()