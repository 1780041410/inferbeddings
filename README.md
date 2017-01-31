# Inferbeddings [![wercker status](https://app.wercker.com/status/47cfd21ce8315fb361ac5b4247ce280a/s/master "wercker status")](https://app.wercker.com/project/byKey/47cfd21ce8315fb361ac5b4247ce280a)

Rule Injection in Knowledge Graph Embeddings via Adversarial Training.


Usage:

```
$ python3 setup.py install --user
running install
running bdist_egg
running egg_info
[...]
$ ./bin/adv-cli.py -h
usage: Rule Injection via Adversarial Training [-h] --train TRAIN [--valid VALID] [--test TEST] [--lr LR] [--nb-batches NB_BATCHES] [--nb-epochs NB_EPOCHS] [--model MODEL] [--similarity SIMILARITY]
                                               [--objective OBJECTIVE] [--margin MARGIN] [--embedding-size EMBEDDING_SIZE] [--predicate-embedding-size PREDICATE_EMBEDDING_SIZE] [--auc] [--seed SEED]
                                               [--clauses CLAUSES] [--adv-lr ADV_LR] [--adv-nb-epochs ADV_NB_EPOCHS] [--adv-weight ADV_WEIGHT] [--adv-margin ADV_MARGIN] [--adv-restart] [--save SAVE]

optional arguments:
  -h, --help                                                                                  show this help message and exit
  --train TRAIN, -t TRAIN
  --valid VALID, -v VALID
  --test TEST, -T TEST
  --lr LR, -l LR
  --nb-batches NB_BATCHES, -b NB_BATCHES
  --nb-epochs NB_EPOCHS, -e NB_EPOCHS
  --model MODEL, -m MODEL                                                                     Model
  --similarity SIMILARITY, -s SIMILARITY                                                      Similarity function
  --objective OBJECTIVE, -o OBJECTIVE                                                         Loss function
  --margin MARGIN, -M MARGIN                                                                  Margin
  --embedding-size EMBEDDING_SIZE, --entity-embedding-size EMBEDDING_SIZE, -k EMBEDDING_SIZE  Entity embedding size
  --predicate-embedding-size PREDICATE_EMBEDDING_SIZE, -p PREDICATE_EMBEDDING_SIZE            Predicate embedding size
  --auc, -a                                                                                   Measure the predictive accuracy using AUC-PR and AUC-ROC
  --seed SEED, -S SEED                                                                        Seed for the PRNG
  --clauses CLAUSES, -c CLAUSES                                                               File containing background knowledge expressed as Horn clauses
  --adv-lr ADV_LR, -L ADV_LR                                                                  Adversary learning rate
  --adv-nb-epochs ADV_NB_EPOCHS, -E ADV_NB_EPOCHS                                             Adversary number of training epochs
  --adv-weight ADV_WEIGHT, -W ADV_WEIGHT                                                      Adversary weight
  --adv-margin ADV_MARGIN                                                                     Adversary margin
  --adv-restart, -R                                                                           Restart the optimization process for identifying the violators
  --save SAVE                                                                                 Path for saving the serialized model

```

If the parameter `--adv-lr` is not specified, the method does not perform any adversarial training -- i.e. it simply trains the Knowledge Graph Embedding models by minimizing a standard pairwise loss in, such as the margin-based ranking loss in [1].

Example - Embedding the WN18 Knowledge Graph:

```
$ ./bin/adv-cli.py --train data/wn18/wordnet-mlj12-train.txt --valid data/wn18/wordnet-mlj12-valid.txt --test data/wn18/wordnet-mlj12-test.txt --lr 0.1 --model ComplEx --similarity dot --margin 5 --embedding-size 100 --nb-epochs 100
INFO:adv-cli.py:#Training Triples: 141442, #Validation Triples: 5000, #Test Triples: 5000
INFO:adv-cli.py:#Entities: 40943	#Predicates: 18
INFO:adv-cli.py:Samples: 141442, no. batches: 10 -> batch size: 14145
INFO:adv-cli.py:Epoch: 1/1	Loss: 9.7014 ± 0.3431
INFO:adv-cli.py:Epoch: 1/1	Fact Loss: 1372195.3594
INFO:adv-cli.py:Epoch: 2/1	Loss: 6.1147 ± 1.5339
INFO:adv-cli.py:Epoch: 2/1	Fact Loss: 864890.9531
INFO:adv-cli.py:Epoch: 3/1	Loss: 2.2779 ± 0.6385
INFO:adv-cli.py:Epoch: 3/1	Fact Loss: 322190.9766
INFO:adv-cli.py:Epoch: 4/1	Loss: 0.8755 ± 0.1999
INFO:adv-cli.py:Epoch: 4/1	Fact Loss: 123841.3086
INFO:adv-cli.py:Epoch: 5/1	Loss: 0.4603 ± 0.0699
INFO:adv-cli.py:Epoch: 5/1	Fact Loss: 65104.3921
INFO:adv-cli.py:Epoch: 6/1	Loss: 0.2811 ± 0.0408
INFO:adv-cli.py:Epoch: 6/1	Fact Loss: 39766.0500
[..]
INFO:adv-cli.py:Epoch: 98/1	Loss: 0.0101 ± 0.0014
INFO:adv-cli.py:Epoch: 98/1	Fact Loss: 1433.6215
INFO:adv-cli.py:Epoch: 99/1	Loss: 0.0094 ± 0.0013
INFO:adv-cli.py:Epoch: 99/1	Fact Loss: 1330.8106
INFO:adv-cli.py:Epoch: 100/1	Loss: 0.0098 ± 0.0013
INFO:adv-cli.py:Epoch: 100/1	Fact Loss: 1379.2251
[..]
INFO:inferbeddings.evaluation.base:### MICRO (test filtered):
INFO:inferbeddings.evaluation.base:	-- left   >> mean: 542.212, median: 1.0, mrr: 0.919, hits@10: 94.62%
INFO:inferbeddings.evaluation.base:	-- right  >> mean: 546.9044, median: 1.0, mrr: 0.925, hits@10: 94.56%
INFO:inferbeddings.evaluation.base:	-- global >> mean: 544.5582, median: 1.0, mrr: 0.922, hits@10: 94.59%
```

[1] Bordes, A. et al. - [Translating Embeddings for Modeling Multi-relational Data](https://www.utc.fr/~bordesan/dokuwiki/_media/en/transe_nips13.pdf) - NIPS 2013
