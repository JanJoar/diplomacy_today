import os
from functools import lru_cache

import requests
import time

model_name = "gpt-5-nano"

endpoints = {
    "gpt-3.5-turbo": "https://api.openai.com/v1/chat/completions",
    "text-davinci-003": "https://api.openai.com/v1/completions",
    "gpt-4": "https://api.openai.com/v1/chat/completions",
    "gpt-4o": "https://api.openai.com/v1/chat/completions",
    "gpt-4o-mini": "https://api.openai.com/v1/chat/completions",
    "gpt-5-nano": "https://api.openai.com/v1/chat/completions",
}


@lru_cache(500)
def ping_gpt(prompt, max_tokens=400, model_name=model_name, temp=0):
    print("Connecting to OpenAI...\n")
    time.sleep(1) # This is to avoid tripping up openai's rate
                  # limiting when sending many orders.
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    endpoint = endpoints[model_name]
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
    }
    json_data = get_json_data(model_name, prompt, max_tokens, temp)
    response = requests.post(endpoint, headers=headers, json=json_data)
    res = response.json()
    answer = parse_res(model_name, res)
    return answer

def ping_gpt_again(reply, prompt, answer, model_name=model_name):
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    #  model_name = "text-davinci-003"
    endpoint = endpoints[model_name]
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
    }
    json_data = get_json_data(model_name, prompt)
    json_data["messages"] += [{"role": "assistant", "content": answer}]
    json_data["messages"] += [{"role": "user", "content": reply}]
    response = requests.post(endpoint, headers=headers, json=json_data)
    res = response.json()
    new_answer = parse_res(model_name, res)
    return new_answer


def get_json_data(model_name, prompt, max_tokens=400, temp=0):
    if model_name in ["gpt-3.5-turbo", "gpt-4", "gpt-4o", "gpt-4o-mini", "gpt-5-nano"]:
        json_data = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temp,
            #  "max_tokens": conf["answer_max_tokens"],
        }
    else:
        json_data = {
            "model": model_name,
            "prompt": prompt,
            "temperature": temp,
            "max_tokens": max_tokens,
        }
    return json_data


def parse_res(model_name, res):
    if model_name in ["gpt-3.5-turbo", "gpt-4", "gpt-4o", "gpt-4o-mini", "gpt-5-nano"]:
        answer = res["choices"][0]["message"]["content"]
    else:
        answer = res["choices"][0]["text"]
    return answer
