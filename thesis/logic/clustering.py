import networkx as nx
import pandas as pd

def build_entity_clusters(entities_with_prob: pd.DataFrame, threshold: float = 0.8):
    edges = entities_with_prob[entities_with_prob["prob"] > threshold]

    G = nx.Graph()

    # alle Nodes hinzufügen
    all_entities = entities_with_prob["entity_id_a"].unique().tolist() + \
                entities_with_prob["entity_id_b"].unique().tolist()

    G.add_nodes_from(set(all_entities))

    # dann Edges
    for _, row in edges.iterrows():
        G.add_edge(row["entity_id_a"], row["entity_id_b"])

    clusters = list(nx.connected_components(G))

    cluster_map = {}

    for cluster in clusters:
        cluster_id = min(cluster)

        for entity in cluster:
            cluster_map[entity] = cluster_id

    cluster_sizes = {min(c): len(c) for c in clusters}

    rows = [
        {
            "entity_id": e,
            "cluster_id": cid,
            "cluster_size": cluster_sizes.get(cid, 1)
        }
        for e, cid in cluster_map.items()
    ]

    print(f"Edges > {threshold}:", len(edges))
    print(edges[["entity_id_a", "entity_id_b", "prob"]].head())

    return pd.DataFrame(rows)