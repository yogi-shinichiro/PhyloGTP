import streamlit as st

st.set_page_config(
    page_title="PhyloGPT",
    page_icon="🌳",
)

from get_CDS_v3 import get_cds
from phylogeny_CDS import make_tree
from Bio import Phylo
import matplotlib.pyplot as plt
from ai_gene import suggest_genes
from gene_info import get_gene_info, explain_gene


@st.cache_data(ttl=86400, max_entries=256, show_spinner=False)
def cached_gene_info(symbol):
    info = get_gene_info(symbol)
    if info is None:
        raise ValueError(f"{symbol}: NCBI Geneで確認できませんでした。")
    return info


@st.cache_data(ttl=86400, max_entries=256, show_spinner=False)
def cached_explanation(info):
    return explain_gene(info)


@st.cache_data(ttl=3600, max_entries=128, show_spinner=False)
def cached_candidates(query):
    return suggest_genes(query)

from ortholog import get_all_orthologs
from taxonomy import classify_orthologs
# Local Japanese search labels; analysis always uses the original scientific name.
# 
# Selected references for Japanese names:
# https://www.nies.go.jp/biodiversity/invasive/DB/detail/40310.html
# https://togotv.dbcls.jp/togopic.2025.003.html
# https://www.env.go.jp/content/900411437.pdf
# Aliases such as マウス and ラット are search conveniences, not taxonomy IDs.

SPECIES_NAMES = {
    "Homo sapiens": ("ヒト", "人間"),
    "Mus musculus": ("ハツカネズミ", "マウス"),
    "Rattus norvegicus": ("ドブネズミ", "ラット"),
    "Gallus gallus": ("セキショクヤケイ", "ニワトリ"),
    "Gallus gallus domesticus": ("ニワトリ",),
    "Anolis carolinensis": ("グリーンアノール",),
    "Xenopus tropicalis": ("ネッタイツメガエル",),
    "Xenopus laevis": ("アフリカツメガエル",),
    "Danio rerio": ("ゼブラフィッシュ", "ゼブラダニオ"),
    "Oryzias latipes": ("ミナミメダカ", "メダカ"),
    "Oryzias sakaizumii": ("キタノメダカ",),
    "Oncorhynchus mykiss": ("ニジマス",),
    "Poecilia reticulata": ("グッピー",),
    "Rana japonica": ("ニホンアカガエル",),
    "Canis lupus familiaris": ("イヌ",),
    "Canis familiaris": ("イヌ",),
    "Felis catus": ("イエネコ", "ネコ"),
    "Bos taurus": ("ウシ",),
    "Sus scrofa": ("イノシシ", "ブタ"),
    "Equus caballus": ("ウマ",),
    "Ovis aries": ("ヒツジ",),
    "Capra hircus": ("ヤギ",),
    "Oryctolagus cuniculus": ("アナウサギ", "ウサギ"),
    "Pan troglodytes": ("チンパンジー",),
    "Macaca mulatta": ("アカゲザル",),
    "Drosophila melanogaster": ("キイロショウジョウバエ",),
    "Caenorhabditis elegans": ("シーエレガンス",),
    "Ambystoma mexicanum": ("メキシコサンショウウオ", "アホロートル", "ウーパールーパー"),
}


def species_label(scientific_name, custom_names=None):
    """Return a bilingual label without changing or merging species identity."""
    names = list(SPECIES_NAMES.get(scientific_name, ()))
    custom = (custom_names or {}).get(scientific_name, "").strip()
    if custom and custom not in names:
        names.append(custom)
    if not names:
        return scientific_name
    return f"{' / '.join(names)} — {scientific_name}"



# ==========================
# ページ設定
# ==========================


st.title("🌳 PhyloGPT")


st.write(
    "調べたい特徴から遺伝子候補を探し、"
    "NCBIのオルソログ情報を使って比較する生物を選び、系統樹を自動作成します。"
)


# ==========================
# AI遺伝子検索
# ==========================

st.subheader("🤖 AIで遺伝子を探す")

ai_query = st.text_input(
    "調べたい特徴やタンパク質を日本語で入力してください",
    placeholder="例：筋肉に関係するタンパク質"
)

if st.button("🔍 AIで候補を探す"):

    if not ai_query.strip():
        st.warning("調べたい内容を入力してください。")

    else:
        try:
            with st.spinner("AIが遺伝子候補を探しています..."):
                candidates = cached_candidates(ai_query.strip())

            st.session_state["gene_candidates"] = list(dict.fromkeys(
                item["gene"].strip().upper()
                for item in candidates
                if isinstance(item, dict) and isinstance(item.get("gene"), str)
                and item["gene"].strip()
            ))

        except Exception as e:
            st.error("AI検索中にエラーが発生しました。")
            st.exception(e)


