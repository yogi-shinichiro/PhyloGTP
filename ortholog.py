from tool_runner import run_tool
from settings import DATASETS_BIN
import json




# ==========================================
# 指定した生物だけorthologを確認
# ==========================================

def get_orthologs(gene, species_list):

    data = json.loads(run_tool(
        [DATASETS_BIN, "summary", "gene", "symbol", gene, "--ortholog", "all"],
        timeout=180,
    ))

    orthologs = {}

    for report in data.get("reports", []):

        gene_data = report.get("gene", {})

        species = gene_data.get("taxname")
        symbol = gene_data.get("symbol")
        gene_id = gene_data.get("gene_id")

        if species in species_list:

            orthologs[species] = {
                "symbol": symbol,
                "gene_id": gene_id
            }

    result_list = []

    for species in species_list:

        if species in orthologs:

            result_list.append({
                "species": species,
                "found": True,
                "symbol": orthologs[species]["symbol"],
                "gene_id": orthologs[species]["gene_id"]
            })

        else:

            result_list.append({
                "species": species,
                "found": False,
                "symbol": None,
                "gene_id": None
            })

    return result_list


# ==========================================
# その遺伝子の全ortholog生物を取得
# ==========================================

def get_all_orthologs(gene):

    data = json.loads(run_tool(
        [DATASETS_BIN, "summary", "gene", "symbol", gene, "--ortholog", "all"],
        timeout=180,
    ))

    orthologs = []

    for report in data.get("reports", []):

        gene_data = report.get("gene", {})

        species = gene_data.get("taxname")
        symbol = gene_data.get("symbol")
        gene_id = gene_data.get("gene_id")
        tax_id = gene_data.get("tax_id")

        if not species:
            continue

        if not symbol:
            continue

        orthologs.append({
            "species": species,
            "symbol": symbol,
            "gene_id": gene_id,
            "tax_id": tax_id
        })

    orthologs.sort(
        key=lambda x: x["species"]
    )

    return orthologs