from openai import OpenAI

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key="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"
)

try:
    completion = client.chat.completions.create(
        model="meta/llama-3.3-70b-instruct",
        messages=[{"role": "user", "content": "Hello, can you see this message?"}],
        temperature=0.2,
        max_tokens=1024
    )
    print("✅ NVIDIA API works!")
    print(completion.choices[0].message.content)
except Exception as e:
    print(f"❌ Error: {e}")
