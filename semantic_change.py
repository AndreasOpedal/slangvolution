"""
Code for semantic change score calculation.
Inludes:
- various clustering methods (KMEANS, GMM, DBSCAN)
- various ensemble Average Pairwise Distance (APD) metrics
"""
# General
import pickle
from collections import Counter
import numpy as np
import pandas as pd
import regex as re
import os
from tqdm import tqdm
# Sklearn
from sklearn.cluster import KMeans, DBSCAN
from sklearn.mixture import GaussianMixture
from sklearn.metrics import silhouette_score
from sklearn.metrics.pairwise import cosine_similarity
# Scipy
from scipy.stats import entropy
from scipy.spatial.distance import jensenshannon, canberra
# Internal imports
from utils import apply_PCA, apply_UMAP
import config

#--------------------- APD, Distance Computation ---------------------#

def compute_average_pairwise_difference(period1_reps, period2_reps, dist="euclidian"):
    '''
    Compute the APD in three modes: euclidian distance, cosine similarity or a combined metric taken by scaling both
    metrics to [0,1] and averaging
    '''
    APD = []
    if dist=="euclidian":
        for x1 in period1_reps:
            for x2 in period2_reps:
                APD.append(np.linalg.norm(x2-x1))
        APD = np.mean(APD)
    elif dist=="cosine":
        APD = cosine_similarity(period1_reps, period2_reps)
        APD = 1 - np.mean(APD)
    elif dist=="manhattan":
        for x1 in period1_reps:
            for x2 in period2_reps:
                APD.append(np.linalg.norm(x2-x1, ord=1))
        APD = np.mean(APD)
    elif dist=="canberra":
        for x1 in period1_reps:
            for x2 in period2_reps:
                APD.append(canberra(x1, x2))
        APD = np.mean(APD)
    elif dist=="combined2":
        APD1 = []
        for x1 in period1_reps:
            for x2 in period2_reps:
                APD1.append(np.linalg.norm(x2-x1) / np.sqrt(np.linalg.norm(x1)**2 + np.linalg.norm(x2)**2))
        APD1 = np.mean(APD1)
        APD2 = cosine_similarity(period1_reps, period2_reps)
        APD2 = 0.5*(1 - np.mean(APD2))
        APD = 0.5*(APD1+APD2)
    elif dist=="combined3a":
        APD1 = []
        APD3 = []
        for x1 in period1_reps:
            for x2 in period2_reps:
                APD1.append(np.linalg.norm(x2 - x1) / np.sqrt(np.linalg.norm(x1) ** 2 + np.linalg.norm(x2) ** 2))
                APD3.append(np.linalg.norm(x2 - x1, ord=1) / (np.linalg.norm(x1, ord=1) + np.linalg.norm(x2, ord=1)))
        APD1 = np.mean(APD1)
        APD3 = np.mean(APD3)
        APD2 = cosine_similarity(period1_reps, period2_reps)
        APD2 = 0.5 * (1 - np.mean(APD2))
        APD = (1/3) * (APD1 + APD2 + APD3)
    elif dist=="combined3b":
        APD1 = []
        APD3 = []
        for x1 in period1_reps:
            for x2 in period2_reps:
                APD1.append(np.linalg.norm(x2 - x1) / np.sqrt(np.linalg.norm(x1) ** 2 + np.linalg.norm(x2) ** 2))
                APD3.append(canberra(x1, x2) / 768)
        APD1 = np.mean(APD1)
        APD3 = np.mean(APD3)
        APD2 = cosine_similarity(period1_reps, period2_reps)
        APD2 = 0.5 * (1 - np.mean(APD2))
        APD = (1/3) * (APD1 + APD2 + APD3)
    elif dist=="combined4":
        APD1 = []
        APD3 = []
        APD4 = []
        for x1 in period1_reps:
            for x2 in period2_reps:
                APD1.append(np.linalg.norm(x2 - x1) / np.sqrt(np.linalg.norm(x1) ** 2 + np.linalg.norm(x2) ** 2))
                APD3.append(np.linalg.norm(x2 - x1, ord=1) / (np.linalg.norm(x1, ord=1) + np.linalg.norm(x2, ord=1)))
                APD4.append(canberra(x1, x2) / 768)
        APD1 = np.mean(APD1)
        APD3 = np.mean(APD3)
        APD4 = np.mean(APD4)
        APD2 = cosine_similarity(period1_reps, period2_reps)
        APD2 = 0.5 * (1 - np.mean(APD2))
        APD = (1/4) * (APD1 + APD2 + APD3 + APD4)
    return APD

