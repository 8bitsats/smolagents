from smolagents.agents import MultiStepAgent
from smolagents.models import VLLMModel
from smolagents.gradio_ui import GradioUI

# Create a VLLM model
model = VLLMModel(
    model_id="mistralai/Mistral-7B-Instruct-v0.2",
    max_tokens=1024,
    temperature=0.7,
)

# Create a simple agent
agent = MultiStepAgent(
    model=model,
    name="Mistral Agent",
    description="A simple agent powered by Mistral-7B-Instruct",
)

# Create and launch the Gradio UI
ui = GradioUI(agent)
ui.launch(share=True) 