from thesis.data_generation.data_generation import generate_dirty_crm_data

def generate_synthetic_crm_sources(
    n_dirty=1000,
    n_clean=9000,
    dirty_seed=1,
    clean_seed=2,
    persist=False
):
    """
    Erzeugt synthetische CRM-Daten für Salesforce und Netsuite
    mit identischer Struktur, aber separater Quelle.
    """

    sf = generate_dirty_crm_data(
        n_dirty, n_clean,
        dirty_seed=dirty_seed,
        clean_seed=clean_seed,
        salesforce=True
    )
    ns = generate_dirty_crm_data( 
        n_dirty, n_clean,
        dirty_seed=dirty_seed,
        clean_seed=clean_seed,
        salesforce=False
    )

    sf["source"] = "salesforce"
    ns["source"] = "netsuite"

    if persist:
        sf.to_csv("../data/raw/dirty_salesforce.csv", index=False)
        ns.to_csv("../data/raw/dirty_netsuite.csv", index=False)

    return sf, ns

from thesis.data_generation.data_generation import generate, duplicate, distort
import numpy as np

def generate_synthetic_crm_sources_new(
    n_dirty=1000,
    n_clean=9000,
    dirty_seed=1,
    clean_seed=2,
    persist=False
):

    # 1. Ground truth erzeugen
    base = generate(n_dirty + n_clean, SEED=42)
    base = duplicate(base)

    # 2. Auf Systeme verteilen
    base["source"] = np.random.choice(
        ["salesforce", "netsuite"],
        size=len(base)
    )

    # 3. Split
    sf = base[base["source"] == "salesforce"].copy()
    ns = base[base["source"] == "netsuite"].copy()

    # 4. Unterschiedlich verzerren
    sf = distort(sf, SEED=dirty_seed, prob_apply=0.6, max_changes_per_field=3)
    ns = distort(ns, SEED=clean_seed, prob_apply=0.6, max_changes_per_field=3)

    # 5. Prefixe setzen (wichtig für deinen bestehenden Code!)
    sf = sf.rename(columns=lambda c: f"sf_{c}" if c not in ["cluster_id", "is_duplicated", "source"] else c)
    ns = ns.rename(columns=lambda c: f"ns_{c}" if c not in ["cluster_id", "is_duplicated", "source"] else c)

    # 6. Persist optional
    if persist:
        sf.to_csv("../data/raw/dirty_salesforce.csv", index=False)
        ns.to_csv("../data/raw/dirty_netsuite.csv", index=False)

    return sf, ns