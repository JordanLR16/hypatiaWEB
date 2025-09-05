#!/bin/bash

# List of constellations
# constellations=("starlink_550" "dove2" "landsat8" "rapideye1", "sentinel2")
constellations=("rapideye1")
month_starts=(0 2678400 5097600 7776000 10368000 13046400 15638400 18316800 20995200 23587200 26265600 28857600)


# Loop through each constellation
for constellation in "${constellations[@]}"
do
    for start_time in "${month_starts[@]}"; do
        echo "Running main_${constellation}.py for start time ${start_time}..."
        python "main_${constellation}.py" 86400 15000 isls_none ground_stations_first_10 algorithm_free_one_only_gs_relays 8 $start_time
    done
done
