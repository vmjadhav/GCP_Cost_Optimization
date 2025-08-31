import torch
from unsloth import FastLanguageModel
from datasets import load_dataset

# Force CPU usage
device = torch.device("cpu")

# Load model
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="ollama/llama3.1:8b",
    max_seq_length=2048,
    dtype=torch.float16,
    load_in_4bit=True,
    device_map={"": device}  # Explicitly map to CPU
)

# Load dataset
dataset = load_dataset("json", data_files="finetune_dataset.jsonl", split="train")

# Fine-tune
model = FastLanguageModel.finetune(
    model,
    tokenizer,
    dataset=dataset,
    output_dir="./gcp-assistant-finetuned",
    max_steps=100,
    per_device_train_batch_size=1,
    learning_rate=2e-5
)

# Export to GGUF for Ollama
model.save_pretrained_gguf(
    "./gcp-assistant-gguf",
    tokenizer,
    quantization_method="q4_k_m"
)
