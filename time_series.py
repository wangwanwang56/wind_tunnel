"""
Functions for playing with time-serieses.
"""
from __future__ import print_function, division
import numpy as np
from numpy import concatenate as cc
import stats


def segment_basic(x, t=None):
    """
    Return the numerical indices indicating the segments of non-False x-values.
    :param x: boolean time-series
    :param t: vector containing indices to use if not 0 to len(x)
    :return: starts, ends, which are numpy arrays containing the start and end idxs of
        segments of consecutive Trues (end idxs are according to Python convention, e.g.,
        np.array([False, False, False, True, True, False]) yields (array([3]), array([5]))
    """

    if t is None:
        t = np.arange(len(x), dtype=int)

    starts = t[(np.diff(cc([[False], x]).astype(int)) == 1).nonzero()[0]]
    ends = t[(np.diff(cc([x, [False]]).astype(int)) == -1).nonzero()[0]] + 1

    return starts, ends


def segment_by_threshold(x, threshold, t=None):
    """
    Segment a 1D time-series by identifying when it crossed a threshold, the times it reached its
    peak value during each segment in which it was above the threshold, as well as the values reached
    during those peaks.
    :param x: signal (1D array)
    :param threshold: value that signal must be >= for segment to start
    :param t: optional time indices to return instead of indices from 0 to len(x)
    :return: segments array, each row containing [start, onset, peak, offset, end] and peaks array,
        containing values of signals at peaks
    """

    if t is None:
        t = np.arange(len(x) + 1, dtype=int)

    # get onsets and offsets of signal going above threshold
    onsets, offsets = segment_basic(x > threshold)

    if len(onsets) == 0:
        return np.zeros((0, 5)), np.array([])

    # the last segment's offset is the next segment's start
    starts = np.array([0] + list(offsets)[:-1])
    # the next segment's onset is the last segment's end
    ends = np.array(list(onsets)[1:] + [len(x)])

    # find peak times and peak values
    peak_times = []
    peak_values = []

    for onset, offset in zip(onsets, offsets):
        peak_times.append(onset + np.argmax(x[onset:offset]))
        peak_values.append(np.max(x[onset:offset]))

    peak_times = np.array(peak_times)
    peak_values = np.array(peak_values)

    # transform indices to provided time indices
    starts = t[starts]
    onsets = t[onsets]
    peak_times = t[peak_times]
    offsets = t[offsets]
    ends = t[ends]

    return np.transpose([starts, onsets, peak_times, offsets, ends]), peak_values


def xcov_multi_with_confidence(xs, ys, lag_backward, lag_forward, confidence=0.95, normed=False):
    """
    Calculate cross-covariance between x and y when multiple time-series are available.
        This function is to be used when it is believed that y is created by filtering x
        with a causal linear filter. If that is the case, then as the number of samples
        increases, the result will approach the shape of the original filter.
    :param xs: list of input time-series
    :param ys: list of output time-series
    :param lag_forward: number of lags to look forward (causal (x yields y))
    :param lag_backward: number of lags to look back (acausal (y yields x))
    :param confidence: confidence of confidence interval desired
    :param normed: if True, results will be normalized by geometric mean of x's & y's variances
    :return: cross-covariance, p-value, lower bound, upper bound
    """

    if not np.all([len(x) == len(y) for x, y in zip(xs, ys)]):
        raise ValueError('Arrays within xs and ys must all be of the same size!')

    covs = []
    p_values = []
    lbs = []
    ubs = []

    for lag in range(-lag_backward, lag_forward):
        if lag == 0:
            x_rel = xs
            y_rel = ys
        elif lag < 0:
            x_rel = [x[-lag:] for x in xs if len(x) > -lag]
            y_rel = [y[:lag] for y in ys if len(y) > -lag]
        else:
            # calculate the cross covariance between x and y with a specific lag
            # first get the relevant xs and ys from each time-series
            x_rel = [x[:-lag] for x in xs if len(x) > lag]
            y_rel = [y[lag:] for y in ys if len(y) > lag]

        all_xs = np.concatenate(x_rel)
        all_ys = np.concatenate(y_rel)

        cov, p_value, lb, ub = stats.cov_with_confidence(all_xs, all_ys, confidence)

        covs.append(cov)
        p_values.append(p_value)
        lbs.append(lb)
        ubs.append(ub)

    covs = np.array(covs)
    p_values = np.array(p_values)
    lbs = np.array(lbs)
    ubs = np.array(ubs)

    if normed:
        # normalize by average variance of signals
        var_x = np.cov(np.concatenate(xs), np.concatenate(xs))[0, 0]
        var_y = np.cov(np.concatenate(ys), np.concatenate(ys))[0, 0]
        norm_factor = np.sqrt(var_x * var_y)
        covs /= norm_factor
        lbs /= norm_factor
        ubs /= norm_factor

    return covs, p_values, lbs, ubs