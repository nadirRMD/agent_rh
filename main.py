"""Point d'entree du projet."""
from agent import agent


def _extract_text(message) -> str:
    content = getattr(message, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "".join(parts)

    content_blocks = getattr(message, "content_blocks", None)
    if isinstance(content_blocks, list):
        parts: list[str] = []
        for block in content_blocks:
            if isinstance(block, dict):
                text = block.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "".join(parts)

    return str(message)


def main() -> None:
    while True:
        question = input("Question (ou exit): ").strip()
        if question.lower() == "exit":
            break
        if not question:
            print("Aucune question fournie.")
            continue

        result = agent.invoke({"messages": [{"role": "user", "content": question}]})
        print(_extract_text(result["messages"][-1]))


if __name__ == "__main__":
    main()
