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
        # Determine Exchange, Segment, and Symbol dynamically
        exchange = main_params.get("exchange", main_params.get("mainExchange", "NFO")).upper()
        segment = main_params.get("segment", main_params.get("mainSegment", "FUT")).upper()
        symbol = main_params.get("symbol", main_params.get("mainSymbol", main_params.get("underlying", "NIFTY"))).upper()
        
        # If symbol contains spaces, it's already a full underlying string; extract the first part
        if " " in symbol: symbol = symbol.split()[0]
        if symbol == "NIFTY50": symbol = "NIFTY"
        
        # AUTO-CORRECTION: NFO does not have an INDEX segment. 
        # If user/AI asks for NFO + INDEX, we must use FUT to make it work in Market Maya.
        if exchange == "NFO" and segment == "INDEX":
            segment = "FUT"
            
        # Construct the official Underlying string for the API
        underlying = f"{symbol} {segment} {exchange}"

        # 1. LEG GENERATION FIRST - To detect leg-specific settings that override master settings
        generated_legs = []
        any_leg_has_tsl = False
        for leg_input in (legs if isinstance(legs, list) else []):
            leg_payload = self._generate_leg_payload(leg_input, exchange, symbol)
            if leg_payload.get("isEnableStoplossTrailing"):
                any_leg_has_tsl = True
            generated_legs.append(leg_payload)

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

        # MUTUALLY EXCLUSIVE RULE: If any leg has TSL, disable master TSL to prevent 400 error
        if any_leg_has_tsl:
            trail_val = 0
            is_master_tsl_enabled = False
        else:
            is_master_tsl_enabled = True if trail_val > 0 else False

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
            "mainExchange": exchange,
            "mainSegment": segment,
            "mainSymbol": symbol,
            "isIntraday": main_params.get("isIntraday", main_params.get("is_intraday", True)),
            "productType": main_params.get("productType", "MIS"),
            "tradingStartTime": main_params.get("tradingStartTime", main_params.get("entry_time", "09:15:00")),
            "tradingEndTime": main_params.get("tradingEndTime", main_params.get("exit_time", "15:15:00")),
            "isRangeBreakOut": main_params.get("isRangeBreakOut", main_params.get("is_range_breakout", False)),
            "rangeEndTime": main_params.get("rangeEndTime", main_params.get("range_end_time", "09:20:00")),
            "isBtstStbt": main_params.get("isBtstStbt", main_params.get("is_btst_stbt", False)),
            "btstGapDays": int(main_params.get("btstGapDays", main_params.get("btst_gap_days", 1))),
            "isCombinedPremEntry": True if int(main_params.get("total_combined_premium", main_params.get("total_combined_premium", main_params.get("total_combined_prem", 0)))) > 0 else (main_params.get("is_combined_premium_entry", main_params.get("is_combined_prem_entry", False))),
            "totalCombinedPremium": int(main_params.get("total_combined_premium", main_params.get("total_combined_prem", 0))),
            
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
            
            # Master SL Trailing Logic (Strategy Level)
            "isEnableStoplossTrailing": is_master_tsl_enabled,
            "profitMove": trail_val,
            "slMove": trail_val,
            "noOfTrailSl": self._parse_trail_count(main_params.get("no_of_trail_sl", 0)),
            
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
            "requiredMargin": self._parse_margin(main_params.get("requiredMargin", main_params.get("required_margin", 1))),
            "shortDescription": main_params.get("shortDescription", ""),
            "detailedDescription": main_params.get("detailedDescription", ""),
            "strategyTypeId": self.strategy_type_id,
            "rebacktest": False,
            "effectAllSubStrategies": False,
            "legs": generated_legs
        }

        return payload


    def _generate_leg_payload(self, leg, default_exchange, symbol):
        strike_type_map = {
            "ATM": "Strike By ATM Value",
            "ATM%": "Strike By ATM %",
            "PREMIUM_RANGE": "Strike By Premium Range",
            "NEAREST_PREMIUM": "Strike By Nearest Premium",
            "DELTA_RANGE": "Strike By Delta Range",
            "NEAREST_DELTA": "Strike By Nearest Delta",
            "THETA_RANGE": "Strike By Theta Range",
            "NEAREST_THETA": "Strike By Nearest Theta",
            "STRIKE BY ATM VALUE": "Strike By ATM Value",
            "STRIKE BY ATM %": "Strike By ATM %"
        }
        
        # Robust ATM Type Mapping - Ensure we always get the full string
        raw_atm = str(leg.get("atmType", leg.get("strike_type", "ATM"))).upper()
        if "STRIKE BY" in raw_atm:
             # Already a full string, just ensure correct case
             atm_type = raw_atm.title().replace("Atm", "ATM")
        else:
             atm_type = strike_type_map.get(raw_atm, "Strike By ATM Value")
        
        # Ranges
        s_range = int(float(leg.get("premium_start_range", leg.get("premiumStartRange", 10))))
        e_range = int(float(leg.get("premium_end_range", leg.get("premiumEndRange", 20))))
        
        # Strike/ATM value
        atm_val = leg.get("strike", leg.get("atm", 0))
        if isinstance(atm_val, str):
            # Extract number including decimals
            nums = re.findall(r"[-+]?\d*\.?\d+", atm_val)
            atm_val = float(nums[0]) if nums else 0.0
        else:
            atm_val = float(atm_val)

        # Smart Casting: Only keep as float if it's Delta or Theta related
        if "Delta" not in atm_type and "Theta" not in atm_type:
            atm_val = int(atm_val)

        # Target/SL
        t_val = int(float(leg.get("target", 0)))
        s_val = int(float(leg.get("sl", 0)))
        
        # Profit Locking logic
        pl = leg.get("profit_locking", leg.get("profitLocking", {}))

        # Trailing SL logic
        tsl = leg.get("trail_sl", leg.get("trailSl", {}))

        # Leg Trailing Robust Mapping: Look for values in both nested and top-level to prevent data loss
        has_tsl = True if (int(tsl.get("trail_sl_market_move", leg.get("trail_sl_market_move", leg.get("trailSlMarketMove", 0)))) > 0 or 
                          int(tsl.get("trail_sl_move", leg.get("trail_sl_move", leg.get("trailSlMove", 0)))) > 0) else False

        # Leg Profit Locking Robust Mapping: Quadruple-redundant search
        # Leg Profit Locking Robust Mapping
        raw_no_trail_tp = leg.get("noOfTimeTrailTp", 
                          leg.get("no_of_time_trail", 
                          pl.get("no_of_time_trail", 
                          pl.get("noOfTimeTrailTp", 0))))
        no_trail_tp = self._parse_trail_count(raw_no_trail_tp)

        # Leg Trailing SL mapping
        raw_trail_sl = self._parse_trail_count(leg.get("noOfTimeTrailSl", tsl.get("no_of_time_trail", leg.get("no_of_time_trail", 0))))
        if not has_tsl:
            raw_trail_sl = 0


        return {
            "id": "",
            "isIdle": leg.get("is_idle", False),
            "tradeSide": str(leg.get("tradeSide", leg.get("action", "BUY"))).upper(),
            "lot": int(leg.get("lot", leg.get("lots", 1))),
            "segment": str(leg.get("segment", "OPT")).upper(),
            "expiry": self._resolve_expiry(leg.get("expiry", leg.get("expiry_bucket")), symbol),
            "optionType": str(leg.get("optionType", leg.get("option", "CE"))).upper(),
            "atmType": atm_type,
            "premiumStartRange": int(float(leg.get("premiumStartRange", leg.get("premium_start_range", 10)))),
            "premiumEndRange": int(float(leg.get("premiumEndRange", leg.get("premium_end_range", 20)))),
            "strikeDirection": self._map_strike_direction(leg.get("strikeDirection", leg.get("strike_direction", "BOTH"))),
            "atm": atm_val,
            "strikeCondition": self._map_condition(leg.get("strikeCondition", leg.get("strike_condition", "Any"))),
            "isEnableLegTarget": True if t_val > 0 else False,
            "targetBy": self._map_target_by(leg.get("targetBy", leg.get("target_by", "Target by Money")), "Target"),
            "target": t_val,
            "isEnableActionOnTarget": leg.get("isEnableActionOnTarget", leg.get("is_enable_action_on_target", False)),
            "actionOnTarget": leg.get("actionOnTarget", leg.get("action_on_target", "Execute Leg")),
            "actionOnTargetLegNo": int(leg.get("actionOnTargetLegNo", leg.get("action_on_target_leg_no", 0))),
            "actionOnTargetDelay": int(leg.get("actionOnTargetDelay", leg.get("action_on_target_delay", 0))),
            "isProfitLockingAndTrailing": True if (int(pl.get("if_profit_reaches", pl.get("ifProfitReaches", leg.get("if_profit_reaches", 0)))) > 0) else False,
            "ifProfitReaches": int(pl.get("if_profit_reaches", pl.get("ifProfitReaches", leg.get("if_profit_reaches", 0)))),
            "lockMinimumProfit": int(pl.get("lock_minimum_profit", pl.get("lockMinimumProfit", leg.get("lock_minimum_profit", 0)))),
            "increseInProfitBy": int(pl.get("increse_in_profit_by", pl.get("increseInProfitBy", leg.get("increse_in_profit_by", 0)))),
            "trailProfitBy": int(pl.get("trail_profit_by", pl.get("trailProfitBy", leg.get("trail_profit_by", 0)))),
            "noOfTimeTrailTp": no_trail_tp,
            "isEnableLegStoploss": True if (s_val > 0 or leg.get("isEnableLegStoploss", leg.get("is_enable_leg_stoploss", False))) else False,
            "slBy": self._map_target_by(leg.get("slBy", leg.get("sl_by", "SL by Money")), "SL"),
            "sl": s_val,
            "isEnableActionOnSl": leg.get("isEnableActionOnSl", leg.get("is_enable_action_on_sl", False)),
            "actionOnSl": leg.get("actionOnSl", leg.get("action_on_sl", "Execute Leg")),
            "actionOnSlLegNo": int(leg.get("actionOnSlLegNo", leg.get("action_on_sl_leg_no", 0))),
            "actionOnSlDelay": int(leg.get("actionOnSlDelay", leg.get("action_on_sl_delay", 0))),
            "isEnableStoplossTrailing": has_tsl,
            "trailSlMarketMove": int(tsl.get("trail_sl_market_move", leg.get("trail_sl_market_move", leg.get("trailSlMarketMove", 0)))) if has_tsl else 0,
            "trailSlMove": int(tsl.get("trail_sl_move", leg.get("trail_sl_move", leg.get("trailSlMove", 0)))) if has_tsl else 0,
            "noOfTimeTrailSl": raw_trail_sl,
            "no_of_time_trail_sl": raw_trail_sl, # Redundant underscored field for some API versions
            "isWaitAndTrade": leg.get("isWaitAndTrade", leg.get("is_wait_and_trade", False)),
            "waitFor": leg.get("waitFor", leg.get("wait_for", "Up %")),
            "waitValue": int(float(leg.get("waitValue", leg.get("wait_value", 0)))),
            "isExecuteOnRangeBreakout": leg.get("isExecuteOnRangeBreakout", leg.get("is_execute_on_range_breakout", False)),
            "executeOnRangeBreakout": leg.get("executeOnRangeBreakout", leg.get("execute_on_range_breakout", "Range High Break"))
        }

    def _parse_margin(self, value):
        """
        Cleans and parses margin strings (e.g., '~1.5L', '200k') into integers.
        """
        if isinstance(value, (int, float)):
            return int(value)
        
        try:
            # Remove common non-numeric characters
            s = str(value).lower().replace("~", "").replace(",", "").replace(" ", "").replace("approx", "")
            
            # Handle 'L' (Lakh) or 'k' (Thousand)
            multiplier = 1
            if 'l' in s:
                multiplier = 100000
                s = s.replace('l', '')
            elif 'k' in s:
                multiplier = 1000
                s = s.replace('k', '')
            
            # Extract only the numeric part (including decimal)
            numeric_part = re.findall(r"[-+]?\d*\.\d+|\d+", s)
            if numeric_part:
                return int(float(numeric_part[0]) * multiplier)
            return 1
        except:
            return 1

    def _parse_trail_count(self, value):
        """
        Parses trail count values. Maps 'unlimited' strings and AI proxies (0, 99, 999) to 9999 
        because Market Maya V3 API rejects a count of 0 when trailing is enabled.
        """
        if isinstance(value, str):
            if value.lower() == "unlimited":
                return 9999
        try:
            val = int(value)
            # If the value is 99 or above, it's usually an AI proxy for unlimited. 
            # If the value is 0, the API will reject it if trailing is enabled.
            # Map both to 9999.
            if val >= 99 or val == 0:
                return 9999
            return val
        except:
            return 9999

    def _resolve_expiry(self, expiry, symbol):
        """
        Forces Current Week for Indices if the value is default or missing.
        """
        expiry = str(expiry) if expiry else "Current Month"
        symbol = str(symbol).upper()
        
        # If it's an index and we are at the default 'Current Month', upgrade to 'Current Week'
        if ("NIFTY" in symbol or "BANKNIFTY" in symbol) and expiry == "Current Month":
            return "Current Week"
            
        return expiry

    def _map_target_type(self, value, category):
        """
        Maps shorthand like 'Point' to 'Target by Point' or 'SL by Point'.
        """
        value = str(value)
        # If it's already a full string, return it
        if "by" in value.lower():
            return value
            
        mapping = {
            "POINT": f"{category} by Point",
            "MONEY": f"{category} by Money",
            "PERCENTAGE": f"{category} by Percentage",
            "PERCENT": f"{category} by Percentage",
            "DELTA": f"{category} by Delta",
            "THETA": f"{category} by Theta"
        }
        
        return mapping.get(value.upper(), f"{category} by Money")

    def _map_condition(self, value):
        """
        Maps shorthand like 'AboveEqual' to 'AboveEqual (>=)'.
        """
        val = str(value)
        if "(" in val:
            return val
            
        mapping = {
            "ABOVEEQUAL": "AboveEqual (>=)",
            "BELOWEQUAL": "BelowEqual (<=)",
            "ANY": "Any"
        }
        return mapping.get(val.upper(), "Any")

    def _map_strike_direction(self, value):
        """
        Maps direction to uppercase BOTH/ITM/OTM.
        """
        val = str(value).upper()
        if val in ["BOTH", "ITM", "OTM"]:
            return val
        return "BOTH"

    def _map_target_by(self, value, category):
        """
        Maps shorthand like 'Money' to 'Target by Money' or 'SL by Money'.
        """
        val = str(value)
        if "by" in val.lower():
            return val
            
        mapping = {
            "MONEY": f"{category} by Money",
            "POINT": f"{category} by Point",
            "PERCENTAGE": f"{category} by Percentage",
            "PERCENT": f"{category} by Percentage",
            "DELTA": f"{category} by Delta",
            "THETA": f"{category} by Theta"
        }
        return mapping.get(val.upper(), f"{category} by Money")

# Singleton instance
generator = PayloadGenerator()
