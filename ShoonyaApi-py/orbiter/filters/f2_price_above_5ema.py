def price_above_5ema_filter(data, weight=20, ema_histories=None):
    """
    Filter #2: LTP > 5EMA → 20pts
    """
    ltp = float(data.get('lp', 0) or 0)
    
    if ema_histories is None:
        ema_histories = {}
    
    token = data.get('tk', 'unknown')
    
    # 🔥 BULLETPROOF structure
    if token not in ema_histories or not isinstance(ema_histories[token], dict):
        ema_histories[token] = {'ema5': {'prices': [], 'ema': 0}}
    
    try:
        ema5_data = ema_histories[token]['ema5']
        ema5_data['prices'].append(ltp)
        if len(ema5_data['prices']) > 5:
            ema5_data['prices'].pop(0)
        ema5_data['ema'] = sum(ema5_data['prices']) / len(ema5_data['prices'])
        
        return weight if ltp > ema5_data['ema'] > 0 else 0
    except:
        return 0
