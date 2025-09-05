#!/usr/bin/env python3
import os
import re
import json
from tqdm import tqdm

def main(folder, output_path):
    # regex to capture the nanosecond timestamp in the filename
    pattern = re.compile(r'^constellation_info_(\d+)\.json$')

    # list & sort all matching files by their integer timestamp
    files = []
    for fn in os.listdir(folder):
        m = pattern.match(fn)
        if m:
            files.append((int(m.group(1)), fn))
    files.sort(key=lambda x: x[0])

    satellite_status = {}

    for time_ns, fn in tqdm(files):
        # convert back to seconds (float)
        timepoint = time_ns / 1e9

        with open(os.path.join(folder, fn), 'r') as fp:
            data = json.load(fp)

        sat0 = data["sat_info"]["0"]
        conn0 = data["sg_connection"]["0"]

        longitude    = sat0["longitude_degrees"]
        latitude     = sat0["latitude_degrees"]
        is_sunlit    = sat0["is_sunlit"]
        is_connected = 1 if len(conn0.get("gs_list", [])) != 0 else 0

        satellite_status[timepoint] = {
            "longitude":    longitude,
            "latitude":     latitude,
            "is_sunlit":    is_sunlit,
            "is_connected": is_connected
        }

    # write out the combined status dict
    with open(output_path, 'w') as out_fp:
        json.dump(satellite_status, out_fp, indent=4)

    print(f"Saved satellite_status for {len(satellite_status)} timepoints to {output_path}")

if __name__ == '__main__':
    gen_data_folder = "gen_data"
    sat_trace_data_folder = "dynamic_state_15000ms_for_86400s"
    output_result_path = "sat_status"

    os.makedirs(output_result_path, exist_ok=True)

    constellation_name_pattern = re.compile(r'(.*)_isls_none_ground_stations_first_10_algorithm_free_one_only_gs_relays')

    for constellation_folder_name in tqdm(os.listdir(gen_data_folder)):
        print(f"work on constellation: {constellation_folder_name}")
        constellation_name = constellation_name_pattern.match(constellation_folder_name).group(1)
        constellation_trace_data_folder_path = os.path.join(gen_data_folder, constellation_folder_name, sat_trace_data_folder)
        output_data_file_path = os.path.join(output_result_path, f"{constellation_name}.json")
        main(constellation_trace_data_folder_path, output_data_file_path)



