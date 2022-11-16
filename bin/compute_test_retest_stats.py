#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Extract statistics linked to test-retest FINTA.
This script should be used after running the tractometry pipeline on
test-retest data.
Each subject should have at least 2 acquisitions. A .json file is required to
match the subject id (e.g. sub-01) to each individual acquisitions
(e.g. {sub-01:[sub-01_ses-1_run-1,sub-01_ses-1_run-2]}).

We use pingouin's ICC2 value:
**ICC2**: A random sample of :math:`k` raters rate each target. The
      measure is one of absolute agreement in the ratings. ICC2 is sensitive
      to differences in means between raters and is a measure of absolute
      agreement.
"""
import argparse
import csv
import json
import os
from collections import defaultdict

import matplotlib.pyplot as plt
import numpy as np
import pandas
import pingouin
from scilpy.io.utils import (
    add_overwrite_arg,
    assert_output_dirs_exist_and_empty,
    assert_inputs_exist,
)


def _build_arg_parser():
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    p.add_argument(
        "--length_stats", required=True, help="Tractometry length statistics."
    )
    p.add_argument(
        "--volume_stats", required=True, help="Tractometry volume statistics."
    )
    p.add_argument(
        "--streamline_count", required=True, help="Streamline count statistics."
    )
    p.add_argument(
        "--subjects",
        required=True,
        help="JSON file mapping a single subject to all its "
        "acquisition ids (e.g. {sub-01:[sub-01_ses-1_run-1,sub-01_ses-1_run-2]}).",
    )

    p.add_argument("-o", "--output", required=True, help="Output directory.")
    p.add_argument("--show", action="store_true", help="Show figures before saving.")
    p.add_argument(
        "--icc",
        choices=["ICC11", "ICC21", "ICC31", "ICC1k", "ICC2k", "ICC3k"],
        help="ICC types",
    )

    add_overwrite_arg(p)

    return p


def main():
    parser = _build_arg_parser()
    args = parser.parse_args()

    assert_inputs_exist(
        parser,
        [
            args.length_stats,
            args.volume_stats,
            args.streamline_count,
            args.subjects,
        ],
    )
    assert_output_dirs_exist_and_empty(parser, args, args.output, create_dir=True)

    with open(args.length_stats, "r") as f:
        length_stats = json.load(f)

    with open(args.volume_stats, "r") as f:
        volume_stats = json.load(f)

    with open(args.streamline_count, "r") as f:
        streamline_count = json.load(f)

    assert sorted(length_stats.keys()) == sorted(volume_stats.keys()), (
        "Not all --length_stats subjects are present in the " "--volume_stats file."
    )

    assert sorted(length_stats.keys()) == sorted(streamline_count.keys()), (
        "Not all --length_stats subjects are present in the " "--streamline_count file."
    )

    bundles = set()
    bundles_per_label = set()
    for stats in [
        length_stats,
    ]:
        for subid, sub_dict in stats.items():
            if not any("label" in s for s in sub_dict.keys()):
                bundles.update(sub_dict.keys())
            else:
                bundles_per_label.update(sub_dict.keys())

    bundles = sorted(bundles)

    with open(args.subjects, "r") as f:
        subjects_mapping = json.load(f)

    # Setup recursive defaultdict for results[bname][moving|harmonized][metric]
    f = lambda: defaultdict(f)
    results = defaultdict(f)

    # Compute ICC for every bundle and every metric, for moving|harmonized data
    for bname in bundles:
        for data_name, stats in zip(
            ["length", "volume", "streamline_count"],
            [length_stats, volume_stats, streamline_count],
        ):
            stats_key = {
                "length": "mean_length",
                "volume": "volume",
                "streamline_count": "streamline_count",
            }

            # Build DataFrane
            data = []
            for subid, sessids in subjects_mapping.items():
                # Get bundle/metric values for all sessions of this subject

                metric_values = {
                    sessid: stats[sessid][bname][stats_key[data_name]]
                    for sessid in sessids
                    if bname in stats[sessid]
                }
                if metric_values:
                    data.append(
                        pandas.DataFrame(
                            {
                                "subid": [subid] * len(metric_values),
                                "sess_id": [
                                    s.replace(f"{subid}_", "")
                                    for s in metric_values.keys()
                                ],
                                "value": metric_values.values(),
                            }
                        )
                    )
            df = pandas.concat(data, ignore_index=True)
            # Compute ICC
            try:

                icc = pingouin.intraclass_corr(
                    data=df,
                    targets="subid",
                    raters="sess_id",
                    ratings="value",
                    nan_policy="omit",
                )
                if args.icc == "ICC11":
                    index = 0
                elif args.icc == "ICC21":
                    index = 1
                elif args.icc == "ICC31":
                    index = 2
                elif args.icc == "ICC1k":
                    index = 3
                elif args.icc == "ICC2k":
                    index = 4
                elif args.icc == "ICC3k":
                    index = 5
                icc2 = icc["ICC"][index]
                ci = icc["CI95%"][index]
            except AssertionError as e:
                # There is less than 5 values available, pingouin cannot
                # compute ICC
                icc = {"ICC": [0.0, 0.0], "CI95%": [[0.0, 0.0], [0.0, 0.0]]}
                icc2 = icc["ICC"][0]
                ci = icc["CI95%"][0]
            except ValueError as e:
                # There are missing values, pingouin cannot compute ICC
                icc = {"ICC": [0.0, 0.0], "CI95%": [[0.0, 0.0], [0.0, 0.0]]}
                icc2 = icc["ICC"][0]
                ci = icc["CI95%"][0]

            print(icc)
            print(icc2)
            results[bname][data_name] = [icc2, ci]

    # Export results to file
    columns = ["Bundle", "icc", "ci_lower", "ci_upper"]

    with open(os.path.join(args.output, "iccs.csv"), "w") as output_csv:
        writer = csv.writer(output_csv)
        writer.writerow(columns)
        for bundle in results.keys():
            for data_name in ["length", "volume", "streamline_count"]:
                row = [f"{bundle}_{data_name}"]
                # Append ICC
                row.append(results[bundle][data_name][0])
                # Extend with CI
                row.extend(results[bundle][data_name][1])
                writer.writerow(row)

    # Plot results
    n_bars = 3
    x_pos = np.arange(len(bundles)) * (3 + n_bars)

    # results[bname][data_src] == [icc, [lower_CI, upper_CI]]
    bundles_iccs = np.array(
        [
            [results[bname][data_src][0] for bname in bundles]
            for data_src in ["length", "volume", "streamline_count"]
        ]
    )
    bundles_cis = np.array(
        [
            [results[bname][data_src][1] for bname in bundles]
            for data_src in ["length", "volume", "streamline_count"]
        ]
    )

    fig, ax = plt.subplots(figsize=((0.5 * len(bundles)), 5))
    colors = ["orange", "green", "blue"]
    for i, (iccs, cis) in enumerate(zip(bundles_iccs, bundles_cis)):
        lower_abs_error, upper_abs_error = cis.transpose()
        lower_rel_error = iccs - lower_abs_error
        upp_rel_error = upper_abs_error - iccs
        ax.bar(
            x_pos + i,
            iccs,
            yerr=[lower_rel_error, upp_rel_error],
            width=0.8,
            align="center",
            alpha=0.75,
            ecolor="black",
            capsize=2,
            color=colors[i],
        )
    ax.set_xlabel("Bundles")
    ax.set_ylabel("ICC")
    ax.set_xticks(x_pos + 1)
    ax.set_xlim(-2, x_pos[-1] + 3)
    ax.set_xticklabels(bundles, fontdict={"fontsize": 8}, rotation=90)
    ax.set_ylim(-1, 1)
    ax.set_title(f"ICC results")
    ax.yaxis.grid(True)
    ax.legend(["Length", "Volume", "Streamline_count"])

    plt.tight_layout()
    plt.savefig(os.path.join(args.output, f"test_retest_icc_barchart.png"))
    if args.show:
        plt.show()
    plt.close()


if __name__ == "__main__":
    main()
