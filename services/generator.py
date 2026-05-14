import json
import re
from config import Config

class PayloadGenerator:
    def __init__(self):
        # The strategyTypeId for Unified Strategy Builder from sample payload
        self.strategy_type_id = "7D0enBHWMRaf4ebeKaB0$OOMQaC0$aC0$"

    def generate_v3_payload(self, main_params, legs):
        """
        Generates a comprehensive V3 payload compatible with Market Maya's CreateUnifiedStrategy API.
        """
        # Determine Symbol and Underlying suffix
        underlying_raw = str(main_params.get("underlying", "NIFTY")).upper()
        symbol = underlying_raw.split()[0] # e.g. "NIFTY"
        
        if symbol == "NIFTY50": symbol = "NIFTY"
        
        # Standardize underlying name for the API
        underlying = f"{symbol} FUT NFO"

        # Determine if Master Target/SL should be enabled
        target_val = int(main_params.get("intradayTarget", main_params.get("master_target", main_params.get("target", 0))))
        sl_val = int(main_params.get("intradaySl", main_params.get("master_stop_loss", main_params.get("sl", 0))))
        
        # Trailing SL Logic (Handle both integer and object format from AI)
        trail_input = main_params.get("trailing_sl", main_params.get("trail_sl", 0))
        if isinstance(trail_input, dict):
            trail_val = int(trail_input.get("activation", trail_input.get("increment", 0)))
        else:
            try: trail_val = int(trail_input)
            except: trail_val = 0

        # Master Profit Locking Logic
        mpl = main_params.get("master_profit_locking", {})
        
        # Determine Trading Days (runMon, runTue, etc.)
        trading_days = main_params.get("trading_days", main_params.get("days", main_params.get("runDays", [])))
        if isinstance(trading_days, str):
            trading_days = [d.strip() for d in trading_days.split(",")]
        
        days_map = {
            "runMon": any(d.lower().startswith("mon") for d in trading_days) if trading_days else True,
            "runTue": any(d.lower().startswith("tue") for d in trading_days) if trading_days else True,
            "runWed": any(d.lower().startswith("wed") for d in trading_days) if trading_days else True,
            "runThu": any(d.lower().startswith("thu") for d in trading_days) if trading_days else True,
            "runFri": any(d.lower().startswith("fri") for d in trading_days) if trading_days else True,
        }
        is_explicit_days = len(trading_days) > 0

        payload = {
            "id": "",
            "strategyName": main_params.get("strategyName", main_params.get("strategy_name", "Aditya")),
            "underlying": underlying,
            "mainExchange": "NFO",
            "mainSegment": "FUT",
            "mainSymbol": symbol,
            "isIntraday": main_params.get("isIntraday", main_params.get("is_intraday", True)),
            "productType": main_params.get("productType", "MIS"),
            "tradingStartTime": main_params.get("tradingStartTime", main_params.get("entry_time", "09:15:00")),
            "tradingEndTime": main_params.get("tradingEndTime", main_params.get("exit_time", "15:15:00")),
            "isRangeBreakOut": main_params.get("isRangeBreakOut", main_params.get("is_range_breakout", False)),
            "rangeEndTime": main_params.get("rangeEndTime", main_params.get("range_end_time", "09:20:00")),
            "isBtstStbt": main_params.get("isBtstStbt", main_params.get("is_btst_stbt", False)),
            "btstGapDays": int(main_params.get("btstGapDays", main_params.get("btst_gap_days", 1))),
            "isCombinedPremEntry": main_params.get("is_combined_prem_entry", False),
            "totalCombinedPremium": int(main_params.get("total_combined_premium", 0)),
            
            # Master Target Logic
            "isEnableMasterTarget": True if target_val > 0 else False,
            "targetBy": main_params.get("target_by", "Combined Profit"),
            "intradayTarget": target_val,
            "isEnableActionOnTarget": False,
            "actionOnTarget": "Reexecute",
            
            # Master Profit Locking Logic (Strategy Level)
            "isEnableProfitLockingTrailing": True if int(mpl.get("if_profit_reaches", 0)) > 0 else False,
            "ifProfitReaches": int(mpl.get("if_profit_reaches", 0)),
            "lockMinimumProfit": int(mpl.get("lock_minimum_profit", 0)),
            "increseInProfitBy": int(mpl.get("increse_in_profit_by", 0)),
            "trailProfitBy": int(mpl.get("trail_profit_by", 0)),
            "noOfTimeTrailTp": int(mpl.get("no_of_time_trail", 0)),
            "noOfIntradayCycle": int(main_params.get("reexecute_on_target_count", 0)),
            "intradayCycleDelay": int(main_params.get("reexecute_on_target_delay", 0)),
            
            # Master SL Logic
            "isEnableMasterSl": True if sl_val > 0 else False,
            "slBy": main_params.get("sl_by", "Combined Loss"),
            "intradaySl": sl_val,
            "isEnableActionOnMasterSl": False,
            "actionOnSl": "Reexecute",
            
            # Master SL Trailing Logic
            "isEnableStoplossTrailing": True if trail_val > 0 else False,
            "profitMove": trail_val,
            "slMove": trail_val,
            "noOfTrailSl": 0,
            
            "noOfReexecuteOnSl": int(main_params.get("reexecute_on_sl_count", 0)),
            "reexecuteDelayOnSl": int(main_params.get("reexecute_on_sl_delay", 0)),
            "isEnableSqroffBeforeExpiryDays": main_params.get("isEnableSqroffBeforeExpiryDays", main_params.get("sqroff_before_expiry", False)),
            "sqroffBeforeExpiryDays": int(main_params.get("sqroffBeforeExpiryDays", main_params.get("sqroff_before_expiry_days", 0))),
            "sqroffTime": "15:15:00",
            
            # Advanced / Checkbox Parameters
            "isEnableWorkingDays": is_explicit_days,
            "runMon": days_map["runMon"],
            "runTue": days_map["runTue"],
            "runWed": days_map["runWed"],
            "runThu": days_map["runThu"],
            "runFri": days_map["runFri"],
            "runSat": False,
            "runSun": False,
            "enableVixFilter": main_params.get("enableVixFilter", main_params.get("vix_filter", False)),
            "vixStartValue": int(main_params.get("vixStartValue", main_params.get("vix_start_value", 1))),
            "vixEndValue": int(main_params.get("vixEndValue", main_params.get("vix_end_value", 5))),
            "enableTpSlOnPauseStrategy": False,
            "sqroffAllLegs": main_params.get("sqroffAllLegs", main_params.get("sqroff_all_legs", main_params.get("squareOffAllLegs", False))),
            "pauseAndSqroffTradingOnMarginExeed": main_params.get("pauseAndSqroffTradingOnMarginExeed", main_params.get("sqroff_on_rejection", main_params.get("sqroffPositionOnRejection", False))),
            "requiredMargin": int(main_params.get("requiredMargin", 1)),
            "shortDescription": main_params.get("shortDescription", ""),
            "detailedDescription": main_params.get("detailedDescription", ""),
            "legs": [self._generate_leg_payload(leg) for leg in (legs if isinstance(legs, list) else [])],
            "strategyTypeId": self.strategy_type_id,
            "rebacktest": False,
            "effectAllSubStrategies": False
        }
        return payload

    def _generate_leg_payload(self, leg):
        # Strike Selection logic mapping
        strike_type_map = {
            "ATM": "Strike By ATM Value",
            "ATM%": "Strike By ATM %",
            "PREMIUM_RANGE": "Strike By Premium Range",
            "NEAREST_PREMIUM": "Strike By Nearest Premium",
            "DELTA_RANGE": "Strike By Delta Range",
            "NEAREST_DELTA": "Strike By Nearest Delta",
            "THETA_RANGE": "Strike By Theta Range",
            "NEAREST_THETA": "Strike By Nearest Theta"
        }
        
        raw_strike_type = str(leg.get("strike_type", leg.get("strikeType", "ATM"))).upper()
        atm_type = strike_type_map.get(raw_strike_type, "Strike By ATM Value")

        # Extract numeric value for ATM / ATM%
        atm_val = 0
        atm_input = str(leg.get("atm", leg.get("strike", "0")))
        nums = re.findall(r'[-+]?\d*\.?\d+', atm_input)
        if nums: atm_val = int(float(nums[0]))

        # Range Logic (for Premium/Delta/Theta)
        s_range = int(leg.get("start_range", leg.get("premiumStartRange", 10)))
        e_range = int(leg.get("end_range", leg.get("premiumEndRange", 20)))

        # Target/SL logic
        leg_target = int(leg.get("target", 0))
        leg_sl = int(leg.get("sl", 0))
        
        # Profit Locking logic
        pl = leg.get("profit_locking", {})
        
        # Trailing SL logic
        tsl = leg.get("trail_sl", {})

        return {
            "id": "",
            "isIdle": leg.get("is_idle", False),
            "tradeSide": str(leg.get("tradeSide", leg.get("action", "BUY"))).upper(),
            "lot": int(leg.get("lot", leg.get("lots", 1))),
            "segment": str(leg.get("segment", "OPT")).upper(),
            "expiry": str(leg.get("expiry", "Current Month")),
            "optionType": str(leg.get("optionType", leg.get("option", "CE"))).upper(),
            "atmType": atm_type,
            "premiumStartRange": s_range,
            "premiumEndRange": e_range,
            "strikeDirection": str(leg.get("direction", "BOTH")).upper(),
            "atm": atm_val,
            "strikeCondition": str(leg.get("condition", "Any")),
            
            # Leg Target
            "isEnableLegTarget": True if leg_target > 0 else False,
            "targetBy": leg.get("target_by", "Target by Money"),
            "target": leg_target,
            "isEnableActionOnTarget": True if leg.get("action_on_target") else False,
            "actionOnTarget": leg.get("action_on_target", "Execute Leg"),
            "actionOnTargetLegNo": int(leg.get("target_action_leg_no", 0)),
            "actionOnTargetDelay": int(leg.get("target_action_delay", 0)),
            
            # Leg Profit Locking
            "isProfitLockingAndTrailing": True if int(pl.get("if_profit_reaches", 0)) > 0 else False,
            "ifProfitReaches": int(pl.get("if_profit_reaches", 0)),
            "lockMinimumProfit": int(pl.get("lock_minimum_profit", 0)),
            "increseInProfitBy": int(pl.get("increse_in_profit_by", 0)),
            "trailProfitBy": int(pl.get("trail_profit_by", 0)),
            "noOfTimeTrailTp": int(pl.get("no_of_time_trail", 0)),
            
            # Leg SL
            "isEnableLegStoploss": True if leg_sl > 0 else False,
            "slBy": leg.get("sl_by", "SL by Money"),
            "sl": leg_sl,
            "isEnableActionOnSl": True if leg.get("action_on_sl") else False,
            "actionOnSl": leg.get("action_on_sl", "Execute Leg"),
            "actionOnSlLegNo": int(leg.get("sl_action_leg_no", 0)),
            "actionOnSlDelay": int(leg.get("sl_action_delay", 0)),
            
            # Leg SL Trailing
            "isEnableStoplossTrailing": True if int(tsl.get("trail_sl_by", 0)) > 0 else False,
            "trailSlMarketMove": int(tsl.get("increase_profit_by", 0)),
            "trailSlMove": int(tsl.get("trail_sl_by", 0)),
            "noOfTimeTrailSl": int(tsl.get("no_of_time_trail", 0)),
            
            # Wait & Trade
            "isWaitAndTrade": leg.get("wait_and_trade", False),
            "waitFor": leg.get("wait_for", "Up %"),
            "waitValue": int(leg.get("wait_value", 0)),
            
            "isExecuteOnRangeBreakout": leg.get("is_execute_on_range_breakout", False),
            "executeOnRangeBreakout": leg.get("execute_on_range_breakout", "Range High Break")
        }

# Singleton instance
generator = PayloadGenerator()
