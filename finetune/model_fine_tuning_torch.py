import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer
from datasets import load_dataset

# Set device to MPS
device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")

# Load model and tokenizer
model_name = "ollama/llama3.1:8b"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype=torch.float16,
    device_map="auto"  # Automatically uses MPS
)

# Load and preprocess dataset
dataset = load_dataset("json", data_files="dataset.jsonl", split="train")

def preprocess_function(examples):
    return tokenizer(examples["prompt"], text_target=examples["response"], truncation=True, max_length=2048)

tokenized_dataset = dataset.map(preprocess_function, batched=True, remove_columns=["prompt", "response"])

# Training arguments
training_args = TrainingArguments(
    output_dir="./gcp-assistant-finetuned",
    num_train_epochs=1,
    per_device_train_batch_size=1,
    learning_rate=2e-5,
    fp16=True,  # Enable mixed precision for MPS
    logging_steps=10,
    save_steps=50,
    save_total_limit=2
)

# Initialize Trainer
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_dataset
)

# Fine-tune
trainer.train()

# Save model
model.save_pretrained("./gcp-assistant-finetuned")
tokenizer.save_pretrained("./gcp-assistant-finetuned")

# Convert to GGUF (requires external tool like llama.cpp)
# Run: python3 convert.py --model ./gcp-assistant-finetuned --outfile ./gcp-assistant-gguf --quantize q4_k_m