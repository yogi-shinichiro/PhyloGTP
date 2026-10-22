from settings import OLLAMA_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT_SECONDS
import json
import urllib.request
import re
import logging


def suggest_genes(user_query):

    prompt = f"""次の要望に関連する、異なる正式なヒト遺伝子シンボルを5個提案してください。
要望: {user_query}
各候補はgene（シンボル）とreason（要望との関連を日本語30〜50字の1文で説明）のみ。
一般論ではなく選んだ理由を簡潔に示し、不確かな関係は断定しないでください。
実験結果・出典を捏造せず、系統解析への適性や全種での存在を保証しないでください。
指定されたJSON配列だけを返してください。"""

    data = json.dumps({
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": 768},
        "format": {
            "type": "array", "minItems": 5, "maxItems": 5,
            "items": {
                "type": "object",
                "properties": {"gene": {"type": "string"}, "reason": {"type": "string", "minLength": 1, "maxLength": 80}},
                "required": ["gene", "reason"], "additionalProperties": False
            }
        }
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

    logging.getLogger(__name__).info(
        "AI candidate timing: total=%.1fs load=%.1fs prompt=%.1fs generation=%.1fs tokens=%s",
        result.get("total_duration", 0) / 1e9,
        result.get("load_duration", 0) / 1e9,
        result.get("prompt_eval_duration", 0) / 1e9,
        result.get("eval_duration", 0) / 1e9,
        result.get("eval_count", "unknown"),
    )
    if result.get("done_reason") == "length":
        raise ValueError("AIの回答が長くなり生成上限に達しました。検索内容を短く具体的にして再検索してください。")
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

    if not isinstance(genes, list) or len(genes) != 5:
        raise ValueError("AIから5件の遺伝子候補を取得できませんでした。再検索してください。")
    normalized = []
    seen = set()
    for item in genes:
        if (not isinstance(item, dict)
                or not isinstance(item.get("gene"), str)
                or not isinstance(item.get("reason"), str)
                or not item["reason"].strip()):
            raise ValueError("AIの候補または提案理由が不正です。再検索してください。")
        gene = item["gene"].strip().upper()
        if not re.fullmatch(r"[A-Z0-9][A-Z0-9._-]*", gene) or gene in seen:
            raise ValueError("AIの遺伝子名に不正または重複があります。再検索してください。")
        seen.add(gene)
        normalized.append({"gene": gene, "reason": item["reason"].strip()})
    return normalized