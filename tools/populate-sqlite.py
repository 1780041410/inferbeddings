#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys

import itertools
import argparse

import sqlite3
from tqdm import tqdm

from inferbeddings.io import read_triples
from inferbeddings.parse import parse_clause

import logging

logger = logging.getLogger(os.path.basename(sys.argv[0]))

# Usage:
# $ ./tools/populate-sqlite.py data/wn18/wordnet-mlj12-train.txt data/wn18/clauses/clauses_0.9.pl

def main(argv):
    def formatter(prog):
        return argparse.HelpFormatter(prog, max_help_position=100, width=200)

    argparser = argparse.ArgumentParser('Populate a Knowledge Base', formatter_class=formatter)

    argparser.add_argument('triples', action='store', type=str, default=None)
    argparser.add_argument('clauses', action='store', type=str, default=None)
    argparser.add_argument('--output', '-o', action='store', type=str, default=None)

    args = argparser.parse_args(argv)

    triples_path = args.triples
    clauses_path = args.clauses
    output_path = args.output

    triples, _ = read_triples(triples_path)

    # Parse the clauses using Sebastian's parser
    with open(clauses_path, 'r') as f:
        clauses_str = [line.strip() for line in f.readlines()]
    clauses = [parse_clause(clause_str) for clause_str in clauses_str]

    # Create a set containing all the entities from the triples
    entity_names = {s for (s, _, _) in triples} | {o for (_, _, o) in triples}

    # Create a set containing all predicate names from the triples and clauses
    predicate_names = {p for (_, p, _) in triples}
    for clause in clauses:
        predicate_names |= {clause.head.predicate.name}
        for atom in clause.body:
            predicate_names |= {atom.predicate.name}

    # Associate each entity and predicate to an unique index
    entity_to_idx = {entity: idx for idx, entity in enumerate(entity_names)}
    idx_to_entity = {idx: entity for entity, idx in entity_to_idx.items()}
    entity_indices = list(idx_to_entity.keys())

    predicate_to_idx = {predicate: idx for idx, predicate in enumerate(predicate_names)}
    idx_to_predicate = {idx: predicate for predicate, idx in predicate_to_idx.items()}
    predicate_indices = list(idx_to_predicate.keys())

    # Creating a set of index triples, for efficiency reasons
    idx_triples = {(entity_to_idx[s], predicate_to_idx[p], entity_to_idx[o]) for (s, p, o) in triples}

    # Adding a field 'idx' to each atom.predicate, containing the index of that predicate
    for clause in clauses:
        head, body = clause.head, clause.body
        head.predicate.idx = predicate_to_idx[head.predicate.name]
        for atom in body:
            atom.predicate.idx = predicate_to_idx[atom.predicate.name]

    # Starting to materialize the KB - until convergence:
    for epoch in [1]:

        connection = sqlite3.connect(':memory:')

        logger.info('Populating the database ..')

        cursor = connection.cursor()
        cursor.execute('CREATE TABLE t (s, p, o)')
        cursor.executemany('INSERT INTO t(s, p, o) VALUES (?, ?, ?)', idx_triples)
        connection.commit()

        logger.info(' .. done.')

        # For each clause ..
        for clause in clauses:
            # .. find all variable assignments that match the body ..
            pass

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main(sys.argv[1:])
