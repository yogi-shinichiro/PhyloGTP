from settings import OLLAMA_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT_SECONDS
import json
import urllib.request
import re


def suggest_genes(user_query):

    prompt = f"""
あなたは分子生物学の解析を支援するAIです。

ユーザーは次のようなタンパク質・機能を探しています。

ユーザーの入力:
{user_query}

この内容に関連し、分子系統解析の候補になりそうな
ヒトの遺伝子を5つ提案してください。

必ず正式なヒト遺伝子シンボルを使用してください。

以下のJSON形式だけで回答してください。
Markdownや説明文は付けないでください。

[
  {{
    "gene": "ACTA1"
  }},
  {{
    "gene": "MYH1"
  }},
  {{
    "gene": "MYH7"
  }},
  {{
    "gene": "TPM3"
  }},
  {{
    "gene": "TTN"
  }}
]

上記の遺伝子名は出力形式の例です。
例をそのまま返すのではなく、
ユーザーの入力内容に応じて候補を選んでください。

必ず5個の異なる遺伝子を返してください。
"""

    data = json.dumps({
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False
    }).encode("utf-8")

    request = urllib.request.Request(
        OLLAMA_URL + "/api/generate",
        data=data,
        headers={
            "Content-Type": "application/json"
        }
    )

    with urllib.request.urlopen(
        request,
        timeout=OLLAMA_TIMEOUT_SECONDS
    ) as response:

        result = json.loads(
            response.read().decode("utf-8")
        )

    text = result["response"].strip()

    # ```json が付いた場合に削除
    text = re.sub(
        r"^```(?:json)?\s*",
        "",
        text
    )

    text = re.sub(
        r"\s*```$",
        "",
        text
    )

    genes = json.loads(text)

    return genes
