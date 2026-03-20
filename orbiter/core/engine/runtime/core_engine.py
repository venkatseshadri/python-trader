# orbiter/core/engine/core_engine.py

import logging
from orbiter.core.engine.rule.rule_manager import RuleManager
from orbiter.core.engine.action.action_manager import ActionManager
from orbiter.core.engine.action.executor import ActionExecutor
from orbiter.core.engine.action.registration_manager import RegistrationManager
from orbiter.utils.constants_manager import ConstantsManager
from orbiter.core.engine.session.session_manager import SessionManager # Import SessionManager
from orbiter.utils.utils import safe_float

logger = logging.getLogger("ORBITER")

class Engine:
    """
    The trading machine. 
    It wires Fact Providers to Rule Evaluation and then to Action Registries.
    """
    def __init__(self, state, session_manager: SessionManager, action_manager: ActionManager):
        logger.debug(f"[{self.__class__.__name__}.__init__] - Initializing Engine.")
        self.state = state
        self.session_manager = session_manager
        self.action_logic = ActionExecutor(state)
        self.action_manager = action_manager # ActionManager passed from OrbiterApp
        self.constants = ConstantsManager.get_instance()
        self.shutdown_triggered = False # Flag for rule-driven shutdown
        
        # 1. Rule Hub
        rules_path = session_manager.get_active_rules_file()
        logger.debug(f"[{self.__class__.__name__}.__init__] - Active rules file: {rules_path}")
        self.rule_manager = RuleManager(self.session_manager.project_root, rules_path, self.session_manager) # Pass session_manager
        logger.debug(f"[{self.__class__.__name__}.__init__] - RuleManager initialized.")

        # 2. Centralized Registration
        self.registration_manager = RegistrationManager(None, self, self.session_manager, self.action_manager, self.rule_manager)
        logger.debug(f"[{self.__class__.__name__}.__init__] - Engine initialization complete.")

    def _get_symbol_key(self, instrument) -> str:
        """Get symbol key from instrument dict."""
        if isinstance(instrument, dict):
            token = instrument.get('token', '')
            exch = instrument.get('exchange', 'NSE')
            return f"{exch}|{token}"
        return str(instrument)

    def _get_lookup_key(self, instrument) -> str:
        """Get lookup key (same as symbol key for now)."""
        return self._get_symbol_key(instrument)

    def tick(self, buffered_ticks: dict = None):
        """
        Executes the trading cycle for all instruments.
        
        Args:
            buffered_ticks: Optional dict of {symbol: [tick_data, ...]} from TickProcessor.
                           If provided, only processes symbols with new ticks.
                           If None, processes all symbols (full scan).
        """
        symbols_to_process = self.state.symbols
        
        if buffered_ticks:
            tick_symbols = list(buffered_ticks.keys())
            logger.debug(f"🔄 ENGINE TICK (buffered) - Processing {len(tick_symbols)} symbols with new data")
            
            # Filter to only symbols with new ticks
            symbols_to_process = [
                s for s in self.state.symbols
                if self._get_symbol_key(s) in tick_symbols or self._get_lookup_key(s) in tick_symbols
            ]
            
            if not symbols_to_process:
                logger.trace("No symbols with new ticks to process")
                return
        else:
            logger.info(f"🔄 ENGINE TICK (full scan) - Universe: {len(self.state.symbols)} symbols")
        
        # Reset scan metrics for this tick
        self.state.last_scan_metrics = []

        # Evaluate global (non-instrument specific) rules
        logger.trace(f"[{self.__class__.__name__}.tick] - Evaluating global engine rules.")
        global_actions = self.rule_manager.evaluate(source=self, context=self.constants.get('fact_contexts', 'engine_global_context'))
        if global_actions:
            logger.debug(f"[{self.__class__.__name__}.tick] - Executing {len(global_actions)} global engine actions.")
            self.action_manager.execute_batch(global_actions)

        # Evaluate instrument-specific rules
        if not symbols_to_process:
            logger.debug(f"[{self.__class__.__name__}.tick] - No symbols to process in this tick.")
            return

        for instrument in symbols_to_process:
            # Extract token string if it's a dictionary (Universe is often a list of dicts)
            token = instrument.get('token') if isinstance(instrument, dict) else instrument
            exch = instrument.get('exchange', 'NSE') if isinstance(instrument, dict) else 'NSE'
            
            # Skip dynamic resolution - tokens in instruments.json are correct
            # get_near_future is broken for MCX (returns symbol name instead of numeric token)
            
            # FIX: Resolve symbol name to numeric token for MCX before creating lookup key
            # This ensures we look up the correct key in SYMBOLDICT (where data is stored by numeric token)
            if exch.upper() == 'MCX' and token and not token.isdigit():
                # Try to resolve using mcx_futures_map
                import json
                import os
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                futures_map_path = os.path.join(project_root, 'orbiter', 'data', 'mcx_futures_map.json')
                if os.path.exists(futures_map_path):
                    try:
                        with open(futures_map_path, 'r') as f:
                            mcx_map = json.load(f)
                        if token.upper() in mcx_map:
                            resolved_token = str(mcx_map[token.upper()][4]) if len(mcx_map[token.upper()]) > 4 else token
                            if resolved_token != token:
                                logger.trace(f"[tick] Resolved {token} -> {resolved_token} for lookup")
                                token = resolved_token
                    except Exception as e:
                        logger.trace(f"[tick] Failed to resolve MCX token: {e}")
            
            lookup_key = f"{exch}|{token}"
            
            logger.trace(f"[{self.__class__.__name__}.tick] - Processing token: {token} | Lookup: {lookup_key}")
            
            # Pack instrument data into extra_facts with 'instrument.' prefix
            # Also inject 'position' for SL/TP filters
            extra_facts = {
                'token': token, 
                'instrument.exchange': exch, 
                'instrument_exchange': exch,
                'position': self.state.active_positions.get(lookup_key, {}),
                'portfolio.active_positions': len(self.state.active_positions),
                'portfolio_active_positions': len(self.state.active_positions),
            }
            if isinstance(instrument, dict):
                for k, v in instrument.items():
                    extra_facts[f"instrument.{k}"] = v
            
            # 📊 Collect Reporting Metrics
            # 🔄 For BSE stocks, use NSE NIFTY data for ADX calculation
            data_token = token
            data_exch = exch
            raw_data = None
            if exch == 'BSE':
                # Use NIFTY on NSE for ADX calculation
                nifty_token = '26000'  # NIFTY 50
                nifty_lookup = f"NSE|{nifty_token}"
                nifty_data = self.state.client.SYMBOLDICT.get(nifty_lookup)
                if nifty_data and nifty_data.get('candles'):
                    logger.info(f"🔄 Using NSE NIFTY data for ADX on BSE stock")
                    raw_data = nifty_data
            
            # Fallback lookup: try prefixed key, then raw token
            if not raw_data:
                raw_data = self.state.client.SYMBOLDICT.get(lookup_key)
            if not raw_data:
                logger.trace(f"[{self.__class__.__name__}.tick] - Prefixed lookup failed for {lookup_key}. Trying raw token: {token}")
                raw_data = self.state.client.SYMBOLDICT.get(token, {})
            
            if not raw_data:
                logger.warning(f"[{self.__class__.__name__}.tick] - No data found for token={token}, lookup_key={lookup_key}. SYMBOLDICT sample keys: {list(self.state.client.SYMBOLDICT.keys())[:10]}")

            # Symbol resolution: prioritize instrument.json symbol
            symbol_name = instrument.get('symbol') if isinstance(instrument, dict) else None
            if not symbol_name:
                symbol_name = self.state.client.master.TOKEN_TO_SYMBOL.get(token, f"{exch}|{token}").split('|')[-1]
            
            company_name = instrument.get('company_name') if isinstance(instrument, dict) else None
            if not company_name:
                company_name = self.state.client.master.TOKEN_TO_COMPANY.get(token, symbol_name)
            
            logger.trace(f"[{self.__class__.__name__}.tick] - Resolved: Symbol={symbol_name}, Company={company_name}")

            candles = raw_data.get('candles', [])
            last_candle = candles[-1] if candles else {}
            if not last_candle:
                logger.trace(f"[{self.__class__.__name__}.tick] - No candles found for {symbol_name}. raw_data keys: {list(raw_data.keys())}")
            
            # LTP extraction from SYMBOLDICT (which uses 'lp' from tick handler)
            ltp = safe_float(raw_data.get('lp') or raw_data.get('ltp') or last_candle.get('intc', 0))
            
            # Robust OHLC extraction - Fallback to LTP if no candles yet
            day_open = safe_float(raw_data.get('o') or raw_data.get('open') or last_candle.get('into', ltp))
            day_high = safe_float(raw_data.get('h') or raw_data.get('high') or last_candle.get('inth', ltp))
            day_low = safe_float(raw_data.get('l') or raw_data.get('low') or last_candle.get('intl', ltp))
            day_close = safe_float(raw_data.get('c') or raw_data.get('close') or last_candle.get('intc', ltp))

            logger.trace(f"[{self.__class__.__name__}.tick] - Price Stats for {symbol_name}: LTP={ltp}, Open={day_open}, High={day_high}, Low={day_low}, Close={day_close}")

            # Extract basic facts for reporting
            # We evaluate technical facts once here so they can be reused for scoring, actions AND reporting
            raw_data_for_filter = {'lp': ltp, 'o': day_open, 'h': day_high, 'l': day_low, 'c': day_close}
            logger.trace(f"[{self.__class__.__name__}.tick] - Filter Data for {symbol_name}: {raw_data_for_filter}")
            
            standardized = self.rule_manager.fact_converter.convert_candle_data(candles)
            standardized['_raw_list'] = candles # Pass raw candles for custom filters (F1-F11)
            
            tech_facts = self.rule_manager.fact_calc.calculate_technical_facts(
                standardized, 
                filter_config=self.session_manager.filters, 
                raw_data_for_filter=raw_data_for_filter,
                **extra_facts
            )
            
            logger.trace(f"[{self.__class__.__name__}.tick] - Tech Facts for {symbol_name}: {list(tech_facts.keys())}")

            # Inject calculated tech facts into extra_facts so evaluate() doesn't re-calculate them poorly
            for k, v in tech_facts.items():
                extra_facts[k.replace('.', '_')] = v
            
            # 🔥 Detailed scoring debug - log key indicators with weights
            # Weights: ADX=0.4, EMA_slope=0.3, SuperTrend=0.3
            adx = tech_facts.get('market.adx') or tech_facts.get('market_adx', 0)
            ema_fast = tech_facts.get('market.ema_fast') or tech_facts.get('market_ema_fast', 0)
            ema_slow = tech_facts.get('market.ema_slow') or tech_facts.get('market_ema_slow', 0)
            supertrend = tech_facts.get('filter.supertrend_direction') or tech_facts.get('market_supertrend_dir', 0)
            ema_slope = ((ema_fast - ema_slow) / ema_slow * 100) if ema_slow else 0
            
            # Manual score calculation: ADX*0.4 + EMA_slope*0.3 + SuperTrend*0.3
            # SuperTrend is -1 or 1, so multiply by 100 to make it comparable
            manual_score = (adx * 0.4) + (abs(ema_slope) * 0.3) + (supertrend * 100 * 0.3)
            
            logger.debug(f"📈 {symbol_name}: ADX={adx:.2f}*0.4 + EMA_slope={ema_slope:.3f}%*0.3 + ST={supertrend}*0.3 = Score:{manual_score:.2f}")
            
            # 🔥 Scoring for visibility
            score = 0.0
            score_details = {'sum_bi': 0.0, 'sum_uni': 0.0}
            if tech_facts:
                result = self.rule_manager.evaluate_score(source=self, context=self.constants.get('fact_contexts', 'instrument_context'), **{**extra_facts, 'raw_data_for_filter': raw_data_for_filter})
                # Handle both old (float) and new (tuple) return formats
                if isinstance(result, tuple):
                    score, score_details = result
                else:
                    score = result
                
                if self.state.verbose_logs:
                    logger.info(f"📊 {symbol_name}: Score {score:.2f} (sum_bi={score_details.get('sum_bi')}, sum_uni={score_details.get('sum_uni')})")

            # Pass score details to evaluate for strategy rules
            extra_facts_with_scores = {**extra_facts, 'strategy_sum_bi': score_details.get('sum_bi', 0), 'strategy_sum_uni': score_details.get('sum_uni', 0)}

            # MARGIN CALCULATION (PE/CE or Future)
            span_pe, span_ce = {'ok': False}, {'ok': False}
            base_symbol = company_name if company_name and '|' not in str(company_name) else symbol_name
            # Simplified base symbol logic for margin lookup
            import re
            base_symbol = re.sub(r'\d{2}[A-Z]{3}\d{2}[FC]$', '', base_symbol).strip()
            if base_symbol.endswith('-EQ'): base_symbol = base_symbol[:-3]

            product = self.state.config.get('OPTION_PRODUCT_TYPE', 'I')
            instrument_type = self.state.config.get('OPTION_INSTRUMENT', 'OPTSTK')
            hedge_steps = self.state.config.get('HEDGE_STEPS', 4)
            expiry_type = self.state.config.get('OPTION_EXPIRY', 'monthly')

            span_key = f"{base_symbol}|{expiry_type}|{instrument_type}|{hedge_steps}"
            cached = self.state.client.span_cache.get(span_key) if self.state.client.span_cache else None
            if cached:
                span_pe = cached.get('pe', {'ok': False})
                span_ce = cached.get('ce', {'ok': False})

            if ltp > 0 and (not span_pe.get('ok') or not span_ce.get('ok')):
                # 1. Try resolving as Option Spreads
                for side in ['PUT', 'CALL']:
                    spread = self.state.client.get_credit_spread_contracts(base_symbol, ltp, side=side, 
                                                                    hedge_steps=hedge_steps,
                                                                    expiry_type=expiry_type,
                                                                    instrument=instrument_type)
                    if spread.get('ok'):
                        if not spread.get('lot_size'): spread['lot_size'] = instrument.get('lotsize') or 1
                        margin = self.state.client.calculate_span_for_spread(spread, product_type=product)
                        if side == 'PUT': span_pe = margin
                        else: span_ce = margin
                
                # 2. Fallback: If spreads failed, it might be a Future strategy (MCX)
                if not span_pe.get('ok'):
                    # 🔥 CRITICAL: Get actual trading symbol from broker master
                    trading_symbol = self.state.client.master.TOKEN_TO_SYMBOL.get(token, f"{exch}|{token}")
                    
                    # If it returns "MCX|472790", it means lookup failed in master. 
                    # Try using company_name if it looks like a trading symbol (not containing |)
                    if "|" in trading_symbol and company_name and "|" not in str(company_name):
                        trading_symbol = company_name

                    future_details = {
                        'tsym': trading_symbol, 
                        'token': token,
                        'exchange': exch,
                        'lot_size': self.state.client.master.TOKEN_TO_LOTSIZE.get(token, 1)
                    }
                    if future_details['tsym'] and "|" not in str(future_details['tsym']):
                        margin = self.state.client.calculate_future_margin(future_details, product_type=product)
                        span_pe = margin
                        span_ce = margin # Mirror for visual consistency

                if self.state.client.span_cache is not None:
                    self.state.client.span_cache[span_key] = {'pe': span_pe, 'ce': span_ce}
                    self.state.client.save_span_cache()

            # Map tech facts to expected report keys (F1-F4)
            f_results = {
                'ef1_orb': {
                    'score': tech_facts.get('filter.orb', 0.0),
                    'orb_high': tech_facts.get('filter.orb.orb_high', 0.0),
                    'orb_low': tech_facts.get('filter.orb.orb_low', 0.0),
                    'orb_open': tech_facts.get('filter.orb.orb_open', 0.0)
                },
                'ef2_price_above_5ema': {
                    'score': tech_facts.get('filter.price_above_5ema', 0.0), 
                    'ema5': tech_facts.get('filter.price_above_5ema.ema5', tech_facts.get('market.ema_fast', 0.0))
                },
                'ef3_5ema_above_9ema': {'score': tech_facts.get('filter.ema5_above_9ema', 0.0)},
                'ef4_supertrend': {'score': tech_facts.get('filter.supertrend', 0.0)},
                'adx': tech_facts.get('market.adx', 0.0)
            }

            metric_entry = {
                'token': token, 'symbol': symbol_name, 'company_name': company_name,
                'day_open': day_open, 'day_high': day_high, 'day_low': day_low, 'day_close': day_close,
                'ltp': ltp, 'filters': f_results, 'score': score,
                'span_pe': span_pe, 'span_ce': span_ce,
                'trade_taken': token in self.state.active_positions
            }
            logger.trace(f"[{self.__class__.__name__}.tick] - Metric Entry for {symbol_name}: {metric_entry}")
            self.state.last_scan_metrics.append(metric_entry)

            # Use extra_facts_with_scores which includes sum_bi and sum_uni
            actions = self.rule_manager.evaluate(source=self, context=self.constants.get('fact_contexts', 'instrument_context'), **extra_facts_with_scores)
            
            # 🔥 SCORE THRESHOLD CHECK - Prevent trades with low/zero scores
            score_threshold = self.state.config.get('trend_score_threshold', 0.25)
            if score and abs(score) < score_threshold:
                if actions:
                    logger.debug(f"⏭️ Skipping {len(actions)} actions for {symbol_name}: score {score:.2f} < threshold {score_threshold}")
                actions = None
            
            if actions:
                # Inject symbol into each action's params so the executor knows which instrument triggered it
                logger.trace(f"🔭 [Engine.tick] BEFORE INJECT: symbol_name={symbol_name}, actions[0].get('params')={actions[0].get('params', {}) if actions else {}}")
                for action in actions:
                    if 'params' not in action: action['params'] = {}
                    if 'symbol' not in action['params']:
                        action['params']['symbol'] = symbol_name
                    logger.trace(f"🔭 [Engine.tick] Action params for {symbol_name}: {action.get('params', {})}")

                logger.debug(f"[{self.__class__.__name__}.tick] - Executing {len(actions)} instrument actions for {token} ({symbol_name}).")
                self.action_manager.execute_batch(actions)
        logger.debug(f"[{self.__class__.__name__}.tick] - Engine tick cycle complete.")


    def shutdown(self, reason: str = "EOD"):
        """
        Action: Triggers a rule-driven shutdown sequence by setting a flag.
        The actual square-off logic is now defined in system_rules.json.
        """
        logger.debug(f"[{self.__class__.__name__}.shutdown] - Shutdown requested. Reason: {reason}")
        
        # Stop tick processor
        if hasattr(self, '_tick_processor') and self._tick_processor:
            self._tick_processor.stop()
        
        self.shutdown_triggered = True
        logger.info(self.constants.get('magic_strings', 'engine_shutdown_triggered_msg').format(reason=reason))

    def prime_data(self):
        """Start market data feed - historical priming + live WebSocket + TickProcessor."""
        from orbiter.core.market_data import MarketData
        from orbiter.core.tick_processor import TickProcessor
        
        if not self.state.client:
            return False
        
        # Start WebSocket feed
        self.state.primed = MarketData.prime_and_subscribe(
            self.state.client,
            self.state.symbols
        )
        
        if self.state.primed:
            # Start tick processor with configurable interval
            interval = self.state.config.get('tick_process_interval_seconds', 60)
            enabled = self.state.config.get('tick_processor_enabled', True)
            
            self._tick_processor = TickProcessor(
                engine=self,
                tick_callback=self._on_buffered_ticks,
                interval_seconds=interval,
                enabled=enabled
            )
            
            # Register tick callback with broker client
            self.state.client.conn.tick_handler.register_tick_callback(self._tick_processor.on_tick)
            self._tick_processor.start()
            
            logger.info(f"✅ TickProcessor started (interval: {interval}s, enabled: {enabled})")
        
        return self.state.primed

    def _on_buffered_ticks(self, engine, ticks: dict):
        """Callback to process buffered ticks."""
        logger.debug(f"Processing {sum(len(v) for v in ticks.values())} buffered ticks")
        self.tick(buffered_ticks=ticks)
