#!/usr/bin/env python3

"""
Generates a Makefile based on metadata descriptions of source files.
"""

__author__ = 'cjm'

import argparse
import yaml
from json import dumps

SKIP = ["goa_pdb", "goa_uniprot_gcrp"]
ONLY_GAF = []

def main():

    parser = argparse.ArgumentParser(description='GO Metadata'
                                                 '',
                                     formatter_class=argparse.RawTextHelpFormatter)

    print("## AUTOGENERATED MAKEFILE\n")
    parser.add_argument('files',nargs='*')
    args = parser.parse_args()
    artifacts = []
    artifacts_by_dataset = {}
    for fn in args.files:
        f = open(fn, 'r')
        obj = yaml.load(f)
        artifacts.extend(obj['datasets'])
        f.close()
    for a in artifacts:
        if 'source' not in a:
            # TODO
            print("## WARNING: no source for: {}".format(a['id']))
            continue
        ds = a['dataset']
        if ds == 'paint':
            print("## WARNING: Skipping PAINT: {}".format(a['id']))
            # TODO
            continue
        if ds == 'rnacentral':
            print("## WARNING: Skipping RNAC: {}".format(a['id']))
            # TODO
            continue

        if ds not in artifacts_by_dataset:
            artifacts_by_dataset[ds] = []
        artifacts_by_dataset[ds].append(a)

    for (ds, alist) in artifacts_by_dataset.items():
        generate_targets(ds, alist)

    targets = [all_files(ds) for ds in artifacts_by_dataset.keys()]
    rule('all_targets', targets)

    simple_ds_list = [ds for (ds, data) in artifacts_by_dataset.items() if not skip_source(ds, data)]
    simple_targets = [all_files(ds) for ds in simple_ds_list]
    rule('all_targets_simple', simple_targets, comments='Excludes aggregated (goa_uniprot)')

    # for now, do not do ttl on goa_uniprot_all
    ttl_targets = [all_ttl(ds) for ds in simple_ds_list]
    rule('all_targets_ttl', ttl_targets, comments='RDF targets. Excludes aggregated (goa_uniprot)')

def generate_targets(ds, alist):
    """
    Generate makefile targets for a dataset, e.g. sgd, goa_human_rna

    Note any dataset can have multiple artifacts associated with it: gaf, gpad, gpi, ...
    """
    types = [a['type'] for a in alist]

    print("## --------------------")
    print("## {}".format(ds))
    print("## --------------------\n")
    if 'gaf' not in types and 'gpad' not in types:
        print("# Metadata incomplete\n")
        rule(all_files(ds))
        return
    if ds in SKIP:
        # TODO move to another config file for 'skips'
        print("# Skipping\n")
        rule(all_files(ds))
        return

    # If any item has the aggregate field, then we just want to pass it through and not run
    # all the targets
    is_ds_aggregated = any([("aggregates" in item) for item in alist])

    ds_targets = [targetdir(ds)]

    if ds not in ONLY_GAF:
        ds_targets += [gzip(filtered_gaf(ds)), gzip(filtered_gpad(ds)), gzip(gpi(ds)), owltools_gafcheck(ds)]

    if is_ds_aggregated:
        ds_targets = [targetdir(ds), gzip(filtered_gaf(ds))]

    if ds == "goa_uniprot_all":
        ds_targets = [
            "target/groups/goa_uniprot_all/goa_uniprot_all.gaf.gz",
            "target/groups/goa_uniprot_all/goa_uniprot_all_noiea.gpad.gz",
            "target/groups/goa_uniprot_all/goa_uniprot_all_noiea.gpi.gz",
            "target/groups/goa_uniprot_all/goa_uniprot_all_noiea-owltools-check.txt",
        ]
        rule(all_files(ds), ds_targets)

        ds_all_ttl = ds_targets + ["target/groups/goa_uniprot_all/goa_uniprot_all_noiea_cam.ttl"]
        rule(all_ttl(ds), ds_all_ttl)

        rule(targetdir(ds),[],
            'mkdir -p '+targetdir(ds))
        url = [e for e in alist if e["type"] == "gaf"][0]['source']
        rule(src_gaf_zip(ds), [targetdir(ds)],
            'wget --retry-connrefused --waitretry=10 -t 10 --no-check-certificate {url} -O $@.tmp && mv $@.tmp $@ && touch $@'.format(url=url))

        return

    rule(all_files(ds), ds_targets)

    ds_all_ttl = ds_targets + [ttl(ds)]
    if ds in ONLY_GAF:
        ds_all_ttl = ds_targets
    rule(all_ttl(ds), ds_all_ttl)

    rule(targetdir(ds),[],
         'mkdir -p '+targetdir(ds))

    # for now we assume everything comes from a GAF
    if 'gaf' in types:
        [gaf] = [a for a in alist if a['type']=='gaf']
        url = gaf['source']
        # GAF from source
        rule(src_gaf_zip(ds),[targetdir(ds)],
             'wget --retry-connrefused --waitretry=10 -t 10 --no-check-certificate {url} -O $@.tmp && mv $@.tmp $@ && touch $@'.format(url=url))

def skip_source(ds, data):
    types = [a['type'] for a in data]
    return ds in SKIP or ('gaf' not in types and 'gpad' not in types)

def create_targetdir(ds):
    return 'create_targetdir_'+ds
def targetdir(ds):
    return 'target/groups/{ds}/'.format(ds=ds)
def all_files(ds):
    return 'all_'+ds
def all_ttl(ds):
    return 'ttl_all_'+ds
def src_gaf_zip(ds):
    return '{dir}{ds}-src.gaf.gz'.format(dir=targetdir(ds),ds=ds)
def src_gaf(ds):
    return "{dir}{ds}-src.gaf".format(dir=targetdir(ds), ds=ds)
def filtered_gaf(ds):
    return '{dir}{ds}.gaf'.format(dir=targetdir(ds),ds=ds)
def filtered_data(fmt, ds):
    return '{dir}{ds}.{fmt}'.format(dir=targetdir(ds), ds=ds, fmt=fmt)
def noiea_gaf(ds):
    return '{dir}{ds}_noiea.gaf'.format(dir=targetdir(ds),ds=ds)
def filtered_gpad(ds):
    return '{dir}{ds}.gpad'.format(dir=targetdir(ds),ds=ds)
def ttl(ds):
    return '{dir}{ds}_cam.ttl'.format(dir=targetdir(ds),ds=ds)
def inferred_ttl(ds):
    return "{dir}{ds}_inferred.ttl".format(dir=targetdir(ds), ds=ds)
def owltools_gafcheck(ds):
    return '{dir}{ds}-owltools-check.txt'.format(dir=targetdir(ds),ds=ds)
def gpi(ds):
    return '{dir}{ds}.gpi'.format(dir=targetdir(ds),ds=ds)
def gzip(f):
    return '{}.gz'.format(f)

def rule(target,dependencies=[],executable=None, comments=None):
    if comments != None:
        print("## {}".format(comments))
    if isinstance(dependencies,list):
        dependencies = " ".join(dependencies)
    print("{}: {}".format(target,dependencies))
    if executable is not None:
        for line in executable.split("\n"):
            print("\t{}".format(line))
    print()

if __name__ == "__main__":
    main()
