"""
Hardware-level energy monitoring using RAPL (via CodeCarbon) with robust fallback.
"""

from __future__ import annotations

import logging
import os
import threading
from typing import Any, Dict, Optional

try:
    from codecarbon import EmissionsTracker
    HAS_CODECARBON = True
except ImportError:
    HAS_CODECARBON = False

logger = logging.getLogger(__name__)

class HardwareEnergyMonitor:
    """
    Wraps CodeCarbon EmissionsTracker to provide safe, start/stop hardware monitoring.
    Falls back to None/Zero if hardware counters are unavailable.
    """

    def __init__(self, country_iso_code: str = "USA"):
        self.enabled = HAS_CODECARBON
        self.tracker: Optional[EmissionsTracker] = None
        self.country_iso_code = country_iso_code
        self._lock = threading.Lock()
        
        if self.enabled:
            try:
                # Initialize in offline mode to avoid API calls during the run
                self.tracker = EmissionsTracker(
                    measure_power_secs=1,
                    save_to_file=False,
                    logging_level="error",
                    tracking_mode="process",
                    country_iso_code=self.country_iso_code
                )
                logger.info("CodeCarbon initialized for hardware monitoring.")
            except Exception as e:
                logger.warning(f"Failed to initialize CodeCarbon: {e}. Falling back to rule-based estimation.")
                self.enabled = False

    def start(self):
        if not self.enabled or not self.tracker:
            return
        
        with self._lock:
            try:
                self.tracker.start()
            except Exception as e:
                logger.warning(f"Failed to start hardware tracker: {e}")
                self.enabled = False

    def stop(self) -> Dict[str, Any]:
        """
        Stops the tracker and returns the measured metrics.
        Returns empty dict if not enabled.
        """
        if not self.enabled or not self.tracker:
            return {}

        with self._lock:
            try:
                emissions = self.tracker.stop()
                # CodeCarbon returns total emissions in kg, we want grams or mg
                # It also tracks energy in kWh
                
                # Retrieve final totals
                energy_kwh = self.tracker._total_energy.kWh
                
                return {
                    "hardware_measured": True,
                    "energy_kwh": float(energy_kwh),
                    "emissions_kg": float(emissions) if emissions is not None else 0.0,
                    "source": "RAPL/CodeCarbon"
                }
            except Exception as e:
                logger.warning(f"Failed to stop hardware tracker: {e}")
                return {"hardware_measured": False, "error": str(e)}

# Global monitor instance
_monitor = HardwareEnergyMonitor()

def get_monitor() -> HardwareEnergyMonitor:
    return _monitor
