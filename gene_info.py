from settings import OLLAMA_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT_SECONDS
from Bio import Entrez
import xml.etree.ElementTree as ET
import json
import urllib.request
import urllib.error
import http.client
import time
from contextlib import closing


class GeneInfoConnectionError(RuntimeError):
    """NCBI could not be reached after bounded retries."""


class GeneNotFoundError(ValueError):
    """No human gene record matched the query."""


def _read_ncbi(open_handle, decode, attempts=3):
    # Retry the read as well as opening the connection; always close handles.
    for attempt in range(attempts):
        try:
            with closing(open_handle()) as handle:
                return decode(handle)
        except urllib.error.HTTPError as exc:
            if exc.code != 429 and not 500 <= exc.code < 600:
                raise
            last_error = exc
        except (http.client.RemoteDisconnected, http.client.IncompleteRead,
                ConnectionError, TimeoutError, urllib.error.URLError) as exc:
            last_error = exc
        if attempt + 1 < attempts:
            time.sleep(2 ** (attempt + 1))
    raise GeneInfoConnectionError(
        "NCBIへの接続が切断されたか、応答を取得できませんでした。"
        "自動再試行後も取得できないため、少し待って再試行してください。"
    ) from last_error


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

    result = _read_ncbi(
        lambda: Entrez.esearch(db="gene", term=query, retmax=1),
        Entrez.read,
    )

    if not result["IdList"]:
        return None

    gene_id = result["IdList"][0]


    # ==========================
    # 2. Geneレコードを取得
    # ==========================

    xml_data = _read_ncbi(
        lambda: Entrez.efetch(db="gene", id=gene_id, rettype="xml"),
        lambda handle: handle.read(),
    )

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
