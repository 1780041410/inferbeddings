# -*- coding: utf-8 -*-

import tensorflow as tf


class AdversarialSets2:
    """
    Utility class for generating Adversarial Sets for RTE.
    """

    def __init__(self, model_class, model_kwargs,
                 scope_name='adversary', embedding_size=300, batch_size=1024, max_sequence_length=10,
                 entailment_idx=0, contradiction_idx=1, neutral_idx=2):
        self.model_class = model_class
        self.model_kwargs = model_kwargs

        self.scope_name = scope_name
        self.embedding_size = embedding_size
        self.batch_size = batch_size
        self.max_sequence_length = max_sequence_length

        self.entailment_idx = entailment_idx
        self.contradiction_idx = contradiction_idx
        self.neutral_idx = neutral_idx

    def _get_sequence(self, name):
        """
        Utility function.

        :param name: Name of the Variable
        :return: tf.Variable with shape [batch size, sequence length, embedding size]
        """
        with tf.variable_scope(self.scope_name):
            sentence = tf.get_variable(name=name,
                                       shape=[self.batch_size, self.max_sequence_length, self.embedding_size],
                                       initializer=tf.contrib.layers.xavier_initializer(), dtype=tf.float32)
            sentence_length = tf.get_variable(name='{}_length'.format(name), shape=[self.batch_size],
                                              initializer=tf.zeros_initializer(), dtype=tf.int32)
        return sentence, sentence_length

    def _probability(self,
                     sequence1, sequence1_length,
                     sequence2, sequence2_length,
                     predicate_idx):
        model_kwargs = self.model_kwargs.copy()

        model_kwargs.update({
            'sequence1': sequence1, 'sequence1_length': sequence1_length,
            'sequence2': sequence2, 'sequence2_length': sequence2_length
        })

        logits = self.model_class(reuse=True, **model_kwargs)()
        return tf.nn.softmax(logits)[:, predicate_idx]

    def rule1_loss(self):
        """
        Adversarial loss term enforcing the rule:
            p(contradicts(S1, S2)) ~ p(contradicts(S2, S1))
        by computing:
            abs[p(contradicts(S1, S2)) - p(contradicts(S2, S1))],
        where the sentence embeddings S1 and S2 can be learned adversarially.

        :return: (tf.Tensor, Set[tf.Variable]) pair containing the adversarial loss
            and the adversarially trainable variables.
        """
        # S1 - [batch_size, time_steps, embedding_size] sentence embedding.
        sequence1, sequence1_length = self._get_sequence(name='rule1_sequence1')
        # S2 - [batch_size, time_steps, embedding_size] sentence embedding.
        sequence2, sequence2_length = self._get_sequence(name='rule1_sequence2')

        # Probability that S1 contradicts S2
        probability_s1_contradicts_s2 = self._probability(sequence1, sequence1_length, sequence2, sequence2_length, self.contradiction_idx)
        # Probability that S2 contradicts S1
        probability_s2_contradicts_s1 = self._probability(sequence2, sequence2_length, sequence1, sequence1_length, self.contradiction_idx)

        loss = tf.abs(probability_s1_contradicts_s2 - probability_s2_contradicts_s1)
        return loss, [sequence1, sequence2], [sequence1_length, sequence2_length]

    def rule2_loss(self):
        """
        Adversarial loss term enforcing the rule:
            entails(S1, S2), entails(S2, S3) \implies entails(S1, S3)
        or, in other terms:
            min(p(entails(S1, S2)) + p(entails(S2, S3))) <= p(entails(S1, S3))
        by computing:
            ReLU[min(p(entails(S1, S2)) + p(entails(S2, S3))) - p(entails(S1, S3))]
        where the sentence embeddings S1, S2 and S3 can be learned adversarially.

        :return: (tf.Tensor, Set[tf.Variable]) pair containing the adversarial loss
            and the adversarially trainable variables.
        """
        # S1 - [batch_size, time_steps, embedding_size] sentence embedding.
        sequence1, sequence1_length = self._get_sequence(name='rule2_sequence1')
        # S2 - [batch_size, time_steps, embedding_size] sentence embedding.
        sequence2, sequence2_length = self._get_sequence(name='rule2_sequence2')
        # S3 - [batch_size, time_steps, embedding_size] sentence embedding.
        sequence3, sequence3_length = self._get_sequence(name='rule2_sequence3')

        # Probability that S1 entails S2
        probability_s1_entails_s2 = self._probability(sequence1, sequence1_length, sequence2, sequence2_length, self.entailment_idx)
        # Probability that S2 entails S3
        probability_s2_entails_s3 = self._probability(sequence2, sequence2_length, sequence3, sequence3_length, self.entailment_idx)
        # Probability that S1 entails S3
        probability_s1_entails_s3 = self._probability(sequence1, sequence1_length, sequence3, sequence3_length, self.entailment_idx)

        body_score = tf.minimum(probability_s1_entails_s2, probability_s2_entails_s3)
        head_score = probability_s1_entails_s3

        # The loss is > 0 if min(P1->P2, P2->P3) > P1->P3, 0 otherwise
        loss = tf.nn.relu(body_score - head_score)
        return loss, [sequence1, sequence2, sequence3], [sequence1_length, sequence2_length, sequence3_length]

    def rule3_loss(self):
        """
        Adversarial loss term enforcing the rule:
            p(entails(S1, S1)) > p(contradicts(S1, S1))
            p(entails(S1, S1)) > p(neutral(S1, S1))
        by computing:
            ReLU[p(contradicts(S1, S1)) - p(entails(S1, S1))]
            + ReLU[p(neutral(S1, S1)) - p(entails(S1, S1))],
        where the sentence embeddings S1 and S2 can be learned adversarially.

        :return: (tf.Tensor, Set[tf.Variable]) pair containing the adversarial loss
            and the adversarially trainable variables.
        """
        # S1 - [batch_size, time_steps, embedding_size] sentence embedding.
        sequence1, sequence1_length = self._get_sequence(name='rule3_sequence1')

        probability_s1_entails_s1 = self._probability(sequence1, sequence1_length, sequence1, sequence1_length, self.entailment_idx)
        probability_s1_contradicts_s1 = self._probability(sequence1, sequence1_length,  sequence1, sequence1_length, self.contradiction_idx)
        probability_s1_neutral_s1 = self._probability(sequence1, sequence1_length, sequence1, sequence1_length, self.neutral_idx)

        loss = tf.nn.relu(probability_s1_contradicts_s1 - probability_s1_entails_s1) + \
               tf.nn.relu(probability_s1_neutral_s1 - probability_s1_entails_s1)
        return loss, [sequence1], [sequence1_length]

    def rule4_loss(self):
        """
        Adversarial loss term enforcing the rule:
            entails(S1, S2), contradicts(S2, S3) => contradicts(S1, S3)
        by making sure that the following constraint:
            min(p(entails(S1, S2)), p(contradicts(S2, S3))) < p(contradicts(S1, S3))
        Always holds. This constraint can be encoded by the following loss:
            ReLU[min(p(entails(S1, S2)), p(contradicts(S2, S3))) - p(contradicts(S1, S3))]

        :return: (tf.Tensor, Set[tf.Variable]) pair containing the adversarial loss
            and the adversarially trainable variables.
        """
        # S1 - [batch_size, time_steps, embedding_size] sentence embedding.
        sequence1, sequence1_length = self._get_sequence(name='rule4_sequence1')
        # S2 - [batch_size, time_steps, embedding_size] sentence embedding.
        sequence2, sequence2_length = self._get_sequence(name='rule4_sequence2')
        # S3 - [batch_size, time_steps, embedding_size] sentence embedding.
        sequence3, sequence3_length = self._get_sequence(name='rule4_sequence3')

        # Probability that S1 entails S2
        probability_s1_entails_s2 = self._probability(sequence1, sequence1_length, sequence2, sequence2_length, self.entailment_idx)
        # Probability that S2 contradicts S3
        probability_s2_contradicts_s3 = self._probability(sequence2, sequence2_length, sequence3, sequence3_length, self.contradiction_idx)
        # Probability that S1 contradicts S3
        probability_s1_contradicts_s3 = self._probability(sequence1, sequence1_length, sequence3, sequence3_length, self.contradiction_idx)

        body_score = tf.minimum(probability_s1_entails_s2, probability_s2_contradicts_s3)
        head_score = probability_s1_contradicts_s3

        # The loss is > 0 if min(P1 => P2, P2 X> P3) > P1 X> P3, 0 otherwise
        loss = tf.nn.relu(body_score - head_score)
        return loss, [sequence1, sequence2, sequence3], [sequence1_length, sequence2_length, sequence3_length]

    def rule5_loss(self):
        """
        Adversarial loss term enforcing the rule:
            neutral(S1, S2), entails(S2, S3) => neutral(S1, S3)
        by making sure that the following constraint:
            min(p(neutral(S1, S2)), p(entails(S2, S3))) < p(neutral(S1, S3))
        Always holds. This constraint can be encoded by the following loss:
            ReLU[min(p(neutral(S1, S2)), p(entails(S2, S3))) - p(neutral(S1, S3))]

        :return: (tf.Tensor, Set[tf.Variable]) pair containing the adversarial loss
            and the adversarially trainable variables.
        """
        # S1 - [batch_size, time_steps, embedding_size] sentence embedding.
        sequence1, sequence1_length = self._get_sequence(name='rule5_sequence1')
        # S2 - [batch_size, time_steps, embedding_size] sentence embedding.
        sequence2, sequence2_length = self._get_sequence(name='rule5_sequence2')
        # S3 - [batch_size, time_steps, embedding_size] sentence embedding.
        sequence3, sequence3_length = self._get_sequence(name='rule5_sequence3')

        # Probability that S1 neutral S2
        probability_s1_neutral_s2 = self._probability(sequence1, sequence1_length, sequence2, sequence2_length, self.neutral_idx)
        # Probability that S2 entails S3
        probability_s2_entails_s3 = self._probability(sequence2, sequence2_length, sequence3, sequence3_length, self.entailment_idx)
        # Probability that S1 neutral S3
        probability_s1_neutral_s3 = self._probability(sequence1, sequence1_length, sequence3, sequence3_length, self.neutral_idx)

        body_score = tf.minimum(probability_s1_neutral_s2, probability_s2_entails_s3)
        head_score = probability_s1_neutral_s3

        # The loss is > 0 if min(P1 ~ P2, P2 => P3) > P1 ~ P3, 0 otherwise
        loss = tf.nn.relu(body_score - head_score)
        return loss, [sequence1, sequence2, sequence3], [sequence1_length, sequence2_length, sequence3_length]

    def rule6_loss(self):
        """
        Adversarial loss term enforcing the rule:
            contradicts(S1, S2) => contradicts(S2, S1)
        by making sure that the following constraint:
            p(contradicts(S1, S2)) < p(contradicts(S2, S1))
        Always holds. This constraint can be encoded by the following loss:
            ReLU[p(contradicts(S1, S2)) - p(contradicts(S2, S1))]

        :return: (tf.Tensor, Set[tf.Variable]) pair containing the adversarial loss
            and the adversarially trainable variables.
        """
        # S1 - [batch_size, time_steps, embedding_size] sentence embedding.
        sequence1, sequence1_length = self._get_sequence(name='rule6_sequence1')
        # S2 - [batch_size, time_steps, embedding_size] sentence embedding.
        sequence2, sequence2_length = self._get_sequence(name='rule6_sequence2')

        # Probability that S1 contradicts S2
        probability_s1_contradicts_s2 = self._probability(sequence1, sequence1_length, sequence2, sequence2_length, self.contradiction_idx)
        # Probability that S2 contradicts S1
        probability_s2_contradicts_s1 = self._probability(sequence2, sequence2_length, sequence1, sequence1_length, self.contradiction_idx)

        body_score = probability_s1_contradicts_s2
        head_score = probability_s2_contradicts_s1

        loss = tf.nn.relu(body_score - head_score)
        return loss, [sequence1, sequence2], [sequence1_length, sequence2_length]

    def rule7_loss(self):
        """
        Adversarial loss term enforcing the rule:
            entails(S1, S2) => neutral(S2, S1)
        by making sure that the following constraint:
            p(entails(S1, S2)) < p(neutral(S2, S1))
        Always holds. This constraint can be encoded by the following loss:
            ReLU[p(entails(S1, S2)) - p(neutral(S2, S1))]

        :return: (tf.Tensor, Set[tf.Variable]) pair containing the adversarial loss
            and the adversarially trainable variables.
        """
        # S1 - [batch_size, time_steps, embedding_size] sentence embedding.
        sequence1, sequence1_length = self._get_sequence(name='rule7_sequence1')
        # S2 - [batch_size, time_steps, embedding_size] sentence embedding.
        sequence2, sequence2_length = self._get_sequence(name='rule7_sequence2')

        # Probability that S1 contradicts S2
        probability_s1_entails_s2 = self._probability(sequence1, sequence1_length, sequence2, sequence2_length, self.entailment_idx)
        # Probability that S2 contradicts S1
        probability_s2_neutral_s1 = self._probability(sequence2, sequence2_length, sequence1, sequence1_length, self.neutral_idx)

        body_score = probability_s1_entails_s2
        head_score = probability_s2_neutral_s1

        loss = tf.nn.relu(body_score - head_score)
        return loss, [sequence1, sequence2], [sequence1_length, sequence2_length]

    def rule8_loss(self):
        """
        Adversarial loss term enforcing the rule:
            neutral(S1, S2) => neutral(S2, S1)
        by making sure that the following constraint:
            p(neutral(S1, S2)) < p(neutral(S2, S1))
        Always holds. This constraint can be encoded by the following loss:
            ReLU[p(neutral(S1, S2)) - p(neutral(S2, S1))]

        :return: (tf.Tensor, Set[tf.Variable]) pair containing the adversarial loss
            and the adversarially trainable variables.
        """
        # S1 - [batch_size, time_steps, embedding_size] sentence embedding.
        sequence1, sequence1_length = self._get_sequence(name='rule8_sequence1')
        # S2 - [batch_size, time_steps, embedding_size] sentence embedding.
        sequence2, sequence2_length = self._get_sequence(name='rule8_sequence2')

        # Probability that S1 contradicts S2
        probability_s1_neutral_s2 = self._probability(sequence1, sequence1_length, sequence2, sequence2_length, self.neutral_idx)
        # Probability that S2 contradicts S1
        probability_s2_neutral_s1 = self._probability(sequence2, sequence2_length, sequence1, sequence1_length, self.neutral_idx)

        body_score = probability_s1_neutral_s2
        head_score = probability_s2_neutral_s1

        loss = tf.nn.relu(body_score - head_score)
        return loss, [sequence1, sequence2], [sequence1_length, sequence2_length]
