import streamlit as st

st.set_page_config(
    page_title="PhyloGPT",
    page_icon="🌳",
)

from get_CDS_v3 import get_cds
from phylogeny_CDS import make_tree
from Bio import Phylo
import matplotlib.pyplot as plt
from io import BytesIO
from pathlib import Path
from ai_gene import suggest_genes
from gene_info import get_gene_info, explain_gene, GeneInfoConnectionError, GeneNotFoundError


def update_species_from_search(gene_name, species, mode, result_key, groups):
    selected = st.session_state[result_key]
    if mode == "🗂️ 分類群から選ぶ":
        store = st.session_state.setdefault("group_species_selection", {})
        values = set(store.get(gene_name, []))
        if selected:
            values.add(species)
        else:
            values.discard(species)
        store[gene_name] = sorted(values)
        for group, items in groups.items():
            if any(item["species"] == species for item in items):
                st.session_state[f"group_species::{gene_name}::{group}::{species}"] = selected
    else:
        values = set(st.session_state.get("species_all", []))
        if selected:
            values.add(species)
        else:
            values.discard(species)
        st.session_state["species_all"] = sorted(values)


@st.cache_data(ttl=86400, max_entries=256, show_spinner=False)
def cached_gene_info(symbol):
    info = get_gene_info(symbol)
    if info is None:
        raise GeneNotFoundError(f"{symbol}: NCBI Geneでヒトの遺伝子を確認できませんでした。")
    return info


@st.cache_data(ttl=86400, max_entries=256, show_spinner=False)
def cached_explanation(info):
    return explain_gene(info)