# ==========================
# AI候補
# ==========================

selected_gene = None
candidates = st.session_state.get("gene_candidates", [])

if candidates:
    st.write("### 🧬 AIが見つけた候補")
    selected_gene = st.radio(
        "系統解析に使用する遺伝子を選択してください", candidates
    )
    st.caption("各候補の「詳しい説明を見る」を開くと、NCBI原文と生成済みの日本語説明を確認できます。")
    generate_explanations = st.button("💡 全候補の日本語AI説明を生成・再試行")
    explanations = st.session_state.setdefault("gene_explanations", {})

    for candidate in candidates:
        st.divider()
        try:
            with st.spinner(f"{candidate} の情報をNCBIから取得しています..."):
                info = cached_gene_info(candidate)
        except Exception as e:
            st.subheader(f"🧬 {candidate}")
            st.warning(f"{candidate} の情報を取得できませんでした。再試行してください。")
            st.exception(e)
            continue

        st.subheader(f"🧬 {candidate} — {info['name']}")
        with st.expander("詳しい説明を見る", expanded=False):
            st.write("#### NCBI Geneの説明全文（原文）")
            st.write(info["summary"])
            st.caption(f"📚 情報源：NCBI Gene / Gene ID: {info['gene_id']}")

            # Summaryが更新された場合は、古い説明を使わない。
            explanation_key = (info["gene_id"], info["symbol"], info["name"], info["summary"])
            if generate_explanations and explanation_key not in explanations:
                try:
                    with st.spinner(f"{candidate} の日本語説明を生成しています..."):
                        explanations[explanation_key] = cached_explanation(info)
                except Exception as e:
                    st.warning(f"{candidate} の日本語説明を生成できませんでした。原文をご確認ください。")
                    st.exception(e)

            explanation = explanations.get(explanation_key)
            if explanation:
                st.write("#### 日本語での説明（AI生成）")
                st.write(explanation["description"])
                st.write("#### 🔬 主な機能")
                for function in explanation["functions"]:
                    st.write(f"・{function}")
elif "gene_candidates" in st.session_state:
    st.info("遺伝子候補が見つかりませんでした。検索内容を変えてお試しください。")


# ==========================
# 遺伝子
# ==========================

st.subheader("🔬 遺伝子")

gene = st.text_input(
    "遺伝子名を直接入力することもできます",
    value=selected_gene if selected_gene else "ALDH2"
)

gene = gene.strip()


# ==========================
# オルソログ生物を取得・分類
# ==========================

species_list = []

if gene:

    if st.button("🌎 比較できる生物を探す"):

        try:
            with st.spinner(
                f"{gene} のオルソログを持つ生物をNCBIから検索しています..."
            ):
                all_orthologs = get_all_orthologs(gene)

            with st.spinner(
                "NCBI Taxonomyを使って分類群ごとに整理しています..."
            ):
                classified_groups = classify_orthologs(all_orthologs)

            st.session_state["all_orthologs"] = all_orthologs
            st.session_state["classified_groups"] = classified_groups
            st.session_state["ortholog_gene"] = gene

        except Exception as e:
            st.error(
                "オルソログ生物の検索・分類中にエラーが発生しました。"
            )
            st.exception(e)


# ==========================
# 生物を選択
# ==========================