def compute_entropy_difference(period1_probs, period2_probs):
    return abs(entropy(period2_probs) - entropy(period1_probs))

def compute_JSD(period1_probs, period2_probs):
    return jensenshannon(period1_probs, period2_probs) ** 2

def normalize_vectors(X):
    res = []
    for x in X:
        res.append(x/np.linalg.norm(x))
    return res

def get_APD_semantic_change_scores(corpus1_reps, corpus2_reps, targets, do_pca=True, do_umap=False):
    results = []
    for target in tqdm(targets):
        scores = {}
        scores["word"] = target
        X1 = [elem.detach().numpy() for elem in corpus1_reps[target]]
        X2 = [elem.detach().numpy() for elem in corpus2_reps[target]]
        X = X1 + X2
        scores["APD Euclidian"] = compute_average_pairwise_difference(X1, X2)
        scores["APD Cosine"] = compute_average_pairwise_difference(X1, X2, dist="cosine")
        scores["APD Combined"] = compute_average_pairwise_difference(X1, X2, dist="combined")
        # scores["APD Manhattan"] = compute_average_pairwise_difference(X1, X2, dist="manhattan")
        # scores["APD Canberra"] = compute_average_pairwise_difference(X1, X2, dist="canberra")
        # scores["APD Combined Manhattan"] = compute_average_pairwise_difference(X1, X2, dist="combined3a")
        # scores["APD Combined Canberra"] = compute_average_pairwise_difference(X1, X2, dist="combined3b")
        #scores["APD Combined All 4"] = compute_average_pairwise_difference(X1, X2, dist="combined4")
        for dim in [2, 5, 10, 20, 50, 100]:
            if do_pca:
                X_reduced = apply_PCA(X, dim)
                scores[f"APD Manhattan pca{dim}"] = compute_average_pairwise_difference(X_reduced[:len(X1)],
                                                                                        X_reduced[len(X1):],
                                                                                        dist="manhattan")
                # scores[f"APD Canberra pca{dim}"] = compute_average_pairwise_difference(X_reduced[:len(X1)],
                #                                                                      X_reduced[len(X1):],
                #                                                                      dist="canberra")
                # scores[f"APD Combined Manhattan pca{dim}"] = compute_average_pairwise_difference(X_reduced[:len(X1)],
                #                                                                        X_reduced[len(X1):],
                #                                                                        dist="combined3a")
                # scores[f"APD Combined Canberra pca{dim}"] = compute_average_pairwise_difference(X_reduced[:len(X1)],
                #                                                                                   X_reduced[len(X1):],
                #                                                                                   dist="combined3b")
                #scores[f"APD Combined All 4 pca{dim}"] = compute_average_pairwise_difference(X_reduced[:len(X1)],
                #                                                                                  X_reduced[len(X1):],
                #                                                                                  dist="combined4")
            if do_umap:
                X_reduced = apply_UMAP(X, dim)
                scores[f"APD Manhattan umap{dim}"] = compute_average_pairwise_difference(X_reduced[:len(X1)],
                                                                                        X_reduced[len(X1):],
                                                                                        dist="manhattan")
                scores[f"APD Canberra umap{dim}"] = compute_average_pairwise_difference(X_reduced[:len(X1)],
                                                                                       X_reduced[len(X1):],
                                                                                       dist="canberra")
                scores[f"APD Combined Manhattan umap{dim}"] = compute_average_pairwise_difference(X_reduced[:len(X1)],
                                                                                                 X_reduced[len(X1):],
                                                                                                 dist="combined3a")
                scores[f"APD Combined Canberra umap{dim}"] = compute_average_pairwise_difference(X_reduced[:len(X1)],
                                                                                                X_reduced[len(X1):],
                                                                                                dist="combined3b")
                scores[f"APD Combined All 4 umap{dim}"] = compute_average_pairwise_difference(X_reduced[:len(X1)],
                                                                                             X_reduced[len(X1):],
                                                                                             dist="combined4")
        results.append(scores)
    return results

