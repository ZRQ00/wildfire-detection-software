import folium
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from flask import Flask, render_template, request
import os

# Predefine directory
APP_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(APP_DIR)

app = Flask(__name__)

# Adds state names to the dataset
def add_state_info(df):
    # Convert to GeoDataFrame
    geometry = [Point(xy) for xy in zip(df["LONGDD83"], df["LATDD83"])]
    geo_df = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")

    # Load US states GeoJSON (you can cache this locally too)
    states = gpd.read_file("https://raw.githubusercontent.com/PublicaMundi/MappingAPI/master/data/geojson/us-states.json")

    # Spatial join to get state info
    joined = gpd.sjoin(geo_df, states[["name", "geometry"]], how="left", predicate="within")

    # Rename the state column
    joined.rename(columns={"name": "state"}, inplace=True)

    return joined

# Load wildfire data
file_path = os.path.join(APP_DIR, "dataset", "wildfire_0.csv")
wildfire_data = pd.read_csv(file_path)

# Add state data for each point
wildfire_with_states = add_state_info(wildfire_data)
wildfire_us = wildfire_with_states.copy()

# Get list of states for frontend
states_list = sorted(wildfire_with_states["state"].dropna().astype(str).unique().tolist())

# Encoding mapping
cause_mapping = {
    0: "Arson",
    1: "Campfire",
    2: "Children",
    3: "Debris burning",
    4: "Equipment Use",
    5: "Firearms/Weapons",
    6: "Lightning",
    7: "Miscellaneous",
    8: "Other Human Cause",
    9: "Other Natural Cause",
    10: "Railroad",
    11: "Smoking",
    12: "Unknown",
    13: "Utilities"
}
cluster_mapping = {
    0: "High-Risk Large Fires",
    1: "Urban Wildfires",
    2: "Remote Small Fires",
    3: "Moderate Risk Zones",
    4: "Frequent Small Fires"
}

# Home
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html", states=states_list)

@app.route("/get-map", methods=["GET", "POST"])
def getMap():
    fire_causes = None
    wildfire_count = None
    selected_state = None
    map_image = None

    if request.method == "POST":
        selected_state = request.form['state']

        # Filter data for the selected state
        state_data = wildfire_with_states[wildfire_with_states['state'] == selected_state].copy()

        # Count wildfires
        wildfire_count = len(state_data)
        
        # Map encodings to readable cause
        state_data['cause_label'] = state_data['STATCAUSE'].map(cause_mapping)
        
        # Count by cause
        fire_causes = state_data['cause_label'].value_counts().to_dict()
        
        # Limit to 5000 points for performance reasons
        state_data = state_data.head(5000)

        # Generate the map
        map_image = generate_map(state_data, fire_causes)
        
    return render_template(
        "results.html",
        states=states_list,
        selected_state=selected_state,
        map_image=map_image,
        wildfire_count=wildfire_count,
        fire_causes=fire_causes
    )

# Generates map for frontend
def generate_map(state_data, fire_causes):
    cause_labels = list(fire_causes.keys())
    cause_colors = [
        '#ff6384', '#36a2eb', '#ffce56', '#4bc0c0',
        '#9966ff', '#ff9f40', '#c9cbcf', '#9b59b6',
        '#2ecc71', '#e74c3c'
    ]
    cause_color_map = dict(zip(cause_labels, cause_colors))
    
    # Create base map
    folium_map = folium.Map(
        location=[state_data["LATDD83"].mean(), state_data["LONGDD83"].mean()],
        zoom_start=4
    )
    
    # Write points on map
    for _, row in state_data.iterrows():
        fire_cause = row['cause_label']
        color = cause_color_map.get(fire_cause, 'gray')
        folium.CircleMarker(
            location=[row['LATDD83'], row['LONGDD83']],
            radius=5,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.6,
            popup=f"Latitude: {row['LATDD83']}, Longitude: {row['LONGDD83']}, Cause: {row['cause_label']}"
        ).add_to(folium_map)

    os.makedirs("static", exist_ok=True)
    map_path = os.path.join("static", "wildfire_map.html")
    folium_map.save(map_path)

    return "wildfire_map.html"
    
@app.route("/get-risk-map", methods=["GET", "POST"])
def getRisk():
    selected_state = None
    cluster_counts = {}

    # Load preclustered data
    clustered_df_path = os.path.join(APP_DIR, "dataset", "preclustered_data.csv")
    clustered_df = pd.read_csv(clustered_df_path)
    clustered_df = add_state_info(clustered_df)

    if request.method == "POST":
        selected_state = request.form['state']
        state_data = clustered_df[clustered_df['state'] == selected_state].copy()
        
        # Map encodings to readable cause
        state_data['cluster'] = state_data['cluster'].map(cluster_mapping)
        
        cluster_counts_raw = state_data['cluster'].value_counts().sort_index()
        cluster_counts = {k : int(v) for k, v in cluster_counts_raw.items()}
        
        generate_cluster_map(state_data)

    return render_template(
        "risk.html",
        states=states_list,
        selected_state=selected_state,
        cluster_counts=cluster_counts
    )

# Function was used to generate a cluster map
def generate_cluster_map(state_data):
    cluster_colors = [
        '#ff6384', '#36a2eb', '#ffce56', '#4bc0c0',
        '#9966ff',
    ]
    cluster_labels = sorted(state_data['cluster'].unique())
    cluster_color_map = {
        label: cluster_colors[i % len(cluster_colors)] for i, label in enumerate(cluster_labels)
    }
    # Create base map
    folium_map = folium.Map(
        location=[state_data["LATDD83"].mean(), state_data["LONGDD83"].mean()],
        zoom_start=4
    )

    for _, row in state_data.iterrows():
        cluster = row['cluster']
        color = cluster_color_map.get(cluster, 'gray')
        folium.CircleMarker(
            location=[row['LATDD83'], row['LONGDD83']],
            radius=5,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.6,
            popup=f"Cluster: {cluster}, Acres: {row['TOTALACRES']:.2f}"
        ).add_to(folium_map)

    os.makedirs("static", exist_ok=True)
    map_path = os.path.join("static", "cluster_map.html")
    folium_map.save(map_path)
    print(" Successfully created map!")
    return "cluster_map.html"

if __name__ == "__main__":
    app.run(debug=True)
