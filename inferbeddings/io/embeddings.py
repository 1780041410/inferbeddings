# -*- coding: utf-8 -*-

import gensim
from inferbeddings.io import iopen

import logging

logger = logging.getLogger(__name__)


def load_glove(path, words=None):
    word_to_embedding = {}

    with iopen(path, 'r') as stream:
        for n, line in enumerate(stream):
            if not isinstance(line, str):
                line = line.decode('utf-8')
            split_line = line.split(' ')
            word = split_line[0]

            if words is None or word in words:
                try:
                    word_to_embedding[word] = [float(f) for f in split_line[1:]]
                except ValueError:
                    logger.error('{}\t{}\t{}'.format(n, word, str(split_line)))

    return word_to_embedding


def load_glove_words(path, words=None):
    res = set()

    with iopen(path, 'r') as stream:
        for n, line in enumerate(stream):
            if not isinstance(line, str):
                line = line.decode('utf-8')
            split_line = line.split(' ')
            word = split_line[0]

            if words is None or word in words:
                res.add(word)

    return res


def load_word2vec(path, words=None, binary=True):
    word_to_embedding = {}

    model = gensim.models.KeyedVectors.load_word2vec_format(path, binary=binary)
    for word in words:
        if word in model:
            word_to_embedding[word] = model[word].tolist()

    return word_to_embedding


def load_word2vec_words(path, words=None):
    raise NotImplementedError('Operation not yet implemented')