def get_APD_scores(corpus1_reps, corpus2_reps, targets, dim=100, min_tweets=150):
    """
    Compute APD between two corpora
    """
    scores = {
        "word" : [],
        #"Euclidian_APD" : [],
        #"cosine_APD" : [],
        "combined_APD": [],
    }
    for target in tqdm(targets):
        if target not in corpus1_reps or target not in corpus2_reps:
            continue
        X1 = [elem.detach().numpy() for elem in corpus1_reps[target]]
        X2 = [elem.detach().numpy() for elem in corpus2_reps[target]]
        X = X1 + X2
        X, X1, X2 = np.array(X), np.array(X1), np.array(X2)
        if X1.shape[0] <= min_tweets or X2.shape[0] <= min_tweets:
            continue
        scores["word"].append(target)
        X_reduced = apply_PCA(X, dim)
        #scores["Euclidian_APD"].append(
        #    compute_average_pairwise_difference(X_reduced[:len(X1)],X_reduced[len(X1):]))

        #scores["cosine_APD"].append(compute_average_pairwise_difference(X_reduced[:len(X1)],
        #                                                                X_reduced[len(X1):],
        #                                                                dist = "cosine"))

        scores["combined_APD"].append(compute_average_pairwise_difference(X_reduced[:len(X1)],
                                                                          X_reduced[len(X1):],
                                                                          dist="combined2"))
    return scores

def inner_APD_scores(corpus_reps, targets, dim=100, min_tweets=50):
    """
    Compute APD within the same corpus
    """
    scores = {
        "word" : [],
        "Euclidian_APD" : [],
        "cosine_APD" : [],
        "combined_APD": [],
    }
    for target in tqdm(targets):
        if target not in corpus_reps:
            continue
        X1 = [elem.detach().numpy() for elem in corpus_reps[target]]
        X1 = np.array(X1)
        n = X1.shape[0]
        if (n/2) <= min_tweets:
            continue
        idxs = np.random.choice(n, int(n/2))
        other_idxs = [k for k in range(n) if k not in idxs]

        X_reduced = apply_PCA(X1, dim)

        scores["word"].append(target)
        scores["Euclidian_APD"].append(
            compute_average_pairwise_difference(X_reduced[idxs],X_reduced[other_idxs]))

        scores["cosine_APD"].append(compute_average_pairwise_difference(X_reduced[idxs],
                                                                        X_reduced[other_idxs],
                                                                        dist = "cosine"))

        scores["combined_APD"].append(compute_average_pairwise_difference(X_reduced[idxs],
                                                                          X_reduced[other_idxs],
                                                                          dist="combined2"))
    return scores

#-------------------------- Clustering ---------------------------#

def get_kmeans_cluster_labels(data, Ks=[2, 3, 4, 5]):
    best_score = 0.1
    best_K = 1
    cluster_labels = np.zeros(len(data))
    for K in Ks:
        clusterer = KMeans(n_clusters=K)
        curr_cluster_labels = clusterer.fit_predict(data)
        curr_score =  silhouette_score(data, curr_cluster_labels)
        if curr_score > best_score:
            best_score = curr_score
            best_K = K
            cluster_labels = curr_cluster_labels
    return cluster_labels, best_K

