def ema5_above_9ema_filter(data, weight=18, ema_histories=None):
    """
    Filter #3: 5EMA > 9EMA → 18pts
    """
    ltp = float(data.get('lp', 0) or 0)
    
    if ema_histories is None:
        ema_histories = {}
    
    token = data.get('tk', 'unknown')
    
    # 🔥 BULLETPROOF: Always create full structure
    if token not in ema_histories or not isinstance(ema_histories[token], dict):
        ema_histories[token] = {
            'ema5': {'prices': [], 'ema': 0},
            'ema9': {'prices': [], 'ema': 0}
        }
    
    # SAFE UPDATE
    try:
        ema5_data = ema_histories[token]['ema5']
        ema9_data = ema_histories[token]['ema9']
        
        ema5_data['prices'].append(ltp)
        if len(ema5_data['prices']) > 5:
            ema5_data['prices'].pop(0)
        ema5_data['ema'] = sum(ema5_data['prices']) / len(ema5_data['prices'])
        
        ema9_data['prices'].append(ltp)
        if len(ema9_data['prices']) > 9:
            ema9_data['prices'].pop(0) 
        ema9_data['ema'] = sum(ema9_data['prices']) / len(ema9_data['prices'])
        
        return weight if ema5_data['ema'] > ema9_data['ema'] > 0 else 0
    except:
        return 0  # Safe fallback
