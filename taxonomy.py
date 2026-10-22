from Bio import Entrez


from settings import configure_entrez
configure_entrez()


def classify_lineage(lineage_ex):
    """
    NCBI TaxonomyのLineageExから大分類を判定する
    """

    lineage_taxids = {
        str(item.get("TaxId"))
        for item in lineage_ex
    }

    # Mammalia
    if "40674" in lineage_taxids:
        return "哺乳類"

    # Aves
    if "8782" in lineage_taxids:
        return "鳥類"

    # Reptiles
    if (
        "8509" in lineage_taxids      # Squamata
        or "8459" in lineage_taxids   # Testudines
        or "1294634" in lineage_taxids  # Crocodylia
    ):
        return "爬虫類"

    # Amphibia
    if "8292" in lineage_taxids:
        return "両生類"

    # Fish
    if (
        "7898" in lineage_taxids      # Actinopterygii
        or "7777" in lineage_taxids   # Chondrichthyes
    ):
        return "魚類"

    return "その他"


def get_taxonomic_group(species):

    # ==========================
    # 1. NCBI Taxonomyで検索
    # ==========================

    handle = Entrez.esearch(
        db="taxonomy",
        term=f'"{species}"[Scientific Name]',
        retmax=1
    )

    result = Entrez.read(handle)
    handle.close()

    if not result["IdList"]:
        return {
            "species": species,
            "tax_id": None,
            "group": "その他",
            "lineage": ""
        }

    tax_id = result["IdList"][0]

    # ==========================
    # 2. Taxonomy情報を取得
    # ==========================

    handle = Entrez.efetch(
        db="taxonomy",
        id=tax_id,
        retmode="xml"
    )

    records = Entrez.read(handle)
    handle.close()

    record = records[0]

    lineage = record.get("Lineage", "")
    lineage_ex = record.get("LineageEx", [])

    group = classify_lineage(lineage_ex)

    return {
        "species": species,
        "tax_id": tax_id,
        "group": group,
        "lineage": lineage
    }


def classify_orthologs(orthologs, batch_size=100):

    groups = {
        "哺乳類": [],
        "鳥類": [],
        "爬虫類": [],
        "両生類": [],
        "魚類": [],
        "その他": []
    }

    # tax_id があるものだけ使用
    valid_items = [
        item
        for item in orthologs
        if item.get("tax_id")
    ]

    # Tax ID -> ortholog情報
    item_map = {
        str(item["tax_id"]): item
        for item in valid_items
    }

    tax_ids = list(item_map.keys())

    # ==========================
    # NCBIへまとめて問い合わせ
    # ==========================

    for start in range(
        0,
        len(tax_ids),
        batch_size
    ):

        batch = tax_ids[
            start:start + batch_size
        ]

        handle = Entrez.efetch(
            db="taxonomy",
            id=",".join(batch),
            retmode="xml"
        )

        records = Entrez.read(handle)
        handle.close()

        for record in records:

            tax_id = str(
                record.get("TaxId")
            )

            if tax_id not in item_map:
                continue

            lineage_ex = record.get(
                "LineageEx",
                []
            )

            group = classify_lineage(
                lineage_ex
            )

            ortholog = item_map[
                tax_id
            ].copy()

            ortholog["group"] = group

            groups[group].append(
                ortholog
            )

    # 生物名順に並べる
    for group in groups:

        groups[group].sort(
            key=lambda x: x["species"]
        )

    return groups