def get_clusterer(model,K,seed):
    if model == "kmeans":
        clusterer = KMeans(n_clusters=K, random_state=seed)
    elif model == "gmm":
        clusterer = GaussianMixture(n_components=K, random_state=seed)
    else:
        raise NameError("Please set model=kmeans or gmm")
    return clusterer

def get_clusters_by_silhouette(data, model="kmeans", k_min=2, k_max=10, seeds=range(0,10), threshold=0.1):
    '''
    Get clusters by picking the configutation with the best silhouette score,
    among an array of different seeds and K values
    '''
    Ks = range(k_min,k_max+1)
    silhouette_scores, best_seeds = {}, {}
    for K in Ks:
        silhouette_scores_K = {}
        for seed in seeds:
            clusterer = get_clusterer(model,K,seed)
            cluster_labels = clusterer.fit_predict(data)
            silhouette_scores_K[seed] = silhouette_score(data, cluster_labels)
        silhouette_scores[K] = max(silhouette_scores_K.values())
        best_seeds[K] = max(silhouette_scores_K, key=silhouette_scores_K.get)
    best_silhouette = max(silhouette_scores.values())
    if best_silhouette < threshold:
        #if best silhouette lower (i.e. worse) than threshold, return only one cluster
        return np.zeros(len(data)), 1, 0
    else:
        best_K = max(silhouette_scores, key=silhouette_scores.get)
        seed = best_seeds[best_K]
        clusterer = get_clusterer(model,K,seed)
        cluster_labels = clusterer.fit_predict(data)
        return cluster_labels, best_K, best_silhouette

def fit_categoricals_from_clusters(cluster_assignments, period1_length, period2_length):
    labels = set(cluster_assignments)

    period1 = cluster_assignments[:period1_length]
    period1_counts = list(Counter(period1).items())
    [period1_counts.append((num, 0)) for num in labels if num not in Counter(period1).keys()]
    period1_counts = sorted(period1_counts)
    probs1 = [count / period1_length for _, count in period1_counts]

    period2 = cluster_assignments[period1_length:]
    period2_counts = list(Counter(period2).items())
    [period2_counts.append((num, 0)) for num in labels if num not in Counter(period2).keys()]
    period2_counts = sorted(period2_counts)
    probs2 = [count / period2_length for _, count in period2_counts]

    return probs1, probs2

def cluster_with_dbscan(data, epsilon, min_samples):
    db = DBSCAN(eps=epsilon, min_samples=min_samples).fit(data)
    core_samples_mask = np.zeros_like(db.labels_, dtype=bool)
    core_samples_mask[db.core_sample_indices_] = True
    labels = db.labels_

    num_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    percent_noise = list(labels).count(-1)/len(labels)

    if percent_noise == 1: silhouette = np.nan
    else:  silhouette = silhouette_score(data, labels)

    return silhouette, num_clusters, percent_noise

def grid_search_dbscan(data, candidate_epsilons, candidate_min_samples):
    results = {
        "epsilon" : [],
        "min_samples" : [],
        "silhouette" : [],
        "num_clusters" : [],
        "percent_noise" : [],
    }
    def update_results(eps, min_samples, silhouette, num_clusters, percent_noise):
        results["epsilon"].append(eps)
        results["min_samples"].append(min_samples)
        results["silhouette"].append(silhouette)
        results["num_clusters"].append(num_clusters)
        results["percent_noise"].append(percent_noise)

    for eps in candidate_epsilons:
        for min_samples in candidate_min_samples:
            silhouette, num_clusters, percent_noise = cluster_with_dbscan(data, eps, min_samples)
            update_results(eps,min_samples, silhouette, num_clusters, percent_noise)

    res = pd.DataFrame(results)
    res["data_dim"] = data.shape[1]
    return res