if (
    "all_orthologs" in st.session_state
    and "classified_groups" in st.session_state
):

    all_orthologs = st.session_state["all_orthologs"]
    classified_groups = st.session_state["classified_groups"]
    ortholog_gene = st.session_state["ortholog_gene"]

    # 別の遺伝子名に変更した後、古い検索結果を誤用しない
    if ortholog_gene != gene:
        st.warning(
            f"現在表示している生物候補は {ortholog_gene} の結果です。"
            f" {gene} で解析する場合は「比較できる生物を探す」を押し直してください。"
        )

    else:
        st.subheader(
            f"🌎 {ortholog_gene} で比較できる生物"
        )

        st.write(
            f"NCBI Orthologで **{len(all_orthologs)}種** 見つかりました。"
        )

        group_order = [
            "哺乳類",
            "鳥類",
            "爬虫類",
            "両生類",
            "魚類",
            "その他",
        ]

        group_icons = {
            "哺乳類": "🐭",
            "鳥類": "🐦",
            "爬虫類": "🦎",
            "両生類": "🐸",
            "魚類": "🐟",
            "その他": "🧬",
        }

        st.write("### 📊 分類群ごとのオルソログ数")

        cols = st.columns(3)

        visible_groups = []

        for index, group in enumerate(group_order):
            count = len(classified_groups.get(group, []))

            if count > 0:
                visible_groups.append(group)

            with cols[index % 3]:
                st.metric(
                    f"{group_icons[group]} {group}",
                    f"{count}種"
                )

        if st.button("検索を解除", key="clear_species_search"):
            st.session_state["species_search_query"] = ""
            st.session_state["applied_species_query"] = ""
        with st.form("species_search_form"):
            query_input = st.text_input(
                "🔍 生物種を検索（日本語名・学名）",
                placeholder="例：マウス、Mus musculus、Xenopus",
                key="species_search_query",
            )
            if st.form_submit_button("🔍 検索"):
                st.session_state["applied_species_query"] = query_input.strip()
        applied_query = st.session_state.get("applied_species_query", "")
        species_query = applied_query.casefold()
        st.caption(
            "検索語を入力して「🔍 検索」を押してください。分類群の一覧では一致した種に🔎を表示し、全種から選ぶ場合は候補を絞り込みます。"
            "日本語は登録済みの主要種に対応します。検索中も選択済みの種は残ります。"
        )
        if species_query:
            st.info(f"検索中：{applied_query}（現在の分類群・オルソログ候補から検索）")

        selection_mode = st.radio(
            "生物の選び方",
            [
                "🗂️ 分類群から選ぶ",
                "🔍 すべての生物から選ぶ",
            ],
            horizontal=True
        )

        if selection_mode == "🗂️ 分類群から選ぶ":

            st.write("### 比較したい分類群を開いて、生物種を選択")
            st.caption(
                "「哺乳類」などをクリックすると、今回の遺伝子で比較できる全種を表示します。"
                "学名にチェックした種だけを系統樹に使用します。複数の分類群から選べます。"
            )
            filtered_species = sorted({
                item["species"] for items in classified_groups.values() for item in items
            })
            # Durable selection survives filtering and switching selection modes.
            selection_store = st.session_state.setdefault("group_species_selection", {})
            saved_selection = set(selection_store.get(ortholog_gene, [])) & set(filtered_species)
            species_list = []
            for group in visible_groups:
                group_species = sorted({item["species"] for item in classified_groups.get(group, [])})
                with st.expander(f"{group_icons[group]} {group}（{len(group_species)}種）", expanded=False):
                    if species_query:
                        st.caption("一覧は全種を表示しています。🔎 は検索語に一致した種です。")
                    for species in group_species:
                        matched = species_query and species_query in species_label(species).casefold()
                        checkbox_key = f"group_species::{ortholog_gene}::{group}::{species}"
                        if checkbox_key not in st.session_state:
                            st.session_state[checkbox_key] = species in saved_selection
                        if matched:
                            st.caption(f"🔎 検索一致：{species}")
                        checked = st.checkbox(
                            species,
                            key=checkbox_key,
                        )
                        if checked:
                            species_list.append(species)
                    selected_count = sum(species in species_list for species in group_species)
                    st.caption(f"{group}：{selected_count} / {len(group_species)}種を選択中")
            species_list = sorted(set(species_list))
            selection_store[ortholog_gene] = species_list
            if species_list:
                with st.expander(f"系統樹に使用する生物を確認（{len(species_list)}種）", expanded=False):
                    for species in species_list:
                        st.write(f"・{species}")

        else:

            species_options = sorted({
                item["species"]
                for item in all_orthologs
            })

            default_species = [
                species
                for species in [
                    "Homo sapiens",
                    "Mus musculus",
                    "Rattus norvegicus",
                    "Gallus gallus",
                    "Xenopus tropicalis",
                ]
                if species in species_options
            ]

            selected_species = st.session_state.get("species_all", default_species)
            visible_species = [
                species for species in species_options
                if not species_query
                or species_query in species_label(species).casefold()
                or species in selected_species
            ]
            if species_query and not any(
                species_query in species_label(species).casefold()
                for species in species_options
            ):
                st.info("一致する生物種がありません。学名で検索するか、分類群・遺伝子を確認してください。")
            if "species_all" in st.session_state:
                st.session_state["species_all"] = [
                    species for species in selected_species if species in visible_species
                ]

            species_list = st.multiselect(
                "全候補から、系統樹に使用する生物を4種以上選択してください",
                options=visible_species,
                default=[species for species in default_species if species in visible_species],
                help="上の検索欄で絞り込み、ここで学名を選びます。×で選択を解除できます。",
                key="species_all"
            )

        if species_query:
            search_pool = filtered_species if selection_mode == "🗂️ 分類群から選ぶ" else species_options
            matches = [species for species in search_pool
                       if species_query in species_label(species).casefold()]
            remaining = [species for species in matches if species not in species_list]
            st.write(f"**検索結果：{len(matches)}種（選択済み {len(matches) - len(remaining)}種 / 追加可能 {len(remaining)}種）**")
            for species in matches:
                status = "選択済み" if species in species_list else "未選択：上の分類群一覧または選択欄から追加できます"
                st.write(f"・{species} — {status}")
            if matches and not remaining and selection_mode == "🔍 すべての生物から選ぶ":
                st.info("検索に一致する種はすべて選択済みです。選択欄の「No results」は、追加できる候補がないことを示します。")

        st.write(
            f"**選択中：{len(species_list)}種**"
        )

        if len(species_list) < 4:
            st.warning(
                "系統樹を作成するには4種以上選択してください。"
            )


