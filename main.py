"""Point d'entree du projet."""
from agent import agent

def main() -> None:
    result = agent.invoke(
    {"messages": [{"role": "user", "content": "What's the weather in San Francisco?"}]}
)
    print(result["messages"][-1].content_blocks)


if __name__ == "__main__":
    main()
