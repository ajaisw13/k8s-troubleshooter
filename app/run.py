from app.agent.agent import run_agent

if __name__ == "__main__":
    while True:
        q = input("\nYou: ")

        if q.lower() in ["exit", "quit"]:
            break

        pod = input("Pod name (optional, press Enter to skip): ").strip() or None
        print("\nAgent:", run_agent(q, pod_name=pod))