# ==========================
# 実行
# ==========================

if st.button("🌳 系統樹を作成"):

    if not gene:
        st.error("遺伝子名を入力してください。")

    elif (
        "ortholog_gene" not in st.session_state
        or st.session_state["ortholog_gene"] != gene
    ):
        st.error(
            "この遺伝子の生物候補がまだ読み込まれていません。"
            "「🌎 比較できる生物を探す」を押してください。"
        )

    elif len(species_list) < 4:
        st.error(
            "系統樹を作成するには4種以上の生物を選択してください。"
        )

    else:
        try:
            # ==========================
            # 1. NCBIから配列取得
            # ==========================

            st.info("🔎 NCBIから配列を取得しています...")

            output_file, not_found, sequence_info, ortholog_results = get_cds(
                species_list,
                gene
            )

            st.success("✅ 配列の取得が完了しました！")

            # ==========================
            # オルソログ確認結果
            # ==========================

            ortholog_count = sum(bool(item["found"]) for item in ortholog_results)

            with st.expander(
                f"🔎 オルソログ確認結果（{ortholog_count}/{len(species_list)}種）",
                expanded=False,
            ):
                for item in ortholog_results:

                    if item["found"]:

                        st.markdown(
                            f"""
**✅ {item["species"]}**

- Ortholog：`{item["symbol"]}`
- NCBI Gene ID：`{item["gene_id"]}`
"""
                        )

                    else:
                        st.markdown(
                            f"""
**⚠️ {item["species"]}**

NCBI Orthologで **{gene} のオルソログを確認できませんでした。**  
この生物は系統解析から除外します。
"""
                        )

            st.info(
                f"🧬 オルソログ確認："
                f"{ortholog_count} / {len(species_list)} 種"
            )

            # ==========================
            # 取得した配列の情報
            # ==========================

            with st.expander(
                f"🧬 使用した配列を見る（{len(sequence_info)}種）",
                expanded=False,
            ):

                for seq in sequence_info:

                    st.markdown(
                        f"""
**✅ {seq["species"]}**

- 遺伝子：`{seq["gene"]}`
- Accession：`{seq["accession"]}`
- タンパク質：{seq["protein"]}
- Protein ID：`{seq["protein_id"]}`
- CDS長：{seq["cds_length"]:,} bp
"""
                    )

            st.success(
                f"取得成功：{len(sequence_info)} / {len(species_list)} 種"
            )

            if not_found:

                st.warning(
                    "⚠️ 解析対象から除外された生物があります。"
                )

                for species in not_found:
                    st.write("・", species)

            else:
                st.write(
                    "🎉 すべての生物から配列を取得できました！"
                )

            # ==========================
            # 系統解析可能かチェック
            # ==========================

            if len(sequence_info) < 4:

                st.error(
                    "⚠️ 系統樹を作成できません。"
                )

                st.warning(
                    f"{gene} の配列を取得できたのは "
                    f"{len(sequence_info)} / {len(species_list)} 種です。"
                )

                st.write(
                    "RAxML-NGによる系統解析には、"
                    "最低4配列が必要です。"
                )

                st.stop()

            # ==========================
            # 2. MAFFT + RAxML-NG
            # ==========================

            st.info("🧬 系統解析を実行しています...")

            tree_file = make_tree(gene)

            st.success(
                "🌳 系統樹の作成が完了しました！"
            )

            # ==========================
            # 3. 系統樹を読み込む
            # ==========================

            tree = Phylo.read(
                tree_file,
                "newick"
            )

            # ==========================
            # 4. 系統樹を描画
            # ==========================

            st.subheader(
                f"🌳 {gene} の系統樹"
            )

            fig = plt.figure(
                figsize=(12, 7)
            )

            ax = fig.add_subplot(111)

            Phylo.draw(
                tree,
                axes=ax,
                do_show=False
            )

            ax.set_xlabel(
                "Substitutions per site"
            )

            ax.set_ylabel("")

            ax.set_title(
                f"Maximum Likelihood Phylogenetic Tree ({gene})"
            )

            plt.tight_layout()

            st.pyplot(fig)

            plt.close(fig)

            st.caption(
                f"Tree file: {tree_file}"
            )

        except Exception as e:

            st.error(
                "❌ エラーが発生しました。"
            )

            st.exception(e)
