#!/usr/bin/env nextflow

if(params.help) {
    usage = file("$baseDir/USAGE")
    cpu_count = Runtime.runtime.availableProcessors()

    bindings = ["cpu_count":"$cpu_count"]

    engine = new groovy.text.SimpleTemplateEngine()
    template = engine.createTemplate(usage.text).make(bindings)
    print template.toString()
    return
}

cpu_count = Runtime.runtime.availableProcessors()
if (!params.processes){
    processes = cpu_count
}
else{
    processes = params.processes
}

log.info "Correlation Flow"
log.info "==============================================="
log.info ""
log.info "Start time: $workflow.start"
log.info ""

log.debug "[Command-line]"
log.debug "$workflow.commandLine"
log.debug ""

log.info "[Git Info]"
log.info "$workflow.repository - $workflow.revision [$workflow.commitId]"
log.info ""

log.info "Options"
log.info "======="
log.info "Num Processes: ${processes}"
log.info ""
log.info ""

workflow.onComplete {
    log.info "Pipeline completed at: $workflow.complete"
    log.info "Execution status: ${ workflow.success ? 'OK' : 'failed' }"
    log.info "Execution duration: $workflow.duration"
}

log.info "Input: $params.input"
root = file(params.input)

Channel
    .fromFilePairs("$root/**/*/Register_Streamlines/*trk", size: -1) { it.parent.parent.parent.name }
    .set{ subjects } // [sid, AF.trk, IFOF.trk, ...]

subjects_config = Channel.fromPath("$params.subjects_config")
Channel.fromPath("$params.bundles_config").into{ bundles_config; bundles_config_for_agreements }



subjects
    .combine(subjects_config)
    .combine(bundles_config)
    .set{files_for_agreements} 


process Compute_Agreements {
    errorStrategy 'ignore'
    memory '2 GB'

    input:
    set sid, file(subjects), file(subjects_config), file(bundles_config) from files_for_agreements

    output:
    file "*.json" into agreement_results

    script:
    String bundles_list = subjects.join(", ").replace(',', '')
    """
    bundle=\$(jq 'keys[]' ${bundles_config})
    for b in \$bundle
    do 
        b=\$(eval echo \$b)
        if [[ "${bundles_list}" == *"\${b}"* ]]; then
            files=\$(echo ${bundles_list} |xargs -d' ' -n 1| grep \$b)
            scil_evaluate_bundles_pairwise_agreement_measures.py \$files ${sid}_\${b}.json \
            --indent 4 --sort_keys -f --processes ${processes}
        fi

    done
    """
}

agreement_results
    .collect()
    .set{all_files_for_agreements}

process Aggregate_Agreements {
    publishDir = params.statsPublishDir

    input:
    file(metrics) from all_files_for_agreements
    file(config) from bundles_config_for_agreements

    output:
    file "*.html"
    file "*.json"

    script:
    String metrics_list = metrics.join(", ").replace(',', '')
    """
    plot_agreements.py ${metrics_list} . --bundles_config ${config}
    """
}

