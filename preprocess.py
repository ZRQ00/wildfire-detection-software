import pandas as pd
import joblib
import os
import geopandas as gpd
from shapely.geometry import Point


APP_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(APP_DIR)

file_path = os.path.join(APP_DIR, "dataset", "wildfire_0.csv")

# Load dataset and model
df = pd.read_csv(file_path)
pickle_files = os.path.join(APP_DIR, "pickle")
scaler = joblib.load(os.path.join(pickle_files, "scaler.pkl"))
kmeans = joblib.load(os.path.join(pickle_files, "kmeans_model.pkl"))

# Features
features = ["Month", "Day", "FIREYEAR", "OWNERAGENCY", "PROTECTIONAGENCY",
            "PERIMEXISTS_N", "PERIMEXISTS_Y", "FIRERPTQC_no", "FIRERPTQC_yes",
            "STATCAUSE", "TOTALACRES"]

# Cluster
scaled = scaler.transform(df[features])
df["cluster"] = kmeans.predict(scaled)

# Save clustered data
df.to_csv("preclustered_data.csv", index=False)