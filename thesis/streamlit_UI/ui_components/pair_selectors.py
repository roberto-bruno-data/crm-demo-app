import streamlit as st
from erlib.utils import ATTRIBUTES
from collections import Counter

def build_pair_label(row):
    return (
        row["nachname_1"] + ", "
        + row["vorname_1"]
        + " ↔ "
        + row["nachname_2"] + ", "
        + row["vorname_2"]
        + " | p=" + str(round(row["prob"], 2))
    )

def render_cluster_attribute(selected_cluster, cluster_entities_df, all_locked, show_identical=False):
    # Header
    if not show_identical:
        st.caption("Identische Attribute ausgeblendet")

    col_status, col_attr, col_select, col_lock = st.columns([0.3, 1, 6, 1])
    col_attr.markdown("**Attribut**")
    col_select.markdown("**Auswahl**")
    col_lock.markdown("**Lock**")

    st.markdown("---")

    for attr in ATTRIBUTES:
        value_key = f"value__{selected_cluster}__{attr}"

        # VALUE INIT
        if value_key not in st.session_state:
            values = (
                cluster_entities_df[attr]
                .dropna()
                .astype(str)
                .str.strip()
            )
            value_counts = Counter(values)
            sorted_values = value_counts.most_common()

            if sorted_values:
                st.session_state[value_key] = sorted_values[0][0]

     
    for attr in ATTRIBUTES:
        value_key = f"value__{selected_cluster}__{attr}"
        user_lock_key = f"user_lock__{selected_cluster}__{attr}"
        ui_key = f"ui__{selected_cluster}__{attr}"
        manual_input_key = f"manual_input__{selected_cluster}__{attr}"

        # ---- VALUES FIRST ----
        values = (
            cluster_entities_df[attr]
            .dropna()
            .astype(str)
            .str.strip()
        )

        value_counts = Counter(values)
        sorted_values = value_counts.most_common()

        cluster_size = len(cluster_entities_df)
        is_unique = (
            len(sorted_values) == 1
            and sorted_values
            and sorted_values[0][1] == cluster_size
        )

        # 👉 AUTO LOCK IMMER!
        if is_unique and user_lock_key not in st.session_state:
            st.session_state[user_lock_key] = True
            st.session_state[ui_key] = True

        # 👉 HIER skippen!
        if is_unique and not show_identical:
            continue

        # ---- ERST JETZT RENDERN ----
        col_status, col_attr, col_select, col_lock = st.columns([0.3, 1, 6, 1])
        col_attr.write(attr.capitalize())

        if ui_key not in st.session_state:
            st.session_state[ui_key] = st.session_state.get(user_lock_key, False)

         # LOCK INIT FIRST
        if user_lock_key not in st.session_state:
            st.session_state[user_lock_key] = is_unique

        # ---- DEFAULT VALUE ----

        selected_value = st.session_state.get(value_key)
        user_locked = st.session_state.get(user_lock_key, False)

        # 👉 effektiver Lock
        effective_lock = user_locked or is_unique

        # ---- OPTIONS BUILD ----
        selected_value = st.session_state.get(value_key)
        MAX_VISIBLE = 3
        options = sorted_values[:MAX_VISIBLE]

        option_values = [val for val, _ in options]

        # 👉 selected IMMER sichtbar halten (sauber)
        if selected_value and selected_value not in option_values:
            options = options[:MAX_VISIBLE - 1] + [(selected_value, 1)]
        
        selected_value = st.session_state.get(value_key)

        max_count = max([c for _, c in sorted_values], default=0)

        # ---- BUTTONS ----
        button_cols = col_select.columns(MAX_VISIBLE + 1)

        for j in range(MAX_VISIBLE):
            
            if j < len(options):
                val, count = options[j]

                # 👉 STATE VORHER bestimmen
                is_selected = (val == selected_value)

                label = f"{val} ({count}x)"
                if count == max_count:
                    label += " ⭐"

                if is_selected and val not in value_counts:
                    label = f"{val} (custom)"

                clicked = button_cols[j].button(
                    label,
                    key=f"btn__{selected_cluster}__{attr}__{val}_{count}",
                    width='stretch',
                    type="primary" if is_selected and user_locked else "secondary"
                )

                # 👉 DIREKT reagieren
                if clicked:
                    st.session_state[value_key] = val
                    st.session_state[user_lock_key] = True
                    st.rerun()

            else:
                button_cols[j].empty()

        col_lock.checkbox(
            "lock",
            key=ui_key,
            label_visibility="collapsed"
        )

        st.session_state[user_lock_key] = (
            st.session_state[ui_key] or is_unique
        )

        # ✅ THEN: read
        user_locked = st.session_state.get(user_lock_key, False)

        selected_value = st.session_state.get(value_key)


        # ---- MANUAL INPUT ----
        with button_cols[-1]:
            st.text_input(
                " ",
                key=manual_input_key,
                placeholder="Eigener Wert...",
                label_visibility="collapsed",
                on_change=handle_manual_input,
                args=(selected_cluster, attr)
            )

        # ---- LOCK CHECKBOX ----


        

        # ---- STATUS BAR ----
        status_bar(col_status, user_locked, is_unique, all_locked)

        st.markdown("---")

# TODO: lockemoji rendert nicht richtig

def status_bar(col, user_locked, is_unique, all_locked):

    if all_locked:
        color = "#fbbc04"  # gold
    elif is_unique:
        color = "#34a853"  # 🟢 auto-locked (unique)
    elif user_locked:
        color = "#34a853"  # 🟢 user locked
    else:
        color = "#ea4335"  # 🔴 offen

    col.markdown(
        f"""
        <div style="
            height: 2rem;
            background-color: {color};
            border-radius: 4px;
        "></div>
        """,
        unsafe_allow_html=True
    )

def handle_manual_input(selected_cluster, attr):
    value_key = f"value__{selected_cluster}__{attr}"
    manual_input_key = f"manual_input__{selected_cluster}__{attr}"
    lock_key = f"lock__{selected_cluster}__{attr}"

    manual_value = st.session_state.get(manual_input_key)

    if manual_value:
        st.session_state[value_key] = manual_value
        user_lock_key = f"user_lock__{selected_cluster}__{attr}"
        st.session_state[user_lock_key] = True

        # 👉 RESET hier erlaubt!
        st.session_state[manual_input_key] = ""

def render_pair_selector(cluster_pairs):
    cluster_pairs = cluster_pairs.copy()
    cluster_pairs["pair_label"] = cluster_pairs.apply(build_pair_label, axis=1)

    pair_map = dict(zip(cluster_pairs["pair_id"], cluster_pairs["pair_label"]))

    selected_pair_id = st.selectbox(
        "Pair im Cluster anzeigen",
        options=cluster_pairs["pair_id"],
        format_func=lambda x: pair_map.get(x, x)
    )

    return selected_pair_id

def get_selected_pair(cluster_pairs, selected_pair_id):
    selected_row = cluster_pairs.loc[
        cluster_pairs["pair_id"] == selected_pair_id
    ]
    return selected_row.iloc[0]