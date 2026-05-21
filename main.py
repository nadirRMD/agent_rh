"""Point d'entree du projet."""
from agent import agent

def main() -> None:
    result = agent.invoke(
    {"messages": [{"role": "user", "content": "je veux posé un congé du 2026-05-22 au 2026-06-06"}]}
)
    print(result["messages"][-1].content_blocks)


if __name__ == "__main__":
    main()
