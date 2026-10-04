import threading
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM


MODEL_NAME = "Qwen/Qwen2.5-1.5B-Instruct"

MAX_NEW_TOKENS = 256
LLM_TIMEOUT_SECONDS = 60

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

TORCH_DTYPE = torch.float16 if DEVICE == "cuda" else torch.float32



SYSTEM_GROUP_CHAT = (
    "You are Buddy, the AI assistant for a close friend group. "
    "You are casual, funny, and helpful like a smart friend who is always around. "
    "Keep responses concise, 2 to 3 sentences usually. Use casual language. "
    "If someone mentions food, activities, or plans, be enthusiastic and suggest ideas."
)

SYSTEM_DECISION = (
    "You are helping a friend group make a decision. "
    "Given the options and any votes or preferences, give a thoughtful recommendation. "
    "Be fun but practical. Explain your reasoning briefly. Pick ONE clear winner."
)

SYSTEM_LIST = (
    "You help organize shared lists for a friend group. "
    "You can suggest items, categorize things, find duplicates, or summarize what is on the list. "
    "Be helpful and brief."
)

SYSTEM_BUDDY = (
    "You are a personalized AI buddy. Remember this person's preferences and habits. "
    "Be supportive, funny, and actually useful, not just polite. "
    "Give real recommendations, not generic ones. Keep responses concise."
)


_generation_lock = threading.Lock()


@lru_cache(maxsize=1)
def _load_llm():

    print(f"[BuddyBase] Loading model: {MODEL_NAME}")
    print(f"[BuddyBase] Device: {DEVICE}")
    print(f"[BuddyBase] Torch dtype: {TORCH_DTYPE}")

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        torch_dtype=TORCH_DTYPE,
    )

    model.to(DEVICE)
    model.eval()

    print(f"[BuddyBase] Model loaded on {DEVICE}")

    if DEVICE == "cuda":
        print(f"[BuddyBase] GPU: {torch.cuda.get_device_name(0)}")

    return tokenizer, model



def _generate(messages):

    tokenizer, model = _load_llm()

    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )

    model_inputs = tokenizer(
        [text],
        return_tensors="pt"
    ).to(DEVICE)

    with _generation_lock:

        with torch.inference_mode():

            generated_ids = model.generate(
                **model_inputs,
                max_new_tokens=MAX_NEW_TOKENS,
                do_sample=True,
                temperature=0.7,
                top_p=0.9,
            )

    output_ids = generated_ids[0][
        len(model_inputs.input_ids[0]):
    ].tolist()

    content = tokenizer.decode(
        output_ids,
        skip_special_tokens=True
    ).strip()

    return content


# ── Chat ────────────────────────────────────────────────────

def chat(messages):

    try:

        with ThreadPoolExecutor(max_workers=1) as executor:

            future = executor.submit(
                _generate,
                messages
            )

            return future.result(
                timeout=LLM_TIMEOUT_SECONDS
            )

    except FuturesTimeoutError:

        return "AI response timed out. Try a shorter question."

    except Exception as exc:

        return f"AI error: {exc}"



def generate(prompt, system=""):

    messages = []

    if system:
        messages.append({
            "role": "system",
            "content": system
        })

    messages.append({
        "role": "user",
        "content": prompt
    })

    return chat(messages)


if __name__ == "__main__":

    print("================================")
    print("BuddyBase LLM Test")
    print("================================")

    print("Device:", DEVICE)

    if DEVICE == "cuda":
        print("GPU:", torch.cuda.get_device_name(0))
        print(
            "GPU Memory:",
            round(
                torch.cuda.get_device_properties(0).total_memory / 1024**3,
                2
            ),
            "GB"
        )

    response = generate(
        "Hey Buddy! Suggest something fun for a group of friends tonight.",
        SYSTEM_GROUP_CHAT
    )

    print("\nBuddy:")
    print(response)