#!/usr/bin/env python3
"""
Summarizes stats from multiple subjects in one plots.
Stats are taken from the FINTA Evaluation Flow and must contains
precision, recall and dice per bundles. 
"""
import argparse
import json
import os
from os.path import join

import plotly
import plotly.graph_objects as go
from scilpy.io.utils import (
    add_overwrite_arg,
)

from tractolearn.tractoio.utils import read_data_from_json_file, save_data_to_json_file


def _build_arg_parser():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("in_jsons", help="JSON file to merge.", nargs="+")
    p.add_argument(
        "out_path",
        help="Output path where to save jsons and html files",
    )
    p.add_argument("--bundles_config", required=True, help="Bundles config")
    add_overwrite_arg(p)

    return p


def main():
    parser = _build_arg_parser()
    args = parser.parse_args()

    if not os.path.isdir(args.out_path):
        raise ValueError(f"out_path must be a path. Got {args.out_path}")

    metric_list = [
        "bundle_adjacency_voxels",
        "w_dice_voxels",
        "density_correlation",
        "dice_voxels",
        "bundle_adjacency_streamlines",
    ]
    y_lims = {
        "dice_voxels": [0, 1.01],
        "w_dice_voxels": [0, 1.01],
        "density_correlation": [0, 1.01],
        "bundle_adjacency_voxels": [0, 10],
        "bundle_adjacency_streamlines": [0, 10],
    }

    bundles = read_data_from_json_file(args.bundles_config)

    ind_dict = {}
    for bundle in bundles:
        ind_dict[bundle] = {}

        bundle_files = [f for f in args.in_jsons if bundle in f]

        for subj in bundle_files:
            if not os.path.isfile(subj):
                continue

            with open(subj) as json_file:
                curr_dict = json.load(json_file)
                if curr_dict == {}:
                    continue
            for metric in metric_list:
                if metric not in ind_dict[bundle]:
                    ind_dict[bundle][metric] = [], []
                ind_dict[bundle][metric][0].extend(curr_dict[metric])
                ind_dict[bundle][metric][1].extend([0] * len(curr_dict[metric]))

    save_data_to_json_file(ind_dict, join(args.out_path, "metrics.json"))

    # colors_dict = {1:'indianred', 2:'forestgreen', 3:'royalblue'}
    for metric in metric_list:
        fig = go.Figure()
        for i, bundle in enumerate(bundles):
            try:
                fig.add_trace(
                    go.Box(
                        y=ind_dict[bundle][metric][0],
                        name=bundle.upper(),
                        marker_size=1.5,
                    )
                )
                fig.update_traces(boxpoints="all", jitter=0.3)
            except Exception as e:
                print(e)
                continue
        fig.update_layout(title=metric.upper(), title_x=0.5, boxgap=0.5, boxgroupgap=0.0)
        fig.update_yaxes(range=y_lims[metric])
        fig.update_layout()
        plotly.offline.plot(
            fig, filename=join(args.out_path, "{}.html".format(metric)), auto_open=False
        )


if __name__ == "__main__":
    main()
