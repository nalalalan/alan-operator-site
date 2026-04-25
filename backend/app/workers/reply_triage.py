def classify_reply(reply_text: str) -> str:
    text = reply_text.lower()
    if any(token in text for token in ["interested", "sounds good", "let's do it", "how much"]):
        return "interested"
    if any(token in text for token in ["not interested", "stop", "unsubscribe"]):
        return "negative"
    return "unclear"
