from Bio import Entrez, SeqIO
import time

from ortholog import get_orthologs


from settings import configure_entrez
configure_entrez()


def normalize_gene_name(name):
    """
    ACTA1 / Acta1 / acta1 などの大文字小文字の違いを吸収する
    """
    return name.strip().upper()


def find_matching_cds(record, target_gene):
    """
    GenBankレコード内から、
    目的遺伝子とgene qualifierが一致するCDSを探す
    """

    target = normalize_gene_name(target_gene)

    for feature in record.features:

        if feature.type != "CDS":
            continue

        genes = feature.qualifiers.get("gene", [])

        for feature_gene in genes:

            if normalize_gene_name(feature_gene) == target:

                return feature

    return None


def get_cds(species_list, gene):

    output_file = f"{gene}_CDS.fasta"

    not_found = []
    sequence_info = []

    print("\n===== NCBI ORTHOLOG CHECK =====")

    ortholog_results = get_orthologs(
        gene,
        species_list
    )

    ortholog_map = {}

    for item in ortholog_results:

        species = item["species"]

        if item["found"]:

            ortholog_map[species] = {
                "symbol": item["symbol"],
                "gene_id": item["gene_id"]
            }

            print(
                f'OK {species} -> '
                f'{item["symbol"]} '
                f'(Gene ID: {item["gene_id"]})'
            )

        else:

            print(
                f'NG {species} -> '
                'Ortholog not found'
            )

    with open(output_file, "w") as outfile:

        for species in species_list:

            print(f"\nSearching : {species}")

            # ==========================
            # Ortholog確認
            # ==========================

            if species not in ortholog_map:

                print("  X Ortholog not found")

                not_found.append(species)

                continue

            target_gene = ortholog_map[species]["symbol"]
            target_gene_id = ortholog_map[species]["gene_id"]

            print(
                f"  Ortholog : {target_gene} "
                f"(Gene ID: {target_gene_id})"
            )


            # ==========================
            # 1. RefSeq mRNAを複数検索
            # ==========================

            query = (
                f'{target_gene}[Gene] AND "{species}"[Organism] '
                'AND srcdb_refseq[PROP] '
                'AND biomol_mrna[PROP]'
            )

            try:

                handle = Entrez.esearch(
                    db="nucleotide",
                    term=query,
                    retmax=10
                )

                search = Entrez.read(handle)
                handle.close()

                ids = search["IdList"]

                # ==========================
                # 2. RefSeqがない場合
                # ==========================

                if not ids:

                    print("  RefSeq mRNA not found.")
                    print("  Searching other mRNA records...")

                    query = (
                        f'{target_gene}[Gene] AND "{species}"[Organism] '
                        'AND biomol_mrna[PROP]'
                    )

                    handle = Entrez.esearch(
                        db="nucleotide",
                        term=query,
                        retmax=10
                    )

                    search = Entrez.read(handle)
                    handle.close()

                    ids = search["IdList"]


                if not ids:

                    print("  X No candidate sequences")

                    not_found.append(species)

                    continue


                # ==========================
                # 3. 候補を全部確認
                # ==========================

                candidates = []

                for seq_id in ids:

                    try:

                        handle = Entrez.efetch(
                            db="nucleotide",
                            id=seq_id,
                            rettype="gb",
                            retmode="text"
                        )

                        record = SeqIO.read(
                            handle,
                            "genbank"
                        )

                        handle.close()

                        # 目的遺伝子と一致するCDSを探す
                        feature = find_matching_cds(
                            record,
                            target_gene
                        )

                        if feature is None:

                            print(
                                f"  Skip {record.id}: "
                                "gene mismatch"
                            )

                            continue


                        cds_seq = feature.extract(
                            record.seq
                        )

                        feature_gene = (
                            feature.qualifiers
                            .get("gene", [gene])[0]
                        )

                        product = (
                            feature.qualifiers
                            .get("product", ["情報なし"])[0]
                        )

                        protein_id = (
                            feature.qualifiers
                            .get("protein_id", ["情報なし"])[0]
                        )


                        # ==========================
                        # 候補の優先順位
                        # ==========================

                        accession = record.id

                        if accession.startswith("NM_"):
                            priority = 1

                        elif accession.startswith("XM_"):
                            priority = 2

                        else:
                            priority = 3


                        candidates.append({

                            "record": record,

                            "feature": feature,

                            "cds_seq": cds_seq,

                            "species": species,

                            "gene": feature_gene,

                            "accession": accession,

                            "protein": product,

                            "protein_id": protein_id,

                            "cds_length": len(cds_seq),

                            "priority": priority

                        })


                    except Exception as e:

                        print(
                            f"  Candidate error: {e}"
                        )


                # ==========================
                # 4. 一致候補なし
                # ==========================

                if not candidates:

                    print(
                        "  X No CDS matched the requested gene"
                    )

                    not_found.append(species)

                    continue


                # ==========================
                # 5. 最も優先度の高い候補
                # ==========================

                candidates.sort(
                    key=lambda x: (
                        x["priority"],
                        -x["cds_length"]
                    )
                )

                best = candidates[0]


                # ==========================
                # 6. FASTAへ保存
                # ==========================

                outfile.write(
                    f">{species.replace(' ', '_')}\n"
                )

                outfile.write(
                    str(best["cds_seq"]) + "\n"
                )


                # ==========================
                # 7. 採用情報
                # ==========================

                refseq_type = "Other"

                if best["accession"].startswith("NM_"):
                    refseq_type = "RefSeq curated (NM_)"

                elif best["accession"].startswith("XM_"):
                    refseq_type = "RefSeq predicted (XM_)"


                sequence_info.append({

                    "species": best["species"],

                    "gene": best["gene"],

                    "accession": best["accession"],

                    "protein": best["protein"],

                    "protein_id": best["protein_id"],

                    "cds_length": best["cds_length"],

                    "candidate_count": len(candidates),

                    "gene_match": True,

                    "refseq_type": refseq_type

                })


                print(
                    f"  Selected : {best['accession']}"
                )

                print(
                    f"  Gene     : {best['gene']}"
                )

                print(
                    f"  Product  : {best['protein']}"
                )

                print(
                    f"  Candidates checked : "
                    f"{len(candidates)}"
                )


                time.sleep(0.4)


            except Exception as e:

                print(
                    "  ERROR :",
                    e
                )

                not_found.append(species)


    return output_file, not_found, sequence_info, ortholog_results