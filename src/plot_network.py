#!/usr/bin/env python3

import pandas as pd
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt
import seaborn as sns
import pygraphviz as pgv

from datetime import date
from networkx.drawing.nx_pydot import write_dot
from pprint import pprint

from utils import read_lines

import argparse
import os
import sys
import re

PROGS = ['sccmap', 'osage', 'patchwork', 'twopi', 'nop', 'unflatten', 'circo', 'gvpr', 'tred',
        'gc', 'dot', 'sfdp', 'ccomps', 'gvcolor', 'acyclic', 'neato', 'fd']
def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument('in_files', metavar='I', nargs='+',
            help='The path to the input file')
    parser.add_argument('-o', '--out-dir', default=os.path.join('..', 'data'),
            help='The path to the output directory')
    parser.add_argument('-m', '--model-file', default=os.path.join('..', 'data', 'gred.dat'),
            help='The path to the file listing the names of the models to be plotted')
    parser.add_argument('-t', '--threshold', type=float, default=.5,
            help='The minimum cosine similarity to consider as consituting a significant ' + \
                 'connection between regions in a given month')
    parser.add_argument('-p', '--prog', default='circo', choices=PROGS,
            help='The positioning algortihm to use when plotting, passed to pygraphviz')
    parser.add_argument('-l', '--label-edges', action='store_true',
            help='Pass this flag to label edges with the cosine similarity in the output plot')
    parser.add_argument('-w', '--print-weights', action='store_true',
            help='Pass this flag to print out the total weights for each region')
    parser.add_argument('-d', '--plot-dipole', action='store_true',
            help='Pass this flag to destinguish between hot and cold extremes')

    return parser.parse_args()

def create_network(arr, models, threshold=0):
    arr[arr < threshold] = 0
    np.fill_diagonal(arr, 0)
    
    g = nx.from_numpy_matrix(arr)
    nx.relabel_nodes(g, {i: m for i, m in enumerate(models)}, copy=False)
    return g

REGION_LABEL_REGEX = r'(region_\d+)'
def get_region_label(filename):
    match = re.search(REGION_LABEL_REGEX, filename)
    if match:
        return '_' + match.groups(1)[0]
    else:
        return ''

CMAP = sns.color_palette('flare', as_cmap=True)
HOT_COLD_CMAP = sns.color_palette('coolwarm', as_cmap=True)
def get_color(val, cmap=CMAP):
    r, g, b, a = [int(256 * x) for x in cmap(val)]
    return f'#{r:0>2x}{g:0>2x}{b:0>2x}'

    #scaled_val = 255 - int(255 * val)
    #return f'#{scaled_val:0>2x}{scaled_val:0>2x}{scaled_val:0>2x}'

def plot_network(g, prog='circo', label_edges=False, save_as='network.pdf',
        plot_dipole=False):
    weights = nx.get_edge_attributes(g, 'weight')
    a = nx.nx_agraph.to_agraph(g)

    cmap = CMAP
    if plot_dipole:
        cmap = HOT_COLD_CMAP

    #degrees = dict(nx.degree(g, weight='cos_sim'))
    degrees = dict(nx.degree(g, weight='cos_sim'))
    max_degree = max(np.max(list(degrees.values())), 1)
    if plot_dipole:
        max_degree *= 2
    degrees = {n: d / max_degree for n, d in degrees.items()}

    for node_id in a.nodes():
        node = a.get_node(node_id)
        
        d = degrees[node_id]
        node.attr['color'] = get_color(degrees[node_id])
        
        node.attr['penwidth'] = 2

    for source, target in a.edges():
        edge = a.get_edge(source, target)

        weight = weights[(source, target)]
        edge.attr['weight'] = weight
        edge.attr['color'] = get_color(weight)
        edge.attr['penwidth'] = 2

        if label_edges:
            edge.attr['label'] = weight
    
    a.draw(save_as, prog=prog)

def print_degrees(g):
    degrees = dict(nx.degree(g, weight='cos_sim'))
    nodes = sorted(degrees.keys(), key=lambda k: degrees[k], reverse=True)
    for n in nodes:
        print(f'\t{n}: {degrees[n]}')

season_names = ['DJF', 'MAM', 'JJA', 'SON']
def get_season(month):
    if month == 12:
        return 0
    return month // 3

def main():
    args = parse_args()
    in_files = args.in_files
    out_dir = args.out_dir
    threshold = args.threshold
    print_weights = args.print_weights
    prog = args.prog
    models = read_lines(args.model_file)

    plot_settings = {
        'prog': args.prog,
        'label_edges': args.label_edges,
        'plot_dipole': args.plot_dipole,
    }

    for in_file in in_files:
        arr = np.loadtxt(in_file, delimiter=',')
        graph = create_network(arr, models, threshold=threshold)

        region_label = get_region_label(in_file)
        out_file = os.path.join(out_dir, f'{prog}_cos_sim_{threshold}_network{region_label}.pdf')
        
        plot_network(graph, save_as=out_file, **plot_settings)

        if print_weights:
            print_degrees(graph)    

if __name__ == '__main__':
    main()
