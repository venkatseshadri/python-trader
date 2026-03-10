# orbiter/core/strategy_selector.py

import logging
from orbiter.utils.yf_adapter import get_market_adx, get_market_regime
from orbiter.utils.argument_parser import ArgumentParser

logger = logging.getLogger("ORBITER")


class StrategySelector:
    """Handles dynamic strategy selection based on market regime."""

    @staticmethod
    def evaluate(context: dict, project_root: str) -> tuple[str | None, str | None]:
        """
        Evaluate market regime and select strategy.
        
        Returns:
            tuple: (strategy_code, strategy_id) or (None, None) if not enabled
        """
        dynamic_config = context.get('dynamic_strategy_config')
        if not dynamic_config or not dynamic_config.get('enabled', False):
            return None, None

        regime = get_market_regime('SENSEX')
        adx = get_market_adx('SENSEX')

        logger.info(f"📊 Market Regime Check: SENSEX ADX = {adx} -> {regime.upper()}")

        strategies = dynamic_config.get('strategies', {})
        if regime == 'sideways':
            strategy = strategies.get('sideways', {})
        elif regime == 'trending':
            strategy = strategies.get('trending', {})
        else:
            strategy = strategies.get('trending', {})

        if not strategy:
            return None, None

        strategy_code = strategy.get('strategyCode')
        strategy_id = strategy.get('strategyId')

        if strategy_code:
            strategy_id = ArgumentParser._resolve_strategy(strategy_code, project_root)

        logger.info(f"🎯 Dynamic Strategy Selected: {strategy_code or strategy_id} ({regime})")
        return strategy_code, strategy_id