def choose_kmeans_k_with_elbow(data, k_min=2, k_max=10, max_iter=200, seed=111, algorithm='auto'):
    from kneed import KneeLocator
    SSD_scores = []
    for k in range(k_min, k_max+1):
            clusterer = KMeans(n_clusters=k,
                    max_iter=max_iter,
                    random_state=seed,
                    algorithm=algorithm)
            clusterer.fit(data)
            SSD_scores.append(clusterer.inertia_)
    kn = KneeLocator(range(k_min, k_max+1), SSD_scores,
                     curve='convex', direction='decreasing')
    elbows = kn.all_elbows
    if len(elbows) == 0:
        return k_max
    else:
        return min(elbows)

def choose_gmm_params_with_bic(data, k_min=2, k_max=10, seed=111, verbose=False):
    bic_scores = []
    lowest_bic = np.infty
    Ks = range(k_min, k_max+1)
    covariance_types = ['spherical', 'tied', 'diag', 'full']
    for k in Ks:
        for cv in covariance_types:
            clusterer = GaussianMixture(n_components=k, covariance_type=cv,
                                        reg_covar = 1e-4, random_state=seed)
            clusterer.fit(data)
            bic_scores.append(clusterer.bic(np.array(data)))
            if bic_scores[-1] < lowest_bic:
                lowest_bic = bic_scores[-1]
                best_K = k
                best_cv = cv
    if verbose:
        return best_K, best_cv, bic_scores
    else:
        return best_K, best_cv

def get_clusters_by_score(data, model="kmeans", k_min=2, k_max=10, seeds=range(101,111)):
    '''
    Select the best clustering by the elbow method using sum of squared distances for the kmeans case,
    and using the Bayesian Information Criterion for the GMM case
    '''
    if model == "kmeans":
        best_silhouette = 0
        for seed in seeds:
            K = choose_kmeans_k_with_elbow(data, k_min, k_max, seed = seed)
            clusterer = KMeans(n_clusters = K, random_state = seed)
            cluster_labels = clusterer.fit_predict(data)
            silhouette = silhouette_score(data, cluster_labels)
            if silhouette > best_silhouette:
                best_silhouette = silhouette
                best_K = K
                best_cluster_labels = cluster_labels
    elif model == "gmm":
        best_K, best_cv = choose_gmm_params_with_bic(data, k_min, k_max, seed = seeds[0])
        clusterer = GaussianMixture(n_components = best_K, covariance_type = best_cv,
                                    reg_covar = 1e-4, random_state = seeds[0])
        best_cluster_labels = clusterer.fit_predict(data)
    return best_cluster_labels, best_K

