#!/bin/bash

set -e

usage() {
  echo "$(basename "$0") [-i inputs -t metric_flow -r registration_flow -c correlation_flow -s subjects -b bundles_config -o output_dir -n processes -a target_anat]" 1>&2
  exit 1
}

while getopts "i:t:r:c:o:s:n:a:b:" args; do
  case "${args}" in
  i) inputs=${OPTARG} ;;
  t) metric_flow=${OPTARG} ;;
  r) registration_flow=${OPTARG} ;;
  c) correlation_flow=${OPTARG} ;;
  o) output=${OPTARG} ;;
  s) subjects=${OPTARG} ;;
  n) processes=${OPTARG} ;;
  a) target_anat=${OPTARG} ;;
  b) bundles_config=${OPTARG} ;;
  *) usage ;;
  esac
done
shift $((OPTIND - 1))

if [ -z "$inputs" ] ||
  [ -z "$metric_flow" ] ||
  [ -z "$registration_flow" ] ||
  [ -z "$correlation_flow" ] ||
  [ -z "$subjects" ] ||
  [ -z "$output" ] ||
  [ -z "$processes" ] ||
  [ -z "$target_anat" ] ||
  [ -z "$bundles_config" ]; then
  usage
else
  echo "Inputs: ${inputs}"
  echo "metric_flow: ${metric_flow}"
  echo "Registration_flow: ${registration_flow}"
  echo "Correlation_flow: ${correlation_flow}"
  echo "Subjects: ${subjects}"
  echo "Bundles_config: ${bundles_config}"
  echo "Outputs: ${output}"
  echo "Processes: ${processes}"
  echo "Target_anat: ${target_anat}"
fi

metric_dir=$output/metric_flow
registration_dir=$output/registration_flow
correlation_dir=$output/correlation_flow

mkdir -p "$metric_dir"
mkdir -p "$registration_dir"
mkdir -p "$correlation_dir"

run_metricflow() {
  local suffix=$1
  local input=$2

  # Run metric-flow
  nextflow run "$metric_flow"/main.nf -w "$metric_dir"/work_"$suffix" --output_dir "$metric_dir"/output_"$suffix" \
    --input "$input" -with-report "$metric_dir"/report_"${suffix}".html --use_provided_centroids false -resume --processes $processes \
    --min_streamline_count 50000
}

run_registrationflow() {
  local suffix=$1
  local input=$2

  # Run metric-flow
  nextflow run "$registration_flow"/main.nf -w "$registration_dir"/work_"$suffix" --output_dir "$registration_dir"/output_"$suffix" \
    --input "$input" -resume --processes $processes --target_anat ${target_anat} --resampling -1
}

run_correlationflow() {
  local suffix=$1
  local input=$2

  # Run metric-flow

  nextflow run "$correlation_flow"/main.nf -w "$correlation_dir"/work_"$suffix" --output_dir "$correlation_dir"/output_"$suffix" \
    --input "$input" --subjects_config $subjects --bundles_config $bundles_config -resume --processes $processes
}

run_metricflow "metric" "$inputs"

for icc in ICC11 ICC21 ICC31 ICC1k ICC2k ICC3k; do
  compute_test_retest_stats.py --length_stats "$metric_dir"/output_metric/Statistics/length_stats.json \
    --volume_stats "$metric_dir"/output_metric/Statistics/volumes.json \
    --streamline_count "$metric_dir"/output_metric/Statistics/streamline_count.json \
    --subject $subjects -o $output/test_retest_${icc} -f --icc "${icc}"
done

run_registrationflow "registration" "$inputs"

sub=$(jq 'keys[]' ${subjects})
mkdir -p ${registration_dir}/inputs_correlation
whole_path_registration=$(readlink -f ${registration_dir}/output_registration)
for s in $sub; do
  s=$(eval echo $s)
  mkdir -p ${correlation_dir}/inputs_correlation/${s}
  ln -sf ${whole_path_registration}/${s}* ${correlation_dir}/inputs_correlation/${s}/
done

run_correlationflow "correlation" "${correlation_dir}/inputs_correlation"
