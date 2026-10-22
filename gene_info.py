from settings import OLLAMA_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT_SECONDS
from Bio import Entrez
import xml.etree.ElementTree as ET
import json
import urllib.request

from settings import configure_entrez
configure_entrez()


def get_gene_info(gene_symbol):

    # ==========================
    # 1. ヒトのGeneを検索
    # ==========================

    query = (
        f'{gene_symbol}[Gene Name] '
        f'AND "Homo sapiens"[Organism]'
    )

    handle = Entrez.esearch(
        db="gene",
        term=query,
        retmax=1
    )

    result = Entrez.read(handle)
    handle.close()

    if not result["IdList"]:
        return None

    gene_id = result["IdList"][0]


    # ==========================
    # 2. Geneレコードを取得
    # ==========================

    handle = Entrez.efetch(
        db="gene",
        id=gene_id,
        rettype="xml"
    )

    xml_data = handle.read()
    handle.close()

    root = ET.fromstring(xml_data)


    # ==========================
    # 3. 正式な遺伝子シンボル
    # ==========================

    symbol_node = root.find(
        ".//Gene-ref_locus"
    )

    symbol = (
        symbol_node.text
        if symbol_node is not None
        else gene_symbol
    )


    # ==========================
    # 4. 正式名称
    # ==========================

    description_node = root.find(
        ".//Gene-ref_desc"
    )

    description = (
        description_node.text
        if description_node is not None
        else "情報なし"
    )


    # ==========================
    # 5. NCBI Gene Summary
    # ==========================

    summary_node = root.find(
        ".//Entrezgene_summary"
    )

    summary = (
        summary_node.text
        if summary_node is not None
        else "NCBIにSummaryが登録されていません。"
    )


    return {
        "gene_id": gene_id,
        "symbol": symbol,
        "name": description,
        "summary": summary
    }

def explain_gene(info):

    prompt = f"""
あなたは大学生向けに分子生物学を説明するアシスタントです。

以下はNCBI Geneから取得した情報です。
この情報だけを根拠にしてください。
書かれていない情報を推測・追加しないでください。

遺伝子:
{info["symbol"]}

正式名称:
{info["name"]}

NCBI Gene Summary:
{info["summary"]}

以下のJSON形式だけで、日本語で回答してください。
functionsの項目数は固定せず、記載された機能だけを列挙してください。

{{
  "description": "この遺伝子が何をする遺伝子なのか、大学生にも分かるように説明。文数の制限は設けず、Summaryに記載された内容を省略せずに伝える",
  "functions": [
    "主な機能1",
    "主な機能2",
    "主な機能3"
  ]
}}
"""

    data = json.dumps({
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json"
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

    explanation = json.loads(result["response"])
    if (
        not isinstance(explanation, dict)
        or not isinstance(explanation.get("description"), str)
        or not explanation["description"].strip()
        or not isinstance(explanation.get("functions"), list)
        or not all(isinstance(item, str) for item in explanation["functions"])
    ):
        raise ValueError("AIの説明形式が不正です。再試行してください。")
    return explanation
