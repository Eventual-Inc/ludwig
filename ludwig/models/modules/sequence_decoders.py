# coding=utf-8
# Copyright (c) 2019 Uber Technologies, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
import logging

import tensorflow.compat.v1 as tf
from tensorflow.keras.layers import Layer, Dense

from ludwig.models.modules.attention_modules import \
    feed_forward_memory_attention
from ludwig.models.modules.initializer_modules import get_initializer
from ludwig.models.modules.recurrent_modules import recurrent_decoder

logger = logging.getLogger(__name__)


class SequenceGeneratorDecoder(Layer):
    def __init__(
            self,
            cell_type='rnn',
            state_size=256,
            embedding_size=64,
            beam_width=1,
            num_layers=1,
            attention_mechanism=None,
            tied_embeddings=None,
            initializer=None,
            regularize=True,
            is_timeseries=False,
            num_classes=0,
            **kwargs
    ):
        super().__init__()


        self.cell_type = cell_type
        self.state_size = state_size
        self.embedding_size = embedding_size
        self.beam_width = beam_width
        self.num_layers = num_layers
        self.attention_mechanism = attention_mechanism
        self.tied_embeddings = tied_embeddings
        self.initializer = initializer
        self.regularize = regularize
        self.is_timeseries = is_timeseries
        self.num_classes = num_classes



    def call(
            self,
            hidden,
            **kwargs
#            output_feature,
#            targets,
#            hidden,
#            hidden_size,
#            regularizer,

    ):

        if len(hidden.shape) != 3 and self.attention_mechanism is not None:
            raise ValueError(
                'Encoder outputs rank is {}, but should be 3 [batch x sequence x hidden] '
                'when attention mechanism is {}. '
                'If you are using a sequential encoder or combiner consider setting reduce_output to None '
                'and flatten to False if those parameters apply.'
                'Also make sure theat reduce_input of {} output feature is None,'.format(
                    len(hidden.shape), self.attention_mechanism,
                    self.output_feature))
        if len(hidden.shape) != 2 and self.attention_mechanism is None:
            raise ValueError(
                'Encoder outputs rank is {}, but should be 2 [batch x hidden] '
                'when attention mechanism is {}. '
                'Consider setting reduce_input of {} output feature to a value different from None.'.format(
                    len(hidden.shape), self.attention_mechanism,
                    self.output_feature))

        tied_embeddings_tensor = None
        # todo tf2  determine how to handle following
        # if self.tied_embeddings is not None:
        #     try:
        #         tied_embeddings_tensor = tf.get_default_graph().get_tensor_by_name(
        #             '{}/embeddings:0'.format(self.tied_embeddings))
        #     except:
        #         raise ValueError(
        #             'An error occurred while obtaining embeddings from the feature {} '
        #             'to use as tied weights in the generator decoder of feature {}. '
        #             '{} does not exists or does not have an embedding weights.v'
        #             'Please check the spelling of the feature name '
        #             'in the tied_embeddings field and '
        #             'be sure its type is not binary, numerical or timeseries.'.format(
        #                 self.tied_embeddings,
        #                 output_feature['name'],
        #                 self.tied_embeddings
        #             )
        #         )


        if self.is_timeseries:
            vocab_size = 1
        else:
            vocab_size = self.num_classes

        if not self.regularize:
            regularizer = None

        predictions_sequence, predictions_sequence_scores, \
        predictions_sequence_length_with_eos, \
        targets_sequence_length_with_eos, eval_logits, train_logits, \
        class_weights, class_biases = recurrent_decoder(
            hidden,
            targets,
            output_feature['max_sequence_length'],
            vocab_size,
            cell_type=self.cell_type,
            state_size=self.state_size,
            embedding_size=self.embedding_size,
            beam_width=self.beam_width,
            num_layers=self.num_layers,
            attention_mechanism=self.attention_mechanism,
            is_timeseries=self.is_timeseries,
            embeddings=tied_embeddings_tensor,
            initializer=self.initializer,
            regularizer=regularizer
        )

        probabilities_target_sequence = tf.nn.softmax(eval_logits)

        return predictions_sequence, predictions_sequence_scores, \
               predictions_sequence_length_with_eos, \
               probabilities_target_sequence, targets_sequence_length_with_eos, \
               eval_logits, train_logits, class_weights, class_biases


class SequenceTaggerDecoder(Layer):
    def __init__(
            self,
            initializer=None,
            use_bias=True,
            kernel_initializer='glorot_uniform',
            bias_initializer='zeros',
            kernel_regularizer=None,
            bias_regularizer=None,
            activity_regularizer=None,
            attention=False,
            num_classes=0,
            is_timeseries=None,
            **kwargs
    ):
        super(SequenceTaggerDecoder, self).__init__()
        self.initializer = initializer
        self.attention = attention

        if is_timeseries:
            units = 1
        else:
            units = num_classes

        self.decoder_layer = Dense(
            units,
            use_bias=use_bias,
            kernel_initializer=kernel_initializer,
            bias_initializer=bias_initializer,
            kernel_regularizer=kernel_regularizer,
            bias_regularizer=bias_regularizer,
            activity_regularizer=activity_regularizer
        )

    def call(
            self,
            inputs,
            training=None,
            mask=None
    ):
        logger.debug('  hidden shape: {0}'.format(inputs.shape))
        if len(inputs.shape) != 3:
            raise ValueError(
                'Decoder inputs rank is {}, but should be 3 [batch x sequence x hidden] '
                'when using a tagger sequential decoder. '
                'Consider setting reduce_output to null / None if a sequential encoder / combiner is used.'.format(
                    len(inputs.shape)))

        # hidden shape [batch_size, sequence_length, hidden_size]
        logits = self.decoder_layer(inputs)

        # TODO tf2 add feed forward attention

        # logits shape [batch_size, sequence_length, vocab_size]
        return logits


