import hashlib

from ruamel.yaml import YAML


def calculate_md5(file_path):
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def check_files():
    dvc_model_path = "/app/model/model.pkl.dvc"
    dvc_metrics_path = "/app/metrics/metrics.json.dvc"
    dvc_data_path = "/app/data/winequality-red.csv.dvc"

    model_path = "/app/model/model.pkl"
    metrics_path = "/app/metrics/metrics.json"
    data_path = "/app/data/winequality-red.csv"

    yaml = YAML()
    with open(dvc_model_path, "r") as file:
        dvc_model = yaml.load(file)

    with open(dvc_metrics_path, "r") as file:
        dvc_metrics = yaml.load(file)

    with open(dvc_data_path, "r") as file:
        dvc_data = yaml.load(file)

    print(dvc_metrics)
    print(dvc_metrics["outs"][0]["md5"])
    print(calculate_md5(metrics_path))

    if dvc_model["outs"][0]["md5"] != calculate_md5(model_path):
        print("Wrong model in storage!")
        return False

    elif dvc_metrics["outs"][0]["md5"] != calculate_md5(metrics_path):
        print("Wrong metrics in storage!")
        return False

    elif dvc_data["outs"][0]["md5"] != calculate_md5(data_path):
        print("Wrong data in storage!")
        return False

    else:
        print("OK")
        return True
