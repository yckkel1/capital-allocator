"""
Portfolio Allocation Module
Functions for diversified portfolio allocation
"""


def allocate_diversified(asset_scores: dict, total_amount: float, config) -> dict:
    """Allocate capital across assets proportionally (not winner-take-all)"""
    positive_scores = {s: max(0, score) for s, score in asset_scores.items()}

    if sum(positive_scores.values()) == 0:
        return {s: 0.0 for s in asset_scores.keys()}

    sorted_assets = sorted(positive_scores.items(), key=lambda x: x[1], reverse=True)

    allocations = {}

    if len(sorted_assets) >= 3 and all(score > 0 for _, score in sorted_assets[:3]):
        total_score = sum(score for _, score in sorted_assets)

        weights = [score / total_score for _, score in sorted_assets]

        allocations[sorted_assets[0][0]] = total_amount * min(config.diversify_top_asset_max, max(config.diversify_top_asset_min, weights[0]))
        allocations[sorted_assets[1][0]] = total_amount * min(config.diversify_second_asset_max, max(config.diversify_second_asset_min, weights[1]))
        allocations[sorted_assets[2][0]] = total_amount * min(config.diversify_third_asset_max, max(config.diversify_third_asset_min, weights[2]))

        total_allocated = sum(allocations.values())
        for symbol in allocations:
            allocations[symbol] = allocations[symbol] * (total_amount / total_allocated)

    elif len(sorted_assets) >= 2 and sorted_assets[1][1] > 0:
        allocations[sorted_assets[0][0]] = total_amount * config.two_asset_top
        allocations[sorted_assets[1][0]] = total_amount * config.two_asset_second
        allocations[sorted_assets[2][0]] = 0.0

    else:
        allocations[sorted_assets[0][0]] = total_amount
        for symbol, _ in sorted_assets[1:]:
            allocations[symbol] = 0.0

    return allocations
