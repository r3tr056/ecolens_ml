
MIN_GWP, MAX_GWP = 0, 1000
MIN_DALY, MAX_DALY = 0, 1000
MIN_FEP, MAX_FEP = 0, 1000
MIN_LAND_OCC, MAX_LAND_OCC = 0, 1000
MIN_WATER, MAX_WATER = 0, 100

def convert_to_percentage(score, min_score, max_score):
    normalized_score = max(min(score, max_score), min_score)
    percentage = ((normalized_score - min_score) / (max_score - min_score)) * 100
    return percentage
