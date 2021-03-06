# -*- coding: utf-8 -*-

import tensorflow as tf

from inferbeddings.models import TranslatingModel, BilinearDiagonalModel, ComplexModel
from inferbeddings.models import similarities

import logging

logger = logging.getLogger(__name__)


class ClosedForm:
    def __init__(self, parser,
                 predicate_embedding_layer,
                 model_class, model_parameters,
                 is_unit_cube):
        self.parser = parser
        self.predicate_embedding_layer = predicate_embedding_layer
        self.model_class, self.model_parameters = model_class, model_parameters
        self.is_unit_cube = is_unit_cube

    def _to_idx(self, predicate_name):
        return self.parser.predicate_to_index[predicate_name]

    def _translating_loss(self, clause):
        head, body = clause.head, clause.body

        # At the moment, only simple rules as in "r(X, Y) :- b(X, Y)" are supported
        assert len(body) == 1
        body_atom = body[0]

        variable_names = {arg.name for arg in head.arguments} | {arg.name for arg in body_atom.arguments}
        assert len(variable_names) == 2

        # Check if it is an inverse rule, as in r(X, Y) :- b(Y, X), or not, as in r(X, Y) :- b(X, Y).
        is_inverse = False
        if head.arguments[0].name == body_atom.arguments[1].name:
            if head.arguments[1].name == body_atom.arguments[0].name:
                is_inverse = True

        # We only support TransE in its L2 squared distance formulation
        assert self.model_parameters['similarity_function'] == similarities.l2_sqr

        # Indices of q and r, respectively
        r_idx, b_idx = self._to_idx(head.predicate.name), self._to_idx(body_atom.predicate.name)

        r = tf.nn.embedding_lookup(self.predicate_embedding_layer, r_idx)
        b = tf.nn.embedding_lookup(self.predicate_embedding_layer, b_idx)

        prefix = tf.reduce_sum(tf.square(r)) - tf.reduce_sum(tf.square(b))
        if is_inverse:
            if self.is_unit_cube:
                loss = tf.nn.relu(prefix + 2 * tf.reduce_sum(tf.abs(r + b)))
            else:
                loss = tf.nn.relu(prefix + 4 * tf.sqrt(tf.reduce_sum(tf.square(r + b))))
        else:
            if self.is_unit_cube:
                loss = tf.nn.relu(prefix + 2 * tf.reduce_sum(tf.abs(r - b)))
            else:
                loss = tf.nn.relu(prefix + 4 * tf.sqrt(tf.reduce_sum(tf.square(r - b))))
        return loss

    def _bilinear_diagonal_loss_one(self, clause):
        head, body = clause.head, clause.body

        # At the moment, only simple rules as in "r(X, Y) :- b(X, Y)" are supported
        assert len(body) == 1
        body_atom = body[0]

        variable_names = {arg.name for arg in head.arguments} | {arg.name for arg in body_atom.arguments}
        assert len(variable_names) == 2

        # Indices of q and r, respectively
        r_idx, b_idx = self._to_idx(head.predicate.name), self._to_idx(body_atom.predicate.name)

        r = tf.nn.embedding_lookup(self.predicate_embedding_layer, r_idx)
        b = tf.nn.embedding_lookup(self.predicate_embedding_layer, b_idx)

        if self.is_unit_cube:
            loss = tf.reduce_sum(tf.nn.relu(b - r))
        else:
            loss = tf.reduce_max(tf.abs(b - r))
        return loss

    def _bilinear_diagonal_loss_two(self, clause):
        head, body = clause.head, clause.body

        # At the moment, only simple rules as in "r(X, Z) :- b1(X, Y), b2(Y, Z)" are supported
        assert len(body) == 2
        body_atom_1 = body[0]
        body_atom_2 = body[1]

        variable_names = {arg.name for arg in head.arguments} | {arg.name for arg in body_atom_1.arguments} | {arg.name for arg in body_atom_2.arguments}
        assert len(variable_names) == 3

        assert body_atom_1.arguments[0].name == head.arguments[0].name
        assert body_atom_2.arguments[1].name == head.arguments[1].name

        # Indices of b1, b2 and r, respectively
        r_idx = self._to_idx(head.predicate.name)
        b1_idx = self._to_idx(body_atom_1.predicate.name)
        b2_idx = self._to_idx(body_atom_2.predicate.name)

        r = tf.nn.embedding_lookup(self.predicate_embedding_layer, r_idx)
        b1 = tf.nn.embedding_lookup(self.predicate_embedding_layer, b1_idx)
        b2 = tf.nn.embedding_lookup(self.predicate_embedding_layer, b2_idx)

        if self.is_unit_cube:
            case_0 = tf.zeros_like(r)
            case_1 = - r
            case_2 = - r + tf.minimum(b1, b2)
            case_3 = tf.minimum(tf.zeros_like(r), b1)
            case_4 = tf.minimum(tf.zeros_like(r), b2)

            # Creating a [k, 5]-dimensional tensor
            _cases = tf.transpose(tf.stack([case_0, case_1, case_2, case_3, case_4]))

            # Computing max(case_i)
            _losses = tf.reduce_max(_cases, axis=1)

            # Computing \sum_i max(case_i)
            loss = tf.reduce_sum(_losses)
        else:
            case_0 = tf.zeros_like(r)
            case_1 = tf.minimum(b1, b2) - r
            case_2 = tf.minimum(- b1, - b2) - r
            case_3 = tf.minimum(b1, - b2) + r
            case_4 = tf.minimum(- b1, b2) + r

            # Creating a [k, 5]-dimensional tensor
            _cases = tf.transpose(tf.stack([case_0, case_1, case_2, case_3, case_4]))

            # Computing max(case_i)
            _losses = tf.reduce_max(_cases, axis=1)

            # Computing \max_i max(case_i)
            loss = tf.reduce_max(_losses)
        return loss

    def _complex_loss(self, clause):
        head, body = clause.head, clause.body

        # At the moment, only simple rules as in "r(X, Y) :- b(X, Y)" are supported
        assert len(body) == 1
        body_atom = body[0]

        variable_names = {arg.name for arg in head.arguments} | {arg.name for arg in body_atom.arguments}
        assert len(variable_names) == 2

        # Check if it is an inverse rule, as in r(X, Y) :- b(Y, X), or not, as in r(X, Y) :- b(X, Y).
        is_inverse = False
        if head.arguments[0].name == body_atom.arguments[1].name:
            if head.arguments[1].name == body_atom.arguments[0].name:
                is_inverse = True

        # Indices of q and r, respectively
        r_idx, b_idx = self._to_idx(head.predicate.name), self._to_idx(body_atom.predicate.name)

        r = tf.nn.embedding_lookup(self.predicate_embedding_layer, r_idx)
        b = tf.nn.embedding_lookup(self.predicate_embedding_layer, b_idx)

        n = r.get_shape()[-1].value
        r_re, r_im = r[:n // 2], r[n // 2:]
        b_re, b_im = b[:n // 2], b[n // 2:]

        if is_inverse:
            if self.is_unit_cube:
                # This ha the same form as the simple implications case,
                # but with r replaced by \compl{r} or, more specifically,
                # r_im replaced by - r_im.
                r_im = - r_im

                delta_re, delta_im = b_re - r_re, b_im - r_im

                # For each index, the loss will be the maximum across such values
                case_1 = 2 * delta_re
                case_2 = tf.abs(delta_im)
                case_3 = delta_re + tf.abs(delta_im)

                # The result will be a [k, 3]-dimensional tensor
                _cases = tf.transpose(tf.stack([case_1, case_2, case_3]))
                # Computing the maximum on dimension 1, leading to a [k]-dimensional tensor
                _losses = tf.reduce_max(_cases, axis=1)

                loss = tf.reduce_sum(_losses)
            else:
                loss = tf.reduce_max(tf.sqrt(tf.square(b_re - r_re) + tf.square(b_im + r_im)))
        else:
            if self.is_unit_cube:
                delta_re, delta_im = b_re - r_re, b_im - r_im

                # For each index, the loss will be the maximum across such values
                case_1 = 2 * delta_re
                case_2 = tf.abs(delta_im)
                case_3 = delta_re + tf.abs(delta_im)

                # The result will be a [k, 3]-dimensional tensor
                _cases = tf.transpose(tf.stack([case_1, case_2, case_3]))
                # Computing the maximum on dimension 1, leading to a [k]-dimensional tensor
                _losses = tf.reduce_max(_cases, axis=1)

                loss = tf.reduce_sum(_losses)
            else:
                loss = tf.reduce_max(tf.sqrt(tf.square(b_re - r_re) + tf.square(b_im - r_im)))
        return loss

    def __call__(self, clause):
        clause_body = clause.body

        loss = None
        if self.model_class == BilinearDiagonalModel:
            # We are using DistMult
            if len(clause_body) == 1:
                loss = self._bilinear_diagonal_loss_one(clause)
            elif len(clause_body) == 2:
                loss = self._bilinear_diagonal_loss_two(clause)
        elif self.model_class == TranslatingModel:
            # We are using DistMult
            loss = self._translating_loss(clause)
        elif self.model_class == ComplexModel:
            # We are using ComplEx
            loss = self._complex_loss(clause)

        assert loss is not None

        return tf.nn.relu(loss)