def get_cluster_semantic_change_scores(corpus1_reps,
                                       corpus2_reps,
                                       targets,
                                       method="pca",
                                       silhouette=True,
                                       normalize=False):
    results = []
    for target in tqdm(targets):
        scores = {}
        scores["word"] = target
        X1 = [elem.detach().numpy() for elem in corpus1_reps[target]]
        X2 = [elem.detach().numpy() for elem in corpus2_reps[target]]
        X = X1 + X2
        if normalize:
            X = normalize_vectors(X)
        if silhouette:
            cluster_labels, _, _ = get_clusters_by_silhouette(X, model="kmeans", k_min=2, k_max=10)
        else:
            cluster_labels, _ = get_clusters_by_score(X, model="kmeans", k_min=2, k_max=10)
        probs1, probs2 = fit_categoricals_from_clusters(cluster_labels, len(X1), len(X2))
        scores["K-Means ED"] = compute_entropy_difference(probs1, probs2)
        scores["K-Means JSD"] = compute_JSD(probs1, probs2)
        if silhouette:
            cluster_labels, _, _ = get_clusters_by_silhouette(X, model="gmm", k_min=2, k_max=10)
        else:
            cluster_labels, _ = get_clusters_by_score(X, model="gmm", k_min=2, k_max=10)
        probs1, probs2 = fit_categoricals_from_clusters(cluster_labels, len(X1), len(X2))
        scores["GMM ED"] = compute_entropy_difference(probs1, probs2)
        scores["GMM JSD"] = compute_JSD(probs1, probs2)

        for dim in [2, 5, 10, 20, 50]:
            if normalize:
                X1 = [elem.detach().numpy() for elem in corpus1_reps[target]]
                X2 = [elem.detach().numpy() for elem in corpus2_reps[target]]
                X = X1 + X2

            if method == "pca": X_reduced = apply_PCA(X, dim)
            elif method == "umap": X_reduced = apply_UMAP(X, dim)

            if normalize:
                X_reduced = normalize_vectors(X_reduced)

            if silhouette:
                cluster_labels, _, _ = get_clusters_by_silhouette(X_reduced, model="kmeans", k_min=2, k_max=10)
            else:
                cluster_labels, _ = get_clusters_by_score(X_reduced, model="kmeans", k_min=2, k_max=10)
            probs1, probs2 = fit_categoricals_from_clusters(cluster_labels, len(X1), len(X2))
            scores[f"K-Means {method}{dim} ED"] = compute_entropy_difference(probs1, probs2)
            scores[f"K-Means {method}{dim} JSD"] = compute_JSD(probs1, probs2)

            if silhouette:
                cluster_labels, _, _ = get_clusters_by_silhouette(X_reduced, model="gmm", k_min=2, k_max=10)
            else:
                cluster_labels, _ = get_clusters_by_score(X_reduced, model="gmm", k_min=2, k_max=10)
            probs1, probs2 = fit_categoricals_from_clusters(cluster_labels, len(X1), len(X2))
            scores[f"GMM {method}{dim} ED"] = compute_entropy_difference(probs1, probs2)
            scores[f"GMM {method}{dim} JSD"] = compute_JSD(probs1, probs2)

        results.append(scores)
    return results

#------------------------- Data Loading --------------------------#

def load_corpus_reps(path):
    with open(path, 'rb') as handle:
        corpus_reps = pickle.load(handle)
    return corpus_reps

def get_data_for_tweets(type='slang', path="data/"):

    old_reps_name = config.REPR_FILE_NAMES[type]['old']
    old_reps = load_corpus_reps(path + old_reps_name)

    new_reps_name = config.REPR_FILE_NAMES[type]['new']
    new_reps = load_corpus_reps(path + new_reps_name)

    return old_reps, new_reps

def get_true_semeval():
    from scipy.stats import spearmanr
    true_scores = open(config.SEMEVAL_PATH).read().strip()
    true_scores = {re.split("\t", target)[0]: float(re.split("\t", target)[1]) for target in
                   re.split("\n", true_scores)}
    truth = list(true_scores.values())

    # def print_results(res):
    #     for key in res[0].keys():
    #         if key != "word":
    #             corr, p = spearmanr(truth, [word[key] for word in results])
    #             print(f"{key}-----\t correlation: ", round(corr, 3), " \t p-value: ", round(p, 3))
    #
    # print("RESULTS APD ALL LAYERS")
    # print_results(results)

def get_data_for_semeval(reps="sum", reps_abs_path="../"):
    with open(config.SEMEVAL_TARGETS_PATH) as f:
        target_words = f.read().strip()
    target_words = [word for word in re.split("\n", target_words)]

    corpus1_reps_path = 'corpus1_'+reps+'_layer_reps.pickle'
    corpus1_reps = load_corpus_reps(os.path.join(reps_abs_path,corpus1_reps_path))
    corpus2_reps_path = 'corpus2_'+reps+'_layer_reps.pickle'
    corpus2_reps = load_corpus_reps(os.path.join(reps_abs_path,corpus2_reps_path))

    return target_words, corpus1_reps, corpus2_reps
