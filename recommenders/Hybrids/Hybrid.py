import numpy as np
from scipy.sparse import hstack

from recommenders.CBF import ItemCBFKNNRecommender
from recommenders.CF import ItemCFKNNRecommender, UserCFKNNRecommender
from recommenders.GraphBased import RP3betaRecommender
from recommenders.Hybrids import UserCBFKNNTopPop
from recommenders.MF import ALS
from recommenders.SLIM_BPR.Cython import SLIM_BPR_Cython
from recommenders.SLIM_ElasticNet import SLIM_ElasticNet


class Hybrid(object):

    def __init__(self, als_weight=0.7952, elastic_weight=1.464, item_cbf_weight=5.977, item_cf_weight=4.636,
                 rp3_weight=6.297, slim_bpr_weight=0.04734, user_cf_weight=0.07668):

        self.urm_train = None

        self.als_weight = als_weight
        self.elastic_weight = elastic_weight
        self.item_cbf_weight = item_cbf_weight
        self.item_cf_weight = item_cf_weight
        self.rp3_weight = rp3_weight
        self.slim_bpr_weight = slim_bpr_weight
        self.user_cf_weight = user_cf_weight

        self.als_recommender = ALS.ALSRecommender()
        self.elastic_recommender = SLIM_ElasticNet.SLIMElasticNetRecommender()
        self.item_cbf_recommender = ItemCBFKNNRecommender.ItemCBFKNNRecommender()
        self.item_cf_recommender = ItemCFKNNRecommender.ItemCFKNNRecommender()
        self.rp3_recommender = RP3betaRecommender.RP3betaRecommender()
        self.slim_bpr_recommender = SLIM_BPR_Cython.SLIM_BPR_Cython()
        self.user_cf_recommender = UserCFKNNRecommender.UserCFKNNRecommender()

        self.fallback_with_hstack_recommender = UserCBFKNNTopPop.UserCBFKNNTopPop()

    def fit(self, urm_train, icm_all, ucm_all, save_matrix=True, load_matrix=False):

        self.urm_train = urm_train

        self.als_recommender.fit(urm_train, save_matrix=save_matrix, load_matrix=load_matrix)
        self.elastic_recommender.fit(urm_train, save_matrix=save_matrix, load_matrix=load_matrix)
        self.item_cbf_recommender.fit(urm_train, icm_all, save_matrix=save_matrix, load_matrix=load_matrix)
        self.item_cf_recommender.fit(urm_train, save_matrix=save_matrix, load_matrix=load_matrix)
        self.rp3_recommender.fit(urm_train, save_matrix=save_matrix, load_matrix=load_matrix)
        self.slim_bpr_recommender.fit(urm_train, save_matrix=save_matrix, load_matrix=load_matrix)
        self.user_cf_recommender.fit(urm_train, save_matrix=save_matrix, load_matrix=load_matrix)

        self.fallback_with_hstack_recommender.fit(urm_train, ucm_all, save_matrix=save_matrix, load_matrix=load_matrix)
        # self.fallback_with_hstack_recommender.fit(urm_train, hstack((self.urm_train, ucm_all)),
        #                                          save_matrix=save_matrix, load_matrix=load_matrix)

    def compute_score(self, user_id):

        item_weights_1 = self.als_recommender.compute_score(user_id)
        item_weights_2 = self.elastic_recommender.compute_score(user_id)
        item_weights_3 = self.item_cbf_recommender.compute_score(user_id)
        item_weights_4 = self.item_cf_recommender.compute_score(user_id)
        item_weights_5 = self.rp3_recommender.compute_score(user_id)
        item_weights_6 = self.slim_bpr_recommender.compute_score(user_id)
        item_weights_7 = self.user_cf_recommender.compute_score(user_id)

        item_weights = item_weights_1 * self.als_weight
        item_weights += item_weights_2 * self.elastic_weight
        item_weights += item_weights_3 * self.item_cbf_weight
        item_weights += item_weights_4 * self.item_cf_weight
        item_weights += item_weights_5 * self.rp3_weight
        item_weights += item_weights_6 * self.slim_bpr_weight
        item_weights += item_weights_7 * self.user_cf_weight

        return item_weights

    def recommend(self, user_id, at=10, exclude_seen=True):

        scores = self.compute_score(user_id)

        if scores.sum() == 0.0:

            return self.fallback_with_hstack_recommender.recommend(user_id, at)

        if exclude_seen:
            scores = self.filter_seen(user_id, scores)

        ranking = scores.argsort()[::-1]

        return ranking[:at]

    def filter_seen(self, user_id, scores):

        start_pos = self.urm_train.indptr[user_id]
        end_pos = self.urm_train.indptr[user_id + 1]

        user_profile = self.urm_train.indices[start_pos:end_pos]

        scores[user_profile] = -np.inf

        return scores
