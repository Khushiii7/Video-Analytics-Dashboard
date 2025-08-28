# This is a placeholder for a real machine learning model.
# It simulates predicting revenue based on watch time and views on specific seconds.

def predict_revenue(video_data):
    """
    A simple, rule-based function to simulate an ML model prediction.
    
    Args:
        video_data (dict): A dictionary containing video metrics.
                           Expected keys: 'total_watch_time', 'heatmap'.

    Returns:
        float: A predicted revenue figure.
    """
    if not video_data:
        return 0.0

    # Base value per second of watch time
    total_watch_time = video_data.get('total_watch_time', 0)
    base_revenue = total_watch_time * 0.015  # e.g., 1.5 cents per second

    # Bonus for engagement on key moments (heatmap)
    heatmap = video_data.get('heatmap', {})
    bonus_revenue = 0
    if heatmap:
        # Give a bonus for every view recorded in the first 10 seconds
        for i in range(10):
            views_at_second = heatmap.get(str(i), 0)
            bonus_revenue += views_at_second * 0.05 # e.g., 5 cents bonus

    predicted_value = base_revenue + bonus_revenue
    
    # Return a nicely formatted float
    return round(predicted_value, 2)