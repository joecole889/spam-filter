==========
 Tutorial
==========

This python 2.7 program demonstrates a simple SVM based spam filter trained
using data downloaded from the SpamAssassin public corpus
(https://spamassassin.apache.org/publiccorpus/). Feature vectors are
assembled for each email according to the presence or absence of words from a
given dictionary. The dictionary is built up based on the frequency of
occurance of words in the email training set or an external list can be
provided. Additionally, the words are regularized by removing non-alphabetic
characters and stemmed using the Porter Stemmer algorithm.
