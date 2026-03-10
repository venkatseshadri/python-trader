# orbiter/core/reporting_service.py

import logging
import time
import os
import gspread
from orbiter.core.ancillary_service import AncillaryService
from orbiter.bot.sheets import log_scan_metrics, Credentials, SCOPE, _get_or_create_worksheet, SCAN_METRICS_HEADER

logger = logging.getLogger("ORBITER")


class ReportingService(AncillaryService):
    """Handles periodic reporting to Google Sheets."""

    def name(self) -> str:
        return "ReportingService"

    def __init__(self, app):
        super().__init__(app)
        self.project_root = app.ctx.project_root
        self.last_scan_log_ts = 0
        self.last_active_strategy = None

    def _run_loop(self):
        engine = self.app.ctx.engine
        if not engine or not getattr(engine, 'initialized', False):
            time.sleep(10)
            return

        now_ts = time.time()
        if now_ts - self.last_scan_log_ts >= 60:
            metrics = getattr(engine.state, 'last_scan_metrics', [])
            if not metrics:
                time.sleep(10)
                return

            current_strat = self.app.ctx.session_manager.strategy_bundle.get('name')
            tab_name = f"scan_metrics_{engine.state.segment_name.lower()}"

            if self.last_active_strategy != current_strat:
                self._clear_sheet(tab_name)
                self.last_active_strategy = current_strat

            logger.info(f"📊 Publishing {len(metrics)} scan metrics to Google Sheets [{tab_name}]...")
            log_scan_metrics(metrics, tab_name=tab_name)

            if hasattr(engine.state, 'syncer') and engine.state.syncer:
                engine.state.syncer.sync_active_positions_to_sheets(engine.state)

            self.last_scan_log_ts = now_ts

        time.sleep(10)

    def _clear_sheet(self, tab_name: str):
        """Clear sheet on strategy change."""
        try:
            creds_path = os.path.join(self.project_root, "orbiter", "bot", "credentials.json")
            creds = Credentials.from_service_account_file(creds_path, scopes=SCOPE)
            client = gspread.authorize(creds)
            book = client.open("trade_log")
            sheet = _get_or_create_worksheet(book, tab_name)
            sheet.clear()
            sheet.insert_row(SCAN_METRICS_HEADER, 1)
            logger.info(f"🧹 Cleared {tab_name} due to strategy switch")
        except Exception as e:
            logger.error(f"⚠️ Sheet clear failed: {e}")
