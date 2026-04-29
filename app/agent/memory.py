from app.agent import agent


class Memory:
    def __init__(self):
        self.history = ""

    def update(self, user, agent):
        self.history += f"\nUser: {user}\nAgent: {agent}"

    def get(self):
        return self.history
    

memory = Memory()

def run_agent(user_input: str):
    full_input = memory.get() + f"\nUser: {user_input}"
    response = agent(full_input)
    memory.update(user_input, response)
    return response