@st.cache_data(ttl=3600, max_entries=128, show_spinner=False)
def cached_candidates(query):
    # Candidate response v3 uses concise reasons and a bounded response.
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

            st.session_state["gene_candidates"] = [item["gene"] for item in candidates]
            st.session_state["gene_candidate_reasons"] = {item["gene"]: item["reason"] for item in candidates}
            st.session_state["gene_candidate_query"] = ai_query.strip()

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
    candidate_query = st.session_state.get("gene_candidate_query")
    if candidate_query:
        st.write("検索内容：", candidate_query)
        if ai_query.strip() != candidate_query:
            st.info("以下は前回の検索結果です。入力を変えた場合は「AIで候補を探す」を押してください。")
    st.caption("提案理由はAIが生成した説明です。NCBIの原文と照合して候補を検討してください。")
    selected_gene = st.radio(
        "系統解析に使用する遺伝子を選択してください", candidates
    )
    st.caption("各候補の「詳しい説明を見る」を開くと、NCBI原文と生成済みの日本語説明を確認できます。")
    generate_explanations = st.button("💡 全候補の日本語AI説明を生成・再試行")
    # Clicking reruns failed lookups; successful entries remain cached.
    st.button("🔄 NCBI情報の取得を再試行", key="retry_ncbi_gene_info")
    explanations = st.session_state.setdefault("gene_explanations", {})

    for candidate in candidates:
        st.divider()
        st.subheader(f"🧬 {candidate}")
        reason = st.session_state.get("gene_candidate_reasons", {}).get(candidate)
        if reason:
            st.write("**この遺伝子を候補にした理由（AI生成）**")
            st.write(reason)
        else:
            st.caption("この候補には提案理由が保存されていません。「AIで候補を探す」で再検索してください。")
        try:
            with st.spinner(f"{candidate} の情報をNCBIから取得しています..."):
                info = cached_gene_info(candidate)
        except GeneInfoConnectionError as e:
            st.warning(f"{candidate}：NCBIとの通信に失敗しました。遺伝子が存在しないという判定ではありません。上の「NCBI情報の取得を再試行」を押してください。")
            with st.expander(f"{candidate} の通信エラー詳細", expanded=False):
                st.exception(e)
            continue
        except GeneNotFoundError:
            st.warning(f"{candidate}：NCBI Geneでヒトの遺伝子を確認できませんでした。AIが提示した遺伝子名の誤りも考えられるため、正式なシンボルを確認するかAI検索をやり直してください。")
            continue
        except Exception as e:
            st.warning(f"{candidate} の情報を取得できませんでした。")
            with st.expander(f"{candidate} のエラー詳細", expanded=False):
                st.exception(e)
            continue

        st.write("**正式名称：**", info["name"])
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
        search_results = st.container()
        applied_query = st.session_state.get("applied_species_query", "")
        species_query = applied_query.casefold()
        st.caption(
            "検索語を入力して「🔍 検索」を押してください。検索結果は検索欄のすぐ下に表示します。全種から選ぶ場合は候補も絞り込みます。"
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
            preferred_species = {
                "哺乳類": ["Homo sapiens", "Mus musculus"],
                "鳥類": ["Gallus gallus"],
                "爬虫類": ["Anolis carolinensis"],
                "両生類": ["Xenopus tropicalis", "Xenopus laevis"],
                "魚類": ["Danio rerio", "Oryzias latipes"],
            }
            initial_species = []
            for group in visible_groups:
                available = sorted({item["species"] for item in classified_groups.get(group, [])})
                if available:
                    chosen = next((name for name in preferred_species.get(group, []) if name in available), available[0])
                    initial_species.append(chosen)
            reset_defaults = st.button("各分類群から1種ずつ選び直す", key="reset_group_defaults")
            if ortholog_gene not in selection_store or reset_defaults:
                selection_store[ortholog_gene] = initial_species
                for group in visible_groups:
                    for item in classified_groups.get(group, []):
                        species = item["species"]
                        st.session_state[f"group_species::{ortholog_gene}::{group}::{species}"] = species in initial_species
            st.caption("初回は候補のある分類群から1種ずつ選択します。自由に追加・解除できます。「選び直す」を押すと現在の選択を各群1種に戻します。")
            saved_selection = set(selection_store.get(ortholog_gene, [])) & set(filtered_species)
            species_list = []
            for group in visible_groups:
                group_species = sorted({item["species"] for item in classified_groups.get(group, [])})
                with st.expander(f"{group_icons[group]} {group}（{len(group_species)}種）", expanded=False):
                    for species in group_species:
                        checkbox_key = f"group_species::{ortholog_gene}::{group}::{species}"
                        if checkbox_key not in st.session_state:
                            st.session_state[checkbox_key] = species in saved_selection
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
                    st.caption("チェックを外すと、その生物を解析対象から除外します。分類群や検索結果の選択にも反映されます。")
                    for species in species_list:
                        selected_key = f"selected_species::{ortholog_gene}::{species}"
                        st.session_state[selected_key] = True
                        st.checkbox(
                            species,
                            key=selected_key,
                            on_change=update_species_from_search,
                            args=(ortholog_gene, species, selection_mode, selected_key, classified_groups),
                        )

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

        with search_results:
            if species_query:
                search_pool = filtered_species if selection_mode == "🗂️ 分類群から選ぶ" else species_options
                matches = [species for species in search_pool
                           if species_query in species_label(species).casefold()]
                remaining = [species for species in matches if species not in species_list]
                st.write(f"**「{applied_query}」の検索結果：{len(matches)}種（選択済み {len(matches) - len(remaining)}種 / 追加可能 {len(remaining)}種）**")
                if not matches:
                    st.info("一致する生物種がありません。学名や検索語を変えてお試しください。")
                st.caption("ここでチェックした種を系統樹に使用します。下の選択欄とも連動します。")
                for species in matches:
                    result_key = f"search_species::{ortholog_gene}::{selection_mode}::{species}"
                    st.session_state[result_key] = species in species_list
                    st.checkbox(
                        species,
                        key=result_key,
                        on_change=update_species_from_search,
                        args=(ortholog_gene, species, selection_mode, result_key, classified_groups),
                    )

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

            try:
                png = BytesIO()
                pdf = BytesIO()
                fig.savefig(png, format="png", dpi=300, bbox_inches="tight")
                fig.savefig(pdf, format="pdf", bbox_inches="tight")
                st.session_state["completed_tree"] = {
                    "gene": gene,
                    "png": png.getvalue(),
                    "pdf": pdf.getvalue(),
                    "newick": Path(tree_file).read_bytes(),
                }
            finally:
                plt.close(fig)

        except Exception as e:

            st.error(
                "❌ エラーが発生しました。"
            )

            st.exception(e)


# Keep the completed result available across widget and download reruns.
if "completed_tree" in st.session_state:
    result = st.session_state["completed_tree"]
    result_gene = result["gene"]
    st.subheader(f"🌳 保存済みの解析結果：{result_gene}")
    st.image(result["png"])
    st.caption("最後に完成した系統樹です。入力や生物種を変更した場合は、再度作成してください。")
    for label, extension, mime, field in (
        ("📷 画像をダウンロード（PNG）", "png", "image/png", "png"),
        ("📄 PDFをダウンロード", "pdf", "application/pdf", "pdf"),
        ("🌳 系統樹データをダウンロード（Newick）", "nwk", "text/plain", "newick"),
    ):
        st.download_button(
            label,
            data=result[field],
            file_name=f"{result_gene}_tree.{extension}",
            mime=mime,
            key=f"tree_download_{field}",
        )
