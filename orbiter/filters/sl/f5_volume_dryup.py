def sl_volume_dryup(data):
    """F5: Volume < 20% of 10min avg"""
    try:
        volume = float(data.get('v', 0))
        return volume < 1000  # TEMP: Low volume threshold
    except:
        return False
