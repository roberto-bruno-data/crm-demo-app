import yaml

def load_config(path="config.yaml"):
    with open(path, "r") as f:
        return yaml.safe_load(f)

def get_crm_config(config, name):
    try:
        return config[name]["base_url"], config[name]["token"]
    except KeyError as e:
        raise KeyError(f"Missing config for {name}: {e}")
